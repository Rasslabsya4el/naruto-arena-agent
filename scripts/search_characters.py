#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCES_DIR = REPO_ROOT / "skills" / "naruto-arena-team-builder" / "references"
CHAKRA_TYPES = ("tai", "nin", "gen", "bloodline", "random")
RANK_BAND_SEQUENCE = (
    "Academy Student",
    "Genin",
    "Chuunin",
    "Missing-Nin",
    "Anbu",
    "Jounin",
    "Sannin",
    "Jinchuuriki",
)
RANK_BAND_INDEX = {label: index for index, label in enumerate(RANK_BAND_SEQUENCE)}
RANK_BAND_ALIASES = {
    "academystudent": "Academy Student",
    "academy": "Academy Student",
    "genin": "Genin",
    "chunin": "Chuunin",
    "chuunin": "Chuunin",
    "missingnin": "Missing-Nin",
    "missingninja": "Missing-Nin",
    "anbu": "Anbu",
    "jonin": "Jounin",
    "jounin": "Jounin",
    "sannin": "Sannin",
    "jinchuriki": "Jinchuuriki",
    "jinchuuriki": "Jinchuuriki",
}

PRESSURE_TAGS = {
    "character.capability.damage_effects",
    "character.capability.damage_amplification",
    "character.capability.damage_aoe",
    "character.capability.damage_single_target",
}
CONTROL_TAGS = {
    "character.capability.stun_effects",
    "character.capability.removal_effects",
    "character.capability.drain_effects",
}
SUSTAIN_TAGS = {
    "character.capability.heal_effects",
    "character.capability.protect_effects",
    "character.capability.damage_reduction",
}
PROTECTION_TAGS = {
    "character.capability.protect_effects",
    "character.capability.self_protection",
    "character.capability.ally_protection",
    "character.capability.damage_reduction",
}
SETUP_TAGS = {
    "character.capability.conditional_effects",
    "character.capability.combo_dependency",
    "character.capability.state_dependency",
}
RESOURCE_TAGS = {
    "character.capability.gain_effects",
    "character.capability.drain_effects",
    "character.capability.removal_effects",
}

ROLE_HINT_RULES = (
    {
        "role_hint": "pressure",
        "label": "Pressure",
        "description": "Direct damage or damage-amplification tags are present in the accepted bundle.",
        "tag_ids": tuple(sorted(PRESSURE_TAGS)),
        "effect_families": ("offense",),
    },
    {
        "role_hint": "control",
        "label": "Control",
        "description": "Stun, removal, drain, or other control-family effects are present in the accepted bundle.",
        "tag_ids": tuple(sorted(CONTROL_TAGS)),
        "effect_families": ("control",),
    },
    {
        "role_hint": "sustain",
        "label": "Sustain",
        "description": "Healing, protection, or damage-reduction tags are present in the accepted bundle.",
        "tag_ids": tuple(sorted(SUSTAIN_TAGS)),
        "effect_families": ("defense", "sustain"),
    },
    {
        "role_hint": "setup",
        "label": "Setup",
        "description": "Conditional or combo-gated effects indicate setup-dependent play patterns.",
        "tag_ids": tuple(sorted(SETUP_TAGS)),
        "effect_families": ("setup",),
    },
    {
        "role_hint": "resource",
        "label": "Resource",
        "description": "Gain, drain, or removal tags indicate resource or denial pressure.",
        "tag_ids": tuple(sorted(RESOURCE_TAGS)),
        "effect_families": ("resource",),
    },
    {
        "role_hint": "protection",
        "label": "Protection",
        "description": "Protection-focused tags suggest the character can help stabilize allied turns.",
        "tag_ids": tuple(sorted(PROTECTION_TAGS)),
        "effect_families": ("defense",),
    },
)

IDENTITY_TOKEN_RE = re.compile(r"[a-z0-9]+")


def require_file(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ValueError(f"Expected {expected} at {path}")


def load_json(path: Path, expected: str) -> Any:
    require_file(path, expected)
    return json.loads(path.read_text(encoding="utf-8"))


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected {label} to be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Expected {label} to be a list")
    return value


def normalize_identity_token(value: str) -> str:
    return "".join(IDENTITY_TOKEN_RE.findall(value.lower()))


def tokenize_identity(value: str) -> set[str]:
    return set(IDENTITY_TOKEN_RE.findall(value.lower()))


def normalize_rank_label(value: Any) -> str | None:
    raw_value = value
    if isinstance(value, dict):
        raw_value = value.get("label") or value.get("raw_text")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    return RANK_BAND_ALIASES.get(normalize_identity_token(raw_value))


def rank_band_index(label: str | None) -> int | None:
    if label is None:
        return None
    return RANK_BAND_INDEX.get(label)


def build_character_unlocks_by_id(missions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    unlocks_by_id: dict[str, dict[str, Any]] = {}

    for mission in missions:
        mission_obj = require_object(mission, "mission record")
        mission_id = mission_obj.get("id")
        mission_name = mission_obj.get("name")
        if not isinstance(mission_id, str) or not isinstance(mission_name, str):
            continue

        rank_label = normalize_rank_label(mission_obj.get("rank_requirement"))
        rank_index = rank_band_index(rank_label)
        level_requirement = mission_obj.get("level_requirement")
        if not isinstance(level_requirement, int):
            level_requirement = None

        for reward in require_list(mission_obj.get("rewards", []), f"rewards for {mission_id}"):
            reward_obj = require_object(reward, f"reward for {mission_id}")
            if reward_obj.get("reward_type") != "character_unlock":
                continue
            character_id = reward_obj.get("character_id")
            if not isinstance(character_id, str) or not character_id.strip():
                continue

            reward_confidence = reward_obj.get("confidence")
            rank_requirement = mission_obj.get("rank_requirement")
            rank_confidence = rank_requirement.get("confidence") if isinstance(rank_requirement, dict) else None
            confidence_values = [
                value
                for value in (reward_confidence, rank_confidence)
                if isinstance(value, (int, float))
            ]
            confidence = min(confidence_values) if confidence_values else None
            ambiguity_flags = []
            if isinstance(rank_requirement, dict) and isinstance(rank_requirement.get("ambiguity_flags"), list):
                ambiguity_flags.extend(rank_requirement["ambiguity_flags"])
            if isinstance(reward_obj.get("ambiguity_flags"), list):
                ambiguity_flags.extend(reward_obj["ambiguity_flags"])

            entry = {
                "source": "mission_reward",
                "minimum_rank_label": rank_label,
                "minimum_rank_index": rank_index,
                "minimum_level": level_requirement,
                "unlock_mission_id": mission_id,
                "unlock_mission_name": mission_name,
                "reward_raw_text": reward_obj.get("raw_text"),
                "confidence": confidence,
                "ambiguity_flags": ambiguity_flags,
                "source_ref_ids": [
                    source_ref_id
                    for source_ref_id in mission_obj.get("source_ref_ids", [])
                    if isinstance(source_ref_id, str)
                ],
            }

            current = unlocks_by_id.get(character_id)
            current_key = (
                current.get("minimum_rank_index") if isinstance(current, dict) else None,
                current.get("minimum_level") if isinstance(current, dict) else None,
                current.get("unlock_mission_name") if isinstance(current, dict) else None,
            )
            entry_key = (rank_index, level_requirement, mission_name)
            if current is None or (
                entry_key[0] is not None
                and (current_key[0] is None or entry_key < current_key)
            ):
                unlocks_by_id[character_id] = entry

    return unlocks_by_id


def build_progression_profile(record: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    record_id = record["id"]
    availability = record.get("availability")
    availability_unlock_state = availability.get("unlock_state") if isinstance(availability, dict) else None
    unlock_entry = context["character_unlocks_by_id"].get(record_id)

    if isinstance(unlock_entry, dict):
        source_ref_ids = [ref for ref in unlock_entry.get("source_ref_ids", []) if isinstance(ref, str)]
        return {
            "source": "mission_reward",
            "classification": "mission_reward_unlock",
            "availability_unlock_state": availability_unlock_state,
            "minimum_rank_label": unlock_entry.get("minimum_rank_label"),
            "minimum_rank_index": unlock_entry.get("minimum_rank_index"),
            "minimum_level": unlock_entry.get("minimum_level"),
            "unlock_mission_id": unlock_entry.get("unlock_mission_id"),
            "unlock_mission_name": unlock_entry.get("unlock_mission_name"),
            "reward_raw_text": unlock_entry.get("reward_raw_text"),
            "confidence": unlock_entry.get("confidence"),
            "ambiguity_flags": unlock_entry.get("ambiguity_flags", []),
            "source_ref_ids": source_ref_ids,
            "source_refs": resolve_source_refs(source_ref_ids, context),
        }

    return {
        "source": "mission_rewards_absent",
        "classification": "base_or_unlisted_mission_reward",
        "availability_unlock_state": availability_unlock_state,
        "minimum_rank_label": None,
        "minimum_rank_index": -1,
        "minimum_level": None,
        "unlock_mission_id": None,
        "unlock_mission_name": None,
        "reward_raw_text": None,
        "confidence": None,
        "ambiguity_flags": [
            {
                "code": "character_not_listed_as_mission_reward",
                "field": "progression",
                "detail": "No accepted mission reward unlocks this character, so mission planning treats the character as part of the base or pre-mission roster.",
                "severity": "info",
            }
        ],
        "source_ref_ids": [],
        "source_refs": [],
    }


def character_within_rank_ceiling(
    summary: dict[str, Any],
    ceiling_rank_label: str,
    *,
    include_unknown_unlock_rank: bool = False,
) -> bool:
    ceiling_index = rank_band_index(ceiling_rank_label)
    if ceiling_index is None:
        return include_unknown_unlock_rank

    progression = summary.get("progression")
    if not isinstance(progression, dict):
        return include_unknown_unlock_rank
    minimum_rank_index = progression.get("minimum_rank_index")
    if not isinstance(minimum_rank_index, int):
        return include_unknown_unlock_rank
    return minimum_rank_index <= ceiling_index


def load_reference_context(references_dir: Path = DEFAULT_REFERENCES_DIR) -> dict[str, Any]:
    characters_payload = require_object(
        load_json(references_dir / "characters.json", "skill-local characters.json"),
        "characters.json",
    )
    missions_payload = require_object(
        load_json(references_dir / "missions.json", "skill-local missions.json"),
        "missions.json",
    )
    tags_payload = require_object(
        load_json(references_dir / "tags.json", "skill-local tags.json"),
        "tags.json",
    )
    effect_taxonomy_payload = require_object(
        load_json(references_dir / "effect-taxonomy.json", "skill-local effect-taxonomy.json"),
        "effect-taxonomy.json",
    )
    source_map_payload = require_object(
        load_json(references_dir / "source-map.json", "skill-local source-map.json"),
        "source-map.json",
    )

    characters = require_list(characters_payload.get("records"), "characters.json records")
    missions = require_list(missions_payload.get("records"), "missions.json records")

    tag_catalog = require_object(tags_payload.get("tag_catalog"), "tags.json tag_catalog")
    character_tag_catalog = require_list(tag_catalog.get("character"), "tags.json tag_catalog.character")
    tag_meta_by_id = {}
    for item in character_tag_catalog:
        item_obj = require_object(item, "character tag catalog entry")
        tag_id = item_obj.get("tag_id")
        if not isinstance(tag_id, str) or not tag_id.strip():
            raise ValueError("Character tag catalog entry is missing tag_id")
        tag_meta_by_id[tag_id] = item_obj

    character_tag_rows = require_list(tags_payload.get("character_tags"), "tags.json character_tags")
    character_tag_rows_by_id = {}
    for row in character_tag_rows:
        row_obj = require_object(row, "character tag row")
        record_id = row_obj.get("record_id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("Character tag row is missing record_id")
        character_tag_rows_by_id[record_id] = row_obj

    effect_families = require_list(effect_taxonomy_payload.get("effect_families"), "effect-taxonomy effect_families")
    effect_types = require_list(effect_taxonomy_payload.get("effect_types"), "effect-taxonomy effect_types")
    skill_classes = require_list(effect_taxonomy_payload.get("skill_classes"), "effect-taxonomy skill_classes")

    effect_family_meta_by_id = {}
    for item in effect_families:
        item_obj = require_object(item, "effect family entry")
        family_id = item_obj.get("family_id")
        if not isinstance(family_id, str) or not family_id.strip():
            raise ValueError("Effect family entry is missing family_id")
        effect_family_meta_by_id[family_id] = item_obj

    effect_type_meta_by_id = {}
    effect_family_by_type = {}
    for item in effect_types:
        item_obj = require_object(item, "effect type entry")
        effect_type = item_obj.get("effect_type")
        family_id = item_obj.get("family_id")
        if not isinstance(effect_type, str) or not effect_type.strip():
            raise ValueError("Effect type entry is missing effect_type")
        if not isinstance(family_id, str) or not family_id.strip():
            raise ValueError(f"Effect type entry {effect_type} is missing family_id")
        effect_type_meta_by_id[effect_type] = item_obj
        effect_family_by_type[effect_type] = family_id

    skill_class_meta_by_id = {}
    for item in skill_classes:
        item_obj = require_object(item, "skill class entry")
        class_id = item_obj.get("class_id")
        if not isinstance(class_id, str) or not class_id.strip():
            raise ValueError("Skill class entry is missing class_id")
        skill_class_meta_by_id[class_id] = item_obj

    source_refs_by_id = require_object(source_map_payload.get("source_refs_by_id"), "source-map source_refs_by_id")
    record_index = require_object(source_map_payload.get("record_index"), "source-map record_index")

    return {
        "references_dir": references_dir,
        "characters": characters,
        "missions": missions,
        "character_unlocks_by_id": build_character_unlocks_by_id(missions),
        "tag_meta_by_id": tag_meta_by_id,
        "character_tag_rows_by_id": character_tag_rows_by_id,
        "effect_family_meta_by_id": effect_family_meta_by_id,
        "effect_type_meta_by_id": effect_type_meta_by_id,
        "effect_family_by_type": effect_family_by_type,
        "skill_class_meta_by_id": skill_class_meta_by_id,
        "source_refs_by_id": source_refs_by_id,
        "record_index": record_index,
    }


def resolve_source_refs(source_ref_ids: list[str], context: dict[str, Any]) -> list[dict[str, Any]]:
    resolved = []
    for source_ref_id in source_ref_ids:
        source_ref = context["source_refs_by_id"].get(source_ref_id)
        if not isinstance(source_ref, dict):
            resolved.append({"source_id": source_ref_id, "missing": True})
            continue
        resolved.append(
            {
                "source_id": source_ref.get("source_id"),
                "url": source_ref.get("url"),
                "section": source_ref.get("section"),
                "snapshot_path": source_ref.get("snapshot_path"),
                "version_label": source_ref.get("version_label"),
            }
        )
    return resolved


def build_tag_details(record: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    row = context["character_tag_rows_by_id"].get(record["id"])
    if not isinstance(row, dict):
        return []

    tag_details = []
    for item in require_list(row.get("tags", []), f"tags for {record['id']}"):
        tag_obj = require_object(item, f"tag entry for {record['id']}")
        tag_id = tag_obj.get("tag_id")
        if not isinstance(tag_id, str) or not tag_id.strip():
            raise ValueError(f"Tag entry for {record['id']} is missing tag_id")
        tag_meta = context["tag_meta_by_id"].get(tag_id, {})
        tag_details.append(
            {
                "tag_id": tag_id,
                "label": tag_meta.get("label", tag_id),
                "category": tag_meta.get("category", "unknown"),
                "definition": tag_meta.get("definition"),
                "evidence_count": tag_obj.get("evidence_count", 0),
            }
        )
    return sorted(tag_details, key=lambda item: (item["category"], item["label"], item["tag_id"]))


def build_skill_summaries(record: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    skills = require_list(record.get("skills"), f"skills for {record['id']}")
    summaries = []

    for skill in skills:
        skill_obj = require_object(skill, f"skill for {record['id']}")
        skill_id = skill_obj.get("skill_id")
        skill_name = skill_obj.get("name")
        if not isinstance(skill_id, str) or not skill_id.strip():
            raise ValueError(f"Skill under {record['id']} is missing skill_id")
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError(f"Skill {skill_id} under {record['id']} is missing name")

        cost_obj = require_object(skill_obj.get("cost"), f"cost for {skill_id}")
        cooldown_obj = require_object(skill_obj.get("cooldown"), f"cooldown for {skill_id}")
        effect_objects = require_list(skill_obj.get("effects"), f"effects for {skill_id}")
        class_objects = require_list(skill_obj.get("classes"), f"classes for {skill_id}")

        cost_components = []
        chakra_types = []
        for component in require_list(cost_obj.get("components"), f"cost components for {skill_id}"):
            component_obj = require_object(component, f"cost component for {skill_id}")
            chakra_type = component_obj.get("chakra_type")
            amount = component_obj.get("amount")
            if not isinstance(chakra_type, str) or not chakra_type.strip():
                raise ValueError(f"Cost component for {skill_id} is missing chakra_type")
            if not isinstance(amount, int) or amount < 0:
                raise ValueError(f"Cost component for {skill_id} has invalid amount")
            cost_components.append({"chakra_type": chakra_type, "amount": amount, "raw_text": component_obj.get("raw_text")})
            chakra_types.append(chakra_type)

        effect_type_counts: Counter[str] = Counter()
        effect_family_counts: Counter[str] = Counter()
        for effect in effect_objects:
            effect_obj = require_object(effect, f"effect under {skill_id}")
            effect_type = effect_obj.get("effect_type")
            if not isinstance(effect_type, str) or not effect_type.strip():
                raise ValueError(f"Effect under {skill_id} is missing effect_type")
            effect_type_counts[effect_type] += 1
            family_id = context["effect_family_by_type"].get(effect_type)
            if family_id is not None:
                effect_family_counts[family_id] += 1

        class_ids = []
        for class_item in class_objects:
            class_obj = require_object(class_item, f"class entry under {skill_id}")
            class_id = class_obj.get("class_id")
            if not isinstance(class_id, str) or not class_id.strip():
                raise ValueError(f"Class entry under {skill_id} is missing class_id")
            class_ids.append(class_id)

        skill_source_refs = [ref for ref in skill_obj.get("source_ref_ids", []) if isinstance(ref, str)]
        summaries.append(
            {
                "skill_id": skill_id,
                "skill_name": skill_name,
                "slot": skill_obj.get("slot"),
                "cost_total": cost_obj.get("total", 0),
                "cost_components": cost_components,
                "chakra_types": sorted(set(chakra_types)),
                "cooldown_turns": cooldown_obj.get("turns"),
                "classes": [
                    {
                        "class_id": class_id,
                        "label": context["skill_class_meta_by_id"].get(class_id, {}).get("label", class_id),
                    }
                    for class_id in sorted(set(class_ids))
                ],
                "effect_types": [
                    {
                        "effect_type": effect_type,
                        "label": context["effect_type_meta_by_id"].get(effect_type, {}).get("label", effect_type),
                        "family_id": context["effect_family_by_type"].get(effect_type),
                        "count": count,
                    }
                    for effect_type, count in sorted(effect_type_counts.items(), key=lambda item: (-item[1], item[0]))
                ],
                "effect_families": [
                    {
                        "family_id": family_id,
                        "label": context["effect_family_meta_by_id"].get(family_id, {}).get("label", family_id),
                        "count": count,
                    }
                    for family_id, count in sorted(effect_family_counts.items(), key=lambda item: (-item[1], item[0]))
                ],
                "source_ref_ids": skill_source_refs,
                "source_refs": resolve_source_refs(skill_source_refs, context),
                "parse_confidence": require_object(skill_obj.get("parse"), f"parse for {skill_id}").get("confidence"),
            }
        )

    return summaries


def build_chakra_profile(skill_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    component_totals: Counter[str] = Counter()
    skill_usage_counts: Counter[str] = Counter()
    skills_by_type: dict[str, list[str]] = defaultdict(list)
    low_cost_skills = []
    expensive_skills = []

    for skill in skill_summaries:
        cost_total = skill.get("cost_total")
        if not isinstance(cost_total, int) or cost_total <= 0:
            continue

        chakra_types_seen = set()
        for component in skill["cost_components"]:
            chakra_type = component["chakra_type"]
            amount = component["amount"]
            component_totals[chakra_type] += amount
            chakra_types_seen.add(chakra_type)
            skills_by_type[chakra_type].append(skill["skill_name"])

        for chakra_type in chakra_types_seen:
            skill_usage_counts[chakra_type] += 1

        skill_entry = {
            "skill_id": skill["skill_id"],
            "skill_name": skill["skill_name"],
            "cost_total": cost_total,
            "chakra_types": skill["chakra_types"],
            "cooldown_turns": skill["cooldown_turns"],
        }
        if cost_total <= 1:
            low_cost_skills.append(skill_entry)
        if cost_total >= 3:
            expensive_skills.append(skill_entry)

    component_totals_by_type = {chakra_type: component_totals.get(chakra_type, 0) for chakra_type in CHAKRA_TYPES}
    skill_usage_counts_by_type = {chakra_type: skill_usage_counts.get(chakra_type, 0) for chakra_type in CHAKRA_TYPES}
    top_types = [
        chakra_type
        for chakra_type, amount in sorted(component_totals.items(), key=lambda item: (-item[1], item[0]))
        if amount > 0
    ]

    return {
        "component_totals": component_totals_by_type,
        "skill_usage_counts": skill_usage_counts_by_type,
        "skills_by_type": {
            chakra_type: sorted(set(skill_names))
            for chakra_type, skill_names in sorted(skills_by_type.items())
        },
        "top_types": top_types,
        "low_cost_skills": sorted(low_cost_skills, key=lambda item: (item["cost_total"], item["skill_name"])),
        "expensive_skills": sorted(expensive_skills, key=lambda item: (-item["cost_total"], item["skill_name"])),
    }


def derive_role_hint_details(tag_ids: list[str], effect_family_ids: list[str]) -> list[dict[str, Any]]:
    tag_id_set = set(tag_ids)
    effect_family_set = set(effect_family_ids)
    details = []

    for rule in ROLE_HINT_RULES:
        matched_tags = sorted(tag_id_set.intersection(rule["tag_ids"]))
        matched_effect_families = sorted(effect_family_set.intersection(rule["effect_families"]))
        if not matched_tags and not matched_effect_families:
            continue
        details.append(
            {
                "role_hint": rule["role_hint"],
                "label": rule["label"],
                "description": rule["description"],
                "trigger_tag_ids": matched_tags,
                "trigger_effect_families": matched_effect_families,
            }
        )

    return details


def build_character_summary(record: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    record_id = record.get("id")
    record_name = record.get("name")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("Character record is missing id")
    if not isinstance(record_name, str) or not record_name.strip():
        raise ValueError(f"Character record {record_id} is missing name")

    parse_obj = require_object(record.get("parse"), f"parse for {record_id}")
    skill_summaries = build_skill_summaries(record, context)
    chakra_profile = build_chakra_profile(skill_summaries)
    tag_details = build_tag_details(record, context)
    tag_ids = [item["tag_id"] for item in tag_details]

    effect_type_counts: Counter[str] = Counter()
    effect_family_counts: Counter[str] = Counter()
    skill_class_ids = set()
    for skill in skill_summaries:
        for effect_type in skill["effect_types"]:
            effect_type_counts[effect_type["effect_type"]] += effect_type["count"]
        for effect_family in skill["effect_families"]:
            effect_family_counts[effect_family["family_id"]] += effect_family["count"]
        for class_item in skill["classes"]:
            skill_class_ids.add(class_item["class_id"])

    effect_types = [
        {
            "effect_type": effect_type,
            "label": context["effect_type_meta_by_id"].get(effect_type, {}).get("label", effect_type),
            "family_id": context["effect_family_by_type"].get(effect_type),
            "count": count,
        }
        for effect_type, count in sorted(effect_type_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    effect_families = [
        {
            "family_id": family_id,
            "label": context["effect_family_meta_by_id"].get(family_id, {}).get("label", family_id),
            "count": count,
        }
        for family_id, count in sorted(effect_family_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    skill_classes = [
        {
            "class_id": class_id,
            "label": context["skill_class_meta_by_id"].get(class_id, {}).get("label", class_id),
        }
        for class_id in sorted(skill_class_ids)
    ]

    role_hint_details = derive_role_hint_details(tag_ids, [item["family_id"] for item in effect_families])
    record_source_ref_ids = [ref for ref in record.get("source_ref_ids", []) if isinstance(ref, str)]
    record_sources = resolve_source_refs(record_source_ref_ids, context)

    slug = record_id.split(":", 1)[1] if ":" in record_id else record_id
    identity_fields = [
        {"field": "name", "value": record_name},
        {"field": "id", "value": record_id},
        {"field": "slug", "value": slug},
        {"field": "slug_words", "value": slug.replace("-", " ")},
    ]

    return {
        "id": record_id,
        "name": record_name,
        "description": record.get("description"),
        "tag_ids": tag_ids,
        "tags": tag_details,
        "effect_type_ids": [item["effect_type"] for item in effect_types],
        "effect_types": effect_types,
        "effect_family_ids": [item["family_id"] for item in effect_families],
        "effect_families": effect_families,
        "skill_class_ids": [item["class_id"] for item in skill_classes],
        "skill_classes": skill_classes,
        "chakra_profile": chakra_profile,
        "role_hints": [item["role_hint"] for item in role_hint_details],
        "role_hint_details": role_hint_details,
        "progression": build_progression_profile(record, context),
        "data_quality": {
            "tag_ids": [tag_id for tag_id in record.get("data_quality_tag_ids", []) if isinstance(tag_id, str)],
            "warnings": [item for item in tag_details if item["category"] == "data_quality"],
            "parse_confidence": parse_obj.get("confidence"),
            "ambiguity_flag_count": len(require_list(parse_obj.get("ambiguity_flags"), f"ambiguity_flags for {record_id}")),
        },
        "record_source_ref_ids": record_source_ref_ids,
        "record_sources": record_sources,
        "skill_summaries": skill_summaries,
        "_identity_fields": identity_fields,
    }


def build_character_summaries(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [build_character_summary(require_object(record, "character record"), context) for record in context["characters"]]


def classify_query_match(summary: dict[str, Any], query: str) -> dict[str, Any] | None:
    if not query.strip():
        return {"kind": "unfiltered", "field": None, "value": None, "rank": 99}

    normalized_query = normalize_identity_token(query)
    if not normalized_query:
        return None

    query_tokens = tokenize_identity(query)
    best_match = None

    for candidate in summary["_identity_fields"]:
        value = candidate["value"]
        normalized_value = normalize_identity_token(value)
        if not normalized_value:
            continue

        if normalized_query == normalized_value:
            current = {"kind": "exact", "field": candidate["field"], "value": value, "rank": 0}
        elif normalized_value.startswith(normalized_query):
            current = {"kind": "prefix", "field": candidate["field"], "value": value, "rank": 1}
        elif query_tokens and query_tokens.issubset(tokenize_identity(value)):
            current = {"kind": "token_subset", "field": candidate["field"], "value": value, "rank": 2}
        elif normalized_query in normalized_value:
            current = {"kind": "contains", "field": candidate["field"], "value": value, "rank": 3}
        else:
            continue

        if best_match is None or current["rank"] < best_match["rank"]:
            best_match = current

    return best_match


def summary_matches_filters(
    summary: dict[str, Any],
    *,
    tag_ids: list[str],
    effect_types: list[str],
    effect_families: list[str],
    skill_classes: list[str],
    chakra_types: list[str],
    exclude_chakra_types: list[str],
    role_hints: list[str],
    max_unlock_rank: str | None,
    include_unknown_unlock_rank: bool,
) -> bool:
    if tag_ids and not set(tag_ids).issubset(summary["tag_ids"]):
        return False
    if effect_types and not set(effect_types).issubset(summary["effect_type_ids"]):
        return False
    if effect_families and not set(effect_families).issubset(summary["effect_family_ids"]):
        return False
    if skill_classes and not set(skill_classes).issubset(summary["skill_class_ids"]):
        return False
    available_chakra_types = {chakra_type for chakra_type, amount in summary["chakra_profile"]["component_totals"].items() if amount > 0}
    if chakra_types and not set(chakra_types).issubset(available_chakra_types):
        return False
    if exclude_chakra_types and set(exclude_chakra_types).intersection(available_chakra_types):
        return False
    if role_hints and not set(role_hints).issubset(summary["role_hints"]):
        return False
    if max_unlock_rank is not None and not character_within_rank_ceiling(
        summary,
        max_unlock_rank,
        include_unknown_unlock_rank=include_unknown_unlock_rank,
    ):
        return False
    return True


def collect_search_matches(
    summaries: list[dict[str, Any]],
    *,
    query: str,
    tag_ids: list[str],
    effect_types: list[str],
    effect_families: list[str],
    skill_classes: list[str],
    chakra_types: list[str],
    exclude_chakra_types: list[str],
    role_hints: list[str],
    max_unlock_rank: str | None = None,
    include_unknown_unlock_rank: bool = False,
) -> list[dict[str, Any]]:
    matches = []

    for summary in summaries:
        query_match = classify_query_match(summary, query)
        if query.strip() and query_match is None:
            continue
        if not summary_matches_filters(
            summary,
            tag_ids=tag_ids,
            effect_types=effect_types,
            effect_families=effect_families,
            skill_classes=skill_classes,
            chakra_types=chakra_types,
            exclude_chakra_types=exclude_chakra_types,
            role_hints=role_hints,
            max_unlock_rank=max_unlock_rank,
            include_unknown_unlock_rank=include_unknown_unlock_rank,
        ):
            continue
        matches.append({"summary": summary, "query_match": query_match})

    matches.sort(
        key=lambda item: (
            item["query_match"]["rank"] if item["query_match"] is not None else 99,
            item["summary"]["name"].lower(),
            item["summary"]["id"],
        )
    )
    return matches


def build_search_result_entry(summary: dict[str, Any], query_match: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "id": summary["id"],
        "name": summary["name"],
        "query_match": None
        if query_match is None or query_match["kind"] == "unfiltered"
        else {
            "kind": query_match["kind"],
            "field": query_match["field"],
            "matched_value": query_match["value"],
        },
        "role_hints": summary["role_hint_details"],
        "tags": summary["tags"],
        "effect_types": summary["effect_types"],
        "effect_families": summary["effect_families"],
        "skill_classes": summary["skill_classes"],
        "progression": summary["progression"],
        "chakra_profile": {
            "component_totals": summary["chakra_profile"]["component_totals"],
            "skill_usage_counts": summary["chakra_profile"]["skill_usage_counts"],
            "top_types": summary["chakra_profile"]["top_types"],
            "low_cost_skills": summary["chakra_profile"]["low_cost_skills"],
            "expensive_skills": summary["chakra_profile"]["expensive_skills"],
        },
        "data_quality": summary["data_quality"],
        "provenance": {
            "record_source_ref_ids": summary["record_source_ref_ids"],
            "record_sources": summary["record_sources"],
        },
    }


def resolve_character_query(query: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = collect_search_matches(
        summaries,
        query=query,
        tag_ids=[],
        effect_types=[],
        effect_families=[],
        skill_classes=[],
        chakra_types=[],
        exclude_chakra_types=[],
        role_hints=[],
        max_unlock_rank=None,
        include_unknown_unlock_rank=False,
    )

    if not matches:
        return {"status": "not_found", "query": query, "candidates": []}

    exact_matches = [item for item in matches if item["query_match"] is not None and item["query_match"]["kind"] == "exact"]
    if len(exact_matches) == 1:
        return {
            "status": "resolved",
            "query": query,
            "query_match": exact_matches[0]["query_match"],
            "character": exact_matches[0]["summary"],
        }
    if len(exact_matches) > 1:
        return {
            "status": "ambiguous",
            "query": query,
            "candidates": [build_search_result_entry(item["summary"], item["query_match"]) for item in exact_matches[:5]],
        }
    if len(matches) == 1:
        return {
            "status": "resolved",
            "query": query,
            "query_match": matches[0]["query_match"],
            "character": matches[0]["summary"],
        }
    return {
        "status": "ambiguous",
        "query": query,
        "candidates": [build_search_result_entry(item["summary"], item["query_match"]) for item in matches[:5]],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search the validated skill-local Naruto Arena character bundle by name/id and transparent metadata "
            "such as tags, effect families, skill classes, chakra demand, and derived role hints."
        )
    )
    parser.add_argument("query", nargs="?", default="", help="Optional name/id query. Uses exact, prefix, token, then contains matching.")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Require a character tag_id from skills/naruto-arena-team-builder/references/tags.json. May be passed multiple times.",
    )
    parser.add_argument(
        "--effect-type",
        action="append",
        default=[],
        help="Require an effect_type present in the character's structured skills. May be passed multiple times.",
    )
    parser.add_argument(
        "--effect-family",
        action="append",
        default=[],
        help="Require an effect family_id from effect-taxonomy.json. May be passed multiple times.",
    )
    parser.add_argument(
        "--skill-class",
        action="append",
        default=[],
        help="Require a captured skill class_id such as physical, chakra, instant, mental, or ranged. May be passed multiple times.",
    )
    parser.add_argument(
        "--chakra-type",
        action="append",
        default=[],
        help="Require observed chakra demand of the given type (tai, nin, gen, bloodline, random). May be passed multiple times.",
    )
    parser.add_argument(
        "--exclude-chakra-type",
        action="append",
        default=[],
        help="Exclude characters that spend the given chakra type anywhere in their structured costs. May be passed multiple times.",
    )
    parser.add_argument(
        "--role-hint",
        action="append",
        default=[],
        help="Require a derived role hint: pressure, control, sustain, setup, resource, or protection. May be passed multiple times.",
    )
    parser.add_argument(
        "--max-unlock-rank",
        help=(
            "Conservatively require the derived mission-reward unlock rank to be at or below this mission rank band. "
            "Accepted aliases include Genin, Chunin/Chuunin, Missing-Nin, Anbu, Jounin, Sannin, and Jinchuuriki."
        ),
    )
    parser.add_argument(
        "--include-unknown-unlock-rank",
        action="store_true",
        help="Allow records whose derived mission-reward unlock rank is unavailable when --max-unlock-rank is used.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to return. Default: 10.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than 0")
    max_unlock_rank = normalize_rank_label(args.max_unlock_rank) if args.max_unlock_rank else None
    if args.max_unlock_rank and max_unlock_rank is None:
        raise SystemExit(f"Unknown --max-unlock-rank value: {args.max_unlock_rank}")

    context = load_reference_context()
    summaries = build_character_summaries(context)
    matches = collect_search_matches(
        summaries,
        query=args.query,
        tag_ids=args.tag,
        effect_types=args.effect_type,
        effect_families=args.effect_family,
        skill_classes=args.skill_class,
        chakra_types=args.chakra_type,
        exclude_chakra_types=args.exclude_chakra_type,
        role_hints=args.role_hint,
        max_unlock_rank=max_unlock_rank,
        include_unknown_unlock_rank=args.include_unknown_unlock_rank,
    )

    payload = {
        "references_dir": str(context["references_dir"]),
        "query": args.query,
        "filters": {
            "tag_ids": args.tag,
            "effect_types": args.effect_type,
            "effect_families": args.effect_family,
            "skill_classes": args.skill_class,
            "chakra_types": args.chakra_type,
            "exclude_chakra_types": args.exclude_chakra_type,
            "role_hints": args.role_hint,
            "max_unlock_rank": max_unlock_rank,
            "include_unknown_unlock_rank": args.include_unknown_unlock_rank,
        },
        "total_matches": len(matches),
        "displayed_count": min(len(matches), args.limit),
        "results": [
            build_search_result_entry(item["summary"], item["query_match"])
            for item in matches[: args.limit]
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

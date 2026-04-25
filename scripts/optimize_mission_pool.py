#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from search_characters import (
    DEFAULT_REFERENCES_DIR,
    RANK_BAND_SEQUENCE,
    build_character_summaries,
    character_within_rank_ceiling,
    load_json,
    load_reference_context,
    normalize_identity_token,
    normalize_rank_label,
    rank_band_index,
    require_list,
    require_object,
    resolve_source_refs,
    tokenize_identity,
)
from team_candidate_report import (
    build_data_quality_warnings,
    build_provenance_hooks,
    build_role_matrix,
    build_strength_notes,
    build_substitution_hooks,
    build_team_chakra_report,
    build_team_identity_hints,
    build_weakness_notes,
)


IDENTITY_FIELDS = ("name", "id", "slug", "slug_words")
OR_CONDITION_RE = re.compile(r"\bor\b", re.IGNORECASE)
SAME_TEAM_RE = re.compile(r"\bsame\s+team\b", re.IGNORECASE)
SKILL_ID_RE = re.compile(r"^skill:([^:]+):")


def load_planning_context(references_dir: Path) -> dict[str, Any]:
    helper_context = load_reference_context(references_dir)
    missions_payload = require_object(
        load_json(references_dir / "missions.json", "skill-local missions.json"),
        "missions.json",
    )
    tags_payload = require_object(
        load_json(references_dir / "tags.json", "skill-local tags.json"),
        "tags.json",
    )
    missions = require_list(missions_payload.get("records"), "missions.json records")
    tag_catalog = require_object(tags_payload.get("tag_catalog"), "tags.json tag_catalog")
    mission_tag_catalog = require_list(tag_catalog.get("mission"), "tags.json tag_catalog.mission")

    mission_tag_meta_by_id = {}
    for item in mission_tag_catalog:
        item_obj = require_object(item, "mission tag catalog entry")
        tag_id = item_obj.get("tag_id")
        if not isinstance(tag_id, str) or not tag_id.strip():
            raise ValueError("Mission tag catalog entry is missing tag_id")
        mission_tag_meta_by_id[tag_id] = item_obj

    mission_tag_rows_by_id = {}
    for row in require_list(tags_payload.get("mission_tags"), "tags.json mission_tags"):
        row_obj = require_object(row, "mission tag row")
        record_id = row_obj.get("record_id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("Mission tag row is missing record_id")
        mission_tag_rows_by_id[record_id] = row_obj

    character_summaries = build_character_summaries(helper_context)
    characters_by_id = {summary["id"]: summary for summary in character_summaries}

    return {
        **helper_context,
        "references_dir": references_dir,
        "missions": missions,
        "mission_tag_meta_by_id": mission_tag_meta_by_id,
        "mission_tag_rows_by_id": mission_tag_rows_by_id,
        "character_summaries": character_summaries,
        "characters_by_id": characters_by_id,
    }


def mission_identity_fields(record: dict[str, Any]) -> list[dict[str, str]]:
    record_id = record.get("id", "")
    name = record.get("name", "")
    slug = record_id.split(":", 1)[1] if ":" in record_id else record_id
    return [
        {"field": "name", "value": name},
        {"field": "id", "value": record_id},
        {"field": "slug", "value": slug},
        {"field": "slug_words", "value": slug.replace("-", " ")},
    ]


def classify_query_match(record: dict[str, Any], query: str) -> dict[str, Any] | None:
    normalized_query = normalize_identity_token(query)
    if not normalized_query:
        return None

    query_tokens = tokenize_identity(query)
    best_match = None
    for candidate in mission_identity_fields(record):
        value = candidate["value"]
        normalized_value = normalize_identity_token(value)
        if not normalized_value:
            continue

        if normalized_query == normalized_value:
            current = {"kind": "exact", "field": candidate["field"], "matched_value": value, "rank": 0}
        elif normalized_value.startswith(normalized_query):
            current = {"kind": "prefix", "field": candidate["field"], "matched_value": value, "rank": 1}
        elif query_tokens and query_tokens.issubset(tokenize_identity(value)):
            current = {"kind": "token_subset", "field": candidate["field"], "matched_value": value, "rank": 2}
        elif normalized_query in normalized_value:
            current = {"kind": "contains", "field": candidate["field"], "matched_value": value, "rank": 3}
        else:
            continue

        if best_match is None or current["rank"] < best_match["rank"]:
            best_match = current

    return best_match


def resolve_mission_query(query: str, missions: list[dict[str, Any]]) -> dict[str, Any]:
    matches = []
    for record in missions:
        record_obj = require_object(record, "mission record")
        query_match = classify_query_match(record_obj, query)
        if query_match is None:
            continue
        matches.append({"record": record_obj, "query_match": query_match})

    matches.sort(
        key=lambda item: (
            item["query_match"]["rank"],
            item["record"].get("name", "").lower(),
            item["record"].get("id", ""),
        )
    )

    if not matches:
        return {"status": "not_found", "query": query, "candidates": []}

    exact_matches = [item for item in matches if item["query_match"]["kind"] == "exact"]
    if len(exact_matches) == 1:
        return {
            "status": "resolved",
            "query": query,
            "query_match": strip_query_rank(exact_matches[0]["query_match"]),
            "mission": exact_matches[0]["record"],
        }
    if len(exact_matches) > 1:
        return {
            "status": "ambiguous",
            "query": query,
            "candidates": [mission_candidate_entry(item) for item in exact_matches[:8]],
        }
    if len(matches) == 1:
        return {
            "status": "resolved",
            "query": query,
            "query_match": strip_query_rank(matches[0]["query_match"]),
            "mission": matches[0]["record"],
        }
    return {
        "status": "ambiguous",
        "query": query,
        "candidates": [mission_candidate_entry(item) for item in matches[:8]],
    }


def strip_query_rank(query_match: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": query_match["kind"],
        "field": query_match["field"],
        "matched_value": query_match["matched_value"],
    }


def mission_candidate_entry(item: dict[str, Any]) -> dict[str, Any]:
    record = item["record"]
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "section_name": record.get("section_name"),
        "query_match": strip_query_rank(item["query_match"]),
    }


def mission_tag_details(record: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    row = context["mission_tag_rows_by_id"].get(record["id"])
    if not isinstance(row, dict):
        return []

    details = []
    for item in require_list(row.get("tags", []), f"tags for {record['id']}"):
        tag_obj = require_object(item, f"tag entry for {record['id']}")
        tag_id = tag_obj.get("tag_id")
        if not isinstance(tag_id, str) or not tag_id.strip():
            raise ValueError(f"Tag entry for {record['id']} is missing tag_id")
        tag_meta = context["mission_tag_meta_by_id"].get(tag_id, {})
        details.append(
            {
                "tag_id": tag_id,
                "label": tag_meta.get("label", tag_id),
                "category": tag_meta.get("category", "unknown"),
                "definition": tag_meta.get("definition"),
                "evidence_count": tag_obj.get("evidence_count", 0),
                "evidence": tag_obj.get("evidence", [])[:3],
            }
        )
    return sorted(details, key=lambda item: (item["category"], item["label"], item["tag_id"]))


def derive_character_refs_from_skill_refs(skill_refs: list[str]) -> list[str]:
    derived = []
    for skill_ref in skill_refs:
        match = SKILL_ID_RE.match(skill_ref)
        if not match:
            continue
        derived.append(f"character:{match.group(1)}")
    return sorted(set(derived))


def has_ambiguity(requirement: dict[str, Any], code: str) -> bool:
    return any(
        isinstance(flag, dict) and flag.get("code") == code
        for flag in requirement.get("ambiguity_flags", [])
    )


def requirement_character_choice(requirement: dict[str, Any]) -> dict[str, Any] | None:
    character_choice = requirement.get("character_choice")
    if not isinstance(character_choice, dict):
        return None
    if character_choice.get("choice_type") != "alternative_eligible_characters":
        return None
    eligible_refs = character_choice.get("eligible_character_refs")
    if not isinstance(eligible_refs, list) or not all(isinstance(ref, str) for ref in eligible_refs):
        return None
    if len(eligible_refs) < 2:
        return None
    if character_choice.get("progress_counting") != "per_eligible_character_present":
        return None
    return character_choice


def alternative_choice_refs(requirement: dict[str, Any], character_refs: list[str]) -> list[str] | None:
    character_choice = requirement_character_choice(requirement)
    if character_choice is None:
        return None
    character_ref_set = set(character_refs)
    eligible_refs = [
        ref
        for ref in character_choice["eligible_character_refs"]
        if ref in character_ref_set
    ]
    return eligible_refs if len(eligible_refs) >= 2 else None


def build_coverage_options(
    requirement: dict[str, Any],
    character_refs: list[str],
    *,
    team_size: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    condition_text = requirement.get("condition_text") or ""
    interpretation_notes = []
    character_choice = requirement_character_choice(requirement)
    eligible_choice_refs = alternative_choice_refs(requirement, character_refs)

    if eligible_choice_refs:
        interpretation_notes.append(
            "Multiple character refs are modeled as alternative eligible characters; each eligible named character present can contribute one progress unit for a qualifying battle."
        )
        return (
            [
                {
                    "option_id": f"{requirement['requirement_id']}:option:{index:02d}",
                    "required_character_ids": [character_id],
                    "required_skill_ids": sorted(ref for ref in requirement.get("skill_refs", []) if isinstance(ref, str)),
                    "option_kind": "alternative_character",
                    "progress_counting": character_choice["progress_counting"],
                    "eligible_character_ids": eligible_choice_refs,
                    "progress_units_per_character": 1,
                    "max_progress_per_qualifying_battle": character_choice.get("max_progress_per_qualifying_battle"),
                    "team_size_fit": len([character_id]) <= team_size,
                }
                for index, character_id in enumerate(eligible_choice_refs, start=1)
            ],
            interpretation_notes,
        )

    if len(character_refs) > 1 and OR_CONDITION_RE.search(condition_text) and not SAME_TEAM_RE.search(condition_text):
        interpretation_notes.append(
            "Multiple character refs were interpreted as alternatives from legacy condition_text because no structured character_choice was available."
        )
        return (
            [
                {
                    "option_id": f"{requirement['requirement_id']}:option:{index:02d}",
                    "required_character_ids": [character_id],
                    "required_skill_ids": sorted(ref for ref in requirement.get("skill_refs", []) if isinstance(ref, str)),
                    "option_kind": "alternative_character",
                    "progress_counting": "per_requirement",
                    "eligible_character_ids": character_refs,
                    "progress_units_per_character": None,
                    "max_progress_per_qualifying_battle": 1,
                    "team_size_fit": len([character_id]) <= team_size,
                }
                for index, character_id in enumerate(character_refs, start=1)
            ],
            interpretation_notes,
        )

    if len(character_refs) > 1 and SAME_TEAM_RE.search(condition_text):
        interpretation_notes.append("Multiple character refs were kept together because condition_text requires the same team.")
    elif len(character_refs) > 1 and has_ambiguity(requirement, "multi_character_condition_not_structured"):
        interpretation_notes.append(
            "Multiple character refs were kept together; the bundle marks the composite condition as not fully structured."
        )

    return (
        [
            {
                "option_id": f"{requirement['requirement_id']}:option:01",
                "required_character_ids": character_refs,
                "required_skill_ids": sorted(ref for ref in requirement.get("skill_refs", []) if isinstance(ref, str)),
                "option_kind": "all_listed_characters",
                "progress_counting": "per_requirement",
                "eligible_character_ids": character_refs,
                "progress_units_per_character": None,
                "max_progress_per_qualifying_battle": 1,
                "team_size_fit": len(character_refs) <= team_size,
            }
        ],
        interpretation_notes,
    )


def build_requirement_entry(requirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement.get("requirement_id"),
        "step_index": requirement.get("step_index"),
        "requirement_type": requirement.get("requirement_type"),
        "count": requirement.get("count"),
        "condition_text": requirement.get("condition_text"),
        "character_choice": requirement.get("character_choice"),
        "confidence": requirement.get("confidence"),
        "ambiguity_flags": requirement.get("ambiguity_flags", []),
    }


def build_mission_analysis(record: dict[str, Any], context: dict[str, Any], *, team_size: int) -> dict[str, Any]:
    record_id = record.get("id")
    record_name = record.get("name")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("Mission record is missing id")
    if not isinstance(record_name, str) or not record_name.strip():
        raise ValueError(f"Mission record {record_id} is missing name")

    hard_constraints = []
    soft_fit_hints = []
    unknown_requirements = []
    missing_character_refs = set()

    for requirement in require_list(record.get("requirements"), f"requirements for {record_id}"):
        requirement_obj = require_object(requirement, f"requirement for {record_id}")
        base_entry = build_requirement_entry(requirement_obj)
        requirement_type = requirement_obj.get("requirement_type")
        character_refs = sorted(ref for ref in requirement_obj.get("character_refs", []) if isinstance(ref, str))
        skill_refs = sorted(ref for ref in requirement_obj.get("skill_refs", []) if isinstance(ref, str))

        if requirement_type == "unknown":
            unknown_requirements.append(
                {
                    **base_entry,
                    "unknown_kind": "hidden_or_unavailable_objective",
                    "reason": "The accepted mission bundle has an explicit unknown requirement for this objective.",
                }
            )
            continue

        derived_from_skills = []
        if not character_refs and skill_refs:
            derived_from_skills = derive_character_refs_from_skill_refs(skill_refs)
            character_refs = derived_from_skills

        if not character_refs:
            soft_fit_hints.append(
                {
                    **base_entry,
                    "hint_kind": "text_only_or_unmodeled_character_group",
                    "reason": "No exact character refs are available, so this requirement cannot be assigned to a deterministic team bucket.",
                }
            )
            continue

        missing_refs = [character_id for character_id in character_refs if character_id not in context["characters_by_id"]]
        missing_character_refs.update(missing_refs)
        coverage_options, interpretation_notes = build_coverage_options(
            requirement_obj,
            character_refs,
            team_size=team_size,
        )

        hard_constraints.append(
            {
                **base_entry,
                "character_refs": character_refs,
                "skill_refs": skill_refs,
                "coverage_options": coverage_options,
                "derived_character_refs_from_skill_refs": derived_from_skills,
                "missing_character_refs": missing_refs,
                "interpretation_notes": interpretation_notes,
            }
        )

    parse_obj = require_object(record.get("parse"), f"parse for {record_id}")
    source_ref_ids = [ref for ref in record.get("source_ref_ids", []) if isinstance(ref, str)]
    tags = mission_tag_details(record, context)

    return {
        "id": record_id,
        "name": record_name,
        "section_id": record.get("section_id"),
        "section_name": record.get("section_name"),
        "level_requirement": record.get("level_requirement"),
        "rank_requirement": record.get("rank_requirement"),
        "prerequisites": record.get("prerequisites", []),
        "rewards": record.get("rewards", []),
        "hard_constraints": hard_constraints,
        "soft_fit_hints": soft_fit_hints,
        "unknown_requirements": unknown_requirements,
        "data_quality": {
            "tag_ids": [tag_id for tag_id in record.get("data_quality_tag_ids", []) if isinstance(tag_id, str)],
            "tags": tags,
            "parse_confidence": parse_obj.get("confidence"),
            "ambiguity_flags": parse_obj.get("ambiguity_flags", []),
            "missing_character_refs": sorted(missing_character_refs),
        },
        "provenance": {
            "source_ref_ids": source_ref_ids,
            "source_refs": resolve_source_refs(source_ref_ids, context),
        },
    }


def mission_rank_entry(analysis: dict[str, Any]) -> dict[str, Any]:
    rank_requirement = analysis.get("rank_requirement")
    rank_label = normalize_rank_label(rank_requirement)
    return {
        "mission_id": analysis["id"],
        "mission_name": analysis["name"],
        "rank_label": rank_label,
        "rank_index": rank_band_index(rank_label),
        "rank_requirement": rank_requirement,
        "level_requirement": analysis.get("level_requirement"),
    }


def infer_roster_ceiling(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [mission_rank_entry(analysis) for analysis in analyses]
    known_entries = [entry for entry in entries if isinstance(entry.get("rank_index"), int)]
    unknown_entries = [entry for entry in entries if not isinstance(entry.get("rank_index"), int)]

    if not known_entries:
        return {
            "status": "unavailable",
            "rank_label": None,
            "rank_index": None,
            "rank_order": list(RANK_BAND_SEQUENCE),
            "source_missions": entries,
            "unknown_rank_missions": unknown_entries,
            "detail": "No requested mission exposes a recognized rank_requirement, so default planning cannot safely widen beyond the base or unlisted mission-reward roster.",
        }

    ceiling_entry = max(known_entries, key=lambda item: (item["rank_index"], item["mission_name"].lower(), item["mission_id"]))
    return {
        "status": "partial" if unknown_entries else "known",
        "rank_label": ceiling_entry["rank_label"],
        "rank_index": ceiling_entry["rank_index"],
        "rank_order": list(RANK_BAND_SEQUENCE),
        "source_missions": entries,
        "unknown_rank_missions": unknown_entries,
        "detail": "Highest recognized requested mission rank is used as the conservative roster ceiling.",
    }


def progression_brief(summary: dict[str, Any]) -> dict[str, Any]:
    progression = summary.get("progression", {})
    if not isinstance(progression, dict):
        progression = {}
    return {
        "id": summary.get("id"),
        "name": summary.get("name"),
        "classification": progression.get("classification"),
        "minimum_rank_label": progression.get("minimum_rank_label"),
        "minimum_rank_index": progression.get("minimum_rank_index"),
        "minimum_level": progression.get("minimum_level"),
        "unlock_mission_id": progression.get("unlock_mission_id"),
        "unlock_mission_name": progression.get("unlock_mission_name"),
    }


def character_allowed_by_progression(summary: dict[str, Any], progression_contract: dict[str, Any]) -> bool:
    if progression_contract.get("override_higher_rank") is True:
        return True

    ceiling = progression_contract.get("roster_ceiling", {})
    ceiling_rank_label = ceiling.get("rank_label") if isinstance(ceiling, dict) else None
    if isinstance(ceiling_rank_label, str):
        return character_within_rank_ceiling(summary, ceiling_rank_label)

    progression = summary.get("progression")
    if not isinstance(progression, dict):
        return False
    return progression.get("minimum_rank_index") == -1


def build_progression_contract(
    analyses: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    include_higher_rank: bool,
) -> dict[str, Any]:
    roster_ceiling = infer_roster_ceiling(analyses)
    summaries = context["character_summaries"]

    provisional_contract = {
        "override_higher_rank": include_higher_rank,
        "roster_ceiling": roster_ceiling,
    }
    allowed = [
        summary
        for summary in summaries
        if character_allowed_by_progression(summary, provisional_contract)
    ]
    blocked = [
        summary
        for summary in summaries
        if summary["id"] not in {item["id"] for item in allowed}
    ]

    if include_higher_rank:
        mode = "explicit_higher_rank_override"
        policy = "Higher-rank characters are allowed because the caller supplied an explicit override."
        blocked = []
        allowed = list(summaries)
    elif roster_ceiling["status"] == "unavailable":
        mode = "rank_ceiling_unavailable_base_only"
        policy = (
            "No recognized mission rank ceiling is available; only base or unlisted mission-reward characters are eligible by default."
        )
    else:
        mode = "conservative_mission_rank_ceiling"
        policy = (
            "Mission and mission-pool requests are progression-scoped by default; eligible characters must be base/unlisted "
            "or mission rewards at or below the highest requested mission rank."
        )

    blocked_examples = sorted(
        [progression_brief(summary) for summary in blocked],
        key=lambda item: (
            item["minimum_rank_index"] if isinstance(item.get("minimum_rank_index"), int) else 999,
            item.get("name") or "",
            item.get("id") or "",
        ),
    )[:8]
    allowed_rank_labels = sorted(
        {
            progression.get("minimum_rank_label")
            for summary in allowed
            for progression in [summary.get("progression", {})]
            if isinstance(progression, dict) and isinstance(progression.get("minimum_rank_label"), str)
        },
        key=lambda label: rank_band_index(label) if rank_band_index(label) is not None else 999,
    )

    return {
        "mode": mode,
        "override_higher_rank": include_higher_rank,
        "policy": policy,
        "override_policy": "Use --include-higher-rank only when the user explicitly says higher-rank units are already owned or asks for future planning.",
        "unknown_rank_policy": "If the requested mission rank cannot be recognized, the default planner does not silently open the full late-rank roster.",
        "roster_ceiling": roster_ceiling,
        "allowed_character_count": len(allowed),
        "allowed_rank_labels": allowed_rank_labels,
        "base_or_unlisted_character_count": sum(
            1
            for summary in summaries
            if isinstance(summary.get("progression"), dict)
            and summary["progression"].get("minimum_rank_index") == -1
        ),
        "blocked_later_rank_count": len(blocked),
        "blocked_later_rank_examples": blocked_examples,
    }


def progression_blocked_character_ids(
    character_ids: list[str],
    context: dict[str, Any],
    progression_contract: dict[str, Any],
) -> list[str]:
    blocked = []
    for character_id in character_ids:
        summary = context["characters_by_id"].get(character_id)
        if not isinstance(summary, dict):
            continue
        if not character_allowed_by_progression(summary, progression_contract):
            blocked.append(character_id)
    return sorted(set(blocked), key=lambda character_id: character_sort_key(character_id, context))


def collect_exact_units(
    analyses: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    team_size: int,
    progression_contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    units = []
    impossible_units = []

    for analysis in analyses:
        for hard_constraint in analysis["hard_constraints"]:
            evaluated_options = []
            for option in hard_constraint["coverage_options"]:
                option_entry = dict(option)
                option_entry["progression_blocked_character_ids"] = progression_blocked_character_ids(
                    option_entry["required_character_ids"],
                    context,
                    progression_contract,
                )
                evaluated_options.append(option_entry)
            unit = {
                "unit_id": hard_constraint["requirement_id"],
                "mission_id": analysis["id"],
                "mission_name": analysis["name"],
                "requirement_id": hard_constraint["requirement_id"],
                "step_index": hard_constraint.get("step_index"),
                "requirement_type": hard_constraint.get("requirement_type"),
                "count": hard_constraint.get("count"),
                "condition_text": hard_constraint.get("condition_text"),
                "confidence": hard_constraint.get("confidence"),
                "coverage_options": evaluated_options,
                "missing_character_refs": hard_constraint["missing_character_refs"],
            }
            usable_options = [
                option
                for option in evaluated_options
                if option["team_size_fit"]
                and all(character_id not in hard_constraint["missing_character_refs"] for character_id in option["required_character_ids"])
                and not option["progression_blocked_character_ids"]
            ]
            if usable_options:
                unit["usable_options"] = usable_options
                units.append(unit)
            else:
                progression_blocked = sorted(
                    {
                        character_id
                        for option in evaluated_options
                        for character_id in option["progression_blocked_character_ids"]
                    },
                    key=lambda character_id: character_sort_key(character_id, context),
                )
                reason_parts = []
                if progression_blocked:
                    reason_parts.append("at least one option exceeds the default progression roster ceiling")
                if any(not option["team_size_fit"] for option in evaluated_options):
                    reason_parts.append("at least one option exceeds the configured team size")
                if hard_constraint["missing_character_refs"]:
                    reason_parts.append("at least one option references missing character records")
                unit["reason"] = (
                    "No coverage option is usable: " + "; ".join(reason_parts)
                    if reason_parts
                    else "No coverage option fits the configured team size or all options reference missing character records."
                )
                unit["progression_blocked_character_refs"] = progression_blocked
                unit["team_size"] = team_size
                impossible_units.append(unit)

    return units, impossible_units


def character_name(character_id: str, context: dict[str, Any]) -> str:
    character = context["characters_by_id"].get(character_id)
    if isinstance(character, dict):
        return character.get("name", character_id)
    return character_id


def character_sort_key(character_id: str, context: dict[str, Any]) -> tuple[str, str]:
    return (character_name(character_id, context).lower(), character_id)


def progress_summary_for_unit_team(
    unit: dict[str, Any],
    character_ids: set[str] | frozenset[str] | tuple[str, ...] | list[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    team_ids = set(character_ids)
    structured_options = [
        option
        for option in unit.get("coverage_options", [])
        if isinstance(option, dict)
        and option.get("progress_counting") == "per_eligible_character_present"
        and isinstance(option.get("eligible_character_ids"), list)
    ]
    if structured_options:
        eligible_ids = sorted(
            {
                character_id
                for option in structured_options
                for character_id in option["eligible_character_ids"]
                if isinstance(character_id, str)
            },
            key=lambda character_id: character_sort_key(character_id, context),
        )
        matched_ids = [
            character_id
            for character_id in eligible_ids
            if character_id in team_ids
        ]
        max_progress = max(
            (
                option.get("max_progress_per_qualifying_battle")
                for option in structured_options
                if isinstance(option.get("max_progress_per_qualifying_battle"), int)
            ),
            default=len(eligible_ids),
        )
        return {
            "progress_counting": "per_eligible_character_present",
            "eligible_character_ids": eligible_ids,
            "matched_eligible_character_ids": matched_ids,
            "progress_units_for_qualifying_battle": len(matched_ids),
            "max_progress_per_qualifying_battle": max_progress,
            "progress_status": "modeled_exact" if matched_ids else "not_satisfied",
        }

    satisfied = any(
        isinstance(option, dict)
        and set(option.get("required_character_ids", [])).issubset(team_ids)
        for option in unit.get("coverage_options", [])
    )
    return {
        "progress_counting": "per_requirement",
        "eligible_character_ids": sorted(
            {
                character_id
                for option in unit.get("coverage_options", [])
                if isinstance(option, dict)
                for character_id in option.get("required_character_ids", [])
                if isinstance(character_id, str)
            },
            key=lambda character_id: character_sort_key(character_id, context),
        ),
        "matched_eligible_character_ids": [],
        "progress_units_for_qualifying_battle": 1 if satisfied else 0,
        "max_progress_per_qualifying_battle": 1,
        "progress_status": "modeled_exact" if satisfied else "not_satisfied",
    }


def build_candidate_buckets(units: list[dict[str, Any]], context: dict[str, Any], *, team_size: int) -> list[dict[str, Any]]:
    character_universe = sorted(
        {
            character_id
            for unit in units
            for option in unit["usable_options"]
            for character_id in option["required_character_ids"]
        },
        key=lambda character_id: character_sort_key(character_id, context),
    )

    candidates = []
    for size in range(1, min(team_size, len(character_universe)) + 1):
        for combo in itertools.combinations(character_universe, size):
            character_ids = frozenset(combo)
            covered_indexes = []
            covered_unit_ids = []
            for index, unit in enumerate(units):
                if any(set(option["required_character_ids"]).issubset(character_ids) for option in unit["usable_options"]):
                    covered_indexes.append(index)
                    covered_unit_ids.append(unit["unit_id"])
            if not covered_indexes:
                continue
            mask = 0
            for index in covered_indexes:
                mask |= 1 << index
            candidates.append(
                {
                    "candidate_id": f"candidate:{len(candidates) + 1:04d}",
                    "character_ids": tuple(sorted(character_ids, key=lambda item: character_sort_key(item, context))),
                    "covered_unit_indexes": tuple(covered_indexes),
                    "covered_unit_ids": tuple(covered_unit_ids),
                    "coverage_mask": mask,
                }
            )

    candidates.sort(key=lambda candidate: candidate_search_key(candidate, context))
    return candidates


def candidate_search_key(candidate: dict[str, Any], context: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -len(candidate["covered_unit_ids"]),
        len(candidate["character_ids"]),
        tuple(character_sort_key(character_id, context) for character_id in candidate["character_ids"]),
    )


def candidate_display_key(candidate: dict[str, Any], context: dict[str, Any]) -> tuple[Any, ...]:
    return (
        tuple(character_sort_key(character_id, context) for character_id in candidate["character_ids"]),
        tuple(candidate["covered_unit_ids"]),
    )


def plan_key(plan: list[dict[str, Any]], context: dict[str, Any]) -> tuple[Any, ...]:
    ordered = sorted(plan, key=lambda candidate: candidate_display_key(candidate, context))
    return (
        len(ordered),
        sum(len(candidate["character_ids"]) for candidate in ordered),
        tuple(candidate_display_key(candidate, context) for candidate in ordered),
    )


def optimize_exact_units(units: list[dict[str, Any]], context: dict[str, Any], *, team_size: int) -> dict[str, Any]:
    if not units:
        return {
            "planning_mode": "no_exact_units",
            "selected_candidates": [],
            "candidate_count": 0,
            "covered_unit_ids": [],
            "uncovered_unit_ids": [],
        }

    candidates = build_candidate_buckets(units, context, team_size=team_size)
    full_mask = (1 << len(units)) - 1
    candidates_by_unit: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        for unit_index in candidate["covered_unit_indexes"]:
            candidates_by_unit[unit_index].append(candidate)

    for unit_index in range(len(units)):
        candidates_by_unit[unit_index].sort(key=lambda candidate: candidate_search_key(candidate, context))

    max_cover = max((len(candidate["covered_unit_ids"]) for candidate in candidates), default=1)
    best_plan: list[dict[str, Any]] | None = None
    seen_depth: dict[int, int] = {}

    def uncovered_indexes(covered_mask: int) -> list[int]:
        return [index for index in range(len(units)) if not covered_mask & (1 << index)]

    def choose_next_unit(covered_mask: int) -> int:
        return min(
            uncovered_indexes(covered_mask),
            key=lambda index: (
                len(candidates_by_unit[index]),
                units[index]["mission_name"].lower(),
                units[index]["requirement_id"],
            ),
        )

    def search(selected: list[dict[str, Any]], covered_mask: int) -> None:
        nonlocal best_plan

        if covered_mask == full_mask:
            if best_plan is None or plan_key(selected, context) < plan_key(best_plan, context):
                best_plan = list(selected)
            return

        if best_plan is not None and len(selected) >= len(best_plan):
            return

        remaining_count = len(uncovered_indexes(covered_mask))
        lower_bound = math.ceil(remaining_count / max_cover)
        if best_plan is not None and len(selected) + lower_bound > len(best_plan):
            return

        previous_depth = seen_depth.get(covered_mask)
        if previous_depth is not None and previous_depth < len(selected):
            return
        seen_depth[covered_mask] = len(selected)

        unit_index = choose_next_unit(covered_mask)
        for candidate in candidates_by_unit[unit_index]:
            new_mask = covered_mask | candidate["coverage_mask"]
            if new_mask == covered_mask:
                continue
            search([*selected, candidate], new_mask)

    search([], 0)

    selected_candidates = sorted(best_plan or [], key=lambda candidate: candidate_display_key(candidate, context))
    covered_mask = 0
    for candidate in selected_candidates:
        covered_mask |= candidate["coverage_mask"]
    covered_unit_ids = [units[index]["unit_id"] for index in range(len(units)) if covered_mask & (1 << index)]
    uncovered_unit_ids = [units[index]["unit_id"] for index in range(len(units)) if not covered_mask & (1 << index)]

    return {
        "planning_mode": "exact_set_cover_over_bundle_constraints",
        "selected_candidates": selected_candidates,
        "candidate_count": len(candidates),
        "covered_unit_ids": covered_unit_ids,
        "uncovered_unit_ids": uncovered_unit_ids,
    }


def member_briefs(character_ids: tuple[str, ...], context: dict[str, Any]) -> list[dict[str, Any]]:
    briefs = []
    for character_id in character_ids:
        member = context["characters_by_id"][character_id]
        briefs.append(
            {
                "id": member["id"],
                "name": member["name"],
                "role_hints": member["role_hint_details"],
                "progression": member["progression"],
                "chakra_profile": {
                    "component_totals": member["chakra_profile"]["component_totals"],
                    "skill_usage_counts": member["chakra_profile"]["skill_usage_counts"],
                    "top_types": member["chakra_profile"]["top_types"],
                },
                "data_quality": member["data_quality"],
                "provenance": {
                    "record_source_ref_ids": member["record_source_ref_ids"],
                    "record_sources": member["record_sources"],
                },
            }
        )
    return briefs


def build_team_surface(character_ids: tuple[str, ...], context: dict[str, Any]) -> dict[str, Any]:
    members = [context["characters_by_id"][character_id] for character_id in character_ids]
    chakra_report = build_team_chakra_report(members)
    data_quality_report = build_data_quality_warnings(members, context)
    weakness_notes = build_weakness_notes(members, chakra_report, data_quality_report)

    return {
        "role_matrix": build_role_matrix(members),
        "team_identity_hints": build_team_identity_hints(members, context),
        "chakra_curve": chakra_report,
        "strength_notes": build_strength_notes(members, context, chakra_report),
        "weakness_notes": weakness_notes,
        "data_quality_warnings": data_quality_report,
        "substitution_hooks": build_substitution_hooks(weakness_notes),
        "provenance_hooks": build_provenance_hooks(members),
    }


def build_bucket_payloads(
    selected_candidates: list[dict[str, Any]],
    units: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    team_size: int,
    progression_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    buckets = []
    for index, candidate in enumerate(selected_candidates, start=1):
        bucket_id = f"bucket:{index:02d}"
        covered_units = [units[unit_index] for unit_index in candidate["covered_unit_indexes"]]
        character_ids = candidate["character_ids"]
        covered_by_mission: dict[str, dict[str, Any]] = {}
        for unit in covered_units:
            progress_summary = progress_summary_for_unit_team(unit, character_ids, context)
            entry = covered_by_mission.setdefault(
                unit["mission_id"],
                {
                    "mission_id": unit["mission_id"],
                    "mission_name": unit["mission_name"],
                    "covered_requirement_ids": [],
                    "covered_conditions": [],
                },
            )
            entry["covered_requirement_ids"].append(unit["requirement_id"])
            entry["covered_conditions"].append(
                {
                    "requirement_id": unit["requirement_id"],
                    "requirement_type": unit["requirement_type"],
                    "condition_text": unit["condition_text"],
                    "count": unit["count"],
                    "progress_summary": progress_summary,
                }
            )

        progression_members = [
            progression_brief(context["characters_by_id"][character_id])
            for character_id in character_ids
        ]
        blocked_by_progression = progression_blocked_character_ids(
            list(character_ids),
            context,
            progression_contract,
        )
        buckets.append(
            {
                "bucket_id": bucket_id,
                "required_member_count": len(character_ids),
                "flex_slots": max(team_size - len(character_ids), 0),
                "required_member_ids": list(character_ids),
                "required_members": member_briefs(character_ids, context),
                "covered_missions": sorted(
                    covered_by_mission.values(),
                    key=lambda item: (item["mission_name"].lower(), item["mission_id"]),
                ),
                "covered_requirement_units": sorted(
                    [
                        {
                            "unit_id": unit["unit_id"],
                            "mission_id": unit["mission_id"],
                            "mission_name": unit["mission_name"],
                            "requirement_id": unit["requirement_id"],
                            "requirement_type": unit["requirement_type"],
                            "condition_text": unit["condition_text"],
                            "progress_summary": progress_summary_for_unit_team(unit, character_ids, context),
                        }
                        for unit in covered_units
                    ],
                    key=lambda item: (item["mission_name"].lower(), item["requirement_id"]),
                ),
                "rationale": [
                    "All listed coverage is based on exact character or skill-owner refs from the skill-local mission bundle.",
                    "Flex slots are intentionally left open when the mission pool does not require a full three-character core.",
                    "Required members are checked against progression_contract before a bucket is selected.",
                ],
                "progression": {
                    "fits_roster_ceiling": not blocked_by_progression,
                    "blocked_member_ids": blocked_by_progression,
                    "member_unlocks": progression_members,
                },
                "team_surface": build_team_surface(character_ids, context),
            }
        )

    return buckets


def coverage_maps(buckets: list[dict[str, Any]]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    requirement_to_buckets: dict[str, set[str]] = defaultdict(set)
    mission_to_buckets: dict[str, set[str]] = defaultdict(set)

    for bucket in buckets:
        bucket_id = bucket["bucket_id"]
        for unit in bucket["covered_requirement_units"]:
            requirement_to_buckets[unit["requirement_id"]].add(bucket_id)
            mission_to_buckets[unit["mission_id"]].add(bucket_id)

    return requirement_to_buckets, mission_to_buckets


def build_coverage_matrix(
    analyses: list[dict[str, Any]],
    impossible_units: list[dict[str, Any]],
    buckets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requirement_to_buckets, mission_to_buckets = coverage_maps(buckets)
    impossible_by_requirement = {unit["requirement_id"]: unit for unit in impossible_units}
    matrix = []

    for analysis in analyses:
        exact_requirement_ids = [item["requirement_id"] for item in analysis["hard_constraints"]]
        covered_requirement_ids = [
            requirement_id for requirement_id in exact_requirement_ids if requirement_id in requirement_to_buckets
        ]
        impossible_requirement_ids = [
            requirement_id for requirement_id in exact_requirement_ids if requirement_id in impossible_by_requirement
        ]
        has_unknown = bool(analysis["unknown_requirements"])
        has_soft = bool(analysis["soft_fit_hints"])

        if has_unknown:
            status = "exact_coverage_with_unknown_requirements" if covered_requirement_ids else "uncertain_unknown_requirements"
        elif not exact_requirement_ids and has_soft:
            status = "uncertain_soft_fit_only"
        elif exact_requirement_ids and len(covered_requirement_ids) == len(exact_requirement_ids):
            status = "fully_covered_split_across_buckets" if len(mission_to_buckets[analysis["id"]]) > 1 else "fully_covered_by_one_bucket"
            if has_soft:
                status = "covered_with_soft_fit_warnings"
        elif covered_requirement_ids:
            status = "partially_covered"
        else:
            status = "not_covered"

        warnings = []
        if has_unknown:
            warnings.append("Mission has explicit unknown requirements; no team bucket is claimed to cover hidden objectives.")
        if has_soft:
            warnings.append("Mission has text-only or unmodeled soft-fit hints that cannot be proven as exact coverage.")
        if impossible_requirement_ids:
            impossible_reasons = [
                impossible_by_requirement[requirement_id]
                for requirement_id in impossible_requirement_ids
                if requirement_id in impossible_by_requirement
            ]
            if any(item.get("progression_blocked_character_refs") for item in impossible_reasons):
                warnings.append("At least one exact requirement exceeds the active progression roster ceiling.")
            else:
                warnings.append("At least one exact requirement does not fit the configured team size or references a missing character.")

        matrix.append(
            {
                "mission_id": analysis["id"],
                "mission_name": analysis["name"],
                "coverage_status": status,
                "bucket_ids": sorted(mission_to_buckets[analysis["id"]]),
                "exact_requirements_total": len(exact_requirement_ids),
                "exact_requirements_covered": len(covered_requirement_ids),
                "covered_requirement_ids": sorted(covered_requirement_ids),
                "uncovered_requirement_ids": sorted(
                    requirement_id
                    for requirement_id in exact_requirement_ids
                    if requirement_id not in covered_requirement_ids
                ),
                "impossible_requirement_ids": sorted(impossible_requirement_ids),
                "unknown_requirement_ids": [
                    item["requirement_id"] for item in analysis["unknown_requirements"]
                ],
                "soft_fit_requirement_ids": [
                    item["requirement_id"] for item in analysis["soft_fit_hints"]
                ],
                "transparency_warnings": warnings,
            }
        )

    return matrix


def build_uncertain_missions(analyses: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix_by_id = {item["mission_id"]: item for item in matrix}
    uncertain = []
    for analysis in analyses:
        reasons = []
        if analysis["unknown_requirements"]:
            reasons.append(
                {
                    "kind": "unknown_requirements",
                    "requirement_ids": [item["requirement_id"] for item in analysis["unknown_requirements"]],
                    "detail": "Objective text is hidden or unavailable in the accepted bundle.",
                }
            )
        if analysis["soft_fit_hints"]:
            reasons.append(
                {
                    "kind": "soft_fit_hints",
                    "requirement_ids": [item["requirement_id"] for item in analysis["soft_fit_hints"]],
                    "detail": "Requirement text is preserved, but exact team coverage cannot be proven from structured refs.",
                }
            )
        if not reasons:
            continue
        uncertain.append(
            {
                "mission_id": analysis["id"],
                "mission_name": analysis["name"],
                "coverage_status": matrix_by_id[analysis["id"]]["coverage_status"],
                "reasons": reasons,
            }
        )
    return uncertain


def split_assumed_team_refs(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def resolve_assumed_team_ref(raw_ref: str, context: dict[str, Any]) -> dict[str, Any]:
    characters_by_id = context["characters_by_id"]
    if raw_ref in characters_by_id:
        return {
            "input": raw_ref,
            "status": "resolved",
            "character_id": raw_ref,
            "name": characters_by_id[raw_ref].get("name"),
            "matched_field": "id",
        }

    normalized_ref = normalize_identity_token(raw_ref)
    matches = []
    for character_id, character in characters_by_id.items():
        for field in ("id", "name"):
            value = character_id if field == "id" else character.get("name")
            if not isinstance(value, str):
                continue
            if normalize_identity_token(value) == normalized_ref:
                matches.append((character_id, character.get("name"), field))

    if len(matches) == 1:
        character_id, name, field = matches[0]
        return {
            "input": raw_ref,
            "status": "resolved",
            "character_id": character_id,
            "name": name,
            "matched_field": field,
        }
    if len(matches) > 1:
        return {
            "input": raw_ref,
            "status": "ambiguous",
            "candidates": [
                {
                    "character_id": character_id,
                    "name": name,
                    "matched_field": field,
                }
                for character_id, name, field in matches[:8]
            ],
        }
    return {
        "input": raw_ref,
        "status": "not_found",
        "candidates": [],
    }


def build_assumed_team_progress(
    analyses: list[dict[str, Any]],
    units: list[dict[str, Any]],
    context: dict[str, Any],
    raw_team: str | None,
) -> dict[str, Any] | None:
    raw_refs = split_assumed_team_refs(raw_team)
    if not raw_refs:
        return None

    resolutions = [resolve_assumed_team_ref(raw_ref, context) for raw_ref in raw_refs]
    resolved_member_ids = sorted(
        {
            item["character_id"]
            for item in resolutions
            if item.get("status") == "resolved" and isinstance(item.get("character_id"), str)
        },
        key=lambda character_id: character_sort_key(character_id, context),
    )
    unit_by_requirement = {
        unit["requirement_id"]: unit
        for unit in units
        if isinstance(unit.get("requirement_id"), str)
    }
    mission_progress = []

    for analysis in analyses:
        requirement_progress = []
        for hard_constraint in analysis["hard_constraints"]:
            requirement_id = hard_constraint["requirement_id"]
            unit = unit_by_requirement.get(requirement_id)
            if unit is None:
                requirement_progress.append(
                    {
                        "requirement_id": requirement_id,
                        "requirement_type": hard_constraint.get("requirement_type"),
                        "condition_text": hard_constraint.get("condition_text"),
                        "progress_status": "unavailable",
                        "progress_units_for_qualifying_battle": None,
                        "detail": "No exact unit was available for this requirement under the active planner constraints.",
                    }
                )
                continue
            requirement_progress.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_type": unit.get("requirement_type"),
                    "condition_text": unit.get("condition_text"),
                    **progress_summary_for_unit_team(unit, resolved_member_ids, context),
                }
            )

        for soft_hint in analysis["soft_fit_hints"]:
            requirement_progress.append(
                {
                    "requirement_id": soft_hint.get("requirement_id"),
                    "requirement_type": soft_hint.get("requirement_type"),
                    "condition_text": soft_hint.get("condition_text"),
                    "progress_status": "unmodeled_text_only_or_group",
                    "progress_units_for_qualifying_battle": None,
                    "detail": "This requirement lacks exact eligible character refs, so assumed-team progress is not invented.",
                }
            )

        for unknown_requirement in analysis["unknown_requirements"]:
            requirement_progress.append(
                {
                    "requirement_id": unknown_requirement.get("requirement_id"),
                    "requirement_type": unknown_requirement.get("requirement_type"),
                    "condition_text": unknown_requirement.get("condition_text"),
                    "progress_status": "unknown_hidden_or_unavailable",
                    "progress_units_for_qualifying_battle": None,
                    "detail": "This objective is explicitly unknown in the accepted bundle.",
                }
            )

        modeled_total = sum(
            item["progress_units_for_qualifying_battle"]
            for item in requirement_progress
            if isinstance(item.get("progress_units_for_qualifying_battle"), int)
        )
        mission_progress.append(
            {
                "mission_id": analysis["id"],
                "mission_name": analysis["name"],
                "modeled_progress_units_for_qualifying_battle": modeled_total,
                "requirements": sorted(
                    requirement_progress,
                    key=lambda item: str(item.get("requirement_id")),
                ),
            }
        )

    return {
        "input_member_refs": raw_refs,
        "member_resolutions": resolutions,
        "resolved_member_ids": resolved_member_ids,
        "unresolved_member_refs": [
            item["input"]
            for item in resolutions
            if item.get("status") != "resolved"
        ],
        "mission_progress": mission_progress,
    }


def build_split_rationale(
    analyses: list[dict[str, Any]],
    units: list[dict[str, Any]],
    buckets: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    *,
    team_size: int,
) -> list[dict[str, Any]]:
    rationale = []
    exact_character_ids = sorted(
        {
            character_id
            for unit in units
            for option in unit["usable_options"]
            for character_id in option["required_character_ids"]
        }
    )

    if not units:
        rationale.append(
            {
                "kind": "no_exact_team_constraints",
                "detail": "Requested missions expose no exact bundle-backed character requirements that can be assigned to team buckets.",
            }
        )
    elif len(buckets) == 1:
        rationale.append(
            {
                "kind": "grouped_into_one_bucket",
                "detail": "All exact mission requirements fit within one practical team bucket.",
                "required_character_count": len(exact_character_ids),
                "team_size": team_size,
            }
        )
    else:
        detail = "The exact mission constraints need more than one practical team bucket."
        if len(exact_character_ids) > team_size:
            detail = (
                "The pool references more exact required characters than one team can hold, so the planner split coverage honestly."
            )
        rationale.append(
            {
                "kind": "split_required",
                "detail": detail,
                "required_character_count": len(exact_character_ids),
                "team_size": team_size,
                "bucket_count": len(buckets),
            }
        )

    for matrix_entry in matrix:
        if matrix_entry["coverage_status"] == "fully_covered_split_across_buckets":
            rationale.append(
                {
                    "kind": "mission_split_across_buckets",
                    "mission_id": matrix_entry["mission_id"],
                    "mission_name": matrix_entry["mission_name"],
                    "bucket_ids": matrix_entry["bucket_ids"],
                    "detail": "This mission has multiple exact requirements that are covered by different team buckets.",
                }
            )
        if matrix_entry["unknown_requirement_ids"]:
            rationale.append(
                {
                    "kind": "uncertainty_warning",
                    "mission_id": matrix_entry["mission_id"],
                    "mission_name": matrix_entry["mission_name"],
                    "unknown_requirement_ids": matrix_entry["unknown_requirement_ids"],
                    "detail": "Unknown objectives are surfaced as uncertainty and are not counted as covered.",
                }
            )

    return rationale


def build_blocked_payload(args: argparse.Namespace, resolutions: list[dict[str, Any]], references_dir: Path) -> dict[str, Any]:
    return {
        "status": "blocked",
        "references_dir": str(references_dir),
        "requested_missions": args.missions,
        "mission_resolutions": resolutions,
        "message": "At least one mission could not be resolved uniquely from the skill-local mission bundle.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a Naruto Arena mission pool into deterministic practical team buckets from the validated skill-local bundle."
        )
    )
    parser.add_argument(
        "missions",
        nargs="+",
        help="Mission ids or names to resolve. Exact names or ids are preferred for deterministic planning.",
    )
    parser.add_argument(
        "--team-size",
        type=int,
        default=3,
        help="Maximum number of required members in one practical team bucket. Default: 3.",
    )
    parser.add_argument(
        "--include-higher-rank",
        action="store_true",
        help=(
            "Explicit override for users who say higher-rank characters are already unlocked or want future-planning teams. "
            "Without this flag, mission planning is bounded by the highest requested mission rank band."
        ),
    )
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=DEFAULT_REFERENCES_DIR,
        help="Skill-local references directory. Defaults to skills/naruto-arena-team-builder/references.",
    )
    parser.add_argument(
        "--assume-team",
        default=None,
        help=(
            "Optional comma-separated character ids or exact names for an assumed team progress audit. "
            "This does not force bucket selection; it reports modeled progress units for the supplied members."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.team_size <= 0:
        raise SystemExit("--team-size must be greater than 0")

    references_dir = args.references_dir.resolve()
    context = load_planning_context(references_dir)

    resolutions = []
    resolved_missions = []
    seen_mission_ids = set()
    for raw_mission in args.missions:
        resolution = resolve_mission_query(raw_mission, context["missions"])
        if resolution["status"] == "resolved":
            mission = resolution["mission"]
            duplicate = mission["id"] in seen_mission_ids
            if not duplicate:
                resolved_missions.append(mission)
                seen_mission_ids.add(mission["id"])
            resolutions.append(
                {
                    "input": raw_mission,
                    "status": "resolved" if not duplicate else "duplicate",
                    "query_match": resolution["query_match"],
                    "mission": {
                        "id": mission["id"],
                        "name": mission["name"],
                        "section_name": mission.get("section_name"),
                    },
                }
            )
            continue
        resolutions.append(
            {
                "input": raw_mission,
                "status": resolution["status"],
                "candidates": resolution.get("candidates", []),
            }
        )

    if any(item["status"] not in {"resolved", "duplicate"} for item in resolutions):
        print(json.dumps(build_blocked_payload(args, resolutions, references_dir), ensure_ascii=False, indent=2))
        return 2

    analyses = [
        build_mission_analysis(record, context, team_size=args.team_size)
        for record in resolved_missions
    ]
    progression_contract = build_progression_contract(
        analyses,
        context,
        include_higher_rank=args.include_higher_rank,
    )
    exact_units, impossible_units = collect_exact_units(
        analyses,
        context,
        team_size=args.team_size,
        progression_contract=progression_contract,
    )
    assumed_team_progress = build_assumed_team_progress(
        analyses,
        [*exact_units, *impossible_units],
        context,
        args.assume_team,
    )
    optimization = optimize_exact_units(exact_units, context, team_size=args.team_size)
    buckets = build_bucket_payloads(
        optimization["selected_candidates"],
        exact_units,
        context,
        team_size=args.team_size,
        progression_contract=progression_contract,
    )
    matrix = build_coverage_matrix(analyses, impossible_units, buckets)
    uncertain_missions = build_uncertain_missions(analyses, matrix)

    payload = {
        "status": "ok",
        "references_dir": str(references_dir),
        "requested_missions": args.missions,
        "mission_resolutions": resolutions,
        "planning_contract": {
            "team_size": args.team_size,
            "coverage_basis": "Only exact character refs or skill-owner refs from the skill-local mission bundle count as covered.",
            "hard_constraint_policy": "Hard constraints are assigned to buckets only when a required character set fits within team_size.",
            "soft_fit_policy": "Text-only groups and unmodeled character groups remain visible as soft-fit hints, not proven coverage.",
            "unknown_policy": "Explicit unknown requirements are never converted into hidden coverage claims.",
            "progression_policy": "By default, eligible characters are bounded by the highest requested mission rank band using mission-reward unlock evidence from the skill-local bundle.",
            "progression_override_policy": "If --include-higher-rank is supplied, the payload records explicit_higher_rank_override and does not apply the conservative ceiling.",
            "alternative_character_progress_policy": "Structured alternative-character mission requirements count one progress unit per eligible named character present in an assumed team for a qualifying battle.",
            "helper_layer": "Bucket reasoning reuses the accepted search_characters.py summaries and team_candidate_report.py helper surfaces.",
        },
        "progression_contract": progression_contract,
        "summary": {
            "resolved_mission_count": len(resolved_missions),
            "exact_requirement_unit_count": len(exact_units),
            "impossible_exact_requirement_unit_count": len(impossible_units),
            "coverage_bucket_count": len(buckets),
            "uncertain_mission_count": len(uncertain_missions),
            "candidate_bucket_count_considered": optimization["candidate_count"],
            "planning_mode": optimization["planning_mode"],
        },
        "coverage_buckets": buckets,
        "coverage_matrix": matrix,
        "uncertain_missions": uncertain_missions,
        "split_rationale": build_split_rationale(
            analyses,
            exact_units,
            buckets,
            matrix,
            team_size=args.team_size,
        ),
        "mission_analyses": analyses,
        "impossible_exact_requirement_units": impossible_units,
    }
    if assumed_team_progress is not None:
        payload["assumed_team_progress"] = assumed_team_progress
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

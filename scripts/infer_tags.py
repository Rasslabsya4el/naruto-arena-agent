#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHARACTERS_PATH = REPO_ROOT / "data" / "normalized" / "characters.json"
DEFAULT_MISSIONS_PATH = REPO_ROOT / "data" / "normalized" / "missions.json"
DEFAULT_TAXONOMY_PATH = REPO_ROOT / "references" / "effect-taxonomy.json"
DEFAULT_TAGS_PATH = REPO_ROOT / "references" / "tags.json"
TAXONOMY_VERSION = "taxonomy-v1"

EFFECT_FAMILY_DEFINITIONS: dict[str, dict[str, str]] = {
    "offense": {
        "label": "Offense",
        "definition": "Effects that directly pressure health totals or raise future damage output.",
    },
    "defense": {
        "label": "Defense",
        "definition": "Effects that prevent damage, add protection, or reduce incoming or outgoing damage.",
    },
    "control": {
        "label": "Control",
        "definition": "Effects that limit enemy actions or apply rule-level restrictions.",
    },
    "sustain": {
        "label": "Sustain",
        "definition": "Effects that restore health or keep a character active over longer fights.",
    },
    "resource": {
        "label": "Resource",
        "definition": "Effects that grant, steal, or otherwise manipulate chakra-like resources and similar gains.",
    },
    "state": {
        "label": "State",
        "definition": "Effects that apply, remove, or modify persistent states without cleanly fitting damage/heal buckets.",
    },
    "setup": {
        "label": "Setup",
        "definition": "Effects that unlock, replace, or improve other skills and future actions.",
    },
    "uncertainty": {
        "label": "Uncertainty",
        "definition": "Fallback or ambiguity buckets that must be surfaced instead of guessed away.",
    },
}

SKILL_CLASS_DEFINITIONS: dict[str, dict[str, str]] = {
    "instant": {
        "label": "Instant",
        "definition": "Source-provided skill class label captured directly from the canonical skill card.",
    },
    "physical": {
        "label": "Physical",
        "definition": "Source-provided skill class label for physical-type skills.",
    },
    "unique": {
        "label": "Unique",
        "definition": "Source-provided skill class label indicating the skill is marked unique by the canonical source.",
    },
    "chakra": {
        "label": "Chakra",
        "definition": "Source-provided skill class label for chakra-type skills.",
    },
    "ranged": {
        "label": "Ranged",
        "definition": "Source-provided skill class label for ranged skills.",
    },
    "melee": {
        "label": "Melee",
        "definition": "Source-provided skill class label for melee skills.",
    },
    "mental": {
        "label": "Mental",
        "definition": "Source-provided skill class label for mental-type skills.",
    },
    "affliction": {
        "label": "Affliction",
        "definition": "Source-provided skill class label for affliction-type skills.",
    },
    "action": {
        "label": "Action",
        "definition": "Source-provided skill class label marking action-type skills.",
    },
    "harmful": {
        "label": "Harmful",
        "definition": "Source-provided skill class label marking harmful skills.",
    },
    "helpful": {
        "label": "Helpful",
        "definition": "Source-provided skill class label marking helpful skills.",
    },
    "control": {
        "label": "Control",
        "definition": "Source-provided skill class label marking control-oriented skills.",
    },
    "passive": {
        "label": "Passive",
        "definition": "Source-provided skill class label marking passive skills.",
    },
}

EFFECT_TYPE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "damage": {
        "family_id": "offense",
        "label": "Damage",
        "definition": "Direct health loss on the described target.",
        "inference_notes": "Use target_shape subtags only when targeting is structured; otherwise keep only the broad damage tag.",
        "tag_hooks": [
            "character.capability.damage_effects",
            "character.capability.damage_single_target",
            "character.capability.damage_aoe",
        ],
    },
    "increase_damage": {
        "family_id": "offense",
        "label": "Increase Damage",
        "definition": "Raises damage dealt by another skill or future attack window.",
        "inference_notes": "Treat as setup or burst support, not standalone pressure, unless paired with direct damage evidence.",
        "tag_hooks": ["character.capability.damage_amplification"],
    },
    "reduce_damage": {
        "family_id": "defense",
        "label": "Reduce Damage",
        "definition": "Reduces damage taken or lowers damage output, depending on the target described by the effect.",
        "inference_notes": "Target-specific protection tags are safe only when the target is structured as self, ally, or all allies.",
        "tag_hooks": [
            "character.capability.damage_reduction",
            "character.capability.self_protection",
            "character.capability.ally_protection",
        ],
    },
    "protect": {
        "family_id": "defense",
        "label": "Protect",
        "definition": "Protection-style effect such as invulnerability, destructible defense, shielding, or similar protective language.",
        "inference_notes": "This bucket is broader than invulnerability alone; inspect raw text when exact protection semantics matter.",
        "tag_hooks": [
            "character.capability.protect_effects",
            "character.capability.self_protection",
            "character.capability.ally_protection",
        ],
    },
    "stun": {
        "family_id": "control",
        "label": "Stun",
        "definition": "Prevents or limits skill use for the stated duration.",
        "inference_notes": "Current normalization does not split partial and full stun variants; downstream use should inspect evidence text when needed.",
        "tag_hooks": ["character.capability.stun_effects"],
    },
    "apply_state": {
        "family_id": "state",
        "label": "Apply State",
        "definition": "Broad parser bucket for applied rules or states such as cannot be countered, invisibility, or other persistent constraints.",
        "inference_notes": "This bucket is intentionally broad and should not be mistaken for a single canonical mechanic family.",
        "tag_hooks": ["character.capability.state_application"],
    },
    "heal": {
        "family_id": "sustain",
        "label": "Heal",
        "definition": "Restores health to the target described by the effect.",
        "inference_notes": "Magnitude can stay partial when the text scales from current health thresholds or other conditions.",
        "tag_hooks": ["character.capability.heal_effects"],
    },
    "remove_state": {
        "family_id": "state",
        "label": "Remove State",
        "definition": "Broad parser bucket for removing chakra, buffs, afflictions, defense, or other existing states.",
        "inference_notes": "Do not assume every remove_state entry is chakra denial; check evidence when exact removal type matters.",
        "tag_hooks": ["character.capability.removal_effects"],
    },
    "gain": {
        "family_id": "resource",
        "label": "Gain",
        "definition": "Broad parser bucket for gaining chakra, defense, or other beneficial recurring value.",
        "inference_notes": "This bucket may mix direct resource gain with other beneficial gain text; keep the tag broad.",
        "tag_hooks": ["character.capability.gain_effects"],
    },
    "drain": {
        "family_id": "resource",
        "label": "Drain",
        "definition": "Broad parser bucket for drain, steal, absorb, or drain-setup text.",
        "inference_notes": "Some drain entries describe setup or replacement text instead of already-resolved drain output.",
        "tag_hooks": ["character.capability.drain_effects"],
    },
    "conditional": {
        "family_id": "setup",
        "label": "Conditional",
        "definition": "Setup text that unlocks, replaces, improves, or otherwise changes later skills or later turns.",
        "inference_notes": "Treat this as an enabler or transform bucket, not proof of immediate output by itself.",
        "tag_hooks": ["character.capability.conditional_effects"],
    },
    "unknown": {
        "family_id": "uncertainty",
        "label": "Unknown",
        "definition": "Fallback effect bucket when current heuristics cannot safely classify the text further.",
        "inference_notes": "Must be surfaced as uncertainty; downstream logic should inspect raw text and not invent a cleaner type.",
        "tag_hooks": ["character.data.effect_fallback_unknown"],
    },
}

CONDITION_TYPE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "previous_skill": {
        "label": "Previous Skill",
        "definition": "The effect applies only while or after a referenced skill has been used or is active.",
        "tag_hooks": ["character.capability.combo_dependency"],
    },
    "requires_state": {
        "label": "Requires State",
        "definition": "The effect depends on a described threshold or state that is not fully resolved to a reusable normalized reference.",
        "tag_hooks": ["character.capability.state_dependency"],
    },
}

MISSION_REQUIREMENT_TYPE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "win_with_character": {
        "label": "Win With Character",
        "definition": "Objective requires winning a number of battles with a named character or character group condition.",
        "tag_hooks": ["mission.objective.win_with_character"],
    },
    "streak": {
        "label": "Streak",
        "definition": "Objective requires consecutive wins before the counter resets.",
        "tag_hooks": ["mission.objective.streak"],
    },
    "use_skill": {
        "label": "Use Skill",
        "definition": "Objective requires activating a specific skill a stated number of times.",
        "tag_hooks": ["mission.objective.use_skill"],
    },
    "unknown": {
        "label": "Unknown",
        "definition": "Objective text is unavailable in the captured mission detail snapshot and must remain explicit unknown state.",
        "tag_hooks": ["mission.objective.unknown"],
    },
}

EFFECT_AMBIGUITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "effect_target_unknown": {
        "label": "Effect Target Unknown",
        "definition": "Parser could not safely resolve a structured target for the effect text.",
        "tag_hooks": ["character.data.effect_target_unknown"],
    },
    "effect_type_heuristic": {
        "label": "Effect Type Heuristic",
        "definition": "Effect type was inferred heuristically rather than from a cleaner parser match.",
        "tag_hooks": ["character.data.effect_type_heuristic"],
    },
    "effect_magnitude_unknown": {
        "label": "Effect Magnitude Unknown",
        "definition": "Parser could not safely extract a structured numeric magnitude from the effect text.",
        "tag_hooks": ["character.data.effect_magnitude_unknown"],
    },
    "effect_fallback_unknown": {
        "label": "Effect Fallback Unknown",
        "definition": "No structured heuristic matched the effect text, so the effect stays in the explicit unknown bucket.",
        "tag_hooks": ["character.data.effect_fallback_unknown"],
    },
}

MISSION_AMBIGUITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "objective_text_missing": {
        "label": "Objective Text Missing",
        "definition": "Mission objective text was unavailable in the captured snapshot.",
        "tag_hooks": ["mission.data.objective_text_missing"],
    },
    "detail_payload_redirect": {
        "label": "Detail Payload Redirect",
        "definition": "Mission detail route returned a redirect-shaped payload instead of the expected mission detail body.",
        "tag_hooks": ["mission.data.detail_payload_redirect"],
    },
    "detail_payload_error_page": {
        "label": "Detail Payload Error Page",
        "definition": "Mission detail route resolved to an error page payload, so the objective stays unknown.",
        "tag_hooks": ["mission.data.detail_payload_error_page"],
    },
    "detail_payload_unexpected_home": {
        "label": "Detail Payload Unexpected Home",
        "definition": "Mission detail route fell back to the site home payload instead of a mission detail payload.",
        "tag_hooks": ["mission.data.detail_payload_unexpected_home"],
    },
    "character_group_not_modeled": {
        "label": "Character Group Not Modeled",
        "definition": "Objective names a character group in text, but the current normalized mission contract does not model that group as explicit character refs.",
        "tag_hooks": ["mission.data.character_group_not_modeled"],
    },
    "multi_character_condition_not_structured": {
        "label": "Multi Character Condition Not Structured",
        "definition": "Objective mentions multiple characters or a compound character condition that stays preserved only in free text.",
        "tag_hooks": ["mission.data.multi_character_condition_not_structured"],
    },
    "character_subject_not_resolved": {
        "label": "Character Subject Not Resolved",
        "definition": "Objective names a character subject that could not be resolved into a normalized character ref.",
        "tag_hooks": ["mission.data.character_subject_not_resolved"],
    },
    "skill_reference_not_resolved": {
        "label": "Skill Reference Not Resolved",
        "definition": "Objective names a skill that could not be safely resolved into a normalized skill ref.",
        "tag_hooks": ["mission.data.skill_reference_not_resolved"],
    },
}

CHARACTER_TAG_CATALOG: dict[str, dict[str, str]] = {
    "character.capability.damage_effects": {
        "label": "Damage Effects",
        "category": "capability",
        "definition": "Character has at least one structured damage effect.",
        "inference": "Assigned when any skill effect has effect_type=damage.",
    },
    "character.capability.damage_single_target": {
        "label": "Single Target Damage",
        "category": "capability",
        "definition": "Character has structured direct damage aimed at one enemy.",
        "inference": "Assigned when a damage effect targets enemy:1.",
    },
    "character.capability.damage_aoe": {
        "label": "AOE Damage",
        "category": "capability",
        "definition": "Character has structured direct damage aimed at all enemies.",
        "inference": "Assigned when a damage effect targets all_enemies.",
    },
    "character.capability.damage_amplification": {
        "label": "Damage Amplification",
        "category": "capability",
        "definition": "Character has at least one structured increase_damage effect.",
        "inference": "Assigned when any skill effect has effect_type=increase_damage.",
    },
    "character.capability.protect_effects": {
        "label": "Protect Effects",
        "category": "capability",
        "definition": "Character has at least one structured protect effect.",
        "inference": "Assigned when any skill effect has effect_type=protect.",
    },
    "character.capability.self_protection": {
        "label": "Self Protection",
        "category": "capability",
        "definition": "Character has structured protection or damage reduction aimed at self.",
        "inference": "Assigned when protect/reduce_damage targets self.",
    },
    "character.capability.ally_protection": {
        "label": "Ally Protection",
        "category": "capability",
        "definition": "Character has structured protection or damage reduction aimed at an ally, all allies, or a self-or-ally target.",
        "inference": "Assigned when protect/reduce_damage targets ally, all_allies, or any.",
    },
    "character.capability.damage_reduction": {
        "label": "Damage Reduction",
        "category": "capability",
        "definition": "Character has at least one structured reduce_damage effect.",
        "inference": "Assigned when any skill effect has effect_type=reduce_damage.",
    },
    "character.capability.stun_effects": {
        "label": "Stun Effects",
        "category": "capability",
        "definition": "Character has at least one structured stun effect.",
        "inference": "Assigned when any skill effect has effect_type=stun.",
    },
    "character.capability.heal_effects": {
        "label": "Heal Effects",
        "category": "capability",
        "definition": "Character has at least one structured heal effect.",
        "inference": "Assigned when any skill effect has effect_type=heal.",
    },
    "character.capability.state_application": {
        "label": "State Application",
        "category": "capability",
        "definition": "Character has at least one structured apply_state effect.",
        "inference": "Assigned when any skill effect has effect_type=apply_state.",
    },
    "character.capability.removal_effects": {
        "label": "Removal Effects",
        "category": "capability",
        "definition": "Character has at least one structured remove_state effect.",
        "inference": "Assigned when any skill effect has effect_type=remove_state.",
    },
    "character.capability.gain_effects": {
        "label": "Gain Effects",
        "category": "capability",
        "definition": "Character has at least one structured gain effect.",
        "inference": "Assigned when any skill effect has effect_type=gain.",
    },
    "character.capability.drain_effects": {
        "label": "Drain Effects",
        "category": "capability",
        "definition": "Character has at least one structured drain effect.",
        "inference": "Assigned when any skill effect has effect_type=drain.",
    },
    "character.capability.conditional_effects": {
        "label": "Conditional Effects",
        "category": "capability",
        "definition": "Character has at least one structured conditional effect that changes later skills or windows.",
        "inference": "Assigned when any skill effect has effect_type=conditional.",
    },
    "character.capability.combo_dependency": {
        "label": "Combo Dependency",
        "category": "capability",
        "definition": "Character has at least one effect conditioned on a previously used or active skill.",
        "inference": "Assigned when any effect condition has condition_type=previous_skill.",
    },
    "character.capability.state_dependency": {
        "label": "State Dependency",
        "category": "capability",
        "definition": "Character has at least one effect conditioned on a threshold or unresolved state gate.",
        "inference": "Assigned when any effect condition has condition_type=requires_state.",
    },
    "character.data.effect_target_unknown": {
        "label": "Effect Target Unknown",
        "category": "data_quality",
        "definition": "Character has at least one effect whose structured target could not be resolved safely.",
        "inference": "Assigned when any effect ambiguity flag has code=effect_target_unknown.",
    },
    "character.data.effect_type_heuristic": {
        "label": "Effect Type Heuristic",
        "category": "data_quality",
        "definition": "Character has at least one effect typed heuristically instead of by a cleaner parser match.",
        "inference": "Assigned when any effect ambiguity flag has code=effect_type_heuristic.",
    },
    "character.data.effect_magnitude_unknown": {
        "label": "Effect Magnitude Unknown",
        "category": "data_quality",
        "definition": "Character has at least one effect with unresolved numeric magnitude.",
        "inference": "Assigned when any effect ambiguity flag has code=effect_magnitude_unknown.",
    },
    "character.data.effect_fallback_unknown": {
        "label": "Effect Fallback Unknown",
        "category": "data_quality",
        "definition": "Character has at least one effect in the explicit fallback unknown bucket.",
        "inference": "Assigned when any effect ambiguity flag has code=effect_fallback_unknown or effect_type=unknown.",
    },
}

MISSION_TAG_CATALOG: dict[str, dict[str, str]] = {
    "mission.objective.win_with_character": {
        "label": "Win With Character",
        "category": "objective",
        "definition": "Mission includes a win_with_character requirement.",
        "inference": "Assigned when any requirement has requirement_type=win_with_character.",
    },
    "mission.objective.streak": {
        "label": "Streak",
        "category": "objective",
        "definition": "Mission includes a streak requirement.",
        "inference": "Assigned when any requirement has requirement_type=streak.",
    },
    "mission.objective.use_skill": {
        "label": "Use Skill",
        "category": "objective",
        "definition": "Mission includes a use_skill requirement.",
        "inference": "Assigned when any requirement has requirement_type=use_skill.",
    },
    "mission.objective.unknown": {
        "label": "Unknown Objective",
        "category": "objective",
        "definition": "Mission still carries an explicit unknown requirement because the detail payload did not reveal objective text.",
        "inference": "Assigned when any requirement has requirement_type=unknown.",
    },
    "mission.objective.named_character_refs": {
        "label": "Named Character Refs",
        "category": "objective",
        "definition": "Mission includes at least one resolved character ref in its requirements.",
        "inference": "Assigned when any requirement includes non-empty character_refs.",
    },
    "mission.objective.named_skill_refs": {
        "label": "Named Skill Refs",
        "category": "objective",
        "definition": "Mission includes at least one resolved skill ref in its requirements.",
        "inference": "Assigned when any requirement includes non-empty skill_refs.",
    },
    "mission.objective.counted_progress": {
        "label": "Counted Progress",
        "category": "objective",
        "definition": "Mission requires a counted number of wins, streaks, or skill uses.",
        "inference": "Assigned when any requirement includes a numeric count.",
    },
    "mission.objective.multi_requirement": {
        "label": "Multi Requirement",
        "category": "objective",
        "definition": "Mission contains more than one normalized requirement entry.",
        "inference": "Assigned when the mission requirements array has length > 1.",
    },
    "mission.data.objective_text_missing": {
        "label": "Objective Text Missing",
        "category": "data_quality",
        "definition": "Mission objective text was unavailable in the captured snapshot.",
        "inference": "Assigned when any requirement ambiguity flag has code=objective_text_missing.",
    },
    "mission.data.detail_payload_redirect": {
        "label": "Detail Payload Redirect",
        "category": "data_quality",
        "definition": "Mission unknown state is supported by a redirect-shaped detail payload.",
        "inference": "Assigned when any requirement ambiguity flag has code=detail_payload_redirect.",
    },
    "mission.data.detail_payload_error_page": {
        "label": "Detail Payload Error Page",
        "category": "data_quality",
        "definition": "Mission unknown state is supported by an error-page detail payload.",
        "inference": "Assigned when any requirement ambiguity flag has code=detail_payload_error_page.",
    },
    "mission.data.detail_payload_unexpected_home": {
        "label": "Detail Payload Unexpected Home",
        "category": "data_quality",
        "definition": "Mission unknown state is supported by an unexpected-home fallback payload.",
        "inference": "Assigned when any requirement ambiguity flag has code=detail_payload_unexpected_home.",
    },
    "mission.data.character_group_not_modeled": {
        "label": "Character Group Not Modeled",
        "category": "data_quality",
        "definition": "Mission objective refers to a character group that is still preserved only in free text.",
        "inference": "Assigned when any requirement ambiguity flag has code=character_group_not_modeled.",
    },
    "mission.data.multi_character_condition_not_structured": {
        "label": "Multi Character Condition Not Structured",
        "category": "data_quality",
        "definition": "Mission objective contains a compound character condition that stays only in free text.",
        "inference": "Assigned when any requirement ambiguity flag has code=multi_character_condition_not_structured.",
    },
    "mission.data.character_subject_not_resolved": {
        "label": "Character Subject Not Resolved",
        "category": "data_quality",
        "definition": "Mission objective names a character subject that could not be resolved into a normalized character ref.",
        "inference": "Assigned when any requirement ambiguity flag has code=character_subject_not_resolved.",
    },
    "mission.data.skill_reference_not_resolved": {
        "label": "Skill Reference Not Resolved",
        "category": "data_quality",
        "definition": "Mission objective names a skill that could not be resolved into a normalized skill ref.",
        "inference": "Assigned when any requirement ambiguity flag has code=skill_reference_not_resolved.",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_array(path: Path, expected: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Expected {expected} file at {path}")
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected {expected} to be a JSON array, found {type(payload).__name__}")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"Expected every {expected} item to be an object")
    return payload


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_tag_evidence(
    tag_evidence: dict[str, list[dict[str, Any]]],
    tag_seen: dict[str, set[str]],
    tag_id: str,
    evidence_key: str,
    evidence: dict[str, Any],
) -> None:
    if tag_id not in tag_seen:
        tag_seen[tag_id] = set()
    if evidence_key in tag_seen[tag_id]:
        return
    tag_seen[tag_id].add(evidence_key)
    tag_evidence.setdefault(tag_id, []).append(evidence)


def build_effect_evidence(skill: dict[str, Any], effect: dict[str, Any], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "skill_id": skill.get("skill_id"),
        "skill_name": skill.get("name"),
        "effect_id": effect.get("effect_id"),
        "effect_type": effect.get("effect_type"),
    }
    payload.update(extra)
    return payload


def build_requirement_evidence(
    requirement: dict[str, Any],
    mission: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mission_id": mission.get("id"),
        "mission_name": mission.get("name"),
        "requirement_id": requirement.get("requirement_id"),
        "requirement_type": requirement.get("requirement_type"),
    }
    payload.update(extra)
    return payload


def validate_registry_coverage(observed: set[str], registry: dict[str, Any], label: str) -> None:
    missing = sorted(observed - set(registry))
    if missing:
        raise ValueError(f"Observed {label} values missing from registry: {missing}")


def effect_target_bucket(effect: dict[str, Any]) -> tuple[str | None, int | None]:
    targeting = effect.get("targeting")
    if not isinstance(targeting, dict):
        return None, None
    target_type = targeting.get("target_type")
    target_count = targeting.get("target_count")
    return target_type if isinstance(target_type, str) else None, target_count if isinstance(target_count, int) else None


def collect_character_metrics(characters: list[dict[str, Any]]) -> dict[str, Any]:
    skill_class_counts: Counter[str] = Counter()
    skill_class_examples: dict[str, list[str]] = {}
    effect_type_counts: Counter[str] = Counter()
    effect_type_examples: dict[str, list[str]] = {}
    condition_type_counts: Counter[str] = Counter()
    condition_type_examples: dict[str, list[str]] = {}
    effect_ambiguity_counts: Counter[str] = Counter()
    effect_ambiguity_examples: dict[str, list[str]] = {}
    skill_count = 0
    effect_count = 0

    for character in characters:
        for skill in character.get("skills", []) or []:
            if not isinstance(skill, dict):
                continue
            skill_count += 1
            skill_id = skill.get("skill_id")
            for skill_class in skill.get("classes", []) or []:
                if not isinstance(skill_class, dict):
                    continue
                class_id = skill_class.get("class_id")
                if not isinstance(class_id, str):
                    continue
                skill_class_counts[class_id] += 1
                skill_class_examples.setdefault(class_id, [])
                if isinstance(skill_id, str) and skill_id not in skill_class_examples[class_id] and len(skill_class_examples[class_id]) < 3:
                    skill_class_examples[class_id].append(skill_id)

            for effect in skill.get("effects", []) or []:
                if not isinstance(effect, dict):
                    continue
                effect_count += 1
                effect_id = effect.get("effect_id")
                effect_type = effect.get("effect_type")
                if isinstance(effect_type, str):
                    effect_type_counts[effect_type] += 1
                    effect_type_examples.setdefault(effect_type, [])
                    if isinstance(effect_id, str) and effect_id not in effect_type_examples[effect_type] and len(effect_type_examples[effect_type]) < 3:
                        effect_type_examples[effect_type].append(effect_id)

                for condition in effect.get("conditions", []) or []:
                    if not isinstance(condition, dict):
                        continue
                    condition_type = condition.get("condition_type")
                    if not isinstance(condition_type, str):
                        continue
                    condition_type_counts[condition_type] += 1
                    condition_type_examples.setdefault(condition_type, [])
                    if isinstance(skill_id, str) and skill_id not in condition_type_examples[condition_type] and len(condition_type_examples[condition_type]) < 3:
                        condition_type_examples[condition_type].append(skill_id)

                for ambiguity_flag in effect.get("ambiguity_flags", []) or []:
                    if not isinstance(ambiguity_flag, dict):
                        continue
                    code = ambiguity_flag.get("code")
                    if not isinstance(code, str):
                        continue
                    effect_ambiguity_counts[code] += 1
                    effect_ambiguity_examples.setdefault(code, [])
                    if isinstance(effect_id, str) and effect_id not in effect_ambiguity_examples[code] and len(effect_ambiguity_examples[code]) < 3:
                        effect_ambiguity_examples[code].append(effect_id)

    return {
        "skill_class_counts": skill_class_counts,
        "skill_class_examples": skill_class_examples,
        "effect_type_counts": effect_type_counts,
        "effect_type_examples": effect_type_examples,
        "condition_type_counts": condition_type_counts,
        "condition_type_examples": condition_type_examples,
        "effect_ambiguity_counts": effect_ambiguity_counts,
        "effect_ambiguity_examples": effect_ambiguity_examples,
        "skill_count": skill_count,
        "effect_count": effect_count,
    }


def collect_mission_metrics(missions: list[dict[str, Any]]) -> dict[str, Any]:
    requirement_type_counts: Counter[str] = Counter()
    requirement_type_examples: dict[str, list[str]] = {}
    mission_ambiguity_counts: Counter[str] = Counter()
    mission_ambiguity_examples: dict[str, list[str]] = {}
    requirement_count = 0

    for mission in missions:
        for requirement in mission.get("requirements", []) or []:
            if not isinstance(requirement, dict):
                continue
            requirement_count += 1
            requirement_id = requirement.get("requirement_id")
            requirement_type = requirement.get("requirement_type")
            if isinstance(requirement_type, str):
                requirement_type_counts[requirement_type] += 1
                requirement_type_examples.setdefault(requirement_type, [])
                if isinstance(requirement_id, str) and requirement_id not in requirement_type_examples[requirement_type] and len(requirement_type_examples[requirement_type]) < 3:
                    requirement_type_examples[requirement_type].append(requirement_id)

            for ambiguity_flag in requirement.get("ambiguity_flags", []) or []:
                if not isinstance(ambiguity_flag, dict):
                    continue
                code = ambiguity_flag.get("code")
                if not isinstance(code, str):
                    continue
                mission_ambiguity_counts[code] += 1
                mission_ambiguity_examples.setdefault(code, [])
                if isinstance(requirement_id, str) and requirement_id not in mission_ambiguity_examples[code] and len(mission_ambiguity_examples[code]) < 3:
                    mission_ambiguity_examples[code].append(requirement_id)

    return {
        "requirement_type_counts": requirement_type_counts,
        "requirement_type_examples": requirement_type_examples,
        "mission_ambiguity_counts": mission_ambiguity_counts,
        "mission_ambiguity_examples": mission_ambiguity_examples,
        "requirement_count": requirement_count,
    }


def build_effect_taxonomy(
    characters: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    characters_path: Path,
    missions_path: Path,
) -> dict[str, Any]:
    character_metrics = collect_character_metrics(characters)
    mission_metrics = collect_mission_metrics(missions)

    validate_registry_coverage(set(character_metrics["skill_class_counts"]), SKILL_CLASS_DEFINITIONS, "skill class")
    validate_registry_coverage(set(character_metrics["effect_type_counts"]), EFFECT_TYPE_DEFINITIONS, "effect_type")
    validate_registry_coverage(set(character_metrics["condition_type_counts"]), CONDITION_TYPE_DEFINITIONS, "condition_type")
    validate_registry_coverage(
        set(mission_metrics["requirement_type_counts"]),
        MISSION_REQUIREMENT_TYPE_DEFINITIONS,
        "mission requirement_type",
    )
    validate_registry_coverage(
        set(character_metrics["effect_ambiguity_counts"]),
        EFFECT_AMBIGUITY_DEFINITIONS,
        "effect ambiguity code",
    )
    validate_registry_coverage(
        set(mission_metrics["mission_ambiguity_counts"]),
        MISSION_AMBIGUITY_DEFINITIONS,
        "mission ambiguity code",
    )

    effect_family_counts: Counter[str] = Counter()
    for effect_type, count in character_metrics["effect_type_counts"].items():
        effect_family_counts[EFFECT_TYPE_DEFINITIONS[effect_type]["family_id"]] += count

    skill_classes = [
        {
            "class_id": class_id,
            "label": definition["label"],
            "definition": definition["definition"],
            "observed_skill_count": character_metrics["skill_class_counts"].get(class_id, 0),
            "sample_skill_ids": character_metrics["skill_class_examples"].get(class_id, []),
        }
        for class_id, definition in SKILL_CLASS_DEFINITIONS.items()
    ]

    effect_types = [
        {
            "effect_type": effect_type,
            "family_id": definition["family_id"],
            "label": definition["label"],
            "definition": definition["definition"],
            "inference_notes": definition["inference_notes"],
            "observed_effect_count": character_metrics["effect_type_counts"].get(effect_type, 0),
            "sample_effect_ids": character_metrics["effect_type_examples"].get(effect_type, []),
            "tag_hooks": definition["tag_hooks"],
        }
        for effect_type, definition in EFFECT_TYPE_DEFINITIONS.items()
    ]

    condition_types = [
        {
            "condition_type": condition_type,
            "label": definition["label"],
            "definition": definition["definition"],
            "observed_condition_count": character_metrics["condition_type_counts"].get(condition_type, 0),
            "sample_skill_ids": character_metrics["condition_type_examples"].get(condition_type, []),
            "tag_hooks": definition["tag_hooks"],
        }
        for condition_type, definition in CONDITION_TYPE_DEFINITIONS.items()
    ]

    mission_requirement_types = [
        {
            "requirement_type": requirement_type,
            "label": definition["label"],
            "definition": definition["definition"],
            "observed_requirement_count": mission_metrics["requirement_type_counts"].get(requirement_type, 0),
            "sample_requirement_ids": mission_metrics["requirement_type_examples"].get(requirement_type, []),
            "tag_hooks": definition["tag_hooks"],
        }
        for requirement_type, definition in MISSION_REQUIREMENT_TYPE_DEFINITIONS.items()
    ]

    return {
        "artifact": "effect_taxonomy",
        "taxonomy_version": TAXONOMY_VERSION,
        "generated_at": iso_now(),
        "source_inputs": {
            "characters_path": repo_relative(characters_path),
            "missions_path": repo_relative(missions_path),
        },
        "summary": {
            "character_count": len(characters),
            "mission_count": len(missions),
            "skill_count": character_metrics["skill_count"],
            "effect_count": character_metrics["effect_count"],
            "requirement_count": mission_metrics["requirement_count"],
        },
        "effect_families": [
            {
                "family_id": family_id,
                "label": definition["label"],
                "definition": definition["definition"],
                "observed_effect_count": effect_family_counts.get(family_id, 0),
            }
            for family_id, definition in EFFECT_FAMILY_DEFINITIONS.items()
        ],
        "skill_classes": skill_classes,
        "effect_types": effect_types,
        "condition_types": condition_types,
        "mission_requirement_types": mission_requirement_types,
        "ambiguity_codes": {
            "effect": [
                {
                    "code": code,
                    "label": definition["label"],
                    "definition": definition["definition"],
                    "observed_count": character_metrics["effect_ambiguity_counts"].get(code, 0),
                    "sample_effect_ids": character_metrics["effect_ambiguity_examples"].get(code, []),
                    "tag_hooks": definition["tag_hooks"],
                }
                for code, definition in EFFECT_AMBIGUITY_DEFINITIONS.items()
            ],
            "mission": [
                {
                    "code": code,
                    "label": definition["label"],
                    "definition": definition["definition"],
                    "observed_count": mission_metrics["mission_ambiguity_counts"].get(code, 0),
                    "sample_requirement_ids": mission_metrics["mission_ambiguity_examples"].get(code, []),
                    "tag_hooks": definition["tag_hooks"],
                }
                for code, definition in MISSION_AMBIGUITY_DEFINITIONS.items()
            ],
        },
    }


def infer_character_tags(characters: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    record_outputs: list[dict[str, Any]] = []
    tag_counts: Counter[str] = Counter()

    for character in characters:
        tag_evidence: dict[str, list[dict[str, Any]]] = {}
        tag_seen: dict[str, set[str]] = {}

        for skill in character.get("skills", []) or []:
            if not isinstance(skill, dict):
                continue
            skill_id = skill.get("skill_id")
            skill_name = skill.get("name")
            for effect in skill.get("effects", []) or []:
                if not isinstance(effect, dict):
                    continue
                effect_id = effect.get("effect_id")
                effect_type = effect.get("effect_type")
                target_type, target_count = effect_target_bucket(effect)

                if effect_type == "damage":
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.damage_effects",
                        str(effect_id),
                        build_effect_evidence(skill, effect),
                    )
                    if target_type == "enemy" and target_count == 1:
                        add_tag_evidence(
                            tag_evidence,
                            tag_seen,
                            "character.capability.damage_single_target",
                            str(effect_id),
                            build_effect_evidence(skill, effect, target_type=target_type, target_count=target_count),
                        )
                    if target_type == "all_enemies":
                        add_tag_evidence(
                            tag_evidence,
                            tag_seen,
                            "character.capability.damage_aoe",
                            str(effect_id),
                            build_effect_evidence(skill, effect, target_type=target_type),
                        )

                if effect_type == "increase_damage":
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.damage_amplification",
                        str(effect_id),
                        build_effect_evidence(skill, effect),
                    )

                if effect_type == "protect":
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.protect_effects",
                        str(effect_id),
                        build_effect_evidence(skill, effect),
                    )

                if effect_type == "reduce_damage":
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.damage_reduction",
                        str(effect_id),
                        build_effect_evidence(skill, effect),
                    )

                if effect_type in {"protect", "reduce_damage"} and target_type == "self":
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.self_protection",
                        str(effect_id),
                        build_effect_evidence(skill, effect, target_type=target_type),
                    )

                if effect_type in {"protect", "reduce_damage"} and target_type in {"ally", "all_allies", "any"}:
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        "character.capability.ally_protection",
                        str(effect_id),
                        build_effect_evidence(skill, effect, target_type=target_type),
                    )

                effect_to_tag = {
                    "stun": "character.capability.stun_effects",
                    "heal": "character.capability.heal_effects",
                    "apply_state": "character.capability.state_application",
                    "remove_state": "character.capability.removal_effects",
                    "gain": "character.capability.gain_effects",
                    "drain": "character.capability.drain_effects",
                    "conditional": "character.capability.conditional_effects",
                    "unknown": "character.data.effect_fallback_unknown",
                }
                tag_id = effect_to_tag.get(effect_type)
                if tag_id:
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        tag_id,
                        str(effect_id),
                        build_effect_evidence(skill, effect),
                    )

                for condition in effect.get("conditions", []) or []:
                    if not isinstance(condition, dict):
                        continue
                    condition_type = condition.get("condition_type")
                    if condition_type == "previous_skill":
                        add_tag_evidence(
                            tag_evidence,
                            tag_seen,
                            "character.capability.combo_dependency",
                            f"{skill_id}:previous_skill:{condition.get('raw_text')}",
                            {
                                "skill_id": skill_id,
                                "skill_name": skill_name,
                                "condition_type": condition_type,
                                "normalized_ref": condition.get("normalized_ref"),
                                "raw_text": condition.get("raw_text"),
                            },
                        )
                    if condition_type == "requires_state":
                        add_tag_evidence(
                            tag_evidence,
                            tag_seen,
                            "character.capability.state_dependency",
                            f"{skill_id}:requires_state:{condition.get('raw_text')}",
                            {
                                "skill_id": skill_id,
                                "skill_name": skill_name,
                                "condition_type": condition_type,
                                "normalized_ref": condition.get("normalized_ref"),
                                "raw_text": condition.get("raw_text"),
                            },
                        )

                for ambiguity_flag in effect.get("ambiguity_flags", []) or []:
                    if not isinstance(ambiguity_flag, dict):
                        continue
                    code = ambiguity_flag.get("code")
                    ambiguity_to_tag = {
                        "effect_target_unknown": "character.data.effect_target_unknown",
                        "effect_type_heuristic": "character.data.effect_type_heuristic",
                        "effect_magnitude_unknown": "character.data.effect_magnitude_unknown",
                        "effect_fallback_unknown": "character.data.effect_fallback_unknown",
                    }
                    ambiguity_tag = ambiguity_to_tag.get(code)
                    if not ambiguity_tag:
                        continue
                    add_tag_evidence(
                        tag_evidence,
                        tag_seen,
                        ambiguity_tag,
                        f"{effect_id}:{code}",
                        build_effect_evidence(skill, effect, ambiguity_code=code),
                    )

        tags = [
            {
                "tag_id": tag_id,
                "evidence_count": len(evidence_list),
                "evidence": evidence_list,
            }
            for tag_id, evidence_list in sorted(tag_evidence.items())
        ]
        for tag_id in tag_evidence:
            tag_counts[tag_id] += 1
        record_outputs.append(
            {
                "record_id": character.get("id"),
                "name": character.get("name"),
                "tag_count": len(tags),
                "tags": tags,
            }
        )

    return record_outputs, tag_counts


def infer_mission_tags(missions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    record_outputs: list[dict[str, Any]] = []
    tag_counts: Counter[str] = Counter()

    for mission in missions:
        tag_evidence: dict[str, list[dict[str, Any]]] = {}
        tag_seen: dict[str, set[str]] = {}
        requirements = [requirement for requirement in mission.get("requirements", []) or [] if isinstance(requirement, dict)]

        if len(requirements) > 1:
            add_tag_evidence(
                tag_evidence,
                tag_seen,
                "mission.objective.multi_requirement",
                str(mission.get("id")),
                {
                    "mission_id": mission.get("id"),
                    "mission_name": mission.get("name"),
                    "requirement_count": len(requirements),
                },
            )

        for requirement in requirements:
            requirement_id = requirement.get("requirement_id")
            requirement_type = requirement.get("requirement_type")
            requirement_to_tag = {
                "win_with_character": "mission.objective.win_with_character",
                "streak": "mission.objective.streak",
                "use_skill": "mission.objective.use_skill",
                "unknown": "mission.objective.unknown",
            }
            direct_tag = requirement_to_tag.get(requirement_type)
            if direct_tag:
                add_tag_evidence(
                    tag_evidence,
                    tag_seen,
                    direct_tag,
                    str(requirement_id),
                    build_requirement_evidence(requirement, mission),
                )

            character_refs = requirement.get("character_refs")
            if isinstance(character_refs, list) and any(isinstance(item, str) and item for item in character_refs):
                add_tag_evidence(
                    tag_evidence,
                    tag_seen,
                    "mission.objective.named_character_refs",
                    str(requirement_id),
                    build_requirement_evidence(requirement, mission, character_refs=character_refs),
                )

            skill_refs = requirement.get("skill_refs")
            if isinstance(skill_refs, list) and any(isinstance(item, str) and item for item in skill_refs):
                add_tag_evidence(
                    tag_evidence,
                    tag_seen,
                    "mission.objective.named_skill_refs",
                    str(requirement_id),
                    build_requirement_evidence(requirement, mission, skill_refs=skill_refs),
                )

            count = requirement.get("count")
            if isinstance(count, int):
                add_tag_evidence(
                    tag_evidence,
                    tag_seen,
                    "mission.objective.counted_progress",
                    str(requirement_id),
                    build_requirement_evidence(requirement, mission, count=count),
                )

            for ambiguity_flag in requirement.get("ambiguity_flags", []) or []:
                if not isinstance(ambiguity_flag, dict):
                    continue
                code = ambiguity_flag.get("code")
                ambiguity_to_tag = {
                    "objective_text_missing": "mission.data.objective_text_missing",
                    "detail_payload_redirect": "mission.data.detail_payload_redirect",
                    "detail_payload_error_page": "mission.data.detail_payload_error_page",
                    "detail_payload_unexpected_home": "mission.data.detail_payload_unexpected_home",
                    "character_group_not_modeled": "mission.data.character_group_not_modeled",
                    "multi_character_condition_not_structured": "mission.data.multi_character_condition_not_structured",
                    "character_subject_not_resolved": "mission.data.character_subject_not_resolved",
                    "skill_reference_not_resolved": "mission.data.skill_reference_not_resolved",
                }
                tag_id = ambiguity_to_tag.get(code)
                if not tag_id:
                    continue
                add_tag_evidence(
                    tag_evidence,
                    tag_seen,
                    tag_id,
                    f"{requirement_id}:{code}",
                    build_requirement_evidence(requirement, mission, ambiguity_code=code),
                )

        tags = [
            {
                "tag_id": tag_id,
                "evidence_count": len(evidence_list),
                "evidence": evidence_list,
            }
            for tag_id, evidence_list in sorted(tag_evidence.items())
        ]
        for tag_id in tag_evidence:
            tag_counts[tag_id] += 1
        record_outputs.append(
            {
                "record_id": mission.get("id"),
                "name": mission.get("name"),
                "tag_count": len(tags),
                "tags": tags,
            }
        )

    return record_outputs, tag_counts


def build_tag_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "character": [
            {
                "tag_id": tag_id,
                **definition,
            }
            for tag_id, definition in CHARACTER_TAG_CATALOG.items()
        ],
        "mission": [
            {
                "tag_id": tag_id,
                **definition,
            }
            for tag_id, definition in MISSION_TAG_CATALOG.items()
        ],
    }


def build_tags_payload(
    characters: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    characters_path: Path,
    missions_path: Path,
) -> dict[str, Any]:
    character_tags, character_tag_counts = infer_character_tags(characters)
    mission_tags, mission_tag_counts = infer_mission_tags(missions)

    character_tagged_records = sum(1 for record in character_tags if record["tag_count"] > 0)
    mission_tagged_records = sum(1 for record in mission_tags if record["tag_count"] > 0)

    return {
        "artifact": "tags",
        "taxonomy_version": TAXONOMY_VERSION,
        "generated_at": iso_now(),
        "source_inputs": {
            "characters_path": repo_relative(characters_path),
            "missions_path": repo_relative(missions_path),
        },
        "summary": {
            "character_record_count": len(characters),
            "mission_record_count": len(missions),
            "character_tagged_record_count": character_tagged_records,
            "mission_tagged_record_count": mission_tagged_records,
            "character_tag_counts": dict(sorted(character_tag_counts.items())),
            "mission_tag_counts": dict(sorted(mission_tag_counts.items())),
        },
        "tag_catalog": build_tag_catalog(),
        "character_tags": character_tags,
        "mission_tags": mission_tags,
    }


def build_stdout_summary(
    taxonomy_path: Path,
    tags_path: Path,
    taxonomy_payload: dict[str, Any],
    tags_payload: dict[str, Any],
) -> dict[str, Any]:
    character_tag_counts = Counter(tags_payload["summary"]["character_tag_counts"])
    mission_tag_counts = Counter(tags_payload["summary"]["mission_tag_counts"])
    return {
        "status": "ok",
        "taxonomy_output": repo_relative(taxonomy_path),
        "tags_output": repo_relative(tags_path),
        "summary": {
            "character_count": taxonomy_payload["summary"]["character_count"],
            "mission_count": taxonomy_payload["summary"]["mission_count"],
            "skill_count": taxonomy_payload["summary"]["skill_count"],
            "effect_count": taxonomy_payload["summary"]["effect_count"],
            "requirement_count": taxonomy_payload["summary"]["requirement_count"],
            "character_tagged_record_count": tags_payload["summary"]["character_tagged_record_count"],
            "mission_tagged_record_count": tags_payload["summary"]["mission_tagged_record_count"],
            "top_character_tags": character_tag_counts.most_common(8),
            "top_mission_tags": mission_tag_counts.most_common(8),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate project-owned effect taxonomy and record-level tag assignments from normalized Naruto Arena data."
    )
    parser.add_argument("--characters", type=Path, default=DEFAULT_CHARACTERS_PATH, help="Path to characters.json")
    parser.add_argument("--missions", type=Path, default=DEFAULT_MISSIONS_PATH, help="Path to missions.json")
    parser.add_argument(
        "--taxonomy-out",
        type=Path,
        default=DEFAULT_TAXONOMY_PATH,
        help="Output path for references/effect-taxonomy.json",
    )
    parser.add_argument(
        "--tags-out",
        type=Path,
        default=DEFAULT_TAGS_PATH,
        help="Output path for references/tags.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    characters_path = args.characters.resolve()
    missions_path = args.missions.resolve()
    taxonomy_out = args.taxonomy_out.resolve()
    tags_out = args.tags_out.resolve()

    characters = require_array(characters_path, "normalized character bundle")
    missions = require_array(missions_path, "normalized mission bundle")

    taxonomy_payload = build_effect_taxonomy(characters, missions, characters_path, missions_path)
    tags_payload = build_tags_payload(characters, missions, characters_path, missions_path)

    write_json(taxonomy_out, taxonomy_payload)
    write_json(tags_out, tags_payload)

    print(json.dumps(build_stdout_summary(taxonomy_out, tags_out, taxonomy_payload, tags_payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

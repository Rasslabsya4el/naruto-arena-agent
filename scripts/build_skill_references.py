#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SOURCE = "https://www.naruto-arena.site/"
BUNDLE_VERSION = "skill-reference-bundle-v1"

DEFAULT_CHARACTERS_PATH = REPO_ROOT / "data" / "normalized" / "characters.json"
DEFAULT_MISSIONS_PATH = REPO_ROOT / "data" / "normalized" / "missions.json"
DEFAULT_TAGS_PATH = REPO_ROOT / "references" / "tags.json"
DEFAULT_EFFECT_TAXONOMY_PATH = REPO_ROOT / "references" / "effect-taxonomy.json"
DEFAULT_CHARACTER_VALIDATION_RESULT = (
    REPO_ROOT / ".orchestrator" / "tasks" / "TASK-EXTRACT-CHARACTERS-VALIDATE-01" / "RESULT.txt"
)
DEFAULT_MISSION_VALIDATION_RESULT = (
    REPO_ROOT / ".orchestrator" / "tasks" / "TASK-EXTRACT-MISSIONS-VALIDATE-01" / "RESULT.txt"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "skills" / "naruto-arena-team-builder" / "references"

BROAD_EFFECT_TYPES = ("protect", "apply_state", "remove_state", "gain", "drain")
EXPECTED_OUTPUTS = (
    "rules.md",
    "characters.json",
    "missions.json",
    "tags.json",
    "effect-taxonomy.json",
    "source-map.json",
    "data-quality-report.md",
)


def require_file(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ValueError(f"Expected {expected} file at {path}")


def load_json(path: Path) -> Any:
    require_file(path, "JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, expected: str) -> str:
    require_file(path, expected)
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_json_list(text: str, prefix: str, suffix: str) -> list[str]:
    pattern = re.compile(re.escape(prefix) + r"(\[[^\]]*\])" + re.escape(suffix))
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Could not parse list between {prefix!r} and {suffix!r}")
    payload = json.loads(match.group(1))
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError(f"Expected string list for {prefix!r}")
    return payload


def extract_int(text: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}=(\d+)", text)
    if match is None:
        raise ValueError(f"Could not parse integer field {label!r}")
    return int(match.group(1))


def extract_detail_state_counts(text: str) -> dict[str, int]:
    match = re.search(r"detail_state_counts=\{([^}]*)\}", text)
    if match is None:
        raise ValueError("Could not parse detail_state_counts")
    counts: dict[str, int] = {}
    for chunk in match.group(1).split(","):
        key, _, raw_value = chunk.strip().partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or not raw_value.isdigit():
            raise ValueError(f"Invalid detail_state_counts entry: {chunk!r}")
        counts[key] = int(raw_value)
    return counts


def parse_character_validation_result(path: Path) -> dict[str, Any]:
    text = read_text(path, "character validation result")
    return {
        "included_record_count": extract_int(text, "included_record_count"),
        "raw_record_count": extract_int(text, "raw_record_count"),
        "excluded_raw_names": extract_json_list(text, "excluded_raw_names=", ", silent_drops="),
        "silent_drops": extract_json_list(text, "silent_drops=", ", unexpected_included_names="),
        "unexpected_included_names": extract_json_list(
            text,
            "unexpected_included_names=",
            ", duplicate_raw_names=",
        ),
        "duplicate_raw_names": extract_json_list(text, "duplicate_raw_names=", ", duplicate_normalized_names="),
        "duplicate_normalized_names": extract_json_list(
            text,
            "duplicate_normalized_names=",
            ", and all included record/source/raw-text checks true.",
        ),
        "result_file": repo_rel(path),
        "sha256": sha256_file(path),
    }


def parse_mission_validation_result(path: Path) -> dict[str, Any]:
    text = read_text(path, "mission validation result")
    return {
        "included_record_count": extract_int(text, "included_record_count"),
        "manifest_detail_count": extract_int(text, "manifest_detail_count"),
        "group_item_count": extract_int(text, "group_item_count"),
        "detail_file_count": extract_int(text, "detail_file_count"),
        "detail_state_counts": extract_detail_state_counts(text),
        "unknown_requirement_record_count": extract_int(text, "unknown_requirement_record_count"),
        "supported_unknown_requirement_count": extract_int(text, "supported_unknown_requirement_count"),
        "missing_level_requirement_count": extract_int(text, "missing_level_requirement_count"),
        "silent_drops": extract_int(text, "silent_drops"),
        "unexpected_included_records": extract_int(text, "unexpected_included_records"),
        "result_file": repo_rel(path),
        "sha256": sha256_file(path),
    }


def extract_source_ref_ids(source_refs: Any) -> list[str]:
    if not isinstance(source_refs, list):
        raise ValueError("Expected source_refs to be a list")
    source_ids: list[str] = []
    for source_ref in source_refs:
        if not isinstance(source_ref, dict):
            raise ValueError("Expected every source_ref to be an object")
        source_id = source_ref.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Expected every source_ref to include a non-empty source_id")
        source_ids.append(source_id)
    return source_ids


def register_source_refs(source_refs_by_id: dict[str, dict[str, Any]], source_refs: Any) -> list[str]:
    source_ids = extract_source_ref_ids(source_refs)
    for source_ref in source_refs:
        source_id = source_ref["source_id"]
        existing = source_refs_by_id.get(source_id)
        if existing is None:
            source_refs_by_id[source_id] = deepcopy(source_ref)
            continue
        if existing != source_ref:
            raise ValueError(f"Conflicting source_ref payloads found for {source_id}")
    return source_ids


def build_tag_category_map(tags_payload: dict[str, Any], scope: str) -> dict[str, str]:
    catalog = tags_payload.get("tag_catalog", {}).get(scope)
    if not isinstance(catalog, list):
        raise ValueError(f"Expected tag_catalog.{scope} to be a list")
    category_by_tag_id: dict[str, str] = {}
    for item in catalog:
        if not isinstance(item, dict):
            raise ValueError(f"Expected every {scope} tag catalog entry to be an object")
        tag_id = item.get("tag_id")
        category = item.get("category")
        if not isinstance(tag_id, str) or not tag_id.strip() or not isinstance(category, str) or not category.strip():
            raise ValueError(f"Invalid {scope} tag catalog entry: {item!r}")
        category_by_tag_id[tag_id] = category
    return category_by_tag_id


def build_record_tag_map(
    tag_records: Any,
    category_by_tag_id: dict[str, str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(tag_records, list):
        raise ValueError("Expected tag records to be a list")

    tag_map: dict[str, dict[str, Any]] = {}
    for entry in tag_records:
        if not isinstance(entry, dict):
            raise ValueError("Expected every tag record entry to be an object")
        record_id = entry.get("record_id")
        tags = entry.get("tags")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("Expected every tag record entry to include a non-empty record_id")
        if not isinstance(tags, list):
            raise ValueError(f"Expected tag record {record_id} to contain a tags list")

        tag_ids: list[str] = []
        data_quality_tag_ids: list[str] = []
        tag_evidence_counts: dict[str, int] = {}

        for tag in tags:
            if not isinstance(tag, dict):
                raise ValueError(f"Expected tag entry for {record_id} to be an object")
            tag_id = tag.get("tag_id")
            evidence_count = tag.get("evidence_count")
            if not isinstance(tag_id, str) or not tag_id.strip():
                raise ValueError(f"Expected tag entry for {record_id} to include a non-empty tag_id")
            if not isinstance(evidence_count, int) or evidence_count < 0:
                raise ValueError(f"Expected tag entry {tag_id} for {record_id} to include a non-negative evidence_count")
            tag_ids.append(tag_id)
            tag_evidence_counts[tag_id] = evidence_count
            if category_by_tag_id.get(tag_id) == "data_quality":
                data_quality_tag_ids.append(tag_id)

        tag_map[record_id] = {
            "tag_ids": sorted(tag_ids),
            "data_quality_tag_ids": sorted(data_quality_tag_ids),
            "tag_evidence_counts": {
                tag_id: tag_evidence_counts[tag_id]
                for tag_id in sorted(tag_evidence_counts)
            },
        }

    return tag_map


def normalize_character_records(
    characters: list[dict[str, Any]],
    tag_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for character in characters:
        record = deepcopy(character)
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("Expected every character record to include a non-empty id")
        tag_info = tag_map.get(record_id)
        if tag_info is None:
            raise ValueError(f"Missing tag entry for character record {record_id}")

        record["source_ref_ids"] = extract_source_ref_ids(record.pop("source_refs"))
        record["tag_ids"] = tag_info["tag_ids"]
        record["data_quality_tag_ids"] = tag_info["data_quality_tag_ids"]
        record["tag_evidence_counts"] = tag_info["tag_evidence_counts"]

        skills = record.get("skills")
        if not isinstance(skills, list):
            raise ValueError(f"Expected character {record_id} skills to be a list")
        for skill in skills:
            if not isinstance(skill, dict):
                raise ValueError(f"Expected character {record_id} skills to contain only objects")
            skill["source_ref_ids"] = extract_source_ref_ids(skill.pop("source_refs"))

        records.append(record)
    return records


def normalize_mission_records(
    missions: list[dict[str, Any]],
    tag_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for mission in missions:
        record = deepcopy(mission)
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("Expected every mission record to include a non-empty id")
        tag_info = tag_map.get(record_id)
        if tag_info is None:
            raise ValueError(f"Missing tag entry for mission record {record_id}")

        record["source_ref_ids"] = extract_source_ref_ids(record.pop("source_refs"))
        record["tag_ids"] = tag_info["tag_ids"]
        record["data_quality_tag_ids"] = tag_info["data_quality_tag_ids"]
        record["tag_evidence_counts"] = tag_info["tag_evidence_counts"]
        records.append(record)
    return records


def build_source_map(
    characters: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    source_inputs: dict[str, dict[str, str]],
    output_dir: Path,
    character_validation: dict[str, Any],
    mission_validation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    source_refs_by_id: dict[str, dict[str, Any]] = {}
    record_index: dict[str, dict[str, Any]] = {}

    for character in characters:
        record_id = character.get("id")
        name = character.get("name")
        if not isinstance(record_id, str) or not isinstance(name, str):
            raise ValueError("Invalid character record while building source map")
        record_source_ref_ids = register_source_refs(source_refs_by_id, character.get("source_refs"))
        skill_index: dict[str, dict[str, Any]] = {}
        for skill in character.get("skills", []):
            if not isinstance(skill, dict):
                raise ValueError(f"Expected skills for {record_id} to contain only objects")
            skill_id = skill.get("skill_id")
            skill_name = skill.get("name")
            if not isinstance(skill_id, str) or not isinstance(skill_name, str):
                raise ValueError(f"Invalid skill record under {record_id}")
            skill_index[skill_id] = {
                "name": skill_name,
                "source_ref_ids": register_source_refs(source_refs_by_id, skill.get("source_refs")),
            }

        record_index[record_id] = {
            "record_type": "character",
            "name": name,
            "artifact_path": repo_rel(output_dir / "characters.json"),
            "source_ref_ids": record_source_ref_ids,
            "child_records": skill_index,
        }

    for mission in missions:
        record_id = mission.get("id")
        name = mission.get("name")
        if not isinstance(record_id, str) or not isinstance(name, str):
            raise ValueError("Invalid mission record while building source map")
        record_index[record_id] = {
            "record_type": "mission",
            "name": name,
            "artifact_path": repo_rel(output_dir / "missions.json"),
            "source_ref_ids": register_source_refs(source_refs_by_id, mission.get("source_refs")),
        }

    excluded_names = character_validation["excluded_raw_names"]
    detail_state_counts = mission_validation["detail_state_counts"]

    return {
        "artifact": "source_map",
        "bundle_version": BUNDLE_VERSION,
        "generated_at": generated_at,
        "canonical_source": CANONICAL_SOURCE,
        "source_inputs": source_inputs,
        "output_artifacts": {
            name: repo_rel(output_dir / name)
            for name in EXPECTED_OUTPUTS
        },
        "accepted_validation_facts": {
            "excluded_disabled_zero_skill_characters": excluded_names,
            "unknown_mission_objective_record_count": mission_validation["unknown_requirement_record_count"],
            "unknown_mission_detail_state_counts": detail_state_counts,
        },
        "summary": {
            "character_record_count": len(characters),
            "mission_record_count": len(missions),
            "source_ref_count": len(source_refs_by_id),
            "excluded_disabled_zero_skill_character_count": len(excluded_names),
            "unknown_mission_objective_record_count": mission_validation["unknown_requirement_record_count"],
        },
        "record_index": {
            record_id: record_index[record_id]
            for record_id in sorted(record_index)
        },
        "source_refs_by_id": {
            source_id: source_refs_by_id[source_id]
            for source_id in sorted(source_refs_by_id)
        },
    }


def count_skill_total(characters: list[dict[str, Any]]) -> int:
    return sum(len(character.get("skills", [])) for character in characters if isinstance(character.get("skills"), list))


def count_unknown_mission_records(missions: list[dict[str, Any]]) -> int:
    return sum(
        1
        for mission in missions
        if isinstance(mission.get("requirements"), list)
        and any(
            isinstance(requirement, dict) and requirement.get("requirement_type") == "unknown"
            for requirement in mission["requirements"]
        )
    )


def validate_input_consistency(
    characters: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    tags_payload: dict[str, Any],
    effect_taxonomy_payload: dict[str, Any],
    character_validation: dict[str, Any],
    mission_validation: dict[str, Any],
) -> None:
    taxonomy_summary = effect_taxonomy_payload.get("summary")
    tag_summary = tags_payload.get("summary")
    if not isinstance(taxonomy_summary, dict) or not isinstance(tag_summary, dict):
        raise ValueError("Expected both effect taxonomy and tags payloads to contain summary objects")

    character_count = len(characters)
    mission_count = len(missions)
    skill_count = count_skill_total(characters)
    unknown_mission_records = count_unknown_mission_records(missions)

    checks = {
        "character_count_matches_taxonomy": character_count == taxonomy_summary.get("character_count"),
        "mission_count_matches_taxonomy": mission_count == taxonomy_summary.get("mission_count"),
        "skill_count_matches_taxonomy": skill_count == taxonomy_summary.get("skill_count"),
        "character_count_matches_tags": character_count == tag_summary.get("character_record_count"),
        "mission_count_matches_tags": mission_count == tag_summary.get("mission_record_count"),
        "character_count_matches_character_validation": character_count == character_validation["included_record_count"],
        "mission_count_matches_mission_validation": mission_count == mission_validation["included_record_count"],
        "mission_unknown_count_matches_validation": unknown_mission_records
        == mission_validation["unknown_requirement_record_count"],
        "mission_unknown_count_matches_tags": unknown_mission_records
        == tag_summary.get("mission_tag_counts", {}).get("mission.objective.unknown"),
        "no_character_silent_drops": not character_validation["silent_drops"],
        "no_character_unexpected_included_names": not character_validation["unexpected_included_names"],
        "no_character_duplicate_raw_names": not character_validation["duplicate_raw_names"],
        "no_character_duplicate_normalized_names": not character_validation["duplicate_normalized_names"],
        "mission_validator_has_no_silent_drops": mission_validation["silent_drops"] == 0,
        "mission_validator_has_no_unexpected_included_records": mission_validation["unexpected_included_records"] == 0,
        "mission_validator_has_no_missing_level_requirement": mission_validation["missing_level_requirement_count"] == 0,
        "mission_unknown_detail_states_sum": sum(
            count
            for state, count in mission_validation["detail_state_counts"].items()
            if state != "mission_status"
        )
        == mission_validation["unknown_requirement_record_count"],
    }

    failing = [name for name, ok in checks.items() if not ok]
    if failing:
        raise ValueError(f"Input consistency checks failed: {', '.join(failing)}")


def build_source_input_summary(paths: dict[str, Path]) -> dict[str, dict[str, str]]:
    return {
        label: {
            "path": repo_rel(path),
            "sha256": sha256_file(path),
        }
        for label, path in paths.items()
    }


def build_character_bundle(
    characters: list[dict[str, Any]],
    character_records: list[dict[str, Any]],
    source_inputs: dict[str, dict[str, str]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "artifact": "skill_character_references",
        "bundle_version": BUNDLE_VERSION,
        "generated_at": generated_at,
        "canonical_source": CANONICAL_SOURCE,
        "provenance": {
            "normalized_input": source_inputs["normalized_characters"],
            "tags_input": source_inputs["tags"],
            "effect_taxonomy_input": source_inputs["effect_taxonomy"],
            "source_map_artifact": "source-map.json",
        },
        "summary": {
            "record_count": len(characters),
            "skill_count": count_skill_total(characters),
            "tagged_record_count": sum(1 for record in character_records if record["tag_ids"]),
            "records_with_data_quality_tags": sum(1 for record in character_records if record["data_quality_tag_ids"]),
        },
        "records": character_records,
    }


def build_mission_bundle(
    missions: list[dict[str, Any]],
    mission_records: list[dict[str, Any]],
    source_inputs: dict[str, dict[str, str]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "artifact": "skill_mission_references",
        "bundle_version": BUNDLE_VERSION,
        "generated_at": generated_at,
        "canonical_source": CANONICAL_SOURCE,
        "provenance": {
            "normalized_input": source_inputs["normalized_missions"],
            "tags_input": source_inputs["tags"],
            "effect_taxonomy_input": source_inputs["effect_taxonomy"],
            "source_map_artifact": "source-map.json",
        },
        "summary": {
            "record_count": len(missions),
            "unknown_requirement_record_count": count_unknown_mission_records(missions),
            "tagged_record_count": sum(1 for record in mission_records if record["tag_ids"]),
            "records_with_data_quality_tags": sum(1 for record in mission_records if record["data_quality_tag_ids"]),
        },
        "records": mission_records,
    }


def build_rules_markdown(
    source_inputs: dict[str, dict[str, str]],
    character_validation: dict[str, Any],
    mission_validation: dict[str, Any],
    generated_at: str,
) -> str:
    lines = [
        "# Naruto Arena Team Builder Reference Rules",
        "",
        "## Canonical Source Lock",
        "",
        f"- Canonical game source: `{CANONICAL_SOURCE}`",
        "- Do not use other Naruto Arena domains, mirrors, or model memory as mechanics sources.",
        "- If a claim is not supported by the local reference files in this directory, report the gap instead of guessing.",
        "",
        "## Allowed Mechanics Sources For The Future Skill",
        "",
        "- `characters.json`, `missions.json`, `tags.json`, `effect-taxonomy.json`, and `source-map.json` in this directory are the only mechanics sources for the future skill.",
        "- Resolve every `source_ref_id` through `source-map.json` when the answer needs exact source URLs, snapshot lineage, or section-level provenance.",
        "- Use `data-quality-report.md` to surface accepted bundle limitations before making narrow strategic claims.",
        "",
        "## Honest Uncertainty Handling",
        "",
        f"- Keep all {mission_validation['unknown_requirement_record_count']} missions with explicit unknown requirements as unknown. Do not invent hidden mission objectives.",
        "- Distinguish confirmed mechanics from strategic inference in every future skill answer.",
        "- If a record carries `data_quality_tag_ids`, surface the relevant uncertainty instead of treating it as noise.",
        f"- The playable bundle intentionally excludes {len(character_validation['excluded_raw_names'])} disabled zero-skill raw stubs: {', '.join(character_validation['excluded_raw_names'])}. Do not present them as playable characters.",
        "",
        "## Taxonomy Guardrails",
        "",
        "- Do not narrow broad accepted effect buckets such as `protect`, `apply_state`, `remove_state`, `gain`, or `drain` beyond the accepted taxonomy definitions unless the exact supporting source text is cited through provenance.",
        "- `character.data.*` and `mission.data.*` tags are evidence-backed data-quality markers, not optional hints.",
        "",
        "## Build Provenance",
        "",
        f"- Bundle version: `{BUNDLE_VERSION}`",
        f"- Generated at: `{generated_at}`",
        "- Regenerate with `python scripts\\build_skill_references.py`.",
        "- Accepted build inputs:",
    ]
    for label in (
        "normalized_characters",
        "normalized_missions",
        "tags",
        "effect_taxonomy",
        "character_validation_result",
        "mission_validation_result",
    ):
        item = source_inputs[label]
        lines.append(f"  - `{item['path']}` (`sha256={item['sha256']}`)")
    return "\n".join(lines)


def build_data_quality_report(
    tags_payload: dict[str, Any],
    effect_taxonomy_payload: dict[str, Any],
    source_inputs: dict[str, dict[str, str]],
    character_validation: dict[str, Any],
    mission_validation: dict[str, Any],
    generated_at: str,
) -> str:
    tag_summary = tags_payload["summary"]
    character_tag_counts = tag_summary["character_tag_counts"]
    mission_tag_counts = tag_summary["mission_tag_counts"]

    broad_effect_notes: list[tuple[str, str]] = []
    for effect_type in effect_taxonomy_payload.get("effect_types", []):
        if not isinstance(effect_type, dict):
            continue
        effect_type_id = effect_type.get("effect_type")
        inference_notes = effect_type.get("inference_notes")
        if effect_type_id in BROAD_EFFECT_TYPES and isinstance(inference_notes, str) and inference_notes.strip():
            broad_effect_notes.append((effect_type_id, inference_notes))

    lines = [
        "# Data Quality Report",
        "",
        "## Bundle Summary",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Bundle version: `{BUNDLE_VERSION}`",
        f"- Playable character records: {character_validation['included_record_count']}",
        f"- Mission records: {mission_validation['included_record_count']}",
        f"- Excluded disabled zero-skill raw characters: {len(character_validation['excluded_raw_names'])}",
        f"- Explicit unknown mission objective records: {mission_validation['unknown_requirement_record_count']}",
        "",
        "## Character Bundle Scope",
        "",
        "- The playable character bundle is intentionally narrower than the raw roster when the canonical source exposes disabled zero-skill stubs.",
        f"- Accepted exclusions: {', '.join(character_validation['excluded_raw_names'])}.",
        f"- Accepted raw-versus-playable counts: raw={character_validation['raw_record_count']}, playable={character_validation['included_record_count']}.",
        "",
        "## Mission Objective Uncertainty",
        "",
        f"- `{mission_validation['unknown_requirement_record_count']}` mission records retain explicit `unknown` requirements because the accepted snapshot does not reveal objective text.",
        "- Accepted raw-detail evidence breakdown:",
        f"  - redirect payloads: {mission_validation['detail_state_counts'].get('redirect', 0)}",
        f"  - error-page payloads: {mission_validation['detail_state_counts'].get('error_page', 0)}",
        f"  - unexpected-home payloads: {mission_validation['detail_state_counts'].get('unexpected_home', 0)}",
        "",
        "## Record-Level Data Quality Tags",
        "",
        f"- `character.data.effect_target_unknown`: {character_tag_counts.get('character.data.effect_target_unknown', 0)} character records",
        f"- `character.data.effect_type_heuristic`: {character_tag_counts.get('character.data.effect_type_heuristic', 0)} character records",
        f"- `character.data.effect_magnitude_unknown`: {character_tag_counts.get('character.data.effect_magnitude_unknown', 0)} character records",
        f"- `character.data.effect_fallback_unknown`: {character_tag_counts.get('character.data.effect_fallback_unknown', 0)} character records",
        f"- `mission.data.objective_text_missing`: {mission_tag_counts.get('mission.data.objective_text_missing', 0)} mission records",
        f"- `mission.data.detail_payload_redirect`: {mission_tag_counts.get('mission.data.detail_payload_redirect', 0)} mission records",
        f"- `mission.data.detail_payload_error_page`: {mission_tag_counts.get('mission.data.detail_payload_error_page', 0)} mission records",
        f"- `mission.data.detail_payload_unexpected_home`: {mission_tag_counts.get('mission.data.detail_payload_unexpected_home', 0)} mission records",
        f"- `mission.data.character_group_not_modeled`: {mission_tag_counts.get('mission.data.character_group_not_modeled', 0)} mission records",
        f"- `mission.data.multi_character_condition_not_structured`: {mission_tag_counts.get('mission.data.multi_character_condition_not_structured', 0)} mission records",
        f"- `mission.data.character_subject_not_resolved`: {mission_tag_counts.get('mission.data.character_subject_not_resolved', 0)} mission records",
        f"- `mission.data.skill_reference_not_resolved`: {mission_tag_counts.get('mission.data.skill_reference_not_resolved', 0)} mission records",
        "",
        "## Taxonomy Guardrails",
        "",
        "- The accepted taxonomy is intentionally conservative. Downstream skill logic must not collapse broad parser buckets into narrower claimed mechanics.",
    ]
    for effect_type_id, inference_notes in broad_effect_notes:
        lines.append(f"- `{effect_type_id}`: {inference_notes}")

    lines.extend(
        [
            "",
            "## Build Inputs",
            "",
        ]
    )
    for label in (
        "normalized_characters",
        "normalized_missions",
        "tags",
        "effect_taxonomy",
        "character_validation_result",
        "mission_validation_result",
    ):
        item = source_inputs[label]
        lines.append(f"- `{item['path']}` (`sha256={item['sha256']}`)")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the skill-local Naruto Arena reference bundle from accepted normalized and taxonomy artifacts."
    )
    parser.add_argument("--characters", type=Path, default=DEFAULT_CHARACTERS_PATH, help="Path to data/normalized/characters.json")
    parser.add_argument("--missions", type=Path, default=DEFAULT_MISSIONS_PATH, help="Path to data/normalized/missions.json")
    parser.add_argument("--tags", type=Path, default=DEFAULT_TAGS_PATH, help="Path to references/tags.json")
    parser.add_argument(
        "--effect-taxonomy",
        type=Path,
        default=DEFAULT_EFFECT_TAXONOMY_PATH,
        help="Path to references/effect-taxonomy.json",
    )
    parser.add_argument(
        "--character-validation-result",
        type=Path,
        default=DEFAULT_CHARACTER_VALIDATION_RESULT,
        help="Path to TASK-EXTRACT-CHARACTERS-VALIDATE-01 result file",
    )
    parser.add_argument(
        "--mission-validation-result",
        type=Path,
        default=DEFAULT_MISSION_VALIDATION_RESULT,
        help="Path to TASK-EXTRACT-MISSIONS-VALIDATE-01 result file",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for skill-local reference artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    characters_path = args.characters.resolve()
    missions_path = args.missions.resolve()
    tags_path = args.tags.resolve()
    effect_taxonomy_path = args.effect_taxonomy.resolve()
    character_validation_result_path = args.character_validation_result.resolve()
    mission_validation_result_path = args.mission_validation_result.resolve()
    output_dir = args.out_dir.resolve()

    characters = load_json(characters_path)
    missions = load_json(missions_path)
    tags_payload = load_json(tags_path)
    effect_taxonomy_payload = load_json(effect_taxonomy_path)

    if not isinstance(characters, list) or not all(isinstance(item, dict) for item in characters):
        raise ValueError("Expected characters input to be a JSON array of objects")
    if not isinstance(missions, list) or not all(isinstance(item, dict) for item in missions):
        raise ValueError("Expected missions input to be a JSON array of objects")
    if not isinstance(tags_payload, dict) or not isinstance(effect_taxonomy_payload, dict):
        raise ValueError("Expected tags and effect taxonomy inputs to be JSON objects")

    character_validation = parse_character_validation_result(character_validation_result_path)
    mission_validation = parse_mission_validation_result(mission_validation_result_path)
    validate_input_consistency(
        characters=characters,
        missions=missions,
        tags_payload=tags_payload,
        effect_taxonomy_payload=effect_taxonomy_payload,
        character_validation=character_validation,
        mission_validation=mission_validation,
    )

    source_inputs = build_source_input_summary(
        {
            "normalized_characters": characters_path,
            "normalized_missions": missions_path,
            "tags": tags_path,
            "effect_taxonomy": effect_taxonomy_path,
            "character_validation_result": character_validation_result_path,
            "mission_validation_result": mission_validation_result_path,
        }
    )
    generated_at = timestamp_utc()

    character_tag_categories = build_tag_category_map(tags_payload, "character")
    mission_tag_categories = build_tag_category_map(tags_payload, "mission")
    character_tag_map = build_record_tag_map(tags_payload.get("character_tags"), character_tag_categories)
    mission_tag_map = build_record_tag_map(tags_payload.get("mission_tags"), mission_tag_categories)

    character_records = normalize_character_records(characters, character_tag_map)
    mission_records = normalize_mission_records(missions, mission_tag_map)

    character_bundle = build_character_bundle(
        characters=characters,
        character_records=character_records,
        source_inputs=source_inputs,
        generated_at=generated_at,
    )
    mission_bundle = build_mission_bundle(
        missions=missions,
        mission_records=mission_records,
        source_inputs=source_inputs,
        generated_at=generated_at,
    )
    source_map = build_source_map(
        characters=characters,
        missions=missions,
        source_inputs=source_inputs,
        output_dir=output_dir,
        character_validation=character_validation,
        mission_validation=mission_validation,
        generated_at=generated_at,
    )
    rules_markdown = build_rules_markdown(
        source_inputs=source_inputs,
        character_validation=character_validation,
        mission_validation=mission_validation,
        generated_at=generated_at,
    )
    data_quality_report = build_data_quality_report(
        tags_payload=tags_payload,
        effect_taxonomy_payload=effect_taxonomy_payload,
        source_inputs=source_inputs,
        character_validation=character_validation,
        mission_validation=mission_validation,
        generated_at=generated_at,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(output_dir / "rules.md", rules_markdown)
    write_json(output_dir / "characters.json", character_bundle)
    write_json(output_dir / "missions.json", mission_bundle)
    write_json(output_dir / "tags.json", tags_payload)
    write_json(output_dir / "effect-taxonomy.json", effect_taxonomy_payload)
    write_json(output_dir / "source-map.json", source_map)
    write_text(output_dir / "data-quality-report.md", data_quality_report)

    summary = {
        "status": "ok",
        "out_dir": str(output_dir),
        "artifacts": [str(output_dir / name) for name in EXPECTED_OUTPUTS],
        "summary": {
            "character_count": len(characters),
            "mission_count": len(missions),
            "skill_count": count_skill_total(characters),
            "unknown_mission_objective_count": mission_validation["unknown_requirement_record_count"],
            "excluded_disabled_zero_skill_character_count": len(character_validation["excluded_raw_names"]),
            "excluded_disabled_zero_skill_characters": character_validation["excluded_raw_names"],
            "unknown_mission_detail_state_counts": mission_validation["detail_state_counts"],
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

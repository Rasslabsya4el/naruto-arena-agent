#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCES_DIR = REPO_ROOT / "skills" / "naruto-arena-team-builder" / "references"
CANONICAL_SOURCE = "https://www.naruto-arena.site/"
CANONICAL_DOMAIN = "www.naruto-arena.site"
EXPECTED_BUNDLE_VERSION = "skill-reference-bundle-v1"
EXPECTED_CHARACTER_COUNT = 196
EXPECTED_MISSION_COUNT = 179
EXPECTED_UNKNOWN_MISSION_COUNT = 122
EXPECTED_CHARACTER_SKILL_COUNT = 877
EXPECTED_EXCLUDED_CHARACTERS = (
    "Edo Tensei Itachi (S)",
    "Shinobi Alliance Kakashi (S)",
)
EXPECTED_OUTPUTS = (
    "rules.md",
    "characters.json",
    "missions.json",
    "tags.json",
    "effect-taxonomy.json",
    "source-map.json",
    "data-quality-report.md",
)
EXPECTED_SOURCE_INPUT_KEYS = (
    "normalized_characters",
    "normalized_missions",
    "tags",
    "effect_taxonomy",
    "character_validation_result",
    "mission_validation_result",
)
REQUIRED_SOURCE_REF_FIELDS = (
    "source_id",
    "url",
    "canonical_domain",
    "snapshot_path",
    "raw_text_hash",
    "section",
)
REQUIRED_RULE_SNIPPETS = (
    f"- Canonical game source: `{CANONICAL_SOURCE}`",
    "- Do not use other Naruto Arena domains, mirrors, or model memory as mechanics sources.",
    "- If a claim is not supported by the local reference files in this directory, report the gap instead of guessing.",
    "- `characters.json`, `missions.json`, `tags.json`, `effect-taxonomy.json`, and `source-map.json` in this directory are the only mechanics sources for the future skill.",
    "- Resolve every `source_ref_id` through `source-map.json` when the answer needs exact source URLs, snapshot lineage, or section-level provenance.",
)
REPORT_COUNT_PATTERNS = {
    "playable_character_records": r"- Playable character records: (\d+)",
    "mission_records": r"- Mission records: (\d+)",
    "excluded_character_count": r"- Excluded disabled zero-skill raw characters: (\d+)",
    "unknown_mission_records": r"- Explicit unknown mission objective records: (\d+)",
    "raw_playable_counts": r"- Accepted raw-versus-playable counts: raw=(\d+), playable=(\d+)\.",
    "redirect_count": r"- redirect payloads: (\d+)",
    "error_page_count": r"- error-page payloads: (\d+)",
    "unexpected_home_count": r"- unexpected-home payloads: (\d+)",
}


def require_file(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ValueError(f"Expected {expected} file at {path}")


def require_dir(path: Path, expected: str) -> None:
    if not path.is_dir():
        raise ValueError(f"Expected {expected} directory at {path}")


def load_json(path: Path, expected: str) -> Any:
    require_file(path, expected)
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, expected: str) -> str:
    require_file(path, expected)
    return path.read_text(encoding="utf-8")


def repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def append_issue(issues: list[str], condition: bool, message: str) -> None:
    if not condition:
        issues.append(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected {label} to be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Expected {label} to be a list")
    return value


def load_bundle_artifacts(references_dir: Path) -> tuple[dict[str, Path], dict[str, Any], str, str]:
    artifact_paths = {name: references_dir / name for name in EXPECTED_OUTPUTS}
    missing = [name for name, path in artifact_paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"Missing required bundle artifacts: {', '.join(missing)}")

    payloads = {
        "characters": load_json(artifact_paths["characters.json"], "skill character reference bundle"),
        "missions": load_json(artifact_paths["missions.json"], "skill mission reference bundle"),
        "tags": load_json(artifact_paths["tags.json"], "skill tag reference bundle"),
        "effect_taxonomy": load_json(artifact_paths["effect-taxonomy.json"], "skill effect taxonomy reference"),
        "source_map": load_json(artifact_paths["source-map.json"], "skill source map reference"),
    }
    rules_text = read_text(artifact_paths["rules.md"], "skill rules reference")
    report_text = read_text(artifact_paths["data-quality-report.md"], "skill data quality report")
    return artifact_paths, payloads, rules_text, report_text


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
        if not isinstance(tag_id, str) or not tag_id.strip():
            raise ValueError(f"Expected every {scope} tag catalog entry to include a non-empty tag_id")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"Expected every {scope} tag catalog entry to include a non-empty category")
        category_by_tag_id[tag_id] = category
    return category_by_tag_id


def build_record_tag_map(tag_records: Any, category_by_tag_id: dict[str, str]) -> dict[str, dict[str, Any]]:
    records = require_list(tag_records, "tag records")
    tag_map: dict[str, dict[str, Any]] = {}

    for entry in records:
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
                raise ValueError(f"Expected every tag entry for {record_id} to be an object")
            tag_id = tag.get("tag_id")
            evidence_count = tag.get("evidence_count")
            if not isinstance(tag_id, str) or not tag_id.strip():
                raise ValueError(f"Expected tag entry for {record_id} to include a non-empty tag_id")
            if not isinstance(evidence_count, int) or evidence_count < 0:
                raise ValueError(
                    f"Expected tag entry {tag_id} for {record_id} to include a non-negative evidence_count"
                )
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


def find_mission_requirement(
    missions: list[dict[str, Any]],
    mission_id: str,
    requirement_id: str,
) -> dict[str, Any] | None:
    for mission in missions:
        if not isinstance(mission, dict) or mission.get("id") != mission_id:
            continue
        requirements = mission.get("requirements", [])
        if not isinstance(requirements, list):
            return None
        for requirement in requirements:
            if isinstance(requirement, dict) and requirement.get("requirement_id") == requirement_id:
                return requirement
    return None


def validate_mission_character_choice_semantics(missions: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    expected_cases = {
        "mission:the-lone-swordsman:req:01": (
            "mission:the-lone-swordsman",
            {"character:momochi-zabuza", "character:hoshigaki-kisame"},
        ),
        "mission:the-drunken-master:req:01": (
            "mission:the-drunken-master",
            {"character:rock-lee", "character:kimimaro"},
        ),
    }
    for requirement_id, (mission_id, expected_refs) in expected_cases.items():
        requirement = find_mission_requirement(missions, mission_id, requirement_id)
        if not isinstance(requirement, dict):
            issues.append(f"missing expected alternative-character requirement {requirement_id}")
            continue
        character_choice = requirement.get("character_choice")
        if not isinstance(character_choice, dict):
            issues.append(f"{requirement_id} missing structured character_choice")
            continue
        eligible_refs = set(character_choice.get("eligible_character_refs", []))
        append_issue(
            issues,
            character_choice.get("choice_type") == "alternative_eligible_characters",
            f"{requirement_id} character_choice.choice_type drifted",
        )
        append_issue(
            issues,
            character_choice.get("progress_counting") == "per_eligible_character_present",
            f"{requirement_id} character_choice.progress_counting drifted",
        )
        append_issue(
            issues,
            character_choice.get("max_progress_per_qualifying_battle") == len(expected_refs),
            f"{requirement_id} character_choice max progress drifted",
        )
        append_issue(
            issues,
            eligible_refs == expected_refs,
            f"{requirement_id} character_choice eligible refs drifted",
        )

    blank_slate_requirement = find_mission_requirement(
        missions,
        "mission:a-blank-slate",
        "mission:a-blank-slate:req:01",
    )
    append_issue(
        issues,
        isinstance(blank_slate_requirement, dict) and blank_slate_requirement.get("character_choice") is None,
        "text-only group mission a-blank-slate unexpectedly gained character_choice",
    )

    unknown_with_choice = [
        requirement.get("requirement_id")
        for mission in missions
        if isinstance(mission, dict)
        for requirement in mission.get("requirements", [])
        if isinstance(requirement, dict)
        and requirement.get("requirement_type") == "unknown"
        and requirement.get("character_choice") is not None
    ]
    append_issue(
        issues,
        not unknown_with_choice,
        f"unknown mission requirements unexpectedly gained character_choice: {unknown_with_choice[:8]}",
    )
    return issues


def count_skill_total(characters: list[dict[str, Any]]) -> int:
    total = 0
    for character in characters:
        skills = character.get("skills")
        if isinstance(skills, list):
            total += len(skills)
    return total


def parse_report_int(text: str, pattern: str, label: str) -> int:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"Could not parse {label} from data-quality-report.md")
    return int(match.group(1))


def parse_report_raw_playable_counts(text: str) -> tuple[int, int]:
    match = re.search(REPORT_COUNT_PATTERNS["raw_playable_counts"], text)
    if match is None:
        raise ValueError("Could not parse raw/playable counts from data-quality-report.md")
    return int(match.group(1)), int(match.group(2))


def validate_rules_text(rules_text: str) -> list[str]:
    issues: list[str] = []
    for snippet in REQUIRED_RULE_SNIPPETS:
        append_issue(issues, snippet in rules_text, f"rules.md missing required snippet: {snippet}")
    return issues


def validate_source_ref_payload(source_ref_id: str, source_ref: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(source_ref, dict):
        return [f"source-map source ref {source_ref_id} is not an object"]
    for field in REQUIRED_SOURCE_REF_FIELDS:
        value = source_ref.get(field)
        append_issue(
            issues,
            isinstance(value, str) and bool(value.strip()),
            f"source-map source ref {source_ref_id} missing usable {field}",
        )
    append_issue(
        issues,
        source_ref.get("canonical_domain") == CANONICAL_DOMAIN,
        f"source-map source ref {source_ref_id} has non-canonical domain",
    )
    url = source_ref.get("url")
    append_issue(
        issues,
        isinstance(url, str) and url.startswith(CANONICAL_SOURCE),
        f"source-map source ref {source_ref_id} has non-canonical url",
    )
    return issues


def validate_record_tag_linkage(
    records: list[dict[str, Any]],
    tag_map: dict[str, dict[str, Any]],
    scope: str,
) -> list[str]:
    issues: list[str] = []
    for record in records:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            issues.append(f"{scope} bundle contains record with missing id")
            continue

        expected = tag_map.get(record_id)
        if expected is None:
            issues.append(f"{scope} record {record_id} is missing from tags.json")
            continue

        tag_ids = record.get("tag_ids")
        data_quality_tag_ids = record.get("data_quality_tag_ids")
        tag_evidence_counts = record.get("tag_evidence_counts")

        if tag_ids != expected["tag_ids"]:
            issues.append(f"{scope} record {record_id} has tag_ids drift against tags.json")
        if data_quality_tag_ids != expected["data_quality_tag_ids"]:
            issues.append(f"{scope} record {record_id} has data_quality_tag_ids drift against tags.json")
        if tag_evidence_counts != expected["tag_evidence_counts"]:
            issues.append(f"{scope} record {record_id} has tag_evidence_counts drift against tags.json")
    return issues


def validate_source_map_linkage(
    characters: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    source_map: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    source_refs_by_id = require_object(source_map.get("source_refs_by_id"), "source_map.source_refs_by_id")
    record_index = require_object(source_map.get("record_index"), "source_map.record_index")
    output_artifacts = require_object(source_map.get("output_artifacts"), "source_map.output_artifacts")

    for source_ref_id, source_ref in source_refs_by_id.items():
        if not isinstance(source_ref_id, str) or not source_ref_id.strip():
            issues.append("source-map contains blank source_ref_id")
            continue
        issues.extend(validate_source_ref_payload(source_ref_id, source_ref))

    characters_artifact_path = output_artifacts.get("characters.json")
    missions_artifact_path = output_artifacts.get("missions.json")

    for record in characters:
        record_id = record.get("id")
        record_name = record.get("name")
        if not isinstance(record_id, str) or not isinstance(record_name, str):
            issues.append("character bundle contains record with unusable id/name")
            continue

        source_ref_ids = record.get("source_ref_ids")
        if not isinstance(source_ref_ids, list) or not source_ref_ids:
            issues.append(f"character record {record_id} missing source_ref_ids")
        else:
            for source_ref_id in source_ref_ids:
                if source_ref_id not in source_refs_by_id:
                    issues.append(f"character record {record_id} references missing source_ref_id {source_ref_id}")

        index_entry = record_index.get(record_id)
        if not isinstance(index_entry, dict):
            issues.append(f"source-map missing record_index entry for {record_id}")
            continue

        if index_entry.get("record_type") != "character":
            issues.append(f"source-map record_index {record_id} has wrong record_type")
        if index_entry.get("name") != record_name:
            issues.append(f"source-map record_index {record_id} has wrong name")
        if index_entry.get("artifact_path") != characters_artifact_path:
            issues.append(f"source-map record_index {record_id} has wrong artifact_path")
        if index_entry.get("source_ref_ids") != source_ref_ids:
            issues.append(f"source-map record_index {record_id} has drifted source_ref_ids")

        child_records = index_entry.get("child_records")
        if not isinstance(child_records, dict):
            issues.append(f"source-map record_index {record_id} missing child_records")
            continue

        expected_skill_ids: set[str] = set()
        skills = record.get("skills")
        if not isinstance(skills, list):
            issues.append(f"character record {record_id} missing skills list")
            continue
        for skill in skills:
            if not isinstance(skill, dict):
                issues.append(f"character record {record_id} contains non-object skill")
                continue
            skill_id = skill.get("skill_id")
            skill_name = skill.get("name")
            skill_source_ref_ids = skill.get("source_ref_ids")
            if not isinstance(skill_id, str) or not skill_id.strip():
                issues.append(f"character record {record_id} has skill with missing skill_id")
                continue
            expected_skill_ids.add(skill_id)
            if not isinstance(skill_source_ref_ids, list) or not skill_source_ref_ids:
                issues.append(f"skill {skill_id} under {record_id} missing source_ref_ids")
            else:
                for source_ref_id in skill_source_ref_ids:
                    if source_ref_id not in source_refs_by_id:
                        issues.append(f"skill {skill_id} under {record_id} references missing source_ref_id {source_ref_id}")
            child_entry = child_records.get(skill_id)
            if not isinstance(child_entry, dict):
                issues.append(f"source-map missing child record for skill {skill_id} under {record_id}")
                continue
            if child_entry.get("name") != skill_name:
                issues.append(f"source-map child record {skill_id} under {record_id} has wrong name")
            if child_entry.get("source_ref_ids") != skill_source_ref_ids:
                issues.append(f"source-map child record {skill_id} under {record_id} has drifted source_ref_ids")

        extra_skill_ids = sorted(set(child_records) - expected_skill_ids)
        if extra_skill_ids:
            issues.append(f"source-map record_index {record_id} has unexpected child_records: {extra_skill_ids}")

    for record in missions:
        record_id = record.get("id")
        record_name = record.get("name")
        if not isinstance(record_id, str) or not isinstance(record_name, str):
            issues.append("mission bundle contains record with unusable id/name")
            continue

        source_ref_ids = record.get("source_ref_ids")
        if not isinstance(source_ref_ids, list) or not source_ref_ids:
            issues.append(f"mission record {record_id} missing source_ref_ids")
        else:
            for source_ref_id in source_ref_ids:
                if source_ref_id not in source_refs_by_id:
                    issues.append(f"mission record {record_id} references missing source_ref_id {source_ref_id}")

        index_entry = record_index.get(record_id)
        if not isinstance(index_entry, dict):
            issues.append(f"source-map missing record_index entry for {record_id}")
            continue

        if index_entry.get("record_type") != "mission":
            issues.append(f"source-map record_index {record_id} has wrong record_type")
        if index_entry.get("name") != record_name:
            issues.append(f"source-map record_index {record_id} has wrong name")
        if index_entry.get("artifact_path") != missions_artifact_path:
            issues.append(f"source-map record_index {record_id} has wrong artifact_path")
        if index_entry.get("source_ref_ids") != source_ref_ids:
            issues.append(f"source-map record_index {record_id} has drifted source_ref_ids")

    summary = require_object(source_map.get("summary"), "source_map.summary")
    append_issue(
        issues,
        summary.get("source_ref_count") == len(source_refs_by_id),
        "source-map summary.source_ref_count does not match source_refs_by_id size",
    )
    return issues


def validate_report_text(
    report_text: str,
    tags_payload: dict[str, Any],
    expected_excluded_names: tuple[str, ...],
) -> list[str]:
    issues: list[str] = []
    tag_summary = require_object(tags_payload.get("summary"), "tags.summary")
    mission_tag_counts = require_object(tag_summary.get("mission_tag_counts"), "tags.summary.mission_tag_counts")
    character_tag_counts = require_object(tag_summary.get("character_tag_counts"), "tags.summary.character_tag_counts")

    playable_character_records = parse_report_int(
        report_text,
        REPORT_COUNT_PATTERNS["playable_character_records"],
        "playable character records",
    )
    mission_records = parse_report_int(report_text, REPORT_COUNT_PATTERNS["mission_records"], "mission records")
    excluded_character_count = parse_report_int(
        report_text,
        REPORT_COUNT_PATTERNS["excluded_character_count"],
        "excluded character count",
    )
    unknown_mission_records = parse_report_int(
        report_text,
        REPORT_COUNT_PATTERNS["unknown_mission_records"],
        "unknown mission objective count",
    )
    raw_count, playable_count = parse_report_raw_playable_counts(report_text)
    redirect_count = parse_report_int(report_text, REPORT_COUNT_PATTERNS["redirect_count"], "redirect count")
    error_page_count = parse_report_int(report_text, REPORT_COUNT_PATTERNS["error_page_count"], "error-page count")
    unexpected_home_count = parse_report_int(
        report_text,
        REPORT_COUNT_PATTERNS["unexpected_home_count"],
        "unexpected-home count",
    )

    append_issue(
        issues,
        playable_character_records == EXPECTED_CHARACTER_COUNT,
        "data-quality-report playable character count drifted",
    )
    append_issue(
        issues,
        mission_records == EXPECTED_MISSION_COUNT,
        "data-quality-report mission count drifted",
    )
    append_issue(
        issues,
        excluded_character_count == len(expected_excluded_names),
        "data-quality-report excluded character count drifted",
    )
    append_issue(
        issues,
        unknown_mission_records == EXPECTED_UNKNOWN_MISSION_COUNT,
        "data-quality-report unknown mission objective count drifted",
    )
    append_issue(
        issues,
        raw_count == EXPECTED_CHARACTER_COUNT + len(expected_excluded_names) and playable_count == EXPECTED_CHARACTER_COUNT,
        "data-quality-report raw/playable character counts drifted",
    )
    append_issue(
        issues,
        redirect_count == mission_tag_counts.get("mission.data.detail_payload_redirect"),
        "data-quality-report redirect payload count drifted against tags summary",
    )
    append_issue(
        issues,
        error_page_count == mission_tag_counts.get("mission.data.detail_payload_error_page"),
        "data-quality-report error-page payload count drifted against tags summary",
    )
    append_issue(
        issues,
        unexpected_home_count == mission_tag_counts.get("mission.data.detail_payload_unexpected_home"),
        "data-quality-report unexpected-home payload count drifted against tags summary",
    )

    for name in expected_excluded_names:
        append_issue(
            issues,
            name in report_text,
            f"data-quality-report missing excluded character name {name}",
        )

    report_tag_checks = {
        "character.data.effect_target_unknown": character_tag_counts.get("character.data.effect_target_unknown"),
        "character.data.effect_type_heuristic": character_tag_counts.get("character.data.effect_type_heuristic"),
        "character.data.effect_magnitude_unknown": character_tag_counts.get("character.data.effect_magnitude_unknown"),
        "character.data.effect_fallback_unknown": character_tag_counts.get("character.data.effect_fallback_unknown"),
        "mission.data.objective_text_missing": mission_tag_counts.get("mission.data.objective_text_missing"),
        "mission.data.detail_payload_redirect": mission_tag_counts.get("mission.data.detail_payload_redirect"),
        "mission.data.detail_payload_error_page": mission_tag_counts.get("mission.data.detail_payload_error_page"),
        "mission.data.detail_payload_unexpected_home": mission_tag_counts.get("mission.data.detail_payload_unexpected_home"),
        "mission.data.character_group_not_modeled": mission_tag_counts.get("mission.data.character_group_not_modeled"),
        "mission.data.multi_character_condition_not_structured": mission_tag_counts.get(
            "mission.data.multi_character_condition_not_structured"
        ),
        "mission.data.character_subject_not_resolved": mission_tag_counts.get("mission.data.character_subject_not_resolved"),
        "mission.data.skill_reference_not_resolved": mission_tag_counts.get("mission.data.skill_reference_not_resolved"),
    }
    for tag_id, expected_count in report_tag_checks.items():
        if expected_count is None:
            issues.append(f"tags.json summary missing {tag_id}")
            continue
        pattern = rf"- `{re.escape(tag_id)}`: (\d+) "
        actual_count = parse_report_int(report_text, pattern, f"{tag_id} count")
        append_issue(
            issues,
            actual_count == expected_count,
            f"data-quality-report count for {tag_id} drifted against tags summary",
        )

    return issues


def build_report(references_dir: Path) -> dict[str, Any]:
    require_dir(references_dir, "skill-local reference bundle directory")
    artifact_paths, payloads, rules_text, report_text = load_bundle_artifacts(references_dir)

    characters_payload = require_object(payloads["characters"], "characters.json")
    missions_payload = require_object(payloads["missions"], "missions.json")
    tags_payload = require_object(payloads["tags"], "tags.json")
    effect_taxonomy_payload = require_object(payloads["effect_taxonomy"], "effect-taxonomy.json")
    source_map_payload = require_object(payloads["source_map"], "source-map.json")

    characters = require_list(characters_payload.get("records"), "characters.json records")
    missions = require_list(missions_payload.get("records"), "missions.json records")
    character_summary = require_object(characters_payload.get("summary"), "characters.json summary")
    mission_summary = require_object(missions_payload.get("summary"), "missions.json summary")
    tags_summary = require_object(tags_payload.get("summary"), "tags.json summary")
    taxonomy_summary = require_object(effect_taxonomy_payload.get("summary"), "effect-taxonomy.json summary")
    source_map_summary = require_object(source_map_payload.get("summary"), "source-map.json summary")
    accepted_validation_facts = require_object(
        source_map_payload.get("accepted_validation_facts"),
        "source-map.json accepted_validation_facts",
    )
    source_inputs = require_object(source_map_payload.get("source_inputs"), "source-map.json source_inputs")
    output_artifacts = require_object(source_map_payload.get("output_artifacts"), "source-map.json output_artifacts")

    character_category_map = build_tag_category_map(tags_payload, "character")
    mission_category_map = build_tag_category_map(tags_payload, "mission")
    character_tag_map = build_record_tag_map(tags_payload.get("character_tags"), character_category_map)
    mission_tag_map = build_record_tag_map(tags_payload.get("mission_tags"), mission_category_map)

    actual_character_count = len(characters)
    actual_mission_count = len(missions)
    actual_skill_count = count_skill_total(characters)
    actual_unknown_mission_count = count_unknown_mission_records(missions)
    actual_character_data_quality_count = sum(
        1 for record in characters if isinstance(record.get("data_quality_tag_ids"), list) and record["data_quality_tag_ids"]
    )
    actual_mission_data_quality_count = sum(
        1 for record in missions if isinstance(record.get("data_quality_tag_ids"), list) and record["data_quality_tag_ids"]
    )
    character_names = {
        record.get("name")
        for record in characters
        if isinstance(record, dict) and isinstance(record.get("name"), str)
    }

    artifact_issues: list[str] = []
    for name, path in artifact_paths.items():
        append_issue(artifact_issues, path.is_file(), f"missing required artifact {name}")
    append_issue(
        artifact_issues,
        sorted(output_artifacts) == sorted(EXPECTED_OUTPUTS),
        "source-map output_artifacts keys drifted",
    )
    for name in EXPECTED_OUTPUTS:
        expected_path = repo_rel(artifact_paths[name])
        append_issue(
            artifact_issues,
            output_artifacts.get(name) == expected_path,
            f"source-map output_artifacts[{name}] does not point at the accepted bundle path",
        )

    rules_issues = validate_rules_text(rules_text)

    metadata_issues: list[str] = []
    append_issue(
        metadata_issues,
        characters_payload.get("artifact") == "skill_character_references",
        "characters.json artifact id drifted",
    )
    append_issue(
        metadata_issues,
        missions_payload.get("artifact") == "skill_mission_references",
        "missions.json artifact id drifted",
    )
    append_issue(
        metadata_issues,
        source_map_payload.get("artifact") == "source_map",
        "source-map.json artifact id drifted",
    )
    for label, payload in (
        ("characters.json", characters_payload),
        ("missions.json", missions_payload),
        ("source-map.json", source_map_payload),
    ):
        append_issue(
            metadata_issues,
            payload.get("bundle_version") == EXPECTED_BUNDLE_VERSION,
            f"{label} bundle_version drifted",
        )
        append_issue(
            metadata_issues,
            payload.get("canonical_source") == CANONICAL_SOURCE,
            f"{label} canonical_source drifted",
        )
    for label, payload in (
        ("characters.json", characters_payload),
        ("missions.json", missions_payload),
    ):
        provenance = payload.get("provenance")
        append_issue(
            metadata_issues,
            isinstance(provenance, dict),
            f"{label} missing provenance object",
        )
        if isinstance(provenance, dict):
            for key in ("normalized_input", "tags_input", "effect_taxonomy_input", "source_map_artifact"):
                append_issue(
                    metadata_issues,
                    key in provenance,
                    f"{label} provenance missing {key}",
                )
            append_issue(
                metadata_issues,
                provenance.get("source_map_artifact") == "source-map.json",
                f"{label} provenance.source_map_artifact drifted",
            )
    append_issue(
        metadata_issues,
        sorted(source_inputs) == sorted(EXPECTED_SOURCE_INPUT_KEYS),
        "source-map source_inputs keys drifted",
    )
    for key in EXPECTED_SOURCE_INPUT_KEYS:
        item = source_inputs.get(key)
        append_issue(
            metadata_issues,
            isinstance(item, dict),
            f"source-map source_inputs missing object for {key}",
        )
        if isinstance(item, dict):
            append_issue(
                metadata_issues,
                isinstance(item.get("path"), str) and bool(item["path"].strip()),
                f"source-map source_inputs[{key}] missing path",
            )
            append_issue(
                metadata_issues,
                isinstance(item.get("sha256"), str) and bool(item["sha256"].strip()),
                f"source-map source_inputs[{key}] missing sha256",
            )

    count_issues: list[str] = []
    append_issue(count_issues, actual_character_count == EXPECTED_CHARACTER_COUNT, "character record count drifted")
    append_issue(count_issues, actual_mission_count == EXPECTED_MISSION_COUNT, "mission record count drifted")
    append_issue(count_issues, actual_skill_count == EXPECTED_CHARACTER_SKILL_COUNT, "character skill count drifted")
    append_issue(
        count_issues,
        actual_unknown_mission_count == EXPECTED_UNKNOWN_MISSION_COUNT,
        "unknown mission objective record count drifted",
    )
    append_issue(
        count_issues,
        character_summary.get("record_count") == EXPECTED_CHARACTER_COUNT,
        "characters.json summary.record_count drifted",
    )
    append_issue(
        count_issues,
        mission_summary.get("record_count") == EXPECTED_MISSION_COUNT,
        "missions.json summary.record_count drifted",
    )
    append_issue(
        count_issues,
        character_summary.get("skill_count") == EXPECTED_CHARACTER_SKILL_COUNT,
        "characters.json summary.skill_count drifted",
    )
    append_issue(
        count_issues,
        mission_summary.get("unknown_requirement_record_count") == EXPECTED_UNKNOWN_MISSION_COUNT,
        "missions.json summary.unknown_requirement_record_count drifted",
    )
    append_issue(
        count_issues,
        tags_summary.get("character_record_count") == EXPECTED_CHARACTER_COUNT,
        "tags.json summary.character_record_count drifted",
    )
    append_issue(
        count_issues,
        tags_summary.get("mission_record_count") == EXPECTED_MISSION_COUNT,
        "tags.json summary.mission_record_count drifted",
    )
    append_issue(
        count_issues,
        taxonomy_summary.get("character_count") == EXPECTED_CHARACTER_COUNT,
        "effect-taxonomy.json summary.character_count drifted",
    )
    append_issue(
        count_issues,
        taxonomy_summary.get("mission_count") == EXPECTED_MISSION_COUNT,
        "effect-taxonomy.json summary.mission_count drifted",
    )
    append_issue(
        count_issues,
        taxonomy_summary.get("skill_count") == EXPECTED_CHARACTER_SKILL_COUNT,
        "effect-taxonomy.json summary.skill_count drifted",
    )
    append_issue(
        count_issues,
        source_map_summary.get("character_record_count") == EXPECTED_CHARACTER_COUNT,
        "source-map.json summary.character_record_count drifted",
    )
    append_issue(
        count_issues,
        source_map_summary.get("mission_record_count") == EXPECTED_MISSION_COUNT,
        "source-map.json summary.mission_record_count drifted",
    )
    append_issue(
        count_issues,
        source_map_summary.get("unknown_mission_objective_record_count") == EXPECTED_UNKNOWN_MISSION_COUNT,
        "source-map.json summary.unknown_mission_objective_record_count drifted",
    )

    unknown_issues: list[str] = []
    mission_tag_counts = require_object(tags_summary.get("mission_tag_counts"), "tags.summary.mission_tag_counts")
    append_issue(
        unknown_issues,
        actual_unknown_mission_count == EXPECTED_UNKNOWN_MISSION_COUNT,
        "missions bundle no longer keeps 122 unknown mission objectives explicit",
    )
    append_issue(
        unknown_issues,
        mission_tag_counts.get("mission.objective.unknown") == EXPECTED_UNKNOWN_MISSION_COUNT,
        "tags.json mission.objective.unknown count drifted",
    )
    append_issue(
        unknown_issues,
        accepted_validation_facts.get("unknown_mission_objective_record_count") == EXPECTED_UNKNOWN_MISSION_COUNT,
        "source-map accepted_validation_facts.unknown_mission_objective_record_count drifted",
    )
    detail_state_counts = accepted_validation_facts.get("unknown_mission_detail_state_counts")
    append_issue(
        unknown_issues,
        isinstance(detail_state_counts, dict),
        "source-map accepted_validation_facts missing unknown_mission_detail_state_counts",
    )
    if isinstance(detail_state_counts, dict):
        for key in ("mission_status", "redirect", "error_page", "unexpected_home"):
            append_issue(
                unknown_issues,
                isinstance(detail_state_counts.get(key), int),
                f"source-map accepted_validation_facts missing integer detail-state count for {key}",
            )

    exclusion_issues: list[str] = []
    excluded_names = accepted_validation_facts.get("excluded_disabled_zero_skill_characters")
    append_issue(
        exclusion_issues,
        isinstance(excluded_names, list) and excluded_names == list(EXPECTED_EXCLUDED_CHARACTERS),
        "source-map accepted excluded character names drifted",
    )
    append_issue(
        exclusion_issues,
        source_map_summary.get("excluded_disabled_zero_skill_character_count") == len(EXPECTED_EXCLUDED_CHARACTERS),
        "source-map excluded character count drifted",
    )
    for name in EXPECTED_EXCLUDED_CHARACTERS:
        append_issue(
            exclusion_issues,
            name not in character_names,
            f"excluded zero-skill character {name} leaked into characters.json",
        )
        append_issue(
            exclusion_issues,
            name in rules_text,
            f"rules.md no longer surfaces excluded character {name}",
        )

    tag_linkage_issues = validate_record_tag_linkage(characters, character_tag_map, "character")
    tag_linkage_issues.extend(validate_record_tag_linkage(missions, mission_tag_map, "mission"))
    append_issue(
        tag_linkage_issues,
        character_summary.get("tagged_record_count") == actual_character_count,
        "characters.json summary.tagged_record_count drifted",
    )
    append_issue(
        tag_linkage_issues,
        mission_summary.get("tagged_record_count") == actual_mission_count,
        "missions.json summary.tagged_record_count drifted",
    )
    append_issue(
        tag_linkage_issues,
        character_summary.get("records_with_data_quality_tags") == actual_character_data_quality_count,
        "characters.json records_with_data_quality_tags drifted",
    )
    append_issue(
        tag_linkage_issues,
        mission_summary.get("records_with_data_quality_tags") == actual_mission_data_quality_count,
        "missions.json records_with_data_quality_tags drifted",
    )
    append_issue(
        tag_linkage_issues,
        tags_summary.get("character_tagged_record_count") == actual_character_count,
        "tags.json character_tagged_record_count drifted",
    )
    append_issue(
        tag_linkage_issues,
        tags_summary.get("mission_tagged_record_count") == actual_mission_count,
        "tags.json mission_tagged_record_count drifted",
    )

    mission_character_choice_issues = validate_mission_character_choice_semantics(missions)
    source_map_issues = validate_source_map_linkage(characters, missions, source_map_payload)
    report_issues = validate_report_text(report_text, tags_payload, EXPECTED_EXCLUDED_CHARACTERS)

    checks = {
        "required_artifact_surfaces_intact": not artifact_issues,
        "canonical_rules_guardrails_intact": not rules_issues,
        "bundle_metadata_and_provenance_surfaces_intact": not metadata_issues,
        "expected_record_and_skill_counts_preserved": not count_issues,
        "unknown_objective_reporting_preserved": not unknown_issues,
        "excluded_character_reporting_preserved": not exclusion_issues,
        "bundle_tag_and_data_quality_linkage_preserved": not tag_linkage_issues,
        "mission_alternative_character_choice_semantics_preserved": not mission_character_choice_issues,
        "source_ref_resolution_and_record_index_linkage_preserved": not source_map_issues,
        "data_quality_report_surface_preserved": not report_issues,
    }

    failures = {
        "artifact_issues": artifact_issues,
        "rules_issues": rules_issues,
        "metadata_issues": metadata_issues,
        "count_issues": count_issues,
        "unknown_objective_issues": unknown_issues,
        "exclusion_issues": exclusion_issues,
        "tag_linkage_issues": tag_linkage_issues,
        "mission_character_choice_issues": mission_character_choice_issues,
        "source_map_issues": source_map_issues,
        "report_issues": report_issues,
    }

    return {
        "status": "failed" if not all(checks.values()) else "ok",
        "references_dir": str(references_dir),
        "artifacts": {
            name: str(path)
            for name, path in artifact_paths.items()
        },
        "summary": {
            "character_record_count": actual_character_count,
            "mission_record_count": actual_mission_count,
            "skill_count": actual_skill_count,
            "unknown_mission_objective_record_count": actual_unknown_mission_count,
            "excluded_disabled_zero_skill_character_count": len(EXPECTED_EXCLUDED_CHARACTERS),
            "excluded_disabled_zero_skill_characters": list(EXPECTED_EXCLUDED_CHARACTERS),
            "character_records_with_data_quality_tags": actual_character_data_quality_count,
            "mission_records_with_data_quality_tags": actual_mission_data_quality_count,
            "source_ref_count": source_map_summary.get("source_ref_count"),
        },
        "checks": checks,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the accepted skill-local Naruto Arena reference bundle contract without rebuilding artifacts."
    )
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=DEFAULT_REFERENCES_DIR,
        help="Path to skills/naruto-arena-team-builder/references",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.references_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1) from exc

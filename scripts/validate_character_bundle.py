#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_PATH = REPO_ROOT / "data" / "normalized" / "characters.json"
DEFAULT_OVERVIEW_PATH = REPO_ROOT / "snapshots" / "raw" / "site_capture" / "latest" / "characters" / "overview.json"
REQUIRED_SOURCE_REF_FIELDS = (
    "source_id",
    "url",
    "canonical_domain",
    "snapshot_path",
    "raw_text_hash",
    "section",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_path(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ValueError(f"Expected {expected} file at {path}")


def load_normalized_records(path: Path) -> list[dict[str, Any]]:
    require_path(path, "normalized character bundle")
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected normalized character bundle to be a JSON array, found {type(payload).__name__}")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Expected every normalized bundle item to be an object")
    return payload


def load_raw_characters(path: Path) -> list[dict[str, Any]]:
    require_path(path, "raw character overview")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected raw overview payload to be an object, found {type(payload).__name__}")
    page_props = payload.get("pageProps")
    if not isinstance(page_props, dict):
        raise ValueError("Expected raw overview payload to contain object pageProps")
    chars = page_props.get("chars")
    if not isinstance(chars, list):
        raise ValueError("Expected raw overview payload to contain list pageProps.chars")
    if not all(isinstance(item, dict) for item in chars):
        raise ValueError("Expected every raw overview character entry to be an object")
    return chars


def duplicate_names(items: list[dict[str, Any]]) -> list[str]:
    counts = Counter(item.get("name") for item in items if isinstance(item.get("name"), str) and item["name"].strip())
    return sorted(name for name, count in counts.items() if count > 1)


def usable_raw_text(raw_text: Any) -> tuple[bool, list[str]]:
    if not isinstance(raw_text, dict):
        return False, ["raw_text_not_object"]

    issues: list[str] = []
    primary = raw_text.get("primary")
    if not isinstance(primary, str) or not primary.strip():
        issues.append("missing_primary")

    fragments = raw_text.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        issues.append("missing_fragments")
    else:
        has_usable_fragment = any(
            isinstance(fragment, dict)
            and isinstance(fragment.get("field"), str)
            and fragment["field"].strip()
            and isinstance(fragment.get("text"), str)
            and fragment["text"].strip()
            and isinstance(fragment.get("source_ref_id"), str)
            and fragment["source_ref_id"].strip()
            for fragment in fragments
        )
        if not has_usable_fragment:
            issues.append("fragments_missing_required_fields")

    return not issues, issues


def source_ref_field_gaps(source_refs: Any) -> list[dict[str, Any]]:
    if not isinstance(source_refs, list) or not source_refs:
        return [{"index": None, "missing_fields": ["source_refs"]}]

    gaps: list[dict[str, Any]] = []
    for index, source_ref in enumerate(source_refs):
        if not isinstance(source_ref, dict):
            gaps.append({"index": index, "missing_fields": ["source_ref_not_object"]})
            continue
        missing_fields = [
            field
            for field in REQUIRED_SOURCE_REF_FIELDS
            if not isinstance(source_ref.get(field), str) or not source_ref[field].strip()
        ]
        if missing_fields:
            gaps.append({"index": index, "missing_fields": missing_fields})
    return gaps


def parse_confidence_present(parse_meta: Any) -> bool:
    return isinstance(parse_meta, dict) and parse_meta.get("confidence") is not None


def raw_skill_count(raw_character: dict[str, Any]) -> int | None:
    skills = raw_character.get("skills")
    if isinstance(skills, list):
        return len(skills)
    return None


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_skills: list[str] = []
    missing_character_source_refs: list[dict[str, Any]] = []
    missing_character_raw_text: list[dict[str, Any]] = []
    missing_parse_confidence: list[str] = []
    skill_source_ref_issues: list[dict[str, Any]] = []
    skill_raw_text_issues: list[dict[str, Any]] = []

    for record in records:
        name = record.get("name") if isinstance(record.get("name"), str) else record.get("id", "<unknown>")
        skills = record.get("skills")
        if not isinstance(skills, list) or not skills:
            missing_skills.append(str(name))
        character_source_ref_gaps = source_ref_field_gaps(record.get("source_refs"))
        if character_source_ref_gaps:
            missing_character_source_refs.append(
                {
                    "name": str(name),
                    "issues": character_source_ref_gaps,
                }
            )
        character_raw_text_ok, character_raw_text_issues = usable_raw_text(record.get("raw_text"))
        if not character_raw_text_ok:
            missing_character_raw_text.append(
                {
                    "name": str(name),
                    "issues": character_raw_text_issues,
                }
            )
        if not parse_confidence_present(record.get("parse")):
            missing_parse_confidence.append(str(name))

        if not isinstance(skills, list):
            continue

        for skill in skills:
            skill_name = skill.get("name") if isinstance(skill.get("name"), str) else skill.get("skill_id", "<unknown skill>")
            label = f"{name} :: {skill_name}"

            raw_text_ok, raw_text_issues = usable_raw_text(skill.get("raw_text"))
            if not raw_text_ok:
                skill_raw_text_issues.append(
                    {
                        "skill": label,
                        "issues": raw_text_issues,
                    }
                )

            skill_source_ref_gaps = source_ref_field_gaps(skill.get("source_refs"))
            if skill_source_ref_gaps:
                skill_source_ref_issues.append(
                    {
                        "skill": label,
                        "issues": skill_source_ref_gaps,
                    }
                )

    return {
        "records_missing_skills": missing_skills,
        "records_with_source_ref_issues": missing_character_source_refs,
        "records_with_raw_text_issues": missing_character_raw_text,
        "records_missing_parse_confidence": missing_parse_confidence,
        "skills_with_source_ref_issues": skill_source_ref_issues,
        "skills_with_raw_text_issues": skill_raw_text_issues,
    }


def build_report(bundle_path: Path, overview_path: Path) -> dict[str, Any]:
    raw_characters = load_raw_characters(overview_path)
    normalized_records = load_normalized_records(bundle_path)

    raw_duplicates = duplicate_names(raw_characters)
    normalized_duplicates = duplicate_names(normalized_records)

    raw_by_name = {record["name"]: record for record in raw_characters if isinstance(record.get("name"), str)}
    normalized_by_name = {
        record["name"]: record for record in normalized_records if isinstance(record.get("name"), str)
    }
    raw_names = set(raw_by_name)
    normalized_names = set(normalized_by_name)

    excluded_names = sorted(raw_names - normalized_names)
    unexpected_included_names = sorted(normalized_names - raw_names)

    intentional_exclusions: list[dict[str, Any]] = []
    silent_drops: list[dict[str, Any]] = []
    for name in excluded_names:
        skill_count = raw_skill_count(raw_by_name[name])
        item = {
            "name": name,
            "raw_skill_count": skill_count,
        }
        if skill_count == 0:
            intentional_exclusions.append(item)
        else:
            silent_drops.append(item)

    record_validation = validate_records(normalized_records)
    all_source_ref_issues = (
        record_validation["records_with_source_ref_issues"] + record_validation["skills_with_source_ref_issues"]
    )
    all_raw_text_issues = (
        record_validation["records_with_raw_text_issues"] + record_validation["skills_with_raw_text_issues"]
    )

    checks = {
        "no_duplicate_raw_names": not raw_duplicates,
        "no_duplicate_normalized_names": not normalized_duplicates,
        "no_unexpected_included_names": not unexpected_included_names,
        "no_silent_drops_found": not silent_drops,
        "all_included_records_have_nonempty_skills": not record_validation["records_missing_skills"],
        "all_included_records_have_usable_source_refs": not all_source_ref_issues,
        "all_included_records_have_usable_raw_text": not all_raw_text_issues,
        "all_included_records_have_parse_confidence": not record_validation["records_missing_parse_confidence"],
    }

    failed = not all(checks.values())
    return {
        "status": "failed" if failed else "ok",
        "bundle_path": str(bundle_path),
        "raw_overview_path": str(overview_path),
        "included_record_count": len(normalized_records),
        "raw_record_count": len(raw_characters),
        "excluded_raw_names": [item["name"] for item in intentional_exclusions + silent_drops],
        "intentional_exclusions": intentional_exclusions,
        "silent_drops": silent_drops,
        "unexpected_included_names": unexpected_included_names,
        "duplicate_raw_names": raw_duplicates,
        "duplicate_normalized_names": normalized_duplicates,
        "record_validation": record_validation,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the normalized character bundle against the raw overview snapshot."
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH, help="Path to characters.json")
    parser.add_argument(
        "--overview",
        type=Path,
        default=DEFAULT_OVERVIEW_PATH,
        help="Path to snapshots/raw/site_capture/latest/characters/overview.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.bundle.resolve(), args.overview.resolve())
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

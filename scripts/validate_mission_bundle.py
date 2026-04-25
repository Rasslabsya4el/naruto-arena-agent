#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "snapshots" / "raw" / "site_capture" / "latest"
DEFAULT_BUNDLE_PATH = REPO_ROOT / "data" / "normalized" / "missions.json"
DEFAULT_MANIFEST_PATH = RAW_ROOT / "manifest.json"
DEFAULT_GROUP_DIR = RAW_ROOT / "missions" / "groups"
DEFAULT_DETAIL_DIR = RAW_ROOT / "missions" / "details"
DEFAULT_COMMON_SCHEMA_PATH = REPO_ROOT / "schemas" / "_common.schema.json"
CANONICAL_DOMAIN = "www.naruto-arena.site"
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
    if not path.exists():
        raise ValueError(f"Expected {expected} at {path}")


def require_file(path: Path, expected: str) -> None:
    require_path(path, expected)
    if not path.is_file():
        raise ValueError(f"Expected {expected} file at {path}")


def require_dir(path: Path, expected: str) -> None:
    require_path(path, expected)
    if not path.is_dir():
        raise ValueError(f"Expected {expected} directory at {path}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_normalized_records(path: Path) -> list[dict[str, Any]]:
    require_file(path, "normalized mission bundle")
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected normalized mission bundle to be a JSON array, found {type(payload).__name__}")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Expected every normalized mission bundle item to be an object")
    return payload


def load_manifest_detail_slugs(path: Path) -> list[str]:
    require_file(path, "site capture manifest")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected manifest payload to be an object, found {type(payload).__name__}")
    missions = payload.get("missions")
    if not isinstance(missions, dict):
        raise ValueError("Expected manifest payload to contain object missions")
    detail_slugs = missions.get("detail_slugs")
    if not isinstance(detail_slugs, list):
        raise ValueError("Expected manifest payload to contain list missions.detail_slugs")
    invalid = [slug for slug in detail_slugs if not isinstance(slug, str) or not slug.strip()]
    if invalid:
        raise ValueError("Expected every manifest mission detail slug to be a non-empty string")
    return detail_slugs


def load_group_items(group_dir: Path) -> dict[str, Any]:
    require_dir(group_dir, "mission groups")
    group_paths = sorted(group_dir.glob("*.json"))
    if not group_paths:
        raise ValueError(f"No mission group snapshot files found in {group_dir}")

    group_items_by_slug: dict[str, dict[str, Any]] = {}
    duplicate_group_slugs: list[str] = []

    for group_path in group_paths:
        payload = load_json(group_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected mission group payload {group_path} to be an object")
        page_props = payload.get("pageProps")
        if not isinstance(page_props, dict):
            raise ValueError(f"Expected mission group payload {group_path} to contain object pageProps")
        items = page_props.get("animeMissions")
        if items is None and "__N_REDIRECT" in page_props:
            continue
        if not isinstance(items, list):
            raise ValueError(f"Expected mission group payload {group_path} to contain list pageProps.animeMissions")

        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Expected mission group item in {group_path} to be an object")
            slug = item.get("linkTo")
            name = item.get("name")
            if not isinstance(slug, str) or not slug.strip():
                raise ValueError(f"Expected mission group item in {group_path} to contain non-empty linkTo")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Expected mission group item {slug!r} in {group_path} to contain non-empty name")
            if slug in group_items_by_slug:
                duplicate_group_slugs.append(slug)
                continue
            group_items_by_slug[slug] = {
                "slug": slug,
                "name": name,
                "group_path": str(group_path),
            }

    return {
        "items_by_slug": group_items_by_slug,
        "duplicate_slugs": sorted(set(duplicate_group_slugs)),
        "count": len(group_items_by_slug),
    }


def load_detail_records(detail_dir: Path) -> dict[str, Any]:
    require_dir(detail_dir, "mission detail snapshots")
    detail_paths = sorted(detail_dir.glob("*.json"))
    if not detail_paths:
        raise ValueError(f"No mission detail snapshot files found in {detail_dir}")

    records_by_slug: dict[str, dict[str, Any]] = {}
    for detail_path in detail_paths:
        payload = load_json(detail_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected mission detail payload {detail_path} to be an object")
        records_by_slug[detail_path.stem] = payload

    return {
        "records_by_slug": records_by_slug,
        "count": len(records_by_slug),
    }


def load_record_id_pattern(path: Path) -> re.Pattern[str]:
    require_file(path, "shared schema")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected shared schema payload to be an object, found {type(payload).__name__}")
    defs = payload.get("$defs")
    if not isinstance(defs, dict):
        raise ValueError("Expected shared schema payload to contain object $defs")
    record_id = defs.get("recordId")
    if not isinstance(record_id, dict):
        raise ValueError("Expected shared schema payload to contain object $defs.recordId")
    pattern = record_id.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("Expected shared schema payload to contain non-empty $defs.recordId.pattern")
    return re.compile(pattern)


def detail_state_from_record(detail_record: dict[str, Any]) -> str:
    page_props = detail_record.get("pageProps", {})
    if "missionStatus" in page_props:
        return "mission_status"
    if "__N_REDIRECT" in page_props:
        return "redirect"
    if detail_record.get("page") == "/_error" and not page_props:
        return "error_page"
    if detail_record.get("page") == "/" and detail_record.get("final_url") == "https://www.naruto-arena.site/":
        return "unexpected_home"
    if not page_props:
        return "empty"
    return "other"


def source_ref_field_gaps(source_refs: Any) -> list[dict[str, Any]]:
    if not isinstance(source_refs, list) or not source_refs:
        return [{"index": None, "issues": ["source_refs_missing"]}]

    gaps: list[dict[str, Any]] = []
    for index, source_ref in enumerate(source_refs):
        if not isinstance(source_ref, dict):
            gaps.append({"index": index, "issues": ["source_ref_not_object"]})
            continue

        issues = [
            f"missing_{field}"
            for field in REQUIRED_SOURCE_REF_FIELDS
            if not isinstance(source_ref.get(field), str) or not source_ref[field].strip()
        ]

        canonical_domain = source_ref.get("canonical_domain")
        if canonical_domain != CANONICAL_DOMAIN:
            issues.append("non_canonical_domain")

        url = source_ref.get("url")
        if isinstance(url, str) and url.strip():
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.netloc != CANONICAL_DOMAIN:
                issues.append("non_canonical_url")

        snapshot_path = source_ref.get("snapshot_path")
        if isinstance(snapshot_path, str) and snapshot_path.strip():
            snapshot_file = REPO_ROOT / snapshot_path
            if not snapshot_file.is_file():
                issues.append("snapshot_file_missing")
            else:
                expected_hash = source_ref.get("raw_text_hash")
                if isinstance(expected_hash, str) and expected_hash.strip():
                    actual_hash = sha256_file(snapshot_file)
                    if actual_hash != expected_hash:
                        issues.append("raw_text_hash_mismatch")

        if issues:
            gaps.append({"index": index, "issues": sorted(set(issues))})

    return gaps


def usable_raw_text(raw_text: Any, source_ref_ids: set[str]) -> tuple[bool, list[str]]:
    if not isinstance(raw_text, dict):
        return False, ["raw_text_not_object"]

    issues: list[str] = []

    primary = raw_text.get("primary")
    if not isinstance(primary, str) or not primary.strip():
        issues.append("missing_primary")

    fragments = raw_text.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        issues.append("missing_fragments")
        return False, sorted(set(issues))

    usable_fragment_found = False
    for fragment in fragments:
        if not isinstance(fragment, dict):
            issues.append("fragment_not_object")
            continue

        field = fragment.get("field")
        text = fragment.get("text")
        source_ref_id = fragment.get("source_ref_id")
        if not isinstance(field, str) or not field.strip():
            issues.append("fragment_missing_field")
        if not isinstance(text, str) or not text.strip():
            issues.append("fragment_missing_text")
        if not isinstance(source_ref_id, str) or not source_ref_id.strip():
            issues.append("fragment_missing_source_ref_id")
        elif source_ref_id not in source_ref_ids:
            issues.append("fragment_source_ref_not_found")

        if (
            isinstance(field, str)
            and field.strip()
            and isinstance(text, str)
            and text.strip()
            and isinstance(source_ref_id, str)
            and source_ref_id.strip()
            and source_ref_id in source_ref_ids
        ):
            usable_fragment_found = True

    if not usable_fragment_found:
        issues.append("no_usable_fragments")

    return not issues, sorted(set(issues))


def usable_parse_meta(parse_meta: Any) -> tuple[bool, list[str]]:
    if not isinstance(parse_meta, dict):
        return False, ["parse_not_object"]

    issues: list[str] = []

    parser_version = parse_meta.get("parser_version")
    if not isinstance(parser_version, str) or not parser_version.strip():
        issues.append("missing_parser_version")

    confidence = parse_meta.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        issues.append("missing_confidence")

    confidence_reasons = parse_meta.get("confidence_reasons")
    if not isinstance(confidence_reasons, list) or not confidence_reasons:
        issues.append("missing_confidence_reasons")
    elif not all(isinstance(reason, str) and reason.strip() for reason in confidence_reasons):
        issues.append("invalid_confidence_reasons")

    ambiguity_flags = parse_meta.get("ambiguity_flags")
    if not isinstance(ambiguity_flags, list):
        issues.append("missing_ambiguity_flags")

    unsupported_version = parse_meta.get("unsupported_version")
    if not isinstance(unsupported_version, bool):
        issues.append("missing_unsupported_version")

    return not issues, sorted(set(issues))


def extract_detail_slug(record: dict[str, Any]) -> str | None:
    source_refs = record.get("source_refs")
    if not isinstance(source_refs, list):
        return None

    preferred_refs = [
        source_ref
        for source_ref in source_refs
        if isinstance(source_ref, dict) and source_ref.get("section") == "detail_page"
    ]
    for source_ref in preferred_refs + [ref for ref in source_refs if isinstance(ref, dict)]:
        snapshot_path = source_ref.get("snapshot_path")
        if isinstance(snapshot_path, str) and snapshot_path.strip():
            snapshot_file = Path(snapshot_path)
            if snapshot_file.name.endswith(".json"):
                return snapshot_file.stem

        url = source_ref.get("url")
        if isinstance(url, str) and url.strip():
            parsed = urlparse(url)
            marker = "/mission/"
            if marker in parsed.path:
                return parsed.path.split(marker, 1)[1].strip("/") or None

    return None


def extract_source_ref_ids(source_refs: Any) -> set[str]:
    if not isinstance(source_refs, list):
        return set()
    return {
        source_ref["source_id"]
        for source_ref in source_refs
        if isinstance(source_ref, dict)
        and isinstance(source_ref.get("source_id"), str)
        and source_ref["source_id"].strip()
    }


def build_expected_detail_flag(detail_state: str) -> str | None:
    if detail_state == "mission_status":
        return None
    return f"detail_payload_{detail_state}"


def validate_record_ids(record: dict[str, Any], record_id_pattern: re.Pattern[str]) -> list[str]:
    issues: list[str] = []

    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id_pattern.fullmatch(record_id):
        issues.append("invalid_record_id")

    requirements = record.get("requirements")
    if isinstance(requirements, list):
        for requirement in requirements:
            if not isinstance(requirement, dict):
                issues.append("requirement_not_object")
                continue
            requirement_id = requirement.get("requirement_id")
            if not isinstance(requirement_id, str) or not record_id_pattern.fullmatch(requirement_id):
                issues.append("invalid_requirement_id")

    source_refs = record.get("source_refs")
    if isinstance(source_refs, list):
        for source_ref in source_refs:
            if not isinstance(source_ref, dict):
                continue
            source_id = source_ref.get("source_id")
            if not isinstance(source_id, str) or not record_id_pattern.fullmatch(source_id):
                issues.append("invalid_source_id")

    raw_text = record.get("raw_text")
    if isinstance(raw_text, dict):
        fragments = raw_text.get("fragments")
        if isinstance(fragments, list):
            for fragment in fragments:
                if not isinstance(fragment, dict):
                    continue
                source_ref_id = fragment.get("source_ref_id")
                if not isinstance(source_ref_id, str) or not record_id_pattern.fullmatch(source_ref_id):
                    issues.append("invalid_fragment_source_ref_id")

    return sorted(set(issues))


def validate_records(
    records: list[dict[str, Any]],
    detail_records_by_slug: dict[str, dict[str, Any]],
    record_id_pattern: re.Pattern[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    records_missing_level_requirement: list[str] = []
    records_with_id_issues: list[dict[str, Any]] = []
    records_with_source_ref_issues: list[dict[str, Any]] = []
    records_with_raw_text_issues: list[dict[str, Any]] = []
    records_with_parse_issues: list[dict[str, Any]] = []
    unknown_requirement_support_issues: list[dict[str, Any]] = []
    known_requirement_without_detail_evidence: list[dict[str, Any]] = []
    normalized_slug_extraction_issues: list[str] = []
    duplicate_normalized_slugs: list[str] = []

    normalized_slug_counter: Counter[str] = Counter()
    unknown_requirement_record_count = 0
    supported_unknown_requirement_count = 0
    unknown_requirement_detail_states: Counter[str] = Counter()

    for record in records:
        name = record.get("name") if isinstance(record.get("name"), str) else record.get("id", "<unknown>")

        level_requirement = record.get("level_requirement")
        if not isinstance(level_requirement, int) or isinstance(level_requirement, bool) or level_requirement < 1:
            records_missing_level_requirement.append(str(name))

        id_issues = validate_record_ids(record, record_id_pattern)
        if id_issues:
            records_with_id_issues.append({"name": str(name), "issues": id_issues})

        source_refs = record.get("source_refs")
        source_ref_ids = extract_source_ref_ids(source_refs)
        source_ref_issues = source_ref_field_gaps(source_refs)
        if not isinstance(source_refs, list) or not any(
            isinstance(source_ref, dict) and source_ref.get("section") == "detail_page" for source_ref in source_refs
        ):
            source_ref_issues.append({"index": None, "issues": ["missing_detail_page_source_ref"]})
        if not isinstance(source_refs, list) or not any(
            isinstance(source_ref, dict) and source_ref.get("section") == "group_page" for source_ref in source_refs
        ):
            source_ref_issues.append({"index": None, "issues": ["missing_group_page_source_ref"]})
        if source_ref_issues:
            records_with_source_ref_issues.append(
                {
                    "name": str(name),
                    "issues": source_ref_issues,
                }
            )

        raw_text_ok, raw_text_issues = usable_raw_text(record.get("raw_text"), source_ref_ids)
        if not raw_text_ok:
            records_with_raw_text_issues.append(
                {
                    "name": str(name),
                    "issues": raw_text_issues,
                }
            )

        parse_ok, parse_issues = usable_parse_meta(record.get("parse"))
        if not parse_ok:
            records_with_parse_issues.append(
                {
                    "name": str(name),
                    "issues": parse_issues,
                }
            )

        detail_slug = extract_detail_slug(record)
        if detail_slug is None:
            normalized_slug_extraction_issues.append(str(name))
            continue

        normalized_slug_counter[detail_slug] += 1
        detail_record = detail_records_by_slug.get(detail_slug)
        if detail_record is None:
            records_with_source_ref_issues.append(
                {
                    "name": str(name),
                    "issues": [{"index": None, "issues": ["detail_snapshot_not_found_for_slug"]}],
                }
            )
            continue

        detail_state = detail_state_from_record(detail_record)
        requirements = record.get("requirements")
        unknown_requirements = [
            requirement
            for requirement in requirements
            if isinstance(requirement, dict) and requirement.get("requirement_type") == "unknown"
        ] if isinstance(requirements, list) else []

        if unknown_requirements:
            unknown_requirement_record_count += 1
            unknown_requirement_detail_states[detail_state] += 1

            if detail_state == "mission_status":
                unknown_requirement_support_issues.append(
                    {
                        "name": str(name),
                        "slug": detail_slug,
                        "detail_state": detail_state,
                        "issues": ["detail_snapshot_exposes_mission_status"],
                    }
                )
            else:
                supported_unknown_requirement_count += 1

            expected_flag = build_expected_detail_flag(detail_state)
            for requirement in unknown_requirements:
                flag_codes = {
                    flag.get("code")
                    for flag in requirement.get("ambiguity_flags", [])
                    if isinstance(flag, dict) and isinstance(flag.get("code"), str)
                }
                missing_flags: list[str] = []
                if "objective_text_missing" not in flag_codes:
                    missing_flags.append("missing_objective_text_missing_flag")
                if expected_flag and expected_flag not in flag_codes:
                    missing_flags.append(f"missing_{expected_flag}_flag")
                if missing_flags:
                    unknown_requirement_support_issues.append(
                        {
                            "name": str(name),
                            "slug": detail_slug,
                            "detail_state": detail_state,
                            "issues": missing_flags,
                        }
                    )
        elif detail_state != "mission_status":
            known_requirement_without_detail_evidence.append(
                {
                    "name": str(name),
                    "slug": detail_slug,
                    "detail_state": detail_state,
                }
            )

    duplicate_normalized_slugs = sorted(
        slug for slug, count in normalized_slug_counter.items() if count > 1
    )

    metrics = {
        "unknown_requirement_record_count": unknown_requirement_record_count,
        "supported_unknown_requirement_count": supported_unknown_requirement_count,
        "unknown_requirement_detail_states": dict(unknown_requirement_detail_states),
        "duplicate_normalized_slugs": duplicate_normalized_slugs,
    }
    record_validation = {
        "records_missing_level_requirement": records_missing_level_requirement,
        "records_with_id_issues": records_with_id_issues,
        "records_with_source_ref_issues": records_with_source_ref_issues,
        "records_with_raw_text_issues": records_with_raw_text_issues,
        "records_with_parse_issues": records_with_parse_issues,
        "unknown_requirement_support_issues": unknown_requirement_support_issues,
        "known_requirement_without_detail_evidence": known_requirement_without_detail_evidence,
        "normalized_slug_extraction_issues": normalized_slug_extraction_issues,
    }
    return record_validation, metrics


def build_report(
    bundle_path: Path,
    manifest_path: Path,
    group_dir: Path,
    detail_dir: Path,
    common_schema_path: Path,
) -> dict[str, Any]:
    normalized_records = load_normalized_records(bundle_path)
    manifest_detail_slugs = load_manifest_detail_slugs(manifest_path)
    group_data = load_group_items(group_dir)
    detail_data = load_detail_records(detail_dir)
    record_id_pattern = load_record_id_pattern(common_schema_path)

    manifest_detail_set = set(manifest_detail_slugs)
    group_slug_set = set(group_data["items_by_slug"])
    detail_slug_set = set(detail_data["records_by_slug"])

    raw_capture_alignment = {
        "manifest_missing_from_groups": sorted(manifest_detail_set - group_slug_set),
        "groups_missing_from_manifest": sorted(group_slug_set - manifest_detail_set),
        "manifest_missing_from_detail_files": sorted(manifest_detail_set - detail_slug_set),
        "detail_files_missing_from_manifest": sorted(detail_slug_set - manifest_detail_set),
    }

    detail_state_counts = Counter(
        detail_state_from_record(detail_record)
        for detail_record in detail_data["records_by_slug"].values()
    )

    record_validation, metrics = validate_records(
        normalized_records,
        detail_data["records_by_slug"],
        record_id_pattern,
    )

    normalized_slugs = {
        extract_detail_slug(record)
        for record in normalized_records
        if extract_detail_slug(record) is not None
    }
    silent_drops = [
        group_data["items_by_slug"].get(slug, {"slug": slug, "name": slug})
        for slug in sorted(manifest_detail_set - normalized_slugs)
    ]
    unexpected_included_records = [
        {
            "slug": slug,
            "name": next(
                (
                    record.get("name")
                    for record in normalized_records
                    if extract_detail_slug(record) == slug and isinstance(record.get("name"), str)
                ),
                slug,
            ),
        }
        for slug in sorted(normalized_slugs - manifest_detail_set)
    ]

    checks = {
        "raw_capture_sets_align": not any(raw_capture_alignment.values()),
        "counts_align": len(normalized_records)
        == len(manifest_detail_slugs)
        == group_data["count"]
        == detail_data["count"],
        "no_duplicate_group_slugs": not group_data["duplicate_slugs"],
        "no_duplicate_normalized_slugs": not metrics["duplicate_normalized_slugs"],
        "no_unexpected_included_records": not unexpected_included_records,
        "no_silent_drops_found": not silent_drops,
        "all_unknown_requirement_records_supported_by_raw_detail_evidence": not record_validation[
            "unknown_requirement_support_issues"
        ],
        "no_known_requirement_records_without_detail_evidence": not record_validation[
            "known_requirement_without_detail_evidence"
        ],
        "all_records_have_level_requirement": not record_validation["records_missing_level_requirement"],
        "all_record_related_ids_schema_safe": not record_validation["records_with_id_issues"],
        "all_records_have_usable_source_refs": not record_validation["records_with_source_ref_issues"]
        and not record_validation["normalized_slug_extraction_issues"],
        "all_records_have_usable_raw_text": not record_validation["records_with_raw_text_issues"],
        "all_records_have_usable_parse_meta": not record_validation["records_with_parse_issues"],
    }

    failed = not all(checks.values())
    return {
        "status": "failed" if failed else "ok",
        "bundle_path": str(bundle_path),
        "manifest_path": str(manifest_path),
        "group_dir": str(group_dir),
        "detail_dir": str(detail_dir),
        "included_record_count": len(normalized_records),
        "manifest_detail_count": len(manifest_detail_slugs),
        "group_item_count": group_data["count"],
        "detail_file_count": detail_data["count"],
        "detail_state_counts": dict(detail_state_counts),
        "unknown_requirement_record_count": metrics["unknown_requirement_record_count"],
        "supported_unknown_requirement_count": metrics["supported_unknown_requirement_count"],
        "unknown_requirement_detail_states": metrics["unknown_requirement_detail_states"],
        "missing_level_requirement_count": len(record_validation["records_missing_level_requirement"]),
        "raw_capture_alignment": raw_capture_alignment,
        "silent_drops": silent_drops,
        "unexpected_included_records": unexpected_included_records,
        "duplicate_group_slugs": group_data["duplicate_slugs"],
        "duplicate_normalized_slugs": metrics["duplicate_normalized_slugs"],
        "record_validation": record_validation,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the normalized mission bundle against the raw mission snapshot set."
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH, help="Path to missions.json")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to snapshots/raw/site_capture/latest/manifest.json",
    )
    parser.add_argument(
        "--groups",
        type=Path,
        default=DEFAULT_GROUP_DIR,
        help="Path to snapshots/raw/site_capture/latest/missions/groups",
    )
    parser.add_argument(
        "--details",
        type=Path,
        default=DEFAULT_DETAIL_DIR,
        help="Path to snapshots/raw/site_capture/latest/missions/details",
    )
    parser.add_argument(
        "--common-schema",
        type=Path,
        default=DEFAULT_COMMON_SCHEMA_PATH,
        help="Path to schemas/_common.schema.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        bundle_path=args.bundle.resolve(),
        manifest_path=args.manifest.resolve(),
        group_dir=args.groups.resolve(),
        detail_dir=args.details.resolve(),
        common_schema_path=args.common_schema.resolve(),
    )
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

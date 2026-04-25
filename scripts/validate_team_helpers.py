#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import search_characters
import team_candidate_report


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SEARCH_SCRIPT = SCRIPTS_DIR / "search_characters.py"
TEAM_REPORT_SCRIPT = SCRIPTS_DIR / "team_candidate_report.py"
EXPECTED_REFERENCES_DIR = REPO_ROOT / "skills" / "naruto-arena-team-builder" / "references"
CANONICAL_SOURCE_PREFIX = "https://www.naruto-arena.site/"
REPRESENTATIVE_SEARCH_ARGS = [
    "Haruno Sakura",
    "--role-hint",
    "sustain",
    "--effect-type",
    "heal",
    "--tag",
    "character.capability.protect_effects",
    "--exclude-chakra-type",
    "bloodline",
    "--limit",
    "5",
]
REPRESENTATIVE_TEAM_ARGS = [
    "Uzumaki Naruto",
    "Haruno Sakura",
    "Hatake Kakashi",
]
FORBIDDEN_OUTPUT_KEYS = {
    "authoritative_score",
    "authoritative_scores",
    "best_team",
    "best_teams",
    "recommended_team",
    "score",
    "scores",
    "selected_team",
    "team_database",
}
FORBIDDEN_SOURCE_SNIPPETS = (
    "data/normalized",
    "data\\normalized",
)
FORBIDDEN_TEAM_IO_SNIPPETS = (
    "open(",
    "read_text(",
    "read_bytes(",
    "json.load(",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the accepted Naruto Arena helper layer by checking skill-local runtime boundaries, "
            "representative search transparency, team-report transparency, and conservative non-hardcoded behavior."
        )
    )
    return parser.parse_args()


def build_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "check": name,
        "status": "passed" if passed else "failed",
        "detail": detail,
    }


def section_status(checks: list[dict[str, Any]]) -> str:
    return "ok" if all(check["status"] == "passed" for check in checks) else "failed"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_python_json(script_path: Path, args: list[str], *, cwd: Path) -> dict[str, Any]:
    command = [sys.executable, "-X", "utf8", str(script_path), *args]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )

    payload = None
    parse_error = None
    stdout = completed.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)

    return {
        "command": subprocess.list2cmdline(command),
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": completed.stderr.strip(),
        "payload": payload,
        "parse_error": parse_error,
    }


def collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    stack = [value]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            keys.update(str(key) for key in current.keys())
            stack.extend(current.values())
            continue
        if isinstance(current, list):
            stack.extend(current)

    return keys


def source_refs_are_canonical(source_refs: list[dict[str, Any]]) -> bool:
    return bool(source_refs) and all(
        isinstance(item, dict)
        and isinstance(item.get("url"), str)
        and item["url"].startswith(CANONICAL_SOURCE_PREFIX)
        for item in source_refs
    )


def find_exact_search_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for result in results:
        query_match = result.get("query_match")
        if isinstance(query_match, dict) and query_match.get("kind") == "exact":
            return result
    return None


def find_member(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    members = payload.get("members")
    if not isinstance(members, list):
        return None
    for member in members:
        if isinstance(member, dict) and member.get("name") == name:
            return member
    return None


def validate_runtime_boundary() -> dict[str, Any]:
    search_source = read_source(SEARCH_SCRIPT)
    team_source = read_source(TEAM_REPORT_SCRIPT)
    defaults = search_characters.load_reference_context.__defaults__ or ()

    checks = [
        build_check(
            "search helper default references dir is skill-local bundle",
            search_characters.DEFAULT_REFERENCES_DIR.resolve() == EXPECTED_REFERENCES_DIR.resolve(),
            f"observed={search_characters.DEFAULT_REFERENCES_DIR.resolve()}",
        ),
        build_check(
            "search helper loader default reuses DEFAULT_REFERENCES_DIR",
            defaults == (search_characters.DEFAULT_REFERENCES_DIR,),
            f"observed_defaults={[str(item) for item in defaults]}",
        ),
        build_check(
            "team report reuses shared load_reference_context",
            team_candidate_report.load_reference_context is search_characters.load_reference_context,
            "team_candidate_report imports load_reference_context directly from search_characters",
        ),
        build_check(
            "helper sources do not mention project normalized data roots",
            all(snippet not in search_source and snippet not in team_source for snippet in FORBIDDEN_SOURCE_SNIPPETS),
            "checked helper source text for data/normalized path fragments",
        ),
        build_check(
            "team report source avoids direct file-read primitives outside shared bundle loader",
            all(snippet not in team_source for snippet in FORBIDDEN_TEAM_IO_SNIPPETS),
            "checked team_candidate_report.py for open/read_text/read_bytes/json.load usage",
        ),
    ]

    return {
        "status": section_status(checks),
        "checks": checks,
    }


def validate_search_helper() -> tuple[dict[str, Any], dict[str, Any] | None]:
    run = run_python_json(SEARCH_SCRIPT, REPRESENTATIVE_SEARCH_ARGS, cwd=REPO_ROOT.parent)
    payload = run["payload"] if isinstance(run["payload"], dict) else None
    results = payload.get("results", []) if isinstance(payload, dict) else []
    exact_result = find_exact_search_result(results) if isinstance(results, list) else None

    exact_role_hints = exact_result.get("role_hints", []) if isinstance(exact_result, dict) else []
    exact_tags = exact_result.get("tags", []) if isinstance(exact_result, dict) else []
    exact_effect_types = exact_result.get("effect_types", []) if isinstance(exact_result, dict) else []
    exact_chakra_profile = exact_result.get("chakra_profile", {}) if isinstance(exact_result, dict) else {}
    exact_progression = exact_result.get("progression", {}) if isinstance(exact_result, dict) else {}
    exact_data_quality = exact_result.get("data_quality", {}) if isinstance(exact_result, dict) else {}
    exact_provenance = exact_result.get("provenance", {}) if isinstance(exact_result, dict) else {}
    exact_tag_ids = {
        tag.get("tag_id")
        for tag in exact_tags
        if isinstance(tag, dict)
    }
    exact_effect_type_ids = {
        effect_type.get("effect_type")
        for effect_type in exact_effect_types
        if isinstance(effect_type, dict)
    }
    exact_role_hint_ids = {
        role_hint.get("role_hint")
        for role_hint in exact_role_hints
        if isinstance(role_hint, dict)
    }
    payload_keys = collect_keys(payload or {})

    checks = [
        build_check(
            "search helper command exits successfully from outside repo root",
            run["returncode"] == 0,
            f"returncode={run['returncode']} cwd={run['cwd']}",
        ),
        build_check(
            "search helper returns parseable JSON payload",
            payload is not None,
            "stdout parsed as JSON" if payload is not None else f"parse_error={run['parse_error']} stderr={run['stderr']}",
        ),
        build_check(
            "search payload reports skill-local references_dir",
            isinstance(payload, dict) and payload.get("references_dir") == str(EXPECTED_REFERENCES_DIR),
            f"observed={payload.get('references_dir') if isinstance(payload, dict) else None}",
        ),
        build_check(
            "search payload returns at least one exact match result",
            isinstance(results, list) and bool(results) and exact_result is not None,
            f"total_matches={payload.get('total_matches') if isinstance(payload, dict) else None}",
        ),
        build_check(
            "exact search result keeps query-match, tag, effect, chakra, data-quality, and provenance surfaces",
            isinstance(exact_result, dict)
            and all(
                key in exact_result
                for key in (
                    "query_match",
                    "role_hints",
                    "tags",
                    "effect_types",
                    "effect_families",
                    "skill_classes",
                    "progression",
                    "chakra_profile",
                    "data_quality",
                    "provenance",
                )
            ),
            f"exact_result_keys={sorted(exact_result.keys()) if isinstance(exact_result, dict) else []}",
        ),
        build_check(
            "exact search result exposes derived progression unlock surface",
            isinstance(exact_progression, dict)
            and exact_progression.get("classification") in {"base_or_unlisted_mission_reward", "mission_reward_unlock"}
            and "minimum_rank_index" in exact_progression,
            f"progression={exact_progression}",
        ),
        build_check(
            "exact search result preserves requested transparency filters",
            "character.capability.protect_effects" in exact_tag_ids
            and "heal" in exact_effect_type_ids
            and "sustain" in exact_role_hint_ids
            and isinstance(exact_chakra_profile.get("component_totals"), dict)
            and exact_chakra_profile["component_totals"].get("bloodline") == 0,
            (
                f"role_hints={sorted(item for item in exact_role_hint_ids if item)} "
                f"tags={sorted(item for item in exact_tag_ids if item)} "
                f"effect_types={sorted(item for item in exact_effect_type_ids if item)}"
            ),
        ),
        build_check(
            "exact search result keeps visible data-quality warnings",
            isinstance(exact_data_quality, dict)
            and bool(exact_data_quality.get("tag_ids"))
            and bool(exact_data_quality.get("warnings")),
            f"data_quality_tags={exact_data_quality.get('tag_ids') if isinstance(exact_data_quality, dict) else None}",
        ),
        build_check(
            "exact search result keeps canonical provenance sources",
            isinstance(exact_provenance, dict)
            and bool(exact_provenance.get("record_source_ref_ids"))
            and source_refs_are_canonical(exact_provenance.get("record_sources", [])),
            f"record_source_ref_ids={exact_provenance.get('record_source_ref_ids') if isinstance(exact_provenance, dict) else None}",
        ),
        build_check(
            "search payload omits authoritative-score and best-team fields",
            FORBIDDEN_OUTPUT_KEYS.isdisjoint(payload_keys),
            f"present_forbidden_keys={sorted(FORBIDDEN_OUTPUT_KEYS.intersection(payload_keys))}",
        ),
    ]

    section = {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "total_matches": payload.get("total_matches") if isinstance(payload, dict) else None,
            "displayed_count": payload.get("displayed_count") if isinstance(payload, dict) else None,
            "exact_result_id": exact_result.get("id") if isinstance(exact_result, dict) else None,
            "exact_result_name": exact_result.get("name") if isinstance(exact_result, dict) else None,
            "data_quality_tags": exact_data_quality.get("tag_ids") if isinstance(exact_data_quality, dict) else None,
            "record_source_ref_ids": exact_provenance.get("record_source_ref_ids") if isinstance(exact_provenance, dict) else None,
        },
    }
    return section, payload


def validate_team_report() -> tuple[dict[str, Any], dict[str, Any] | None]:
    run = run_python_json(TEAM_REPORT_SCRIPT, REPRESENTATIVE_TEAM_ARGS, cwd=REPO_ROOT.parent)
    payload = run["payload"] if isinstance(run["payload"], dict) else None
    members = payload.get("members", []) if isinstance(payload, dict) else []
    resolutions = payload.get("resolutions", []) if isinstance(payload, dict) else []
    chakra_curve = payload.get("chakra_curve", {}) if isinstance(payload, dict) else {}
    weakness_notes = payload.get("weakness_notes", []) if isinstance(payload, dict) else []
    substitution_hooks = payload.get("substitution_hooks", []) if isinstance(payload, dict) else []
    provenance_hooks = payload.get("provenance_hooks", {}) if isinstance(payload, dict) else {}
    data_quality_warnings = payload.get("data_quality_warnings", {}) if isinstance(payload, dict) else {}
    naruto_member = find_member(payload or {}, "Uzumaki Naruto")
    payload_keys = collect_keys(payload or {})

    shared_pressure_notes = [
        note
        for note in chakra_curve.get("notes", [])
        if isinstance(note, dict) and note.get("note_type") == "shared_chakra_pressure"
    ] if isinstance(chakra_curve, dict) else []
    weakness_note_ids = [
        note.get("note_id")
        for note in weakness_notes
        if isinstance(note, dict)
    ] if isinstance(weakness_notes, list) else []
    provenance_members = provenance_hooks.get("members", []) if isinstance(provenance_hooks, dict) else []

    checks = [
        build_check(
            "team report command exits successfully from outside repo root",
            run["returncode"] == 0,
            f"returncode={run['returncode']} cwd={run['cwd']}",
        ),
        build_check(
            "team report returns parseable JSON payload",
            payload is not None,
            "stdout parsed as JSON" if payload is not None else f"parse_error={run['parse_error']} stderr={run['stderr']}",
        ),
        build_check(
            "team report resolves all requested members transparently",
            isinstance(payload, dict)
            and payload.get("status") == "ok"
            and payload.get("resolved_member_count") == len(REPRESENTATIVE_TEAM_ARGS)
            and isinstance(resolutions, list)
            and len(resolutions) == len(REPRESENTATIVE_TEAM_ARGS)
            and all(
                isinstance(item, dict)
                and item.get("status") == "resolved"
                and isinstance(item.get("query_match"), dict)
                and item["query_match"].get("kind") == "exact"
                for item in resolutions
            ),
            f"resolved_member_count={payload.get('resolved_member_count') if isinstance(payload, dict) else None}",
        ),
        build_check(
            "team members preserve resolved-member surfaces",
            isinstance(members, list)
            and len(members) == len(REPRESENTATIVE_TEAM_ARGS)
            and all(
                isinstance(member, dict)
                and all(
                    key in member
                    for key in (
                        "id",
                        "name",
                        "role_hints",
                        "progression",
                        "chakra_profile",
                        "skill_summaries",
                        "data_quality",
                        "provenance",
                    )
                )
                for member in members
            ),
            f"member_names={[member.get('name') for member in members if isinstance(member, dict)]}",
        ),
        build_check(
            "team report preserves role-shell, chakra-pressure, strength, weakness, substitution, data-quality, and provenance surfaces",
            isinstance(payload, dict)
            and isinstance(payload.get("role_matrix"), dict)
            and bool(payload.get("team_identity_hints"))
            and isinstance(chakra_curve, dict)
            and bool(shared_pressure_notes)
            and bool(payload.get("strength_notes"))
            and bool(weakness_notes)
            and bool(substitution_hooks)
            and isinstance(data_quality_warnings, dict)
            and data_quality_warnings.get("warning_count", 0) > 0
            and isinstance(provenance_hooks, dict)
            and bool(provenance_members),
            (
                f"role_matrix_keys={sorted(payload.get('role_matrix', {}).keys()) if isinstance(payload, dict) else []} "
                f"weakness_note_ids={weakness_note_ids}"
            ),
        ),
        build_check(
            "team report keeps substitution hooks tied back to search helper filters",
            isinstance(substitution_hooks, list)
            and all(
                isinstance(hook, dict)
                and isinstance(hook.get("cli_example"), str)
                and "search_characters.py" in hook["cli_example"]
                for hook in substitution_hooks
            ),
            f"substitution_reasons={[hook.get('reason') for hook in substitution_hooks if isinstance(hook, dict)]}",
        ),
        build_check(
            "team report keeps visible data-quality uncertainty notes",
            "data_quality_uncertainty" in weakness_note_ids
            and isinstance(data_quality_warnings, dict)
            and data_quality_warnings.get("warning_count", 0) > 0,
            f"warning_count={data_quality_warnings.get('warning_count') if isinstance(data_quality_warnings, dict) else None}",
        ),
        build_check(
            "team report keeps canonical provenance hooks",
            isinstance(provenance_members, list)
            and len(provenance_members) == len(REPRESENTATIVE_TEAM_ARGS)
            and all(
                isinstance(member, dict)
                and source_refs_are_canonical(member.get("record_sources", []))
                and isinstance(member.get("skill_sources"), list)
                and bool(member["skill_sources"])
                and all(
                    isinstance(skill, dict) and source_refs_are_canonical(skill.get("source_refs", []))
                    for skill in member["skill_sources"]
                )
                for member in provenance_members
            ),
            f"provenance_member_names={[member.get('name') for member in provenance_members if isinstance(member, dict)]}",
        ),
        build_check(
            "team report surfaces member-level data-quality and provenance markers without suppression",
            isinstance(naruto_member, dict)
            and isinstance(naruto_member.get("data_quality"), dict)
            and bool(naruto_member["data_quality"].get("warnings"))
            and isinstance(naruto_member.get("provenance"), dict)
            and source_refs_are_canonical(naruto_member["provenance"].get("record_sources", [])),
            f"naruto_data_quality_tags={naruto_member.get('data_quality', {}).get('tag_ids') if isinstance(naruto_member, dict) else None}",
        ),
        build_check(
            "team report omits authoritative-score and best-team fields",
            FORBIDDEN_OUTPUT_KEYS.isdisjoint(payload_keys),
            f"present_forbidden_keys={sorted(FORBIDDEN_OUTPUT_KEYS.intersection(payload_keys))}",
        ),
    ]

    section = {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "resolved_member_count": payload.get("resolved_member_count") if isinstance(payload, dict) else None,
            "member_names": [member.get("name") for member in members if isinstance(member, dict)],
            "role_matrix_keys": sorted(payload.get("role_matrix", {}).keys()) if isinstance(payload, dict) else [],
            "weakness_note_ids": weakness_note_ids,
            "substitution_reasons": [
                hook.get("reason")
                for hook in substitution_hooks
                if isinstance(hook, dict)
            ],
        },
    }
    return section, payload


def validate_conservative_behavior(
    search_payload: dict[str, Any] | None,
    team_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    search_keys = collect_keys(search_payload or {})
    team_keys = collect_keys(team_payload or {})
    team_source = read_source(TEAM_REPORT_SCRIPT).lower()

    checks = [
        build_check(
            "search payload exposes data-quality warnings instead of suppressing them",
            isinstance(search_payload, dict)
            and isinstance(search_payload.get("results"), list)
            and any(
                isinstance(result, dict)
                and isinstance(result.get("data_quality"), dict)
                and bool(result["data_quality"].get("warnings"))
                for result in search_payload["results"]
            ),
            f"search_result_count={search_payload.get('displayed_count') if isinstance(search_payload, dict) else None}",
        ),
        build_check(
            "team payload exposes provenance hooks instead of suppressing them",
            isinstance(team_payload, dict)
            and isinstance(team_payload.get("provenance_hooks"), dict)
            and bool(team_payload["provenance_hooks"].get("members")),
            f"provenance_member_count={len(team_payload.get('provenance_hooks', {}).get('members', [])) if isinstance(team_payload, dict) else None}",
        ),
        build_check(
            "helper payloads do not require opaque score fields",
            FORBIDDEN_OUTPUT_KEYS.isdisjoint(search_keys) and FORBIDDEN_OUTPUT_KEYS.isdisjoint(team_keys),
            (
                f"search_forbidden={sorted(FORBIDDEN_OUTPUT_KEYS.intersection(search_keys))} "
                f"team_forbidden={sorted(FORBIDDEN_OUTPUT_KEYS.intersection(team_keys))}"
            ),
        ),
        build_check(
            "team report source does not describe a static best-team database",
            "best team" not in team_source and "best_team" not in team_source and "best teams" not in team_source,
            "checked team_candidate_report.py for best-team wording markers",
        ),
    ]

    return {
        "status": section_status(checks),
        "checks": checks,
    }


def main() -> int:
    parse_args()

    runtime_boundary = validate_runtime_boundary()
    search_section, search_payload = validate_search_helper()
    team_section, team_payload = validate_team_report()
    conservative_behavior = validate_conservative_behavior(search_payload, team_payload)

    sections = {
        "runtime_boundary": runtime_boundary,
        "search_helper": search_section,
        "team_report": team_section,
        "conservative_behavior": conservative_behavior,
    }
    failures = [
        f"{section_name}: {check['check']}"
        for section_name, section in sections.items()
        for check in section["checks"]
        if check["status"] == "failed"
    ]
    report = {
        "status": "ok" if not failures else "failed",
        "references_dir": str(EXPECTED_REFERENCES_DIR),
        "representative_commands": {
            "search_helper": search_section["command"],
            "team_report": team_section["command"],
        },
        "sections": sections,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

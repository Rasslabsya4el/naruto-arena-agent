#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import optimize_mission_pool
import search_characters
import team_candidate_report


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
PLANNER_SCRIPT = SCRIPTS_DIR / "optimize_mission_pool.py"
EXPECTED_REFERENCES_DIR = REPO_ROOT / "skills" / "naruto-arena-team-builder" / "references"

GROUPED_ARGS = ["Survival", "A Girl Grown Up", "Medical Training"]
SPLIT_UNKNOWN_ARGS = ["Survival", "A Dishonored Shinobi", "A Cautious Blade in the Cloud"]
SOFT_ONLY_ARGS = ["A Blank Slate"]
BLOCKED_ARGS = ["Definitely Not A Mission"]
LOW_RANK_ARGS = ["A Girl Grown Up"]
HIGH_RANK_ARGS = ["A Cautious Blade in the Cloud"]
LOW_RANK_OVERRIDE_ARGS = ["--include-higher-rank", "A Girl Grown Up"]
LONE_SWORDSMAN_DOUBLECOUNT_ARGS = [
    "--include-higher-rank",
    "--assume-team",
    "character:momochi-zabuza,character:hoshigaki-kisame",
    "The Lone Swordsman",
]
SECOND_OR_DOUBLECOUNT_ARGS = [
    "--include-higher-rank",
    "--assume-team",
    "character:rock-lee,character:kimimaro",
    "The Drunken Master",
]

FORBIDDEN_OUTPUT_KEYS = {
    "authoritative_score",
    "authoritative_scores",
    "best_team",
    "best_teams",
    "recommended_team",
    "selected_team",
    "team_database",
    "team_score",
    "team_scores",
    "score",
    "scores",
}
FORBIDDEN_SOURCE_PATTERNS = (
    r"\bauthoritative[-_ ]scores?\b",
    r"\bbest[-_ ]teams?\b",
    r"\brecommended[-_ ]teams?\b",
    r"\bselected[-_ ]team\b",
    r"\bteam[-_ ]database\b",
    r"\bteam[-_ ]scores?\b",
    r'"scores?"\s*:',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the accepted Naruto Arena mission-pool planner contract with fixed "
            "grouped, split, unknown-objective, soft-fit-only, blocked-query, helper-boundary, "
            "and no-opaque-ranking checks."
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


def run_planner(args: list[str]) -> dict[str, Any]:
    command = [sys.executable, "-X", "utf8", str(PLANNER_SCRIPT), *args]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )

    stdout = completed.stdout.strip()
    payload = None
    parse_error = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)

    return {
        "command": subprocess.list2cmdline(command),
        "cwd": str(REPO_ROOT.parent),
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


def collect_bucket_member_ids(payload: dict[str, Any]) -> list[set[str]]:
    buckets = payload.get("coverage_buckets", [])
    if not isinstance(buckets, list):
        return []
    return [
        set(bucket.get("required_member_ids", []))
        for bucket in buckets
        if isinstance(bucket, dict) and isinstance(bucket.get("required_member_ids"), list)
    ]


def find_matrix_entry(payload: dict[str, Any], mission_id: str) -> dict[str, Any] | None:
    matrix = payload.get("coverage_matrix", [])
    if not isinstance(matrix, list):
        return None
    for entry in matrix:
        if isinstance(entry, dict) and entry.get("mission_id") == mission_id:
            return entry
    return None


def find_analysis(payload: dict[str, Any], mission_id: str) -> dict[str, Any] | None:
    analyses = payload.get("mission_analyses", [])
    if not isinstance(analyses, list):
        return None
    for analysis in analyses:
        if isinstance(analysis, dict) and analysis.get("id") == mission_id:
            return analysis
    return None


def find_hard_constraint(payload: dict[str, Any], mission_id: str, requirement_id: str) -> dict[str, Any] | None:
    analysis = find_analysis(payload, mission_id)
    if not isinstance(analysis, dict):
        return None
    constraints = analysis.get("hard_constraints", [])
    if not isinstance(constraints, list):
        return None
    for constraint in constraints:
        if isinstance(constraint, dict) and constraint.get("requirement_id") == requirement_id:
            return constraint
    return None


def find_assumed_progress_requirement(
    payload: dict[str, Any],
    mission_id: str,
    requirement_id: str,
) -> dict[str, Any] | None:
    assumed = payload.get("assumed_team_progress")
    if not isinstance(assumed, dict):
        return None
    missions = assumed.get("mission_progress", [])
    if not isinstance(missions, list):
        return None
    for mission in missions:
        if not isinstance(mission, dict) or mission.get("mission_id") != mission_id:
            continue
        requirements = mission.get("requirements", [])
        if not isinstance(requirements, list):
            return None
        for requirement in requirements:
            if isinstance(requirement, dict) and requirement.get("requirement_id") == requirement_id:
                return requirement
    return None


def has_rationale(payload: dict[str, Any], kind: str, **expected: Any) -> bool:
    rationale = payload.get("split_rationale", [])
    if not isinstance(rationale, list):
        return False
    for item in rationale:
        if not isinstance(item, dict) or item.get("kind") != kind:
            continue
        if all(item.get(key) == value for key, value in expected.items()):
            return True
    return False


def has_uncertain_reason(payload: dict[str, Any], mission_id: str, reason_kind: str) -> bool:
    uncertain = payload.get("uncertain_missions", [])
    if not isinstance(uncertain, list):
        return False
    for mission in uncertain:
        if not isinstance(mission, dict) or mission.get("mission_id") != mission_id:
            continue
        reasons = mission.get("reasons", [])
        return isinstance(reasons, list) and any(
            isinstance(reason, dict) and reason.get("kind") == reason_kind for reason in reasons
        )
    return False


def payload_ok(run: dict[str, Any]) -> bool:
    payload = run.get("payload")
    return run["returncode"] == 0 and isinstance(payload, dict) and payload.get("status") == "ok"


def validate_grouped_exact(run: dict[str, Any]) -> dict[str, Any]:
    payload = run["payload"] if isinstance(run["payload"], dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    buckets = payload.get("coverage_buckets", []) if isinstance(payload, dict) else []
    matrix = payload.get("coverage_matrix", []) if isinstance(payload, dict) else []
    bucket_member_ids = collect_bucket_member_ids(payload)
    expected_members = {
        "character:haruno-sakura",
        "character:uchiha-sasuke",
        "character:uzumaki-naruto",
    }
    expected_missions = {
        "mission:survival",
        "mission:a-girl-grown-up",
        "mission:medical-training",
    }
    matrix_statuses = {
        entry.get("mission_id"): entry.get("coverage_status")
        for entry in matrix
        if isinstance(entry, dict)
    }
    checks = [
        build_check(
            "grouped planner command succeeds",
            payload_ok(run),
            f"returncode={run['returncode']} parse_error={run['parse_error']}",
        ),
        build_check(
            "grouped exact requirements collapse into one bucket",
            summary.get("coverage_bucket_count") == 1
            and summary.get("exact_requirement_unit_count") == 4
            and summary.get("uncertain_mission_count") == 0
            and len(buckets) == 1,
            (
                f"coverage_bucket_count={summary.get('coverage_bucket_count')} "
                f"exact_requirement_unit_count={summary.get('exact_requirement_unit_count')} "
                f"uncertain_mission_count={summary.get('uncertain_mission_count')}"
            ),
        ),
        build_check(
            "grouped bucket keeps the compatible Team 7 exact core",
            bucket_member_ids == [expected_members],
            f"bucket_member_ids={[sorted(item) for item in bucket_member_ids]}",
        ),
        build_check(
            "grouped matrix marks every requested mission covered by one bucket",
            expected_missions.issubset(matrix_statuses.keys())
            and all(matrix_statuses.get(mission_id) == "fully_covered_by_one_bucket" for mission_id in expected_missions),
            f"matrix_statuses={matrix_statuses}",
        ),
        build_check(
            "grouped rationale records one-bucket compatibility",
            has_rationale(payload, "grouped_into_one_bucket", required_character_count=3, team_size=3),
            f"split_rationale={[item.get('kind') for item in payload.get('split_rationale', []) if isinstance(item, dict)]}",
        ),
    ]
    return {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "coverage_bucket_count": summary.get("coverage_bucket_count"),
            "exact_requirement_unit_count": summary.get("exact_requirement_unit_count"),
            "required_member_ids": sorted(next(iter(bucket_member_ids), set())),
            "matrix_statuses": matrix_statuses,
        },
    }


def validate_split_and_unknown(run: dict[str, Any]) -> dict[str, Any]:
    payload = run["payload"] if isinstance(run["payload"], dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    bucket_member_ids = collect_bucket_member_ids(payload)
    dishonored_entry = find_matrix_entry(payload, "mission:a-dishonored-shinobi")
    unknown_entry = find_matrix_entry(payload, "mission:a-cautious-blade-in-the-cloud")
    unknown_analysis = find_analysis(payload, "mission:a-cautious-blade-in-the-cloud")
    required_union = set().union(*bucket_member_ids) if bucket_member_ids else set()
    checks = [
        build_check(
            "split planner command succeeds",
            payload_ok(run),
            f"returncode={run['returncode']} parse_error={run['parse_error']}",
        ),
        build_check(
            "incompatible exact mission pool splits across multiple buckets",
            summary.get("coverage_bucket_count") == 2
            and summary.get("exact_requirement_unit_count") == 3
            and len(bucket_member_ids) == 2
            and len(required_union) == 4,
            (
                f"coverage_bucket_count={summary.get('coverage_bucket_count')} "
                f"exact_requirement_unit_count={summary.get('exact_requirement_unit_count')} "
                f"required_union={sorted(required_union)}"
            ),
        ),
        build_check(
            "split rationale records more exact required characters than team size",
            has_rationale(payload, "split_required", required_character_count=4, team_size=3, bucket_count=2),
            f"split_rationale={payload.get('split_rationale')}",
        ),
        build_check(
            "multi-requirement mission is covered honestly across two buckets",
            isinstance(dishonored_entry, dict)
            and dishonored_entry.get("coverage_status") == "fully_covered_split_across_buckets"
            and dishonored_entry.get("exact_requirements_total") == 2
            and dishonored_entry.get("exact_requirements_covered") == 2
            and len(dishonored_entry.get("bucket_ids", [])) == 2,
            f"dishonored_entry={dishonored_entry}",
        ),
        build_check(
            "unknown-objective mission remains uncertain and uncovered",
            isinstance(unknown_entry, dict)
            and unknown_entry.get("coverage_status") == "uncertain_unknown_requirements"
            and unknown_entry.get("exact_requirements_total") == 0
            and unknown_entry.get("exact_requirements_covered") == 0
            and not unknown_entry.get("covered_requirement_ids")
            and bool(unknown_entry.get("unknown_requirement_ids"))
            and bool(unknown_entry.get("transparency_warnings")),
            f"unknown_entry={unknown_entry}",
        ),
        build_check(
            "unknown objective carries through mission analysis and uncertain_missions",
            isinstance(unknown_analysis, dict)
            and bool(unknown_analysis.get("unknown_requirements"))
            and not unknown_analysis.get("hard_constraints")
            and has_uncertain_reason(payload, "mission:a-cautious-blade-in-the-cloud", "unknown_requirements"),
            f"unknown_analysis_keys={sorted(unknown_analysis.keys()) if isinstance(unknown_analysis, dict) else []}",
        ),
    ]
    return {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "coverage_bucket_count": summary.get("coverage_bucket_count"),
            "exact_requirement_unit_count": summary.get("exact_requirement_unit_count"),
            "required_union": sorted(required_union),
            "dishonored_status": dishonored_entry.get("coverage_status") if isinstance(dishonored_entry, dict) else None,
            "unknown_status": unknown_entry.get("coverage_status") if isinstance(unknown_entry, dict) else None,
        },
    }


def validate_soft_fit_only(run: dict[str, Any]) -> dict[str, Any]:
    payload = run["payload"] if isinstance(run["payload"], dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    matrix_entry = find_matrix_entry(payload, "mission:a-blank-slate")
    analysis = find_analysis(payload, "mission:a-blank-slate")
    checks = [
        build_check(
            "soft-fit-only planner command succeeds",
            payload_ok(run),
            f"returncode={run['returncode']} parse_error={run['parse_error']}",
        ),
        build_check(
            "soft-fit-only mission creates no fake exact bucket",
            summary.get("exact_requirement_unit_count") == 0
            and summary.get("coverage_bucket_count") == 0
            and summary.get("uncertain_mission_count") == 1
            and payload.get("coverage_buckets") == [],
            (
                f"exact_requirement_unit_count={summary.get('exact_requirement_unit_count')} "
                f"coverage_bucket_count={summary.get('coverage_bucket_count')} "
                f"uncertain_mission_count={summary.get('uncertain_mission_count')}"
            ),
        ),
        build_check(
            "soft-fit-only matrix remains warning-only",
            isinstance(matrix_entry, dict)
            and matrix_entry.get("coverage_status") == "uncertain_soft_fit_only"
            and matrix_entry.get("exact_requirements_total") == 0
            and matrix_entry.get("exact_requirements_covered") == 0
            and not matrix_entry.get("covered_requirement_ids")
            and bool(matrix_entry.get("soft_fit_requirement_ids")),
            f"matrix_entry={matrix_entry}",
        ),
        build_check(
            "soft-fit hint is preserved in analysis and uncertain_missions",
            isinstance(analysis, dict)
            and bool(analysis.get("soft_fit_hints"))
            and not analysis.get("hard_constraints")
            and not analysis.get("unknown_requirements")
            and has_uncertain_reason(payload, "mission:a-blank-slate", "soft_fit_hints"),
            f"analysis_keys={sorted(analysis.keys()) if isinstance(analysis, dict) else []}",
        ),
        build_check(
            "soft-fit-only rationale records no exact team constraints",
            has_rationale(payload, "no_exact_team_constraints"),
            f"split_rationale={[item.get('kind') for item in payload.get('split_rationale', []) if isinstance(item, dict)]}",
        ),
    ]
    return {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "coverage_bucket_count": summary.get("coverage_bucket_count"),
            "exact_requirement_unit_count": summary.get("exact_requirement_unit_count"),
            "coverage_status": matrix_entry.get("coverage_status") if isinstance(matrix_entry, dict) else None,
            "soft_fit_requirement_ids": matrix_entry.get("soft_fit_requirement_ids") if isinstance(matrix_entry, dict) else None,
        },
    }


def validate_alternative_character_doublecount(
    run: dict[str, Any],
    *,
    mission_id: str,
    requirement_id: str,
    expected_member_ids: set[str],
    label: str,
) -> dict[str, Any]:
    payload = run["payload"] if isinstance(run["payload"], dict) else {}
    hard_constraint = find_hard_constraint(payload, mission_id, requirement_id)
    character_choice = hard_constraint.get("character_choice") if isinstance(hard_constraint, dict) else None
    assumed_requirement = find_assumed_progress_requirement(payload, mission_id, requirement_id)
    matched_ids = (
        set(assumed_requirement.get("matched_eligible_character_ids", []))
        if isinstance(assumed_requirement, dict) and isinstance(assumed_requirement.get("matched_eligible_character_ids"), list)
        else set()
    )
    eligible_ids = (
        set(character_choice.get("eligible_character_refs", []))
        if isinstance(character_choice, dict) and isinstance(character_choice.get("eligible_character_refs"), list)
        else set()
    )
    checks = [
        build_check(
            f"{label} planner command succeeds",
            payload_ok(run),
            f"returncode={run['returncode']} parse_error={run['parse_error']}",
        ),
        build_check(
            f"{label} requirement exposes structured alternative character choice",
            isinstance(character_choice, dict)
            and character_choice.get("choice_type") == "alternative_eligible_characters"
            and character_choice.get("progress_counting") == "per_eligible_character_present"
            and character_choice.get("max_progress_per_qualifying_battle") == len(expected_member_ids)
            and eligible_ids == expected_member_ids,
            f"character_choice={character_choice}",
        ),
        build_check(
            f"{label} assumed team double-counts both eligible named characters",
            isinstance(assumed_requirement, dict)
            and assumed_requirement.get("progress_counting") == "per_eligible_character_present"
            and assumed_requirement.get("progress_units_for_qualifying_battle") == len(expected_member_ids)
            and matched_ids == expected_member_ids,
            f"assumed_requirement={assumed_requirement}",
        ),
    ]
    return {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "eligible_ids": sorted(eligible_ids),
            "matched_ids": sorted(matched_ids),
            "progress_units_for_qualifying_battle": (
                assumed_requirement.get("progress_units_for_qualifying_battle")
                if isinstance(assumed_requirement, dict)
                else None
            ),
        },
    }


def validate_blocked_query(run: dict[str, Any]) -> dict[str, Any]:
    payload = run["payload"] if isinstance(run["payload"], dict) else {}
    resolutions = payload.get("mission_resolutions", []) if isinstance(payload, dict) else []
    first_resolution = resolutions[0] if resolutions and isinstance(resolutions[0], dict) else {}
    checks = [
        build_check(
            "unresolved mission query returns blocked exit code",
            run["returncode"] == 2 and isinstance(payload, dict) and payload.get("status") == "blocked",
            f"returncode={run['returncode']} status={payload.get('status') if isinstance(payload, dict) else None}",
        ),
        build_check(
            "blocked payload preserves unresolved resolution instead of guessing",
            first_resolution.get("status") == "not_found"
            and first_resolution.get("input") == BLOCKED_ARGS[0]
            and first_resolution.get("candidates") == []
            and "mission" not in first_resolution,
            f"first_resolution={first_resolution}",
        ),
        build_check(
            "blocked payload omits planning coverage surfaces",
            "coverage_buckets" not in payload
            and "coverage_matrix" not in payload
            and "mission_analyses" not in payload,
            f"payload_keys={sorted(payload.keys()) if isinstance(payload, dict) else []}",
        ),
    ]
    return {
        "status": section_status(checks),
        "command": run["command"],
        "cwd": run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "returncode": run["returncode"],
            "status": payload.get("status") if isinstance(payload, dict) else None,
            "resolution_status": first_resolution.get("status"),
        },
    }


def validate_progression_ceiling(
    low_rank_run: dict[str, Any],
    high_rank_run: dict[str, Any],
    override_run: dict[str, Any],
) -> dict[str, Any]:
    low_payload = low_rank_run["payload"] if isinstance(low_rank_run["payload"], dict) else {}
    high_payload = high_rank_run["payload"] if isinstance(high_rank_run["payload"], dict) else {}
    override_payload = override_run["payload"] if isinstance(override_run["payload"], dict) else {}
    low_contract = low_payload.get("progression_contract", {}) if isinstance(low_payload, dict) else {}
    high_contract = high_payload.get("progression_contract", {}) if isinstance(high_payload, dict) else {}
    override_contract = override_payload.get("progression_contract", {}) if isinstance(override_payload, dict) else {}
    low_ceiling = low_contract.get("roster_ceiling", {}) if isinstance(low_contract, dict) else {}
    high_ceiling = high_contract.get("roster_ceiling", {}) if isinstance(high_contract, dict) else {}
    low_allowed_ranks = set(low_contract.get("allowed_rank_labels", [])) if isinstance(low_contract, dict) else set()
    high_allowed_ranks = set(high_contract.get("allowed_rank_labels", [])) if isinstance(high_contract, dict) else set()
    override_allowed_ranks = set(override_contract.get("allowed_rank_labels", [])) if isinstance(override_contract, dict) else set()
    low_buckets = low_payload.get("coverage_buckets", []) if isinstance(low_payload, dict) else []

    checks = [
        build_check(
            "low-rank mission planner command succeeds",
            payload_ok(low_rank_run),
            f"returncode={low_rank_run['returncode']} parse_error={low_rank_run['parse_error']}",
        ),
        build_check(
            "low-rank mission infers conservative Genin ceiling",
            isinstance(low_contract, dict)
            and low_contract.get("mode") == "conservative_mission_rank_ceiling"
            and low_ceiling.get("rank_label") == "Genin"
            and low_contract.get("blocked_later_rank_count", 0) > 0,
            f"low_contract={low_contract}",
        ),
        build_check(
            "low-rank mission does not allow Sannin or later ranks by default",
            "Sannin" not in low_allowed_ranks
            and "Jinchuuriki" not in low_allowed_ranks
            and {"Academy Student", "Genin"}.issuperset(low_allowed_ranks),
            f"low_allowed_ranks={sorted(low_allowed_ranks)}",
        ),
        build_check(
            "low-rank required bucket members fit the active ceiling",
            isinstance(low_buckets, list)
            and bool(low_buckets)
            and all(
                isinstance(bucket, dict)
                and isinstance(bucket.get("progression"), dict)
                and bucket["progression"].get("fits_roster_ceiling") is True
                and not bucket["progression"].get("blocked_member_ids")
                for bucket in low_buckets
            ),
            f"low_bucket_progression={[bucket.get('progression') for bucket in low_buckets if isinstance(bucket, dict)]}",
        ),
        build_check(
            "higher-rank mission expands ceiling through Sannin but not beyond it",
            payload_ok(high_rank_run)
            and isinstance(high_contract, dict)
            and high_contract.get("mode") == "conservative_mission_rank_ceiling"
            and high_ceiling.get("rank_label") == "Sannin"
            and "Sannin" in high_allowed_ranks
            and "Jinchuuriki" not in high_allowed_ranks
            and high_contract.get("allowed_character_count", 0) > low_contract.get("allowed_character_count", 9999),
            f"high_allowed_ranks={sorted(high_allowed_ranks)} high_contract={high_contract}",
        ),
        build_check(
            "explicit override opens higher-rank roster and records the override",
            payload_ok(override_run)
            and isinstance(override_contract, dict)
            and override_contract.get("mode") == "explicit_higher_rank_override"
            and override_contract.get("override_higher_rank") is True
            and override_contract.get("blocked_later_rank_count") == 0
            and "Jinchuuriki" in override_allowed_ranks
            and override_contract.get("allowed_character_count", 0) > low_contract.get("allowed_character_count", 9999),
            f"override_contract={override_contract}",
        ),
    ]

    return {
        "status": section_status(checks),
        "command": low_rank_run["command"],
        "cwd": low_rank_run["cwd"],
        "checks": checks,
        "observed_excerpt": {
            "low_ceiling": low_ceiling.get("rank_label") if isinstance(low_ceiling, dict) else None,
            "low_allowed_ranks": sorted(low_allowed_ranks),
            "low_blocked_later_rank_count": low_contract.get("blocked_later_rank_count") if isinstance(low_contract, dict) else None,
            "high_ceiling": high_ceiling.get("rank_label") if isinstance(high_ceiling, dict) else None,
            "high_allowed_ranks": sorted(high_allowed_ranks),
            "override_mode": override_contract.get("mode") if isinstance(override_contract, dict) else None,
        },
    }


def validate_helper_boundary(grouped_run: dict[str, Any]) -> dict[str, Any]:
    payload = grouped_run["payload"] if isinstance(grouped_run["payload"], dict) else {}
    bucket = next(iter(payload.get("coverage_buckets", [])), {}) if isinstance(payload, dict) else {}
    team_surface = bucket.get("team_surface", {}) if isinstance(bucket, dict) else {}
    checks = [
        build_check(
            "planner default references dir is the skill-local bundle",
            optimize_mission_pool.DEFAULT_REFERENCES_DIR.resolve() == EXPECTED_REFERENCES_DIR.resolve(),
            f"observed={optimize_mission_pool.DEFAULT_REFERENCES_DIR.resolve()}",
        ),
        build_check(
            "planner reuses search helper loader and character summaries",
            optimize_mission_pool.load_reference_context is search_characters.load_reference_context
            and optimize_mission_pool.build_character_summaries is search_characters.build_character_summaries,
            "checked imported helper function identity",
        ),
        build_check(
            "planner reuses accepted team-report helper surfaces",
            optimize_mission_pool.build_team_chakra_report is team_candidate_report.build_team_chakra_report
            and optimize_mission_pool.build_role_matrix is team_candidate_report.build_role_matrix
            and optimize_mission_pool.build_strength_notes is team_candidate_report.build_strength_notes
            and optimize_mission_pool.build_weakness_notes is team_candidate_report.build_weakness_notes
            and optimize_mission_pool.build_substitution_hooks is team_candidate_report.build_substitution_hooks
            and optimize_mission_pool.build_provenance_hooks is team_candidate_report.build_provenance_hooks,
            "checked imported team_candidate_report helper function identity",
        ),
        build_check(
            "planner output reports skill-local references_dir",
            payload.get("references_dir") == str(EXPECTED_REFERENCES_DIR),
            f"observed={payload.get('references_dir') if isinstance(payload, dict) else None}",
        ),
        build_check(
            "bucket payload exposes helper-derived team surface",
            isinstance(team_surface, dict)
            and isinstance(team_surface.get("role_matrix"), dict)
            and isinstance(team_surface.get("chakra_curve"), dict)
            and isinstance(team_surface.get("strength_notes"), list)
            and isinstance(team_surface.get("weakness_notes"), list)
            and isinstance(team_surface.get("substitution_hooks"), list)
            and isinstance(team_surface.get("provenance_hooks"), dict),
            f"team_surface_keys={sorted(team_surface.keys()) if isinstance(team_surface, dict) else []}",
        ),
    ]
    return {
        "status": section_status(checks),
        "checks": checks,
    }


def validate_forbidden_fields(runs: list[dict[str, Any]]) -> dict[str, Any]:
    payload_keys = set()
    for run in runs:
        if isinstance(run.get("payload"), dict):
            payload_keys.update(collect_keys(run["payload"]))

    source_text = PLANNER_SCRIPT.read_text(encoding="utf-8").lower()
    source_hits = [
        pattern
        for pattern in FORBIDDEN_SOURCE_PATTERNS
        if re.search(pattern, source_text, flags=re.IGNORECASE)
    ]
    checks = [
        build_check(
            "representative planner payloads omit authoritative-score and best-team fields",
            FORBIDDEN_OUTPUT_KEYS.isdisjoint(payload_keys),
            f"present_forbidden_keys={sorted(FORBIDDEN_OUTPUT_KEYS.intersection(payload_keys))}",
        ),
        build_check(
            "planner source omits static best-team and opaque score markers",
            not source_hits,
            f"present_forbidden_source_patterns={source_hits}",
        ),
        build_check(
            "planner contract describes exact coverage instead of opaque ranking",
            all(
                isinstance(run.get("payload"), dict)
                and (
                    run["payload"].get("status") == "blocked"
                    or "exact character refs" in run["payload"].get("planning_contract", {}).get("coverage_basis", "")
                )
                for run in runs
            ),
            "checked planning_contract.coverage_basis on successful payloads",
        ),
    ]
    return {
        "status": section_status(checks),
        "checks": checks,
    }


def main() -> int:
    parse_args()

    grouped_run = run_planner(GROUPED_ARGS)
    split_unknown_run = run_planner(SPLIT_UNKNOWN_ARGS)
    soft_only_run = run_planner(SOFT_ONLY_ARGS)
    blocked_run = run_planner(BLOCKED_ARGS)
    low_rank_run = run_planner(LOW_RANK_ARGS)
    high_rank_run = run_planner(HIGH_RANK_ARGS)
    override_run = run_planner(LOW_RANK_OVERRIDE_ARGS)
    lone_swordsman_doublecount_run = run_planner(LONE_SWORDSMAN_DOUBLECOUNT_ARGS)
    second_or_doublecount_run = run_planner(SECOND_OR_DOUBLECOUNT_ARGS)
    runs = [
        grouped_run,
        split_unknown_run,
        soft_only_run,
        blocked_run,
        low_rank_run,
        high_rank_run,
        override_run,
        lone_swordsman_doublecount_run,
        second_or_doublecount_run,
    ]

    sections = {
        "grouped_exact_coverage": validate_grouped_exact(grouped_run),
        "split_and_unknown_objective": validate_split_and_unknown(split_unknown_run),
        "soft_fit_only": validate_soft_fit_only(soft_only_run),
        "lone_swordsman_alternative_character_doublecount": validate_alternative_character_doublecount(
            lone_swordsman_doublecount_run,
            mission_id="mission:the-lone-swordsman",
            requirement_id="mission:the-lone-swordsman:req:01",
            expected_member_ids={"character:momochi-zabuza", "character:hoshigaki-kisame"},
            label="lone swordsman",
        ),
        "second_alternative_character_doublecount": validate_alternative_character_doublecount(
            second_or_doublecount_run,
            mission_id="mission:the-drunken-master",
            requirement_id="mission:the-drunken-master:req:01",
            expected_member_ids={"character:rock-lee", "character:kimimaro"},
            label="second alternative-character case",
        ),
        "blocked_query": validate_blocked_query(blocked_run),
        "progression_ceiling": validate_progression_ceiling(low_rank_run, high_rank_run, override_run),
        "helper_boundary": validate_helper_boundary(grouped_run),
        "forbidden_fields": validate_forbidden_fields(runs),
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
            "grouped_exact_coverage": sections["grouped_exact_coverage"]["command"],
            "split_and_unknown_objective": sections["split_and_unknown_objective"]["command"],
            "soft_fit_only": sections["soft_fit_only"]["command"],
            "lone_swordsman_alternative_character_doublecount": sections[
                "lone_swordsman_alternative_character_doublecount"
            ]["command"],
            "second_alternative_character_doublecount": sections["second_alternative_character_doublecount"]["command"],
            "blocked_query": sections["blocked_query"]["command"],
            "progression_ceiling": sections["progression_ceiling"]["command"],
        },
        "sections": sections,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

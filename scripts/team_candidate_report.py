#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from typing import Any

from search_characters import (
    CHAKRA_TYPES,
    CONTROL_TAGS,
    PRESSURE_TAGS,
    PROTECTION_TAGS,
    RESOURCE_TAGS,
    SETUP_TAGS,
    SUSTAIN_TAGS,
    build_character_summaries,
    load_reference_context,
    resolve_character_query,
)


def build_member_evidence(
    member: dict[str, Any],
    context: dict[str, Any],
    relevant_tag_ids: set[str],
    *,
    max_tags: int = 2,
    max_examples: int = 2,
) -> dict[str, Any]:
    row = context["character_tag_rows_by_id"].get(member["id"], {})
    tag_entries = row.get("tags", []) if isinstance(row, dict) else []
    trigger_tags = []

    for tag_entry in tag_entries:
        if not isinstance(tag_entry, dict):
            continue
        tag_id = tag_entry.get("tag_id")
        if tag_id not in relevant_tag_ids:
            continue
        tag_meta = context["tag_meta_by_id"].get(tag_id, {})
        examples = []
        for raw_example in tag_entry.get("evidence", [])[:max_examples]:
            if not isinstance(raw_example, dict):
                continue
            example = dict(raw_example)
            skill_id = example.get("skill_id")
            if isinstance(skill_id, str):
                skill_summary = next((skill for skill in member["skill_summaries"] if skill["skill_id"] == skill_id), None)
                if isinstance(skill_summary, dict):
                    example["source_ref_ids"] = skill_summary["source_ref_ids"]
                    example["source_refs"] = skill_summary["source_refs"]
            examples.append(example)
        trigger_tags.append(
            {
                "tag_id": tag_id,
                "label": tag_meta.get("label", tag_id),
                "evidence_count": tag_entry.get("evidence_count", 0),
                "examples": examples,
            }
        )

    return {
        "member_id": member["id"],
        "name": member["name"],
        "role_hints": member["role_hints"],
        "trigger_tags": trigger_tags[:max_tags],
    }


def members_with_any_tag(members: list[dict[str, Any]], tag_ids: set[str]) -> list[dict[str, Any]]:
    return [member for member in members if set(member["tag_ids"]).intersection(tag_ids)]


def dedupe_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_members = []
    seen_ids = set()
    for member in members:
        member_id = member["id"]
        if member_id in seen_ids:
            continue
        seen_ids.add(member_id)
        unique_members.append(member)
    return unique_members


def build_role_matrix(members: list[dict[str, Any]]) -> dict[str, list[str]]:
    role_matrix: dict[str, list[str]] = defaultdict(list)
    for member in members:
        for role_hint in member["role_hints"]:
            role_matrix[role_hint].append(member["name"])
    return {role_hint: sorted(names) for role_hint, names in sorted(role_matrix.items())}


def build_team_identity_hints(members: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    pressure_members = members_with_any_tag(members, PRESSURE_TAGS)
    control_members = members_with_any_tag(members, CONTROL_TAGS)
    sustain_members = members_with_any_tag(members, SUSTAIN_TAGS)
    protection_members = members_with_any_tag(members, PROTECTION_TAGS)
    setup_members = members_with_any_tag(members, SETUP_TAGS)
    resource_members = members_with_any_tag(members, RESOURCE_TAGS)

    hints = []
    if pressure_members and control_members:
        evidence_members = []
        for member in dedupe_members([*pressure_members, *control_members]):
            evidence_members.append(build_member_evidence(member, context, PRESSURE_TAGS.union(CONTROL_TAGS)))
        hints.append(
            {
                "identity_id": "control_pressure_shell",
                "label": "Control-Pressure Shell",
                "summary": "Control tags and damage-oriented tags coexist, so the team has a visible path to safer kill windows.",
                "evidence": evidence_members,
            }
        )

    if pressure_members and (sustain_members or protection_members):
        evidence_members = []
        for member in dedupe_members([*pressure_members, *sustain_members, *protection_members]):
            evidence_members.append(build_member_evidence(member, context, PRESSURE_TAGS.union(SUSTAIN_TAGS).union(PROTECTION_TAGS)))
        hints.append(
            {
                "identity_id": "pressure_with_stabilizers",
                "label": "Pressure With Stabilizers",
                "summary": "Damage tags sit next to heal/protect/reduction tags, which suggests the team can keep pressure online longer instead of racing every turn.",
                "evidence": evidence_members,
            }
        )

    if setup_members and (control_members or sustain_members or protection_members):
        evidence_members = []
        for member in dedupe_members([*setup_members, *control_members, *sustain_members, *protection_members]):
            evidence_members.append(build_member_evidence(member, context, SETUP_TAGS.union(CONTROL_TAGS).union(SUSTAIN_TAGS).union(PROTECTION_TAGS)))
        hints.append(
            {
                "identity_id": "setup_support_shell",
                "label": "Setup-Support Shell",
                "summary": "Setup-dependent tags are present and the team also shows support/control signals that can buy time for gated turns.",
                "evidence": evidence_members,
            }
        )

    if resource_members and control_members:
        evidence_members = []
        for member in dedupe_members([*resource_members, *control_members]):
            evidence_members.append(build_member_evidence(member, context, RESOURCE_TAGS.union(CONTROL_TAGS)))
        hints.append(
            {
                "identity_id": "resource_denial_shell",
                "label": "Resource-Denial Shell",
                "summary": "Drain/removal-style tags overlap with control tags, which points toward slower tempo-denial play instead of pure race pressure.",
                "evidence": evidence_members,
            }
        )

    return hints


def build_team_chakra_report(members: list[dict[str, Any]]) -> dict[str, Any]:
    total_components: Counter[str] = Counter()
    total_skill_usage: Counter[str] = Counter()
    members_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    low_cost_skills = []
    expensive_skills = []

    for member in members:
        profile = member["chakra_profile"]
        for chakra_type in CHAKRA_TYPES:
            amount = profile["component_totals"].get(chakra_type, 0)
            skill_count = profile["skill_usage_counts"].get(chakra_type, 0)
            total_components[chakra_type] += amount
            total_skill_usage[chakra_type] += skill_count
            if amount > 0:
                members_by_type[chakra_type].append(
                    {
                        "member_id": member["id"],
                        "name": member["name"],
                        "component_total": amount,
                        "skill_count": skill_count,
                        "skills": profile["skills_by_type"].get(chakra_type, []),
                    }
                )
        low_cost_skills.extend(
            [
                {
                    "member_id": member["id"],
                    "name": member["name"],
                    **skill,
                }
                for skill in profile["low_cost_skills"]
            ]
        )
        expensive_skills.extend(
            [
                {
                    "member_id": member["id"],
                    "name": member["name"],
                    **skill,
                }
                for skill in profile["expensive_skills"]
            ]
        )

    shared_pressure = []
    for chakra_type in CHAKRA_TYPES:
        entries = members_by_type.get(chakra_type, [])
        if len(entries) < 2:
            continue
        total_amount = total_components.get(chakra_type, 0)
        if total_amount <= 0:
            continue
        shared_pressure.append(
            {
                "chakra_type": chakra_type,
                "total_component_amount": total_amount,
                "total_skill_usage": total_skill_usage.get(chakra_type, 0),
                "members": entries,
                "risk_level": "high" if chakra_type != "random" and total_amount >= 4 else "medium",
            }
        )

    notes = []
    for entry in shared_pressure:
        if entry["chakra_type"] == "random":
            summary = "Multiple members lean on random costs, which adds some flexibility but still depends on draw quality."
        else:
            summary = (
                f"Multiple members spend {entry['chakra_type']} chakra, so that color is a visible shared pressure point in the curve."
            )
        notes.append(
            {
                "note_type": "shared_chakra_pressure",
                "chakra_type": entry["chakra_type"],
                "risk_level": entry["risk_level"],
                "summary": summary,
                "evidence": entry,
            }
        )

    if low_cost_skills:
        notes.append(
            {
                "note_type": "low_cost_options",
                "risk_level": "info",
                "summary": "The team has low-cost skills that can keep turns functional when premium colors do not line up yet.",
                "evidence": sorted(low_cost_skills, key=lambda item: (item["cost_total"], item["name"], item["skill_name"]))[:8],
            }
        )

    if len(expensive_skills) >= len(members):
        notes.append(
            {
                "note_type": "expensive_skill_density",
                "risk_level": "medium",
                "summary": "Several 3+ chakra skills are present, so the team may need patience before its highest-output turns are fully online.",
                "evidence": sorted(expensive_skills, key=lambda item: (-item["cost_total"], item["name"], item["skill_name"]))[:8],
            }
        )

    return {
        "component_totals": {chakra_type: total_components.get(chakra_type, 0) for chakra_type in CHAKRA_TYPES},
        "skill_usage_counts": {chakra_type: total_skill_usage.get(chakra_type, 0) for chakra_type in CHAKRA_TYPES},
        "shared_pressure": shared_pressure,
        "low_cost_skills": sorted(low_cost_skills, key=lambda item: (item["cost_total"], item["name"], item["skill_name"])),
        "expensive_skills": sorted(expensive_skills, key=lambda item: (-item["cost_total"], item["name"], item["skill_name"])),
        "notes": notes,
    }


def build_strength_notes(
    members: list[dict[str, Any]],
    context: dict[str, Any],
    chakra_report: dict[str, Any],
) -> list[dict[str, Any]]:
    pressure_members = members_with_any_tag(members, PRESSURE_TAGS)
    control_members = members_with_any_tag(members, CONTROL_TAGS)
    sustain_members = members_with_any_tag(members, SUSTAIN_TAGS)
    setup_members = members_with_any_tag(members, SETUP_TAGS)
    resource_members = members_with_any_tag(members, RESOURCE_TAGS)

    notes = []
    if pressure_members and control_members:
        evidence_members = []
        for member in dedupe_members([*pressure_members, *control_members]):
            evidence_members.append(build_member_evidence(member, context, PRESSURE_TAGS.union(CONTROL_TAGS)))
        notes.append(
            {
                "note_id": "control_creates_pressure_windows",
                "summary": "The accepted bundle shows both control and damage tags, so the team has a grounded route to force cleaner attack windows.",
                "evidence": evidence_members,
            }
        )

    if pressure_members and sustain_members:
        evidence_members = []
        for member in dedupe_members([*pressure_members, *sustain_members]):
            evidence_members.append(build_member_evidence(member, context, PRESSURE_TAGS.union(SUSTAIN_TAGS)))
        notes.append(
            {
                "note_id": "sustain_backs_pressure",
                "summary": "Heal/protect/reduction tags can help the pressure pieces survive long enough to matter instead of demanding an immediate race.",
                "evidence": evidence_members,
            }
        )

    if setup_members and (control_members or sustain_members):
        evidence_members = []
        for member in dedupe_members([*setup_members, *control_members, *sustain_members]):
            evidence_members.append(build_member_evidence(member, context, SETUP_TAGS.union(CONTROL_TAGS).union(SUSTAIN_TAGS)))
        notes.append(
            {
                "note_id": "setup_has_cover",
                "summary": "Setup-dependent members are not isolated; the rest of the shell shows support or disruption that can cover those slower turns.",
                "evidence": evidence_members,
            }
        )

    if resource_members and control_members:
        evidence_members = []
        for member in dedupe_members([*resource_members, *control_members]):
            evidence_members.append(build_member_evidence(member, context, RESOURCE_TAGS.union(CONTROL_TAGS)))
        notes.append(
            {
                "note_id": "tempo_denial_angle",
                "summary": "Resource-denial tags plus control tags give the team a visible tempo-denial angle beyond pure raw damage.",
                "evidence": evidence_members,
            }
        )

    for chakra_note in chakra_report["notes"]:
        if chakra_note["note_type"] == "low_cost_options":
            notes.append(
                {
                    "note_id": "curve_has_low_cost_fallbacks",
                    "summary": "The bundle exposes at least a few cheap skills, so the team is not forced to skip every turn until premium colors appear.",
                    "evidence": chakra_note["evidence"],
                }
            )
            break

    return notes[:5]


def build_data_quality_warnings(members: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    tag_to_members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    parse_confidences = []

    for member in members:
        parse_confidence = member["data_quality"].get("parse_confidence")
        if isinstance(parse_confidence, (int, float)):
            parse_confidences.append(parse_confidence)
        for tag_id in member["data_quality"]["tag_ids"]:
            tag_to_members[tag_id].append(member)

    warnings = []
    for tag_id, affected_members in sorted(tag_to_members.items()):
        tag_meta = context["tag_meta_by_id"].get(tag_id, {})
        warnings.append(
            {
                "tag_id": tag_id,
                "label": tag_meta.get("label", tag_id),
                "definition": tag_meta.get("definition"),
                "members": sorted(member["name"] for member in affected_members),
            }
        )

    return {
        "warning_count": len(warnings),
        "parse_confidence_range": {
            "min": min(parse_confidences) if parse_confidences else None,
            "max": max(parse_confidences) if parse_confidences else None,
        },
        "warnings": warnings,
    }


def build_weakness_notes(
    members: list[dict[str, Any]],
    chakra_report: dict[str, Any],
    data_quality_report: dict[str, Any],
) -> list[dict[str, Any]]:
    pressure_members = members_with_any_tag(members, PRESSURE_TAGS)
    control_members = members_with_any_tag(members, CONTROL_TAGS)
    sustain_members = members_with_any_tag(members, SUSTAIN_TAGS)
    protection_members = members_with_any_tag(members, PROTECTION_TAGS)
    setup_members = members_with_any_tag(members, SETUP_TAGS)

    notes = []
    if not pressure_members:
        notes.append(
            {
                "note_id": "no_clear_pressure_tag",
                "risk_level": "high",
                "summary": "The selected trio does not show obvious damage or amplification tags, so the team lacks a clearly grounded closer from bundle evidence alone.",
            }
        )

    if not control_members:
        notes.append(
            {
                "note_id": "limited_control_tags",
                "risk_level": "medium",
                "summary": "No obvious stun/removal/drain tags are present, so the team may struggle to force safer attack windows.",
            }
        )

    if not sustain_members and not protection_members:
        notes.append(
            {
                "note_id": "limited_stabilization",
                "risk_level": "medium",
                "summary": "The team does not show strong heal/protect/reduction coverage, so its fallback plan may be fragile when the race goes badly.",
            }
        )

    if setup_members and not (control_members or sustain_members or protection_members):
        notes.append(
            {
                "note_id": "setup_without_cover",
                "risk_level": "high",
                "summary": "Setup-dependent tags are present without equally visible support/control cover, which makes those setup turns easier to punish.",
                "affected_members": sorted(member["name"] for member in setup_members),
            }
        )

    for chakra_note in chakra_report["notes"]:
        if chakra_note["note_type"] == "shared_chakra_pressure":
            notes.append(
                {
                    "note_id": f"chakra_pressure_{chakra_note['chakra_type']}",
                    "risk_level": chakra_note["risk_level"],
                    "summary": chakra_note["summary"],
                    "evidence": chakra_note["evidence"],
                }
            )

    if data_quality_report["warning_count"] > 0:
        notes.append(
            {
                "note_id": "data_quality_uncertainty",
                "risk_level": "medium",
                "summary": "One or more selected records carry accepted data-quality warnings, so exact targeting or effect semantics may remain partially uncertain.",
                "evidence": data_quality_report,
            }
        )

    return notes[:6]


def build_substitution_hooks(weakness_notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hooks = []
    for note in weakness_notes:
        note_id = note["note_id"]
        if note_id == "no_clear_pressure_tag":
            hooks.append(
                {
                    "reason": "Patch missing pressure",
                    "suggested_search_filters": {
                        "role_hints": ["pressure"],
                        "tag_ids": ["character.capability.damage_effects"],
                    },
                    "cli_example": "python scripts/search_characters.py --role-hint pressure --tag character.capability.damage_effects --limit 8",
                }
            )
        elif note_id == "limited_control_tags":
            hooks.append(
                {
                    "reason": "Add cleaner control windows",
                    "suggested_search_filters": {
                        "role_hints": ["control"],
                        "tag_ids": ["character.capability.stun_effects"],
                    },
                    "cli_example": "python scripts/search_characters.py --role-hint control --tag character.capability.stun_effects --limit 8",
                }
            )
        elif note_id == "limited_stabilization":
            hooks.append(
                {
                    "reason": "Add sustain or protection",
                    "suggested_search_filters": {
                        "role_hints": ["sustain", "protection"],
                        "tag_ids": ["character.capability.protect_effects"],
                    },
                    "cli_example": "python scripts/search_characters.py --role-hint sustain --role-hint protection --tag character.capability.protect_effects --limit 8",
                }
            )
        elif note_id.startswith("chakra_pressure_"):
            chakra_type = note_id.removeprefix("chakra_pressure_")
            hooks.append(
                {
                    "reason": f"Reduce shared {chakra_type} pressure",
                    "suggested_search_filters": {
                        "role_hints": [],
                        "chakra_types": [],
                        "exclude_chakra_types": [chakra_type],
                    },
                    "cli_example": f"python scripts/search_characters.py --exclude-chakra-type {chakra_type} --limit 8",
                }
            )
        elif note_id == "setup_without_cover":
            hooks.append(
                {
                    "reason": "Support setup turns with sustain or control",
                    "suggested_search_filters": {
                        "role_hints": ["control", "sustain"],
                        "tag_ids": [
                            "character.capability.stun_effects",
                            "character.capability.heal_effects",
                        ],
                    },
                    "cli_example": "python scripts/search_characters.py --role-hint control --role-hint sustain --limit 8",
                }
            )

    deduped = []
    seen = set()
    for hook in hooks:
        marker = hook["reason"]
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(hook)
    return deduped[:4]


def build_member_report(member: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": member["id"],
        "name": member["name"],
        "role_hints": member["role_hint_details"],
        "progression": member["progression"],
        "chakra_profile": {
            "component_totals": member["chakra_profile"]["component_totals"],
            "skill_usage_counts": member["chakra_profile"]["skill_usage_counts"],
            "top_types": member["chakra_profile"]["top_types"],
            "low_cost_skills": member["chakra_profile"]["low_cost_skills"],
            "expensive_skills": member["chakra_profile"]["expensive_skills"],
        },
        "skill_summaries": member["skill_summaries"],
        "data_quality": member["data_quality"],
        "provenance": {
            "record_source_ref_ids": member["record_source_ref_ids"],
            "record_sources": member["record_sources"],
        },
    }


def build_provenance_hooks(members: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "members": [
            {
                "member_id": member["id"],
                "name": member["name"],
                "record_sources": member["record_sources"],
                "skill_sources": [
                    {
                        "skill_id": skill["skill_id"],
                        "skill_name": skill["skill_name"],
                        "source_ref_ids": skill["source_ref_ids"],
                        "source_refs": skill["source_refs"],
                    }
                    for skill in member["skill_summaries"]
                ],
            }
            for member in members
        ]
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a transparent candidate-team report from the validated skill-local Naruto Arena bundle. "
            "The report resolves members, surfaces role-shell hints, chakra-pressure notes, strengths, weaknesses, "
            "substitution hooks, data-quality warnings, and provenance."
        )
    )
    parser.add_argument(
        "members",
        nargs="+",
        help="Character ids or names to resolve from the skill-local bundle. Use exact names or ids for deterministic resolution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if len(args.members) < 2:
        raise SystemExit("team_candidate_report.py expects at least two member inputs")

    context = load_reference_context()
    summaries = build_character_summaries(context)

    resolutions = []
    resolved_members = []
    seen_ids = set()

    for raw_member in args.members:
        resolution = resolve_character_query(raw_member, summaries)
        if resolution["status"] == "resolved":
            member = resolution["character"]
            duplicate = member["id"] in seen_ids
            if not duplicate:
                resolved_members.append(member)
                seen_ids.add(member["id"])
            resolutions.append(
                {
                    "input": raw_member,
                    "status": "resolved" if not duplicate else "duplicate",
                    "query_match": resolution.get("query_match"),
                    "character": {
                        "id": member["id"],
                        "name": member["name"],
                    },
                }
            )
            continue

        resolutions.append(
            {
                "input": raw_member,
                "status": resolution["status"],
                "candidates": resolution.get("candidates", []),
            }
        )

    unresolved = [item for item in resolutions if item["status"] != "resolved"]
    if unresolved:
        payload = {
            "status": "blocked",
            "requested_members": args.members,
            "resolutions": resolutions,
            "message": "At least one member could not be resolved uniquely from the skill-local bundle.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    chakra_report = build_team_chakra_report(resolved_members)
    data_quality_report = build_data_quality_warnings(resolved_members, context)
    team_identity_hints = build_team_identity_hints(resolved_members, context)
    strength_notes = build_strength_notes(resolved_members, context, chakra_report)
    weakness_notes = build_weakness_notes(resolved_members, chakra_report, data_quality_report)
    substitution_hooks = build_substitution_hooks(weakness_notes)

    payload = {
        "status": "ok",
        "requested_members": args.members,
        "resolved_member_count": len(resolved_members),
        "resolutions": resolutions,
        "members": [build_member_report(member) for member in resolved_members],
        "role_matrix": build_role_matrix(resolved_members),
        "team_identity_hints": team_identity_hints,
        "chakra_curve": chakra_report,
        "strength_notes": strength_notes,
        "weakness_notes": weakness_notes,
        "data_quality_warnings": data_quality_report,
        "substitution_hooks": substitution_hooks,
        "provenance_hooks": build_provenance_hooks(resolved_members),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

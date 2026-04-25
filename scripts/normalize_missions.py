#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any


BASE_URL = "https://www.naruto-arena.site"
PARSER_VERSION = "normalize_missions.py:v3"
OR_CONDITION_RE = re.compile(r"\bor\b", re.IGNORECASE)
SAME_TEAM_RE = re.compile(r"\bsame\s+team\b", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(r"[â€™']", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def to_record_id(prefix: str, value: str) -> str:
    slug = slugify_name(value)
    if not slug:
        raise ValueError(f"Could not slugify value for {prefix!r}: {value!r}")
    return f"{prefix}:{slug}"


def mission_id_from_slug(slug: str) -> str:
    return to_record_id("mission", slug)


def mission_detail_source_id_from_slug(slug: str) -> str:
    return to_record_id("source:mission-detail", slug)


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def make_flag(code: str, field: str | None = None, detail: str | None = None, severity: str = "warning") -> dict[str, Any]:
    flag: dict[str, Any] = {"code": code}
    if field is not None:
        flag["field"] = field
    if detail is not None:
        flag["detail"] = detail
    if severity:
        flag["severity"] = severity
    return flag


def dedupe_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for flag in flags:
        key = (
            flag.get("code"),
            flag.get("field"),
            flag.get("detail"),
            flag.get("severity"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(flag)
    return deduped


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def sanitize_progress_text(text: str) -> str:
    return re.sub(r"\s*\(\d+/\d+\)\s*$", "", text.strip())


def capture_mode_for_source(source: str | None) -> str:
    if source == "next-data":
        return "next_data"
    if source == "browser-fallback":
        return "browser_rendered"
    return "unknown"


def detail_state_from_record(detail_record: dict[str, Any]) -> str:
    page_props = detail_record.get("pageProps", {})
    if "missionStatus" in page_props:
        return "mission_status"
    if "__N_REDIRECT" in page_props:
        return "redirect"
    if detail_record.get("page") == "/_error" and not page_props:
        return "error_page"
    if detail_record.get("page") == "/" and detail_record.get("final_url") == f"{BASE_URL}/":
        return "unexpected_home"
    if not page_props:
        return "empty"
    return "other"


def build_source_ref(
    *,
    record: dict[str, Any],
    source_id: str,
    snapshot_path: Path,
    repo_root: Path,
    section: str,
) -> dict[str, Any]:
    route = record.get("route", "")
    return {
        "source_id": source_id,
        "url": f"{BASE_URL}{route}",
        "canonical_domain": "www.naruto-arena.site",
        "visibility": "session_aware",
        "capture_mode": capture_mode_for_source(record.get("source")),
        "retrieved_at": record.get("capturedAt"),
        "snapshot_path": relative_posix(snapshot_path, repo_root),
        "raw_text_hash": sha256_file(snapshot_path),
        "section": section,
        "version_label": record.get("buildId"),
    }


def build_character_index(characters_overview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    character_index: dict[str, dict[str, Any]] = {}
    for char in characters_overview.get("pageProps", {}).get("chars", []):
        name = char.get("name")
        if not name:
            continue
        character_id = to_record_id("character", name)
        skills: dict[str, str] = {}
        for skill in char.get("skills", []):
            skill_name = skill.get("name")
            if not skill_name:
                continue
            skills[skill_name] = f"skill:{slugify_name(name)}:{slugify_name(skill_name)}"
        character_index[name] = {
            "id": character_id,
            "skills": skills,
        }
    return character_index


def split_subject_tokens(subject: str) -> list[str]:
    tokens = [part.strip() for part in re.split(r"\s+or\s+|\s+and\s+|,\s*", subject) if part.strip()]
    return tokens or [subject.strip()]


def resolve_character_refs(subject: str, character_index: dict[str, dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    subject = subject.strip()
    if not subject:
        return [], []

    lowered = subject.casefold()
    if lowered.startswith("any "):
        return [], [
            make_flag(
                "character_group_not_modeled",
                "character_refs",
                f"Grouped character condition preserved only in condition_text: {subject}.",
                "warning",
            )
        ]

    flags: list[dict[str, Any]] = []
    refs: list[str] = []
    tokens = split_subject_tokens(subject)

    if len(tokens) > 1:
        flags.append(
            make_flag(
                "multi_character_condition_not_structured",
                "character_refs",
                f"Composite subject preserved only in condition_text: {subject}.",
                "info",
            )
        )

    for token in tokens:
        character = character_index.get(token)
        if character:
            refs.append(character["id"])
            continue
        flags.append(
            make_flag(
                "character_subject_not_resolved",
                "character_refs",
                f"Could not resolve '{token}' to a deterministic character id from characters overview.",
                "warning",
            )
        )

    return unique_strings(refs), flags


def parse_use_subject_and_skill(text: str) -> tuple[str | None, str | None]:
    if not text.startswith("Use "):
        return None, None

    before_quote, quote, remainder = text.partition('"')
    if not quote:
        return None, None

    skill_name, closing_quote, _ = remainder.partition('"')
    if not closing_quote:
        return None, None

    subject = before_quote[len("Use ") :].strip()
    if subject.endswith("'s"):
        subject = subject[:-2]
    elif subject.endswith("'"):
        subject = subject[:-1]
    return subject.strip(), skill_name.strip()


def extract_subject(text: str) -> str | None:
    if " with " in text:
        subject = text.split(" with ", 1)[1].rstrip(".")
        if subject.endswith(" on the same team"):
            subject = subject[: -len(" on the same team")]
        return subject.strip()
    if " against " in text:
        return text.split(" against ", 1)[1].rstrip(".").strip()
    return None


def requirement_type_for_text(text: str) -> str:
    lowered = text.casefold()
    if lowered.startswith("use "):
        return "use_skill"
    if " against " in lowered:
        return "win_against_character"
    if " in a row " in lowered:
        return "streak"
    if lowered.startswith("win "):
        return "win_with_character"
    if lowered.startswith("unlock "):
        return "unlock"
    if lowered.startswith("collect "):
        return "collect"
    if lowered.startswith("survive "):
        return "survive"
    return "unknown"


def requirement_confidence(requirement_type: str, flags: list[dict[str, Any]], placeholder: bool = False) -> float:
    if placeholder:
        return 0.25

    confidence = 0.95 if requirement_type != "unknown" else 0.45

    codes = {flag["code"] for flag in flags}
    if "multi_character_condition_not_structured" in codes:
        confidence = min(confidence, 0.85)
    if "character_group_not_modeled" in codes:
        confidence = min(confidence, 0.7)
    if "character_subject_not_resolved" in codes:
        confidence = min(confidence, 0.55)
    if "skill_reference_not_resolved" in codes:
        confidence = min(confidence, 0.6)

    return round(confidence, 2)


def build_character_choice(text: str, character_refs: list[str], confidence: float) -> dict[str, Any] | None:
    if len(character_refs) < 2:
        return None
    if not OR_CONDITION_RE.search(text) or SAME_TEAM_RE.search(text):
        return None
    return {
        "choice_type": "alternative_eligible_characters",
        "eligible_character_refs": character_refs,
        "progress_counting": "per_eligible_character_present",
        "max_progress_per_qualifying_battle": len(character_refs),
        "confidence": confidence,
        "ambiguity_flags": [],
    }


def build_requirement(
    *,
    mission_id: str,
    requirement_index: int,
    text: str,
    character_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    requirement_type = requirement_type_for_text(text)
    flags: list[dict[str, Any]] = []
    character_refs: list[str] = []
    skill_refs: list[str] = []

    subject = extract_subject(text)
    if subject:
        character_refs, subject_flags = resolve_character_refs(subject, character_index)
        flags.extend(subject_flags)

    if requirement_type == "use_skill":
        subject_name, skill_name = parse_use_subject_and_skill(text)
        if subject_name:
            character_refs, subject_flags = resolve_character_refs(subject_name, character_index)
            flags.extend(subject_flags)
        if subject_name and skill_name and subject_name in character_index:
            skill_ref = character_index[subject_name]["skills"].get(skill_name)
            if skill_ref:
                skill_refs.append(skill_ref)
            else:
                flags.append(
                    make_flag(
                        "skill_reference_not_resolved",
                        "skill_refs",
                        f"Could not resolve skill '{skill_name}' under '{subject_name}' from characters overview.",
                        "warning",
                    )
                )
        elif skill_name:
            flags.append(
                make_flag(
                    "skill_reference_not_resolved",
                    "skill_refs",
                    f"Could not resolve skill '{skill_name}' because the source character was not matched deterministically.",
                    "warning",
                )
            )

    count_match = re.search(r"\d+", text)
    count = int(count_match.group(0)) if count_match else None

    flags = dedupe_flags(flags)
    confidence = requirement_confidence(requirement_type, flags)
    requirement_id = f"{mission_id}:req:{requirement_index:02d}"

    return {
        "requirement_id": requirement_id,
        "step_index": requirement_index,
        "requirement_type": requirement_type,
        "character_refs": character_refs,
        "skill_refs": skill_refs,
        "character_choice": build_character_choice(text, character_refs, confidence),
        "count": count,
        "condition_text": text,
        "confidence": confidence,
        "ambiguity_flags": flags,
    }


def build_missing_requirement(*, mission_id: str, slug: str, detail_state: str) -> dict[str, Any]:
    state_detail = {
        "redirect": "Mission detail route returned a redirect payload instead of missionStatus.",
        "error_page": "Mission detail route rendered an error page with empty pageProps.",
        "unexpected_home": "Mission detail route fell back to the site home page instead of mission content.",
        "empty": "Mission detail route produced empty pageProps.",
        "other": "Mission detail route produced an unsupported pageProps shape.",
    }.get(detail_state, "Mission detail route did not expose missionStatus.")

    flags = dedupe_flags(
        [
            make_flag(
                "objective_text_missing",
                "requirements",
                f"Mission objective text was unavailable in the captured snapshot for /mission/{slug}.",
                "warning",
            ),
            make_flag(
                f"detail_payload_{detail_state}",
                "source_refs",
                state_detail,
                "warning",
            ),
        ]
    )

    return {
        "requirement_id": f"{mission_id}:req:01",
        "step_index": None,
        "requirement_type": "unknown",
        "character_refs": [],
        "skill_refs": [],
        "character_choice": None,
        "count": None,
        "condition_text": f"Mission objective unavailable in captured snapshot for route /mission/{slug}.",
        "confidence": requirement_confidence("unknown", flags, placeholder=True),
        "ambiguity_flags": flags,
    }


def build_rank_requirement(label: str | None) -> dict[str, Any]:
    flags = [
        make_flag(
            "numeric_rank_not_provided",
            "rank_requirement.numeric_rank",
            "The snapshot exposes only the rank label, not a numeric rank value.",
            "info",
        )
    ]
    return {
        "label": label,
        "numeric_rank": None,
        "raw_text": label,
        "confidence": 0.85 if label else 0.3,
        "ambiguity_flags": flags,
    }


def build_level_requirement(group_item: dict[str, Any], slug: str) -> int:
    level_requirement = group_item.get("levelRequirement")
    if not isinstance(level_requirement, int) or isinstance(level_requirement, bool) or level_requirement < 1:
        raise RuntimeError(
            f"Mission group row for {slug!r} is missing a valid integer levelRequirement."
        )
    return level_requirement


def build_rewards(
    *,
    group_item: dict[str, Any],
    mission_status: dict[str, Any] | None,
    character_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rewards: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []

    reward_name = group_item.get("unlockedCharacter")
    if mission_status and mission_status.get("unlockedChar"):
        reward_name = mission_status["unlockedChar"].get("name") or reward_name

    unlocked_border = mission_status.get("unlockedBorder") if mission_status else None

    if reward_name:
        character = character_index.get(reward_name)
        ambiguity_flags: list[dict[str, Any]] = []
        rewards.append(
            {
                "reward_type": "character_unlock",
                "character_id": character["id"] if character else None,
                "mission_id": None,
                "border_id": None,
                "raw_text": reward_name,
                "confidence": 0.98 if character else 0.6,
                "ambiguity_flags": ambiguity_flags
                if character
                else [
                    make_flag(
                        "reward_character_not_resolved",
                        "rewards.character_id",
                        f"Could not resolve reward character '{reward_name}' against characters overview.",
                        "warning",
                    )
                ],
            }
        )

    if unlocked_border:
        rewards.append(
            {
                "reward_type": "border_unlock",
                "character_id": None,
                "mission_id": None,
                "border_id": to_record_id("border", unlocked_border),
                "raw_text": unlocked_border,
                "confidence": 0.9,
                "ambiguity_flags": [],
            }
        )

    if not rewards:
        flags.append(
            make_flag(
                "reward_not_exposed",
                "rewards",
                "No reward character or border was exposed for this mission in the captured snapshot.",
                "warning",
            )
        )

    return rewards, flags


def build_prerequisites(
    *,
    group_item: dict[str, Any],
    mission_id_by_name: dict[str, str],
) -> list[dict[str, Any]]:
    prerequisites: list[dict[str, Any]] = []
    for prerequisite in group_item.get("completedRequeriments", []):
        name = prerequisite.get("name")
        if not name:
            continue
        ref_id = mission_id_by_name.get(name)
        flags: list[dict[str, Any]] = []
        confidence = 0.95
        if ref_id is None:
            confidence = 0.6
            flags.append(
                make_flag(
                    "prerequisite_mission_not_resolved",
                    "prerequisites.ref_id",
                    f"Could not resolve prerequisite mission '{name}' to a normalized mission id.",
                    "warning",
                )
            )

        prerequisites.append(
            {
                "prerequisite_type": "mission",
                "ref_id": ref_id,
                "raw_text": name,
                "confidence": round(confidence, 2),
                "ambiguity_flags": flags,
            }
        )
    return prerequisites


def build_group_summary_lines(group_item: dict[str, Any]) -> list[str]:
    lines = [
        f"Mission: {group_item['name']}",
        f"Section: {group_item['anime']}",
        f"Rank requirement: {group_item['rankRequirement']}",
    ]
    level_requirement = group_item.get("levelRequirement")
    if level_requirement is not None:
        lines.append(f"Level requirement: {level_requirement}")
    reward_name = group_item.get("unlockedCharacter")
    if reward_name:
        lines.append(f"Reward character: {reward_name}")
    for prerequisite in group_item.get("completedRequeriments", []):
        prerequisite_name = prerequisite.get("name")
        if prerequisite_name:
            lines.append(f"Prerequisite mission: {prerequisite_name}")
    return lines


def build_raw_text(
    *,
    group_lines: list[str],
    progress_lines: list[str],
    detail_source_id: str,
    group_source_id: str,
) -> dict[str, Any]:
    fragments: list[dict[str, Any]] = [
        {
            "field": "group_summary",
            "text": "\n".join(group_lines),
            "source_ref_id": group_source_id,
        }
    ]

    for index, line in enumerate(progress_lines, start=1):
        fragments.append(
            {
                "field": f"detail_progress_{index}",
                "text": line,
                "source_ref_id": detail_source_id,
            }
        )

    primary = "\n".join(progress_lines) if progress_lines else "\n".join(group_lines)
    return {
        "primary": primary,
        "fragments": fragments,
    }


def round_confidence(values: list[float]) -> float:
    return round(fmean(values), 2)


def build_parse_meta(
    *,
    detail_state: str,
    level_requirement: int,
    rank_requirement: dict[str, Any],
    requirements: list[dict[str, Any]],
    rewards: list[dict[str, Any]],
    prerequisites: list[dict[str, Any]],
    extra_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    notes: list[str] = []
    reasons: list[str] = []
    flags: list[dict[str, Any]] = []
    provisional_fields: list[str] = ["rank_requirement.numeric_rank"]

    if detail_state == "mission_status":
        reasons.append("Mission objective text was captured from missionStatus progress lines.")
        notes.append("Viewer progress counters were stripped from mission objective text.")
    else:
        reasons.append("Mission detail route did not expose missionStatus, so an unknown requirement placeholder was inserted.")
        provisional_fields.append("requirements")

    reasons.append(f"Level requirement {level_requirement} was mapped from the public mission group listing.")

    if rewards:
        reasons.append("Reward data was mapped from the mission group listing and cross-checked against characters overview.")
    else:
        reasons.append("No structured reward could be proven from the captured mission sources.")
        provisional_fields.append("rewards")

    if prerequisites:
        reasons.append("Prerequisite mission names were mapped deterministically from the mission group listing.")

    flags.extend(extra_flags)
    flags.extend(rank_requirement["ambiguity_flags"])
    for requirement in requirements:
        flags.extend(requirement["ambiguity_flags"])
    for reward in rewards:
        flags.extend(reward["ambiguity_flags"])
    for prerequisite in prerequisites:
        flags.extend(prerequisite["ambiguity_flags"])

    component_confidences = [rank_requirement["confidence"]] + [requirement["confidence"] for requirement in requirements]
    component_confidences.extend(reward["confidence"] for reward in rewards)
    component_confidences.extend(prerequisite["confidence"] for prerequisite in prerequisites)
    if not rewards:
        component_confidences.append(0.4)

    overall_confidence = round_confidence(component_confidences)
    if detail_state != "mission_status":
        overall_confidence = min(overall_confidence, 0.5)
    if not rewards:
        overall_confidence = min(overall_confidence, 0.8)

    return {
        "parser_version": PARSER_VERSION,
        "confidence": overall_confidence,
        "confidence_reasons": reasons,
        "ambiguity_flags": dedupe_flags(flags),
        "unsupported_version": False,
        "normalized_at": now_iso(),
        "provisional_fields": unique_strings(provisional_fields),
        "notes": unique_strings(notes),
    }


def build_steps(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for requirement in requirements:
        step_index = requirement.get("step_index")
        if step_index is None:
            continue
        steps.append(
            {
                "step_index": step_index,
                "text": requirement["condition_text"],
                "requirement_refs": [requirement["requirement_id"]],
                "confidence": requirement["confidence"],
                "ambiguity_flags": requirement["ambiguity_flags"],
            }
        )
    return steps


def build_mission_record(
    *,
    slug: str,
    group_item: dict[str, Any],
    group_record: dict[str, Any],
    group_path: Path,
    detail_record: dict[str, Any],
    detail_path: Path,
    repo_root: Path,
    character_index: dict[str, dict[str, Any]],
    mission_id_by_name: dict[str, str],
) -> dict[str, Any]:
    mission_id = mission_id_from_slug(slug)
    detail_state = detail_state_from_record(detail_record)
    mission_status = detail_record.get("pageProps", {}).get("missionStatus")
    level_requirement = build_level_requirement(group_item, slug)

    detail_source_id = mission_detail_source_id_from_slug(slug)
    group_source_id = f"source:mission-group:{group_path.stem}"

    group_lines = build_group_summary_lines(group_item)
    progress_lines = []
    if mission_status:
        progress_lines = [
            sanitized
            for step in mission_status.get("progress", [])
            if (sanitized := sanitize_progress_text(step.get("text", "")))
        ]

    if progress_lines:
        requirements = [
            build_requirement(
                mission_id=mission_id,
                requirement_index=index,
                text=line,
                character_index=character_index,
            )
            for index, line in enumerate(progress_lines, start=1)
        ]
    else:
        requirements = [
            build_missing_requirement(
                mission_id=mission_id,
                slug=slug,
                detail_state=detail_state,
            )
        ]

    rewards, reward_flags = build_rewards(
        group_item=group_item,
        mission_status=mission_status,
        character_index=character_index,
    )
    rank_requirement = build_rank_requirement(group_item.get("rankRequirement"))
    prerequisites = build_prerequisites(group_item=group_item, mission_id_by_name=mission_id_by_name)

    record = {
        "id": mission_id,
        "record_type": "mission",
        "record_family": "public_fact",
        "name": group_item["name"],
        "section_id": group_path.stem,
        "section_name": group_record.get("pageProps", {}).get("animeName"),
        "description": None,
        "level_requirement": level_requirement,
        "rank_requirement": rank_requirement,
        "requirements": requirements,
        "rewards": rewards,
        "prerequisites": prerequisites,
        "steps": build_steps(requirements),
        "source_refs": [
            build_source_ref(
                record=detail_record,
                source_id=detail_source_id,
                snapshot_path=detail_path,
                repo_root=repo_root,
                section="detail_page",
            ),
            build_source_ref(
                record=group_record,
                source_id=group_source_id,
                snapshot_path=group_path,
                repo_root=repo_root,
                section="group_page",
            ),
        ],
        "raw_text": build_raw_text(
            group_lines=group_lines,
            progress_lines=progress_lines,
            detail_source_id=detail_source_id,
            group_source_id=group_source_id,
        ),
        "parse": build_parse_meta(
            detail_state=detail_state,
            level_requirement=level_requirement,
            rank_requirement=rank_requirement,
            requirements=requirements,
            rewards=rewards,
            prerequisites=prerequisites,
            extra_flags=reward_flags,
        ),
    }

    return record


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    raw_root = repo_root / "snapshots" / "raw" / "site_capture" / "latest"
    output_path = repo_root / "data" / "normalized" / "missions.json"

    manifest = load_json(raw_root / "manifest.json")
    characters_overview = load_json(raw_root / "characters" / "overview.json")
    character_index = build_character_index(characters_overview)

    group_records: dict[str, dict[str, Any]] = {}
    group_paths: dict[str, Path] = {}
    mission_items_by_slug: dict[str, dict[str, Any]] = {}
    mission_id_by_name: dict[str, str] = {}

    for group_path in sorted((raw_root / "missions" / "groups").glob("*.json")):
        group_slug = group_path.stem
        group_record = load_json(group_path)
        group_records[group_slug] = group_record
        group_paths[group_slug] = group_path
        for item in group_record.get("pageProps", {}).get("animeMissions", []):
            mission_items_by_slug[item["linkTo"]] = {
                "group_item": item,
                "group_record": group_record,
                "group_path": group_path,
            }
            mission_id_by_name[item["name"]] = mission_id_from_slug(item["linkTo"])

    detail_slugs = manifest.get("missions", {}).get("detail_slugs", [])
    records: list[dict[str, Any]] = []
    detail_state_counts: dict[str, int] = {}

    for slug in detail_slugs:
        detail_path = raw_root / "missions" / "details" / f"{slug}.json"
        detail_record = load_json(detail_path)
        if slug not in mission_items_by_slug:
            raise RuntimeError(f"Mission slug {slug!r} exists in manifest but not in mission groups.")

        mission_context = mission_items_by_slug[slug]
        record = build_mission_record(
            slug=slug,
            group_item=mission_context["group_item"],
            group_record=mission_context["group_record"],
            group_path=mission_context["group_path"],
            detail_record=detail_record,
            detail_path=detail_path,
            repo_root=repo_root,
            character_index=character_index,
            mission_id_by_name=mission_id_by_name,
        )
        records.append(record)
        state = detail_state_from_record(detail_record)
        detail_state_counts[state] = detail_state_counts.get(state, 0) + 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "record_count": len(records),
                "output_path": relative_posix(output_path, repo_root),
                "detail_states": detail_state_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

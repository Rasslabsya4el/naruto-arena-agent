#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = REPO_ROOT / "snapshots" / "raw" / "site_capture" / "latest"
CHARACTER_INDEX_PATH = SNAPSHOT_ROOT / "characters" / "index.json"
CHARACTER_DETAILS_ROOT = SNAPSHOT_ROOT / "characters" / "details"
OUTPUT_PATH = REPO_ROOT / "data" / "normalized" / "characters.json"
PARSER_VERSION = "normalize_characters.py:2"
CHARACTERS_URL = "https://www.naruto-arena.site/characters-and-skills"
CANONICAL_DOMAIN = "www.naruto-arena.site"

ENERGY_MAP = {
    "Tai": "tai",
    "Nin": "nin",
    "Gen": "gen",
    "Blood": "bloodline",
    "Random": "random",
}

CANONICAL_CLASS_IDS = {
    "Physical": "physical",
    "Chakra": "chakra",
    "Mental": "mental",
    "Melee": "melee",
    "Ranged": "ranged",
    "Instant": "instant",
    "Action": "action",
    "Unique": "unique",
    "Passive": "passive",
    "Affliction": "affliction",
    "Control": "control",
    "Helpful": "helpful",
    "Harmful": "harmful",
}

TAG_RE = re.compile(r"<[A-Za-z]+>")
WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(r"[’']", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = TAG_RE.sub("", value)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def split_sentences(raw_text: str) -> list[tuple[str, str]]:
    raw_sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(raw_text) if part.strip()]
    return [(raw_sentence, clean_text(raw_sentence)) for raw_sentence in raw_sentences if clean_text(raw_sentence)]


def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def dedupe_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def make_ambiguity(
    code: str,
    field: str | None = None,
    detail: str | None = None,
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "code": code,
        "field": field,
        "detail": detail,
        "severity": severity,
    }


def map_capture_mode(raw_value: str | None) -> str:
    if raw_value == "next-data":
        return "next_data"
    if raw_value == "browser-fallback":
        return "browser_rendered"
    return "unknown"


def make_source_ref(
    *,
    source_id: str,
    snapshot_path: str,
    section: str,
    raw_payload: Any,
    source: str | None,
    captured_at: str | None,
    build_id: str | None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "url": CHARACTERS_URL,
        "canonical_domain": CANONICAL_DOMAIN,
        "visibility": "public",
        "capture_mode": map_capture_mode(source),
        "retrieved_at": captured_at,
        "snapshot_path": snapshot_path,
        "raw_text_hash": dump_hash(raw_payload),
        "section": section,
        "version_label": build_id,
    }


def make_raw_text_block(primary: str, fragments: list[dict[str, Any]]) -> dict[str, Any]:
    filtered_fragments = [fragment for fragment in fragments if fragment["text"]]
    block_primary = primary or (filtered_fragments[0]["text"] if filtered_fragments else "")
    return {
        "primary": block_primary,
        "fragments": filtered_fragments,
    }


def make_fragment(field: str, text: str | None, source_ref_id: str) -> dict[str, Any] | None:
    if not text:
        return None
    return {
        "field": field,
        "text": text,
        "source_ref_id": source_ref_id,
    }


def normalize_cost(raw_energy: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    ambiguities: list[dict[str, Any]] = []

    for token in raw_energy:
        mapped = ENERGY_MAP.get(token)
        if mapped is None:
            mapped = "unknown"
            ambiguities.append(
                make_ambiguity(
                    "unknown_energy_token",
                    field="cost",
                    detail=f"Unrecognized raw energy token: {token}",
                )
            )

        bucket = grouped.setdefault(
            mapped,
            {
                "chakra_type": mapped,
                "amount": 0,
                "raw_tokens": [],
                "confidence": 1.0 if mapped != "unknown" else 0.0,
            },
        )
        bucket["amount"] += 1
        bucket["raw_tokens"].append(token)

    components = [
        {
            "chakra_type": bucket["chakra_type"],
            "amount": bucket["amount"],
            "raw_text": " + ".join(bucket["raw_tokens"]),
            "confidence": bucket["confidence"],
        }
        for bucket in grouped.values()
    ]

    return (
        {
            "components": components,
            "total": sum(component["amount"] for component in components),
            "raw_text": " + ".join(raw_energy) if raw_energy else None,
            "confidence": 1.0 if not ambiguities else 0.5,
            "ambiguity_flags": dedupe_dicts(ambiguities),
        },
        ambiguities,
    )


def normalize_cooldown(raw_value: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ambiguities: list[dict[str, Any]] = []
    turns: int | None

    if isinstance(raw_value, int):
        turns = raw_value
    else:
        turns = None
        ambiguities.append(
            make_ambiguity(
                "invalid_cooldown_value",
                field="cooldown",
                detail=f"Expected integer cooldown but found {raw_value!r}.",
            )
        )

    return (
        {
            "turns": turns,
            "raw_text": None if turns is None else str(turns),
            "confidence": 1.0 if turns is not None else 0.0,
            "ambiguity_flags": dedupe_dicts(ambiguities),
        },
        ambiguities,
    )


def normalize_classes(raw_classes: list[str], source_ref_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    normalized: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    provisional = False

    for raw_label in raw_classes:
        cleaned = raw_label.strip("*")
        if raw_label in CANONICAL_CLASS_IDS:
            normalized.append(
                {
                    "class_id": CANONICAL_CLASS_IDS[raw_label],
                    "label": raw_label,
                    "source_ref_id": source_ref_id,
                    "confidence": 1.0,
                }
            )
            continue

        if cleaned in CANONICAL_CLASS_IDS and raw_label != cleaned:
            normalized.append(
                {
                    "class_id": CANONICAL_CLASS_IDS[cleaned],
                    "label": raw_label,
                    "source_ref_id": source_ref_id,
                    "confidence": 0.6,
                }
            )
            ambiguities.append(
                make_ambiguity(
                    "footnoted_class_token",
                    field="classes",
                    detail=f"Class token kept with raw suffix/prefix marker: {raw_label}",
                )
            )
            provisional = True
            continue

        ambiguities.append(
            make_ambiguity(
                "unrecognized_class_token",
                field="classes",
                detail=f"Class token omitted from normalized classes: {raw_label}",
            )
        )
        provisional = True

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str]] = set()
    for item in normalized:
        key = (item["class_id"], item["label"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped, dedupe_dicts(ambiguities), provisional


def extract_conditions(text: str, skill_lookup: dict[str, str]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []

    for pattern in (
        r"Requires '([^']+)'(?: to be active on [^.]+)?",
        r"During '([^']+)'",
        r"Cannot be used during '([^']+)'",
        r"Can only be used during '([^']+)'",
    ):
        for match in re.finditer(pattern, text):
            skill_name = match.group(1)
            conditions.append(
                {
                    "condition_type": "previous_skill",
                    "raw_text": match.group(0),
                    "normalized_ref": skill_lookup.get(skill_name),
                    "confidence": 1.0 if skill_name in skill_lookup else 0.5,
                }
            )

    for match in re.finditer(r"(When [^.]+?)(?:,|\.|$)", text):
        conditions.append(
            {
                "condition_type": "requires_state",
                "raw_text": match.group(1).strip(),
                "normalized_ref": None,
                "confidence": 0.5,
            }
        )

    for match in re.finditer(r"(At \d+ [^.]+? stacks?)(?:,|\.|$)", text):
        conditions.append(
            {
                "condition_type": "requires_state",
                "raw_text": match.group(1).strip(),
                "normalized_ref": None,
                "confidence": 0.5,
            }
        )

    return dedupe_dicts(conditions)


def infer_effect_types(text: str) -> list[str]:
    lower = text.lower()
    effect_types: list[str] = []
    has_additional_damage = "additional damage" in lower

    if has_additional_damage:
        effect_types.append("increase_damage")
    if not has_additional_damage and re.search(
        r"\b(?:deal|deals|dealing|receive|receives|receiving|take|takes|taking)\b.*\bdamage\b",
        lower,
    ):
        effect_types.append("damage")
    if re.search(r"\blose(?:s|ing)?\s+\d+\s+health\b", lower):
        effect_types.append("damage")
    if re.search(r"\bheal(?:s|ing)?\b", lower):
        effect_types.append("heal")
    if "stun" in lower:
        effect_types.append("stun")
    if "damage reduction" in lower:
        effect_types.append("reduce_damage")
    if re.search(r"\b(?:drain|absorb|absorption)\b", lower):
        effect_types.append("drain")
    if re.search(r"\bgain(?:s|ing)?\b.*\bchakra\b", lower):
        effect_types.append("gain")
    if "remove" in lower or "removing" in lower:
        if "effect" in lower or "skill" in lower or "state" in lower:
            effect_types.append("remove_state")
    if (
        "invulnerable" in lower
        or "ignore all harmful effects" in lower
        or "ignore harmful effects" in lower
        or "ignore non-damage effects" in lower
        or "ignore stun effects" in lower
    ):
        effect_types.append("protect")
    if (
        "cannot be countered" in lower
        or "cannot be removed" in lower
        or "cannot reduce damage" in lower
        or "unable to become invulnerable" in lower
        or "this skill is invisible" in lower
        or "invisible" in lower
    ):
        effect_types.append("apply_state")
    if (
        "replaced" in lower
        or "improved" in lower
        or "requires " in lower
        or "may be used" in lower
        or "cost 1 less" in lower
        or "cost 2 less" in lower
        or "becomes " in lower
        or "be classed as" in lower
    ):
        effect_types.append("conditional")

    return ordered_unique(effect_types)


def target_from_text(text: str, char_name: str) -> dict[str, Any]:
    lower = text.lower()
    char_lower = char_name.lower()

    if "all enemies" in lower:
        return {"target_type": "all_enemies", "target_count": None, "raw_text": "all enemies"}
    if "all allies" in lower:
        return {"target_type": "all_allies", "target_count": None, "raw_text": "all allies"}
    if "herself or an ally" in lower or "himself or an ally" in lower or "self or an ally" in lower:
        return {"target_type": "any", "target_count": 1, "raw_text": "self or an ally"}
    if "one enemy" in lower or "an enemy" in lower:
        return {"target_type": "enemy", "target_count": 1, "raw_text": "one enemy"}
    if "one ally" in lower or "an ally" in lower:
        return {"target_type": "ally", "target_count": 1, "raw_text": "one ally"}
    if (
        lower.startswith("this skill makes")
        or f"{char_lower} gains" in lower
        or f"{char_lower} will gain" in lower
        or f"{char_lower} loses" in lower
        or f"{char_lower} takes" in lower
        or f"{char_lower} will ignore" in lower
        or lower.startswith(char_lower)
    ):
        return {"target_type": "self", "target_count": 1, "raw_text": char_name}
    return {"target_type": "unknown", "target_count": None, "raw_text": None}


def magnitude_for_effect(effect_type: str, text: str) -> dict[str, Any]:
    lower = text.lower()

    if effect_type == "damage":
        match = re.search(r"(\d+)\s+(?:additional\s+)?(?:piercing\s+|affliction\s+)?damage", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "health", "operator": "exact", "raw_text": match.group(0)}
        match = re.search(r"lose(?:s|ing)?\s+(\d+)\s+health", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "health", "operator": "exact", "raw_text": match.group(0)}

    if effect_type == "heal":
        match = re.search(r"(\d+)\s+health", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "health", "operator": "exact", "raw_text": match.group(0)}

    if effect_type == "increase_damage":
        match = re.search(r"(\d+)\s+additional damage", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "health", "operator": "exact", "raw_text": match.group(0)}

    if effect_type == "reduce_damage":
        match = re.search(r"(\d+)\s*%", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "percent", "operator": "exact", "raw_text": match.group(0)}
        match = re.search(r"(\d+)\s+(?:points? of\s+)?(?:unpierceable\s+)?damage reduction", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "health", "operator": "exact", "raw_text": match.group(0)}

    if effect_type in {"gain", "drain", "conditional"}:
        match = re.search(r"(\d+)\s+less\s+\w+\s+chakra", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "chakra", "operator": "exact", "raw_text": match.group(0)}
        match = re.search(r"(\d+)\s+chakra", lower)
        if match:
            amount = int(match.group(1))
            return {"amount": amount, "unit": "chakra", "operator": "exact", "raw_text": match.group(0)}

    return {"amount": None, "unit": "unknown", "operator": "unknown", "raw_text": None}


def duration_for_effect(effect_type: str, text: str) -> dict[str, Any]:
    lower = text.lower()

    match = re.search(r"the following (\d+) turns", lower)
    if match:
        return {"turns": int(match.group(1)), "timing": "ongoing", "raw_text": match.group(0)}

    if "the following turn" in lower:
        return {"turns": 1, "timing": "next_turn", "raw_text": "the following turn"}

    match = re.search(r"for (\d+) turns?", lower)
    if match:
        return {"turns": int(match.group(1)), "timing": "ongoing", "raw_text": match.group(0)}

    if "next turn" in lower:
        return {"turns": 1, "timing": "next_turn", "raw_text": "next turn"}

    if "this turn" in lower:
        return {"turns": 1, "timing": "this_turn", "raw_text": "this turn"}

    if "permanently" in lower:
        return {"turns": None, "timing": "ongoing", "raw_text": "permanently"}

    if effect_type in {"damage", "heal", "increase_damage", "drain", "gain"}:
        return {"turns": None, "timing": "instant", "raw_text": None}

    return {"turns": None, "timing": "unknown", "raw_text": None}


def confidence_for_effect(
    effect_type: str,
    targeting: dict[str, Any],
    magnitude: dict[str, Any],
) -> float:
    confidence = 0.75

    if effect_type in {"conditional", "apply_state"}:
        confidence -= 0.15
    if effect_type == "unknown":
        confidence = 0.35
    if targeting["target_type"] == "unknown":
        confidence -= 0.1
    if effect_type in {"damage", "heal", "increase_damage", "reduce_damage", "gain", "drain"} and magnitude["amount"] is None:
        confidence -= 0.15

    return round(max(0.35, confidence), 2)


def build_effects(
    *,
    description: str,
    char_id: str,
    char_name: str,
    skill_lookup: dict[str, str],
) -> tuple[list[dict[str, Any]], bool]:
    effects: list[dict[str, Any]] = []
    skill_level_conditions: list[dict[str, Any]] = []
    provisional = False

    for raw_sentence, clean_sentence in split_sentences(description):
        effect_types = infer_effect_types(clean_sentence)
        lower_sentence = clean_sentence.lower()
        local_conditions = extract_conditions(clean_sentence, skill_lookup)

        if effect_types == ["conditional"] and (
            lower_sentence.startswith("requires ")
            or lower_sentence.startswith("cannot be used during ")
            or lower_sentence.startswith("can only be used during ")
            or lower_sentence.startswith("when ")
            or lower_sentence.startswith("at ")
        ):
            skill_level_conditions.extend(local_conditions)
            provisional = True
            continue

        if not effect_types:
            if local_conditions:
                skill_level_conditions.extend(local_conditions)
                provisional = True
            continue

        provisional = True
        for effect_type in effect_types:
            targeting = target_from_text(clean_sentence, char_name)
            magnitude = magnitude_for_effect(effect_type, clean_sentence)
            duration = duration_for_effect(effect_type, clean_sentence)
            ambiguities: list[dict[str, Any]] = []

            if targeting["target_type"] == "unknown":
                ambiguities.append(
                    make_ambiguity(
                        "effect_target_unknown",
                        field="effects",
                        detail=f"Could not infer target from: {clean_sentence}",
                    )
                )

            if effect_type in {"damage", "heal", "increase_damage", "reduce_damage", "gain", "drain"} and magnitude["amount"] is None:
                ambiguities.append(
                    make_ambiguity(
                        "effect_magnitude_unknown",
                        field="effects",
                        detail=f"Could not infer numeric magnitude from: {clean_sentence}",
                    )
                )

            if effect_type in {"conditional", "apply_state"}:
                ambiguities.append(
                    make_ambiguity(
                        "effect_type_heuristic",
                        field="effects",
                        detail=f"Effect type inferred heuristically from: {clean_sentence}",
                        severity="info",
                    )
                )

            effects.append(
                {
                    "effect_id": f"effect:{char_id}:{len(effects) + 1}",
                    "effect_type": effect_type,
                    "targeting": targeting,
                    "magnitude": magnitude,
                    "duration": duration,
                    "conditions": dedupe_dicts(skill_level_conditions + local_conditions),
                    "raw_text": clean_sentence,
                    "confidence": confidence_for_effect(effect_type, targeting, magnitude),
                    "ambiguity_flags": dedupe_dicts(ambiguities),
                }
            )

    if not effects:
        provisional = True
        clean_description = clean_text(description)
        effects.append(
            {
                "effect_id": f"effect:{char_id}:1",
                "effect_type": "unknown",
                "targeting": {
                    "target_type": "unknown",
                    "target_count": None,
                    "raw_text": None,
                },
                "magnitude": {
                    "amount": None,
                    "unit": "unknown",
                    "operator": "unknown",
                    "raw_text": None,
                },
                "duration": {
                    "turns": None,
                    "timing": "unknown",
                    "raw_text": None,
                },
                "conditions": dedupe_dicts(skill_level_conditions),
                "raw_text": clean_description,
                "confidence": 0.35,
                "ambiguity_flags": [
                    make_ambiguity(
                        "effect_fallback_unknown",
                        field="effects",
                        detail=f"No structured effect heuristic matched: {clean_description}",
                    )
                ],
            }
        )

    deduped_effects: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for effect in effects:
        key = (effect["effect_type"], effect["raw_text"])
        if key in seen:
            continue
        seen.add(key)
        effect["effect_id"] = f"effect:{char_id}:{len(deduped_effects) + 1}"
        deduped_effects.append(effect)

    return deduped_effects, provisional


def build_parse_meta(
    *,
    confidence: float,
    reasons: list[str],
    ambiguities: list[dict[str, Any]],
    provisional_fields: list[str],
    notes: list[str] | None = None,
    normalized_at: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "parser_version": PARSER_VERSION,
        "confidence": round(confidence, 2),
        "confidence_reasons": ordered_unique(reasons),
        "ambiguity_flags": dedupe_dicts(ambiguities),
        "unsupported_version": False,
        "normalized_at": normalized_at,
        "provisional_fields": ordered_unique(provisional_fields),
    }
    if notes:
        payload["notes"] = notes
    return payload


def normalize_skill(
    *,
    char_id: str,
    char_name: str,
    slot: int,
    raw_skill: dict[str, Any],
    snapshot_path: str,
    source: str | None,
    captured_at: str | None,
    build_id: str | None,
    normalized_at: str,
    skill_lookup: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    skill_name = raw_skill["name"]
    skill_slug = slugify_name(skill_name) or f"skill-{slot}"
    skill_id = f"skill:{char_id}:{slot}:{skill_slug}"
    source_ref_id = f"source:{char_id}:skill:{slot}"
    source_ref = make_source_ref(
        source_id=source_ref_id,
        snapshot_path=snapshot_path,
        section=f"skill:{slot}:{skill_name}",
        raw_payload=raw_skill,
        source=source,
        captured_at=captured_at,
        build_id=build_id,
    )

    cost, cost_ambiguities = normalize_cost(raw_skill.get("energy", []))
    cooldown, cooldown_ambiguities = normalize_cooldown(raw_skill.get("cooldown"))
    classes, class_ambiguities, provisional_classes = normalize_classes(raw_skill.get("classes", []), source_ref_id)
    effects, provisional_effects = build_effects(
        description=raw_skill.get("description", ""),
        char_id=f"{char_id}:skill:{slot}",
        char_name=char_name,
        skill_lookup=skill_lookup,
    )
    effect_ambiguities = [flag for effect in effects for flag in effect["ambiguity_flags"]]

    raw_fragments = [
        make_fragment("name", raw_skill.get("name"), source_ref_id),
        make_fragment("theme_name", raw_skill.get("themeName"), source_ref_id),
        make_fragment("description", raw_skill.get("description"), source_ref_id),
        make_fragment("energy", " | ".join(raw_skill.get("energy", [])), source_ref_id),
        make_fragment("classes", " | ".join(raw_skill.get("classes", [])), source_ref_id),
        make_fragment(
            "cooldown",
            None if raw_skill.get("cooldown") is None else str(raw_skill.get("cooldown")),
            source_ref_id,
        ),
    ]

    reasons = [
        "name, cost, cooldown, and raw description were copied directly from the raw snapshot",
        "effect records were inferred heuristically from raw description text",
    ]
    provisional_fields = ["effects"]
    notes: list[str] = []
    confidence = 0.82
    all_ambiguities = cost_ambiguities + cooldown_ambiguities + class_ambiguities + effect_ambiguities

    if provisional_classes:
        confidence -= 0.1
        reasons.append("some raw class tokens were malformed or footnoted and could not be normalized cleanly")
        provisional_fields.append("classes")

    if provisional_effects:
        confidence -= 0.1

    if raw_skill.get("url") or raw_skill.get("themepic"):
        notes.append("External image URLs were kept only in raw snapshot provenance and not copied into normalized image_refs.")

    return (
        {
            "record_type": "skill",
            "record_family": "public_fact",
            "skill_id": skill_id,
            "slot": slot,
            "name": skill_name,
            "description": clean_text(raw_skill.get("description")),
            "cost": cost,
            "cooldown": cooldown,
            "classes": classes,
            "effects": effects,
            "source_refs": [source_ref],
            "raw_text": make_raw_text_block(
                primary=raw_skill.get("description") or skill_name,
                fragments=[fragment for fragment in raw_fragments if fragment],
            ),
            "parse": build_parse_meta(
                confidence=max(0.4, confidence),
                reasons=reasons,
                ambiguities=all_ambiguities,
                provisional_fields=provisional_fields,
                notes=notes or None,
                normalized_at=normalized_at,
            ),
        },
        all_ambiguities,
    )


def normalize_character(
    *,
    detail_path: Path,
    raw_entry: dict[str, Any],
    normalized_at: str,
) -> dict[str, Any]:
    raw_character = raw_entry["character"]
    char_slug = slugify_name(raw_character["name"]) or "character"
    char_id = f"character:{char_slug}"
    snapshot_path = relative_path(detail_path)
    source_ref_id = f"source:{char_id}:character"
    source_ref = make_source_ref(
        source_id=source_ref_id,
        snapshot_path=snapshot_path,
        section=f"character:{raw_character['name']}",
        raw_payload=raw_character,
        source=raw_entry.get("source"),
        captured_at=raw_entry.get("capturedAt"),
        build_id=raw_entry.get("buildId"),
    )

    raw_skills = raw_character.get("skills", [])
    skill_lookup = {
        skill["name"]: f"skill:{char_id}:{slot}:{slugify_name(skill['name']) or f'skill-{slot}'}"
        for slot, skill in enumerate(raw_skills, start=1)
    }
    normalized_skills: list[dict[str, Any]] = []
    skill_ambiguities: list[dict[str, Any]] = []
    for slot, raw_skill in enumerate(raw_skills, start=1):
        normalized_skill, ambiguities = normalize_skill(
            char_id=char_id,
            char_name=raw_character["name"],
            slot=slot,
            raw_skill=raw_skill,
            snapshot_path=snapshot_path,
            source=raw_entry.get("source"),
            captured_at=raw_entry.get("capturedAt"),
            build_id=raw_entry.get("buildId"),
            normalized_at=normalized_at,
            skill_lookup=skill_lookup,
        )
        normalized_skills.append(normalized_skill)
        skill_ambiguities.extend(ambiguities)

    raw_fragments = [
        make_fragment("name", raw_character.get("name"), source_ref_id),
        make_fragment("description", raw_character.get("description"), source_ref_id),
        make_fragment(
            "skill_names",
            " | ".join(skill.get("name", "") for skill in raw_skills if skill.get("name")),
            source_ref_id,
        ),
    ]

    availability_ambiguities = [
        make_ambiguity(
            "availability_not_in_character_snapshot",
            field="availability",
            detail="The listed raw snapshot does not expose provable character unlock data.",
        )
    ]

    parse_ambiguities = availability_ambiguities + skill_ambiguities
    provisional_fields = ["availability", "classes"]
    reasons = [
        "character names, descriptions, and skill lists were copied directly from the raw snapshot",
        "unlock availability is not present in the listed snapshot and remains explicitly unknown",
        "character-level classes are not provided by the raw character cards",
    ]
    notes: list[str] = []
    confidence = 0.72

    if not raw_skills:
        confidence -= 0.17
        reasons.append("this raw character entry currently has zero skills because the canonical snapshot marks it as temporarily disabled")
        parse_ambiguities.append(
            make_ambiguity(
                "no_skill_entries_in_snapshot",
                field="skills",
                detail="Raw character entry contains zero skills.",
            )
        )
        notes.append("Current raw snapshot marks this character as temporarily disabled and provides no skill entries.")

    if raw_character.get("url") or raw_character.get("themepic"):
        notes.append("External image URLs were kept only in raw snapshot provenance and not copied into normalized image_refs.")

    return {
        "id": char_id,
        "record_type": "character",
        "record_family": "public_fact",
        "name": raw_character["name"],
        "description": clean_text(raw_character.get("description")) or None,
        "availability": {
            "unlock_state": "unknown",
            "unlock_mission_id": None,
            "unlock_mission_name": None,
            "raw_unlock_text": None,
            "confidence": 0.0,
            "ambiguity_flags": dedupe_dicts(availability_ambiguities),
        },
        "classes": [],
        "skills": normalized_skills,
        "source_refs": [source_ref],
        "raw_text": make_raw_text_block(
            primary=raw_character.get("description") or raw_character["name"],
            fragments=[fragment for fragment in raw_fragments if fragment],
        ),
        "parse": build_parse_meta(
            confidence=max(0.4, confidence),
            reasons=reasons,
            ambiguities=parse_ambiguities,
            provisional_fields=provisional_fields,
            notes=notes or None,
            normalized_at=normalized_at,
        ),
    }


def character_exclusion_reason(raw_character: dict[str, Any]) -> str | None:
    raw_skills = raw_character.get("skills", [])
    if raw_skills:
        return None

    description = clean_text(raw_character.get("description"))
    if "temporarily disabled" in description.lower():
        return "Excluded because the canonical raw snapshot marks this character as temporarily disabled and provides zero skills."

    return "Excluded because the canonical raw snapshot provides zero skills, which violates the current character schema."


def build_characters() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    normalized_at = now_iso()
    index_entries = load_json(CHARACTER_INDEX_PATH)
    records: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []

    for item in index_entries:
        detail_path = SNAPSHOT_ROOT / item["file"]
        raw_entry = load_json(detail_path)
        raw_character = raw_entry["character"]
        exclusion_reason = character_exclusion_reason(raw_character)
        if exclusion_reason is not None:
            excluded.append(
                {
                    "name": raw_character["name"],
                    "snapshot_path": relative_path(detail_path),
                    "reason": exclusion_reason,
                }
            )
            continue
        records.append(
            normalize_character(
                detail_path=detail_path,
                raw_entry=raw_entry,
                normalized_at=normalized_at,
            )
        )

    return records, excluded


def main() -> None:
    records, excluded = build_characters()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    verified = load_json(OUTPUT_PATH)

    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                "record_count": len(verified),
                "excluded_characters": excluded,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

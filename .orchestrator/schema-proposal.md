# Naruto Arena Normalized Schema Proposal

Status: draft for `TASK-SCHEMA-PLAN-01`.

This proposal defines the data direction for canonical Naruto Arena references sourced only from `https://www.naruto-arena.site/`. It is a planning artifact, not an implemented schema or validator package. The model intentionally stays separate from team recommendation reasoning: records describe source-backed game facts, while future skill/helper logic consumes those records to reason about teams.

## Design Principles

- Keep every normalized fact traceable to a canonical source URL and raw extracted text.
- Preserve ambiguity instead of silently choosing an interpretation when source text is unclear.
- Represent effects and tags as machine-readable annotations with definitions, confidence, and provenance.
- Avoid inventing game mechanics before site reconnaissance confirms page structure and vocabulary.
- Store enough parse metadata to audit missing data, low-confidence records, and unsupported source versions.

## Shared Record Conventions

Every top-level record should include these fields unless site reconnaissance proves a narrower shape is safer:

```json
{
  "id": "stable_slug",
  "name": "Source Display Name",
  "record_type": "character | skill | mission | tag | source_snapshot",
  "source_refs": [
    {
      "source_id": "src_character_naruto",
      "url": "https://www.naruto-arena.site/...",
      "canonical_domain": "www.naruto-arena.site",
      "retrieved_at": "2026-04-24T00:00:00Z",
      "snapshot_path": "references/raw/...html",
      "raw_text_hash": "sha256:...",
      "section": "optional page section or selector",
      "version_label": "site reported version if present, else null"
    }
  ],
  "raw_text": {
    "primary": "Exact extracted text used for this record.",
    "fragments": [
      {
        "field": "skills[0].description",
        "text": "Exact source text for the field.",
        "source_ref_id": "src_character_naruto"
      }
    ]
  },
  "parse": {
    "parser_version": "draft-or-tool-version",
    "confidence": 0.0,
    "confidence_reasons": ["why confidence is not 1.0"],
    "ambiguity_flags": ["ambiguous_effect_scope"],
    "unsupported_version": false,
    "normalized_at": "2026-04-24T00:00:00Z"
  }
}
```

## Character Records

Character records should describe roster facts and link to skill records without embedding team-building recommendations. The normalized output should expose characters as first-class records, not only as names nested inside missions or teams.

```json
{
  "id": "naruto_uzumaki",
  "record_type": "character",
  "name": "Naruto Uzumaki",
  "display_name": "Naruto Uzumaki",
  "aliases": [],
  "availability": {
    "unlock_state": "starter | mission_unlock | unknown",
    "unlock_mission_ids": [],
    "raw_unlock_text": null
  },
  "classes": [
    {
      "class_id": "class_ninja",
      "label": "source class label",
      "source_ref_id": "src_character_naruto",
      "confidence": 0.0
    }
  ],
  "skill_ids": ["skill_naruto_uzumaki_1"],
  "tags": [
    {
      "tag_id": "tag_damage",
      "assigned_by": "parser | curator | taxonomy_rule",
      "confidence": 0.0,
      "evidence_field": "skills[0].effects[0]"
    }
  ],
  "source_refs": [],
  "raw_text": {},
  "parse": {}
}
```

Required character fields: `id`, `name`, `skill_ids`, `source_refs`, `raw_text`, and `parse.confidence`. Availability, aliases, classes, and tags may be unknown but must be explicit rather than omitted after extraction.

## Skill Records

Skill records carry the most important mechanical detail. They should preserve source wording and extract structured fields only when supported by source text.

```json
{
  "id": "skill_naruto_uzumaki_1",
  "record_type": "skill",
  "character_id": "naruto_uzumaki",
  "name": "Source Skill Name",
  "slot": 1,
  "raw_description": "Exact source description.",
  "cost": {
    "components": [
      { "chakra_type": "tai | nin | gen | bloodline | random | unknown", "amount": 1 }
    ],
    "total": 1,
    "raw_text": "Exact cost text or icon alt text.",
    "confidence": 0.0
  },
  "cooldown": {
    "turns": 0,
    "raw_text": "Exact cooldown text.",
    "confidence": 0.0
  },
  "classes": [
    {
      "class_id": "class_physical",
      "label": "source class label",
      "source_ref_id": "src_character_naruto",
      "confidence": 0.0
    }
  ],
  "effects": [
    {
      "effect_id": "effect_skill_naruto_uzumaki_1_1",
      "effect_type": "damage | heal | stun | protect | reduce_damage | increase_damage | drain | gain | apply_state | remove_state | conditional | unknown",
      "targeting": {
        "target_type": "enemy | ally | self | all_enemies | all_allies | any | unknown",
        "target_count": 1,
        "raw_text": "source target wording"
      },
      "magnitude": {
        "amount": null,
        "unit": "health | chakra | turns | percent | unknown",
        "operator": "exact | up_to | at_least | per_turn | unknown",
        "raw_text": "source magnitude wording"
      },
      "duration": {
        "turns": null,
        "timing": "instant | this_turn | next_turn | ongoing | unknown",
        "raw_text": "source duration wording"
      },
      "conditions": [
        {
          "condition_type": "requires_state | target_class | previous_skill | mission_context | unknown",
          "raw_text": "source condition wording",
          "normalized_ref": null,
          "confidence": 0.0
        }
      ],
      "raw_text": "exact phrase supporting this effect",
      "confidence": 0.0,
      "ambiguity_flags": []
    }
  ],
  "tags": [],
  "source_refs": [],
  "raw_text": {},
  "parse": {}
}
```

Costs should not default missing values to zero. If the site omits or renders cost in an unparsed icon, use `chakra_type: "unknown"`, retain raw text/icon metadata, and flag `cost_unparsed`.

Cooldowns should accept integer turns only when explicitly parsed. Unknown, variable, or conditional cooldowns should be represented with `turns: null`, raw wording, and an ambiguity flag.

## Mission Records

Mission records should support mission-aware team planning without precomputing recommendations.

```json
{
  "id": "mission_source_slug",
  "record_type": "mission",
  "name": "Source Mission Name",
  "raw_description": "Exact source mission text.",
  "requirements": [
    {
      "requirement_id": "req_mission_source_slug_1",
      "requirement_type": "win_with_character | win_against_character | use_skill | streak | unlock | unknown",
      "character_refs": ["naruto_uzumaki"],
      "skill_refs": [],
      "count": null,
      "condition_text": "Exact requirement wording.",
      "confidence": 0.0,
      "ambiguity_flags": []
    }
  ],
  "rewards": [
    {
      "reward_type": "character_unlock | mission_unlock | unknown",
      "character_id": null,
      "mission_id": null,
      "raw_text": "Exact reward wording.",
      "confidence": 0.0
    }
  ],
  "prerequisites": [
    {
      "prerequisite_type": "mission | character | unknown",
      "ref_id": null,
      "raw_text": "Exact prerequisite wording.",
      "confidence": 0.0
    }
  ],
  "tags": [],
  "source_refs": [],
  "raw_text": {},
  "parse": {}
}
```

Mission requirements should remain source-fact records. Future optimization logic can use `requirements`, `rewards`, and character/skill refs to build coverage matrices, but those matrices should not live in the mission schema as fixed recommendations.

## Tag Definition Records

Tags should be curated or taxonomy-rule outputs, not free-form labels sprinkled through data. A tag definition should explain what evidence is required and where the tag may be applied.

```json
{
  "id": "tag_control",
  "record_type": "tag",
  "label": "control",
  "applies_to": ["character", "skill", "effect", "mission"],
  "definition": "A source-backed or effect-derived label used for retrieval and reasoning.",
  "inference_rules": [
    {
      "rule_id": "rule_tag_control_1",
      "source": "effect_taxonomy | curated",
      "requires_effect_types": ["stun"],
      "requires_raw_terms": [],
      "excludes_when": [],
      "confidence_floor": 0.8
    }
  ],
  "examples": [],
  "non_examples": [],
  "status": "draft | accepted | deprecated",
  "source_refs": [],
  "parse": {
    "confidence": 1.0,
    "ambiguity_flags": []
  }
}
```

Initial tag categories should be conservative: mechanical tags derived from effect objects, cost/curve tags derived from costs and cooldowns, and mission tags derived from mission requirements. Strategy-facing labels such as `burst`, `control`, or `stall` should remain tentative until site data and taxonomy rules define evidence thresholds.

## Effect Taxonomy Strategy

The initial taxonomy should be a controlled vocabulary plus `unknown`, not a claim that every Naruto Arena mechanic is already understood. Suggested top-level types:

- `damage`: source text states health damage or damage over time.
- `heal`: source text states health restoration.
- `stun`: source text states a target cannot use one or more skill classes or skills.
- `protect`: source text states invulnerability, protection, counter-prevention, or damage avoidance; subtypes must wait for site wording.
- `reduce_damage` and `increase_damage`: source text modifies damage taken or dealt.
- `drain` and `gain`: source text removes or grants chakra/resources.
- `apply_state` and `remove_state`: source text applies/removes a named condition that is not yet safely mapped to another type.
- `conditional`: effect only applies under a source-stated condition.
- `unknown`: parser found effect-like text but cannot safely classify it.

Each taxonomy entry should define allowed fields, required evidence, incompatible fields, and validator behavior. For example, `damage` requires a health magnitude or an ambiguity flag explaining why magnitude is unavailable; `stun` requires a duration or a duration ambiguity flag; `unknown` requires raw text and a low-confidence warning.

## Validator Plan

Validators should run as pipeline gates before skill references are built.

### Provenance And Version Validators

- Reject top-level records without at least one `source_refs[].url`.
- Reject source URLs outside `https://www.naruto-arena.site/` unless an explicit future version-comparison mode is enabled.
- Warn or reject records with `unsupported_version: true` or a `version_label` not accepted by project config.
- Verify `snapshot_path` exists for records produced from snapshots once raw ingestion exists.

### Completeness Validators

- Reject character records missing `id`, `name`, `skill_ids`, `raw_text.primary`, or `parse.confidence`.
- Reject skill records missing `character_id`, `name`, `raw_description`, `cost`, `cooldown`, `effects`, or source refs.
- Reject mission records missing `name`, `raw_description`, `requirements`, source refs, or confidence metadata.
- Warn when optional fields remain unknown after extraction, but require explicit `unknown`/`null` plus an ambiguity flag rather than omission.

### Parse Integrity Validators

- Compare raw page extraction counts to normalized record counts to catch silent parse drops.
- Require every raw character/skill/mission fragment to be either normalized or listed in a `parse_drop_report` with reason and source URL.
- Reject records with `parse.confidence` below the configured publish threshold for skill references; keep them in quarantine/draft outputs.
- Require `confidence_reasons` when confidence is less than `1.0`.

### Mechanical Field Validators

- Validate chakra cost components use only configured chakra types plus `unknown`.
- Reject negative cost amounts and negative cooldowns.
- Reject numeric cooldowns that are not integers.
- Require raw text and ambiguity flags for unknown, variable, or conditional costs/cooldowns.
- Validate effects use defined `effect_type` values and required fields for each type.

### Taxonomy Validators

- Reject undefined tags: every record tag must be present in tag definitions before published references are built.
- Reject tag assignments below the tag definition confidence floor for published references.
- Require `assigned_by`, `confidence`, and evidence for every tag assignment.
- Detect tags whose inference rules reference undefined effect types, classes, or fields.

### Cross-Reference Validators

- Validate `character_id`, `skill_ids`, mission character refs, mission skill refs, unlock refs, and prerequisites point to known records or are explicitly unresolved with raw text.
- Detect duplicate IDs and conflicting normalized names.
- Detect source fragments that map to multiple incompatible records without an ambiguity flag.

## Refinement Needed After Site Reconnaissance

- Actual page inventory: roster pages, individual character pages, mission pages, unlock pages, and whether data is server-rendered or scripted.
- Source selectors and text boundaries for names, skill slots, costs, cooldowns, classes, and mission requirements.
- Canonical representation of chakra icons/types and whether alt text or filenames are needed as raw evidence.
- Actual class vocabulary used by the site and whether classes apply to skills, effects, or both.
- Mission wording patterns, reward/prerequisite structure, and whether missions reference hidden IDs or only display names.
- Whether the site exposes an explicit version/build label; if not, version support should be represented by canonical domain plus snapshot timestamp.
- Real examples of ambiguous skills to calibrate confidence thresholds and ambiguity flags.

## Separation From Team Recommendation Reasoning

The normalized schema should not store best teams, opening plans, synergy scores, or matchup advice. It should expose grounded facts and annotations that later team-building helpers can combine into candidate teams, coverage matrices, chakra curve notes, substitutions, and uncertainty statements. Any recommendation artifact should cite these records rather than mutate them.

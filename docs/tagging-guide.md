# Tagging Guide

## Purpose

This project's first taxonomy layer exists to make the accepted normalized character and mission bundles usable for later reference build and team-planning work without hardcoding ready-made teams.

The tagging layer does three things:

- defines explicit registries for normalized skill classes, effect types, condition types, mission requirement types, and ambiguity codes;
- assigns project-owned record-level tags to characters and missions from accepted normalized data;
- preserves uncertainty as tags instead of hiding it behind guessed mechanics.

## Generated Artifacts

- `references/effect-taxonomy.json`
  Machine-readable registry with explicit definitions, observed counts, sample ids, and tag hooks for the currently observed normalized effect space.

- `references/tags.json`
  Machine-readable tag catalog plus per-record tag assignments for characters and missions.

- `references/synergy-patterns.md`
  Downstream planning guidance that uses the generated tags as comparison language rather than as fixed team outputs.

## Regeneration

Run:

```powershell
python scripts\infer_tags.py
```

The script reads only the accepted normalized bundles under `data/normalized/` and rewrites:

- `references/effect-taxonomy.json`
- `references/tags.json`

The script will fail if it observes a skill class, effect type, condition type, mission requirement type, or supported ambiguity code that is not registered in the script definitions. That failure is intentional: new normalized shapes should force an explicit taxonomy update instead of silently falling through.

## Character Tags

Character tags are aggregated from structured skill effects and their conditions.

- Capability tags describe observed mechanics such as damage, stun, heal, protect, gain, drain, conditional setup, and removal buckets.
- Target-shape tags such as `character.capability.damage_single_target`, `character.capability.damage_aoe`, `character.capability.self_protection`, and `character.capability.ally_protection` are assigned only when targeting is explicit in structured data.
- Data-quality tags under `character.data.*` come directly from effect ambiguity codes or the explicit `unknown` effect bucket.

These tags are intentionally conservative. If a skill effect keeps `target_type=unknown`, the broad capability tag is still allowed, but the narrower target-shape tag is not.

## Mission Tags

Mission tags are aggregated from normalized mission requirements and requirement ambiguity flags.

- Objective tags mirror normalized requirement types such as `win_with_character`, `streak`, `use_skill`, and explicit `unknown`.
- Support tags such as `mission.objective.named_character_refs`, `mission.objective.named_skill_refs`, and `mission.objective.counted_progress` expose planning-relevant structure that downstream tools can filter on.
- Data-quality tags under `mission.data.*` preserve source-backed gaps such as missing objective text, redirect-backed unknown objectives, and unresolved grouped conditions.

If a mission objective stays unknown in normalized data, the tag layer must keep that uncertainty visible. It must not invent a more specific mission type.

## Downstream Use

Use tags to narrow search space and explain reasoning, not to replace the underlying record evidence.

- Reference-build work can index records by tag families without re-parsing free text.
- Team-building helpers can combine record-level tags with exact skill evidence to find candidate synergies and safer substitutes.
- Mission planning can filter for named-character, named-skill, streak, and unknown-objective missions without re-inspecting every requirement blob.

## Extension Rules

- Prefer adding a new explicit registry entry over widening an old definition until it becomes vague.
- Keep capability tags grounded in structured normalized fields. If a future tag depends on raw-text heuristics, document that heuristic explicitly.
- Preserve ambiguity as first-class output. If the parser does not know, the taxonomy should say that it does not know.

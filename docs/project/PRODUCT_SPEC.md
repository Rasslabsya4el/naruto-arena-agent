# PRODUCT_SPEC

Use this file for product behavior contracts that are more specific than `PRODUCT_BRIEF.md`.

## Contract Surface

- User-visible behavior: recommend and explain Naruto Arena teams, mission coverage, substitutions, weaknesses, and mechanics from the validated skill-local reference bundle.
- Inputs: natural-language user goals, character names, missions, mission pools, existing teams, or mechanic/comparison questions.
- Outputs: candidate teams or grouped plans, recommendation rationale, win condition, synergy, chakra curve notes, first-turn priorities, matchup notes, failure modes, substitutions, confidence, source provenance, and explicit data gaps.
- Error or blocked states: missing local data, low parse confidence, unsupported source/version, unresolved mission or character identity, unknown mission objectives, or insufficient references.

## Interface Rules

- All mechanics claims must come from local references sourced to `https://www.naruto-arena.site/`.
- Runtime mechanics must be read from `skills/naruto-arena-team-builder/references/`.
- Strategic recommendations may infer from local data, but must distinguish inference from confirmed mechanics.
- Mission and mission-pool recommendations are progression-scoped by default: unless the user explicitly says that higher-rank characters are already unlocked or wants forward-looking planning, the runtime must keep recommendations inside the highest requested mission-rank band.
- The skill must not use model memory as a mechanics source.
- The skill must not silently fill unknown costs, cooldowns, classes, effects, missions, or unlocks.
- The skill must not use static best-team tables as product logic.
- The skill must not claim guaranteed mission coverage when mission objectives are unknown, hidden, soft-fit only, or low-confidence.

## Required Fields

- Character and skill records: name, source URL, raw source text, normalized fields where known, confidence, and ambiguity flags.
- Skill mechanics: costs, cooldowns, classes, effects, targets, durations, conditions, and tags where observable.
- Mission records: requirements, rewards/unlocks, level requirements, referenced characters/conditions, source URL, raw text, confidence, ambiguity flags, and explicit unknown/hidden requirement markers where applicable.
- Recommendation reports: teams considered, selected team or group, goal fit, win condition, chakra curve, first-turn priorities, matchup notes, substitutions, weaknesses, provenance, and data gaps.

## MVP Request Classes

1. Build around a character.
   Required behavior: resolve the character/version, generate and reject candidate teams, recommend a trio, and include team identity, fit, game plan, first turns, good and bad matchups, failure modes, mission coverage, substitutions, and confidence/data gaps.
2. Build for a mission.
   Required behavior: resolve the mission, summarize proven requirements and unknowns, enforce the default roster ceiling implied by the mission rank unless the user explicitly overrides it, recommend a best-effort team, explain known coverage, give a play plan, list weaknesses/failure modes, provide substitutions when flexible, and state confidence/unknowns.
3. Optimize a mission pool.
   Required behavior: resolve each mission, use the highest requested mission rank as the default roster ceiling unless the user explicitly overrides it, group compatible requirements, split conflicts, show coverage explanation and conflict explanation, include an explicit coverage matrix, state play priorities, and surface uncertain or blocked requirements.
4. Diagnose or improve an existing team.
   Required behavior: resolve each member, give a verdict, identify the biggest problem, propose a minimal fix, explain why it helps, include a broader rebuild only when needed, state mission fit, and separate proven mechanics from inference.
5. Explain mechanics, roles, or character differences.
   Required behavior: restate the question, list confirmed local facts, separate strategic inference, list data gaps/unknowns, and resolve source references when provenance matters.

## Accepted Evidence Surface

- `skills/naruto-arena-team-builder/SKILL.md` defines the runtime load order, source boundary, request classes, anti-hallucination rules, and concrete response contract.
- `scripts/validate_skill_reference_bundle.py` proves the skill-local reference bundle contract without rebuilding it.
- `scripts/validate_team_helpers.py` proves helper outputs preserve transparent search and team-report surfaces without hardcoded best-team fields or authoritative scores.
- `scripts/validate_mission_pool.py` proves grouped coverage, forced splits, soft-fit-only handling, unknown-objective carry-through, blocked unresolved queries, and helper-boundary reuse.
- `.orchestrator/tasks/TASK-E2E-ANSWER-SAMPLES-01/ANSWER-SAMPLES.md` provides representative final answers for all five request classes.

## Non-Goals

- Static best-team lists as product logic.
- Mechanics from other Naruto Arena versions.
- Broad UI before data pipeline and skill behavior are proven.
- Exhaustive strategic correctness across the full roster or every matchup.
- Solving hidden or unknown mission objective text that the canonical local data does not expose.
- Treating account-specific progression or unlock state as public fact data.

## Current Known Limits

- The skill-local bundle currently reports 196 playable character records, 179 mission records, 877 bundled skills, 122 explicit unknown mission objective records, 2 excluded disabled zero-skill characters, and 1260 source refs.
- Data-quality warnings remain part of the active contract and must be surfaced when relevant.
- Representative answer samples are accepted proof of answer-surface feasibility, not an automated transcript regression harness.

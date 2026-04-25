# PRODUCT_BRIEF

## Product Goal

- What the product does: provides a data-driven Codex skill named `naruto-arena-team-builder` for Naruto Arena team building, mission planning, team diagnosis, substitutions, weakness analysis, and grounded mechanics explanations.
- Why it exists: users need concrete Naruto Arena guidance that is grounded in the current local reference bundle instead of model memory, mixed game versions, or static best-team lists.
- Useful outcome: the user receives practical teams or plans with mission coverage, win condition, chakra curve notes, first-turn priorities, substitutions, weaknesses, provenance, and explicit uncertainty.

## Target User

- Primary user: a Naruto Arena player using Codex as a personal team-building and progression assistant.
- They are trying to build around a character, complete one mission, optimize a mission pool, diagnose an existing team, or understand a mechanic or character difference.
- They care most about current-version mechanics, practical play plans, mission progress, substitutions, weaknesses, and clear data-gap handling.

## Key User Scenarios

1. Scenario: build a team around a named character.
   Success looks like: the skill resolves the character/version, compares candidate teams, recommends a coherent trio, and explains team identity, game plan, first turns, good and bad matchups, failure modes, substitutions, mission fit, and confidence gaps.
2. Scenario: build a team for one mission.
   Success looks like: the skill resolves the mission, lists known requirements and unknown objectives, recommends a best-effort team, explains why the known requirements are covered, and names remaining risks.
3. Scenario: optimize a pool of missions.
   Success looks like: the skill groups compatible mission requirements into the fewest practical teams, splits conflicts honestly, shows an explicit coverage matrix, and keeps unknown or soft-fit requirements visible.
4. Scenario: diagnose or improve an existing team.
   Success looks like: the skill evaluates synergy, chakra curve, win condition, weaknesses, substitutions, and goal fit from local references.
5. Scenario: explain mechanics, roles, or character differences.
   Success looks like: the skill separates confirmed local data from strategic inference and cites data gaps or source limitations instead of guessing.

## MVP Outcome

- The near-MVP state is supported by accepted evidence: the repository has validated normalized data, a validated skill-local reference bundle, a skill entrypoint with concrete response contracts, helper/planner scripts, and representative answer samples covering all five MVP request classes.
- The MVP answer surface is proven representatively, not exhaustively. It does not claim solved meta strategy, guaranteed matchup correctness, solved hidden mission text, or complete account-specific progression planning.
- The product is not acceptable if it invents mechanics, mixes other Naruto Arena versions, omits source URLs where provenance matters, hardcodes best teams as core behavior, silently drops ambiguity, or claims coverage for unknown mission objectives.

## In Scope

- Canonical-site ingestion and raw snapshot preservation from `https://www.naruto-arena.site/`.
- Normalized characters, skills, costs, cooldowns, classes, effects, missions, level requirements, tags, confidence, ambiguity, and source references.
- Skill-local references consumed by `skills/naruto-arena-team-builder/SKILL.md` at runtime.
- Validators for schema integrity, reference-bundle integrity, helper surfaces, mission-pool planning, provenance, data-quality reporting, and representative answer samples.
- Data-driven helper/planner surfaces for character search, team candidate reports, mission coverage, substitutions, weaknesses, and grouped mission pools.

## Out Of Scope For Now

- Data from Naruto Arena mirrors or other versions.
- Static best-team hardcoding as product logic.
- Broad UI or unrelated product surfaces before the pipeline and skill behavior are proven.
- Balance/meta claims beyond documented local data and explicit strategic inference.
- Treating hidden or unknown mission objectives as solved when the local bundle does not reveal them.
- Account-specific progression or unlock-state planning unless a later authenticated workflow provides that data explicitly.

## Constraints And Boundaries

- Legal/access boundary: use only `https://www.naruto-arena.site/` unless a future task explicitly authorizes comparison sources.
- Environment boundary: authenticated or protected site flows require assisted, compliant workflows.
- Runtime boundary: skill answers must use `skills/naruto-arena-team-builder/references/` as the mechanics source, not model memory, external pages, project-root normalized data, or orchestration artifacts.
- Honesty boundary: hidden/unknown mission objectives, low-confidence parsing, target uncertainty, and heuristic effect typing must be surfaced explicitly.
- Strategy boundary: recommendations can infer from local data, but must label inference and avoid claiming exhaustive strategic correctness.

## Current Limitations

- The accepted bundle includes 122 source-backed unknown mission objective records.
- Many character records carry accepted data-quality warnings, including target uncertainty and heuristic effect typing.
- Two disabled zero-skill raw character entries are excluded from the playable bundle with audit-backed reporting.
- Fresh authenticated refresh validation for the hardened capture metadata is still blocked until authenticated environment variables are available in the worker shell.
- Representative answer samples prove the current answer surface can be expressed honestly, but they are not an automated transcript regression harness.

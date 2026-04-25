# Naruto Arena Team Builder Skill — Orchestrator Roadmap

This roadmap tracks the MVP dependency graph for the Naruto Arena Team Builder Skill. Product source of truth lives in `.orchestrator/product-source-of-truth.md`.

## MVP Outcome

- MVP is complete when canonical Naruto Arena site data can be ingested, normalized, validated, converted into local skill references, and used by `naruto-arena-team-builder` to produce grounded team recommendations for representative user prompts.
- MVP is incomplete if any core mechanics are invented, source URLs are missing, non-canonical versions are mixed in, best teams are hardcoded, or e2e validation is absent.

## Phase Summary

| Phase | Status | Meaning now |
| --- | --- | --- |
| `R0` | `completed` | Repo discovery and bootstrap baseline are complete; publish is optional. |
| `R0b` | `completed` | Root policy wording is aligned to the accepted repo state and durable boundaries. |
| `R1` | `completed` | Canonical site strategy is now proven well enough for MVP capture: authenticated Playwright plus route-level fallback. |
| `R2` | `completed` | Raw capture MVP is accepted for the current parsed data. |
| `R3` | `completed` | Character extraction and roster-coverage validation are accepted. |
| `R3b` | `completed` | Mission extraction and mission-bundle coverage validation are accepted. |
| `R4` | `completed` | Schema files and validator proof are accepted. |
| `R4b` | `completed` | Mission schema refinement is accepted with `level_requirement` modeled. |
| `R5` | `completed` | Taxonomy/tag inference is accepted as the bridge between normalized data and skill-ready references. |
| `R6` | `completed` | Skill-local references and their dedicated validator are accepted as the runtime data surface for the future skill. |
| `R7` | `completed` | Skill instructions and concrete response contract are accepted on top of the validated local reference bundle. |
| `R8` | `completed` | Team-building helpers and their contract validator are accepted. |
| `R8b` | `completed` | Mission pool optimization and its contract validator are accepted. |
| `R9b` | `completed` | Mission-runtime correction wave is accepted: progression-safe mission recommendations and visible `A or B` double-count semantics are now modeled on the local bundle. |
| `R9` | `completed` | End-to-end proof and repo-facing docs finalization are accepted for the current representative MVP surface. |
| `R10` | `completed` | User-requested publication wave is accepted: the repo now has a public README and first GitHub push. |

## Phases

### R0 - completed

*Repository discovery and doc style alignment*

- Goal: confirm project root, local/remote git state, repo tooling, AGENTS policy, and main README template style.
- Exit criteria: local repo is initialized/linked, root policy exists, canonical docs are bootstrapped from templates, and project baseline is ready for implementation tasks.
- Dependencies: none.
- Tasks:
  - `TASK-DISCOVERY-REPO-01` - completed; repo/docs/templates inspected and bootstrap inputs confirmed.
  - `TASK-REPO-BOOTSTRAP-01` - completed; local git repo, origin remote, AGENTS.md, docs, and `.gitignore` created.
  - `TASK-REPO-PUBLISH-01` - optional; commit and push initialized baseline if explicitly authorized.

### R0b - completed

*Root policy alignment*

- Goal: keep the root repo policy accurate enough that future worker tasks inherit the accepted current state instead of stale bootstrap assumptions.
- Exit criteria: root `AGENTS.md` matches the accepted repo reality, repository map, and product stage without weakening the canonical-source, security, or validation boundaries.
- Dependencies: `R0`, accepted repo-facing docs.
- Tasks:
  - `TASK-AGENTS-ALIGN-01` - completed; root `AGENTS.md` now reflects the accepted repo state and durable boundaries without stale bootstrap-only wording.

### R1 - completed

*Canonical site reconnaissance*

- Goal: inspect `https://www.naruto-arena.site/` only and identify page/URL/API/static behavior for ingestion.
- Exit criteria: accepted recon defines which facts are publicly renderable, which fields are session-dependent, and which acquisition steps are safe for MVP data.
- Dependencies: canonical source decision.
- Tasks:
  - `TASK-DISCOVERY-SITE-01` - superseded after the original thread was lost.
  - `TASK-DISCOVERY-SITE-PARSE-03` - completed; accepted parse recon from canonical public HTML/Next artifacts.
  - Local authenticated Playwright capture has already proven a viable mainline acquisition path for characters, missions, ladders, manual pages, and public profile data.

### R2 - completed

*Raw ingestion MVP*

- Goal: implement reproducible raw snapshot capture from canonical site.
- Exit criteria: raw snapshots are local, timestamped/versioned enough for reproducible normalization, and preserve source URLs.
- Dependencies: `TASK-DISCOVERY-SITE-01`, repo tooling decision.
- Tasks:
  - `TASK-INGEST-RAW-01` - completed; capture runner now has a safe operator contract, output-path guard, and capture metadata contract for runtime snapshots.

### R3 - completed

*Character extraction MVP*

- Goal: extract character and skill data from raw snapshots.
- Exit criteria: characters/skills include names, costs, cooldowns, classes/effects where observable, source URLs, raw text, and parse confidence.
- Dependencies: `R2`, `TASK-SCHEMA-PLAN-01`.
- Tasks:
  - `TASK-EXTRACT-CHARACTERS-01` - completed; accepted playable bundle now exists with 196 included records and explicit exclusion of two disabled zero-skill raw entries.
  - `TASK-EXTRACT-CHARACTERS-VALIDATE-01` - completed; reusable validation now proves no silent drops, explicit exclusions, and source/provenance readiness.

### R3b - completed

*Mission extraction MVP*

- Goal: extract mission requirements, rewards/unlocks, and referenced characters/conditions.
- Exit criteria: missions are represented with requirements, rewards, source URLs, raw text, and ambiguity flags.
- Dependencies: `R2`, `R4b`.
- Tasks:
  - `TASK-EXTRACT-MISSIONS-01` - completed; accepted normalized mission bundle now exists with 179 records, structured `level_requirement`, schema-safe ids, and explicit unknown requirements where the source hides objectives.
  - `TASK-EXTRACT-MISSIONS-VALIDATE-01` - completed; reusable validation now proves mission coverage, unknown-objective honesty, and provenance readiness.

### R4 - completed

*Normalized schema and validator planning*

- Goal: design stable JSON schemas for characters, skills, effects, tags, provenance, and validation rules.
- Exit criteria: concrete schema files and validator tests exist after site recon confirms actual data surfaces.
- Dependencies: product source of truth.
- Tasks:
  - `TASK-SCHEMA-PLAN-01` - completed; draft normalized schema and validator plan written to `.orchestrator/schema-proposal.md`.
  - `TASK-SCHEMA-FILES-01` - completed; concrete schema files separate public facts from session-aware user state.
  - `TASK-SCHEMA-VALIDATE-02` - completed; cross-file refs and representative payload fixtures are now proven against the captured snapshot.

### R4b - completed

*Mission schema and validator*

- Goal: extend schema/validators to missions and mission-pool optimization inputs.
- Exit criteria: mission records support coverage matrix, grouped planning, unlock/reward reasoning, uncertainty, and confirmed public level requirements.
- Dependencies: `TASK-SCHEMA-PLAN-01`, `TASK-DISCOVERY-SITE-01`.
- Tasks:
  - `TASK-SCHEMA-MISSIONS-01` - completed; mission schema and fixture now support the public `level_requirement` field.

### R5 - completed

*Taxonomy and tag inference*

- Goal: define machine-readable tags/effects for team-building reasoning.
- Exit criteria: tags have definitions, examples, inference rules, confidence handling, and validation checks.
- Dependencies: `R3`, `R3b`, `R4`.
- Tasks:
  - `TASK-TAXONOMY-01` - completed; accepted reproducible taxonomy/tagging layer now exists under `references/` plus `docs/tagging-guide.md`.

### R6 - completed

*Build skill references*

- Goal: convert validated data into local references consumable by the Codex skill.
- Exit criteria: a rebuildable skill-local bundle exists with rules, characters, missions, tags, effect taxonomy, source map, and data-quality reporting, all sourced from accepted normalized data and taxonomy artifacts.
- Dependencies: `R3`, `R3b`, `R5`.
- Tasks:
  - `TASK-REFERENCES-BUILD-01` - completed; accepted skill-local reference bundle now exists under `skills/naruto-arena-team-builder/references/` with rules, source map, and data-quality reporting.
  - `TASK-REFERENCES-VALIDATE-01` - completed; dedicated validator now proves bundle completeness, provenance carry-through, unknown-objective honesty, exclusion reporting, and tag/data-quality linkage.

### R7 - completed

*Skill implementation*

- Goal: create `naruto-arena-team-builder` skill instructions and usage surface.
- Exit criteria: the skill package entrypoint exists, loads the validated local reference bundle instead of project-root sources, uses local references only, enforces anti-hallucination rules, and answers representative prompts in grounded format.
- Dependencies: `R6`.
- Tasks:
  - `TASK-SKILL-BASE-01` - completed; accepted base skill entrypoint now exists and locks runtime behavior to the validated local reference bundle.
  - `TASK-SKILL-PROMPTS-01` - completed; accepted concrete response contract now exists for character, mission, mission-pool, diagnosis, and mechanics requests.

### R8 - completed

*Team-building helper scripts*

- Goal: support candidate generation, synergy/counter notes, chakra curve assessment, and substitutions from normalized data.
- Exit criteria: helpers produce auditable candidate sets without hardcoded best teams.
- Dependencies: `R6`, `R7`.
- Tasks:
  - `TASK-TEAM-HELPERS-01` - completed; accepted deterministic helper scripts now exist for transparent character search and team-candidate reporting on top of the validated skill-local bundle.
  - `TASK-TEAM-HELPERS-VALIDATE-01` - completed; dedicated validation now freezes helper runtime boundaries, transparent output surfaces, and conservative no-best-team behavior.

### R8b - completed

*Mission pool optimization behavior*

- Goal: recommend minimal practical teams for mission pools with coverage matrix and tradeoffs.
- Exit criteria: representative mission-pool prompts produce grounded grouped plans and explicit uncertainty.
- Dependencies: `R3b`, `R8`.
- Tasks:
  - `TASK-MISSION-POOL-01` - completed; accepted deterministic mission-pool planning now exists with grouped buckets, split rationale, soft-fit handling, blocked unresolved queries, and explicit unknown-objective carry-through.
  - `TASK-MISSION-POOL-VALIDATE-01` - completed; dedicated validation now freezes grouped coverage, forced splits, soft-fit-only handling, blocked-query behavior, helper-boundary reuse, and no-opaque-ranking guarantees.

### R9b - completed

*Mission runtime semantics correction*

- Goal: close the remaining mission-runtime gaps for visible mission semantics and progression-safe recommendation constraints.
- Exit criteria: alternative-character mission requirements are machine-readable enough for stacked progress, mission-team requests respect conservative roster ceilings derived from mission rank unless the user explicitly opts out, and representative cases are proven without weakening hidden/unknown-objective honesty.
- Dependencies: `R3b`, `R6`, `R8b`.
- Tasks:
  - `TASK-MISSION-RANK-CEILING-01` - completed; mission-team and mission-pool recommendations now respect the highest requested mission rank band by default and expose an explicit higher-rank override path.
  - `TASK-MISSION-OR-DOUBLECOUNT-01` - completed; visible exact `A or B` mission requirements such as `The Lone Swordsman` now carry structured alternative-character semantics, and planner audit surfaces prove double progress when both eligible named characters are present.

### R9 - completed

*End-to-end validation*

- Goal: prove the whole pipeline and skill behavior honestly.
- Exit criteria: clean pipeline runs, validators pass or blockers are documented, skill answers representative prompts, and MVP status is honest.
- Dependencies: `R2` through `R8b`.
- Tasks:
  - `TASK-E2E-MVP-01` - completed; first representative prompt proof shows every MVP request class is supportable from the frozen local bundle and validated helper/planner layers, but final prose section discipline still lacks transcript-style evidence.
  - `TASK-E2E-ANSWER-SAMPLES-01` - completed; accepted representative answer samples now prove required sections, explicit grouped mission coverage, provenance discipline, and confirmed-vs-inference separation across all five MVP request classes.
  - `TASK-DOCS-FINALIZE-01` - completed; repo-facing docs now reflect the accepted answer-surface proof, runtime grounding boundaries, and current limitations without overclaiming.

### R10 - completed

*Publication polish and push*

- Goal: turn the current accepted technical repo state into a public-facing repository handoff with a stronger README and a pushed upstream history.
- Exit criteria: `README.md` is publication-quality, accurately reflects the current repo and skill usage, receives a deliberate humanization pass, and the repository is committed and pushed to `origin` or blocked with exact git evidence.
- Dependencies: accepted `R6` through `R9b`.
- Tasks:
  - `TASK-README-PUBLISH-01` - completed; repo-wide technical README rewrite, prose-humanization pass, and first upstream push were all accepted.

## Current Boundaries

- Account-specific progression and unlock state remain outside the accepted public-fact bundle unless a separate authorized workflow is opened.
- Any use of non-canonical Naruto Arena sources requires explicit user approval.

## Current Dispatch Batch

- `TASK-REPO-SYNC-PUSH-01` - ready; stage the full current local repo state, create one sync commit on `master`, and push it to `origin` so GitHub matches the accepted local README/docs cleanup state.









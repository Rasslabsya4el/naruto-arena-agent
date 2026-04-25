# Naruto Arena Team Builder

`naruto-arena-team-builder` is a Codex skill for Naruto Arena team building, mission planning, mission-pool grouping, team diagnosis, substitutions, weakness analysis, and mechanics explanations.

The project is built around one rule: Naruto Arena mechanics must come from the local reference bundle generated from `https://www.naruto-arena.site/`. The skill must not answer from model memory, other Naruto Arena domains, mirrors, or static best-team lists.

## Current State

This repository has a usable local MVP surface:

- A validated skill-local reference bundle with 196 playable character records, 179 mission records, 877 bundled skills, and 1260 source references.
- 122 mission records with explicit unknown objectives. These stay unknown in answers instead of being guessed.
- 2 disabled zero-skill raw character entries excluded from the playable bundle with audit-backed reporting.
- A Codex skill entrypoint with runtime rules, source boundaries, request classes, and answer contracts.
- Helper scripts for character search, transparent team reports, and mission-pool planning.
- Validators for the skill reference bundle, helper surface, and mission-pool planner.
- Representative answer samples for all five MVP request classes.

The accepted proof is representative, not exhaustive. The repo proves that the current bundle and helper layer can support grounded answers for the declared request classes. It does not claim a solved metagame, guaranteed matchup correctness, solved hidden mission text, or complete account-specific progression planning.

## What The Skill Can Answer

The skill is meant for five request classes:

1. Build a practical team around a character.
2. Build a team for a specific mission.
3. Optimize a pool of missions into the fewest practical team groups.
4. Diagnose or improve an existing team.
5. Explain mechanics, roles, or character differences.

Good answers should include practical play pattern, mission fit when relevant, weaknesses, substitutions, confirmed mechanics, strategic inference, source provenance, and data gaps.

Mission and mission-pool requests are progression-scoped by default. Unless the user says higher-rank characters are already unlocked or asks for future planning, recommendations stay inside the highest mission-rank band implied by the requested mission set.

## How It Works

The repo keeps data, rules, helper logic, and orchestration state separate.

1. `data/normalized/` stores accepted normalized project data.
2. `references/` stores project-owned taxonomy and tag artifacts.
3. `skills/naruto-arena-team-builder/references/` stores the validated runtime bundle used by the Codex skill.
4. `skills/naruto-arena-team-builder/SKILL.md` defines the runtime load order, source boundary, reasoning flow, and required answer surfaces.
5. `scripts/` contains capture, normalization, reference-build, helper, planner, and validator scripts.

At runtime, the skill must read mechanics from `skills/naruto-arena-team-builder/references/` only. Project-root `data/normalized/` and `references/` are build inputs, not runtime answer sources.

The required runtime bundle files are:

- `skills/naruto-arena-team-builder/references/rules.md`
- `skills/naruto-arena-team-builder/references/characters.json`
- `skills/naruto-arena-team-builder/references/missions.json`
- `skills/naruto-arena-team-builder/references/tags.json`
- `skills/naruto-arena-team-builder/references/effect-taxonomy.json`
- `skills/naruto-arena-team-builder/references/source-map.json`
- `skills/naruto-arena-team-builder/references/data-quality-report.md`

## Skill Installation And Use

This repository contains the skill source package at:

```text
skills/naruto-arena-team-builder/
```

Codex discovers installed skills from the local Codex skills directory. On this Windows machine, the installed location is:

```text
C:\Users\user\.codex\skills\naruto-arena-team-builder\
```

The repo does not currently include an installer. To use this skill from a fresh clone, copy or link the repo package into your Codex skills directory, then start a new Codex thread so skill discovery can reload.

Example Windows copy command:

```powershell
Copy-Item -Recurse -Force .\skills\naruto-arena-team-builder C:\Users\user\.codex\skills\naruto-arena-team-builder
```

Editing the repo copy does not automatically update the installed Codex copy unless that installed directory is a link back to the repo. Keep that distinction in mind when testing skill instruction changes.

Once installed, ask Codex Naruto Arena questions directly. The skill should be selected for prompts such as:

```text
Build a practical team around Uzumaki Naruto.
Build a team for A Dishonored Shinobi.
Optimize teams for Survival, A Girl Grown Up, and Medical Training.
Diagnose Uzumaki Naruto / Uchiha Sasuke (S) / Haruno Sakura.
What is the practical difference between Uzumaki Naruto and Uzumaki Naruto (S)?
```

## Helper Commands

Run commands from the repository root.

Character search:

```powershell
python scripts\search_characters.py "Uzumaki Naruto" --limit 8
python scripts\search_characters.py --role-hint control --exclude-chakra-type nin --limit 5
```

Transparent team report:

```powershell
python scripts\team_candidate_report.py "Uzumaki Naruto" "Uchiha Sasuke" "Haruno Sakura"
```

Mission-pool planner:

```powershell
python scripts\optimize_mission_pool.py "Survival" "A Girl Grown Up" "Medical Training"
```

Use `--include-higher-rank` only when the user explicitly wants higher-rank or future-planning suggestions. The default mission behavior is conservative about progression.

Help surfaces:

```powershell
python scripts\search_characters.py --help
python scripts\team_candidate_report.py --help
python scripts\optimize_mission_pool.py --help
```

The helper outputs are intentionally transparent JSON. They expose role hints, chakra pressure, weaknesses, substitutions, mission coverage, data-quality warnings, and provenance hooks. They do not produce authoritative scores or static best-team answers.

## Validation

Use these checks before accepting changes to the current runtime surface:

```powershell
python scripts\validate_skill_reference_bundle.py
python scripts\validate_team_helpers.py
python scripts\validate_mission_pool.py
```

What these validators prove:

- `validate_skill_reference_bundle.py` checks required bundle files, record counts, provenance linkage, unknown-objective reporting, disabled-character exclusion reporting, and data-quality linkage.
- `validate_team_helpers.py` checks that helper scripts read the skill-local bundle and preserve transparent search and team-report fields without opaque ranking or best-team fields.
- `validate_mission_pool.py` checks grouped mission coverage, forced splits, soft-fit-only handling, unknown-objective carry-through, blocked unresolved queries, helper-boundary reuse, and no-opaque-ranking behavior.

Representative final answer samples live at:

```text
.orchestrator/tasks/TASK-E2E-ANSWER-SAMPLES-01/ANSWER-SAMPLES.md
```

Those samples show the intended answer surface. They are not an automated transcript regression harness.

## Repository Map

- `AGENTS.md` - repository policy for future Codex workers.
- `README.md` - public entrypoint for the repo.
- `docs/project/` - product brief, product spec, current state, and durable decisions.
- `docs/roadmap.md` - phase graph and remaining task inventory.
- `docs/task-queue.md` - live task queue.
- `docs/validation-log.md` - accepted validation history.
- `docs/tagging-guide.md` - taxonomy and tag-generation notes.
- `.orchestrator/` - orchestration handoffs, task results, and product control-plane artifacts.
- `data/normalized/` - accepted normalized project data used to build references.
- `references/` - project-owned taxonomy and reference-building artifacts.
- `schemas/` - JSON schema contracts for public facts and session-aware user state.
- `scripts/` - capture, normalization, reference-build, helper, planner, and validator scripts.
- `skills/naruto-arena-team-builder/` - Codex skill package and skill-local runtime bundle.
- `skills/naruto-arena-team-builder/references/` - runtime mechanics, provenance, taxonomy, and data-quality references used by the skill.

Runtime outputs, raw generated snapshots, logs, caches, browser sessions, local credentials, and test output are not project memory and should not be committed.

## Source And Data Boundaries

The canonical game source is only:

```text
https://www.naruto-arena.site/
```

Do not use other Naruto Arena domains, mirrors, model memory, or third-party mechanics pages as gameplay evidence unless a future task explicitly authorizes comparison.

The project should surface uncertainty instead of hiding it:

- Unknown mission objectives stay explicit.
- Low-confidence or heuristic effect parsing stays visible through data-quality tags.
- Broad effect buckets such as `protect`, `apply_state`, `remove_state`, `gain`, and `drain` should not be narrowed without exact supporting text.
- Strategic recommendations must be labeled as inference when they go beyond confirmed bundle facts.
- Account-specific progression and unlock state are separate from public fact data and need a later authenticated workflow if the product expands in that direction.

## Maintenance Notes

The current raw capture runner is contract-hardened, but a fresh authenticated refresh validation is still deferred until the needed authenticated environment variables are available. That does not block using the accepted local bundle, but it matters for future data refresh work.

Useful maintenance commands:

```powershell
python scripts\capture_site.py --help
python scripts\capture_site.py --print-contract
python scripts\infer_tags.py
python scripts\build_skill_references.py
python scripts\validate_schemas.py
python scripts\validate_character_bundle.py
python scripts\validate_mission_bundle.py
```

Run live capture only into ignored runtime snapshot space such as `snapshots/raw/`. Do not write live capture output into tracked source directories.

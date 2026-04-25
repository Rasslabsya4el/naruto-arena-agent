# AGENTS.md

## Mission

This repository builds the `naruto-arena-team-builder` Codex skill: a data-driven assistant for Naruto Arena team building, mission planning, substitutions, weaknesses, and grounded mechanic explanations.

Canonical game source is `https://www.naruto-arena.site/`. Do not use other Naruto Arena domains, mirrors, model memory, or third-party pages for game mechanics unless a future task explicitly authorizes comparison.

## Instruction Architecture

- Treat this root file as the default policy for the whole repository.
- Keep durable product memory in `docs/project/` and task orchestration state in `.orchestrator/`.
- Put implementation-specific scoped `AGENTS.md` files only when a subtree needs different rules.
- Do not duplicate long playbooks here; link docs instead.

## Project Memory And Control Plane

- Product docs: `docs/project/PRODUCT_BRIEF.md`, `docs/project/PRODUCT_SPEC.md`, and `docs/project/CURRENT_STATE.md`.
- Orchestrator product source: `.orchestrator/product-source-of-truth.md` while orchestration continues.
- Durable decisions: `docs/project/DECISION_LOG.md` and `.orchestrator/decisions.md` while orchestration continues.
- Roadmap: `docs/roadmap.md`.
- Live task queue: `docs/task-queue.md`.
- Validation history: `docs/validation-log.md`.
- Runtime outputs, caches, logs, raw generated snapshots, and test output are not project memory.

## Repository Map

- `docs/project/` — product brief, current state, decisions, and product/spec contracts.
- `docs/` — roadmap, task queue, and validation log.
- `.orchestrator/` — task handoff and orchestration artifacts.
- `skills/naruto-arena-team-builder/` — Codex skill entrypoint and skill-local runtime bundle.
- `skills/naruto-arena-team-builder/references/` — validated mechanics, provenance, taxonomy, and data-quality references used by the skill at runtime.
- `data/normalized/` — accepted normalized project data used to build skill references.
- `references/` — project-owned taxonomy and reference-building artifacts.
- `schemas/` — JSON schema contracts for public facts and session-aware user state.
- `scripts/` — capture, normalization, reference-build, helper, planner, and validator scripts.
- `snapshots/raw/` — ignored runtime capture space, not durable project memory.

## Product Reality

- The repository now has accepted normalized data, schema files, a skill-local reference bundle, a base skill entrypoint, helper/planner scripts, validators, and representative answer-surface samples.
- The skill-local runtime bundle currently reports 196 playable character records, 179 mission records, 877 bundled skills, 1260 source references, 122 explicit unknown mission objective records, and 2 excluded disabled zero-skill raw characters.
- The current accepted answer surface covers building around a character, building for a mission, optimizing a mission pool, diagnosing or improving an existing team, and explaining mechanics or character differences.
- The accepted proof is representative, not exhaustive strategic correctness across every roster, mission, matchup, or account state.
- Fresh authenticated refresh validation for hardened capture metadata remains blocked until authenticated environment variables are available.
- The skill must not hardcode best teams as the product core.
- Every mechanics claim must be grounded in local references with source URLs.
- Missing or low-confidence data must be surfaced explicitly instead of guessed.

## Discovery Policy

- Start from files, folders, commands, or task specs named by the task.
- Explore local neighbors before broad scans.
- Do not inspect runtime/output directories, logs, caches, generated snapshots, bulky fixtures, or browser session data unless the task explicitly requires them.
- Do not read tests during initial discovery unless the task is about tests, validation, regression, or a nearby change needs a targeted check.

## Editing Rules

- Prefer minimal, stage-correct diffs.
- Preserve unrelated user changes.
- Keep data, schemas, validators, skill instructions, and reasoning helpers separated.
- Do not create implementation/runtime code during discovery or documentation tasks.
- Do not add static best-team lists as source logic.
- Do not commit generated artifacts, secrets, `.env` files, local sessions, caches, or runtime data.

## Validation Policy

- Run the smallest targeted validation that proves the task contract.
- Prefer repo-native wrappers once tooling exists.
- For Python files, run targeted tests when relevant and `python -m py_compile` for changed Python modules.
- Do not run expensive scraping, integration, browser, or output-generating flows unless the task requires them.
- If validation is not run, state that explicitly in the result.

## Git And Repo Hygiene

- Check branch and worktree state before edits.
- Do not commit or push unless a task explicitly authorizes it.
- Keep `origin` pointed at `https://github.com/Rasslabsya4el/naruto-arena-agent.git` unless a durable decision changes it.
- Git-tracked source and docs are source of truth; runtime artifacts are not.

## Security And Boundaries

- Respect legal, authentication, captcha, privacy, and environment boundaries.
- Do not fabricate credentials, source responses, game mechanics, or validation proof.
- If site access requires login/manual action, design an assisted workflow and record the blocker instead of bypassing it.

## Output Contract

After each task, report changed paths, what changed, validation run, residual risks, and follow-up. If blocked, name the blocker and the smallest missing artifact or decision.

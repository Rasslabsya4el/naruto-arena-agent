# CURRENT_STATE

## Snapshot Date

- Date: 2026-04-25

## Confirmed Tracked Reality

- The local workspace has been initialized as a Git repository and linked to `https://github.com/Rasslabsya4el/naruto-arena-agent.git`.
- The first upstream publication is now complete; `origin/master` points to `06458e055c6493e8e78baa3cd1f3f34406385be8`, which includes the public README rewrite and the accepted repository history.
- Root policy and canonical project docs now exist.
- Discarded browser/auth-refresh experimental reports, stale browser-task families, and their repo-facing doc references have now been removed from the tracked local repo state.
- Accepted canonical-site parse recon exists in `.orchestrator/site-parse-recon-report.md`.
- Canonical raw capture now exists at the ignored runtime path `snapshots/raw/site_capture/latest/` with a manifest covering 198 characters, 9 mission groups, 179 mission details, both public ladders, manual pages, and one public profile snapshot.
- The current working acquisition path is an authenticated Playwright session that reads canonical Next data when available and falls back to rendered page `__NEXT_DATA__` when the canonical Next JSON route is broken or empty.
- Schema validation proof now exists against snapshot-derived fixtures: cross-file `$ref` resolution works and the current schema set validates representative public-fact and user-state payloads.
- Mission schema refinement is now accepted; the public mission field is modeled as `level_requirement` in the schema layer and fixture set.
- An accepted normalized character bundle now exists with 196 included records; two temporarily disabled zero-skill raw entries were excluded instead of being turned into invented playable records.
- An accepted normalized mission bundle now exists with 179 records; it emits structured `level_requirement`, uses schema-safe deterministic ids, and preserves hidden or unknown mission objectives as explicit source-backed unknown requirements.
- Character bundle validation is now accepted; the reusable validator confirms 196 included playable records, exactly two intentional zero-skill exclusions, and no silent drops.
- Raw-ingestion hardening is now accepted; `scripts/capture_site.py` exposes a safe operator contract via `--help` and `--print-contract`, rejects tracked output paths outside `snapshots/raw`, and writes capture metadata when the capture runner is executed.
- Mission bundle validation is now accepted; the reusable validator confirms all 179 normalized mission records are source-backed, `level_requirement` is complete, and the 122 unknown-objective records are supported by raw detail payload states rather than silent loss.
- Accepted taxonomy and tagging artifacts now exist under `references/` plus `docs/tagging-guide.md`, and `scripts/infer_tags.py` regenerates them reproducibly from the accepted normalized bundles.
- An accepted skill-local reference bundle now exists under `skills/naruto-arena-team-builder/references/`, with `rules.md`, bundle-wrapped `characters.json` and `missions.json`, local copies of `tags.json` and `effect-taxonomy.json`, plus `source-map.json` and `data-quality-report.md`.
- Reference-contract validation is now accepted; `scripts/validate_skill_reference_bundle.py` proves the skill-local bundle keeps required artifacts, provenance linkage, record counts, unknown-objective reporting, disabled-character exclusion reporting, and tag/data-quality linkage intact without rebuilding the bundle.
- An accepted base skill entrypoint now exists at `skills/naruto-arena-team-builder/SKILL.md`; it loads `references/rules.md` first, constrains runtime mechanics to the validated skill-local bundle, routes provenance through `source-map.json`, and forbids model-memory or project-root runtime sourcing.
- The accepted skill entrypoint now also includes the concrete MVP answer contract for character builds, mission answers, mission-pool planning, diagnosis, and mechanics explanations, including required practical sections and explicit separation of confirmed data, inference, and gaps.
- Accepted helper scripts now exist at `scripts/search_characters.py` and `scripts/team_candidate_report.py`; they read only the validated skill-local bundle at runtime and surface transparent character-candidate and team-candidate facts, including chakra pressure, weakness notes, data-quality warnings, substitution hooks, and provenance hooks.
- Helper-contract validation is now accepted; `scripts/validate_team_helpers.py` proves the helper runtime stays on the skill-local bundle, preserves transparent search/team-report surfaces, and avoids authoritative-score or hardcoded best-team behavior in representative outputs.
- Accepted mission-pool planning now exists at `scripts/optimize_mission_pool.py`; it resolves mission queries against the validated skill-local bundle, groups compatible exact requirements into practical buckets, splits incompatible pools honestly, preserves soft-fit-only and unknown-objective states, and returns blocked payloads instead of guessing unresolved missions.
- Mission-pool contract validation is now accepted; `scripts/validate_mission_pool.py` proves grouped compatibility, forced split logic, soft-fit-only handling, blocked unresolved queries, helper-boundary reuse, and no-opaque-ranking behavior on representative planner runs.
- Mission and mission-pool recommendations are now progression-safe by default; the accepted runtime derives a conservative roster ceiling from mission rank, keeps low-rank requests out of later-rank unlock bands, and exposes an explicit higher-rank override path when the user asks for it.
- Visible exact alternative-character mission requirements are now structurally modeled in the accepted local surface; cases like `The Lone Swordsman` and `The Drunken Master` now preserve eligible-character alternatives explicitly and expose double-count progress semantics when both eligible named characters are present together.
- A first representative e2e proof wave is now reviewed; it shows every declared MVP request class can be grounded from the accepted local bundle and validated helper/planner surfaces, but it does not yet freeze real final answer transcripts or section-compliance evidence.
- Accepted representative answer samples now exist for all five MVP request classes; the current artifact proves required sections, explicit grouped mission coverage, provenance discipline, and confirmed-vs-inference separation survive into user-facing prose.
- Accepted repo-facing docs now exist; `README.md`, `docs/project/PRODUCT_BRIEF.md`, and `docs/project/PRODUCT_SPEC.md` now describe the proven request classes, runtime grounding model, current limits, and representative answer-surface evidence without overclaiming strategy certainty.
- Accepted root policy alignment now exists; `AGENTS.md` now describes the current repo map and accepted project reality instead of stale bootstrap/discovery-only state while preserving canonical-source, security, validation, and anti-hallucination boundaries.
- Public home-page data is confirmed from `__NEXT_DATA__`, and build artifacts confirm route families for characters, missions, ladders, profiles, and clans.
- Concrete schema files now exist under `schemas/` for common structures, characters, missions, ladder entries, public profiles, public clans, and user progress.
- The repo now has a raw capture runner, accepted normalizers, bundle validators, accepted taxonomy artifacts, an accepted skill-local reference bundle, a dedicated reference validator, an accepted skill entrypoint with prompt/output contract, a deterministic helper layer, a dedicated helper validator, a deterministic mission-pool planner, a dedicated mission-pool validator, a first e2e proof wave, and accepted answer-surface samples.
- `.orchestrator/` contains bootstrap/product planning artifacts and bounded task handoff files.

## Current Mainline Focus

- Current active phase: no mandatory MVP phase is open; the accepted local bundle and the first public GitHub publication are both in place.
- Current honest next step: no mandatory follow-up is tracked for the current MVP line; future product-scope work should be opened explicitly when needed.
- Why that step is next: the current local bundle, mission-runtime corrections, repo-facing docs, and first upstream publication are already accepted, so there is no remaining mandatory pre-publication work on the current MVP line.

## Active Bottlenecks

- Account-specific progression and unlock state likely require a separate authenticated workflow and should not be mixed into public-fact records.
- The accepted mission bundle still contains 122 source-backed unknown requirement placeholders because the current snapshot does not reveal objective text for many mission detail routes.
- The accepted character bundle excludes two temporarily disabled raw entries, but the exclusion is now audit-backed rather than an unresolved coverage question.
- The accepted taxonomy is intentionally conservative in some effect buckets, so downstream consumers must not over-interpret broad normalized categories as narrower proven mechanics.
- Some canonical routes still require rendered-page fallback because direct canonical Next JSON responses are inconsistent for part of the mission surface.
## Runtime Or Environment Facts That Matter

- Remote repository: `https://github.com/Rasslabsya4el/naruto-arena-agent.git`.
- Current published head: `origin/master` at `06458e055c6493e8e78baa3cd1f3f34406385be8`.
- Canonical game source: `https://www.naruto-arena.site/` only.
- Normalized project data is expected to live under `data/normalized/`, and skill-ready copies can be built later from there.
- Project-owned taxonomy artifacts now live under top-level `references/`, and the next build step can create skill-local copies under `skills/naruto-arena-team-builder/references/`.
- The accepted skill-local bundle currently summarizes 196 playable character records, 179 mission records, 1260 deduplicated source refs, 122 unknown mission objective records, and 2 explicitly excluded disabled zero-skill raw characters.
- The accepted reference validator currently proves those bundle invariants without rebuilding artifacts, which means future skill tasks can depend on a frozen skill-local contract instead of ad hoc artifact inspection.
- The accepted skill entrypoint already covers load order, allowed data sources, request classes, candidate/rejection logic, uncertainty handling, and concrete answer sections, so helper tasks should extend that surface instead of rewriting it.
- The accepted helper layer currently supports name/id search plus tag/effect/chakra/role narrowing and a transparent team report with role shell hints, chakra pressure, strength/weakness notes, substitution hooks, data-quality warnings, and provenance hooks.
- The accepted helper validator now regression-checks that helper runtime stays on the skill-local bundle and that representative outputs keep transparency fields instead of opaque scoring or hardcoded best-team claims.
- The accepted mission-pool planner currently emits `coverage_buckets`, `coverage_matrix`, `uncertain_missions`, `split_rationale`, and full per-mission analyses, while leaving flex slots open instead of inventing filler characters when exact constraints do not require a full team.
- The accepted mission-pool validator now regression-checks grouped exact coverage, forced split cases, soft-fit-only missions, unknown-objective carry-through, blocked unresolved queries, helper-boundary reuse, and forbidden ranking fields.
- Accepted answer samples now prove that final sections such as First Turns, Good Matchups, Bad Matchups, explicit grouped mission coverage, and confirmed-vs-inference separation can be expressed honestly from the frozen bundle and helpers.
- Runtime outputs and generated snapshots are still not project memory, but the current raw snapshot is a valid local input for the next bounded worker tasks.

## What Is Not Source Of Truth

- Runtime directories, generated snapshots, logs, caches, browser sessions, local credentials, and test output.
- Model memory about Naruto Arena mechanics.
- Other Naruto Arena sites, mirrors, or third-party pages unless explicitly authorized by a future decision.

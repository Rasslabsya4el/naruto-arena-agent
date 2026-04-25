# Naruto Arena Team Builder Skill — Product Source Of Truth

## Source Prompt

- Primary project brief: `C:\Users\user\Documents\Codex\2026-04-24\new-chat-2\naruto_arena_orchestrator_prompt.md`
- This file is the orchestrator-level product source of truth distilled from that brief.
- If this file conflicts with the source prompt, reread the source prompt and update this file before dispatching implementation work.

## Canonical Game Source

- Canonical site: `https://www.naruto-arena.site/`
- Only this site is allowed as the Naruto Arena data source for this project.
- Other Naruto Arena versions, mirrors, model memory, and third-party pages are forbidden unless the user explicitly authorizes version comparison.
- If site data conflicts with memory or another source, `https://www.naruto-arena.site/` wins.

## Product Goal

- Build a data-driven Codex skill named `naruto-arena-team-builder`.
- The project ingests Naruto Arena data from the canonical site, stores raw snapshots, normalizes game data, enriches it with tags/effect objects, and builds local skill references.
- The skill recommends teams from structured local data instead of hardcoded “best teams”.
- Every claim about mechanics, costs, cooldowns, classes, effects, tags, missions, and sources must be grounded in local references that point back to source URLs.
- If data is missing or parse confidence is low, the skill must say so instead of inventing mechanics.

## Target User

- Primary user: a Naruto Arena player using Codex as a personal team-building and progression planner.
- The user wants concrete teams, mission coverage, first-turn plans, substitutions, weaknesses, and explanations tied to current local data.
- The user may ask in ordinary language, for example around a character, a mission, a mission pool, an existing team, or a mechanic.

## Core User Scenarios

- Build a team around a character, including role from data, candidate teams, recommendation, game plan, bad matchups, substitutions, and confidence/data gaps.
- Build a team for one mission, including mission requirements, recommended team, why it clears the mission, play plan, and backups.
- Optimize a pool of missions, including minimum practical teams, coverage matrix, grouping rationale, and tradeoffs.
- Improve or diagnose an existing team, including synergy, chakra curve, win condition, weaknesses, substitutions, and whether it should be used for the user’s goal.
- Answer “what should I play next?” using available missions/unlocks and current local data.
- Explain mechanics without hallucinating, separating confirmed local data from strategic inference and data gaps.
- Mission and progression requests are progression-scoped by default: unless the user explicitly says otherwise, recommendations must stay inside the highest mission-rank band implied by the asked mission set instead of assuming access to later-rank characters.

## MVP Outcome

- The MVP is done when the repo can ingest/snapshot enough canonical site data, normalize characters/skills and missions into validated JSON, build skill references, and run the skill on representative prompts with grounded team recommendations.
- MVP answers must include 2-3 candidate teams when appropriate, mission coverage when missions are provided, win condition, synergy explanation, chakra curve notes, opening plan, weaknesses, substitutions, and explicit uncertainty where data is incomplete.
- The MVP is not done if the skill relies on memorized Naruto Arena mechanics, mixes data from other versions, silently drops ambiguous skill text, lacks source URLs, hardcodes best teams, or claims success without e2e validation.

## Non-Goals

- Do not hardcode a static list of best teams as the product core.
- Do not scrape or merge other Naruto Arena mirrors or versions by default.
- Do not implement broad unrelated UI/features before the data pipeline and skill behavior are proven.
- Do not claim balance/meta correctness beyond what local data and documented reasoning support.

## Required Architecture Boundaries

- Source layer stores reproducible raw snapshots with provenance.
- Extraction layer discovers canonical pages and extracts source text/data without lossy overwrites.
- Normalization layer produces stable JSON for characters, skills, costs, cooldowns, classes, effects, missions, requirements, rewards, tags, and source references.
- Some missions may legitimately have hidden or unknown objectives in the canonical game state; normalization must preserve that as explicit unknown/hidden mission requirements instead of inventing mechanics or treating the record as inherently broken.
- Mission normalization and planning must preserve alternative eligible-character requirement sets structurally enough to support stacked per-battle progress when a visible mission requirement can be advanced by more than one named character in the same team.
- Project-owned normalized outputs live under `data/normalized/`; skill-ready copies are built later from that layer into the skill package reference directory.
- Tagging/taxonomy layer defines tags and effect objects instead of leaving unexplained labels.
- Skill layer consumes local references only and keeps data separate from reasoning.
- Validation layer checks schema integrity, source URL presence, parse confidence, tag definitions, and representative skill prompts.

## Anti-Hallucination Rules For Skill Docs

- Use local references as source of truth.
- Do not answer from memory about Naruto Arena mechanics.
- Do not mix mechanics from other Naruto Arena versions.
- If data is missing, say exactly what is missing.
- If parse confidence is low, present the recommendation as tentative.
- Prefer “based on current local data” phrasing when appropriate.
- Never invent cooldowns, costs, effects, missions, or character skills.

## Current Discovery Boundary

- No implementation should start until repo/doc style, canonical-site reconnaissance, and schema planning are complete enough for bounded implementation tasks.

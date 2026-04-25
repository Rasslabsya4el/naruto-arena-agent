# Naruto Arena Team Builder Reference Rules

## Canonical Source Lock

- Canonical game source: `https://www.naruto-arena.site/`
- Do not use other Naruto Arena domains, mirrors, or model memory as mechanics sources.
- If a claim is not supported by the local reference files in this directory, report the gap instead of guessing.

## Allowed Mechanics Sources For The Future Skill

- `characters.json`, `missions.json`, `tags.json`, `effect-taxonomy.json`, and `source-map.json` in this directory are the only mechanics sources for the future skill.
- Resolve every `source_ref_id` through `source-map.json` when the answer needs exact source URLs, snapshot lineage, or section-level provenance.
- Use `data-quality-report.md` to surface accepted bundle limitations before making narrow strategic claims.

## Honest Uncertainty Handling

- Keep all 122 missions with explicit unknown requirements as unknown. Do not invent hidden mission objectives.
- Distinguish confirmed mechanics from strategic inference in every future skill answer.
- If a record carries `data_quality_tag_ids`, surface the relevant uncertainty instead of treating it as noise.
- The playable bundle intentionally excludes 2 disabled zero-skill raw stubs: Edo Tensei Itachi (S), Shinobi Alliance Kakashi (S). Do not present them as playable characters.

## Taxonomy Guardrails

- Do not narrow broad accepted effect buckets such as `protect`, `apply_state`, `remove_state`, `gain`, or `drain` beyond the accepted taxonomy definitions unless the exact supporting source text is cited through provenance.
- `character.data.*` and `mission.data.*` tags are evidence-backed data-quality markers, not optional hints.

## Build Provenance

- Bundle version: `skill-reference-bundle-v1`
- Generated at: `2026-04-24T19:10:35Z`
- Regenerate with `python scripts\build_skill_references.py`.
- Accepted build inputs:
  - `data\normalized\characters.json` (`sha256=882c2b2f2661f4dc20e3f8abe7eb1478b866b1cdfa4d74ae5a32bb982bfc59b2`)
  - `data\normalized\missions.json` (`sha256=6f6cbd1331a299f0cff167be6d738a1c0764879c14dc9972ddb9fd9db2efd4a4`)
  - `references\tags.json` (`sha256=57b143bbe902d6df32dfbfd25c9ae3e579df625b0cf351d855223eb83e910812`)
  - `references\effect-taxonomy.json` (`sha256=bcc427736278d144895f5f4a886a2ac4c3c11f9baba9f277a035bd343e35a8e1`)
  - `.orchestrator\tasks\TASK-EXTRACT-CHARACTERS-VALIDATE-01\RESULT.txt` (`sha256=f87da2f40b9df416cc68f48149574fd7c9bf27214f5f9fa52ebafaf46479a460`)
  - `.orchestrator\tasks\TASK-EXTRACT-MISSIONS-VALIDATE-01\RESULT.txt` (`sha256=982aba9bb0a8ba99d41c99d499eb4db3d92754b4930dacf769bc1c50d408f636`)

# Data Quality Report

## Bundle Summary

- Generated at: `2026-04-24T19:10:35Z`
- Bundle version: `skill-reference-bundle-v1`
- Playable character records: 196
- Mission records: 179
- Excluded disabled zero-skill raw characters: 2
- Explicit unknown mission objective records: 122

## Character Bundle Scope

- The playable character bundle is intentionally narrower than the raw roster when the canonical source exposes disabled zero-skill stubs.
- Accepted exclusions: Edo Tensei Itachi (S), Shinobi Alliance Kakashi (S).
- Accepted raw-versus-playable counts: raw=198, playable=196.

## Mission Objective Uncertainty

- `122` mission records retain explicit `unknown` requirements because the accepted snapshot does not reveal objective text.
- Accepted raw-detail evidence breakdown:
  - redirect payloads: 71
  - error-page payloads: 50
  - unexpected-home payloads: 1

## Record-Level Data Quality Tags

- `character.data.effect_target_unknown`: 190 character records
- `character.data.effect_type_heuristic`: 145 character records
- `character.data.effect_magnitude_unknown`: 74 character records
- `character.data.effect_fallback_unknown`: 28 character records
- `mission.data.objective_text_missing`: 122 mission records
- `mission.data.detail_payload_redirect`: 71 mission records
- `mission.data.detail_payload_error_page`: 50 mission records
- `mission.data.detail_payload_unexpected_home`: 1 mission records
- `mission.data.character_group_not_modeled`: 12 mission records
- `mission.data.multi_character_condition_not_structured`: 10 mission records
- `mission.data.character_subject_not_resolved`: 3 mission records
- `mission.data.skill_reference_not_resolved`: 1 mission records

## Taxonomy Guardrails

- The accepted taxonomy is intentionally conservative. Downstream skill logic must not collapse broad parser buckets into narrower claimed mechanics.
- `protect`: This bucket is broader than invulnerability alone; inspect raw text when exact protection semantics matter.
- `apply_state`: This bucket is intentionally broad and should not be mistaken for a single canonical mechanic family.
- `remove_state`: Do not assume every remove_state entry is chakra denial; check evidence when exact removal type matters.
- `gain`: This bucket may mix direct resource gain with other beneficial gain text; keep the tag broad.
- `drain`: Some drain entries describe setup or replacement text instead of already-resolved drain output.

## Build Inputs

- `data\normalized\characters.json` (`sha256=882c2b2f2661f4dc20e3f8abe7eb1478b866b1cdfa4d74ae5a32bb982bfc59b2`)
- `data\normalized\missions.json` (`sha256=6f6cbd1331a299f0cff167be6d738a1c0764879c14dc9972ddb9fd9db2efd4a4`)
- `references\tags.json` (`sha256=57b143bbe902d6df32dfbfd25c9ae3e579df625b0cf351d855223eb83e910812`)
- `references\effect-taxonomy.json` (`sha256=bcc427736278d144895f5f4a886a2ac4c3c11f9baba9f277a035bd343e35a8e1`)
- `.orchestrator\tasks\TASK-EXTRACT-CHARACTERS-VALIDATE-01\RESULT.txt` (`sha256=f87da2f40b9df416cc68f48149574fd7c9bf27214f5f9fa52ebafaf46479a460`)
- `.orchestrator\tasks\TASK-EXTRACT-MISSIONS-VALIDATE-01\RESULT.txt` (`sha256=982aba9bb0a8ba99d41c99d499eb4db3d92754b4930dacf769bc1c50d408f636`)

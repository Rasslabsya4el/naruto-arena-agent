task_id: TASK-README-TONE-RESET-01
mode: manual_file_handoff
role_skill: $universal-subtask-worker
status: ready

goal:
- Rewrite `README.md` into a short casual first-person README in Russian that reads like the user wrote it for a personal test repo, not like formal product documentation.

why_now:
- User explicitly rejected the current README as too AI-ish, too long, and too formal.
- The repo is a personal Codex skill/test project, so the public entrypoint should match that energy instead of sounding like enterprise docs.

repo_root:
C:\Coding\Naruto arena agent

context_files:
- C:\Coding\Naruto arena agent\AGENTS.md
- C:\Coding\Naruto arena agent\README.md
- C:\Coding\Naruto arena agent\docs\project\CURRENT_STATE.md
- C:\Coding\Naruto arena agent\docs\project\DECISION_LOG.md
- C:\Coding\Naruto arena agent\skills\naruto-arena-team-builder\SKILL.md

write_scope:
- C:\Coding\Naruto arena agent\README.md
- C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-README-TONE-RESET-01\RESULT.txt

do_not_touch:
- C:\Coding\Naruto arena agent\docs
- C:\Coding\Naruto arena agent\data
- C:\Coding\Naruto arena agent\schemas
- C:\Coding\Naruto arena agent\scripts
- C:\Coding\Naruto arena agent\skills\naruto-arena-team-builder\references
- C:\Coding\Naruto arena agent\.orchestrator\roadmap.md
- C:\Coding\Naruto arena agent\.orchestrator\decisions.md
- C:\Coding\Naruto arena agent\.git

acceptance:
- `README.md` is materially shorter than the current version and no longer reads like formal product documentation.
- The README is written in simple first-person Russian and feels casual/personal instead of corporate or AI-ish.
- It explicitly says that the user played Naruto Arena a lot as a kid.
- It explains in simple words that Naruto Arena is a browser turn-based 3v3 battler where you combine different characters.
- It explains that the idea was to make a Codex skill/agent that gets the game data from the site and gives reasoned answers based on that data.
- It says the agent can build teams, explain how to use teams or individual characters, make a battle plan, and analyze an enemy comp to suggest focus target and what to play around such as counters, heals, and similar threats.
- It explicitly says this is basically a skill for Codex because the user uses Codex.
- It explicitly frames the repo as a personal test project made for the user, not as a serious product.
- The README avoids long architecture/validation/roadmap sections, avoids product-marketing tone, and avoids sounding overexplained.

validation:
- Run `rg -n "Naruto Arena|Codex|3 на 3|команд|план|фокус|противник|хил|каунтер" README.md` and confirm the rewritten README still covers the intended practical surface.
- Run `rg -n "Current State|Validation|Repository Map|Maintenance Notes|MVP|representative|validated|runtime|provenance" README.md` and confirm the old heavy formal sections/wording are gone or reduced to intentional minimal wording only.
- Run `git diff -- README.md`.

delegation_inside_task:
No. NO_VALID_SUBAGENT_SPLIT.

result_file:
C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-README-TONE-RESET-01\RESULT.txt

result_contract:
- task_id
- status: completed | partial | blocked | failed
- changed_files
- validation
- completed_acceptance
- limitations
- follow_up_needed
- follow_up

chat_response_contract:
- Write the result artifact to the exact result_file path.
- Final chat response must be exactly the absolute result_file path.
- No prose.
- No markdown.
- No summary.
- No questions to user.
- If blocked, still write result_file with status: blocked, then return only the path.

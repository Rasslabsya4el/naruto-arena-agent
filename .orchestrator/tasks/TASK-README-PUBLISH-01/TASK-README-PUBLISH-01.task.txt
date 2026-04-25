task_id: TASK-README-PUBLISH-01
mode: manual_file_handoff
role_skill: $universal-subtask-worker
status: ready

goal:
- Perform a full technical read of the current repository and turn that understanding into a GitHub-quality `README.md` that explains what the project is, how the skill works, how to install or use it, what is validated, what is still limited, and how to work with the repo safely.
- After the technical rewrite, run a dedicated prose-humanization pass using the local `$universal-humanizer` skill guidance so the README reads like deliberate human writing instead of stiff generated text.
- Publish the whole repository to the configured Git remote after the README is finalized.

why_now:
- The project now has a technically accepted local bundle, helper/planner layer, mission-runtime corrections, and publishable repository state, but the current README is still a mostly technical snapshot rather than the polished public-facing entrypoint the repo now needs.
- The user explicitly wants one end-to-end worker pass that audits the repo deeply, upgrades the README to publication quality, humanizes the final prose, and then pushes the repository upstream.

repo_root:
C:\Coding\Naruto arena agent

context_files:
- C:\Coding\Naruto arena agent\AGENTS.md
- C:\Coding\Naruto arena agent\README.md
- C:\Coding\Naruto arena agent\docs\project\PRODUCT_BRIEF.md
- C:\Coding\Naruto arena agent\docs\project\PRODUCT_SPEC.md
- C:\Coding\Naruto arena agent\docs\project\CURRENT_STATE.md
- C:\Coding\Naruto arena agent\docs\project\DECISION_LOG.md
- C:\Coding\Naruto arena agent\docs\roadmap.md
- C:\Coding\Naruto arena agent\docs\task-queue.md
- C:\Coding\Naruto arena agent\docs\validation-log.md
- C:\Coding\Naruto arena agent\docs\tagging-guide.md
- C:\Coding\Naruto arena agent\skills\naruto-arena-team-builder
- C:\Coding\Naruto arena agent\scripts
- C:\Coding\Naruto arena agent\schemas
- C:\Coding\Naruto arena agent\references
- C:\Coding\Naruto arena agent\data\normalized
- C:\Coding\Naruto arena agent\.orchestrator\product-source-of-truth.md
- C:\Coding\Naruto arena agent\.orchestrator\roadmap.md
- C:\Coding\Naruto arena agent\.orchestrator\decisions.md
- C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-E2E-ANSWER-SAMPLES-01\ANSWER-SAMPLES.md
- C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-DOCS-FINALIZE-01\RESULT.txt
- C:\Users\user\.codex\skills\universal-humanizer\SKILL.md

write_scope:
- C:\Coding\Naruto arena agent\README.md
- C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-README-PUBLISH-01\RESULT.txt

do_not_touch:
- C:\Coding\Naruto arena agent\snapshots\raw
- C:\Coding\Naruto arena agent\runtime
- C:\Coding\Naruto arena agent\runtime_local
- C:\Coding\Naruto arena agent\output
- C:\Coding\Naruto arena agent\outputs
- C:\Coding\Naruto arena agent\logs
- C:\Coding\Naruto arena agent\tmp
- C:\Coding\Naruto arena agent\temp
- C:\Coding\Naruto arena agent\cache
- C:\Coding\Naruto arena agent\caches
- C:\Coding\Naruto arena agent\artifacts
- C:\Coding\Naruto arena agent\reports
- C:\Coding\Naruto arena agent\.env
- C:\Coding\Naruto arena agent\.env.*

acceptance:
- Audit the repository deeply enough that the rewritten README accurately describes the real architecture, validated runtime surfaces, helper/planner entrypoints, skill install/use flow, validation commands, repository layout, current limitations, and canonical-source boundaries without guessing.
- Rewrite `README.md` into a polished GitHub-facing document that is useful for a new technical reader and a user who wants to run or use the skill.
- The README must explain the current reality of skill usage honestly, including the difference between the skill package inside the repo and installation into `C:\Users\user\.codex\skills` when relevant.
- Before finalizing the README prose, explicitly apply the guidance from `C:\Users\user\.codex\skills\universal-humanizer\SKILL.md` and keep the meaning technically exact while making the prose read natural, specific, and deliberate.
- Do not invent packaging, installation automation, deployment steps, supported features, or solved gameplay coverage that the repo does not actually prove.
- Keep canonical-source, anti-hallucination, unknown-objective, and progression-scope rules visible in the final README.
- Stage the entire repository, create a commit on the current checked-out branch, and push it to `origin`.
- If push or commit fails because of authentication, remote, or git-state issues, still write the result file with exact blocker evidence and the farthest successful git step.

validation:
- Run `python scripts\validate_skill_reference_bundle.py`.
- Run `python scripts\validate_team_helpers.py`.
- Run `python scripts\validate_mission_pool.py`.
- Run `python scripts\search_characters.py --help`.
- Run `python scripts\team_candidate_report.py --help`.
- Run `python scripts\optimize_mission_pool.py --help`.
- Run `git status --short --branch` before commit and again after commit/push.
- Run `git log -1 --stat --oneline` after commit.
- Run `git remote -v`.
- Run `git ls-remote --heads origin` after push attempt.

delegation_inside_task:
No. NO_VALID_SUBAGENT_SPLIT.

result_file:
C:\Coding\Naruto arena agent\.orchestrator\tasks\TASK-README-PUBLISH-01\RESULT.txt

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

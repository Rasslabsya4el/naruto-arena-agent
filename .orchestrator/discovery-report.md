# Naruto Arena Team Builder Skill — Repository Discovery Report

## Scope

- Task: `TASK-DISCOVERY-REPO-01`
- Date: 2026-04-24
- Workspace inspected: `C:\Coding\Naruto arena agent`
- Remote checked: `https://github.com/Rasslabsya4el/naruto-arena-agent.git`
- Product/runtime implementation was not changed.

## Local Workspace State

- `C:\Coding\Naruto arena agent` is not currently a Git repository.
- `git status --short --branch` from the workspace fails with `fatal: not a git repository (or any of the parent directories): .git`.
- The current workspace contains only the orchestrator control plane, not application source files.
- Root entries currently present:
  - `.orchestrator/`
- Files/directories observed under `.orchestrator/`:
  - `.orchestrator/decisions.md`
  - `.orchestrator/product-source-of-truth.md`
  - `.orchestrator/roadmap.md`
  - `.orchestrator/tasks/`
  - `.orchestrator/tasks/TASK-BOOTSTRAP-PRODUCT-01/TASK-BOOTSTRAP-PRODUCT-01.task.txt`
  - `.orchestrator/tasks/TASK-DISCOVERY-REPO-01/TASK-DISCOVERY-REPO-01.task.txt`
  - `.orchestrator/tasks/TASK-DISCOVERY-SITE-01/TASK-DISCOVERY-SITE-01.task.txt`
  - `.orchestrator/tasks/TASK-SCHEMA-PLAN-01/TASK-SCHEMA-PLAN-01.task.txt`

## Remote Repository State

- `git ls-remote --heads https://github.com/Rasslabsya4el/naruto-arena-agent.git` exits with code `0` and returns no heads.
- `git ls-remote https://github.com/Rasslabsya4el/naruto-arena-agent.git` exits with code `0` and returns no refs.
- Interpretation: the remote is reachable, but currently appears empty/uninitialized.
- The local workspace is not linked to the remote because it has no `.git/` directory.

## AGENTS.md State

- No `AGENTS.md` file was found in `C:\Coding\Naruto arena agent`.
- No parent `AGENTS.md` file was found at `C:\Coding\AGENTS.md` or `C:\AGENTS.md`.
- Therefore, no project-local AGENTS policy currently applies to future files in this workspace.
- Future repo initialization should add a root `AGENTS.md` based on `C:\Coding\Main readme repo\AGENTS_TEMPLATE.md` before substantial implementation work.

## Main README Repo Templates

The following templates should govern future project documentation and AGENTS creation:

- `C:\Coding\Main readme repo\AGENTS_TEMPLATE.md`
  - Governs root `AGENTS.md` structure.
  - Relevant sections include Mission, Instruction Architecture, Project Memory And Control Plane, Delegation Policy, Repository Map, Discovery Policy, Editing Rules, Validation Policy, Output Contract, Git And Repo Hygiene, Security And Boundaries, and Project-Specific Additions.
- `C:\Coding\Main readme repo\project-doc-templates\docs\project\PRODUCT_BRIEF.md`
  - Governs concise product framing, user scenarios, MVP outcome, scope, constraints, and open product questions.
- `C:\Coding\Main readme repo\project-doc-templates\docs\project\CURRENT_STATE.md`
  - Governs tracked reality, current focus, bottlenecks, environment facts, and non-source-of-truth runtime outputs.
- `C:\Coding\Main readme repo\project-doc-templates\docs\project\DECISION_LOG.md`
  - Governs durable decision records.
- `C:\Coding\Main readme repo\project-doc-templates\docs\project\PRODUCT_SPEC.md`
  - Exists in the template tree and should govern contract surfaces, interface rules, proof scenarios, and non-goals when detailed behavior is specified.
- `C:\Coding\Main readme repo\project-doc-templates\docs\roadmap.md`
  - Governs canonical phase graph and full task inventory.
- `C:\Coding\Main readme repo\project-doc-templates\docs\task-queue.md`
  - Governs live queue state, not the full roadmap.
- `C:\Coding\Main readme repo\project-doc-templates\docs\validation-log.md`
  - Governs validation wave summaries and residual risk.

## Recommended Canonical Project Layout

Recommended documentation/control-plane locations after repo bootstrap:

- `AGENTS.md` — root agent policy based on `AGENTS_TEMPLATE.md`.
- `docs/project/PRODUCT_BRIEF.md` — product brief distilled from `.orchestrator/product-source-of-truth.md`.
- `docs/project/CURRENT_STATE.md` — current tracked repo/runtime reality.
- `docs/project/DECISION_LOG.md` — durable decisions, migrated or mirrored from `.orchestrator/decisions.md`.
- `docs/project/PRODUCT_SPEC.md` — skill/runtime contract once schema and command surfaces are known.
- `docs/roadmap.md` — canonical phase graph, aligned with `.orchestrator/roadmap.md`.
- `docs/task-queue.md` — live ready/in-progress/blocked queue.
- `docs/validation-log.md` — validation wave records.
- `.orchestrator/` — bounded task handoff/control-plane artifacts while orchestration continues.

Recommended future implementation layout, pending schema/site discovery tasks:

- `skills/naruto-arena-team-builder/` — final Codex skill package.
- `references/` or `skills/naruto-arena-team-builder/references/` — normalized local game database and source-backed snapshots, depending on the final skill packaging decision.
- `scripts/` — ingestion, normalization, validation, and schema helper scripts.
- `tests/` — targeted contract tests for parser/schema/skill behavior.
- runtime/output directories should be explicitly marked non-source-of-truth in docs and, if created, protected by scoped `AGENTS.md` or ignore rules.

## Immediate Repo Setup Tasks

Recommended next bounded task: initialize and link the local repository before product/runtime implementation.

Minimum setup task should:

- Run `git init` in `C:\Coding\Naruto arena agent`.
- Add remote `origin` pointing to `https://github.com/Rasslabsya4el/naruto-arena-agent.git`.
- Create root `AGENTS.md` from `C:\Coding\Main readme repo\AGENTS_TEMPLATE.md`, tailored to this project.
- Create the canonical `docs/` files from the templates listed above.
- Add a focused `.gitignore` before any runtime scraping artifacts are produced.
- Commit/push only if the orchestrator explicitly authorizes that task to create Git history and publish the initialized baseline.

## Constraints For Future Workers

- Canonical game source remains `https://www.naruto-arena.site/` only unless a future task explicitly allows comparison sources.
- The project must remain data-driven and must not hardcode best teams as product behavior.
- Local structured references must cite source URLs and should prefer explicit unknowns over guessed mechanics.
- Implementation should wait for repo bootstrap plus site/schema discovery outputs.

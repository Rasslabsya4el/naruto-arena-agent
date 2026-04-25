# Naruto Arena Team Builder Skill — Decisions

Use this file for durable orchestration/product decisions only.

## 2026-04-24 - Canonical Game Source - accepted

### Context

- Naruto Arena has multiple versions and mirrors.
- The project requires stable grounded data for a non-hallucinating team-builder skill.

### Decision

- Use only `https://www.naruto-arena.site/` as the canonical game source.
- Do not use other domains, mirrors, or model memory for mechanics unless the user explicitly authorizes version comparison.

### Consequences

- Every data record and mechanical claim must trace back to local references sourced from the canonical site.
- Workers must reject or flag any data that comes from unsupported versions.
- Site reconnaissance may inspect only the canonical domain unless a blocker is reported for orchestrator review.

## 2026-04-24 - Data-Driven Skill, No Hardcoded Best Teams - accepted

### Context

- The product must be a team-building assistant, not a static advice list.

### Decision

- Store normalized game data and references separately from reasoning/instructions.
- The skill may generate and compare teams using local data, but must not hardcode a fixed set of best teams as the core product.

### Consequences

- Schema, validators, provenance, taxonomy, and skill reference build are MVP-critical.
- Recommendations must explain uncertainty and avoid invented mechanics.

## 2026-04-24 - Discovery Before Implementation - accepted

### Context

- Current repo has no implementation files and no project docs beyond `.orchestrator` bootstrap artifacts.
- The source prompt requires repo/doc-template discovery, site reconnaissance, and schema planning before implementation.

### Decision

- Dispatch bounded discovery/planning tasks first.
- Do not create scraper, normalizer, validator, or skill implementation tasks until initial reports are accepted.

### Consequences

- First safe parallel batch is repo discovery, site reconnaissance, and schema planning.
- These tasks may write only their result/report artifacts and must not change product/runtime code.

## 2026-04-24 - GitHub Repository Registered - accepted

### Context

- User created the GitHub repository `https://github.com/Rasslabsya4el/naruto-arena-agent.git`.
- Orchestrator inspection found the local workspace is not yet a git repository.
- `git ls-remote` returned no heads, so the remote appears empty or not yet initialized with branches.

### Decision

- Treat `https://github.com/Rasslabsya4el/naruto-arena-agent.git` as the intended project remote.
- Keep implementation blocked until repo discovery confirms how to initialize/link local state safely.

### Consequences

- `TASK-DISCOVERY-REPO-01` must include local/remote git state and recommend the next repo-bootstrap task.
- Site reconnaissance and schema planning remain safe because their write scopes do not depend on git initialization.

## 2026-04-24 - Repository Discovery Completed - accepted

### Context

- `TASK-DISCOVERY-REPO-01` inspected local workspace, parent policy files, main README repo templates, and GitHub remote state.
- Local workspace is not a git repository.
- Remote `https://github.com/Rasslabsya4el/naruto-arena-agent.git` is reachable but has no refs/heads.
- No applicable AGENTS.md exists yet.

### Decision

- Use the repo discovery report as the basis for repo bootstrap.
- Dispatch a bounded repo-bootstrap task before any product/runtime implementation work.

### Consequences

- Next repo task should initialize/link git, add root AGENTS.md, create canonical docs from templates, and add .gitignore.
- Pushing/committing is not authorized by default inside the task; it must be reported as a follow-up unless explicitly authorized later.

## 2026-04-24 - Schema Planning Completed - accepted

### Context

- `TASK-SCHEMA-PLAN-01` produced `.orchestrator/schema-proposal.md` and a valid result file.
- The proposal covers characters, skills, costs, cooldowns, classes, effects, tags, missions, source references, raw text, confidence, ambiguity flags, validators, and data/reasoning separation.
- The proposal intentionally avoided implementation because canonical-site structure is not accepted yet.

### Decision

- Accept the schema proposal as planning input for future schema implementation.
- Do not dispatch concrete schema files or validator implementation until `TASK-DISCOVERY-SITE-01` and `TASK-REPO-BOOTSTRAP-01` are accepted.

### Consequences

- `TASK-SCHEMA-FILES-01` is planned but blocked.
- Site reconnaissance must confirm actual page/data surfaces before schema fields become durable implementation contracts.

## 2026-04-24 - Authenticated Browser Recon Required - accepted

### Context

- Canonical site reconnaissance through scripted endpoint probing triggered platform safety checks in the worker thread.
- User clarified that full required Naruto Arena data likely requires authenticated access.
- User authorized use of their own account for authenticated site access, but credentials must not be persisted into repository files, task files, result files, logs, or screenshots.

### Decision

- Stop endpoint-probing style reconnaissance for the site task.
- Continue site discovery through the Codex in-app browser with a normal authenticated browser session.
- If authentication is needed, use interactive/manual login in the browser session and do not store credentials on disk.
- Data acquisition must remain limited to the canonical domain `https://www.naruto-arena.site/`.

### Consequences

- The site discovery handoff is replaced with a browser-first follow-up task.
- Workers must collect page-level evidence and data-surface notes from normal navigation/exportable rendered state, not from aggressive API guessing or bypass techniques.
- Any Cloudflare/rate-limit/auth barrier must be documented as a product ingestion constraint, not bypassed.

## 2026-04-24 - Site Recon Thread Lost - accepted

### Context

- The site recon worker thread triggered another platform safety issue and then disappeared before returning a result file.
- No `RESULT.txt` or `RESULT-01.txt` exists under `.orchestrator/tasks/TASK-DISCOVERY-SITE-01/`.
- The project still needs canonical-site discovery, likely requiring authenticated normal browser access.

### Decision

- Treat the previous site recon worker thread as lost with no accepted output.
- Do not continue that thread.
- Create a replacement new-thread task with stricter browser-only/manual-evidence constraints.

### Consequences

- Any partial chat observations from the lost thread are not accepted as durable evidence.
- New site discovery must return a result file and must avoid shell endpoint probing or API/route enumeration.

## 2026-04-24 - Browser Recon Blocked By Node Runtime - blocked

### Context

- `TASK-DISCOVERY-SITE-BROWSER-02` followed the browser-only policy and avoided shell endpoint probing.
- Browser Use / node_repl initialization failed before navigation because resolved Node was `v20.19.5` and the runtime requires `>= v22.22.0`.
- No canonical site pages were inspected and no credentials/session data were accessed.

### Decision

- Do not accept browser recon as site discovery evidence.
- Treat this as an environment blocker that must be fixed before rerunning authenticated browser recon.

### Consequences

- Create a bounded runtime fix task for Browser Use/node_repl Node version configuration.
- Site data acquisition remains blocked until browser recon successfully runs.

## 2026-04-24 - Site Recon Should Run On GPT-5.4 Worker - accepted

### Context

- User identified that repeated false-positive cybersecurity blocking happens when using GPT-5.5 for site parsing tasks.
- User will run the parsing worker on GPT-5.4 instead.
- Previous browser-only recovery path is no longer the preferred path for the next attempt.

### Decision

- Supersede the browser-runtime-fix path for now.
- Dispatch a new normal site parsing/recon task intended for a GPT-5.4 worker.
- Keep canonical source restriction: only `https://www.naruto-arena.site/`.
- Do not persist credentials, cookies, tokens, or auth session data in task files or reports.

### Consequences

- `TASK-BROWSER-RUNTIME-FIX-01` is no longer the immediate next blocker task.
- New site task may use normal public HTTP/HTML/Next artifact inspection and browser navigation as needed, but must not bypass auth/rate limits/Cloudflare or use non-canonical mirrors.

## 2026-04-24 - Repository Bootstrap Completed - accepted

### Context

- `TASK-REPO-BOOTSTRAP-01` initialized the local repository, added origin remote, created root AGENTS.md, canonical docs, and .gitignore.
- No implementation/runtime source files were created.
- No commit or push was performed.

### Decision

- Accept repository bootstrap as complete.
- Treat the repository baseline as ready for first commit/publish decision and later implementation tasks after site evidence is available.

### Consequences

- A publish task may be dispatched if the user wants the baseline committed and pushed.
- Data pipeline implementation remains blocked until site data acquisition evidence is accepted.

## 2026-04-24 - Site Parse Recon Accepted - accepted

### Context

- `TASK-DISCOVERY-SITE-PARSE-03` produced `.orchestrator/site-parse-recon-report.md` and a valid result file.
- The report confirms public home-page data, canonical route inventory, expected prop shapes from same-site Next artifacts, and current redirect-to-home behavior for tested non-home raw fetches.

### Decision

- Accept the parse recon as discovery evidence.
- Use it to unblock schema-file implementation and refine the next browser validation task.

### Consequences

- Site discovery is no longer empty; schema work can proceed from accepted evidence.
- Raw ingestion still waits for browser validation of non-home public routes.

## 2026-04-24 - Separate Public Facts From Session-Aware User State - accepted

### Context

- Accepted parse recon shows that mission/profile surfaces mix public facts with viewer-specific progression and completion state.

### Decision

- Keep public facts and session-aware user state in separate record families and acquisition workflows.

### Consequences

- Schema files must not mix per-account state into public-fact records.
- Any authenticated capture becomes a separate follow-up track, not part of baseline public ingestion.

## 2026-04-24 - Public Browser Validation Blocked By Local Runtime - blocked

### Context

- `TASK-DISCOVERY-SITE-BROWSER-PUBLIC-04` failed before the first navigation step.
- Browser Use / `node_repl` resolved Node `v20.19.5`, but the browser runtime requires `>= 22.22.0`.
- No canonical browser evidence was collected.

### Decision

- Treat this as an environment blocker, not a site-access blocker.
- Keep schema work moving while a separate runtime-fix task addresses the local browser branch.

### Consequences

- Browser validation must be rerun only after the local runtime is fixed.
- Raw ingestion remains blocked on browser evidence, but schema work is not blocked by this environment issue.

## 2026-04-24 - Concrete Schema Files Accepted - accepted

### Context

- `TASK-SCHEMA-FILES-01` created concrete schema files for common structures, characters, missions, ladder entries, public profiles, public clans, and user progress.
- The task validated JSON syntax and the intended public-fact versus user-state split.

### Decision

- Accept the concrete schema files as the current schema baseline.
- Require a follow-up schema-validation task to prove cross-file refs and representative fixtures before ingestion implementation relies on them.

### Consequences

- Schema work moves from file creation to validation.
- Public-fact/user-state boundaries are now durable enough to guide downstream tasks.

## 2026-04-24 - Browser Runtime Diagnosis Accepted - accepted

### Context

- `TASK-BROWSER-RUNTIME-FIX-01` confirmed that `node_repl` resolves `C:\nvm4w\nodejs\node.exe` at `v20.19.5`.
- Browser Use requires `>= 22.22.0`.
- Installed `22.20.0` is insufficient, and the bundled Codex Node path was not validated as an executable fallback.

### Decision

- Accept the runtime diagnosis as sufficient blocker evidence.
- Use the existing `nvm` workflow as the least-risk fix path.

### Consequences

- The next runtime task should request explicit confirmation before applying `nvm install 22.22.0` and `nvm use 22.22.0`.
- Browser validation remains blocked until that runtime change and a bootstrap recheck succeed.

## 2026-04-24 - Normalized Project Data Lives Under data/normalized - accepted

### Context

- The source prompt expects primary normalized outputs at `data/normalized/characters.json` and `data/normalized/missions.json`.
- Skill-ready reference artifacts are a later build product, not the first normalized source of truth.

### Decision

- Keep project-owned normalized canonical data under `data/normalized/`.
- Build later skill-facing copies from that normalized layer into the skill package reference directory.

### Consequences

- Character and mission normalization tasks should target `data/normalized/` first.
- Reference-build tasks should consume normalized project data instead of re-reading raw snapshots directly.

## 2026-04-24 - Authenticated Playwright Capture Unblocks Mainline Ingestion - accepted

### Context

- A local authenticated capture run against `https://www.naruto-arena.site/` produced a usable raw snapshot bundle with characters, missions, ladders, manual pages, and public profile data.
- The capture works by combining authenticated Next JSON reads with rendered-page fallback for routes where the canonical Next JSON path is inconsistent.
- Browser Use remains blocked by the local Node runtime, but Python Playwright capture is already functioning.

### Decision

- Treat authenticated Playwright capture as the current mainline raw acquisition path for the project.
- Treat the Browser Use runtime issue as a secondary tooling branch, not the mainline ingestion blocker.

### Consequences

- Mainline work can move to schema proof and normalization from the existing raw snapshot.
- Browser Use runtime repair remains useful for optional in-app browser validation, but it no longer gates the next MVP tasks.
- Session-aware user state still stays separate from public-fact normalization.

## 2026-04-24 - Schema Proof Accepted, Mission Level Requirement Must Be Modeled - accepted

### Context

- Snapshot-derived schema fixtures and the local validator now prove that the current schema set is structurally valid.
- That proof also surfaced a real public mission field from the canonical snapshot, `levelRequirement`, that the current mission schema cannot store.

### Decision

- Accept schema validation as successful proof for the current schema baseline.
- Before mission normalization starts, extend the mission schema so public level requirements are not silently dropped.

### Consequences

- Character normalization can proceed.
- Mission normalization should wait for a small mission-schema refinement task.

## 2026-04-24 - Hidden Or Unknown Mission Objectives Are Valid Canonical State - accepted

### Context

- User clarified that some Naruto Arena missions legitimately have hidden or unknown objectives.
- The first mission normalization pass preserved explicit unknown mission requirements where the captured canonical data did not reveal objective text.

### Decision

- Do not treat hidden or unknown mission objectives as an automatic ingestion failure.
- When the canonical source does not reveal a mission objective, preserve an explicit unknown/hidden requirement state with ambiguity markers instead of inventing the mechanic.

### Consequences

- Mission normalization follow-ups should focus on real contract gaps such as missing structured public fields or schema-invalid ids, not on forcing every mission into a known objective.
- Skill/runtime behavior must explain that some mission goals are genuinely hidden or unknown in the source data.

## 2026-04-24 - Playable Character Bundle May Exclude Disabled Zero-Skill Raw Entries - accepted

### Context

- The raw snapshot contains two character entries, `Shinobi Alliance Kakashi (S)` and `Edo Tensei Itachi (S)`, with zero skills because the canonical source currently marks them as disabled.
- The current character schema requires non-empty `skills`, and inventing placeholder skills would break the product contract.

### Decision

- Treat `data/normalized/characters.json` as the accepted playable character bundle, not as a mandatory full mirror of every raw character stub.
- It is acceptable to exclude disabled zero-skill raw entries from that playable bundle when exclusion is explicit and source-backed.

### Consequences

- Downstream team-building work can rely on the accepted character bundle without inventing mechanics for disabled entries.
- Any future requirement for full raw-roster completeness should use a separate exclusion-aware contract or artifact, not silently change the playable bundle semantics.

## 2026-04-24 - Mission Schema Uses `level_requirement` For Public Level Gates - accepted

### Context

- The canonical snapshot exposes a real public mission level gate.
- Schema refinement needed one durable field name for normalized mission records and fixtures.

### Decision

- Use `level_requirement` as the public normalized field name for mission level gates.
- Keep it in the public mission schema and out of viewer-specific availability/completion state.

### Consequences

- Mission normalization follow-ups should emit `level_requirement` into normalized records.
- Downstream mission planning, references, and skill behavior should rely on this field name instead of raw-text scraping for level gates.

## 2026-04-24 - Live Capture Output Must Stay Under snapshots/raw - accepted

### Context

- The hardened capture runner now exposes a safe operator contract and explicitly rejects output paths outside runtime snapshot space.
- Live raw captures are runtime artifacts, not tracked project memory.

### Decision

- Future live capture runs must write only under `snapshots/raw`.
- Contract inspection should use `python scripts\capture_site.py --help` or `python scripts\capture_site.py --print-contract` instead of ad hoc path guesses or trial writes into tracked source directories.

### Consequences

- Fresh refresh validation should prove `manifest.captureContract`, `manifest.routeCapture`, and per-record `capture.*` fields only through runtime-path snapshots.
- Worker tasks should treat writes into tracked source paths like `data/normalized` as a hard failure for live capture output.

## 2026-04-24 - Project-Owned Taxonomy Artifacts Live Under Top-Level references - accepted

### Context

- Taxonomy now becomes the active layer between accepted normalized data and later skill-reference build.
- The repo keeps normalized data, schemas, validators, and reference/reasoning artifacts separated.

### Decision

- Phase-5 taxonomy outputs should live under top-level `references\` plus `docs\tagging-guide.md`, not inside `data\normalized` and not directly inside a future skill package.
- Later reference-build work can copy or transform these project-owned taxonomy artifacts into skill-local references as needed.

### Consequences

- `TASK-TAXONOMY-01` should produce `references\effect-taxonomy.json`, `references\tags.json`, and `references\synergy-patterns.md` as project-owned source artifacts.
- `TASK-REFERENCES-BUILD-01` becomes the phase that decides the final skill-local reference layout.

## 2026-04-24 - Skill Runtime Must Read Skill-Local Reference Bundle - accepted

### Context

- The project now has an accepted skill-local reference bundle built from accepted normalized data, taxonomy artifacts, and validation facts.
- Future skill/runtime work needs one stable local surface instead of mixing reads from `data/normalized`, top-level `references`, and orchestration result files.

### Decision

- Future skill/runtime behavior must read its mechanics and provenance surfaces from `skills/naruto-arena-team-builder/references/`.
- `source-map.json` and `data-quality-report.md` are part of that required bundle contract, not optional side artifacts.

### Consequences

- `TASK-REFERENCES-VALIDATE-01` should validate bundle completeness, provenance carry-through, and data-quality/report invariants against the skill-local bundle.
- `TASK-SKILL-BASE-01` should load local bundle artifacts and must not bypass them by reading project-root `references/` or `data/normalized/` directly at runtime.

## 2026-04-24 - Fresh Authenticated Refresh Validation Is Deferred Hardening, Not Current-Use Blocker - accepted

### Context

- The current repo already has an accepted raw snapshot, accepted normalized data, accepted validators, an accepted skill-local reference bundle, accepted helper/planner layers, and accepted representative answer samples.
- User clarified that for the current working agent, no new site refresh is needed because the required data is already parsed and the product is already operating on that local bundle.
- `TASK-INGEST-RAW-VALIDATE-01` would only prove a fresh rerun of the hardened capture contract on newly generated raw artifacts.

### Decision

- Treat `TASK-INGEST-RAW-VALIDATE-01` as deferred ingestion hardening for future data refreshes, not as a blocker for the current usable agent surface.
- Do not require authenticated env vars merely to declare the currently parsed local-data skill usable.

### Consequences

- The current representative MVP surface is no longer blocked on fresh authenticated refresh validation.
- If the project later needs to refresh site data, prove the new capture metadata contract on a fresh run, or resume ingestion maintenance, then `TASK-INGEST-RAW-VALIDATE-01` should be revived.
- Current next steps become optional operational choices such as publish, integration, or future refresh work, not mandatory proof debt for current use.

## 2026-04-24 - Alternative-Character Mission Progress Must Be Modeled Explicitly - accepted

### Context

- The accepted normalized and skill-local mission bundles already contain visible composite-subject requirements such as `The Lone Swordsman`, whose text says `Win 4 battles in a row with Momochi Zabuza or Hoshigaki Kisame.`
- User clarified a required gameplay rule for this project: if both eligible named characters are present on the team for this kind of mission, progress should count twice rather than once.
- The current local mission/runtime surface still preserves these eligible pairs mostly in free text, which means mission planning can undercount progress for this subset of missions.

### Decision

- Treat visible `A or B` mission requirements as a dedicated product/runtime semantic that must not remain free-text-only.
- Add a bounded follow-up that makes the eligible alternatives explicit enough for normalization, references, and mission planning to support stacked per-battle progress when more than one eligible named character is present.

### Consequences

- Until that follow-up lands, alternative-character mission progress must not be treated as fully exact in the runtime.
- Mission normalization, bundle-building, planner behavior, and targeted validators may all need refinement, but hidden or unknown mission objectives still remain explicit unknowns instead of guessed text.

## 2026-04-24 - Mission Requests Imply A Conservative Roster Ceiling From Mission Rank - accepted

### Context

- User clarified a product rule for mission-team advice: if they ask for teams for missions, the skill should assume characters are unlocked only within the rank band implied by those missions.
- Concrete example: if the user asks for a team to unlock `Choji (C)`, the answer should not default to `Sannin+` or similar later-rank characters.
- The current local bundle already exposes `rank_requirement` and `level_requirement` for missions, but the accepted runtime contract does not yet force mission recommendations to honor that progression ceiling by default.

### Decision

- Treat mission and mission-pool requests as progression-scoped by default.
- Unless the user explicitly says that higher-rank characters are already unlocked or asks for aspirational or future-planning teams, recommendations must stay within the highest requested mission rank band.

### Consequences

- Mission recommendation logic must not treat the full character bundle as freely available for every mission request.
- If runtime data needs a small structural addition to represent unlock bands safely, add that durable structure rather than relying only on prompt wording.
- If a mission rank is missing or ambiguous, the answer should surface that limit instead of silently widening the roster to late-rank characters.

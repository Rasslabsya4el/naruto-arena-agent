# Browser Use / node_repl Runtime Fix Report

Date: 2026-04-24
Task: `TASK-BROWSER-RUNTIME-FIX-01`
Status: blocked

## Scope

- Diagnose why Browser Use / `node_repl` resolves an incompatible Node runtime.
- Provide the least risky fix path.
- Do not inspect or navigate the Naruto Arena site in this task.

## Diagnosis

- `node_repl` currently resolves `C:\nvm4w\nodejs\node.exe`.
- Direct shell checks show that this active `nvm` target is `v20.19.5`.
- `node_repl` bootstrap still fails with the same direct repro:
  - `Node runtime too old for node_repl (resolved C:\nvm4w\nodejs\node.exe): found v20.19.5, requires >= v22.22.0.`
- `NODE_REPL_NODE_PATH` is not set, so there is no override forcing `node_repl` to a different binary.
- `nvm list` shows only:
  - `20.19.5` active
  - `22.20.0` installed but inactive
- `22.20.0` is still below the Browser Use minimum `>= v22.22.0`, so switching to the already installed alternate version would not fix the blocker.

## Alternate Runtime Check

- `where.exe node` also finds the Codex app bundled runtime at:
  - `C:\Program Files\WindowsApps\OpenAI.Codex_26.422.2437.0_x64__2p2nqsd0c76g0\app\resources\node.exe`
- File metadata for that bundled runtime reports version `24.14.0`.
- Direct execution of that bundled runtime from this worker returns `Access is denied`.
- Because that binary could not be executed from this worker, it is not a validated fallback path for this task.

## Root Cause

- The Browser Use / `node_repl` runtime is following the active `nvm` shim path.
- The active `nvm` version is `20.19.5`.
- No compatible and runnable `nvm`-managed Node `>= v22.22.0` is currently active.
- No `NODE_REPL_NODE_PATH` override is configured.

## Least-Risky Fix Path

Use the existing `nvm` workflow instead of the WindowsApps bundled Node path.

Required user-approved commands:

```powershell
nvm install 22.22.0
nvm use 22.22.0
node --version
```

Expected result after those commands:

- `node --version` returns `v22.22.0` or newer.
- `C:\nvm4w\nodejs\node.exe` then points at a compatible runtime for `node_repl`.

If `node_repl` still resolves the old version after `nvm use`, the next bounded fix is to launch Codex with an explicit override such as:

```powershell
setx NODE_REPL_NODE_PATH "C:\Users\user\AppData\Local\nvm\v22.22.0\node.exe"
```

That override was not applied in this task because changing runtime environment settings requires explicit user confirmation.

## Validation Summary

- Browser Use / `node_repl` failure reproduced directly in this task.
- Local runtime resolution path identified.
- Current active and installed `nvm` versions identified.
- Alternate bundled Codex Node path inspected and found non-validated because direct execution is denied.
- No Naruto Arena navigation was performed.
- No credentials, cookies, tokens, browser session stores, or auth files were accessed or changed.

## Follow-Up

- Perform the approved `nvm install` / `nvm use` change outside this worker or in a separately authorized runtime-change task.
- Then rerun a minimal Browser Use bootstrap check before re-dispatching browser recon.

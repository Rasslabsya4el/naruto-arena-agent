# Canonical Site Public Browser Report

Date: 2026-04-24
Task: `TASK-DISCOVERY-SITE-BROWSER-PUBLIC-04`
Canonical source only: `https://www.naruto-arena.site/`
Status: blocked

## Scope

- Validate whether non-home canonical routes render publicly in a normal browser session without login.
- Record rendered-route outcomes and visible public fields only.
- Do not persist credentials, cookies, tokens, auth headers, or session values.

## Browser Runtime Blocker

- Attempted to initialize the Browser Use in-app browser runtime through `node_repl` with the `iab` backend before opening any canonical route.
- Browser navigation did not start because the resolved Node runtime was too old for the browser runtime:
  - `C:\nvm4w\nodejs\node.exe`
  - found `v20.19.5`
  - required `>= v22.22.0`
- A bounded environment check with `load_workspace_dependencies()` reported that no bundled workspace runtime dependencies are configured, so there was no ready bundled Node fallback available inside this task.

## Routes Opened

- None.

The blocker occurred before the first navigation, so no evidence was collected for:

- `/`
- `/characters-and-skills`
- representative `/chars/<slug>`
- `/ninja-missions`
- representative `/missions/<section>`
- representative `/mission/<id>`
- `/ninja-ladder`
- `/clan-ladder`
- representative `/profile/<id>`
- representative `/clan/<id>`

## Session And Data Safety Notes

- No login was performed.
- No canonical site page was opened in the browser runtime.
- No credentials, cookies, tokens, auth headers, localStorage values, or sessionStorage values were accessed or written.

## Outcome

- This task did not produce browser evidence about public route rendering.
- The accepted raw-fetch finding that tested non-home routes redirect to `/` remains unresolved in real-browser mode.

## Follow-Up Needed

- Provide a Browser Use / `node_repl` runtime that resolves Node `>= v22.22.0`.
- Rerun this exact public-browser route check without login after the runtime blocker is removed.

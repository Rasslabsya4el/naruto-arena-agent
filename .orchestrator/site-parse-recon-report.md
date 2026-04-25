# Canonical Site Parse Recon Report

Date: 2026-04-24
Task: `TASK-DISCOVERY-SITE-PARSE-03`
Canonical source only: `https://www.naruto-arena.site/`

## Scope And Method

- No login was performed.
- Only canonical-site routes and same-site page-loading artifacts were inspected.
- Methods used:
  - direct document fetches for visible routes;
  - same-site `_next/data/<buildId>/...json` requests that mirror normal Next.js client navigation;
  - same-site `_next/static/...` build manifest and page bundles that are part of normal page loading;
  - extraction of `/` page `__NEXT_DATA__`.
- No credentials, cookies, tokens, auth headers, or session storage values were captured or written.

## Canonical URLs And Methods Inspected

### Direct document fetch

- `https://www.naruto-arena.site/`
- `https://www.naruto-arena.site/chars/aburame-shino`
- `https://www.naruto-arena.site/ninja-missions`
- `https://www.naruto-arena.site/ladders`
- `https://www.naruto-arena.site/profile/ace`
- `https://www.naruto-arena.site/clan/elite-four`
- `https://www.naruto-arena.site/game-manual`
- `https://www.naruto-arena.site/register`

### Same-site `_next/data` probes

- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/chars/aburame-shino.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/ninja-missions.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/ladders.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/profile/ace.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/clan/elite-four.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/characters-and-skills.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/unlock-chars.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/game-manual.json`
- `https://www.naruto-arena.site/_next/data/J1qQni2nXuFhz6ESh3H5p/the-basics.json`

### Same-site route/build artifacts

- `https://www.naruto-arena.site/_next/static/J1qQni2nXuFhz6ESh3H5p/_buildManifest.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/index-8e25dc3b330efed8.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/characters-and-skills-7c4cf0376d4e8789.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/chars/[id]-67522eeb2e3938e0.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/ninja-missions-02074e209c88b5e3.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/missions/[id]-fc236c5a8ccf7455.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/mission/[id]-e070ada316176065.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/profile/[id]-5dda3b440803a56d.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/clan/[id]-ea64423c7d33e2af.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/ladders-b7a607535166d9ba.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/ninja-ladder-44aff3e6f25ae620.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/clan-ladder-fde349e1c5093821.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/road-to-hokage-db08b2e4ecbc4d0e.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/hall-of-fame-8a6e66f34eb9896b.js`
- `https://www.naruto-arena.site/_next/static/chunks/pages/unlock-chars-72df06460a9b657f.js`

## Observed Behavior

### 1. Public home page already exposes real data

- `/` responds publicly and includes `__NEXT_DATA__`.
- The home `__NEXT_DATA__` includes:
  - `announcementPosts` with current balance/news posts;
  - `topTierPlayers.topLevelPlayers`;
  - `topTierPlayers.topWinPlayers`;
  - `topTierPlayers.topStreakPlayers`;
  - `topTierPlayers.topBestClans`;
  - `_season` leader slots such as `rikudouSennin`, `hokage`, `raikage`, `tsuchikage`, `kazekage`, `mizukage`.
- The inspected home snapshot exposed 5 announcement posts and top-10 lists for level, wins, streak, and clans.

### 2. Non-browser route fetches currently redirect to `/`

- Direct document fetches for tested non-home routes resolved back to `/`.
- Same-site `_next/data/...json` requests for tested non-home routes returned JSON redirects of the form:
  - `{"pageProps":{"__N_REDIRECT":"/","__N_REDIRECT_STATUS":307},"__N_SSP":true}`
- This means raw non-browser acquisition of most target routes is not currently reliable.
- The redirect alone does **not** prove login is required; it may be due to route protection, JS/browser challenge requirements, or other server-side gating.

### 3. The public build manifest clearly declares MVP-relevant routes

The canonical build manifest exposes these relevant routes:

- `/characters-and-skills`
- `/chars/[id]`
- `/ninja-missions`
- `/missions/[id]`
- `/mission/[id]`
- `/profile/[id]`
- `/clan/[id]`
- `/ninja-ladder`
- `/clan-ladder`
- `/road-to-hokage`
- `/hall-of-fame`
- `/unlock-chars`
- `/game-manual`
- `/the-basics`

### 4. Route bundles reveal the data shapes expected by each page

#### Characters and skills

- `/characters-and-skills` bundle describes a public overview page for all characters and links each record to `/chars/<slug>`.
- `/chars/[id]` bundle expects:
  - character name;
  - character description;
  - mission unlock name or no requirement;
  - `skills[]` with skill name, description, cooldown, chakra/energy icons, and classes;
  - image dictionaries for face and skill art.

#### Missions

- `/ninja-missions` bundle expects mission sections/anime groupings with descriptions and links to `/missions/<section>`.
- `/missions/[id]` bundle expects per-mission list data including:
  - mission name;
  - unlocked character;
  - rank requirement;
  - prerequisite/completed requirements;
  - availability/completion booleans;
  - link to `/mission/<id>`.
- `/mission/[id]` bundle expects detail data including:
  - mission name;
  - section/anime link-back;
  - reward panel;
  - unlocked character and/or unlocked border;
  - rank requirement;
  - progress steps.

#### Profiles and clans

- `/profile/[id]` bundle expects:
  - target account data;
  - clan information;
  - ladder, quick, and private game lists from the last 24 hours;
  - replay availability flags.
- `/clan/[id]` bundle expects:
  - clan name and abbreviation;
  - clan ladder rank;
  - level/xp stats;
  - member groupings/member lists;
  - links back to member profiles.

#### Ladders

- `/ninja-ladder` bundle expects tabular player data with:
  - rank;
  - username;
  - level;
  - xp;
  - wins;
  - losses;
  - streak.
- `/clan-ladder` bundle expects similar clan standings with clan abbreviation, clan name, level, xp, wins, and losses.
- `/hall-of-fame` bundle expects season summary data including wins, losses, streak, fame, level, and profile links.
- `/road-to-hokage` is informational and explains season mechanics/rewards rather than serving as the raw ranking surface.

### 5. Session-dependent vs product-fact data

- The site distinguishes between generic page data and viewer/session-aware state through `userPlayer` props.
- Mission list/detail bundles contain fields like availability/completion and completed requirements that are likely session-aware for a specific account.
- That means mission facts and rewards may be public, but **personal progression state** likely needs an authenticated session if the product wants account-specific planning.

### 6. Excluded surface

- `/unlock-chars` is not a safe ingestion source for MVP facts.
- It is a mutating surface that posts to a same-site API and should be excluded from any read-only acquisition plan.
- No literal secret values from that bundle are reproduced in repo artifacts.

## Data Category Assessment

| Category | Current evidence | Access assessment | Safe acquisition path |
| --- | --- | --- | --- |
| Character roster list | Declared public route `/characters-and-skills`; bundle expects full overview records | Partially visible publicly; raw non-browser fetch currently redirects | Normal browser capture after JS/challenge clearance; no login evidence yet |
| Character detail and skills | `/chars/[id]` bundle expects description, unlock mission, skill text, cooldown, chakra, classes | Partially visible publicly; raw non-browser fetch currently redirects | Normal browser capture after JS/challenge clearance; if still blocked in browser, escalate as auth/blocker |
| Mission section list | `/ninja-missions` bundle expects public section cards and descriptions | Partially visible publicly; raw non-browser fetch currently redirects | Normal browser capture after JS/challenge clearance |
| Mission list within a section | `/missions/[id]` bundle expects mission requirements, rank gates, unlock refs | Partially visible publicly; some fields likely session-aware | Browser capture for public facts; authenticated browser only if account-specific availability/completion is required |
| Mission detail / rewards | `/mission/[id]` bundle expects reward, unlocked char/border, progress text | Partially visible publicly; progress may be session-aware | Browser capture for mission facts; authenticated browser for personal completion state |
| Ladders / standings | Home `__NEXT_DATA__` already exposes top lists; ladder bundles expect full tables | Public data definitely exists, but full ladder routes still redirect in raw fetch mode | Public browser capture first; authenticated session not obviously required for standings |
| Clan pages | Home links to clan pages; clan bundle expects roster and stats | Likely public surface, but raw non-browser fetch redirects | Public browser capture after JS/challenge clearance |
| Public player profiles | Home/news link to profiles; profile bundle expects target account and recent games | Likely public surface, but raw non-browser fetch redirects | Public browser capture after JS/challenge clearance |
| User-specific unlock/progression state | Mission bundles include availability/completion state tied to session | Likely auth/session-dependent | User-authorized authenticated browser capture only; do not store session material |

## Safe Acquisition Plan

### Phase 1 — public browser-first capture

Use a normal browser session on the canonical site, without login first, and capture only rendered/public facts from:

- `/`
- `/characters-and-skills`
- representative `/chars/<slug>`
- `/ninja-missions`
- representative `/missions/<section>`
- representative `/mission/<id>`
- `/ninja-ladder`
- `/clan-ladder`
- representative `/profile/<user>`
- representative `/clan/<slug>`

Why:

- raw route fetches are currently redirected;
- bundles prove the routes exist and define the data model;
- a real browser session is the lowest-risk next step to determine whether the blocker is only a JS/challenge gate.

### Phase 2 — authenticated browser capture only if needed

If the product needs personal mission progress, available missions, or current unlock state:

- use a user-authorized authenticated browser session;
- manually log in;
- capture only rendered facts or same-site responses necessary for that user-state slice;
- never store cookies, tokens, headers, or raw session exports.

### Phase 3 — ingestion boundary for later tasks

Later ingestion should treat data surfaces as two buckets:

- **public-fact bucket**: character facts, skill text, mission text, rewards, public ladder/clan/profile facts;
- **session-state bucket**: user progression, available missions, unlocked content for a specific account.

Do not merge those two buckets implicitly.

## Likely Directly Capturable Fields

### Public-fact fields likely available from route props

- character name
- character description
- character unlock mission label
- skill name
- skill description
- skill cooldown
- skill chakra cost/icon sequence
- skill classes
- mission section/anime name
- mission name
- mission rank requirement
- mission prerequisite mission names
- mission reward text
- unlocked character reference
- unlocked border/reference
- public ladder rank rows
- public clan ladder rows
- public profile recent match rows
- public clan roster/member rows

### Fields likely requiring manual/authenticated steps

- current user mission completion state
- current user mission availability state
- current user unlock inventory
- any viewer-specific replay/private visibility behavior
- any personalized “what should I play next?” inputs derived from the logged-in account

## Recommended Follow-Up For The Ingestion Pipeline

1. Treat direct raw HTTP scraping of non-home routes as unproven and currently blocked.
2. Validate route accessibility in a real browser session before designing scraper contracts.
3. Build schemas so public facts and user-state facts are separate record families.
4. Exclude mutating/admin-like surfaces from ingestion scope.
5. Once browser evidence is accepted, create a bounded raw-capture task that stores only reproducible public facts and later a separate authenticated assisted workflow for user-state capture.

## Bottom Line

- Core MVP data surfaces for characters, skills, missions, profiles, clans, and ladders clearly exist on the canonical site.
- Public home-page evidence is already confirmed.
- Most non-home routes cannot currently be trusted from raw non-browser fetches because they redirect to `/`.
- The safest next acquisition path is **browser-first public capture**, followed by **authenticated browser capture only for user-specific progression state**.

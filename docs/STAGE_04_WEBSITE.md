# Stage 4–5: Website and API integration

The CricketLens website is a React 18 + TypeScript single-page app built with Vite and Tailwind CSS
(`web/`). It reads everything from the FastAPI backend in `src/cricketlens/api/`, which computes statistics
from `data/processed` and `data/derived` and calls the Stage 3 inference functions with the saved models.
This document describes the frontend, lists every API endpoint, and records the definitions and guards the
two layers share.

## Running it

From the repository root, with the Python environment installed (`pip install -e ".[dev]"`, see the
README):

```bash
# backend, port 8000 (data, models and reports are found from the package location, so any
# directory works; CRICKETLENS_ROOT overrides it)
python -m uvicorn cricketlens.api.app:app --host 127.0.0.1 --port 8000

# frontend, port 5173, in a second terminal
cd web
npm ci
npm run dev
```

The Vite dev server forwards `/api/*` to `http://127.0.0.1:8000` (`web/vite.config.ts`). `npm run build`
runs `tsc` and writes a production bundle to `web/dist/` (git-ignored). Interactive API documentation is at
`http://127.0.0.1:8000/docs`.

The dev server listens on `localhost` only. The frontend calls the relative `/api` (`web/src/api/base.ts`);
`VITE_API_BASE_URL` overrides it at build time for a frontend deployed apart from the API. The API allows
cross-origin requests only from the origins in `CORS_ALLOW_ORIGINS` (comma-separated; default
`http://localhost:5173` and `http://127.0.0.1:5173`), with GET and POST and no credentials.

## Deploying to Vercel

One Vercel project serves both parts on one domain: the React build as static files, and the FastAPI app as
a Python Vercel Function under `/api`.

- `vercel.json`: `"framework": null` (the root `pyproject.toml` lists FastAPI, which would otherwise select
  the FastAPI preset and send every request to the app); build `cd web && npm ci && npm run build`; output
  `web/dist`. Rewrites: `/api/(.*)` → `/api/index`, and every other path without a file extension →
  `/index.html` for deep links. Existing static files are served before any rewrite, so the hero images,
  `/figures/stage_02/*` and the JavaScript assets come from the static build, and a missing asset is a
  404 rather than the app.
- `api/index.py` adds `src/` to the import path and imports `app` from `cricketlens.api.app`; the app is
  not duplicated.
- `api/requirements.txt` lists only what the running API imports (FastAPI, Pydantic, pandas, NumPy, SciPy,
  scikit-learn 1.8.0, joblib), pinned to the tested versions. Vercel reads the dependency file next to the
  entrypoint before the root `pyproject.toml`, so matplotlib, uvicorn and the test tools are not installed.
  `api/.python-version` selects Python 3.14.
- The function's `excludeFiles` removes everything outside `api/` and `src/`, and `includeFiles` adds back
  exactly the 46 files the API opens: `data/processed/{matches,deliveries,innings,batter_innings,
  stage03_wicket_full_history_2008_2026}.csv`, the six `data/derived` tables, the two deployment models, the
  Stage 1 audit files, seven Stage 2 tables, the Stage 3 results JSON and holdout forecasts, and the 20
  Stage 2 figures. Nothing in `data/raw` is read at runtime. `maxDuration` is 60 seconds.

Environment variables: none required. `CORS_ALLOW_ORIGINS` and `VITE_API_BASE_URL` matter only when the
frontend and the API are deployed on different origins; `CRICKETLENS_ROOT` only to read the data from
another directory.

A Vercel deployment is reachable by anyone with its URL; the hero artwork's image rights were not verified
(`LICENSE_NOTES.md`), so keep the deployment protected or replace the artwork before making it public.

### (a) Dashboard import from GitHub

1. The owner of `Bhagy25/IPL_Predictor` authorises the Vercel GitHub app for the repository (on Vercel's
   import screen, or in GitHub under Settings → Applications).
2. Vercel: **Add New… → Project** → import `IPL_Predictor`.
3. Root Directory: the repository root (`./`). Leave the Framework Preset, build and output settings as
   they are (`vercel.json` sets them) and add no environment variables. **Deploy**.
4. New projects deploy `main` to production, and `main` does not contain this configuration. Set
   **Settings → Environments → Production → Branch Tracking** to `feature/cricketlens-final` and **Save**.
5. **Deployments → Create Deployment** → branch `feature/cricketlens-final` → **Create Deployment**. Later
   pushes to that branch deploy to production automatically; other branches get preview deployments.

### (b) Vercel CLI from a local clone

From a fresh clone, so that `.venv/`, `node_modules/` and other local files are not uploaded:

```bash
git clone --branch feature/cricketlens-final https://github.com/Bhagy25/IPL_Predictor.git
cd IPL_Predictor
npm i -g vercel        # or prefix each command with npx
vercel login
vercel                 # link or create the project and deploy (the first deployment is production)
vercel --prod          # later production deployments; plain `vercel` makes previews
```

Keep the code directory `./` and do not override the detected settings when asked.

### Verifying a deployment

- `GET /api/health`: `status` `"healthy"`; `archive_matches` 1243; `archive` 19 seasons, 2008-04-18 to
  2026-05-31; `derived_tables.available` true; `prediction_models.wicket.available` and
  `prediction_models.batter.available` true. A JSON 404 or the website's HTML instead means the `/api`
  rewrite or the function is not working; `"degraded"` names the missing data or model.
- Refresh on a deep link (`/players`, `/tracker`): the app loads, and an unknown path returns to the
  homepage.
- One wicket and one batter prediction in the Prediction Arena.

### Measurements

Measured locally for this configuration (a serverless instance will differ somewhat):

| Measure | Result | Vercel limit |
|---|---|---|
| Function bundle, uncompressed: Linux wheels for CPython 3.14 (`pip install --target`) plus the bundled files | 384.9 MB: 330.3 MB packages (SciPy 132.8, pandas 69.0, NumPy 65.3, scikit-learn 42.7), 54.6 MB files | 500 MB (Python) |
| API process memory | 187 MB once started, 237 MB with all data loaded, 260 MB after 1,161 requests; peak 340 MB | 2 GB (Hobby) |
| Cold start, process start to first 200 | `/api/overview/summary` median 7.4 s; `/api/players/ba607b88/overview` median 8.7 s (three fresh processes each) | `maxDuration` 60 s |
| Largest response body, over every operation, all 20 figures and parameter variants (1,161 requests) | 0.16 MB, `/api/predict/options` | 4.5 MB |

The production build was also checked locally behind the same rewrites (`web/dist` served with
`vercel.json`'s rules, `/api` proxied to the API started from another directory): every route by direct
URL and after a refresh, navigation, back and forward, unknown URLs, both predictions and Tracker export
and import, at 1440px and 390px, with no console errors or warnings.

## Frontend architecture

### Routes

`web/src/App.tsx` defines six routes inside one `BrowserRouter` (opted in to the React Router v7
`startTransition` and relative-splat behaviour). Each page is lazy-loaded into its own chunk behind a
`Suspense` fallback, so a visit downloads only the shell and the pages it opens.

| Path | Page | Content |
|---|---|---|
| `/` | `IPLOverviewPage` | Hero, archive figures, season charts, team records and champions |
| `/teams` | `TeamAnalysisPage` | Franchise overview, season filter, opponents, head-to-head, venues |
| `/players` | `PlayerExplorerPage` | Player directory and career or season profiles with a match log |
| `/eda` | `StatisticsEDAPage` | Filterable full-history analysis, player comparison, Stage 2 research figures |
| `/predict` | `PredictionArenaPage` | Next-over wicket risk and batter milestone tools; model evaluation |
| `/tracker` | `PredictionTrackerPage` | Saved predictions with outcomes and scores; 2026 holdout replay |

`/overview` redirects to `/`, and any unknown path redirects to `/`.

### Shared pieces

- `components/Navbar.tsx`, `Footer.tsx`: the six-route navigation (a menu on narrow screens) and a footer
  whose archive span and API status come from `/api/health`.
- `components/HeroCollage.tsx`: the approved hero artwork as one `<picture>` (desktop image from 768px,
  mobile image below), so only one PNG is downloaded.
- `components/KPICards.tsx`, `PerspectiveCharts.tsx`, `TeamRecordsTable.tsx`, `ComponentStatesShowcase.tsx`:
  homepage sections.
- `components/eda/`: `ChartFrame` (title, applied filters, coverage, definitions and source for each chart),
  `AreaViews` (one view per analysis area) and `PlayerComparison`.
- `components/player/`: `ProfileSections` (stat cards, keyboard-operable tabs, scrollable data tables),
  `MatchLog` and `playerFormat` (null-state wording).
- `components/predict/`: `WicketTool`, `BatterTool`, `HoldoutReplay`, `shared` (form fields, errors,
  disclaimer) and `trackerStore` (saved predictions).
- `api/*.ts`: one typed client per endpoint group; `types/index.ts` mirrors the API schemas;
  `utils/format.ts` formats counts, rates, percentages and season ranges.

### State handling

- Each page keeps its own React state and fetches what it needs. When inputs change faster than responses
  arrive, only the latest response is applied (request counters or an `AbortController`). The homepage,
  Statistics & EDA, the prediction tools, the holdout replay and the footer also cancel requests still
  running when they are left.
- The Statistics & EDA filters (season range, team, venue and minimums) live in the URL query string, so a
  view can be bookmarked or shared.
- Loading, error-with-Retry and empty states are shown explicitly; a value the API reports as undefined is
  shown as "—" with the reason, never as 0.
- The Prediction Tracker keeps saved predictions in `localStorage` under `cricketlens.predictionTracker` as
  versioned JSON (version 1). Every read and write is wrapped: if storage is blocked or full the tracker keeps
  working in memory and says so, and unreadable stored data is copied aside rather than discarded. Imports
  are validated against the schema before anything is added. Nothing is sent to the server.

## Prediction guards

Predictions come only from a successful API response; the browser checks the same rules first, but the API
is the authority.

| Tool | Rule | Response |
|---|---|---|
| Wicket | Completed overs 1–19, innings 1 or 2, wickets 0–9, runs ≥ 0, last-over runs ≤ runs, last-over wickets ≤ wickets (the rules of `predict_wicket.forecast()`) | 422 with a message per field |
| Wicket | Teams must be two different active franchises and the venue one the model was trained on (its encoders would otherwise silently ignore an unknown name) | 422 |
| Wicket | Physically impossible: runs > 36 × completed overs + 30, or last-over runs > 56 (36 from six legal balls plus an allowance for extras) | 422 |
| Wicket | Runs, run rate or last-over runs outside the range seen at that checkpoint in the 44,161 training rows (`data/processed/stage03_wicket_full_history_2008_2026.csv`) | Probability unchanged, plus an extrapolation warning listing each input and its observed range |
| Batter | The player must have eligible batting history; teams and venue as above | 422 |
| Batter | The match date must be after the last match in the data (2026-05-31) and after the player's latest eligible innings (the rule of `forecast_future_batter.forecast()`) | 422 |
| Batter | By default only players in a 2026 match squad are listed; others can be included and their forecasts carry a note that they assume the player plays again | Note in the response |
| Batter | P(50+) must not exceed P(30+) | Treated as a server error, never returned |
| Both | A missing or invalid model file | 503; `/api/health` reports it; no probability is returned |

## Definitions

The definitions shown on the website come from the API responses and match the README's "Key definitions":
results and Super Overs, win % = wins ÷ (matches − no results), team and bowler-credited wickets, batting
innings including non-striker appearances, ducks, averages, phases, roles, the first-innings histogram
eligibility, champions and franchise renames. The comparative window used by the homepage team records and
Team Analysis runs from the first season every current franchise played to the latest season (2022–2026).
The 2026 holdout applies only to model evaluation; every descriptive statistic includes 2026.

## API endpoint reference

Generated from the running application's `/openapi.json` (OpenAPI 3.1.0, API version 0.1.0). A `?` marks
an optional query parameter.

| Group | Method | Path | Summary | Query / body |
|---|---|---|---|---|
| System | GET | `/api/health` | Health check and archive verification status | — |
| Overview | GET | `/api/overview/summary` | Get 8 verified historical IPL KPI metrics and dataset coverage | — |
| Overview | GET | `/api/overview/charts` | Get historical IPL charts and verified team records | — |
| Teams | GET | `/api/teams` | List all canonical IPL franchises | — |
| Teams | GET | `/api/teams/head-to-head` | Get head-to-head records between two franchises | `team1`, `team2`, `season?` |
| Teams | GET | `/api/teams/{team_id}/overview` | Get comprehensive analytical profile for a team | `season?` |
| Teams | GET | `/api/teams/{team_id}/venues` | Venue records for a team with a minimum-matches filter | `season?`, `min_matches?` |
| Players | GET | `/api/players` | List and search players with pagination and filters | `query?`, `role?`, `experience_filter?`, `page?`, `page_size?`, `sort_by?`, `min_innings?` |
| Players | GET | `/api/players/{player_id}/overview` | Get detailed career profile (Batting, Bowling, Match Logs) for a player | `season?` |
| Players | GET | `/api/players/{player_id}/matches` | Paginated match-by-match log for a player | `season?`, `page?`, `page_size?` |
| Statistics & EDA | GET | `/api/eda/filters` | Filter options for the full-history analysis | — |
| Statistics & EDA | GET | `/api/eda/analysis` | Filterable full-history EDA across the analysis areas | `season_from?`, `season_to?`, `team?`, `venue?`, `venue_min_matches?`, `bat_min_balls?`, `bowl_min_balls?` |
| Statistics & EDA | GET | `/api/eda/player-comparison` | Compare 2–4 players within a season range | `players`, `season_from?`, `season_to?`, `team?`, `venue?` |
| Statistics & EDA | GET | `/api/eda/catalog` | Get catalog of 20 Stage 2 exploratory figures | — |
| Statistics & EDA | GET | `/api/eda/summary` | Get raw statistical tables backing Stage 2 figures | — |
| Statistics & EDA | GET | `/api/eda/figures/{figure_name}` | Serve high-resolution Stage 2 PNG figure | — |
| Predictions | GET | `/api/predict/options` | Inputs the deployment models accept | — |
| Predictions | POST | `/api/predict/wicket` | Chance of at least one wicket in the next over | JSON body |
| Predictions | POST | `/api/predict/batter` | Chance of a batter scoring 30+ and 50+ | JSON body |
| Predictions | GET | `/api/predict/models` | Model metadata and the official Stage 3 evaluation | — |
| Predictions | GET | `/api/predict/holdout-replay` | 2026 holdout replay: matches and season summary | — |
| Predictions | GET | `/api/predict/holdout-replay/{match_id}` | 2026 holdout replay for one match | — |

22 operations.

# Session Log

## Session Summary — 2026-06-03 (Phase 2 — Frontend + Backend additions)

### Completed
- **Phase 1 bug fix (targeted):** `services/results.py` — computed P&L into a local
  `pnl_units` float so the type checker can prove non-null before deriving
  `profit_loss_dollars` (was a `float | None` arithmetic warning on line 132). No behavior
  change. Committed separately.
- **Backend additions (no analytics logic changed):**
  - `GET /api/system/stats` → DB counts (trades, events, snapshots, odds lines, active sports).
  - `POST /api/system/seed` → runs the seed script logic on demand (for the Settings reset button).
  - `services/odds_ingestion.py` — added `PLAYER_PROP_MARKETS` and a `poll_player_props()`
    per-event method (player props are only on the per-event endpoint). Fixture fallback
    preserved; live path is default when a real key is present.
  - New schemas: `SystemStats`, `SeedResult`.
- **Step 8 — Frontend scaffold:** Vite proxy `/api → :8000`, tsconfig `@/*` path alias +
  strict, Tailwind dark theme with the surface/signal color tokens, postcss. `src/api/client.ts`
  (the only place `fetch` is called), `src/types/index.ts` (mirrors backend schemas exactly),
  `src/store/settingsStore.ts` (Zustand + localStorage), hooks (`useOpportunities` auto-refresh
  60s, `useTrades`, `usePnl`, `useCLV`, `useBankroll`, `useCredits`, `useEvents`, `useSystemStats`),
  shared components (StatCard, Badge, DataTable w/ sort + row expansion, PriceDisplay, EdgeBadge,
  Card, Button, Toaster, feedback states, Layout w/ sidebar + paper-mode badge).
- **Step 9 — All 6 pages:** Dashboard (opportunity feed + P&L/credits/bankroll widgets +
  sparkline), Opportunities (filter bar + sortable table + inline book-comparison expansion),
  Trade Logger (URL-prefilled form + live Kelly suggestion), Trade Journal (summary bar +
  filters + 25/page pagination + CSV export + row detail), Analytics (6 Recharts panels:
  equity curve, CLV histogram, edge-vs-P&L scatter w/ regression trendline, P&L by sport,
  rolling 50-bet win rate, CLV by bookmaker), Settings (API config, trading params, system).
- **Step 11 — Verified:** `tsc --noEmit` clean (strict), `pnpm build` succeeds (866 modules).
  Ran backend (:8000, seeded) + Vite dev (:3000) together: frontend serves, `/api` proxy
  reaches the backend, real data flows (pnl 100 trades / 55% / $1256 / 90 equity points;
  opportunities = 1 after a poll).
- **Step 12 — README** rewritten per spec (what it does, ASCII architecture, quick start,
  key concepts, paper-trading-first, API key, project structure).

### Current State
- **Working:** Full stack builds and runs. Backend tests still green (26 passed). Frontend
  typechecks strict and builds. End-to-end data wiring verified through the dev proxy.
- **Verified by build + data flow, NOT by human eyeball:** chart rendering and visual layout
  were not opened in a browser in this session — the React app builds and serves and the data
  is correct, but someone should `pnpm dev` + open http://localhost:3000 to confirm the visuals.
- **Deviations from the Phase 2 prompt's type sketches (intentional):** frontend types mirror
  the *actual* Phase 1 backend schemas per CLAUDE.md ("mirror exactly"), so `PnLSummary` uses
  `win_rate_pct` / `net_units` / `equity_curve[{date,bankroll,cumulative_pnl_units}]` rather
  than the prompt's `win_rate` / `cumulative_units`. Dashboard "Today/Week/All-time" P&L and
  the Analytics CLV-by-bookmaker / edge-vs-ROI / rolling-win-rate panels are computed
  client-side from `/trades` + `/events` + `/analytics/bankroll` (the backend doesn't expose
  per-trade-sport or per-book CLV directly). Opportunities' sport filter is best-effort
  (opportunities carry team names, not `sport_key`) — noted inline in the page.
- **Toolchain note:** pnpm/Docker aren't installed system-wide; used `corepack pnpm` and a pip
  venv (`backend/.venv`). `node_modules`, `.venv`, `dist`, `bettor.db` are gitignored.

### Next Session Should Start With
- Open the app in a browser (`pnpm dev`) and visually confirm all 6 pages + 6 charts render.
- When a real `ODDS_API_KEY` is available (from PA): run Step 10's live-poll verification
  (real rows in odds_snapshots/odds_lines, real credits in api_usage_log, real opportunities).

### Open Questions
- Player-prop ingestion (`poll_player_props`) is implemented but unexercised without a live
  key; confirm the real API's prop response nesting (the `description` field for player name)
  on first live poll.
- Bundle size warning (~672 kB, Recharts-dominated). Fine for an internal tool; could
  code-split later if it matters.

---

## Session Summary — 2026-06-03

### Completed
- **Step 1 — Scaffold:** Full repo structure per CLAUDE.md. `.gitignore` (Python/Node/Docker/IDE/OS),
  `backend/pyproject.toml` (Poetry, all required deps + dev group), `frontend/package.json` (pnpm:
  React 18, react-router v6, TS, Vite, Tailwind, Recharts, Zustand), frontend config/placeholder
  scaffold (Vite/tsconfig/tailwind/index.html/main.tsx/App.tsx), root `README.md`.
- **Step 2 — Docker:** `docker-compose.yml` (postgres 15 + healthcheck, backend, frontend on
  `bettor-network`), `backend/Dockerfile` (python:3.11-slim + Poetry), `frontend/Dockerfile`
  (node:20-alpine + pnpm), `backend/.env.example` (verbatim from CLAUDE.md).
- **Step 3 — DB + migrations:** `app/config.py` (pydantic-settings, all env vars typed),
  `app/db/base.py` (async engine, `AsyncSessionLocal`, `get_db`), `app/db/models.py` (all 8 models —
  sports, events, odds_snapshots, odds_lines, closing_lines, trades, bankroll_snapshots,
  api_usage_log — SQLAlchemy 2.0 typed mapping, portable `Uuid` PKs, 3 enums, `__repr__` on each).
  Alembic configured to read `DATABASE_URL` from settings; initial migration autogenerated
  (`5afa82df087e_initial_schema`) — applies cleanly, all 8 tables present.
- **Step 4 — Analytics (the core):** `no_vig.py`, `edge_detection.py` (SHARP_HIERARCHY, sharp-anchor
  selection with consensus-average fallback, Kelly sizing, `find_edges`), `clv.py`. **26 tests pass,
  95% coverage on `app/analytics`** (target was 80%). All required cases from the prompt covered.
- **Step 5 — Ingestion:** `services/odds_ingestion.py` (`OddsIngestionService`: poll_sport,
  poll_all_active_sports, mark_closing_lines, fetch_and_store_sports; 429 exponential backoff;
  **fixture fallback in dev when no API key**). `services/results.py` (scores + settlement + CLV).
  Fixture `tests/fixtures/sample_odds_response.json` (3 NFL games × Pinnacle/DK/FD/BetMGM, h2h+spreads).
- **Step 6 — API:** `main.py` (lifespan + APScheduler jobs: poll every `POLL_INTERVAL_MINUTES`,
  mark closing lines every 15m; request-logging middleware; CORS; `GET /health`). Pydantic schemas
  (odds/trades/analytics). All endpoints from the API map implemented under `/api`. Verified via
  TestClient: `/health` 200, `/api/opportunities` returns `[]` pre-poll and a ranked edge post-poll.
- **Step 7 — Seed:** `scripts/seed_demo_data.py` → 100 settled paper trades (55 W / 45 L),
  avg CLV **+1.80%**, sports 38/37/25 (NFL/NBA/MLB), final bankroll **$1,256.02**, 90 daily
  bankroll snapshots, 20 completed events. Idempotent reseed. `seed=41` chosen to hit CLV target.

### Current State
- **Working:** Full backend runs. Tests green (26 passed). Migration applies. Seed populates a
  realistic dataset. Verified live against SQLite: `GET /api/trades` → 100, `GET /api/analytics/pnl`
  → 90-point equity curve ($1000 → $1256, 55% win rate), `/analytics/clv` (mean +1.80, 73% positive),
  `/analytics/edge` buckets, `/analytics/bankroll` (90 snapshots), `POST /trades` (Kelly computed
  server-side), `PUT /trades/{id}` (void), real-money trade blocked 403 under paper mode, manual
  `POST /system/poll` ingests fixture data.
- **Local dev note:** Poetry/Docker/pnpm are not installed on this machine, so verification used a
  pip venv at `backend/.venv` and SQLite (`sqlite+aiosqlite`, the CLAUDE.md test DB). All deps pinned
  in `pyproject.toml` for the real Postgres/Docker deployment. `backend/.venv` and `bettor.db` are
  gitignored.
- **Nothing known broken.** Frontend is intentionally a placeholder (Phase 2).

### Next Session Should Start With
- **Phase 2:** build the React frontend against this live API (see `Phase_2_prompt.md`). Start with
  `src/api/client.ts` + `src/types/` mirroring the Pydantic schemas, then the Dashboard page.

### Open Questions
- Real Odds API response headers (`x-requests-last`/`x-requests-remaining`) drive the credits
  dashboard; only validated against fixtures (fixture mode logs 0 credits). Confirm header names on
  the first live poll from Pennsylvania.
- Closing-line capture for CLV depends on the 15-min scheduler having a snapshot near commence_time;
  poll cadence vs. game start timing should be validated with live data.

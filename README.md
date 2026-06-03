# Bettor — Sports Betting Edge Finding System

## What It Does

Bettor is a systematic, CLV-first sports betting tool. Instead of trying to predict
winners, it asks a narrower and more answerable question: **are we consistently getting
better prices than the market closes at?** That signal — Closing Line Value — is the most
reliable public evidence that a betting approach is genuinely sharp, and it shows up long
before the P&L variance washes out.

The engine polls live odds across many bookmakers, strips the vig from each market to
recover a fair "no-vig" probability, anchors to the sharpest available book (Pinnacle
first), and flags any book offering a price whose implied probability sits far enough
below that fair estimate to clear an edge threshold. Every flagged play is sized with a
fractional Kelly stake and logged to a trading journal with its entry price and edge. After
games start it captures the closing line and computes CLV; after they finish it settles the
trade into realized P&L.

Everything runs in **paper trading mode** first. The point is to validate — over a real
sample of CLV — that the edge is real *before* any capital is at risk. A single
`PAPER_TRADING_MODE` flag gates real execution; the backend refuses real-money trades while
it is on.

## Architecture

```
  The Odds API (v4)
        │  poll every N minutes (httpx + APScheduler)
        ▼
  Ingestion Service ──► PostgreSQL ◄── Analytics (no-vig · edge detection · CLV · Kelly)
   (odds_snapshots,         ▲                         │
    odds_lines,             │                         ▼
    closing_lines)          └──────────────────  FastAPI  (/api/*)
                                                     │  JSON
                                                     ▼
                                              React + Vite SPA
                                  (Dashboard · Opportunities · Trade Logger ·
                                   Journal · Analytics · Settings)
```

- **Backend:** Python 3.11 · FastAPI (async) · SQLAlchemy 2.0 async · Alembic · APScheduler
- **Frontend:** React 18 · TypeScript (strict) · Vite · Tailwind · Recharts · Zustand
- **Data:** PostgreSQL 15 in prod, in-memory SQLite for tests
- **Infra:** Docker Compose (postgres + backend + frontend)

## Quick Start

```bash
# First-time setup
cp backend/.env.example backend/.env
# Edit backend/.env — add ODDS_API_KEY and generate a SECRET_KEY (openssl rand -hex 32)

# Start everything
docker-compose up --build

# In a separate terminal — run migrations and seed demo data
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_demo_data.py
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

Without an `ODDS_API_KEY`, the backend runs in **fixture mode** in development — it serves
bundled sample odds so the whole stack works end-to-end without spending API credits.

### Local development without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .            # or: poetry install
alembic upgrade head
python scripts/seed_demo_data.py
uvicorn app.main:app --reload
pytest --cov=app/analytics --cov-report=term-missing   # 26 tests, 95% coverage

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev        # proxies /api to http://localhost:8000
```

## Key Concepts

### Closing Line Value (CLV)
`clv = (closing_decimal − entry_decimal) / entry_decimal × 100`. Positive CLV means we got
a better price than the market's closing line. A sustained average CLV above ~+1.5% over
50+ bets is the primary evidence the edge is real.

### No-Vig Probability
Bookmaker odds embed a margin. Convert each price to an implied probability, sum them
(>1 because of the vig), and normalize so they sum to 1.0. A −110/−110 market implies
52.38% each, normalizes to 50% each, and reveals a 4.76% vig.

### The Sharp Book Hierarchy
Not all books are equally efficient. We anchor our "true" probability to the sharpest book
available, in order: **Pinnacle → Betfair → Circa → Bookmaker → DraftKings → FanDuel →
BetMGM → Caesars.** If none are present we fall back to the consensus average of the rest.

### Kelly Criterion Sizing
`f* = (b·p − q) / b`, where `b = decimal − 1`, `p` is our probability, `q = 1 − p`. We stake
a fraction of full Kelly (quarter Kelly by default) and never stake into a non-positive
edge.

## Paper Trading First

`PAPER_TRADING_MODE=true` gates all real execution. The operator validates the edge against
real CLV while in a jurisdiction where betting isn't available, then flips the flag to
`false` only when deploying real capital from a legal jurisdiction. The backend rejects any
`real` trade while paper mode is on.

## Getting an Odds API Key

Sign up at [the-odds-api.com](https://the-odds-api.com). The free tier includes a monthly
credit allotment; each odds request costs credits proportional to the number of markets and
bookmakers requested. Every request is logged to `api_usage_log` and surfaced in the
Settings page and Dashboard credits widget.

## Project Structure

```
backend/
  app/
    analytics/   no_vig · edge_detection · clv        (the core, unit-tested)
    api/         odds · trades · analytics · system   (FastAPI routers under /api)
    db/          base (async engine) · models         (8 SQLAlchemy models)
    schemas/     Pydantic request/response models
    services/    odds_ingestion · results
    main.py      app factory · lifespan · scheduler · middleware
  alembic/       migrations
  scripts/       seed_demo_data.py
  tests/         analytics tests + fixtures

frontend/
  src/
    api/         client.ts   (the only place fetch is called)
    types/       interfaces mirroring backend schemas
    hooks/       one per data domain (useOpportunities, useTrades, …)
    store/       Zustand settings store (localStorage)
    components/  StatCard · Badge · DataTable · charts primitives · Layout
    pages/       Dashboard · Opportunities · TradeLogger · TradeJournal · Analytics · Settings
```

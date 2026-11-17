# Bettor

A paper-trading system for sports betting, judged on closing line value (CLV) instead of win rate.

Win/loss records take hundreds of bets to separate skill from luck. CLV shows up much sooner: if the prices you bet keep beating the price the market closes at, you are probably finding real edges. Bettor is built around measuring that.

It polls odds from many sportsbooks and removes each book's margin to get a fair probability, anchored to the sharpest book available. It flags prices that beat that fair line by more than a threshold, sizes them with fractional Kelly, and logs them to a journal. After kickoff it records the closing line and computes CLV for each bet; after the game it settles the result.

Everything runs in paper mode. While `PAPER_TRADING_MODE` is on, the backend rejects any trade marked as real money.

## Architecture

```
The Odds API (v4)
      │  polled on a schedule (httpx + APScheduler)
      ▼
Ingestion ──► PostgreSQL ◄── Analytics: no-vig, edge detection, CLV, Kelly
(odds snapshots,    ▲                    │
 lines, closings)   └──────────── FastAPI (/api/*)
                                         │
                                         ▼
                                React + TypeScript SPA
```

| Layer | Stack |
|---|---|
| Backend | Python 3.11, FastAPI (async), SQLAlchemy 2.0, Alembic, APScheduler |
| Frontend | React 18, TypeScript (strict), Vite, Tailwind, Recharts, Zustand |
| Data | PostgreSQL 15; in-memory SQLite in tests |
| Infra | Docker Compose (Postgres, backend, frontend) |

The analytics core (`backend/app/analytics/`) has 26 unit tests at 95% coverage.

## How the numbers work

**No-vig probability.** Convert each side's odds to an implied probability. The sum comes out above 1 because of the book's margin; dividing each side by that sum removes the margin. For example, −110/−110 implies 52.38% per side and 4.76% total margin, so the fair line is 50/50.

**Which book defines "fair."** The fair price comes from the sharpest book quoting the market, in this order: Pinnacle, Betfair, Circa, Bookmaker, DraftKings, FanDuel, BetMGM, Caesars. If none of these quote it, the fair price is a consensus average of the other books.

**Edge.** Fair probability minus the implied probability of the price being offered. Bets are flagged only above a configurable threshold.

**Kelly sizing.** `f* = (b·p − q) / b`, with `b` = decimal odds − 1, `p` = fair win probability and `q = 1 − p`. Bettor stakes quarter Kelly by default and never stakes when the edge is zero or negative.

**CLV.** `(closing_decimal − entry_decimal) / entry_decimal × 100`. Positive means you beat the close.

## The app

Six pages:
- **Dashboard:** live opportunities, P&L, bankroll, and API credits used.
- **Opportunities:** a sortable table with book-by-book price comparison.
- **Trade Logger:** a form pre-filled from an opportunity, with a suggested Kelly stake.
- **Journal:** filterable trade history with CSV export.
- **Analytics:** equity curve, CLV histogram, edge vs. P&L, P&L by sport, rolling win rate, and CLV by bookmaker.
- **Settings.**

Every Odds API request is logged so you can see where credits are going.

## Running it

```bash
cp backend/.env.example backend/.env    # add ODDS_API_KEY and a SECRET_KEY (openssl rand -hex 32)
docker-compose up --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_demo_data.py
```

Once it's up:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Without an `ODDS_API_KEY`, the backend serves a bundled sample odds response, so the whole stack runs without spending API credits.

Without Docker:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e . && alembic upgrade head && python scripts/seed_demo_data.py
uvicorn app.main:app --reload
pytest --cov=app/analytics

cd ../frontend && pnpm install && pnpm dev   # proxies /api to :8000
```

## Layout

```
backend/app/
  analytics/   no_vig, edge_detection, clv (unit-tested core)
  api/         odds, trades, analytics, system routers
  db/          async engine and 8 SQLAlchemy models
  schemas/     Pydantic request/response models
  services/    odds ingestion, result settlement
frontend/src/
  api/ hooks/ store/ components/ pages/
```

## Status

Built as a paper-trading tool. It has not been run long enough to say whether its edges are real; that is what the CLV tracking is for.

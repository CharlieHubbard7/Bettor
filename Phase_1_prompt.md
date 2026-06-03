# Phase 1 — Infrastructure, Analytics Core, and Seeded Backend

## Context

Read `CLAUDE.md` fully before starting. Everything in this prompt derives from it.
This is a personal sports betting edge-finding system called **Bettor**. We are building in phases.
Phase 1 delivers a fully working backend with real analytics, a seeded database, and a running API.
The frontend comes in Phase 2.

---

## What Phase 1 Covers (Steps 1–7)

1. Repo scaffold and git init
2. Docker Compose + PostgreSQL
3. SQLAlchemy models + Alembic initial migration
4. Core analytics modules + tests
5. Odds ingestion service (with fixture/mock data)
6. FastAPI routes (returning real data from DB)
7. Seed script — 100 realistic historical trades

Do not start on the React frontend. Stop cleanly after step 7 and output the Session Summary described in `CLAUDE.md`.

---

## Step 1 — Repo Scaffold

Create the full directory structure from `CLAUDE.md` (the "Repo Structure" section).
Create all `__init__.py` files. Create placeholder files with a single docstring comment so the
structure is navigable. Do not fill in logic yet — that comes per-step below.

Initialize git:
```bash
git init
git checkout -b main
```

Create `.gitignore` covering: Python (`__pycache__`, `.venv`, `*.pyc`, `.env`, `*.egg-info`),
Node (`node_modules`, `dist`, `.pnpm-store`), Docker (`postgres_data/`), IDE (`.idea`, `.vscode`),
and OS (`.DS_Store`).

Create `backend/pyproject.toml` with Poetry. Required dependencies:
```
fastapi = "^0.111"
uvicorn = {extras = ["standard"], version = "^0.30"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
alembic = "^1.13"
asyncpg = "^0.29"
aiosqlite = "^0.20"
httpx = "^0.27"
pydantic = "^2.7"
pydantic-settings = "^2.2"
loguru = "^0.7"
apscheduler = "^3.10"
pandas = "^2.2"
polars = "^0.20"

[dev]
pytest = "^8.2"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
```

Create `frontend/package.json` for pnpm with:
- react 18, react-dom, react-router-dom v6
- typescript, vite, @vitejs/plugin-react
- tailwindcss, autoprefixer, postcss
- recharts, zustand
- @types/react, @types/react-dom

---

## Step 2 — Docker Compose

Create `docker-compose.yml` at repo root. Spec:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: bettor
      POSTGRES_PASSWORD: bettor
      POSTGRES_DB: bettor
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bettor"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    volumes: ["./backend:/app"]
    env_file: ./backend/.env
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build: ./frontend
    command: pnpm dev --host
    ports: ["3000:3000"]
    volumes: ["./frontend:/app", "/app/node_modules"]

volumes:
  postgres_data:

networks:
  default:
    name: bettor-network
```

Create `backend/Dockerfile`:
- Base: `python:3.11-slim`
- Install Poetry, copy `pyproject.toml`, run `poetry install --no-root`
- Copy app code
- Expose 8000

Create `frontend/Dockerfile`:
- Base: `node:20-alpine`
- Install pnpm, copy `package.json`, run `pnpm install`
- Copy source
- Expose 3000

Create `backend/.env.example` exactly as specified in `CLAUDE.md`.

**Verification**: `docker-compose up postgres` should start and pass healthcheck.

---

## Step 3 — Database Models + Migrations

### `app/db/base.py`
Create async SQLAlchemy engine and `AsyncSession` factory:
```python
# Use create_async_engine with DATABASE_URL from settings
# Use async_sessionmaker
# Expose: engine, AsyncSessionLocal, get_db (FastAPI dependency)
```

### `app/db/models.py`
Implement all models from the "Database Models" section of `CLAUDE.md`.
Use `mapped_column` and `Mapped` (SQLAlchemy 2.0 style).
All UUID primary keys use `uuid.uuid4` as default.
All `DateTime` columns store UTC — use `datetime.utcnow` as server default.
Add `__repr__` to every model.

Enums to define as Python `enum.Enum`:
- `TradeType`: `paper`, `real`
- `TradeStatus`: `open`, `settled`, `void`
- `TradeResult`: `win`, `loss`, `push`

### Alembic Setup
Run `alembic init alembic` inside backend.
Configure `alembic.ini` and `alembic/env.py` to use `DATABASE_URL` from settings and import all models.
Generate initial migration: `alembic revision --autogenerate -m "initial schema"`.
Review the generated file and confirm all tables are present.

**Verification**: `alembic upgrade head` creates all tables. `psql` into the container and `\dt` shows all tables.

---

## Step 4 — Core Analytics Modules + Tests

This step is the most important. Build these with production rigor.

### `app/analytics/no_vig.py`

```python
def american_to_decimal(american: int) -> float: ...
def decimal_to_american(decimal: float) -> int: ...
def implied_probability(decimal_odds: float) -> float: ...

@dataclass
class NoVigResult:
    outcome_probs: dict[str, float]   # outcome_name → no-vig probability
    vig_pct: float
    fair_decimal_odds: dict[str, float]

def calculate_no_vig(outcomes: dict[str, float]) -> NoVigResult:
    """
    outcomes: dict of outcome_name → decimal_odds
    Returns no-vig probabilities, vig%, and fair odds for each outcome.
    """
```

### `app/analytics/edge_detection.py`

```python
SHARP_HIERARCHY: list[str] = [...]  # from CLAUDE.md

@dataclass
class EdgeOpportunity:
    event_id: str
    market_key: str
    outcome_name: str
    player_name: str | None
    our_prob: float
    book_implied_prob: float
    edge_pct: float
    best_book: str
    best_price_american: int
    best_price_decimal: float
    sharp_anchor_book: str
    kelly_fraction: float
    recommended_stake_units: float

def select_sharp_anchor(available_books: list[str]) -> str | None:
    """Return the sharpest book from SHARP_HIERARCHY that is in available_books."""

def calculate_kelly(
    our_prob: float,
    decimal_odds: float,
    kelly_fraction: float = 0.25,
) -> float:
    """Return fractional Kelly stake. Returns 0.0 if edge is negative."""

def find_edges(
    event_id: str,
    lines: list[OddsLineData],
    edge_threshold: float = 0.02,
    kelly_fraction: float = 0.25,
) -> list[EdgeOpportunity]:
    """
    Core edge detection function.
    1. Group lines by bookmaker
    2. Find sharp anchor using SHARP_HIERARCHY
    3. Compute no-vig prob from anchor
    4. Compare each book's raw implied prob against sharp no-vig prob
    5. Flag where edge > threshold
    """
```

### `app/analytics/clv.py`

```python
def calculate_clv(
    entry_price_decimal: float,
    closing_price_decimal: float,
) -> float:
    """CLV as a percentage. Positive = we got better than closing price."""

def aggregate_clv_stats(clv_values: list[float]) -> dict:
    """Return mean, median, std_dev, pct_positive, sample_size."""
```

### Tests (`backend/tests/`)

`conftest.py`: define fixtures for sample odds data, a set of bookmaker lines, etc.

`test_no_vig.py` — required test cases:
- `-110/-110` → implied 52.38% each, no-vig 50% each, vig 4.76%
- `-150/+130` → correct no-vig probabilities (verify by hand)
- Three-way market (soccer 1X2) → probabilities sum to 1.0
- `american_to_decimal` round-trips for both positive and negative lines
- Single-outcome market raises an error (can't strip vig with 1 outcome)

`test_edge_detection.py` — required test cases:
- Pinnacle present → used as anchor
- Pinnacle absent, betfair present → betfair used
- All sharp books absent → falls back to average of remaining books
- Positive edge → `EdgeOpportunity` returned
- Edge below threshold → nothing returned
- Negative edge → Kelly returns `0.0`
- Zero edge → Kelly returns `0.0`
- Quarter Kelly of a 5% edge at +100 → correct fractional stake

`test_clv.py` — required test cases:
- Entry 1.91, closing 1.83 → negative CLV (line moved against us)
- Entry 1.91, closing 2.00 → positive CLV (got better than closing)
- Entry == closing → 0.0 CLV
- `aggregate_clv_stats` on a known list → correct mean and pct_positive

Run `pytest --cov=app/analytics --cov-report=term-missing` and confirm 80%+ coverage before moving on.

---

## Step 5 — Odds Ingestion Service

### `app/services/odds_ingestion.py`

Build a class `OddsIngestionService` with:

```python
class OddsIngestionService:
    def __init__(self, session: AsyncSession, settings: Settings): ...

    async def poll_sport(self, sport_key: str) -> None:
        """
        Fetch odds for all events in a sport.
        1. Call The Odds API /v4/sports/{sport}/odds
        2. Save raw response to odds_snapshots (append-only)
        3. Parse each bookmaker/market/outcome into odds_lines rows
        4. Log credits used to api_usage_log
        5. Handle 429 with exponential backoff (max 5 retries, start 1s)
        """

    async def poll_all_active_sports(self) -> None:
        """Poll all sports where active=True in the sports table."""

    async def mark_closing_lines(self) -> None:
        """
        For any event where commence_time has passed:
        Find the last odds_line snapshot per event/market/bookmaker/outcome
        and set is_closing_line=True.
        """

    async def fetch_and_store_sports(self) -> None:
        """Sync the sports table from /v4/sports."""
```

**In development (ENVIRONMENT=development)**, if `ODDS_API_KEY` is not set or is the placeholder,
load fixture data from `backend/tests/fixtures/sample_odds_response.json` instead of calling the API.
This lets the full stack run without burning API credits during development.

Create `backend/tests/fixtures/sample_odds_response.json` — a realistic mock response for 2–3 NFL games
with at least Pinnacle, DraftKings, FanDuel, and BetMGM lines for h2h and spreads markets.

### APScheduler setup in `app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start AsyncIOScheduler
    # Add job: poll_all_active_sports every POLL_INTERVAL_MINUTES
    # Add job: mark_closing_lines every 15 minutes
    yield
    # Shutdown scheduler
```

---

## Step 6 — FastAPI Routes

### `app/main.py`
- FastAPI app with lifespan
- Mount `api/router.py` at `/api`
- CORS: allow all origins in development, lock down in production
- Add request logging middleware (log method, path, status, duration)
- Health check: `GET /health` → `{"status": "ok", "environment": "development"}`

### `app/schemas/` — Pydantic v2 models

Build full request/response schemas for all endpoints. Key ones:
- `OddsLineResponse` — mirrors the `odds_lines` table
- `EdgeOpportunityResponse` — mirrors `EdgeOpportunity` dataclass
- `TradeCreate` — for POST /trades
- `TradeResponse` — full trade record
- `CLVStats` — summary stats
- `PnLSummary` — equity curve data points + summary
- `BankrollSnapshot`
- `ApiUsageSummary`

### Implement all endpoints from the "API Endpoint Map" in `CLAUDE.md`

For each endpoint:
- Use `Depends(get_db)` for the session
- Use `Depends(get_settings)` for config
- Return typed Pydantic response models
- Log significant actions with `logger.info()`
- Wrap multi-step DB operations in explicit transactions

Key endpoint logic:
- `GET /api/opportunities` — query latest odds_lines snapshot, run `find_edges()`, return ranked list
- `POST /api/trades` — validate the trade, compute Kelly, insert to DB
- `GET /api/analytics/pnl` — aggregate `profit_loss_units` from settled trades, build equity curve data

**Verification**: `uvicorn app.main:app --reload` starts. `GET /health` returns 200. `GET /api/opportunities` returns an empty list (not an error). All routes appear in `http://localhost:8000/docs`.

---

## Step 7 — Seed Script

### `scripts/seed_demo_data.py`

Standalone script (not a FastAPI route). Run with `python scripts/seed_demo_data.py`.
Uses `asyncio.run()` with a direct `AsyncSession`.

Produce exactly:
- 100 `Trade` records
  - 55 wins, 45 losses (55% win rate)
  - CLV values: normally distributed around +1.8%, std dev 3%
  - Spread across: ~40% NFL, ~35% NBA, ~25% MLB
  - Markets: ~30% player props, ~40% spreads, ~30% h2h
  - Bookmakers: DraftKings, FanDuel, BetMGM, Caesars, Pinnacle, Bookmaker
  - Dates: last 90 days, roughly 1–2 trades per day
  - Edge pct: normally distributed around 3.2%, std dev 1.5%
  - Entry prices: realistic American odds between -160 and +180
  - All `trade_type = paper`, `status = settled`

- 90 `BankrollSnapshot` records (one per day, last 90 days)
  - Start at $1,000. Build a realistic equity curve with variance.
  - Use a random walk with slight positive drift (matching 55% win rate)
  - End somewhere between $1,100 and $1,400 (realistic for 100 paper trades)

- Insert the sports (NFL, NBA, MLB) into the `sports` table with `active=True`
- Insert ~20 representative `Event` records (completed, with scores)

Print a summary on completion:
```
Seeded 100 trades: 55 wins / 45 losses
Avg CLV: +1.82%
Final bankroll: $1,247.00
Sports: NFL (40), NBA (35), MLB (25)
```

**Verification**: Run the script, then `GET /api/analytics/pnl` returns a real equity curve.
`GET /api/trades` returns 100 trades. Dashboard will have real data to display in Phase 2.

---

## End of Phase 1

When all 7 steps are complete and verified:

1. Commit everything: `git add -A && git commit -m "feat: phase 1 complete — backend, analytics, seeded DB"`
2. Create `develop` branch: `git checkout -b develop`
3. Output the Session Summary as specified in `CLAUDE.md` and append it to `SESSIONS.md`

The Phase 2 prompt picks up from here and builds the entire React frontend against this live API.
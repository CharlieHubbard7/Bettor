This file is the single source of truth for every Claude Code session working on this project.
Read it fully before writing a single line of code. Every architectural decision is documented here.
Do not deviate from the patterns established in this file without explicitly flagging the deviation and explaining why.

What This Project Does
Bettor is a systematic sports betting edge-finding system built for paper trading and eventual real-money deployment.
The core loop:

Poll live odds from The Odds API (v4) across multiple bookmakers every 5 minutes
Strip vig and compute true implied probabilities (no-vig model)
Anchor to sharp book consensus (Pinnacle-first hierarchy)
Flag lines where our edge over a book exceeds a configurable threshold (default 2%)
Log every "trade" with entry price, edge%, and Kelly-sized stake
After games start, compute Closing Line Value (CLV) — the primary signal of whether we are sharp
After games end, settle trades with real P&L
Visualize everything: equity curve, CLV distribution, edge vs. ROI correlation

The deployment context: Currently paper trading only (operator is in Texas, where sports betting is illegal). A PAPER_TRADING_MODE environment flag gates real execution. Real deployment happens from Pennsylvania (CMU).

Repo Structure
Bettor/
├── CLAUDE.md                  ← you are here
├── README.md
├── docker-compose.yml
├── .gitignore
│
├── backend/
│   ├── pyproject.toml         ← Poetry-managed dependencies
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/          ← migration files, never edit manually
│   │
│   ├── app/
│   │   ├── main.py            ← FastAPI app factory, lifespan, middleware
│   │   ├── config.py          ← all settings via pydantic-settings, reads from .env
│   │   ├── dependencies.py    ← FastAPI dependency injection (db session, current user)
│   │   │
│   │   ├── db/
│   │   │   ├── base.py        ← SQLAlchemy async engine + session factory
│   │   │   └── models.py      ← ALL SQLAlchemy ORM models in one file
│   │   │
│   │   ├── schemas/           ← Pydantic v2 request/response models, one file per domain
│   │   │   ├── odds.py
│   │   │   ├── trades.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py      ← mounts all sub-routers
│   │   │   ├── odds.py
│   │   │   ├── trades.py
│   │   │   ├── analytics.py
│   │   │   └── system.py
│   │   │
│   │   ├── analytics/
│   │   │   ├── no_vig.py      ← vig stripping and true probability calculation
│   │   │   ├── edge_detection.py  ← sharp consensus + edge flagging
│   │   │   └── clv.py         ← closing line value computation
│   │   │
│   │   └── services/
│   │       ├── odds_ingestion.py  ← The Odds API polling service
│   │       └── results.py         ← game results fetcher + trade settler
│   │
│   ├── scripts/
│   │   └── seed_demo_data.py  ← populates DB with 100 realistic historical trades
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_no_vig.py
│       ├── test_edge_detection.py
│       └── test_clv.py
│
└── frontend/
    ├── package.json           ← pnpm-managed
    ├── vite.config.ts
    ├── tsconfig.json          ← strict mode enabled
    ├── tailwind.config.ts
    │
    └── src/
        ├── main.tsx
        ├── App.tsx            ← router setup
        ├── api/               ← all fetch calls, typed with the backend schemas
        │   └── client.ts
        ├── components/        ← reusable UI primitives
        ├── pages/             ← one folder per route
        │   ├── Dashboard/
        │   ├── Opportunities/
        │   ├── Trades/
        │   ├── Analytics/
        │   └── Settings/
        ├── hooks/             ← custom hooks: useOpportunities, useTrades, usePnl, etc.
        ├── store/             ← Zustand stores (settings, bankroll state)
        └── types/             ← TypeScript interfaces mirroring backend Pydantic schemas

Tech Stack — Do Not Deviate
LayerTechnologyNotesBackend languagePython 3.11+Use match statements, TypeAlias, modern typingWeb frameworkFastAPIAsync endpoints only. No sync route handlers.ORMSQLAlchemy 2.0 asyncUse AsyncSession, select() syntax, not legacy query()MigrationsAlembicAuto-generate then review. Never hand-edit version files.Database (prod)PostgreSQL 15Via Docker ComposeDatabase (tests)SQLite (async)In-memory, via aiosqliteTask schedulingAPSchedulerAsyncIOScheduler, not BackgroundSchedulerHTTP clienthttpxAsync client only. No requests.Data manipulationPandas + PolarsPandas for general wrangling, Polars for performance-critical pathsConfig managementpydantic-settingsAll env vars typed and validated at startupLoggingloguruStructured JSON in production, pretty in devPython packagingPoetrypyproject.toml only. No requirements.txt.Frontend frameworkReact 18Functional components only. No class components.Frontend languageTypeScriptstrict: true. Zero any types.Build toolViteStylingTailwind CSSDark theme by default. Use CSS variables for theme tokens.ChartsRechartsFor all data visualizationsState managementZustandFor global app state (settings, paper mode toggle)Node package managerpnpmNever npm or yarnAuthJWT (single-user)Simple — this is a personal toolContainerizationDocker Composepostgres + backend + frontend, all networked

Database Models
All models live in app/db/models.py. This is the canonical schema — all migrations derive from it.
sports
ColumnTypeNotessport_keyString PKe.g. americanfootball_nfltitleStringHuman-readableactiveBooleanWhether we are tracking this sportlast_updatedDateTime
events
ColumnTypeNotesidString PKFrom The Odds APIsport_keyString FK → sportscommence_timeDateTimeUTChome_teamStringaway_teamStringcompletedBooleanDefault Falsehome_scoreIntegerNullableaway_scoreIntegerNullable
odds_snapshots
Append-only raw blob storage. Never mutate rows.
ColumnTypeNotesidUUID PKevent_idString FK → eventsraw_jsonJSONFull API responsesnapshot_timeDateTimeUTCcredits_usedIntegercredits_remainingInteger
odds_lines
Normalized, queryable odds data parsed from snapshots.
ColumnTypeNotesidUUID PKsnapshot_idUUID FK → odds_snapshotsevent_idString FK → eventssport_keyStringcommence_timeDateTimehome_teamStringaway_teamStringbookmaker_keyStringe.g. pinnacle, draftkingsmarket_keyStringe.g. h2h, spreads, totals, player_pointsoutcome_nameStringTeam name or player name + over/underprice_americanIntegere.g. -110, +150price_decimalFloate.g. 1.909, 2.5pointFloatNullable — for spreads, totals, propsplayer_nameStringNullable — for player props onlysnapshot_timestampDateTimeis_closing_lineBooleanDefault False, set retroactively
closing_lines
The final odds_line snapshot before game commence_time, per event/market/bookmaker/outcome.
trades
The core trading journal.
ColumnTypeNotesidUUID PKevent_idString FK → eventsmarket_keyStringoutcome_nameStringplayer_nameStringNullableentry_price_americanIntegerentry_price_decimalFloatour_probFloatOur model's true probabilitysharp_consensus_probFloatPinnacle/sharp anchor at time of tradeedge_pctFloatour_prob - book_implied_probkelly_fractionFloatFull Kelly fractionstake_unitsFloatQuarter Kelly defaultstake_dollarsFloatNullablebookmakerStringWhere we'd place ittrade_typeEnumpaper | realstatusEnumopen | settled | voidresultEnumwin | loss | push | nullclosing_price_americanIntegerNullable, filled post-game-startclvFloatNullable, filled post-game-startprofit_loss_unitsFloatNullable, filled post-settlementprofit_loss_dollarsFloatNullable, filled post-settlementcreated_atDateTimesettled_atDateTimeNullablenotesTextNullable
bankroll_snapshots
ColumnTypeNotesidUUID PKdateDateUniquestarting_bankrollFloatending_bankrollFloattrades_countIntegerunits_wonFloatunits_lostFloatroi_pctFloatcumulative_roi_pctFloat
api_usage_log
ColumnTypeNotesidUUID PKendpointStringsport_keyStringNullablecredits_usedIntegercredits_remainingIntegerresponse_statusIntegerHTTP statuscalled_atDateTime

Core Analytics — The Heart of This System
Sharp Book Hierarchy
Used in edge_detection.py to select the consensus anchor. Always use the sharpest available book.
pythonSHARP_HIERARCHY = [
    "pinnacle",
    "betfair",
    "circa",
    "bookmaker",
    "draftkings",
    "fanduel",
    "betmgm",
    "caesars",
]
No-Vig Calculation (no_vig.py)
implied_prob = 1 / decimal_odds
no_vig_prob = implied_prob / sum(all implied_probs in market)
vig_pct = (sum(implied_probs) - 1) * 100
fair_decimal_odds = 1 / no_vig_prob

Always operate on decimal odds internally. Convert American ↔ decimal at the boundaries.
A -110/-110 market has implied probs of 0.5238 each. No-vig = 0.5 each. Vig = 4.76%.

Edge Detection (edge_detection.py)
sharp_prob = no_vig_prob of the sharp anchor book
book_implied_prob = 1 / book_decimal_odds  (raw, not no-vig)
edge_pct = sharp_prob - book_implied_prob
flag if edge_pct > EDGE_THRESHOLD (default 0.02)
Kelly Sizing (edge_detection.py)
b = decimal_odds - 1
p = our_prob (sharp consensus no-vig)
q = 1 - p
full_kelly = (b * p - q) / b
stake = full_kelly * KELLY_FRACTION  (default 0.25 = quarter Kelly)
stake = max(0, stake)  # never bet negative edge
CLV (clv.py)
clv = (closing_price_decimal - entry_price_decimal) / entry_price_decimal * 100
Positive CLV = we got better odds than the market settled on = we are sharp.
Target: avg CLV > +1.5% over any 50+ trade sample.

API Reference — The Odds API v4
Base URL: https://api.the-odds-api.com
Key endpoints used:

GET /v4/sports — list sports (uses 1 credit)
GET /v4/sports/{sport}/odds — odds for all events in a sport (credits vary by bookmaker count)
GET /v4/sports/{sport}/events/{eventId}/odds — odds for one event
GET /v4/sports/{sport}/scores — completed game scores (1 credit)

Key parameters:

apiKey — from settings, never hardcoded
regions=us — always for US books
markets=h2h,spreads,totals or player_points,player_rebounds etc.
bookmakers=pinnacle,draftkings,fanduel,... — comma-separated
oddsFormat=american or decimal — use decimal internally

Rate limiting: Exponential backoff starting at 1s, max 5 retries. Log every 429.
Credit budget: Log every request in api_usage_log. Surface remaining credits prominently in the UI.

Environment Variables
All variables are typed in app/config.py via pydantic-settings. The .env.example is the source of truth.
ODDS_API_KEY=                   # required — The Odds API key
DATABASE_URL=postgresql+asyncpg://bettor:bettor@localhost:5432/bettor
SECRET_KEY=                     # required — JWT signing key, generate with openssl rand -hex 32
PAPER_TRADING_MODE=true         # gates real execution
ACTIVE_BANKROLL=1000            # in dollars
DEFAULT_KELLY_FRACTION=0.25     # quarter Kelly
EDGE_THRESHOLD=0.02             # 2% minimum edge to flag
POLL_INTERVAL_MINUTES=5
LOG_LEVEL=INFO
ENVIRONMENT=development         # development | production

API Endpoint Map
All routes are prefixed with /api.
MethodPathDescriptionGET/sportsList active sportsGET/eventsUpcoming events (filter: sport, date)GET/odds/{event_id}All current odds + edge calcs for one eventGET/opportunitiesAll current +EV plays above thresholdPOST/tradesLog a new tradeGET/tradesList trades (filter: sport, status, date range, type)PUT/trades/{id}Update trade (notes, void)GET/analytics/clvCLV summary statsGET/analytics/pnlP&L summary + equity curve dataGET/analytics/edgeEdge detection analyticsGET/analytics/bankrollBankroll historyGET/system/creditsAPI usage dashboardPOST/system/pollManually trigger odds poll

Frontend Pages
RouteComponentPurpose/DashboardCommand center: live opps feed, P&L summary, credits widget/opportunitiesOpportunitiesFull filterable +EV table with per-row expansion/trades/newTradeLoggerLog a trade (pre-filled from opportunity click)/tradesTradeJournalFull trade history, filters, CSV export/analyticsAnalyticsEquity curve, CLV histogram, edge vs ROI scatter/settingsSettingsAPI key, sports, thresholds, bankroll, paper mode
Design language: Dark theme. Data-dense. Bloomberg Terminal aesthetic — this is an operator's tool, not a marketing site. Use zinc-900 background, zinc-800 cards, emerald-400 for positive values, red-400 for negative, amber-400 for warnings/neutral edges.

Code Conventions
Python

Type hints on every function signature — parameters and return values
Docstrings on every class and every public method (Google style)
No bare except: — always catch specific exceptions
No magic numbers — all constants in config.py or module-level SCREAMING_SNAKE_CASE
Use loguru for all logging: from loguru import logger
Async all the way: async def for all route handlers, service methods, and DB calls
Use AsyncSession from SQLAlchemy, never sync session
Pydantic v2 for all schemas — use model_validator, field_validator, not v1 @validator

TypeScript / React

strict: true in tsconfig — zero any types
Functional components only
One custom hook per data domain: useOpportunities, useTrades, usePnl, etc.
All API types live in src/types/ and mirror the backend Pydantic schemas exactly
All fetch logic lives in src/api/client.ts — pages never call fetch directly
Zustand for global state (settings store, paper mode toggle)
No prop drilling beyond 2 levels — use context or store

Git

Branch: main (stable) and develop (active work)
Commit message format: type(scope): description — e.g. feat(analytics): add CLV calculator
Never commit .env files — .gitignore covers them


Testing
Tests live in backend/tests/. Run with pytest from the backend/ directory.
Target: 80%+ coverage on all analytics modules (no_vig.py, edge_detection.py, clv.py).
Key test cases that must exist:

-110/-110 market → 52.38% implied each, 50% no-vig each, 4.76% vig
-150/+130 market → correct no-vig probabilities
Edge detection with Pinnacle available vs. fallback hierarchy
Kelly sizing with positive edge, zero edge, and negative edge (must return 0)
CLV calculation: positive CLV (got better than closing), negative CLV, push (same price)
Sharp hierarchy fallback: Pinnacle absent → betfair, betfair absent → circa, etc.

Use pytest-asyncio for any async test. Use in-memory SQLite (aiosqlite) for DB-touching tests — never the real Postgres instance.

Docker Compose Services
postgres   → port 5432, persistent volume at ./postgres_data
backend    → port 8000, hot reload via uvicorn --reload, mounts ./backend
frontend   → port 3000, Vite dev server, mounts ./frontend
All services on a shared bettor-network bridge network.
Backend connects to postgres via service name: postgresql+asyncpg://bettor:bettor@postgres:5432/bettor

Seed Data Spec
scripts/seed_demo_data.py must produce:

100 historical trades, mix of paper type
55% win rate (realistic for +EV model)
Average CLV of +1.8%
Mix: ~40% NFL, ~35% NBA, ~25% MLB
Mix: ~30% player props, ~40% spreads, ~30% h2h
Equity curve with realistic variance — not a straight line
Bankroll snapshots for the last 90 days
Trades spread across at least 6 different bookmakers


Known Future Work (Do Not Build Yet)

Real-money execution layer (blocked on Texas → Pennsylvania move)
Betfair Exchange integration for laying bets
Machine learning model for probability estimation (beyond no-vig)
Discord/Telegram alerts for new opportunities
Mobile PWA
Multi-user support

When Claude Code sessions address these, check this file first. Do not add them until explicitly instructed.

How to Run Locally
bash# First time setup
cp backend/.env.example backend/.env
# Edit backend/.env — add ODDS_API_KEY and generate a SECRET_KEY

# Start everything
docker-compose up --build

# In a separate terminal — run migrations and seed
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_demo_data.py

# Access
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API docs:  http://localhost:8000/docs

Session Handoff Protocol
At the end of every Claude Code session, output a short summary in this format:
## Session Summary — [date]
### Completed
- [list what was built/changed]
### Current State
- [what is working, what is broken]
### Next Session Should Start With
- [exact first task]
### Open Questions
- [anything unresolved]
This summary should be appended to a SESSIONS.md file in the repo root so the next session can orient instantly.
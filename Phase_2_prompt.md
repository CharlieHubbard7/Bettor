# Phase 2 — React Frontend + Live Odds API Wiring

## Context

Read `CLAUDE.md` and `SESSIONS.md` fully before starting.
Phase 1 is complete: the backend is running, the database is seeded with 100 demo trades,
and all API endpoints are live at `http://localhost:8000`.

Phase 2 delivers the full React frontend wired to the live backend, plus real Odds API integration
replacing the fixture mocks from Phase 1.

---

## What Phase 2 Covers (Steps 8–12)

8. React frontend scaffold (Vite + TypeScript + Tailwind)
9. All 6 pages built and wired to the backend API
10. Real Odds API calls wired in (replacing dev fixtures)
11. End-to-end smoke test
12. README + final commit

Do not modify any backend analytics logic. If you discover a bug in Phase 1 code while building the
frontend, fix it with a targeted commit and note it in `SESSIONS.md`.

---

## Step 8 — Frontend Scaffold

### Project setup

In `frontend/`:
```bash
pnpm install
```

Configure:
- `vite.config.ts`: proxy `/api` to `http://localhost:8000` so no CORS issues in dev
- `tsconfig.json`: `strict: true`, `paths` alias `@/*` → `./src/*`
- `tailwind.config.ts`: enable dark mode via `class`, extend theme with the color tokens below
- `postcss.config.js`: tailwind + autoprefixer

**Color tokens** (add to tailwind theme extend):
```ts
colors: {
  surface: {
    DEFAULT: '#18181b',  // zinc-900 — page background
    card:    '#27272a',  // zinc-800 — card backgrounds
    border:  '#3f3f46',  // zinc-700 — borders
    muted:   '#52525b',  // zinc-600 — muted text
  },
  signal: {
    profit:  '#34d399',  // emerald-400
    loss:    '#f87171',  // red-400
    warn:    '#fbbf24',  // amber-400
    neutral: '#94a3b8',  // slate-400
  }
}
```

Set `<html class="dark">` in `index.html`. All backgrounds default to `surface.DEFAULT`.

### `src/api/client.ts`

Single file. All fetch calls live here — no page or hook ever calls `fetch` directly.

```typescript
const BASE_URL = '/api'

async function get<T>(path: string, params?: Record<string, string>): Promise<T>
async function post<T>(path: string, body: unknown): Promise<T>
async function put<T>(path: string, body: unknown): Promise<T>

// Named exports for every endpoint:
export const api = {
  sports:        { list: () => get<Sport[]>('/sports') },
  events:        { list: (params?) => get<Event[]>('/events', params) },
  opportunities: { list: (params?) => get<EdgeOpportunity[]>('/opportunities', params) },
  odds:          { byEvent: (id: string) => get<EventOdds>(`/odds/${id}`) },
  trades: {
    list:   (params?) => get<Trade[]>('/trades', params),
    create: (body: TradeCreate) => post<Trade>('/trades', body),
    update: (id: string, body: Partial<Trade>) => put<Trade>(`/trades/${id}`, body),
  },
  analytics: {
    clv:       () => get<CLVStats>('/analytics/clv'),
    pnl:       () => get<PnLSummary>('/analytics/pnl'),
    edge:      () => get<EdgeAnalytics>('/analytics/edge'),
    bankroll:  () => get<BankrollSnapshot[]>('/analytics/bankroll'),
  },
  system: {
    credits: () => get<ApiUsageSummary>('/system/credits'),
    poll:    () => post<{ message: string }>('/system/poll', {}),
  },
}
```

### `src/types/index.ts`

TypeScript interfaces matching every backend Pydantic response schema.
Key types:
```typescript
interface EdgeOpportunity {
  event_id: string
  market_key: string
  outcome_name: string
  player_name: string | null
  our_prob: number
  book_implied_prob: number
  edge_pct: number          // e.g. 0.034 = 3.4%
  best_book: string
  best_price_american: number
  best_price_decimal: number
  sharp_anchor_book: string
  kelly_fraction: number
  recommended_stake_units: number
}

interface Trade {
  id: string
  event_id: string
  market_key: string
  outcome_name: string
  player_name: string | null
  entry_price_american: number
  our_prob: number
  edge_pct: number
  stake_units: number
  stake_dollars: number | null
  bookmaker: string
  trade_type: 'paper' | 'real'
  status: 'open' | 'settled' | 'void'
  result: 'win' | 'loss' | 'push' | null
  clv: number | null
  profit_loss_units: number | null
  created_at: string
  settled_at: string | null
  notes: string | null
}

interface PnLSummary {
  equity_curve: { date: string; cumulative_units: number; cumulative_dollars: number }[]
  total_trades: number
  win_rate: number
  total_units: number
  total_dollars: number
  roi_pct: number
  avg_clv: number
}
```

### `src/hooks/`

One hook per data domain. Each hook:
- Uses `useState` + `useEffect` for fetching
- Exposes `data`, `loading`, `error`, `refetch`
- Auto-refetches on a configurable interval (opportunities: 60s, everything else: manual)

```
useOpportunities(filters?)  → EdgeOpportunity[]
useTrades(filters?)         → Trade[]
usePnl()                    → PnLSummary
useCLV()                    → CLVStats
useBankroll()               → BankrollSnapshot[]
useCredits()                → ApiUsageSummary
useSettings()               → Zustand store (read + write)
```

### `src/store/settingsStore.ts`

Zustand store persisted to localStorage:
```typescript
interface SettingsState {
  paperTradingMode: boolean
  activeBankroll: number
  edgeThreshold: number       // 0.02 default
  kellyFraction: number       // 0.25 default
  activeSports: string[]
  oddsApiKey: string          // stored locally for display; real key is in .env
  setPaperTradingMode: (v: boolean) => void
  setActiveBankroll: (v: number) => void
  // etc.
}
```

### Shared components to build first

Before any pages, build these reusable primitives in `src/components/`:

- `StatCard` — label + big number + optional delta indicator
- `Badge` — colored pill (used for win/loss/push, paper/real, sport labels)
- `DataTable` — generic sortable table with column config + optional row expansion
- `LoadingSpinner` — centered spinner
- `ErrorState` — error message with retry button
- `PageHeader` — title + optional subtitle + optional action button slot
- `Divider` — horizontal rule
- `PriceDisplay` — formats American odds: `+150` in emerald, `-110` in red-400
- `EdgeBadge` — shows edge% with color: emerald > 5%, amber 2–5%

---

## Step 9 — All Six Pages

Build pages in this order. Verify each one loads with real seeded data before moving on.

### Page 1: Dashboard (`/`)

Layout: 2-column on desktop, 1-column on mobile.

**Left column** (wider):
- `OpportunityFeed` component — live table of current +EV plays
  - Columns: Event, Market, Player, Edge%, Our Prob, Book Prob, Best Price, Best Book, Kelly%, Units
  - `EdgeBadge` on the Edge% column
  - `PriceDisplay` on Best Price
  - Clicking a row navigates to `/trades/new?opportunity={event_id}&...` with pre-filled params
  - Auto-refreshes every 60 seconds
  - Shows last-updated timestamp

**Right column** (narrower):
- `PnLWidget` — Today / This Week / All Time units and $ (3 `StatCard`s)
- `CreditsWidget` — remaining API credits with a progress bar, last poll time, manual poll button
- `BankrollWidget` — current bankroll, change today, small sparkline (last 7 days)

Empty state: if no opportunities, show a message with the last poll time and a "Poll Now" button.

---

### Page 2: Opportunities (`/opportunities`)

Full-page filterable table.

**Filter bar** (horizontal, above table):
- Sport: multi-select dropdown (NFL, NBA, MLB, or All)
- Market: multi-select (h2h, spreads, totals, player props, or All)
- Min Edge%: number input (default 2)
- Bookmaker: multi-select

**Table**: same columns as Dashboard OpportunityFeed, but with additional columns visible:
- Sharp Anchor Book
- Vig% (of the best book)
- Full Kelly (not just quarter)

**Row expansion** (click to expand inline, no modal):
- Full odds comparison grid: all bookmakers × outcomes for this event/market
- For each book: American odds, decimal odds, implied prob, delta from sharp anchor
- Highlight the best available price in emerald
- Small note showing which book is the sharp anchor

**Sorting**: default by edge% descending. All columns sortable.

---

### Page 3: Trade Logger (`/trades/new`)

Form to log a trade. Reads URL search params to pre-fill when arriving from an opportunity click.

**Fields**:
- Event (searchable dropdown, queries `/api/events`)
- Market (dropdown: h2h, spreads, totals, player props)
- Outcome / Player (conditional: player name input shown only for props)
- Entry Price (American odds input — validates format)
- Our Probability (auto-computed from entry price using no-vig, but editable)
- Bookmaker (dropdown of known books)
- Stake Units (number input)
- Stake Dollars (optional, computed from bankroll × stake units, editable)
- Paper / Real toggle (defaults to `PAPER_TRADING_MODE` from settings store)
- Notes (textarea, optional)

**Live Kelly suggestion**: As user fills in price and our_prob, compute and display:
- Full Kelly %
- Quarter Kelly % (recommended)
- Suggested units at current bankroll

**Submit**: POST to `/api/trades`. On success, navigate to `/trades` with a success toast.

---

### Page 4: Trade Journal (`/trades`)

Full trade history.

**Summary bar** (above table, always visible):
- Total Trades | Win Rate | Avg CLV | Total Units | Total $ | ROI%
- Use `StatCard` components, color-coded

**Filter bar**:
- Date range (start / end date pickers)
- Sport, Market, Status (open/settled/void), Type (paper/real), Result (win/loss/push)

**Table columns**:
Date | Event | Market | Outcome | Entry Price | Edge% | CLV | Stake | Result | P&L Units | P&L $ | Book | Notes

- `Badge` for result (win=emerald, loss=red, push=amber)
- `Badge` for trade_type (paper=zinc, real=blue)
- CLV colored: positive=emerald, negative=red, null=muted
- Click row to expand: show full trade details including sharp_consensus_prob, our_prob, timestamps

**Export button**: CSV download of filtered trades. Generate client-side from the fetched data.

**Pagination**: 25 trades per page.

---

### Page 5: Analytics (`/analytics`)

Six chart panels in a 2×3 grid layout on desktop, stacked on mobile.
All charts use Recharts. All have a title, subtitle, and loading/error state.

1. **Equity Curve** — `LineChart`, cumulative P&L units over time
   - X axis: date, Y axis: cumulative units
   - Reference line at 0
   - Tooltip showing date, cumulative units, cumulative $

2. **CLV Distribution** — `BarChart` histogram
   - X axis: CLV% buckets (-6%, -4%, -2%, 0%, +2%, +4%, +6%+)
   - Y axis: count of trades
   - Bars: emerald for positive buckets, red for negative
   - Annotation: mean CLV line

3. **Edge% vs Actual ROI** — `ScatterChart`
   - X axis: edge% at time of trade
   - Y axis: actual P&L units for that trade
   - Color dots by sport
   - Trendline (linear regression, computed client-side)
   - This is the key chart — does edge predict results?

4. **P&L by Category** — `BarChart` grouped
   - X axis: sport (NFL, NBA, MLB) and market type
   - Y axis: total units won/lost
   - Two bar groups: won vs lost

5. **Rolling Win Rate** — `LineChart`
   - 50-bet rolling window
   - Reference line at 50% and 55%
   - Shows variance around the win rate over time

6. **CLV by Bookmaker** — horizontal `BarChart`
   - X axis: avg CLV%, Y axis: bookmaker name
   - Shows which books have softest lines
   - Sort descending by avg CLV

---

### Page 6: Settings (`/settings`)

Two-column form layout. Settings persist via the Zustand store (localStorage).

**Section 1 — API Configuration**:
- Odds API Key (password input, shows last 4 chars, button to reveal)
- Current credit balance (fetched live from `/api/system/credits`)
- Polling interval (slider: 5–60 minutes)
- Active sports (checkbox list: NFL, NBA, MLB, NCAAB, NHL, Soccer)

**Section 2 — Trading Parameters**:
- Paper Trading Mode (large toggle — prominent, since this gates real money)
- Active Bankroll ($)
- Edge Threshold (slider: 1%–10%, default 2%)
- Kelly Fraction (slider: 0.1–1.0, default 0.25, labels: "Quarter Kelly" at 0.25, "Half Kelly" at 0.5, "Full Kelly" at 1.0)

**Section 3 — System**:
- Manual poll button ("Poll Odds Now")
- Database stats (total trades, events tracked, snapshots stored — fetched from a `/api/system/stats` endpoint, add this if it doesn't exist)
- "Seed Demo Data" button (calls a POST endpoint — useful for resetting; add `POST /api/system/seed` endpoint that runs the seed script logic)

---

### App-level layout

`App.tsx`:
- React Router v6 with `createBrowserRouter`
- Persistent sidebar on desktop, bottom nav on mobile
- Sidebar items: Dashboard, Opportunities, Trade Logger, Trade Journal, Analytics, Settings
- Paper Trading Mode indicator in the sidebar (prominent amber badge when active)
- Active route highlighted in sidebar

---

## Step 10 — Wire Real Odds API

In Phase 1, the ingestion service used fixture JSON when `ODDS_API_KEY` was unset.
Now we activate the real polling path.

**Changes to `odds_ingestion.py`**:
- The fixture fallback should still exist for local dev without a key
- When a real key is present, the live API path should be the default
- Add markets to poll: `h2h,spreads,totals` for game markets + separate calls for player props
  - Player prop market keys to support: `player_points`, `player_rebounds`, `player_assists`,
    `player_pass_tds`, `player_rush_yards`, `player_receiving_yards`
- Store the `bookmakers` response field correctly (some API responses nest bookmakers differently for props)

**Verify with a real key**:
1. Set `ODDS_API_KEY` in `.env`
2. Call `POST /api/system/poll`
3. Confirm new rows in `odds_snapshots` and `odds_lines`
4. Confirm `GET /api/opportunities` returns real data
5. Confirm credits were logged in `api_usage_log`
6. Check `GET /api/system/credits` reflects the real credit balance

---

## Step 11 — End-to-End Smoke Test

Run through this manually before committing:

1. `docker-compose up` — all 3 services start without errors
2. `http://localhost:3000` — Dashboard loads with seeded data
3. Dashboard Opportunity Feed — shows mock/live opportunities, auto-refreshes
4. Credits Widget — shows API usage
5. Navigate to `/opportunities` — filter by sport, sort by edge%
6. Click an opportunity row — expands with full book comparison
7. Click "Log Trade" from an opportunity — navigates to `/trades/new` pre-filled
8. Submit a paper trade — appears in `/trades` journal
9. `/analytics` — all 6 charts render (no blank panels)
10. `/settings` — toggle paper mode, change edge threshold, save persists across refresh
11. `POST /api/system/poll` — completes without 500 error
12. `GET /api/docs` — Swagger UI shows all endpoints with correct schemas

If any step fails, fix it before proceeding to Step 12.

---

## Step 12 — README + Final Commit

### `README.md`

Write a clean, structured README:

```markdown
# Bettor — Sports Betting Edge Finding System

## What It Does
[2-3 paragraph overview: CLV-first approach, why no-vig matters, the paper→real pipeline]

## Architecture
[ASCII diagram showing: Odds API → Ingestion Service → PostgreSQL → FastAPI → React]

## Quick Start
[docker-compose instructions from CLAUDE.md]

## Key Concepts
### Closing Line Value (CLV)
### No-Vig Probability
### The Sharp Book Hierarchy
### Kelly Criterion Sizing

## Paper Trading First
[Explain the PAPER_TRADING_MODE flag and why you validate edge before deploying capital]

## Getting an Odds API Key
[Link to the-odds-api.com, note the free tier credits]

## Project Structure
[Brief description of backend/frontend layout]
```

### Final git state

```bash
git add -A
git commit -m "feat: phase 2 complete — full frontend + live odds wiring"
git push origin main
git push origin develop
```

Output the full Session Summary as specified in `CLAUDE.md` and append to `SESSIONS.md`.

---

## Phase 2 Complete — What You Should Have

```
docker-compose up
```

→ `http://localhost:3000` — Full dashboard with seeded P&L, equity curve, CLV distribution
→ Add real Odds API key to `.env` → system polls live odds, surfaces real +EV opportunities
→ Click any opportunity → log a paper trade in 10 seconds
→ `/analytics` → see if your edge detection is actually working via CLV distribution
→ When you move to Pennsylvania — flip `PAPER_TRADING_MODE=false` → system ready for real capital
"""Seed the database with realistic historical demo data.

Run standalone (after ``alembic upgrade head``)::

    python scripts/seed_demo_data.py

Produces 100 settled paper trades (55% win rate, avg CLV ~+1.8%), ~20 completed events
across NFL/NBA/MLB, and 90 daily bankroll snapshots forming a realistic equity curve.
Re-running is idempotent: existing demo trades, snapshots, and events are cleared first.

This script is deliberately self-contained — it imports only the models and analytics, so
it can be run without the FastAPI app or scheduler.
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running as `python scripts/seed_demo_data.py` from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete  # noqa: E402

from app.analytics.no_vig import (  # noqa: E402
    american_to_decimal,
    decimal_to_american,
    implied_probability,
)
from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    BankrollSnapshot,
    Event,
    Sport,
    Trade,
    TradeResult,
    TradeStatus,
    TradeType,
)

# --- Configuration -------------------------------------------------------------------

RANDOM_SEED = 41
N_TRADES = 100
N_WINS = 55
N_EVENTS = 20
N_DAYS = 90
STARTING_BANKROLL = 1000.0
TARGET_FINAL_BANKROLL = 1250.0  # final is scaled toward this, clamped to [1100, 1400]

SPORTS = {
    "americanfootball_nfl": "NFL",
    "basketball_nba": "NBA",
    "baseball_mlb": "MLB",
}
# (sport_key, weight) — ~40% NFL, ~35% NBA, ~25% MLB.
SPORT_WEIGHTS = [
    ("americanfootball_nfl", 0.40),
    ("basketball_nba", 0.35),
    ("baseball_mlb", 0.25),
]
# (market_key, is_prop, weight) — ~30% props, ~40% spreads, ~30% h2h.
MARKET_WEIGHTS = [
    ("player_points", True, 0.30),
    ("spreads", False, 0.40),
    ("h2h", False, 0.30),
]
BOOKMAKERS = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle", "bookmaker"]

KELLY_FRACTION = 0.25
CLV_MEAN, CLV_STD = 1.8, 3.0
EDGE_MEAN, EDGE_STD = 0.032, 0.015

# Representative team/player pools per sport for plausible labels.
TEAMS = {
    "americanfootball_nfl": [
        ("Kansas City Chiefs", "Buffalo Bills"),
        ("San Francisco 49ers", "Dallas Cowboys"),
        ("Philadelphia Eagles", "New York Giants"),
        ("Baltimore Ravens", "Cincinnati Bengals"),
    ],
    "basketball_nba": [
        ("Boston Celtics", "Miami Heat"),
        ("Denver Nuggets", "Los Angeles Lakers"),
        ("Milwaukee Bucks", "New York Knicks"),
        ("Phoenix Suns", "Golden State Warriors"),
    ],
    "baseball_mlb": [
        ("Los Angeles Dodgers", "San Diego Padres"),
        ("Atlanta Braves", "New York Mets"),
        ("Houston Astros", "Texas Rangers"),
        ("New York Yankees", "Boston Red Sox"),
    ],
}
PLAYERS = {
    "americanfootball_nfl": ["Patrick Mahomes", "Josh Allen", "CeeDee Lamb"],
    "basketball_nba": ["Jayson Tatum", "Nikola Jokic", "Luka Doncic"],
    "baseball_mlb": ["Mookie Betts", "Aaron Judge", "Ronald Acuna Jr."],
}


def _weighted_choice(rng: random.Random, weighted: list) -> tuple:
    """Pick one (item...) tuple by its trailing weight using ``rng``."""
    weights = [entry[-1] for entry in weighted]
    return rng.choices(weighted, weights=weights, k=1)[0]


def _build_events(rng: random.Random, now: datetime) -> list[Event]:
    """Build ~N_EVENTS completed events distributed across the sports by weight."""
    events: list[Event] = []
    for i in range(N_EVENTS):
        sport_key, _ = _weighted_choice(rng, SPORT_WEIGHTS)
        home, away = rng.choice(TEAMS[sport_key])
        commence = now - timedelta(days=rng.randint(1, N_DAYS - 1), hours=rng.randint(0, 23))
        home_score = rng.randint(0, 6) * rng.randint(3, 7)
        away_score = rng.randint(0, 6) * rng.randint(3, 7)
        events.append(
            Event(
                id=f"demo-{sport_key}-{i:03d}",
                sport_key=sport_key,
                commence_time=commence,
                home_team=home,
                away_team=away,
                completed=True,
                home_score=home_score,
                away_score=away_score,
            )
        )
    return events


def _build_trades(
    rng: random.Random, events: list[Event], now: datetime
) -> list[Trade]:
    """Build N_TRADES settled paper trades with the target distributions."""
    events_by_sport: dict[str, list[Event]] = {key: [] for key in SPORTS}
    for event in events:
        events_by_sport[event.sport_key].append(event)

    # Exactly N_WINS wins / (N_TRADES - N_WINS) losses, shuffled.
    results = [TradeResult.win] * N_WINS + [TradeResult.loss] * (N_TRADES - N_WINS)
    rng.shuffle(results)

    trades: list[Trade] = []
    for i in range(N_TRADES):
        sport_key, _ = _weighted_choice(rng, SPORT_WEIGHTS)
        # Guarantee an event exists for the chosen sport.
        if not events_by_sport[sport_key]:
            sport_key = next(k for k, v in events_by_sport.items() if v)
        event = rng.choice(events_by_sport[sport_key])

        market_key, is_prop, _ = _weighted_choice(rng, MARKET_WEIGHTS)
        bookmaker = rng.choice(BOOKMAKERS)
        result = results[i]

        american = rng.randint(-160, 180)
        if -100 < american < 100:  # avoid invalid -99..+99 region
            american = 100 if american >= 0 else -100
        entry_decimal = american_to_decimal(american)
        book_implied = implied_probability(entry_decimal)

        edge = max(0.002, rng.gauss(EDGE_MEAN, EDGE_STD))
        our_prob = min(0.97, book_implied + edge)
        sharp_consensus = our_prob

        # Quarter-Kelly stake from the (positive) edge.
        b = entry_decimal - 1.0
        full_kelly = max(0.0, (b * our_prob - (1.0 - our_prob)) / b)
        stake_units = round(full_kelly * KELLY_FRACTION, 4)

        if result == TradeResult.win:
            pnl_units = round(stake_units * b, 4)
        else:
            pnl_units = round(-stake_units, 4)

        clv = round(rng.gauss(CLV_MEAN, CLV_STD), 3)
        # Closing decimal implied by CLV: closing = entry * (1 + clv/100).
        closing_decimal = entry_decimal * (1.0 + clv / 100.0)

        created_at = now - timedelta(
            days=rng.randint(0, N_DAYS - 1),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        outcome_name, player_name = _label_for(rng, event, market_key, is_prop)

        trades.append(
            Trade(
                event_id=event.id,
                market_key=market_key,
                outcome_name=outcome_name,
                player_name=player_name,
                entry_price_american=american,
                entry_price_decimal=round(entry_decimal, 4),
                our_prob=round(our_prob, 4),
                sharp_consensus_prob=round(sharp_consensus, 4),
                edge_pct=round(our_prob - book_implied, 4),
                kelly_fraction=round(full_kelly, 4),
                stake_units=stake_units,
                bookmaker=bookmaker,
                trade_type=TradeType.paper,
                status=TradeStatus.settled,
                result=result,
                closing_price_american=decimal_to_american(closing_decimal),
                clv=clv,
                profit_loss_units=pnl_units,
                created_at=created_at,
                settled_at=created_at + timedelta(hours=4),
            )
        )
    return trades


def _label_for(
    rng: random.Random, event: Event, market_key: str, is_prop: bool
) -> tuple[str, str | None]:
    """Return (outcome_name, player_name) appropriate for the market type."""
    if is_prop:
        player = rng.choice(PLAYERS[event.sport_key])
        side = rng.choice(["Over", "Under"])
        return f"{player} {side} 24.5", player
    team = rng.choice([event.home_team, event.away_team])
    if market_key == "spreads":
        point = rng.choice([-7.5, -3.5, -1.5, 1.5, 3.5, 7.5])
        return f"{team} {point:+.1f}", None
    return team, None


def _build_bankroll_snapshots(
    trades: list[Trade], now: datetime, unit_dollars: float
) -> list[BankrollSnapshot]:
    """Build one snapshot per day for the last N_DAYS from daily trade P&L."""
    by_day: dict = {}
    for trade in trades:
        day = trade.created_at.date()
        by_day.setdefault(day, []).append(trade)

    snapshots: list[BankrollSnapshot] = []
    bankroll = STARTING_BANKROLL
    for offset in range(N_DAYS - 1, -1, -1):
        day = (now - timedelta(days=offset)).date()
        day_trades = by_day.get(day, [])
        units_won = sum(t.profit_loss_units for t in day_trades if t.profit_loss_units and t.profit_loss_units > 0)
        units_lost = sum(-t.profit_loss_units for t in day_trades if t.profit_loss_units and t.profit_loss_units < 0)
        day_net_dollars = (units_won - units_lost) * unit_dollars
        starting = bankroll
        bankroll = starting + day_net_dollars
        snapshots.append(
            BankrollSnapshot(
                date=day,
                starting_bankroll=round(starting, 2),
                ending_bankroll=round(bankroll, 2),
                trades_count=len(day_trades),
                units_won=round(units_won, 4),
                units_lost=round(units_lost, 4),
                roi_pct=round(day_net_dollars / starting * 100.0, 4) if starting else 0.0,
                cumulative_roi_pct=round(
                    (bankroll - STARTING_BANKROLL) / STARTING_BANKROLL * 100.0, 4
                ),
            )
        )
    return snapshots


async def seed() -> None:
    """Populate the database with demo data and print a summary."""
    rng = random.Random(RANDOM_SEED)
    now = datetime.utcnow()

    async with AsyncSessionLocal() as session:
        # Idempotent reseed: clear demo data (order respects FKs).
        await session.execute(delete(BankrollSnapshot))
        await session.execute(delete(Trade))
        await session.execute(delete(Event))
        await session.commit()

        # Sports.
        for key, title in SPORTS.items():
            sport = await session.get(Sport, key)
            if sport is None:
                session.add(Sport(sport_key=key, title=title, active=True))
            else:
                sport.active = True
        await session.commit()

        # Events + trades.
        events = _build_events(rng, now)
        session.add_all(events)
        await session.flush()

        trades = _build_trades(rng, events, now)
        session.add_all(trades)

        # Scale unit dollars so the final bankroll lands in a realistic range.
        net_units = sum(t.profit_loss_units or 0.0 for t in trades)
        if net_units > 0:
            unit_dollars = (TARGET_FINAL_BANKROLL - STARTING_BANKROLL) / net_units
        else:
            unit_dollars = 10.0
        for trade in trades:
            trade.stake_dollars = round(trade.stake_units * unit_dollars, 2)
            if trade.profit_loss_units is not None:
                trade.profit_loss_dollars = round(
                    trade.profit_loss_units * unit_dollars, 2
                )

        snapshots = _build_bankroll_snapshots(trades, now, unit_dollars)
        session.add_all(snapshots)
        await session.commit()

        _print_summary(trades, snapshots)


def _print_summary(trades: list[Trade], snapshots: list[BankrollSnapshot]) -> None:
    """Print a human-readable summary of the seeded data."""
    wins = sum(1 for t in trades if t.result == TradeResult.win)
    losses = sum(1 for t in trades if t.result == TradeResult.loss)
    avg_clv = sum(t.clv or 0.0 for t in trades) / len(trades)
    final_bankroll = snapshots[-1].ending_bankroll if snapshots else STARTING_BANKROLL
    counts = {title: 0 for title in SPORTS.values()}
    sport_titles = {k: v for k, v in SPORTS.items()}
    by_event_sport = {}
    # Count trades by sport via their event id prefix (demo-<sport_key>-...).
    for t in trades:
        for key, title in sport_titles.items():
            if t.event_id.startswith(f"demo-{key}-"):
                counts[title] += 1
                by_event_sport[t.event_id] = title
                break

    print(f"Seeded {len(trades)} trades: {wins} wins / {losses} losses")
    print(f"Avg CLV: {avg_clv:+.2f}%")
    print(f"Final bankroll: ${final_bankroll:,.2f}")
    print(
        "Sports: "
        + ", ".join(f"{title} ({counts[title]})" for title in SPORTS.values())
    )


if __name__ == "__main__":
    asyncio.run(seed())

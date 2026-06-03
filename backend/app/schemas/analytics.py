"""Pydantic schemas for analytics and system responses."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CLVStats(BaseModel):
    """Summary statistics over a set of CLV values."""

    mean: float
    median: float
    std_dev: float
    pct_positive: float
    sample_size: int


class EquityPoint(BaseModel):
    """A single point on the equity curve."""

    date: date
    bankroll: float
    cumulative_pnl_units: float


class PnLSummary(BaseModel):
    """P&L summary plus the equity-curve series."""

    total_trades: int
    settled_trades: int
    wins: int
    losses: int
    pushes: int
    win_rate_pct: float
    net_units: float
    roi_pct: float
    starting_bankroll: float
    current_bankroll: float
    equity_curve: list[EquityPoint]


class EdgeBucket(BaseModel):
    """ROI aggregated within an edge range, for the edge-vs-ROI analysis."""

    edge_bucket: str
    trades: int
    avg_edge_pct: float
    net_units: float
    roi_pct: float


class EdgeAnalytics(BaseModel):
    """Edge-detection analytics: correlation of edge size with realized ROI."""

    avg_edge_pct: float
    buckets: list[EdgeBucket]


class BankrollSnapshotResponse(BaseModel):
    """A daily bankroll snapshot."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    starting_bankroll: float
    ending_bankroll: float
    trades_count: int
    units_won: float
    units_lost: float
    roi_pct: float
    cumulative_roi_pct: float


class ApiUsageSummary(BaseModel):
    """Aggregate Odds API credit usage."""

    total_calls: int
    total_credits_used: int
    latest_credits_remaining: int
    last_called_at: datetime | None = None


class PollResult(BaseModel):
    """Result of a manually triggered odds poll."""

    status: str
    sports_polled: list[str]
    detail: str


class SystemStats(BaseModel):
    """Database-wide counts surfaced on the Settings page."""

    total_trades: int
    total_events: int
    total_snapshots: int
    total_odds_lines: int
    active_sports: int


class SeedResult(BaseModel):
    """Result of (re)seeding demo data."""

    status: str
    detail: str

"""Routes for CLV, P&L, edge, and bankroll analytics."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.clv import aggregate_clv_stats
from app.config import Settings
from app.dependencies import get_db, get_settings
from app.db.models import BankrollSnapshot, Trade, TradeResult, TradeStatus
from app.schemas.analytics import (
    BankrollSnapshotResponse,
    CLVStats,
    EdgeAnalytics,
    EdgeBucket,
    EquityPoint,
    PnLSummary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Edge buckets (as fractions) for the edge-vs-ROI analysis.
EDGE_BUCKETS: list[tuple[str, float, float]] = [
    ("0-2%", 0.0, 0.02),
    ("2-4%", 0.02, 0.04),
    ("4-6%", 0.04, 0.06),
    ("6%+", 0.06, float("inf")),
]


async def _settled_trades(session: AsyncSession) -> list[Trade]:
    """Return all settled trades ordered by creation time."""
    result = await session.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.settled)
        .order_by(Trade.created_at.asc())
    )
    return list(result.scalars().all())


@router.get("/clv", response_model=CLVStats)
async def clv_stats(session: AsyncSession = Depends(get_db)) -> CLVStats:
    """Return summary CLV statistics across all trades with a recorded CLV."""
    result = await session.execute(select(Trade.clv).where(Trade.clv.is_not(None)))
    values = [row[0] for row in result.all() if row[0] is not None]
    return CLVStats(**aggregate_clv_stats(values))


@router.get("/pnl", response_model=PnLSummary)
async def pnl_summary(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PnLSummary:
    """Return P&L summary statistics plus the equity-curve series."""
    trades = await _settled_trades(session)
    wins = sum(1 for t in trades if t.result == TradeResult.win)
    losses = sum(1 for t in trades if t.result == TradeResult.loss)
    pushes = sum(1 for t in trades if t.result == TradeResult.push)
    decisive = wins + losses
    net_units = sum(t.profit_loss_units or 0.0 for t in trades)
    total_staked = sum(t.stake_units for t in trades)
    roi_pct = (net_units / total_staked * 100.0) if total_staked else 0.0

    # Equity curve from daily bankroll snapshots.
    snap_result = await session.execute(
        select(BankrollSnapshot).order_by(BankrollSnapshot.date.asc())
    )
    snapshots = list(snap_result.scalars().all())

    starting = (
        snapshots[0].starting_bankroll if snapshots else settings.active_bankroll
    )
    current = snapshots[-1].ending_bankroll if snapshots else settings.active_bankroll

    equity_curve: list[EquityPoint] = []
    cumulative = 0.0
    for snap in snapshots:
        cumulative += snap.units_won - snap.units_lost
        equity_curve.append(
            EquityPoint(
                date=snap.date,
                bankroll=snap.ending_bankroll,
                cumulative_pnl_units=cumulative,
            )
        )

    return PnLSummary(
        total_trades=len(trades),
        settled_trades=len(trades),
        wins=wins,
        losses=losses,
        pushes=pushes,
        win_rate_pct=(wins / decisive * 100.0) if decisive else 0.0,
        net_units=net_units,
        roi_pct=roi_pct,
        starting_bankroll=starting,
        current_bankroll=current,
        equity_curve=equity_curve,
    )


@router.get("/edge", response_model=EdgeAnalytics)
async def edge_analytics(session: AsyncSession = Depends(get_db)) -> EdgeAnalytics:
    """Return edge-vs-ROI analytics, bucketed by edge size."""
    trades = await _settled_trades(session)
    avg_edge = (sum(t.edge_pct for t in trades) / len(trades)) if trades else 0.0

    buckets: list[EdgeBucket] = []
    for label, low, high in EDGE_BUCKETS:
        bucket_trades = [t for t in trades if low <= t.edge_pct < high]
        if not bucket_trades:
            buckets.append(
                EdgeBucket(
                    edge_bucket=label,
                    trades=0,
                    avg_edge_pct=0.0,
                    net_units=0.0,
                    roi_pct=0.0,
                )
            )
            continue
        net = sum(t.profit_loss_units or 0.0 for t in bucket_trades)
        staked = sum(t.stake_units for t in bucket_trades)
        buckets.append(
            EdgeBucket(
                edge_bucket=label,
                trades=len(bucket_trades),
                avg_edge_pct=sum(t.edge_pct for t in bucket_trades)
                / len(bucket_trades),
                net_units=net,
                roi_pct=(net / staked * 100.0) if staked else 0.0,
            )
        )

    return EdgeAnalytics(avg_edge_pct=avg_edge, buckets=buckets)


@router.get("/bankroll", response_model=list[BankrollSnapshotResponse])
async def bankroll_history(
    session: AsyncSession = Depends(get_db),
) -> list[BankrollSnapshot]:
    """Return the full daily bankroll history, oldest first."""
    result = await session.execute(
        select(BankrollSnapshot).order_by(BankrollSnapshot.date.asc())
    )
    return list(result.scalars().all())

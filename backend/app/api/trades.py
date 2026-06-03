"""Routes for logging, listing, and updating trades."""

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.edge_detection import _full_kelly, calculate_kelly
from app.analytics.no_vig import american_to_decimal, implied_probability
from app.config import Settings
from app.dependencies import get_db, get_settings
from app.db.models import Trade, TradeStatus, TradeType
from app.schemas.trades import TradeCreate, TradeResponse, TradeUpdate

router = APIRouter(tags=["trades"])


@router.post("/trades", response_model=TradeResponse, status_code=201)
async def create_trade(
    payload: TradeCreate,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Trade:
    """Validate and log a new trade, computing edge and Kelly stake server-side.

    Real-money trades are rejected while ``PAPER_TRADING_MODE`` is enabled.
    """
    if payload.trade_type == TradeType.real and settings.paper_trading_mode:
        raise HTTPException(
            status_code=403,
            detail="Real-money trades are disabled while PAPER_TRADING_MODE is on.",
        )

    entry_decimal = american_to_decimal(payload.entry_price_american)
    book_implied = implied_probability(entry_decimal)
    edge_pct = payload.our_prob - book_implied
    full_kelly = _full_kelly(payload.our_prob, entry_decimal)
    stake_units = calculate_kelly(
        payload.our_prob, entry_decimal, settings.default_kelly_fraction
    )

    trade = Trade(
        event_id=payload.event_id,
        market_key=payload.market_key,
        outcome_name=payload.outcome_name,
        player_name=payload.player_name,
        entry_price_american=payload.entry_price_american,
        entry_price_decimal=entry_decimal,
        our_prob=payload.our_prob,
        sharp_consensus_prob=payload.sharp_consensus_prob,
        edge_pct=edge_pct,
        kelly_fraction=full_kelly,
        stake_units=stake_units,
        stake_dollars=payload.stake_dollars,
        bookmaker=payload.bookmaker,
        trade_type=payload.trade_type,
        status=TradeStatus.open,
        notes=payload.notes,
    )
    session.add(trade)
    await session.commit()
    await session.refresh(trade)
    logger.info(
        "Logged {} trade {} edge={:.3f} stake={:.3f}u",
        trade.trade_type.value,
        trade.outcome_name,
        edge_pct,
        stake_units,
    )
    return trade


@router.get("/trades", response_model=list[TradeResponse])
async def list_trades(
    sport: str | None = Query(default=None),
    status: TradeStatus | None = Query(default=None),
    trade_type: TradeType | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[Trade]:
    """List trades with optional filters by status, type, and date range."""
    stmt = select(Trade)
    if status:
        stmt = stmt.where(Trade.status == status)
    if trade_type:
        stmt = stmt.where(Trade.trade_type == trade_type)
    if start_date:
        stmt = stmt.where(Trade.created_at >= datetime(
            start_date.year, start_date.month, start_date.day
        ))
    if end_date:
        stmt = stmt.where(Trade.created_at <= datetime(
            end_date.year, end_date.month, end_date.day, 23, 59, 59
        ))
    result = await session.execute(stmt.order_by(Trade.created_at.desc()))
    trades = list(result.scalars().all())

    # ``sport`` filters via the related event's sport_key.
    if sport:
        from app.db.models import Event

        event_ids = {t.event_id for t in trades}
        if event_ids:
            rows = await session.execute(
                select(Event.id).where(
                    Event.id.in_(event_ids), Event.sport_key == sport
                )
            )
            allowed = {row[0] for row in rows.all()}
            trades = [t for t in trades if t.event_id in allowed]
    return trades


@router.put("/trades/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: UUID,
    payload: TradeUpdate,
    session: AsyncSession = Depends(get_db),
) -> Trade:
    """Update a trade's notes or status (e.g. void it)."""
    trade = await session.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    if payload.notes is not None:
        trade.notes = payload.notes
    if payload.status is not None:
        trade.status = payload.status
    await session.commit()
    await session.refresh(trade)
    return trade

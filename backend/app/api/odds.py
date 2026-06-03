"""Routes for sports, events, current odds, and edge opportunities."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.edge_detection import EdgeOpportunity, OddsLineData, find_edges
from app.config import Settings
from app.dependencies import get_db, get_settings
from app.db.models import Event, OddsLine, Sport
from app.schemas.odds import (
    EdgeOpportunityResponse,
    EventOddsResponse,
    EventResponse,
    OddsLineResponse,
    SportResponse,
)

router = APIRouter(tags=["odds"])


async def _latest_lines_for_event(
    session: AsyncSession, event_id: str
) -> list[OddsLine]:
    """Return the odds lines from the most recent snapshot for an event."""
    latest_ts = await session.scalar(
        select(OddsLine.snapshot_timestamp)
        .where(OddsLine.event_id == event_id)
        .order_by(OddsLine.snapshot_timestamp.desc())
        .limit(1)
    )
    if latest_ts is None:
        return []
    result = await session.execute(
        select(OddsLine).where(
            OddsLine.event_id == event_id,
            OddsLine.snapshot_timestamp == latest_ts,
        )
    )
    return list(result.scalars().all())


def _lines_to_dataclass(lines: list[OddsLine]) -> list[OddsLineData]:
    """Convert ORM odds lines into edge-detection input dataclasses."""
    return [
        OddsLineData(
            bookmaker_key=line.bookmaker_key,
            market_key=line.market_key,
            outcome_name=line.outcome_name,
            price_decimal=line.price_decimal,
            price_american=line.price_american,
            point=line.point,
            player_name=line.player_name,
        )
        for line in lines
    ]


def _opportunity_to_response(
    opp: EdgeOpportunity, event: Event | None
) -> EdgeOpportunityResponse:
    """Map an :class:`EdgeOpportunity` to its response schema, enriched with event info."""
    return EdgeOpportunityResponse(
        event_id=opp.event_id,
        market_key=opp.market_key,
        outcome_name=opp.outcome_name,
        player_name=opp.player_name,
        our_prob=opp.our_prob,
        book_implied_prob=opp.book_implied_prob,
        edge_pct=opp.edge_pct,
        best_book=opp.best_book,
        best_price_american=opp.best_price_american,
        best_price_decimal=opp.best_price_decimal,
        sharp_anchor_book=opp.sharp_anchor_book,
        kelly_fraction=opp.kelly_fraction,
        recommended_stake_units=opp.recommended_stake_units,
        home_team=event.home_team if event else None,
        away_team=event.away_team if event else None,
        commence_time=event.commence_time if event else None,
    )


@router.get("/sports", response_model=list[SportResponse])
async def list_sports(
    active_only: bool = Query(default=True),
    session: AsyncSession = Depends(get_db),
) -> list[Sport]:
    """List tracked sports, optionally only the active ones."""
    stmt = select(Sport)
    if active_only:
        stmt = stmt.where(Sport.active.is_(True))
    result = await session.execute(stmt.order_by(Sport.sport_key))
    return list(result.scalars().all())


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    sport: str | None = Query(default=None),
    on_date: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db),
) -> list[Event]:
    """List upcoming/known events, filterable by sport and date."""
    stmt = select(Event)
    if sport:
        stmt = stmt.where(Event.sport_key == sport)
    if on_date:
        day_start = datetime(on_date.year, on_date.month, on_date.day)
        day_end = datetime(on_date.year, on_date.month, on_date.day, 23, 59, 59)
        stmt = stmt.where(Event.commence_time.between(day_start, day_end))
    result = await session.execute(stmt.order_by(Event.commence_time))
    return list(result.scalars().all())


@router.get("/odds/{event_id}", response_model=EventOddsResponse)
async def get_event_odds(
    event_id: str,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EventOddsResponse:
    """Return all current odds for one event plus its edge calculations."""
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    lines = await _latest_lines_for_event(session, event_id)
    opportunities = find_edges(
        event_id,
        _lines_to_dataclass(lines),
        edge_threshold=settings.edge_threshold,
        kelly_fraction=settings.default_kelly_fraction,
    )
    return EventOddsResponse(
        event=EventResponse.model_validate(event),
        lines=[OddsLineResponse.model_validate(line) for line in lines],
        opportunities=[_opportunity_to_response(o, event) for o in opportunities],
    )


@router.get("/opportunities", response_model=list[EdgeOpportunityResponse])
async def list_opportunities(
    sport: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[EdgeOpportunityResponse]:
    """Return all current +EV plays above the configured edge threshold, ranked."""
    now = datetime.utcnow()
    stmt = select(Event).where(Event.commence_time > now, Event.completed.is_(False))
    if sport:
        stmt = stmt.where(Event.sport_key == sport)
    result = await session.execute(stmt)
    events = list(result.scalars().all())

    responses: list[EdgeOpportunityResponse] = []
    for event in events:
        lines = await _latest_lines_for_event(session, event.id)
        if not lines:
            continue
        opportunities = find_edges(
            event.id,
            _lines_to_dataclass(lines),
            edge_threshold=settings.edge_threshold,
            kelly_fraction=settings.default_kelly_fraction,
        )
        responses.extend(_opportunity_to_response(o, event) for o in opportunities)

    responses.sort(key=lambda r: r.edge_pct, reverse=True)
    return responses

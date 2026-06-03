"""System routes: API credit usage and manual poll triggering."""

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import get_db, get_settings
from app.db.models import ApiUsageLog, Event, OddsLine, OddsSnapshot, Sport, Trade
from app.schemas.analytics import (
    ApiUsageSummary,
    PollResult,
    SeedResult,
    SystemStats,
)
from app.services.odds_ingestion import OddsIngestionService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/credits", response_model=ApiUsageSummary)
async def api_credits(session: AsyncSession = Depends(get_db)) -> ApiUsageSummary:
    """Return aggregate Odds API credit usage."""
    total_calls = await session.scalar(select(func.count()).select_from(ApiUsageLog))
    total_used = await session.scalar(select(func.coalesce(func.sum(ApiUsageLog.credits_used), 0)))

    latest = await session.execute(
        select(ApiUsageLog).order_by(ApiUsageLog.called_at.desc()).limit(1)
    )
    latest_log = latest.scalar_one_or_none()

    return ApiUsageSummary(
        total_calls=int(total_calls or 0),
        total_credits_used=int(total_used or 0),
        latest_credits_remaining=latest_log.credits_remaining if latest_log else 0,
        last_called_at=latest_log.called_at if latest_log else None,
    )


@router.post("/poll", response_model=PollResult)
async def trigger_poll(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PollResult:
    """Manually trigger an odds poll across all active sports."""
    service = OddsIngestionService(session, settings)

    # Ensure there are active sports to poll (seeds demo sports in fixture mode).
    existing = await session.scalar(select(func.count()).select_from(Sport))
    if not existing:
        await service.fetch_and_store_sports()

    result = await session.execute(select(Sport.sport_key).where(Sport.active.is_(True)))
    sport_keys = [row[0] for row in result.all()]

    await service.poll_all_active_sports()
    logger.info("Manual poll triggered for {} sports", len(sport_keys))
    return PollResult(
        status="ok",
        sports_polled=sport_keys,
        detail=f"Polled {len(sport_keys)} active sport(s).",
    )


@router.get("/stats", response_model=SystemStats)
async def system_stats(session: AsyncSession = Depends(get_db)) -> SystemStats:
    """Return database-wide counts for the Settings page."""

    async def _count(model) -> int:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)

    active = int(
        await session.scalar(
            select(func.count()).select_from(Sport).where(Sport.active.is_(True))
        )
        or 0
    )
    return SystemStats(
        total_trades=await _count(Trade),
        total_events=await _count(Event),
        total_snapshots=await _count(OddsSnapshot),
        total_odds_lines=await _count(OddsLine),
        active_sports=active,
    )


@router.post("/seed", response_model=SeedResult)
async def seed_demo_data() -> SeedResult:
    """(Re)seed the database with demo data — useful for resetting state.

    Runs the same idempotent logic as ``scripts/seed_demo_data.py`` using its own
    session, then returns a summary message.
    """
    # Imported lazily so the seed script's module-level setup runs only on demand.
    from scripts.seed_demo_data import seed

    await seed()
    logger.info("Demo data reseeded via API")
    return SeedResult(status="ok", detail="Demo data reseeded (100 trades).")

"""FastAPI application factory, lifespan, scheduler, and middleware."""

import time
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.router import api_router
from app.config import get_settings
from app.db.base import AsyncSessionLocal
from app.services.odds_ingestion import OddsIngestionService

# Mark closing lines every 15 minutes (independent of the odds poll interval).
CLOSING_LINE_INTERVAL_MINUTES = 15


async def _poll_job() -> None:
    """Scheduled job: poll all active sports for fresh odds."""
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        service = OddsIngestionService(session, settings)
        try:
            await service.poll_all_active_sports()
        except Exception as exc:  # noqa: BLE001 — scheduler jobs must not crash the loop
            logger.exception("Scheduled odds poll failed: {}", exc)


async def _closing_lines_job() -> None:
    """Scheduled job: mark closing lines for events that have commenced."""
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        service = OddsIngestionService(session, settings)
        try:
            await service.mark_closing_lines()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scheduled closing-line marking failed: {}", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the APScheduler odds jobs on startup; shut them down on exit."""
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _poll_job,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="poll_active_sports",
        replace_existing=True,
    )
    scheduler.add_job(
        _closing_lines_job,
        "interval",
        minutes=CLOSING_LINE_INTERVAL_MINUTES,
        id="mark_closing_lines",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: poll every {}m, closing lines every {}m",
        settings.poll_interval_minutes,
        CLOSING_LINE_INTERVAL_MINUTES,
    )
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="Bettor API",
        version="0.1.0",
        description="Systematic sports betting edge-finding system.",
        lifespan=lifespan,
    )

    # CORS: permissive in development, locked down in production.
    allow_origins = ["*"] if settings.is_development else ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log method, path, status, and duration for every request."""
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "{} {} -> {} ({:.1f}ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "environment": settings.environment}

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

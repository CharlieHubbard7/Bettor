"""Top-level API router that mounts all sub-routers under ``/api``."""

from fastapi import APIRouter

from app.api import analytics, odds, system, trades

api_router = APIRouter()
api_router.include_router(odds.router)
api_router.include_router(trades.router)
api_router.include_router(analytics.router)
api_router.include_router(system.router)

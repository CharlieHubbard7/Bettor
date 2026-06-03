"""Game results fetching and trade settlement.

After games complete this service records scores, computes Closing Line Value against the
captured closing line, and settles open trades into realized profit/loss.
"""

from datetime import datetime

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.clv import calculate_clv
from app.config import Settings
from app.db.models import (
    ApiUsageLog,
    ClosingLine,
    Event,
    Trade,
    TradeResult,
    TradeStatus,
)

ODDS_API_BASE_URL = "https://api.the-odds-api.com"


def settle_pnl(stake_units: float, decimal_odds: float, result: TradeResult) -> float:
    """Return realized P&L in units for a settled trade.

    Args:
        stake_units: Units staked on the trade.
        decimal_odds: Decimal odds the bet was placed at.
        result: The settlement outcome.

    Returns:
        Profit (positive) or loss (negative) in units. A push returns ``0.0``.
    """
    match result:
        case TradeResult.win:
            return stake_units * (decimal_odds - 1.0)
        case TradeResult.loss:
            return -stake_units
        case TradeResult.push:
            return 0.0


class ResultsService:
    """Fetches completed-game scores and settles the trades that depend on them."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Initialize the service with a DB session and app settings."""
        self.session = session
        self.settings = settings

    async def fetch_scores(self, sport_key: str) -> None:
        """Fetch completed-game scores for a sport and persist them on events.

        Args:
            sport_key: The Odds API sport key.

        Note:
            No-ops in development without a configured API key — settlement of seeded
            demo data does not depend on live scores.
        """
        if self.settings.is_development and not self.settings.odds_api_key_is_configured:
            logger.info("Skipping live scores fetch for {} (no API key)", sport_key)
            return

        url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/scores"
        params = {"apiKey": self.settings.odds_api_key, "daysFrom": 3}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        self.session.add(
            ApiUsageLog(
                endpoint=f"/v4/sports/{sport_key}/scores",
                sport_key=sport_key,
                credits_used=int(response.headers.get("x-requests-last", 0) or 0),
                credits_remaining=int(
                    response.headers.get("x-requests-remaining", 0) or 0
                ),
                response_status=response.status_code,
            )
        )

        for game in response.json():
            if not game.get("completed"):
                continue
            event = await self.session.get(Event, game["id"])
            if event is None:
                continue
            event.completed = True
            for score in game.get("scores", []):
                if score["name"] == event.home_team:
                    event.home_score = int(score["score"])
                elif score["name"] == event.away_team:
                    event.away_score = int(score["score"])
        await self.session.commit()

    async def apply_clv(self, trade: Trade) -> None:
        """Fill in a trade's closing price and CLV from the captured closing line."""
        result = await self.session.execute(
            select(ClosingLine).where(
                ClosingLine.event_id == trade.event_id,
                ClosingLine.market_key == trade.market_key,
                ClosingLine.outcome_name == trade.outcome_name,
                ClosingLine.bookmaker_key == trade.bookmaker,
            )
        )
        closing = result.scalar_one_or_none()
        if closing is None:
            return
        trade.closing_price_american = closing.price_american
        trade.clv = calculate_clv(trade.entry_price_decimal, closing.price_decimal)

    async def settle_trade(self, trade: Trade, result: TradeResult) -> None:
        """Settle a single open trade into a realized result and P&L.

        Args:
            trade: The trade to settle.
            result: Win/loss/push outcome.
        """
        pnl_units = settle_pnl(trade.stake_units, trade.entry_price_decimal, result)
        trade.result = result
        trade.status = TradeStatus.settled
        trade.profit_loss_units = pnl_units
        if trade.stake_dollars is not None:
            unit_dollars = (
                trade.stake_dollars / trade.stake_units if trade.stake_units else 0.0
            )
            trade.profit_loss_dollars = pnl_units * unit_dollars
        trade.settled_at = datetime.utcnow()
        await self.apply_clv(trade)

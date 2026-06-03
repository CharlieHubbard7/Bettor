"""The Odds API polling and normalization service.

Fetches odds for active sports, persists the raw responses append-only, normalizes them
into queryable ``odds_lines`` rows, and tracks credit usage. In development without a
configured API key it loads a local fixture so the full stack runs without spending
credits.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.no_vig import decimal_to_american
from app.config import Settings
from app.db.models import (
    ApiUsageLog,
    ClosingLine,
    Event,
    OddsLine,
    OddsSnapshot,
    Sport,
)

ODDS_API_BASE_URL = "https://api.the-odds-api.com"
DEFAULT_REGIONS = "us"
DEFAULT_MARKETS = "h2h,spreads,totals"
DEFAULT_BOOKMAKERS = "pinnacle,draftkings,fanduel,betmgm,caesars"

# Player-prop markets are only available on the per-event odds endpoint, not the
# bulk sport-odds endpoint, so they are polled separately per event.
PLAYER_PROP_MARKETS = [
    "player_points",
    "player_rebounds",
    "player_assists",
    "player_pass_tds",
    "player_rush_yards",
    "player_receiving_yards",
]

# Exponential backoff for HTTP 429 (rate-limited) responses.
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.0

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "sample_odds_response.json"
)


def _parse_api_datetime(value: str) -> datetime:
    """Parse an ISO-8601 (Z-suffixed) timestamp into a naive UTC datetime."""
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).replace(tzinfo=None)


class OddsIngestionService:
    """Polls The Odds API and persists normalized odds for active sports."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Initialize the service.

        Args:
            session: Async DB session to read/write through.
            settings: Application settings (API key, environment, etc.).
        """
        self.session = session
        self.settings = settings

    @property
    def _use_fixture(self) -> bool:
        """Whether to serve fixture data instead of calling the live API.

        True in development when no usable API key is configured — this lets the stack
        run end-to-end without burning credits.
        """
        return self.settings.is_development and not self.settings.odds_api_key_is_configured

    async def fetch_and_store_sports(self) -> None:
        """Sync the ``sports`` table from ``/v4/sports``.

        In fixture mode, seeds the three sports the demo data uses (NFL, NBA, MLB) so
        downstream polling has active sports to iterate.
        """
        if self._use_fixture:
            await self._seed_fixture_sports()
            return

        url = f"{ODDS_API_BASE_URL}/v4/sports"
        params = {"apiKey": self.settings.odds_api_key}
        response = await self._request_with_backoff("GET", url, params=params)
        await self._log_api_usage("/v4/sports", None, response)
        payload = response.json()

        for item in payload:
            await self._upsert_sport(
                sport_key=item["key"],
                title=item.get("title", item["key"]),
                active=bool(item.get("active", False)),
            )
        await self.session.commit()
        logger.info("Synced {} sports from The Odds API", len(payload))

    async def poll_sport(self, sport_key: str) -> None:
        """Fetch, store, and normalize odds for all events in a sport.

        Args:
            sport_key: The Odds API sport key, e.g. ``americanfootball_nfl``.
        """
        events_payload = await self._fetch_sport_odds(sport_key)
        snapshot_time = datetime.utcnow()

        line_count = 0
        for event_blob in events_payload:
            await self._upsert_event(event_blob)
            snapshot = OddsSnapshot(
                event_id=event_blob["id"],
                raw_json=event_blob,
                snapshot_time=snapshot_time,
                credits_used=0,
                credits_remaining=0,
            )
            self.session.add(snapshot)
            await self.session.flush()  # assign snapshot.id for the FK
            line_count += self._normalize_event_lines(
                event_blob, snapshot.id, snapshot_time
            )

        await self.session.commit()
        logger.info(
            "Polled sport {} — {} events, {} odds lines",
            sport_key,
            len(events_payload),
            line_count,
        )

    async def poll_player_props(self, sport_key: str, event_id: str) -> None:
        """Fetch and store player-prop odds for a single event.

        Player props are only served by the per-event odds endpoint, so they require
        one call per event. No-ops in fixture mode (props are not in the fixture).

        Args:
            sport_key: The Odds API sport key.
            event_id: The event to fetch props for.
        """
        if self._use_fixture:
            logger.debug("Skipping player props for {} (fixture mode)", event_id)
            return

        url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": self.settings.odds_api_key,
            "regions": DEFAULT_REGIONS,
            "markets": ",".join(PLAYER_PROP_MARKETS),
            "bookmakers": DEFAULT_BOOKMAKERS,
            "oddsFormat": "decimal",
        }
        response = await self._request_with_backoff("GET", url, params=params)
        await self._log_api_usage(
            f"/v4/sports/{sport_key}/events/{event_id}/odds", sport_key, response
        )
        event_blob = response.json()
        if not event_blob.get("bookmakers"):
            return

        snapshot_time = datetime.utcnow()
        snapshot = OddsSnapshot(
            event_id=event_blob["id"],
            raw_json=event_blob,
            snapshot_time=snapshot_time,
        )
        self.session.add(snapshot)
        await self.session.flush()
        self._normalize_event_lines(event_blob, snapshot.id, snapshot_time)
        await self.session.commit()

    async def poll_all_active_sports(self) -> None:
        """Poll every sport flagged ``active`` in the ``sports`` table."""
        result = await self.session.execute(
            select(Sport.sport_key).where(Sport.active.is_(True))
        )
        sport_keys = [row[0] for row in result.all()]
        if not sport_keys:
            logger.warning("No active sports to poll")
            return
        for sport_key in sport_keys:
            try:
                await self.poll_sport(sport_key)
            except httpx.HTTPError as exc:
                logger.error("Failed to poll {}: {}", sport_key, exc)

    async def mark_closing_lines(self) -> None:
        """Mark the final odds line per event/market/bookmaker/outcome as closing.

        For every event whose ``commence_time`` has passed, find the latest snapshot of
        each distinct line and set ``is_closing_line=True``, then upsert it into
        ``closing_lines`` as the CLV reference price.
        """
        now = datetime.utcnow()
        started = await self.session.execute(
            select(Event.id).where(Event.commence_time <= now)
        )
        event_ids = [row[0] for row in started.all()]
        if not event_ids:
            return

        marked = 0
        for event_id in event_ids:
            result = await self.session.execute(
                select(OddsLine)
                .where(OddsLine.event_id == event_id)
                .order_by(OddsLine.snapshot_timestamp.asc())
            )
            lines = result.scalars().all()

            # Keep the latest line per distinct key (iteration is ascending by time).
            latest: dict[tuple, OddsLine] = {}
            for line in lines:
                key = (
                    line.market_key,
                    line.bookmaker_key,
                    line.outcome_name,
                    line.point,
                    line.player_name,
                )
                latest[key] = line

            for line in latest.values():
                if not line.is_closing_line:
                    line.is_closing_line = True
                    marked += 1
                await self._upsert_closing_line(line)

        await self.session.commit()
        if marked:
            logger.info("Marked {} closing lines across {} events", marked, len(event_ids))

    # --- internal helpers ------------------------------------------------------------

    async def _fetch_sport_odds(self, sport_key: str) -> list[dict]:
        """Return the raw event-odds payload for a sport (fixture or live API)."""
        if self._use_fixture:
            logger.info("Using fixture odds data for {} (no API key configured)", sport_key)
            return self._load_fixture()

        url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/odds"
        params = {
            "apiKey": self.settings.odds_api_key,
            "regions": DEFAULT_REGIONS,
            "markets": DEFAULT_MARKETS,
            "bookmakers": DEFAULT_BOOKMAKERS,
            "oddsFormat": "decimal",
        }
        response = await self._request_with_backoff("GET", url, params=params)
        await self._log_api_usage(f"/v4/sports/{sport_key}/odds", sport_key, response)
        return response.json()

    def _load_fixture(self) -> list[dict]:
        """Load and return the bundled fixture odds payload."""
        with FIXTURE_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _normalize_event_lines(
        self, event_blob: dict, snapshot_id, snapshot_time: datetime
    ) -> int:
        """Parse one event's bookmaker blob into OddsLine rows. Returns the count added."""
        count = 0
        for bookmaker in event_blob.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    decimal_price = float(outcome["price"])
                    self.session.add(
                        OddsLine(
                            snapshot_id=snapshot_id,
                            event_id=event_blob["id"],
                            sport_key=event_blob["sport_key"],
                            commence_time=_parse_api_datetime(
                                event_blob["commence_time"]
                            ),
                            home_team=event_blob["home_team"],
                            away_team=event_blob["away_team"],
                            bookmaker_key=bookmaker["key"],
                            market_key=market["key"],
                            outcome_name=outcome["name"],
                            price_decimal=decimal_price,
                            price_american=decimal_to_american(decimal_price),
                            point=outcome.get("point"),
                            player_name=outcome.get("description"),
                            snapshot_timestamp=snapshot_time,
                        )
                    )
                    count += 1
        return count

    async def _upsert_event(self, event_blob: dict) -> None:
        """Insert or update an Event from an API event blob."""
        event = await self.session.get(Event, event_blob["id"])
        commence = _parse_api_datetime(event_blob["commence_time"])
        if event is None:
            self.session.add(
                Event(
                    id=event_blob["id"],
                    sport_key=event_blob["sport_key"],
                    commence_time=commence,
                    home_team=event_blob["home_team"],
                    away_team=event_blob["away_team"],
                    completed=False,
                )
            )
            # Ensure the sport row exists to satisfy the FK.
            await self._ensure_sport(event_blob["sport_key"], event_blob.get("sport_title"))
        else:
            event.commence_time = commence
            event.home_team = event_blob["home_team"]
            event.away_team = event_blob["away_team"]

    async def _ensure_sport(self, sport_key: str, title: str | None) -> None:
        """Create the sport row if it does not yet exist (active by default)."""
        sport = await self.session.get(Sport, sport_key)
        if sport is None:
            self.session.add(
                Sport(sport_key=sport_key, title=title or sport_key, active=True)
            )

    async def _upsert_sport(self, sport_key: str, title: str, active: bool) -> None:
        """Insert or update a Sport row."""
        sport = await self.session.get(Sport, sport_key)
        if sport is None:
            self.session.add(Sport(sport_key=sport_key, title=title, active=active))
        else:
            sport.title = title
            sport.active = active
            sport.last_updated = datetime.utcnow()

    async def _upsert_closing_line(self, line: OddsLine) -> None:
        """Insert or update the ClosingLine for an odds line's distinct key."""
        result = await self.session.execute(
            select(ClosingLine).where(
                ClosingLine.event_id == line.event_id,
                ClosingLine.market_key == line.market_key,
                ClosingLine.bookmaker_key == line.bookmaker_key,
                ClosingLine.outcome_name == line.outcome_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            self.session.add(
                ClosingLine(
                    event_id=line.event_id,
                    sport_key=line.sport_key,
                    bookmaker_key=line.bookmaker_key,
                    market_key=line.market_key,
                    outcome_name=line.outcome_name,
                    player_name=line.player_name,
                    point=line.point,
                    price_american=line.price_american,
                    price_decimal=line.price_decimal,
                )
            )
        else:
            existing.price_american = line.price_american
            existing.price_decimal = line.price_decimal
            existing.point = line.point

    async def _seed_fixture_sports(self) -> None:
        """Seed NFL/NBA/MLB as active sports for fixture-mode development."""
        demo = {
            "americanfootball_nfl": "NFL",
            "basketball_nba": "NBA",
            "baseball_mlb": "MLB",
        }
        for key, title in demo.items():
            await self._upsert_sport(key, title, active=True)
        await self.session.commit()
        logger.info("Seeded {} demo sports (fixture mode)", len(demo))

    async def _request_with_backoff(
        self, method: str, url: str, *, params: dict
    ) -> httpx.Response:
        """Issue an HTTP request, retrying 429s with exponential backoff.

        Raises:
            httpx.HTTPStatusError: On non-429 error responses, or after retries exhaust.
        """
        backoff = INITIAL_BACKOFF_SECONDS
        last_response: httpx.Response | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                response = await client.request(method, url, params=params)
                if response.status_code == 429:
                    last_response = response
                    logger.warning(
                        "429 rate-limited on {} (attempt {}/{}), backing off {}s",
                        url,
                        attempt,
                        MAX_RETRIES,
                        backoff,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                    continue
                response.raise_for_status()
                return response
        assert last_response is not None
        last_response.raise_for_status()
        return last_response  # pragma: no cover

    async def _log_api_usage(
        self, endpoint: str, sport_key: str | None, response: httpx.Response
    ) -> None:
        """Record an Odds API call's credit usage in ``api_usage_log``."""
        used = int(response.headers.get("x-requests-last", 0) or 0)
        remaining = int(response.headers.get("x-requests-remaining", 0) or 0)
        self.session.add(
            ApiUsageLog(
                endpoint=endpoint,
                sport_key=sport_key,
                credits_used=used,
                credits_remaining=remaining,
                response_status=response.status_code,
            )
        )

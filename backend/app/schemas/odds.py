"""Pydantic schemas for odds and edge-opportunity responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SportResponse(BaseModel):
    """A tracked sport."""

    model_config = ConfigDict(from_attributes=True)

    sport_key: str
    title: str
    active: bool
    last_updated: datetime


class EventResponse(BaseModel):
    """An upcoming or completed event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    completed: bool
    home_score: int | None = None
    away_score: int | None = None


class OddsLineResponse(BaseModel):
    """A single normalized odds line (mirrors the ``odds_lines`` table)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    sport_key: str
    bookmaker_key: str
    market_key: str
    outcome_name: str
    price_american: int
    price_decimal: float
    point: float | None = None
    player_name: str | None = None
    snapshot_timestamp: datetime
    is_closing_line: bool


class EdgeOpportunityResponse(BaseModel):
    """A flagged positive-EV opportunity (mirrors the ``EdgeOpportunity`` dataclass)."""

    event_id: str
    market_key: str
    outcome_name: str
    player_name: str | None = None
    our_prob: float
    book_implied_prob: float
    edge_pct: float = Field(description="our_prob - book_implied_prob, as a fraction.")
    best_book: str
    best_price_american: int
    best_price_decimal: float
    sharp_anchor_book: str
    kelly_fraction: float
    recommended_stake_units: float
    # Enrichment for the UI — populated by the route when available.
    home_team: str | None = None
    away_team: str | None = None
    commence_time: datetime | None = None


class EventOddsResponse(BaseModel):
    """All current odds for an event plus any edge calculations."""

    event: EventResponse
    lines: list[OddsLineResponse]
    opportunities: list[EdgeOpportunityResponse]

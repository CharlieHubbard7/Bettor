"""Pydantic schemas for trade creation, update, and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TradeResult, TradeStatus, TradeType


class TradeCreate(BaseModel):
    """Request body for logging a new trade.

    Kelly fraction and stake are computed server-side from ``our_prob`` and the entry
    price unless explicitly provided.
    """

    event_id: str
    market_key: str
    outcome_name: str
    player_name: str | None = None
    entry_price_american: int
    our_prob: float = Field(gt=0.0, lt=1.0, description="Our true probability.")
    sharp_consensus_prob: float = Field(gt=0.0, lt=1.0)
    bookmaker: str
    stake_dollars: float | None = None
    trade_type: TradeType = TradeType.paper
    notes: str | None = None


class TradeUpdate(BaseModel):
    """Request body for updating a trade (notes or voiding)."""

    notes: str | None = None
    status: TradeStatus | None = None


class TradeResponse(BaseModel):
    """A full trade record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    market_key: str
    outcome_name: str
    player_name: str | None = None
    entry_price_american: int
    entry_price_decimal: float
    our_prob: float
    sharp_consensus_prob: float
    edge_pct: float
    kelly_fraction: float
    stake_units: float
    stake_dollars: float | None = None
    bookmaker: str
    trade_type: TradeType
    status: TradeStatus
    result: TradeResult | None = None
    closing_price_american: int | None = None
    clv: float | None = None
    profit_loss_units: float | None = None
    profit_loss_dollars: float | None = None
    created_at: datetime
    settled_at: datetime | None = None
    notes: str | None = None

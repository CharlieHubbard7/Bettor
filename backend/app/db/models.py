"""All SQLAlchemy ORM models for Bettor.

This module is the canonical schema; every Alembic migration derives from it. Models use
SQLAlchemy 2.0 typed mapping (``Mapped`` / ``mapped_column``). UUID primary keys use the
portable :class:`sqlalchemy.Uuid` type (native UUID on Postgres, CHAR on SQLite) so the
same models run against both the Postgres prod DB and the in-memory SQLite test DB.
"""

import enum
import uuid
from datetime import date as date_type, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Return the current naive UTC timestamp (all DateTime columns store UTC)."""
    return datetime.utcnow()


class TradeType(str, enum.Enum):
    """Whether a trade is a paper (simulated) or real-money bet."""

    paper = "paper"
    real = "real"


class TradeStatus(str, enum.Enum):
    """Lifecycle status of a trade."""

    open = "open"
    settled = "settled"
    void = "void"


class TradeResult(str, enum.Enum):
    """Settlement outcome of a trade."""

    win = "win"
    loss = "loss"
    push = "push"


def _enum_column(enum_cls: type[enum.Enum]) -> SAEnum:
    """Build a portable ``Enum`` column that stores the enum *values* (not names)."""
    return SAEnum(
        enum_cls,
        values_callable=lambda e: [member.value for member in e],
        native_enum=False,
        validate_strings=True,
    )


class Sport(Base):
    """A sport we may track odds for (e.g. ``americanfootball_nfl``)."""

    __tablename__ = "sports"

    sport_key: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<Sport key={self.sport_key!r} active={self.active}>"


class Event(Base):
    """A single game/match, identified by The Odds API event id."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sport_key: Mapped[str] = mapped_column(
        String, ForeignKey("sports.sport_key"), nullable=False, index=True
    )
    commence_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Event id={self.id!r} {self.away_team} @ {self.home_team}>"


class OddsSnapshot(Base):
    """Append-only raw blob storage of a full API response. Never mutated."""

    __tablename__ = "odds_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("events.id"), nullable=False, index=True
    )
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    credits_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lines: Mapped[list["OddsLine"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OddsSnapshot id={self.id} event={self.event_id!r}>"


class OddsLine(Base):
    """Normalized, queryable odds data parsed from a snapshot."""

    __tablename__ = "odds_lines"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("odds_snapshots.id"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("events.id"), nullable=False, index=True
    )
    sport_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    commence_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    bookmaker_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    market_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    outcome_name: Mapped[str] = mapped_column(String, nullable=False)
    price_american: Mapped[int] = mapped_column(Integer, nullable=False)
    price_decimal: Mapped[float] = mapped_column(Float, nullable=False)
    point: Mapped[float | None] = mapped_column(Float, nullable=True)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    is_closing_line: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    snapshot: Mapped["OddsSnapshot"] = relationship(back_populates="lines")

    def __repr__(self) -> str:
        return (
            f"<OddsLine {self.bookmaker_key}:{self.market_key}:{self.outcome_name} "
            f"@ {self.price_american}>"
        )


class ClosingLine(Base):
    """The final odds_line before commence_time, per event/market/bookmaker/outcome.

    Populated retroactively from the marked closing ``odds_lines`` rows; used as the CLV
    reference price after a game starts.
    """

    __tablename__ = "closing_lines"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("events.id"), nullable=False, index=True
    )
    sport_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    bookmaker_key: Mapped[str] = mapped_column(String, nullable=False)
    market_key: Mapped[str] = mapped_column(String, nullable=False)
    outcome_name: Mapped[str] = mapped_column(String, nullable=False)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    point: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_american: Mapped[int] = mapped_column(Integer, nullable=False)
    price_decimal: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<ClosingLine event={self.event_id!r} {self.bookmaker_key}:"
            f"{self.market_key}:{self.outcome_name} @ {self.price_american}>"
        )


class Trade(Base):
    """The core trading journal — one row per logged bet."""

    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("events.id"), nullable=False, index=True
    )
    market_key: Mapped[str] = mapped_column(String, nullable=False)
    outcome_name: Mapped[str] = mapped_column(String, nullable=False)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)

    entry_price_american: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price_decimal: Mapped[float] = mapped_column(Float, nullable=False)
    our_prob: Mapped[float] = mapped_column(Float, nullable=False)
    sharp_consensus_prob: Mapped[float] = mapped_column(Float, nullable=False)
    edge_pct: Mapped[float] = mapped_column(Float, nullable=False)
    kelly_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    stake_units: Mapped[float] = mapped_column(Float, nullable=False)
    stake_dollars: Mapped[float | None] = mapped_column(Float, nullable=True)
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)

    trade_type: Mapped[TradeType] = mapped_column(
        _enum_column(TradeType), nullable=False, default=TradeType.paper
    )
    status: Mapped[TradeStatus] = mapped_column(
        _enum_column(TradeStatus), nullable=False, default=TradeStatus.open, index=True
    )
    result: Mapped[TradeResult | None] = mapped_column(
        _enum_column(TradeResult), nullable=True
    )

    closing_price_american: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss_units: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss_dollars: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Trade id={self.id} {self.outcome_name!r} edge={self.edge_pct:.3f} "
            f"status={self.status.value}>"
        )


class BankrollSnapshot(Base):
    """A daily snapshot of bankroll state and that day's P&L."""

    __tablename__ = "bankroll_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    date: Mapped[date_type] = mapped_column(
        Date, nullable=False, unique=True, index=True
    )
    starting_bankroll: Mapped[float] = mapped_column(Float, nullable=False)
    ending_bankroll: Mapped[float] = mapped_column(Float, nullable=False)
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    units_won: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    units_lost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roi_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cumulative_roi_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<BankrollSnapshot {self.date} ${self.ending_bankroll:.2f}>"


class ApiUsageLog(Base):
    """One row per outbound Odds API request, for credit tracking."""

    __tablename__ = "api_usage_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    sport_key: Mapped[str | None] = mapped_column(String, nullable=True)
    credits_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    called_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<ApiUsageLog {self.endpoint} status={self.response_status} "
            f"used={self.credits_used}>"
        )

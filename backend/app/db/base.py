"""Async SQLAlchemy engine, session factory, and the declarative base.

This module owns the single async engine and session maker for the app. Models import
:class:`Base` from here; routes and services obtain sessions via :func:`get_db`.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _create_engine() -> AsyncEngine:
    """Build the async engine from settings.

    SQLite connections need ``check_same_thread=False`` to be shared across the async
    event loop; Postgres needs no special connect args.
    """
    settings = get_settings()
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )


engine: AsyncEngine = _create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped async session.

    The session is committed implicitly by callers; this dependency guarantees the
    session is always closed, and rolls back on unhandled exceptions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

"""Alembic migration environment.

Uses the application's ``DATABASE_URL`` from settings and the ORM ``Base.metadata`` as
the autogenerate target. Migrations run synchronously: the async driver in the URL is
swapped for its sync equivalent so Alembic's synchronous engine API can be used.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import settings and all models so Base.metadata is fully populated.
from app.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401  (imported for side effect: model registration)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url() -> str:
    """Return the configured DATABASE_URL with the async driver swapped for a sync one."""
    url = get_settings().database_url
    return (
        url.replace("+asyncpg", "")
        .replace("+aiosqlite", "")
        .replace("postgresql+asyncpg", "postgresql")
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live DB connection)."""
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live (synchronous) DB connection."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

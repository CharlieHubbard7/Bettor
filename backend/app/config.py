"""Application configuration.

All settings are read from environment variables (or a ``.env`` file) and validated
at startup via pydantic-settings. The ``.env.example`` is the source of truth for the
available variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings.

    Attributes mirror the variables documented in ``.env.example``. Reading happens
    once at startup; use :func:`get_settings` to obtain the cached singleton.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # The Odds API
    odds_api_key: str = Field(default="", description="The Odds API v4 key.")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./bettor.db",
        description="Async SQLAlchemy connection string.",
    )

    # Security
    secret_key: str = Field(
        default="dev-insecure-change-me",
        description="JWT signing key. Generate with `openssl rand -hex 32`.",
    )

    # Trading configuration
    paper_trading_mode: bool = Field(
        default=True, description="Gates real execution. Never False in Texas."
    )
    active_bankroll: float = Field(default=1000.0, description="Bankroll in dollars.")
    default_kelly_fraction: float = Field(
        default=0.25, description="Fraction of full Kelly to stake (quarter Kelly)."
    )
    edge_threshold: float = Field(
        default=0.02, description="Minimum edge (as a fraction) required to flag a play."
    )
    poll_interval_minutes: int = Field(
        default=5, description="Minutes between odds polls."
    )

    # Runtime
    log_level: str = Field(default="INFO")
    environment: Literal["development", "production"] = Field(default="development")

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: str) -> str:
        """Lower-case and strip the environment string before validation."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @property
    def is_development(self) -> bool:
        """Whether the app is running in the development environment."""
        return self.environment == "development"

    @property
    def odds_api_key_is_configured(self) -> bool:
        """Whether a usable (non-placeholder) Odds API key is present.

        In development, an absent or placeholder key triggers fixture-based ingestion
        so the stack runs without burning API credits.
        """
        key = self.odds_api_key.strip()
        return bool(key) and key.lower() not in {"changeme", "placeholder", "your-key"}


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()

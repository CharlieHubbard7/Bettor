"""FastAPI dependency-injection providers.

Re-exports the DB session dependency and the settings provider so routes can depend on a
single, stable import path.
"""

from app.config import Settings, get_settings
from app.db.base import get_db

__all__ = ["get_db", "get_settings", "Settings"]

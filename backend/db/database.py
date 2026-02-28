"""Database connection and session management.

Provides engine, SessionLocal, and Base for use across the application
and scraper scripts. Configuration is read from core.config.settings
(which loads DATABASE_URL from .env).

The canonical FastAPI request-scoped get_db() dependency lives in
api/dependencies.py. This module exposes get_db_engine() for scripts
that need the engine directly.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL normalisation — SQLAlchemy requires "postgresql://", not "postgres://"
# ---------------------------------------------------------------------------

_db_url = settings.database_url
if _db_url and _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

if not _db_url:
    logger.warning("DATABASE_URL is not set — engine will not be usable")
else:
    logger.debug("DATABASE_URL loaded")

# ---------------------------------------------------------------------------
# Engine
# Note: pool_pre_ping re-validates connections before use, which avoids
# stale-connection errors after Supabase's idle timeout.
# ---------------------------------------------------------------------------

engine = create_engine(
    _db_url or "postgresql://",   # placeholder keeps create_engine from raising at import
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "connect_timeout": 10,
        "options": "-c client_encoding=utf8",
    },
)

# ---------------------------------------------------------------------------
# Session factory and ORM base
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db_engine():
    """Return the shared engine (used by scraper scripts)."""
    return engine
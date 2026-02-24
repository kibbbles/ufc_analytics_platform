"""
dependencies.py — FastAPI dependency injection

Provides get_db() for use with Depends() in route handlers, wrapping the
session factory from db.database so FastAPI manages the session lifecycle
(open on request start, close on request end, even if an error occurs).

Usage in a route handler:
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from api.dependencies import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        result = db.execute(text("SELECT 1"))
        ...
"""

from typing import Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, guaranteed to close after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> bool:
    """Execute SELECT 1 to verify the database is reachable.

    Returns:
        True if the database responds.

    Raises:
        RuntimeError: with a descriptive message if the connection fails.
    """
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        raise RuntimeError(f"Database connectivity check failed: {exc}") from exc
    finally:
        db.close()

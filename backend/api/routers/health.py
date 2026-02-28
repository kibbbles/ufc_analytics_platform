"""api/routers/health.py — Health check endpoints.

Routes (mounted at root, no /api/v1 prefix):
    GET /health        Liveness check — returns env, version, timestamp
    GET /health/db     Readiness check — verifies DB is reachable
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.config import settings
from db.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_VERSION = "1.0.0"


@router.get("/health", summary="Liveness check")
def health():
    """Returns environment, version, and current UTC timestamp."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": _VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/db", summary="Readiness check")
def health_db():
    """Verifies the database is reachable by executing SELECT 1.

    Returns HTTP 200 when connected, HTTP 503 when not.
    Uses a direct SessionLocal() call (not the request-scoped dependency)
    so this works even outside a normal request lifecycle.
    """
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.debug("health/db: database reachable")
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        logger.warning("health/db: database unreachable — %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": str(exc)},
        )
    finally:
        db.close()

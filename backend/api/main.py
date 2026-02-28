"""
main.py — UFC Analytics API entry point

The FastAPI application instance lives here. All middleware, routers,
and startup/shutdown events are registered in this file.

Usage
-----
Development (auto-reloads on file save):
    cd backend
    uvicorn api.main:app --reload --port 8000

Production (multiple worker processes):
    cd backend
    gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

Docs (once running):
    http://localhost:8000/docs    — Swagger UI (interactive)
    http://localhost:8000/redoc   — ReDoc (read-only)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers.health import router as health_router
from api.v1.router import v1_router
from core.config import settings
from core.logging import configure_logging
from core.middleware import RequestIDMiddleware, TimingMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    configure_logging(settings.log_level)
    logger.info(
        "UFC Analytics API starting",
        extra={
            "environment": settings.environment,
            "version": "1.0.0",
            "log_level": settings.log_level,
            "allowed_origins": settings.allowed_origins,
        },
    )
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("UFC Analytics API shutting down")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UFC Analytics API",
    description=(
        "ML-powered UFC fight analytics. "
        "Provides fight outcome predictions, style evolution trends, "
        "and fighter endurance profiles."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware  (add_middleware order matters: last added = outermost = first to
# handle incoming requests)
#
#   Execution order for a request:
#     CORS → RequestID → Timing → route handler
#   Execution order for a response:
#     route handler → Timing → RequestID → CORS
# ---------------------------------------------------------------------------

# Timing — added first so it runs innermost (after RequestID has set the ID)
app.add_middleware(TimingMiddleware)

# RequestID — stamps request.state.request_id and X-Request-ID header
app.add_middleware(RequestIDMiddleware)

# CORS — outermost so browser preflight OPTIONS requests are handled immediately
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return structured JSON for all HTTP errors (404, 422, etc.)."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions: log the traceback, return clean JSON."""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "unhandled exception",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)            # /health, /health/db  (unversioned)
app.include_router(v1_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"], summary="API root")
def root():
    """Confirms the API is running. Returns service name, version, and docs URL."""
    return {
        "service": "UFC Analytics API",
        "version": "1.0.0",
        "docs":    "/docs",
    }

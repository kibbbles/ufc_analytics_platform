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

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analytics, events, fighters, fights, predictions


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before `yield` runs once on startup.
    Code after `yield` runs once on shutdown.

    Startup tasks (added in later tasks):
    - Verify DB connectivity
    - Load ML models into memory
    """
    yield


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
# Middleware
# ---------------------------------------------------------------------------

# CORS — allow the React frontend dev server to call this API.
# In production, replace localhost origins with the deployed frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server (default)
        "http://localhost:3000",   # fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID, timing, and structured error handling middleware added in Task 4.4.


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(fighters.router)
app.include_router(fights.router)
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(predictions.router)


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

"""api/v1/router.py — Aggregates all v1 endpoint routers.

Included in api/main.py under the prefix /api/v1, so final paths are:
    /api/v1/fighters
    /api/v1/fights
    /api/v1/events
    /api/v1/predictions
    /api/v1/analytics
"""

from fastapi import APIRouter

from api.v1.endpoints import analytics, events, fighters, fights, predictions

v1_router = APIRouter()

v1_router.include_router(fighters.router,   prefix="/fighters",   tags=["fighters"])
v1_router.include_router(fights.router,     prefix="/fights",     tags=["fights"])
v1_router.include_router(events.router,     prefix="/events",     tags=["events"])
v1_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
v1_router.include_router(analytics.router,  prefix="/analytics",  tags=["analytics"])

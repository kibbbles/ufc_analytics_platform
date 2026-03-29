"""api/v1/endpoints/upcoming.py — Upcoming event endpoints.

Routes:
    GET /upcoming/events            All upcoming events ordered by date ASC
    GET /upcoming/events/{id}       Single event + full fight card + predictions
    GET /upcoming/fights/{id}       Single fight + prediction
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.upcoming import (
    UpcomingEventListResponse,
    UpcomingEventResponse,
    UpcomingEventWithFightsResponse,
    UpcomingFightPrediction,
    UpcomingFightResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prediction_from_row(row) -> UpcomingFightPrediction | None:
    """Build prediction schema from a DB row — returns None if no prediction exists."""
    if row is None or row["win_prob_a"] is None:
        return None
    return UpcomingFightPrediction(
        win_prob_a=row["win_prob_a"],
        win_prob_b=row["win_prob_b"],
        method_ko_tko=row["method_ko_tko"],
        method_sub=row["method_sub"],
        method_dec=row["method_dec"],
        model_version=row["model_version"],
        features_json=row["features_json"],
    )


# ---------------------------------------------------------------------------
# GET /upcoming/events
# ---------------------------------------------------------------------------

@router.get(
    "/events",
    response_model=UpcomingEventListResponse,
    summary="List all upcoming UFC events",
)
def list_upcoming_events(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            ue.id,
            ue.event_name,
            ue.date_proper   AS event_date,
            ue.location,
            ue.is_numbered,
            COUNT(uf.id)     AS fight_count
        FROM upcoming_events ue
        LEFT JOIN upcoming_fights uf
            ON uf.event_id = ue.id
            AND (uf.archived IS NULL OR uf.archived = FALSE)
        WHERE ue.date_proper >= CURRENT_DATE - INTERVAL '1 day'
        GROUP BY ue.id
        ORDER BY ue.date_proper ASC
    """)).mappings().all()

    return UpcomingEventListResponse(
        data=[UpcomingEventResponse(**dict(r)) for r in rows]
    )


# ---------------------------------------------------------------------------
# GET /upcoming/events/{event_id}
# ---------------------------------------------------------------------------

@router.get(
    "/events/{event_id}",
    response_model=UpcomingEventWithFightsResponse,
    summary="Get upcoming event with full fight card",
)
def get_upcoming_event(event_id: str, db: Session = Depends(get_db)):
    event_row = db.execute(text("""
        SELECT
            ue.id,
            ue.event_name,
            ue.date_proper  AS event_date,
            ue.location,
            ue.is_numbered,
            COUNT(uf.id)    AS fight_count
        FROM upcoming_events ue
        LEFT JOIN upcoming_fights uf ON uf.event_id = ue.id
        WHERE ue.id = :event_id
        GROUP BY ue.id
    """), {"event_id": event_id}).mappings().first()

    if event_row is None:
        raise HTTPException(status_code=404, detail=f"Upcoming event '{event_id}' not found")

    fight_rows = db.execute(text("""
        SELECT
            uf.id,
            uf.event_id,
            uf.fighter_a_name,
            uf.fighter_b_name,
            uf.fighter_a_id,
            uf.fighter_b_id,
            uf.weight_class,
            uf.is_title_fight,
            uf.odds_a,
            uf.odds_b,
            uf.implied_prob_a,
            uf.implied_prob_b,
            up.win_prob_a,
            up.win_prob_b,
            up.method_ko_tko,
            up.method_sub,
            up.method_dec,
            up.model_version,
            up.features_json
        FROM upcoming_fights uf
        LEFT JOIN upcoming_predictions up ON up.fight_id = uf.id
        WHERE uf.event_id = :event_id
          AND (uf.archived IS NULL OR uf.archived = FALSE)
        ORDER BY uf.position ASC NULLS LAST, uf.id ASC
    """), {"event_id": event_id}).mappings().all()

    fights = [
        UpcomingFightResponse(
            **{k: v for k, v in dict(r).items()
               if k in UpcomingFightResponse.model_fields},
            prediction=_prediction_from_row(r),
        )
        for r in fight_rows
    ]

    return UpcomingEventWithFightsResponse(**dict(event_row), fights=fights)


# ---------------------------------------------------------------------------
# GET /upcoming/fights/{fight_id}
# ---------------------------------------------------------------------------

@router.get(
    "/fights/{fight_id}",
    response_model=UpcomingFightResponse,
    summary="Get single upcoming fight with prediction",
)
def get_upcoming_fight(fight_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT
            uf.id,
            uf.event_id,
            uf.fighter_a_name,
            uf.fighter_b_name,
            uf.fighter_a_id,
            uf.fighter_b_id,
            uf.weight_class,
            uf.is_title_fight,
            uf.odds_a,
            uf.odds_b,
            uf.implied_prob_a,
            uf.implied_prob_b,
            up.win_prob_a,
            up.win_prob_b,
            up.method_ko_tko,
            up.method_sub,
            up.method_dec,
            up.model_version,
            up.features_json
        FROM upcoming_fights uf
        LEFT JOIN upcoming_predictions up ON up.fight_id = uf.id
        WHERE uf.id = :fight_id
          AND (uf.archived IS NULL OR uf.archived = FALSE)
    """), {"fight_id": fight_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Upcoming fight '{fight_id}' not found")

    return UpcomingFightResponse(
        **{k: v for k, v in dict(row).items()
           if k in UpcomingFightResponse.model_fields},
        prediction=_prediction_from_row(row),
    )

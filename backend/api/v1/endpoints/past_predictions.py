"""api/v1/endpoints/past_predictions.py — Model scorecard endpoint.

Routes:
    GET /past-predictions                          Summary stats + recent predictions list
    GET /past-predictions/events                   Paginated event list with accuracy per event
    GET /past-predictions/events/{event_id}        All fight predictions for a given event
"""

from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.past_prediction import (
    PastPredictionItem,
    PastPredictionSummary,
    PastPredictionsResponse,
    PastPredictionEventItem,
    PastPredictionEventsResponse,
    PastPredictionEventDetail,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PastPredictionsResponse,
    summary="Model scorecard — summary accuracy + recent prediction outcomes",
)
def get_past_predictions(
    limit: int = Query(default=20, ge=1, le=200, description="Number of recent predictions to return"),
    db: Session = Depends(get_db),
) -> PastPredictionsResponse:
    # ---- Summary row --------------------------------------------------------
    summary_row = db.execute(text("""
        SELECT
            COUNT(*)                                                          AS total_fights,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)                      AS correct,
            SUM(CASE WHEN confidence >= 0.65 THEN 1 ELSE 0 END)              AS high_conf_fights,
            SUM(CASE WHEN is_correct AND confidence >= 0.65 THEN 1 ELSE 0 END) AS high_conf_correct,
            MIN(event_date)                                                   AS date_from,
            MAX(event_date)                                                   AS date_to
        FROM past_predictions
    """)).mappings().first()

    total_fights     = int(summary_row["total_fights"] or 0)
    correct          = int(summary_row["correct"] or 0)
    high_conf_fights = int(summary_row["high_conf_fights"] or 0)
    high_conf_correct= int(summary_row["high_conf_correct"] or 0)

    accuracy          = correct / total_fights if total_fights > 0 else 0.0
    high_conf_accuracy= high_conf_correct / high_conf_fights if high_conf_fights > 0 else 0.0

    date_from_val = summary_row["date_from"]
    date_to_val   = summary_row["date_to"]

    years_rows = db.execute(text("""
        SELECT DISTINCT EXTRACT(YEAR FROM event_date)::int AS yr
        FROM past_predictions
        WHERE event_date IS NOT NULL
        ORDER BY yr DESC
    """)).scalars().all()

    summary = PastPredictionSummary(
        total_fights=total_fights,
        correct=correct,
        accuracy=accuracy,
        high_conf_fights=high_conf_fights,
        high_conf_correct=high_conf_correct,
        high_conf_accuracy=high_conf_accuracy,
        date_from=str(date_from_val) if date_from_val else "",
        date_to=str(date_to_val) if date_to_val else "",
        available_years=[int(y) for y in years_rows],
    )

    # ---- Recent predictions -------------------------------------------------
    if total_fights == 0:
        return PastPredictionsResponse(summary=summary, recent=[])

    recent_rows = db.execute(text("""
        SELECT
            fight_id,
            event_id,
            event_name,
            event_date,
            fighter_a_id,
            fighter_b_id,
            fighter_a_name,
            fighter_b_name,
            weight_class,
            win_prob_a,
            win_prob_b,
            pred_method_ko_tko,
            pred_method_sub,
            pred_method_dec,
            predicted_winner_id,
            predicted_method,
            actual_winner_id,
            actual_method,
            is_correct,
            confidence,
            is_upset
        FROM past_predictions
        ORDER BY event_date DESC, fight_id
        LIMIT :limit
    """), {"limit": limit}).mappings().all()

    recent = [PastPredictionItem(**dict(r)) for r in recent_rows]

    return PastPredictionsResponse(summary=summary, recent=recent)


@router.get(
    "/events",
    response_model=PastPredictionEventsResponse,
    summary="Paginated list of events that have model predictions, most recent first",
)
def list_past_prediction_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: str | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
) -> PastPredictionEventsResponse:
    params: dict = {}
    conditions: list[str] = []

    if search:
        conditions.append("LOWER(event_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"
    if year:
        conditions.append("EXTRACT(YEAR FROM event_date) = :year")
        params["year"] = year

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total: int = db.execute(text(f"""
        SELECT COUNT(DISTINCT event_id)
        FROM past_predictions
        {where}
    """), params).scalar() or 0

    params["limit"]  = page_size
    params["offset"] = (page - 1) * page_size

    rows = db.execute(text(f"""
        SELECT
            event_id,
            MAX(event_name)   AS event_name,
            MAX(event_date)   AS event_date,
            COUNT(*)          AS fight_count,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct_count
        FROM past_predictions
        {where}
        GROUP BY event_id
        ORDER BY MAX(event_date) DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    items = [
        PastPredictionEventItem(
            event_id=r["event_id"],
            event_name=r["event_name"],
            event_date=r["event_date"],
            fight_count=int(r["fight_count"]),
            correct_count=int(r["correct_count"]),
            accuracy=int(r["correct_count"]) / int(r["fight_count"]) if r["fight_count"] else 0.0,
        )
        for r in rows
    ]

    return PastPredictionEventsResponse(
        data=items,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=PastPredictionEventDetail,
    summary="All model predictions for a specific past event",
)
def get_past_prediction_event(
    event_id: str,
    db: Session = Depends(get_db),
) -> PastPredictionEventDetail:
    rows = db.execute(text("""
        SELECT
            fight_id, event_id, event_name, event_date,
            fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
            weight_class, win_prob_a, win_prob_b,
            pred_method_ko_tko, pred_method_sub, pred_method_dec,
            predicted_winner_id, predicted_method,
            actual_winner_id, actual_method,
            is_correct, confidence, is_upset
        FROM past_predictions
        WHERE event_id = :event_id
        ORDER BY fight_id
    """), {"event_id": event_id}).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No predictions found for event '{event_id}'")

    fights = [PastPredictionItem(**dict(r)) for r in rows]
    correct_count = sum(1 for f in fights if f.is_correct)
    sample = fights[0]

    return PastPredictionEventDetail(
        event_id=event_id,
        event_name=sample.event_name,
        event_date=sample.event_date,
        fight_count=len(fights),
        correct_count=correct_count,
        accuracy=correct_count / len(fights) if fights else 0.0,
        fights=fights,
    )

"""api/v1/endpoints/past_predictions.py — Model scorecard endpoint.

Routes:
    GET /past-predictions?limit=20    Summary stats + recent predictions list
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.past_prediction import (
    PastPredictionItem,
    PastPredictionSummary,
    PastPredictionsResponse,
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

    summary = PastPredictionSummary(
        total_fights=total_fights,
        correct=correct,
        accuracy=accuracy,
        high_conf_fights=high_conf_fights,
        high_conf_correct=high_conf_correct,
        high_conf_accuracy=high_conf_accuracy,
        date_from=str(date_from_val) if date_from_val else "",
        date_to=str(date_to_val) if date_to_val else "",
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

"""api/v1/endpoints/predictions.py — Fight outcome prediction endpoint.

Routes:
    POST /predictions/fight-outcome

ML model integration is added in Task 6. Until then this endpoint validates
that both fighters exist and returns a stub 50/50 response so the frontend
can be wired up end-to-end before the model is ready.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.prediction import MethodProbabilities, PredictionRequest, PredictionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/fight-outcome",
    response_model=PredictionResponse,
    summary="Predict fight outcome",
)
def predict_fight_outcome(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    # Validate both fighters exist before returning any prediction
    for fid in (request.fighter_a_id, request.fighter_b_id):
        exists = db.execute(
            text("SELECT 1 FROM fighter_details WHERE id = :id"),
            {"id": fid},
        ).first()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"Fighter '{fid}' not found")

    # --- Stub response (Task 6 will replace this with the real model) ---
    logger.info(
        "prediction stub called",
        extra={
            "fighter_a_id": request.fighter_a_id,
            "fighter_b_id": request.fighter_b_id,
        },
    )
    return PredictionResponse(
        fighter_a_id=request.fighter_a_id,
        fighter_b_id=request.fighter_b_id,
        predicted_winner_id=request.fighter_a_id,
        win_probability=0.5,
        confidence=0.0,
        method_probabilities=MethodProbabilities(
            ko_tko=0.33,
            submission=0.33,
            decision=0.34,
        ),
        similar_fight_ids=[],
    )

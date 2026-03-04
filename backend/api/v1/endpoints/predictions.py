"""api/v1/endpoints/predictions.py — Fight outcome prediction endpoint.

Routes:
    POST /predictions/fight-outcome
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from features.pipeline import build_prediction_features
from ml.predictor import predict
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
    req: Request,
    db: Session = Depends(get_db),
):
    # ---- Validate both fighters exist ------------------------------------
    for fid in (request.fighter_a_id, request.fighter_b_id):
        exists = db.execute(
            text("SELECT 1 FROM fighter_details WHERE id = :id"),
            {"id": fid},
        ).first()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"Fighter '{fid}' not found")

    # ---- Check models are loaded ----------------------------------------
    store = getattr(req.app.state, "models", None)
    if store is None or not store.ready:
        raise HTTPException(
            status_code=503,
            detail="Prediction models not available — run ml.run_train first",
        )

    # ---- Build features -------------------------------------------------
    # Apply any slider overrides from the request
    overrides: dict = {}
    if request.fighter_a_weight_lbs    is not None: overrides["fighter_a_weight_lbs"]    = request.fighter_a_weight_lbs
    if request.fighter_a_reach_inches  is not None: overrides["fighter_a_reach_inches"]  = request.fighter_a_reach_inches
    if request.fighter_a_age           is not None: overrides["fighter_a_age"]           = request.fighter_a_age
    if request.fighter_b_weight_lbs    is not None: overrides["fighter_b_weight_lbs"]    = request.fighter_b_weight_lbs
    if request.fighter_b_reach_inches  is not None: overrides["fighter_b_reach_inches"]  = request.fighter_b_reach_inches
    if request.fighter_b_age           is not None: overrides["fighter_b_age"]           = request.fighter_b_age

    feat = build_prediction_features(
        fighter_a_id=request.fighter_a_id,
        fighter_b_id=request.fighter_b_id,
        weight_class=request.weight_class,
    )

    # Apply slider overrides to the feature dict
    if overrides:
        _apply_slider_overrides(feat, overrides, request.fighter_a_id, request.fighter_b_id)

    # ---- Run inference --------------------------------------------------
    result = predict(store, feat)

    winner_id = request.fighter_a_id if result["predicted_winner"] == "a" else request.fighter_b_id

    logger.info(
        "prediction: a=%s b=%s  p_a_wins=%.3f  method=KO:%.2f/SUB:%.2f/DEC:%.2f",
        request.fighter_a_id, request.fighter_b_id,
        result["win_probability"],
        result["ko_tko"], result["submission"], result["decision"],
    )

    return PredictionResponse(
        fighter_a_id=request.fighter_a_id,
        fighter_b_id=request.fighter_b_id,
        predicted_winner_id=winner_id,
        win_probability=result["win_probability"],
        confidence=result["confidence"],
        method_probabilities=MethodProbabilities(
            ko_tko=result["ko_tko"],
            submission=result["submission"],
            decision=result["decision"],
        ),
        similar_fight_ids=[],
    )


def _apply_slider_overrides(feat: dict, overrides: dict, a_id: str, b_id: str) -> None:
    """Mutate feat in-place with slider override values.

    Overrides supply absolute values for a single fighter's physical attributes.
    We re-compute the differential against the other fighter's value already in feat.
    """
    slider_map = {
        "fighter_a_weight_lbs":   ("weight_diff_lbs",    +1),
        "fighter_a_reach_inches": ("reach_diff_inches",  +1),
        "fighter_a_age":          ("age_diff_days",       +365),   # age in years → days approx
        "fighter_b_weight_lbs":   ("weight_diff_lbs",    -1),
        "fighter_b_reach_inches": ("reach_diff_inches",  -1),
        "fighter_b_age":          ("age_diff_days",       -365),
    }
    for key, (feat_col, sign) in slider_map.items():
        if key not in overrides:
            continue
        val = overrides[key]
        current_diff = feat.get(feat_col)
        if current_diff is not None:
            # Back-calculate what the other side's value was, then recompute diff
            if sign > 0:
                # a_val = override; b_val = a_val - current_diff
                other = val - current_diff
                feat[feat_col] = float(val - other)
            else:
                # b_val = override; a_val = current_diff + b_val
                other = current_diff + val
                feat[feat_col] = float(other - val)

"""schemas/prediction.py — ML prediction request/response schemas.

Used by POST /predictions/fight-outcome (Product 1: Fight Outcome Predictor).
ML model integration added in Task 6; until then, endpoints return stub responses.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fighter_a_id: str
    fighter_b_id: str

    # Optional slider overrides — let the UI explore "what if" scenarios
    fighter_a_weight_lbs: Optional[float] = Field(None, gt=0)
    fighter_a_reach_inches: Optional[float] = Field(None, gt=0)
    fighter_a_age: Optional[int] = Field(None, ge=18, le=60)
    fighter_b_weight_lbs: Optional[float] = Field(None, gt=0)
    fighter_b_reach_inches: Optional[float] = Field(None, gt=0)
    fighter_b_age: Optional[int] = Field(None, ge=18, le=60)


class MethodProbabilities(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    ko_tko: float
    submission: float
    decision: float


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fighter_a_id: str
    fighter_b_id: str
    predicted_winner_id: str
    win_probability: float = Field(..., ge=0.0, le=1.0)  # P(fighter_a wins)
    confidence: float = Field(..., ge=0.0, le=1.0)
    method_probabilities: MethodProbabilities
    similar_fight_ids: list[str] = []  # comparable historical fights

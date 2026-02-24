"""
predictions.py — ML prediction endpoints

Routes:
    POST /predictions/fight-outcome     Predict win probability and method for a matchup

Powers Product 1 (Fight Outcome Predictor with Interactive Sliders).
ML model integration added in Task 6. Stub response returned until then.
Implemented in Task 4.5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/predictions", tags=["predictions"])

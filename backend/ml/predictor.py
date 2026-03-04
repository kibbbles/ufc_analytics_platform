"""ml/predictor.py — Real-time inference wrapper.

Takes a feature dict produced by build_prediction_features() and a loaded
ModelStore, and returns win probability + method probabilities.

Public API
----------
predict(store, feat, sel) -> dict
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_SEL_PATH = Path(__file__).parent.parent / "features" / "selected_features.json"


def predict(
    store: Any,                 # ModelStore
    feat: dict,
    sel: dict | None = None,
) -> dict:
    """Run win/loss and method predictions for a feature dict.

    Args:
        store:  Loaded ModelStore (from ml.loader).
        feat:   Feature dict from build_prediction_features().
        sel:    Contents of selected_features.json.  Loaded from disk if None.

    Returns:
        dict with keys:
            win_probability   float  P(fighter_a wins)
            predicted_winner  "a" | "b"
            confidence        float  |prob - 0.5| * 2  (0 = coin-flip, 1 = certain)
            ko_tko            float
            submission        float
            decision          float
    """
    if sel is None:
        with open(_SEL_PATH, encoding="utf-8") as f:
            sel = json.load(f)

    feature_names      = sel["feature_names"]
    categorical        = sel["categorical_features"]
    all_cols           = feature_names + categorical

    # Build single-row DataFrame matching the column order the pipeline expects
    row = pd.DataFrame([{c: feat.get(c) for c in all_cols}])

    # ---- Win / loss prediction -------------------------------------------
    win_proba = store.win_pipeline.predict_proba(row)[0]
    # Class order: [0=fighter_b_wins, 1=fighter_a_wins]
    classes = list(store.win_pipeline.classes_)
    win_prob = float(win_proba[classes.index(1)] if 1 in classes else win_proba[1])

    # ---- Method prediction -----------------------------------------------
    method_proba   = store.method_pipeline.predict_proba(row)[0]
    method_classes = list(store.method_pipeline.classes_)
    method_map     = dict(zip(method_classes, method_proba.tolist()))

    return {
        "win_probability": win_prob,
        "predicted_winner": "a" if win_prob >= 0.5 else "b",
        "confidence": float(abs(win_prob - 0.5) * 2),
        "ko_tko":     method_map.get("ko_tko",     0.0),
        "submission": method_map.get("submission", 0.0),
        "decision":   method_map.get("decision",   0.0),
    }

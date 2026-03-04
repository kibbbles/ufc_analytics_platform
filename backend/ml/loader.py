"""ml/loader.py — Load serialized models from backend/models/ at startup.

Used by the FastAPI lifespan to populate app.state.models so every request
handler can reach the fitted pipelines without re-loading from disk.

Usage
-----
    from ml.loader import ModelStore
    store = ModelStore.load(Path("models"))
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

_HERE       = Path(__file__).parent.parent   # backend/
MODELS_DIR  = _HERE / "models"


@dataclass
class ModelStore:
    """Container for all loaded ML artefacts."""

    win_pipeline:    Any   # fitted sklearn Pipeline  (XGBoost binary)
    method_pipeline: Any   # fitted sklearn Pipeline  (RF multi-class)
    feature_importance: dict = field(default_factory=dict)
    ready: bool = True

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls, models_dir: Path = MODELS_DIR) -> "ModelStore":
        """Load win_loss_v1.joblib, method_v1.joblib and feature_importance.json.

        Raises FileNotFoundError if either model file is missing so the
        lifespan can catch it and mark the store as not-ready.
        """
        win_path    = models_dir / "win_loss_v1.joblib"
        method_path = models_dir / "method_v1.joblib"
        imp_path    = models_dir / "feature_importance.json"

        if not win_path.exists():
            raise FileNotFoundError(f"win model not found: {win_path}")
        if not method_path.exists():
            raise FileNotFoundError(f"method model not found: {method_path}")

        win    = joblib.load(win_path)
        method = joblib.load(method_path)
        feat_imp = json.loads(imp_path.read_text()) if imp_path.exists() else {}

        logger.info("ModelStore: loaded win model from %s", win_path)
        logger.info("ModelStore: loaded method model from %s", method_path)
        return cls(win_pipeline=win, method_pipeline=method, feature_importance=feat_imp)

    @classmethod
    def empty(cls) -> "ModelStore":
        """Sentinel store used when models haven't been trained yet."""
        return cls(win_pipeline=None, method_pipeline=None, ready=False)

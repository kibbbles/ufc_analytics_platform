"""ml/loader.py — Load serialized models from backend/models/ at startup.

Used by the FastAPI lifespan to populate app.state.models so every request
handler can reach the fitted pipelines without re-loading from disk.

Usage
-----
    from ml.loader import ModelStore
    store = ModelStore.load(Path("models"))
"""

from __future__ import annotations

import hashlib
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
    # Content fingerprint of the artefacts these pipelines were loaded from.
    # Retraining rewrites the .joblib files but leaves every version STRING
    # unchanged - MODEL_NAME here and PIPELINE_VERSION in features/pipeline.py
    # are both constants describing the model family and the feature shape, not
    # the fitted weights. Consumers that need to know "are these the same models
    # as last time" have nothing else to compare, so they get this.
    fingerprint: str = "unknown"

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
        fingerprint = cls.fingerprint_of(win_path, method_path)

        logger.info("ModelStore: loaded win model from %s", win_path)
        logger.info("ModelStore: loaded method model from %s", method_path)
        logger.info("ModelStore: artefact fingerprint %s", fingerprint)
        return cls(win_pipeline=win, method_pipeline=method,
                   feature_importance=feat_imp, fingerprint=fingerprint)

    @staticmethod
    def fingerprint_of(*paths: Path) -> str:
        """Short content hash over the given artefact files.

        Hashes bytes rather than mtime so it is stable across a fresh checkout,
        which matters because retrain.yml commits these files and CI clones them
        anew on every run.
        """
        digest = hashlib.sha256()
        for path in paths:
            digest.update(Path(path).read_bytes())
        return digest.hexdigest()[:12]

    @classmethod
    def empty(cls) -> "ModelStore":
        """Sentinel store used when models haven't been trained yet."""
        return cls(win_pipeline=None, method_pipeline=None, ready=False,
                   fingerprint="unloaded")

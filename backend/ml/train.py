"""ml/train.py — Train win/loss and method prediction models.

Reads training_data.parquet + selected_features.json, performs a temporal
train/val/test split, trains two scikit-learn pipelines, evaluates on the
holdout set, serializes to backend/models/, and writes feature_importance.json.

Models
------
1. win_loss_v1.joblib
   XGBoostClassifier binary classifier: P(fighter_a wins)
   Wrapped in CalibratedClassifierCV (isotonic) for well-calibrated probs.

2. method_v1.joblib
   RandomForestClassifier multi-class: ko_tko | submission | decision
   Trained on the subset of fights with a decodable method.

Usage
-----
    cd backend
    python -m ml.run_train          # normal run
    python -m ml.run_train --eval   # evaluate only (no serialization)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

_HERE        = Path(__file__).parent.parent          # backend/
PARQUET_PATH = _HERE / "features" / "training_data.parquet"
SEL_PATH     = _HERE / "features" / "selected_features.json"
MODELS_DIR   = _HERE / "models"

# Ordered weight-class categories (lightest → heaviest)
# Used by OrdinalEncoder so the encoding preserves ordinal meaning.
_WC_ORDER = [
    "Women's Strawweight",
    "Women's Flyweight",
    "Women's Bantamweight",
    "Women's Featherweight",
    "Flyweight",
    "Bantamweight",
    "Featherweight",
    "Lightweight",
    "Welterweight",
    "Middleweight",
    "Light Heavyweight",
    "Heavyweight",
    "Super Heavyweight",
    "Open Weight",
    "Catch Weight",
]

# Method string → label used by the method classifier
_METHOD_LABELS = {
    "ko_tko":     ["KO/TKO", "TKO", "KO"],
    "submission": ["Submission"],
    "decision":   ["Decision - Unanimous", "Decision - Split", "Decision - Majority",
                   "Decision (Unanimous)", "Decision (Split)", "Decision (Majority)",
                   "U-DEC", "S-DEC", "M-DEC"],
}


def _encode_method(raw: str) -> str | None:
    """Map a raw METHOD string to one of ko_tko / submission / decision / None."""
    if pd.isna(raw):
        return None
    m = str(raw).strip().upper()
    if "KO" in m or "TKO" in m:
        return "ko_tko"
    if "SUB" in m:
        return "submission"
    if "DEC" in m:
        return "decision"
    return None   # DQ, No Contest, etc. — excluded from method training


def _build_preprocessor(feature_names: list[str], categorical: list[str]) -> ColumnTransformer:
    """Return a ColumnTransformer for numeric + categorical features."""
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(
            categories=[_WC_ORDER],
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )),
    ])
    return ColumnTransformer([
        ("num", numeric_transformer,      feature_names),
        ("cat", categorical_transformer,  categorical),
    ], remainder="drop")


def train(eval_only: bool = False) -> dict:
    """Run the full training pipeline.

    Args:
        eval_only: If True, skip serialization (useful for CI checks).

    Returns:
        Evaluation metrics dict.
    """
    # ------------------------------------------------------------------ #
    # 1. Load data                                                         #
    # ------------------------------------------------------------------ #
    logger.info("Loading %s", PARQUET_PATH)
    df = pd.read_parquet(PARQUET_PATH)
    logger.info("Parquet: %d rows x %d columns", len(df), len(df.columns))

    with open(SEL_PATH, encoding="utf-8") as f:
        sel = json.load(f)

    feature_names = sel["feature_names"]
    categorical   = sel["categorical_features"]   # ["weight_class"]
    all_features  = feature_names + categorical

    # ------------------------------------------------------------------ #
    # 2. Temporal train / val / test split (70 / 15 / 15)                 #
    # ------------------------------------------------------------------ #
    df = df.sort_values("event_date").reset_index(drop=True)
    n         = len(df)
    train_end = int(n * 0.70)
    val_end   = int(n * 0.85)

    train_df = df.iloc[:train_end]
    val_df   = df.iloc[train_end:val_end]
    test_df  = df.iloc[val_end:]

    logger.info(
        "Split: train=%d (up to %s)  val=%d  test=%d (from %s)",
        len(train_df), train_df["event_date"].max(),
        len(val_df),
        len(test_df),   test_df["event_date"].min(),
    )

    X_train = train_df[all_features]
    y_train = train_df["fighter_a_wins"]
    X_val   = val_df[all_features]
    y_val   = val_df["fighter_a_wins"]
    X_test  = test_df[all_features]
    y_test  = test_df["fighter_a_wins"]

    # ------------------------------------------------------------------ #
    # 3. Win / loss model  (XGBoost binary classifier)                    #
    # ------------------------------------------------------------------ #
    logger.info("Training XGBoost win/loss model...")

    preprocessor = _build_preprocessor(feature_names, categorical)

    xgb = XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    win_base = Pipeline([("pre", preprocessor), ("clf", xgb)])
    win_base.fit(X_train, y_train)

    # Calibrate on validation set
    win_pipeline = CalibratedClassifierCV(win_base, cv="prefit", method="isotonic")
    win_pipeline.fit(X_val, y_val)

    # Evaluate on test set
    y_pred_win  = win_pipeline.predict(X_test)
    y_proba_win = win_pipeline.predict_proba(X_test)[:, 1]
    win_acc     = accuracy_score(y_test, y_pred_win)
    win_auc     = roc_auc_score(y_test, y_proba_win)

    logger.info("Win/loss  accuracy=%.4f  ROC-AUC=%.4f", win_acc, win_auc)
    logger.info("\n%s", classification_report(y_test, y_pred_win, target_names=["B wins", "A wins"]))

    # ------------------------------------------------------------------ #
    # 4. Method model  (Random Forest multi-class)                        #
    # ------------------------------------------------------------------ #
    logger.info("Training Random Forest method model...")

    method_col = df["method"].map(_encode_method)
    df_m = df[method_col.notna()].copy()
    df_m["method_class"] = method_col[method_col.notna()]

    # Same temporal indices for method subset
    m_train = df_m[df_m.index < train_end]
    m_val   = df_m[(df_m.index >= train_end) & (df_m.index < val_end)]
    m_test  = df_m[df_m.index >= val_end]

    logger.info(
        "Method split: train=%d  val=%d  test=%d",
        len(m_train), len(m_val), len(m_test),
    )

    Xm_train = pd.concat([m_train[all_features], m_val[all_features]])
    ym_train = pd.concat([m_train["method_class"], m_val["method_class"]])
    Xm_test  = m_test[all_features]
    ym_test  = m_test["method_class"]

    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    method_preprocessor = _build_preprocessor(feature_names, categorical)
    method_pipeline = Pipeline([("pre", method_preprocessor), ("clf", rf)])
    method_pipeline.fit(Xm_train, ym_train)

    ym_pred   = method_pipeline.predict(Xm_test)
    method_acc = accuracy_score(ym_test, ym_pred)

    logger.info("Method accuracy=%.4f", method_acc)
    logger.info("\n%s", classification_report(ym_test, ym_pred))

    # ------------------------------------------------------------------ #
    # 5. Feature importance                                               #
    # ------------------------------------------------------------------ #
    # XGBoost feature importances from the base estimator inside calibrated wrapper
    try:
        xgb_step = win_base.named_steps["clf"]
        raw_imp  = xgb_step.feature_importances_
        # ColumnTransformer outputs numeric first, then categorical
        col_names = feature_names + categorical
        feat_imp  = {col_names[i]: float(raw_imp[i]) for i in range(len(raw_imp))}
        feat_imp  = dict(sorted(feat_imp.items(), key=lambda x: x[1], reverse=True))
    except Exception:
        feat_imp = {}

    metrics = {
        "win_accuracy": round(float(win_acc), 4),
        "win_roc_auc":  round(float(win_auc), 4),
        "method_accuracy": round(float(method_acc), 4),
        "train_rows":   len(train_df),
        "test_rows":    len(test_df),
        "train_date_range": [
            str(train_df["event_date"].min()),
            str(train_df["event_date"].max()),
        ],
        "test_date_range": [
            str(test_df["event_date"].min()),
            str(test_df["event_date"].max()),
        ],
    }

    if eval_only:
        logger.info("eval_only=True — skipping serialization")
        return metrics

    # ------------------------------------------------------------------ #
    # 6. Serialize                                                        #
    # ------------------------------------------------------------------ #
    MODELS_DIR.mkdir(exist_ok=True)

    joblib.dump(win_pipeline,    MODELS_DIR / "win_loss_v1.joblib")
    joblib.dump(method_pipeline, MODELS_DIR / "method_v1.joblib")

    imp_path = MODELS_DIR / "feature_importance.json"
    imp_path.write_text(json.dumps(feat_imp, indent=2))

    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))

    logger.info("Saved models to %s", MODELS_DIR)
    logger.info("Metrics: %s", metrics)
    return metrics

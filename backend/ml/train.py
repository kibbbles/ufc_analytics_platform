"""ml/train.py — Train win/loss and method prediction models.

Trains three candidate models (Logistic Regression, XGBoost, Random Forest)
on the same temporal split, selects the best by validation-set ROC-AUC, and
serializes it as win_loss_v1.joblib.  All run metrics are appended to
models/experiment_log.json for cross-run comparison.

Models
------
1. win_loss_v1.joblib
   Best of: LogisticRegression | XGBClassifier | RandomForestClassifier
   Selected by validation-set ROC-AUC (not test — avoids model-selection leakage).

2. method_v1.joblib
   RandomForestClassifier multi-class: ko_tko | submission | decision

Usage
-----
    cd backend
    python -m ml.run_train          # normal run
    python -m ml.run_train --eval   # evaluate only (no serialization)
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
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
        ("num", numeric_transformer,     feature_names),
        ("cat", categorical_transformer, categorical),
    ], remainder="drop")


def _candidate_models(
    feature_names: list[str],
    categorical: list[str],
) -> dict[str, tuple[Pipeline, bool]]:
    """Return {model_name: (pipeline, use_early_stopping)}.

    XGBoost uses early stopping (val set stops tree growth); the training loop
    handles this specially — see _fit_pipeline().  LR and RF use standard
    pipeline.fit().
    """
    def _pre() -> ColumnTransformer:
        # Each model gets its own preprocessor instance so fit state is isolated.
        return _build_preprocessor(feature_names, categorical)

    lr = Pipeline([
        ("pre", _pre()),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=0.1,
            class_weight="balanced",
            solver="lbfgs",
            random_state=42,
        )),
    ])

    # XGBoost: high n_estimators ceiling — early_stopping_rounds decides actual count.
    # Reduced complexity vs previous run to close the 15% train/test gap:
    #   max_depth 4→3, min_child_weight 5→15, reg_alpha 0.1→1.0, subsample 0.8→0.7
    xgb = Pipeline([
        ("pre", _pre()),
        ("clf", XGBClassifier(
            n_estimators=1000,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.7,
            colsample_bytree=0.7,
            min_child_weight=15,
            gamma=2,
            reg_alpha=1.0,
            reg_lambda=2.0,
            eval_metric="logloss",
            early_stopping_rounds=50,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    # RF: tighter constraints to close the 13% train/test gap:
    #   max_depth 8→6, min_samples_leaf 10→30, added min_samples_split=20
    rf = Pipeline([
        ("pre", _pre()),
        ("clf", RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=30,
            min_samples_split=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    return {
        "logistic_regression": (lr,  False),  # LR probs are naturally calibrated
        "xgboost":             (xgb, True),   # calibrate on val set
        "random_forest":       (rf,  False),
    }


def _fit_pipeline(
    name: str,
    base_pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> object:
    """Fit a pipeline and return the inference-ready model.

    XGBoost receives early stopping via a manual two-step fit:
      1. Fit the preprocessor on X_train.
      2. Transform both X_train and X_val.
      3. Fit XGBoost with eval_set so early_stopping_rounds takes effect.
    The pipeline object is then fully fitted and used as-is for inference
    (no isotonic calibration — early stopping produces better-calibrated
    probabilities than the previous calibrate-on-val approach).

    All other models use standard pipeline.fit().
    """
    if name == "xgboost":
        pre = base_pipeline.named_steps["pre"]
        clf = base_pipeline.named_steps["clf"]
        X_train_pre = pre.fit_transform(X_train, y_train)
        X_val_pre   = pre.transform(X_val)
        clf.fit(
            X_train_pre, y_train,
            eval_set=[(X_val_pre, y_val)],
            verbose=False,
        )
        best = getattr(clf, "best_iteration", None)
        if best is not None:
            logger.info("  XGBoost early stopped at tree %d", best + 1)
        return base_pipeline   # pre + clf both fitted; no calibration wrapper

    base_pipeline.fit(X_train, y_train)
    return base_pipeline


def _run_shap_analysis(
    best_name: str,
    best_pipeline,
    X_test: pd.DataFrame,
    feature_names: list[str],
    categorical: list[str],
) -> dict:
    """Compute SHAP values for the best win/loss model on the held-out test set.

    Saves:
        models/shap_values.npy    — raw SHAP array  (n_test x n_features)
        models/shap_summary.json  — mean |SHAP| per feature, sorted descending
        models/shap_importance.png — horizontal bar chart of mean |SHAP|

    Returns the shap_summary dict (empty on failure).
    """
    try:
        import shap
        import matplotlib
        matplotlib.use("Agg")   # headless — no GUI or display needed
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning(
            "shap or matplotlib not installed — skipping SHAP analysis. "
            "pip install shap matplotlib"
        )
        return {}

    all_features = feature_names + categorical

    pre = best_pipeline.named_steps["pre"]
    clf = best_pipeline.named_steps["clf"]
    X_test_pre = pre.transform(X_test)

    logger.info(
        "Running SHAP analysis for %s on %d test samples...",
        best_name, len(X_test),
    )

    try:
        if best_name == "logistic_regression":
            explainer = shap.LinearExplainer(clf, X_test_pre)
            shap_vals = explainer.shap_values(X_test_pre)
        else:  # random_forest or xgboost
            explainer = shap.TreeExplainer(clf)
            raw = explainer.shap_values(X_test_pre)
            # sklearn RF returns [class0_vals, class1_vals]; XGBoost returns 2-D array.
            # Newer SHAP may return 3-D (n_samples, n_features, n_classes).
            if isinstance(raw, list):
                shap_vals = raw[1]           # class 1 = fighter A wins
            elif isinstance(raw, np.ndarray) and raw.ndim == 3:
                shap_vals = raw[:, :, 1]     # newer SHAP Explanation API
            else:
                shap_vals = raw
    except Exception as exc:
        logger.warning("SHAP computation failed: %s", exc)
        return {}

    # Mean absolute SHAP per feature — global importance ranking
    mean_abs = np.abs(shap_vals).mean(axis=0)
    shap_summary = {
        col: float(mean_abs[i])
        for i, col in enumerate(all_features)
    }
    shap_summary = dict(sorted(shap_summary.items(), key=lambda x: x[1], reverse=True))

    # Persist raw values and summary
    np.save(MODELS_DIR / "shap_values.npy", shap_vals)
    (MODELS_DIR / "shap_summary.json").write_text(json.dumps(shap_summary, indent=2))

    # Bar chart — top 20 features by mean |SHAP|
    top_n = min(20, len(all_features))
    top_f = list(shap_summary.keys())[:top_n]
    top_v = [shap_summary[f] for f in top_f]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(range(top_n), top_v[::-1], color="#2196F3", alpha=0.85)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(top_f[::-1], fontsize=9)
    ax.set_xlabel("Mean |SHAP value|", fontsize=11)
    ax.set_title(
        f"SHAP Feature Importance — {best_name.replace('_', ' ').title()}"
        f"  (n={len(X_test)} test fights)",
        fontsize=12,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(MODELS_DIR / "shap_importance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    top_feat = list(shap_summary.keys())[0]
    top_val  = list(shap_summary.values())[0]
    logger.info("SHAP done. Top feature: %s (mean|SHAP|=%.5f)", top_feat, top_val)
    return shap_summary


def _extract_importance(
    trained_pipeline,
    feature_names: list[str],
    categorical: list[str],
) -> dict[str, float]:
    """Extract named feature importances from a trained pipeline or calibrated wrapper.

    - XGBoost / RF: uses .feature_importances_ (Gini / gain)
    - Logistic Regression: uses abs(coef_[0]) — magnitude of coefficients
    """
    col_names = feature_names + categorical
    try:
        p = trained_pipeline
        if hasattr(p, "estimator"):        # unwrap CalibratedClassifierCV
            p = p.estimator
        clf = p.named_steps["clf"]

        if hasattr(clf, "feature_importances_"):
            imp = clf.feature_importances_
        elif hasattr(clf, "coef_"):
            imp = np.abs(clf.coef_[0])
        else:
            return {}

        imp_dict = {
            col_names[i]: float(imp[i])
            for i in range(min(len(imp), len(col_names)))
        }
        return dict(sorted(imp_dict.items(), key=lambda x: x[1], reverse=True))
    except Exception as exc:
        logger.warning("Could not extract feature importance: %s", exc)
        return {}


def train(eval_only: bool = False) -> dict:
    """Run the full training pipeline.

    Args:
        eval_only: If True, skip serialization (useful for CI checks).

    Returns:
        Evaluation metrics dict for the best model.
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

    # Short fingerprint of the feature set — tracked in experiment log
    feat_hash = hashlib.md5(
        json.dumps(sorted(feature_names)).encode()
    ).hexdigest()[:8]

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
    # 3. Train & evaluate all candidate models                            #
    # ------------------------------------------------------------------ #
    candidates = _candidate_models(feature_names, categorical)
    model_results: dict[str, dict] = {}
    trained_models: dict[str, object] = {}

    for name, (base_pipeline, _) in candidates.items():
        logger.info("Training %s...", name)
        pipeline = _fit_pipeline(name, base_pipeline, X_train, y_train, X_val, y_val)

        # Train accuracy — overfitting diagnostic only, never used for selection
        train_pred = pipeline.predict(X_train)
        train_acc  = float(accuracy_score(y_train, train_pred))

        # Val metrics — used for model selection (never the test set)
        val_pred  = pipeline.predict(X_val)
        val_proba = pipeline.predict_proba(X_val)[:, 1]
        val_acc   = float(accuracy_score(y_val, val_pred))
        val_auc   = float(roc_auc_score(y_val, val_proba))

        # Test metrics — final holdout evaluation only
        test_pred  = pipeline.predict(X_test)
        test_proba = pipeline.predict_proba(X_test)[:, 1]
        test_acc   = float(accuracy_score(y_test, test_pred))
        test_auc   = float(roc_auc_score(y_test, test_proba))

        gap = round(val_acc - test_acc, 4)   # Tilburg reports this difference
        logger.info(
            "  %-22s train_acc=%.4f  val_acc=%.4f  val_auc=%.4f  "
            "test_acc=%.4f  test_auc=%.4f  gap(val-test)=%.4f",
            name, train_acc, val_acc, val_auc, test_acc, test_auc, gap,
        )
        logger.info("\n%s", classification_report(
            y_test, test_pred, target_names=["B wins", "A wins"]
        ))

        model_results[name] = {
            "train_accuracy": round(train_acc, 4),
            "val_accuracy":   round(val_acc,  4),
            "val_auc":        round(val_auc,  4),
            "test_accuracy":  round(test_acc, 4),
            "test_auc":       round(test_auc, 4),
            "val_test_gap":   round(gap,      4),
        }
        trained_models[name] = pipeline

    # ------------------------------------------------------------------ #
    # 4. Select best model by validation AUC                              #
    # ------------------------------------------------------------------ #
    best_name     = max(model_results, key=lambda n: model_results[n]["val_auc"])
    best_pipeline = trained_models[best_name]
    best_res      = model_results[best_name]

    logger.info(
        "Best model: %s  (val_acc=%.4f  val_auc=%.4f  test_acc=%.4f  "
        "test_auc=%.4f  gap=%.4f)",
        best_name,
        best_res["val_accuracy"], best_res["val_auc"],
        best_res["test_accuracy"], best_res["test_auc"],
        best_res["val_test_gap"],
    )

    feat_imp = _extract_importance(best_pipeline, feature_names, categorical)

    # ------------------------------------------------------------------ #
    # 5. Method model  (Random Forest multi-class)                        #
    # ------------------------------------------------------------------ #
    logger.info("Training Random Forest method model...")

    method_col = df["method"].map(_encode_method)
    df_m       = df[method_col.notna()].copy()
    df_m["method_class"] = method_col[method_col.notna()]

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

    rf_method = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    method_preprocessor = _build_preprocessor(feature_names, categorical)
    method_pipeline = Pipeline([("pre", method_preprocessor), ("clf", rf_method)])
    method_pipeline.fit(Xm_train, ym_train)

    ym_pred    = method_pipeline.predict(Xm_test)
    method_acc = float(accuracy_score(ym_test, ym_pred))

    logger.info("Method accuracy=%.4f", method_acc)
    logger.info("\n%s", classification_report(ym_test, ym_pred))

    # ------------------------------------------------------------------ #
    # 6. Assemble metrics & experiment log entry                          #
    # ------------------------------------------------------------------ #
    metrics = {
        "win_accuracy":     round(best_res["test_accuracy"], 4),
        "win_roc_auc":      round(best_res["test_auc"], 4),
        "best_model":       best_name,
        "method_accuracy":  round(method_acc, 4),
        "train_rows":       len(train_df),
        "test_rows":        len(test_df),
        "train_date_range": [
            str(train_df["event_date"].min()),
            str(train_df["event_date"].max()),
        ],
        "test_date_range": [
            str(test_df["event_date"].min()),
            str(test_df["event_date"].max()),
        ],
    }

    log_entry = {
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "feature_hash":    feat_hash,
        "n_features":      len(feature_names),
        "train_rows":      len(train_df),
        "val_rows":        len(val_df),
        "test_rows":       len(test_df),
        "models":          model_results,
        "best_model":      best_name,
        "method_accuracy": round(method_acc, 4),
    }

    if eval_only:
        logger.info("eval_only=True — skipping serialization")
        return metrics

    # ------------------------------------------------------------------ #
    # 7. SHAP analysis on best model                                      #
    # ------------------------------------------------------------------ #
    MODELS_DIR.mkdir(exist_ok=True)

    shap_summary = _run_shap_analysis(
        best_name, best_pipeline, X_test, feature_names, categorical
    )
    if shap_summary:
        metrics["shap_top10"] = dict(list(shap_summary.items())[:10])

    # ------------------------------------------------------------------ #
    # 8. Serialize                                                        #
    # ------------------------------------------------------------------ #
    joblib.dump(best_pipeline,   MODELS_DIR / "win_loss_v1.joblib")
    joblib.dump(method_pipeline, MODELS_DIR / "method_v1.joblib")

    (MODELS_DIR / "feature_importance.json").write_text(
        json.dumps(feat_imp, indent=2)
    )
    (MODELS_DIR / "metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )

    # Append to experiment log (create if missing)
    log_path = MODELS_DIR / "experiment_log.json"
    existing_log: list = json.loads(log_path.read_text()) if log_path.exists() else []
    existing_log.append(log_entry)
    log_path.write_text(json.dumps(existing_log, indent=2))

    logger.info("Saved models to %s", MODELS_DIR)
    logger.info("Metrics: %s", metrics)
    return metrics

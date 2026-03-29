"""ml/experiment_age_raw.py — Age raw features experiment.

Compares two Random Forest models (identical hyperparameters):
  Baseline : current 30 selected features (diff_age_at_fight as the only age signal)
  Experiment: same 30 features + fighter_a_age_days + fighter_b_age_days as raw values

Run from the backend/ directory:
    python ml/experiment_age_raw.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import text

from db.database import SessionLocal

# ── Config ────────────────────────────────────────────────────────────────────

PARQUET   = os.path.join(os.path.dirname(__file__), "..", "features", "training_data.parquet")
SEL_JSON  = os.path.join(os.path.dirname(__file__), "..", "features", "selected_features.json")

RF_PARAMS = dict(
    n_estimators=300,
    max_depth=6,
    min_samples_leaf=30,
    min_samples_split=20,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)

TRAIN_FRAC = 0.70
VAL_FRAC   = 0.15   # remaining 15% is test

# ── Load data ─────────────────────────────────────────────────────────────────

print("Loading training data...")
df = pd.read_parquet(PARQUET)
df["event_date"] = pd.to_datetime(df["event_date"])
df = df.sort_values("event_date").reset_index(drop=True)

with open(SEL_JSON) as f:
    sel = json.load(f)
base_features    = sel["feature_names"]          # 30 features
categorical_feats = sel.get("categorical_features", [])

# ── Fetch raw ages from DB ────────────────────────────────────────────────────

print("Fetching raw fighter ages from DB...")
db = SessionLocal()
rows = db.execute(text("""
    SELECT ft.fighter_id, ft.dob_date
    FROM fighter_tott ft
    WHERE ft.dob_date IS NOT NULL
""")).mappings().all()
db.close()

dob_map = {r["fighter_id"]: pd.Timestamp(r["dob_date"]) for r in rows}

def age_at(fighter_id: str, event_date: pd.Timestamp) -> float | None:
    dob = dob_map.get(fighter_id)
    if dob is None or pd.isna(event_date):
        return None
    return float((event_date - dob).days)

df["fighter_a_age_days"] = [
    age_at(a, d) for a, d in zip(df["fighter_a_id"], df["event_date"])
]
df["fighter_b_age_days"] = [
    age_at(b, d) for b, d in zip(df["fighter_b_id"], df["event_date"])
]

print(f"  fighter_a_age_days non-null: {df['fighter_a_age_days'].notna().sum()}/{len(df)}")
print(f"  fighter_b_age_days non-null: {df['fighter_b_age_days'].notna().sum()}/{len(df)}")

# ── Chronological train / val / test split ───────────────────────────────────

n = len(df)
train_end = int(n * TRAIN_FRAC)
val_end   = int(n * (TRAIN_FRAC + VAL_FRAC))

train_df = df.iloc[:train_end]
val_df   = df.iloc[train_end:val_end]
test_df  = df.iloc[val_end:]

print(f"\nSplit: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

target = "fighter_a_wins"

# ── Helper: encode weight_class ───────────────────────────────────────────────

def prep_X(data: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    X = data[features].copy()
    if "weight_class" in X.columns:
        X["weight_class"] = LabelEncoder().fit_transform(
            X["weight_class"].astype(str)
        )
    return X

# ── Helper: build sklearn Pipeline (imputer + RF) ────────────────────────────

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf",      RandomForestClassifier(**RF_PARAMS)),
    ])

# ── Helper: evaluate ─────────────────────────────────────────────────────────

def evaluate(pipe: Pipeline, X: pd.DataFrame, y: pd.Series, split: str) -> dict:
    y_pred  = pipe.predict(X)
    y_prob  = pipe.predict_proba(X)[:, 1]
    acc     = accuracy_score(y, y_pred)
    auc     = roc_auc_score(y, y_prob)
    brier   = float(np.mean((y_prob - y.values) ** 2))
    bss     = 1.0 - brier / 0.25
    return {"split": split, "accuracy": acc, "roc_auc": auc, "brier": brier, "brier_skill": bss}

# ── Train baseline (30 features) ──────────────────────────────────────────────

print("\n── Baseline (30 features, diff_age_at_fight only) ──")
base_pipe = build_pipeline()
X_train_base = prep_X(train_df, base_features)
X_val_base   = prep_X(val_df,   base_features)
X_test_base  = prep_X(test_df,  base_features)
y_train = train_df[target]
y_val   = val_df[target]
y_test  = test_df[target]

base_pipe.fit(X_train_base, y_train)
base_results = [
    evaluate(base_pipe, X_train_base, y_train, "train"),
    evaluate(base_pipe, X_val_base,   y_val,   "val"),
    evaluate(base_pipe, X_test_base,  y_test,  "test"),
]

# ── Train experiment (32 features — adds fighter_a/b_age_days) ───────────────

print("── Experiment (32 features — +fighter_a_age_days, +fighter_b_age_days) ──")
exp_features = base_features + ["fighter_a_age_days", "fighter_b_age_days"]
exp_pipe = build_pipeline()
X_train_exp = prep_X(train_df, exp_features)
X_val_exp   = prep_X(val_df,   exp_features)
X_test_exp  = prep_X(test_df,  exp_features)

exp_pipe.fit(X_train_exp, y_train)
exp_results = [
    evaluate(exp_pipe, X_train_exp, y_train, "train"),
    evaluate(exp_pipe, X_val_exp,   y_val,   "val"),
    evaluate(exp_pipe, X_test_exp,  y_test,  "test"),
]

# ── Print comparison table ────────────────────────────────────────────────────

print("\n" + "═" * 72)
print(f"{'':8} {'Accuracy':>10} {'ROC-AUC':>10} {'Brier':>10} {'Skill Score':>12}")
print("─" * 72)
for split in ("train", "val", "test"):
    br = next(r for r in base_results if r["split"] == split)
    er = next(r for r in exp_results  if r["split"] == split)
    delta_acc = er["accuracy"] - br["accuracy"]
    delta_auc = er["roc_auc"]  - br["roc_auc"]
    print(f"\n[{split.upper()}]")
    print(f"  {'Baseline':<18} {br['accuracy']:>9.3%} {br['roc_auc']:>10.4f} {br['brier']:>10.4f} {br['brier_skill']:>11.1%}")
    print(f"  {'+ Raw Ages':<18} {er['accuracy']:>9.3%} {er['roc_auc']:>10.4f} {er['brier']:>10.4f} {er['brier_skill']:>11.1%}")
    sign_acc = "▲" if delta_acc > 0.0005 else ("▼" if delta_acc < -0.0005 else "·")
    sign_auc = "▲" if delta_auc > 0.0005 else ("▼" if delta_auc < -0.0005 else "·")
    print(f"  {'Δ':<18} {sign_acc} {delta_acc:>+8.3%} {sign_auc} {delta_auc:>+8.4f}")
print("\n" + "═" * 72)

# ── Feature importances for the experiment model ──────────────────────────────

rf_exp = exp_pipe.named_steps["rf"]
imps   = sorted(
    zip(exp_features, rf_exp.feature_importances_),
    key=lambda x: x[1], reverse=True
)
print("\nTop 10 feature importances (experiment model):")
for feat, imp in imps[:10]:
    marker = " ← NEW" if feat in ("fighter_a_age_days", "fighter_b_age_days") else ""
    print(f"  {feat:<45} {imp:.4f}{marker}")

print("\nAge feature importances:")
age_feats = ["diff_age_at_fight", "fighter_a_age_days", "fighter_b_age_days"]
for feat, imp in imps:
    if feat in age_feats:
        print(f"  {feat:<45} {imp:.4f}")

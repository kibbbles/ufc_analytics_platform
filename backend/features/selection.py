"""features/selection.py — Feature selection analysis.

Builds a full per-fight training matrix from all feature modules (5.2–5.6),
scores each feature against the binary outcome (fighter_a_wins) using mutual
information, removes collinear pairs (|r| > 0.9 Pearson), and writes the
final feature list to backend/features/selected_features.json.

The training matrix assembly logic lives here temporarily and will be
extracted into pipeline.py (Task 5.8) once that module is built.

Public API
----------
build_training_matrix() -> DataFrame
    One row per fight with all A-B differential features + fighter_a_wins.

run_feature_selection() -> dict
    Runs MI + collinearity filtering, writes selected_features.json,
    and returns the result dict.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from features.pipeline import build_training_matrix

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
OUTPUT_PATH = _HERE / "selected_features.json"


# ---------------------------------------------------------------------------
# Training matrix assembly (migrates to pipeline.py in Task 5.8)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------

def run_feature_selection() -> dict:
    """Run MI + collinearity filtering and write selected_features.json.

    Steps
    -----
    1. Build full training matrix via build_training_matrix().
    2. Median-impute NaN values (for MI computation only — training imputes
       differently).
    3. Score all features with mutual_info_classif against fighter_a_wins.
    4. Compute Pearson |r| matrix; greedily remove the lower-MI feature from
       every pair exceeding 0.90.
    5. Sort survivors by MI score descending.
    6. Write selected_features.json and return the result dict.
    """
    mat = build_training_matrix()

    # weight_class is a string categorical — always included, encoded by Task 6.
    # It bypasses MI/Pearson here and is recorded separately in the JSON.
    CATEGORICAL = ["weight_class"]

    id_cols = {"fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins"} | set(CATEGORICAL)
    feature_cols = [c for c in mat.columns if c not in id_cols]

    y = mat["fighter_a_wins"].astype(int)
    X = mat[feature_cols].copy()

    # Drop any feature that is entirely NaN (no signal possible)
    all_nan = X.columns[X.isna().all()].tolist()
    if all_nan:
        logger.warning("Dropping all-NaN features: %s", all_nan)
        X = X.drop(columns=all_nan)
        feature_cols = list(X.columns)

    # Median imputation for MI scoring (selection-only; training imputes differently)
    medians = X.median()
    X_filled = X.fillna(medians)

    # ---- Step 1: Mutual information scores --------------------------------
    logger.info("Computing mutual information scores for %d features...", len(feature_cols))
    mi_raw = mutual_info_classif(X_filled, y, random_state=42)
    mi_scores: dict[str, float] = dict(zip(feature_cols, mi_raw.tolist()))

    # ---- Step 2: Pearson collinearity filter ------------------------------
    logger.info("Computing Pearson correlation matrix...")
    corr = X_filled.corr().abs()

    # Collect all pairs with |r| > 0.90 (upper triangle only, sorted by |r| desc)
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    collinear_pairs = (
        upper.stack()
        .reset_index()
        .rename(columns={"level_0": "f1", "level_1": "f2", 0: "r"})
        .query("r > 0.90")
        .sort_values("r", ascending=False)
        .reset_index(drop=True)
    )

    removed: list[dict] = []
    dropped: set[str] = set()

    for _, row in collinear_pairs.iterrows():
        f1, f2, r_val = row["f1"], row["f2"], row["r"]
        if f1 in dropped or f2 in dropped:
            continue
        # Drop the lower-MI feature; break ties by dropping the one named later
        # alphabetically (arbitrary but deterministic)
        drop = f1 if mi_scores[f1] <= mi_scores[f2] else f2
        keep = f2 if drop == f1 else f1
        dropped.add(drop)
        removed.append({
            "feature":          drop,
            "correlated_with":  keep,
            "r":                round(float(r_val), 4),
            "mi_score_dropped": round(float(mi_scores[drop]), 6),
            "mi_score_kept":    round(float(mi_scores[keep]), 6),
        })

    # ---- Step 3: Sort survivors by MI score descending --------------------
    selected = [c for c in feature_cols if c not in dropped]
    selected.sort(key=lambda c: mi_scores[c], reverse=True)

    # ---- Assemble result --------------------------------------------------
    result = {
        "generated_at":             datetime.now(timezone.utc).isoformat(),
        "n_training_rows":          int(len(mat)),
        "n_features_before":        len(feature_cols),
        "n_features_removed_collinear": len(removed),
        "n_features_selected":      len(selected),
        # Numeric/binary features that passed selection (ordered by MI score)
        "feature_names":            selected,
        "mi_scores":                {c: round(float(mi_scores[c]), 6) for c in selected},
        # Categorical features — always included; Task 6 handles encoding
        "categorical_features":     CATEGORICAL,
        "removed_collinear":        removed,
    }

    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    logger.info(
        "run_feature_selection: %d features selected -> %s",
        len(selected), OUTPUT_PATH,
    )
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        stream=sys.stdout,
    )
    result = run_feature_selection()

    print(f"\n{'='*60}")
    print(f"Training rows : {result['n_training_rows']:,}")
    print(f"Features in   : {result['n_features_before']}")
    print(f"Removed (|r|>0.9): {result['n_features_removed_collinear']}")
    print(f"Features out  : {result['n_features_selected']}")
    print(f"\nTop 15 by MI score:")
    for name in result["feature_names"][:15]:
        print(f"  {result['mi_scores'][name]:.6f}  {name}")
    if result["removed_collinear"]:
        print(f"\nRemoved collinear pairs:")
        for item in result["removed_collinear"]:
            print(f"  dropped {item['feature']} (MI={item['mi_score_dropped']:.4f})"
                  f"  corr={item['r']} with {item['correlated_with']}")
    print(f"\nWrote: {OUTPUT_PATH}")

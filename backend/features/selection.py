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

from features.differentials import build_differentials
from features.extractors import (
    get_fights_long_df,
    get_fighters_df,
    get_matchups_df,
    get_stats_df,
)
from features.opponent_quality import build_opponent_quality
from features.rolling_metrics import build_rolling_metrics
from features.style_features import build_style_features
from features.time_features import build_time_features

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
OUTPUT_PATH = _HERE / "selected_features.json"


# ---------------------------------------------------------------------------
# Training matrix assembly (migrates to pipeline.py in Task 5.8)
# ---------------------------------------------------------------------------

def _add_fighter_diffs(mat: pd.DataFrame, feat_df: pd.DataFrame) -> pd.DataFrame:
    """Merge a per-(fighter_id, fight_id) feature DataFrame into *mat* as A-B diffs.

    For each feature column in feat_df (everything except fighter_id/fight_id):
      1. Merge fighter_a's values via (fighter_a_id, fight_id).
      2. Merge fighter_b's values via (fighter_b_id, fight_id).
      3. Compute diff_<col> = a_<col> - b_<col> and drop the raw A/B columns.

    *mat* must contain fighter_a_id, fighter_b_id, and fight_id.
    """
    feat_cols = [c for c in feat_df.columns if c not in ("fighter_id", "fight_id")]

    # Fighter A side
    a_df = (
        feat_df
        .rename(columns={"fighter_id": "fighter_a_id"})
        .rename(columns={c: f"_a_{c}" for c in feat_cols})
    )
    mat = mat.merge(
        a_df[["fighter_a_id", "fight_id"] + [f"_a_{c}" for c in feat_cols]],
        on=["fighter_a_id", "fight_id"],
        how="left",
    )

    # Fighter B side
    b_df = (
        feat_df
        .rename(columns={"fighter_id": "fighter_b_id"})
        .rename(columns={c: f"_b_{c}" for c in feat_cols})
    )
    mat = mat.merge(
        b_df[["fighter_b_id", "fight_id"] + [f"_b_{c}" for c in feat_cols]],
        on=["fighter_b_id", "fight_id"],
        how="left",
    )

    # Compute diffs and drop raw A/B columns
    for c in feat_cols:
        mat[f"diff_{c}"] = mat[f"_a_{c}"] - mat[f"_b_{c}"]
        mat = mat.drop(columns=[f"_a_{c}", f"_b_{c}"])

    return mat


def build_training_matrix() -> pd.DataFrame:
    """Assemble the full training matrix from all feature modules.

    Returns one row per fight (fights with NULL outcome are excluded) with:
      - fight_id, fighter_a_id, fighter_b_id, fighter_a_wins  (IDs + target)
      - height_diff_inches … loss_streak_diff                  (from differentials)
      - diff_roll3_* / diff_ewa_*                              (from rolling_metrics)
      - diff_striking_ratio … diff_decision_rate               (from style_features)
      - diff_days_since_last_fight … diff_days_in_weight_class (from time_features)
      - diff_avg_opponent_win_pct … diff_avg_opponent_losses   (from opponent_quality)
    """
    logger.info("build_training_matrix: loading raw data...")
    stats    = get_stats_df()
    fights   = get_fights_long_df()
    fighters = get_fighters_df()
    matchups = get_matchups_df()

    logger.info("build_training_matrix: computing feature modules...")
    diff_df = build_differentials(matchups, fighters, fights)
    rm_df   = build_rolling_metrics(stats)
    sf_df   = build_style_features(stats, fights)
    tf_df   = build_time_features(fights, fighters)
    oq_df   = build_opponent_quality(fights)

    # Base frame: one row per fight with a known outcome
    mat = (
        matchups[["fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins"]]
        .copy()
    )
    mat = mat[mat["fighter_a_wins"].notna()].copy()
    mat["fighter_a_wins"] = mat["fighter_a_wins"].astype(int)

    # Merge physical/experience diffs — already in A-B format from differentials.py
    diff_feat_cols = [
        c for c in diff_df.columns
        if c not in ("fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins")
    ]
    mat = mat.merge(diff_df[["fight_id"] + diff_feat_cols], on="fight_id", how="left")

    # Merge per-fighter features as A-B diffs
    for feat_df in (rm_df, sf_df, tf_df, oq_df):
        mat = _add_fighter_diffs(mat, feat_df)

    n_feat = len(mat.columns) - 4  # subtract fight_id, fighter_a_id, fighter_b_id, target
    logger.info("build_training_matrix: %d rows × %d feature columns", len(mat), n_feat)
    return mat


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

    id_cols = {"fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins"}
    feature_cols = [c for c in mat.columns if c not in id_cols]

    y = mat["fighter_a_wins"].astype(int)
    X = mat[feature_cols].copy()

    # Drop any feature that is entirely NaN (no signal possible)
    all_nan = X.columns[X.isna().all()].tolist()
    if all_nan:
        logger.warning("Dropping all-NaN features: %s", all_nan)
        X = X.drop(columns=all_nan)
        feature_cols = list(X.columns)

    # Median imputation for MI scoring
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
            "feature":         drop,
            "correlated_with": keep,
            "r":               round(float(r_val), 4),
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
        "feature_names":            selected,
        "mi_scores":                {c: round(float(mi_scores[c]), 6) for c in selected},
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

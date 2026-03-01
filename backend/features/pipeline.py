"""features/pipeline.py — Feature engineering pipeline orchestrator.

Two public functions:

build_training_matrix(date_from, date_to, save_path)
    Assembles the full per-fight feature matrix from all feature modules,
    optionally saves to a parquet file, and returns the DataFrame.
    One row per fight (draws / NCs excluded); columns match selected_features.json.

build_prediction_features(fighter_a_id, fighter_b_id, weight_class, as_of)
    Returns a flat dict of features for a hypothetical matchup — ready for
    real-time inference.  All time-based features are computed relative to
    `as_of` (defaults to today) so the dict reflects each fighter's state
    going into the fight.
"""

from __future__ import annotations

import json
import logging
from datetime import date as date_type
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from features.differentials import build_differentials, _career_stats
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

_HERE        = Path(__file__).parent
PARQUET_PATH = _HERE / "training_data.parquet"
_SEL_PATH    = _HERE / "selected_features.json"

# Weight class → weight limit in lbs (ordinal reference; encoding done in Task 6)
WEIGHT_CLASS_LBS: dict[str, int] = {
    "Women's Strawweight":   115,
    "Women's Flyweight":     125,
    "Flyweight":             125,
    "Women's Bantamweight":  135,
    "Bantamweight":          135,
    "Women's Featherweight": 145,
    "Featherweight":         145,
    "Lightweight":           155,
    "Welterweight":          170,
    "Middleweight":          185,
    "Light Heavyweight":     205,
    "Heavyweight":           265,
    "Super Heavyweight":     285,
    "Open Weight":           185,
    "Catch Weight":          170,
}


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _add_fighter_diffs(mat: pd.DataFrame, feat_df: pd.DataFrame) -> pd.DataFrame:
    """Merge a per-(fighter_id, fight_id) DataFrame into *mat* as A-B diffs.

    For each feature column (everything except fighter_id / fight_id):
      1. Merge fighter_a's values via (fighter_a_id, fight_id).
      2. Merge fighter_b's values via (fighter_b_id, fight_id).
      3. Compute diff_<col> = a - b and drop the raw A/B columns.
    """
    feat_cols = [c for c in feat_df.columns if c not in ("fighter_id", "fight_id")]

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

    for c in feat_cols:
        mat[f"diff_{c}"] = mat[f"_a_{c}"] - mat[f"_b_{c}"]
        mat = mat.drop(columns=[f"_a_{c}", f"_b_{c}"])

    return mat


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_training_matrix(
    date_from: Optional[date_type] = None,
    date_to:   Optional[date_type] = None,
    save_path: Optional[Path]      = None,
) -> pd.DataFrame:
    """Assemble the full per-fight training matrix.

    Args:
        date_from: Inclusive lower bound on event date (optional).
        date_to:   Inclusive upper bound on event date (optional).
        save_path: If provided, the DataFrame is saved to this path as
                   parquet.  Defaults to PARQUET_PATH when called without
                   an explicit path from run scripts.

    Returns:
        DataFrame — one row per fight with a known outcome.  Columns:
          fight_id, fighter_a_id, fighter_b_id, fighter_a_wins  (IDs + target)
          weight_class, is_women_division, is_title_fight        (context)
          height_diff_inches … loss_streak_diff                  (differentials)
          diff_roll3_* / diff_ewa_*                              (rolling)
          diff_striking_ratio … diff_decision_rate               (style)
          diff_days_since_last_fight … diff_days_in_weight_class (time)
          diff_avg_opponent_win_pct … diff_avg_opponent_losses   (opp quality)
    """
    logger.info("build_training_matrix: loading raw data...")
    stats    = get_stats_df(date_from, date_to)
    fights   = get_fights_long_df(date_from, date_to)
    fighters = get_fighters_df()
    matchups = get_matchups_df(date_from, date_to)

    logger.info("build_training_matrix: computing feature modules...")
    diff_df = build_differentials(matchups, fighters, fights)
    rm_df   = build_rolling_metrics(stats)
    sf_df   = build_style_features(stats, fights)
    tf_df   = build_time_features(fights, fighters)
    oq_df   = build_opponent_quality(fights)

    # Base frame: one row per fight with a known outcome
    mat = matchups[[
        "fight_id", "fighter_a_id", "fighter_b_id",
        "fighter_a_wins", "weight_class", "is_title_fight",
    ]].copy()
    mat = mat[mat["fighter_a_wins"].notna()].copy()
    mat["fighter_a_wins"]    = mat["fighter_a_wins"].astype(int)
    mat["is_title_fight"]    = mat["is_title_fight"].astype(int)
    mat["is_women_division"] = mat["weight_class"].str.startswith("Women's", na=False).astype(int)

    # Physical/experience diffs (already A-B format from differentials.py)
    diff_feat_cols = [
        c for c in diff_df.columns
        if c not in ("fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins")
    ]
    mat = mat.merge(diff_df[["fight_id"] + diff_feat_cols], on="fight_id", how="left")

    # Per-fighter feature modules → A-B diffs
    for feat_df in (rm_df, sf_df, tf_df, oq_df):
        mat = _add_fighter_diffs(mat, feat_df)

    n_feat = len(mat.columns) - 4
    logger.info("build_training_matrix: %d rows x %d feature columns", len(mat), n_feat)

    if save_path is not None:
        save_path = Path(save_path)
        mat.to_parquet(save_path, index=False)
        logger.info("build_training_matrix: saved -> %s", save_path)

    return mat


def build_prediction_features(
    fighter_a_id: str,
    fighter_b_id: str,
    weight_class: Optional[str] = None,
    as_of: Optional[date_type]  = None,
) -> dict:
    """Build a feature dict for a hypothetical matchup, ready for inference.

    Features are computed from each fighter's full career history up to
    `as_of` (defaults to today).  Time-based features (age, days since
    last fight, career length) are recomputed relative to `as_of` so they
    reflect each fighter's current state, not their state as of their last
    recorded fight.

    Args:
        fighter_a_id: fighter_details.id for fighter A.
        fighter_b_id: fighter_details.id for fighter B.
        weight_class: Weight class for the matchup.  If None, falls back to
                      fighter A's most recent weight class.
        as_of:        Reference date (defaults to today).

    Returns:
        Dict with keys matching selected_features.json (feature_names +
        categorical_features).  Unknown values are None.
    """
    today = pd.Timestamp(as_of or date_type.today())

    # ---- Load data --------------------------------------------------------
    stats    = get_stats_df()
    fights   = get_fights_long_df()
    fighters = get_fighters_df()

    # ---- Compute feature modules ------------------------------------------
    rm_df = build_rolling_metrics(stats)
    sf_df = build_style_features(stats, fights)
    tf_df = build_time_features(fights, fighters)
    oq_df = build_opponent_quality(fights)

    # fight_id → date lookup for ordering
    fight_dates = (
        fights[["fight_id", "date_proper"]]
        .drop_duplicates("fight_id")
        .assign(date_proper=lambda d: pd.to_datetime(d["date_proper"]))
    )

    def _latest(feat_df: pd.DataFrame, fid: str) -> dict:
        """Return the most recent feature row for a fighter as a plain dict."""
        rows = feat_df[feat_df["fighter_id"] == fid].copy()
        if rows.empty:
            return {}
        rows = rows.merge(fight_dates, on="fight_id", how="left")
        rows = rows.sort_values("date_proper")
        row  = rows.iloc[-1]
        drop = [c for c in ("fighter_id", "fight_id", "date_proper") if c in row.index]
        return row.drop(drop).to_dict()

    a_rm = _latest(rm_df, fighter_a_id)
    b_rm = _latest(rm_df, fighter_b_id)
    a_sf = _latest(sf_df, fighter_a_id)
    b_sf = _latest(sf_df, fighter_b_id)
    a_tf = _latest(tf_df, fighter_a_id)
    b_tf = _latest(tf_df, fighter_b_id)
    a_oq = _latest(oq_df, fighter_a_id)
    b_oq = _latest(oq_df, fighter_b_id)

    # ---- Override time-based features using `as_of` -----------------------
    fighters_idx = fighters.set_index("id")

    def _override_time(fid: str, tf_feats: dict, wc: Optional[str]) -> dict:
        tf = dict(tf_feats)
        fighter_fights = fights[fights["fighter_id"] == fid].copy()
        fighter_fights["date_proper"] = pd.to_datetime(fighter_fights["date_proper"])
        fighter_fights = fighter_fights[fighter_fights["date_proper"] <= today]

        if not fighter_fights.empty:
            last_fight  = fighter_fights["date_proper"].max()
            first_fight = fighter_fights["date_proper"].min()
            tf["days_since_last_fight"] = int((today - last_fight).days)
            tf["career_length_days"]    = int((today - first_fight).days)
            if wc:
                wc_fights = fighter_fights[fighter_fights["weight_class"] == wc]
                if not wc_fights.empty:
                    tf["days_in_weight_class"] = int((today - wc_fights["date_proper"].min()).days)
                else:
                    tf["days_in_weight_class"] = 0
        else:
            tf["days_since_last_fight"] = 365   # debut encoding
            tf["career_length_days"]    = 0
            tf["days_in_weight_class"]  = 0

        # age_at_fight — recompute with as_of date
        if fid in fighters_idx.index:
            dob = fighters_idx.at[fid, "dob_date"]
            if dob is not None and not (isinstance(dob, float) and np.isnan(dob)):
                tf["age_at_fight"] = int((today - pd.Timestamp(dob)).days)

        return tf

    # Determine weight class (fallback to fighter_a's most recent)
    if weight_class is None:
        a_fights = fights[fights["fighter_id"] == fighter_a_id]
        if not a_fights.empty:
            a_fights = a_fights.copy()
            a_fights["date_proper"] = pd.to_datetime(a_fights["date_proper"])
            weight_class = a_fights.sort_values("date_proper").iloc[-1]["weight_class"]

    a_tf = _override_time(fighter_a_id, a_tf, weight_class)
    b_tf = _override_time(fighter_b_id, b_tf, weight_class)

    # ---- Physical + experience differentials ------------------------------
    # Recompute career stats (experience, streaks) using full DB history
    career = _career_stats(fights)
    career = career.sort_values(["fighter_id", "fight_id"])

    def _current_career(fid: str) -> dict:
        rows = career[career["fighter_id"] == fid]
        if rows.empty:
            return {"total_fights_before": 0, "win_streak": 0, "loss_streak": 0}
        # Last row = state BEFORE their next (upcoming) fight
        last = rows.iloc[-1]
        # cumcount is 0-indexed fights_before; after last fight it's len(rows)-1
        # We want total fights = len(rows) (all fights are "before" the upcoming one)
        return {
            "total_fights_before": int(len(rows)),
            "win_streak":          int(last["win_streak"]),
            "loss_streak":         int(last["loss_streak"]),
        }

    a_career = _current_career(fighter_a_id)
    b_career = _current_career(fighter_b_id)

    # Physical attributes
    def _phys(fid: str) -> dict:
        if fid not in fighters_idx.index:
            return {}
        row = fighters_idx.loc[fid]
        dob = row.get("dob_date")
        age_days = None
        if dob is not None and not (isinstance(dob, float) and np.isnan(dob)):
            age_days = int((today - pd.Timestamp(dob)).days)
        return {
            "height_inches": row.get("height_inches"),
            "weight_lbs":    row.get("weight_lbs"),
            "reach_inches":  row.get("reach_inches"),
            "age_days":      age_days,
        }

    a_phys = _phys(fighter_a_id)
    b_phys = _phys(fighter_b_id)

    def _diff(a_val, b_val):
        if a_val is None or b_val is None:
            return None
        try:
            return float(a_val) - float(b_val)
        except (TypeError, ValueError):
            return None

    # ---- Assemble flat diff dict ------------------------------------------
    feat: dict = {}

    # Differentials (matching differentials.py column names exactly)
    feat["height_diff_inches"] = _diff(a_phys.get("height_inches"), b_phys.get("height_inches"))
    feat["weight_diff_lbs"]    = _diff(a_phys.get("weight_lbs"),    b_phys.get("weight_lbs"))
    feat["reach_diff_inches"]  = _diff(a_phys.get("reach_inches"),  b_phys.get("reach_inches"))
    feat["age_diff_days"]      = _diff(a_phys.get("age_days"),      b_phys.get("age_days"))
    feat["experience_diff"]    = _diff(a_career["total_fights_before"], b_career["total_fights_before"])
    feat["win_streak_diff"]    = _diff(a_career["win_streak"],  b_career["win_streak"])
    feat["loss_streak_diff"]   = _diff(a_career["loss_streak"], b_career["loss_streak"])

    # Per-fighter module diffs (diff_ prefix matches _add_fighter_diffs convention)
    for col in set(a_rm) | set(b_rm):
        feat[f"diff_{col}"] = _diff(a_rm.get(col), b_rm.get(col))
    for col in set(a_sf) | set(b_sf):
        feat[f"diff_{col}"] = _diff(a_sf.get(col), b_sf.get(col))
    for col in set(a_tf) | set(b_tf):
        feat[f"diff_{col}"] = _diff(a_tf.get(col), b_tf.get(col))
    for col in set(a_oq) | set(b_oq):
        feat[f"diff_{col}"] = _diff(a_oq.get(col), b_oq.get(col))

    # Context features
    feat["weight_class"]      = weight_class
    feat["is_women_division"] = int(str(weight_class or "").startswith("Women's"))
    feat["is_title_fight"]    = 0   # unknown for future fights; default non-title

    # ---- Filter to selected features only ---------------------------------
    if _SEL_PATH.exists():
        with open(_SEL_PATH, encoding="utf-8") as f:
            sel = json.load(f)
        all_keys = sel["feature_names"] + sel["categorical_features"]
        feat = {k: feat.get(k) for k in all_keys}

    return feat

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

# Feature-pipeline version stamped onto prediction rows.  Bump when the
# inference feature computation changes in a way that alters outputs.
# "streak_phantom_v2" = the synthetic-upcoming-fight (Option B) fix that
# corrected win/loss streak lag, the fight_id sort bug, and null win_rate_diff.
PIPELINE_VERSION = "streak_phantom_v2"

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
        "date_proper",
    ]].copy()
    mat = mat[mat["fighter_a_wins"].notna()].copy()
    mat["fighter_a_wins"]    = mat["fighter_a_wins"].astype(int)
    mat["is_title_fight"]    = mat["is_title_fight"].astype(int)
    mat["is_women_division"] = mat["weight_class"].str.startswith("Women's", na=False).astype(int)
    mat = mat.rename(columns={"date_proper": "event_date"})

    # Method column for method classifier training (winner row has method)
    method_map = (
        fights[fights["is_winner"] == True][["fight_id", "method"]]  # noqa: E712
        .drop_duplicates("fight_id")
        .set_index("fight_id")["method"]
    )
    mat["method"] = mat["fight_id"].map(method_map)

    # ---- Data quality filters (following Tilburg 2021) --------------------
    # Applied to training rows only.  Pre-cutoff / debut fights still exist
    # in `fights` and `stats` so rolling metrics retain full career history
    # for fighters whose careers span the cutoff date.

    # 1. October 1998 cutoff — frequent missing data in early UFC events.
    #    event_date may be a datetime.date object (from PostgreSQL DATE column),
    #    so cast to Timestamp for a type-safe comparison.
    cutoff = pd.Timestamp("1998-10-01")
    n_before_cutoff = len(mat)
    mat = mat[pd.to_datetime(mat["event_date"]) >= cutoff]
    logger.info(
        "build_training_matrix: Oct-1998 cutoff removed %d fights",
        n_before_cutoff - len(mat),
    )

    # 2. Debut filter — drop any fight where either fighter had zero prior
    #    UFC fights.  Those rows have all stat-based features zero-imputed
    #    (no career history) and add noise rather than signal.
    career_all = _career_stats(fights)
    debut_fight_ids = set(
        career_all[career_all["total_fights_before"] == 0]["fight_id"].unique()
    )
    n_before_debut = len(mat)
    mat = mat[~mat["fight_id"].isin(debut_fight_ids)]
    logger.info(
        "build_training_matrix: debut filter removed %d fights "
        "(%d fight_ids had at least one debutant)",
        n_before_debut - len(mat),
        len(debut_fight_ids),
    )

    # 3. Remove Super Heavyweight and Open Weight matches — no upper weight
    #    limit; too few fights and not representative (Tilburg 2021).
    _no_limit_classes = {"Super Heavyweight", "Open Weight"}
    n_before_shw = len(mat)
    mat = mat[~mat["weight_class"].isin(_no_limit_classes)]
    if n_before_shw > len(mat):
        logger.info(
            "build_training_matrix: removed %d Super Heavyweight / Open Weight fights",
            n_before_shw - len(mat),
        )

    # Physical/experience diffs (already A-B format from differentials.py)
    diff_feat_cols = [
        c for c in diff_df.columns
        if c not in ("fight_id", "fighter_a_id", "fighter_b_id", "fighter_a_wins")
    ]
    mat = mat.merge(diff_df[["fight_id"] + diff_feat_cols], on="fight_id", how="left")

    # Per-fighter feature modules → A-B diffs
    for feat_df in (rm_df, sf_df, tf_df, oq_df):
        mat = _add_fighter_diffs(mat, feat_df)

    # ---- Deduplication safety net -----------------------------------------
    # If fighter_tott has duplicate rows per fighter_id the merge chain above
    # can fan out.  Drop any resulting duplicate fight_ids before flipping.
    n_before = len(mat)
    mat = mat.drop_duplicates(subset="fight_id", keep="first")
    if len(mat) < n_before:
        logger.warning(
            "build_training_matrix: dropped %d duplicate fight_id rows "
            "(fighter_tott has duplicate records for some fighters)",
            n_before - len(mat),
        )

    # ---- Perspective flipping: balance the target class -------------------
    # UFCStats fight detail pages list the winner on the left, making
    # fighter_a_id systematically the winner (~64% without flipping).
    # Randomly flip ~50% of rows so the model cannot exploit position bias:
    #   - negate all diff_* columns  (A-B becomes B-A)
    #   - swap fighter_a_id / fighter_b_id
    #   - flip fighter_a_wins  (1 → 0, 0 → 1)
    rng = np.random.default_rng(seed=42)
    flip_mask = rng.random(len(mat)) < 0.5
    diff_cols = [c for c in mat.columns if "diff" in c]
    mat.loc[flip_mask, diff_cols] = -mat.loc[flip_mask, diff_cols].values
    orig_a = mat.loc[flip_mask, "fighter_a_id"].values
    orig_b = mat.loc[flip_mask, "fighter_b_id"].values
    mat.loc[flip_mask, "fighter_a_id"] = orig_b
    mat.loc[flip_mask, "fighter_b_id"] = orig_a
    mat.loc[flip_mask, "fighter_a_wins"] = 1 - mat.loc[flip_mask, "fighter_a_wins"]
    logger.info(
        "build_training_matrix: flipped %d/%d rows — target balance: %.1f%%",
        flip_mask.sum(), len(mat),
        mat["fighter_a_wins"].mean() * 100,
    )

    n_feat = len(mat.columns) - 4
    logger.info("build_training_matrix: %d rows x %d feature columns", len(mat), n_feat)

    if save_path is not None:
        save_path = Path(save_path)
        mat.to_parquet(save_path, index=False)
        logger.info("build_training_matrix: saved -> %s", save_path)

    return mat


# ---------------------------------------------------------------------------
# Inference-time augmentation (Option B — synthetic "upcoming fight" row)
# ---------------------------------------------------------------------------

# Sentinel fight_id prefix for the phantom row.  "~" is ASCII 126, so a
# ~UP_<id> fight_id sorts AFTER every real fight hash (lowercase hex and
# uppercase alphanumerics) — guaranteeing the phantom is last even on a
# same-day date tie.  Combined with date_proper = as_of (>= every completed
# fight), this makes the phantom strictly the last row per fighter, so every
# shift-based builder shifts the phantom's own values out of its own features.
_UPCOMING_PREFIX = "~UP_"


def _phantom_fight_id(fighter_id: str) -> str:
    return f"{_UPCOMING_PREFIX}{fighter_id}"


def _augment_for_inference(
    fights: pd.DataFrame,
    stats: pd.DataFrame,
    fighter_a_id: str,
    fighter_b_id: str,
    weight_class: Optional[str],
    as_of: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Append one synthetic "upcoming fight" row per fighter to *fights* and
    *stats* so the existing shift-based builders roll every completed fight
    into the phantom row.

    The phantom carries no outcome or stats of its own: is_winner=False and
    method=None are inert (only ever read via shift into a later row, which
    does not exist), and all stat columns are 0 (summed to 0, then shifted
    out by every rolling/expanding/ewm window).  The phantom therefore
    contributes NOTHING to its own features — see the field-by-field mapping
    in the PR notes.  Training (build_training_matrix) is untouched.

    Returns (fights_aug, stats_aug, {fighter_id: phantom_fight_id}).
    """
    phantom_ids = {
        fighter_a_id: _phantom_fight_id(fighter_a_id),
        fighter_b_id: _phantom_fight_id(fighter_b_id),
    }

    # ---- fights (long) phantom rows — one per fighter --------------------
    fight_rows = []
    for fid, opp in ((fighter_a_id, fighter_b_id), (fighter_b_id, fighter_a_id)):
        fight_rows.append({
            "fight_id":                 phantom_ids[fid],
            "fighter_id":               fid,
            "opponent_id":              opp,
            "is_winner":                False,      # inert: shifted out, never read for its own row
            "weight_class":             weight_class,
            "method":                   None,
            "total_fight_time_seconds": np.nan,
            "date_proper":              as_of,
        })
    fights_ph  = pd.DataFrame(fight_rows, columns=fights.columns)
    fights_aug = pd.concat([fights, fights_ph], ignore_index=True)
    fights_aug["date_proper"] = pd.to_datetime(fights_aug["date_proper"])

    # ---- stats (per round) phantom rows — one "Round 1" row per fighter --
    stat_num_cols = [
        c for c in stats.columns
        if c not in ("id", "fight_id", "event_id", "fighter_id", "ROUND", "date_proper")
    ]
    stat_rows = []
    for fid in (fighter_a_id, fighter_b_id):
        row = {c: 0 for c in stat_num_cols}      # 0 → summed to 0 → shifted out
        row.update({
            "id":          phantom_ids[fid],
            "fight_id":    phantom_ids[fid],
            "event_id":    None,
            "fighter_id":  fid,
            "ROUND":       "Round 1",             # numeric-matching so it survives the round filter
            "date_proper": as_of,
        })
        stat_rows.append(row)
    stats_ph  = pd.DataFrame(stat_rows, columns=stats.columns)
    stats_aug = pd.concat([stats, stats_ph], ignore_index=True)
    stats_aug["date_proper"] = pd.to_datetime(stats_aug["date_proper"])

    return fights_aug, stats_aug, phantom_ids


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
    fighters_idx = fighters.set_index("id")

    # Determine weight class (fallback to fighter_a's most recent) BEFORE
    # augmentation so the phantom row carries the correct weight class.
    if weight_class is None:
        a_fights = fights[fights["fighter_id"] == fighter_a_id]
        if not a_fights.empty:
            a_fights = a_fights.copy()
            a_fights["date_proper"] = pd.to_datetime(a_fights["date_proper"])
            weight_class = a_fights.sort_values("date_proper").iloc[-1]["weight_class"]

    # ---- Option B: synthetic "upcoming fight" row -------------------------
    # Append one phantom fight per fighter (dated `today`, no outcome/stats)
    # so the existing shift-based builders roll every completed fight into the
    # phantom row.  The selected phantom row is each fighter's CURRENT state
    # going into the upcoming fight — most recent result INCLUDED — whereas
    # reading a real fight row lags by one fight by design (no-leakage
    # training).  This also removes the systemic one-fight lag that affected
    # rolling / style / opponent-quality at inference.  Training is untouched.
    fights_aug, stats_aug, phantom_ids = _augment_for_inference(
        fights, stats, fighter_a_id, fighter_b_id, weight_class, today
    )

    # ---- Compute feature modules on the augmented data --------------------
    career = _career_stats(fights_aug)
    rm_df  = build_rolling_metrics(stats_aug)
    sf_df  = build_style_features(stats_aug, fights_aug)
    tf_df  = build_time_features(fights_aug, fighters)
    oq_df  = build_opponent_quality(fights_aug)

    def _phantom_feats(feat_df: pd.DataFrame, fid: str) -> dict:
        """Return the phantom-row feature values for a fighter as a plain dict."""
        sentinel = phantom_ids[fid]
        rows = feat_df[
            (feat_df["fighter_id"] == fid) & (feat_df["fight_id"] == sentinel)
        ]
        if rows.empty:
            return {}
        row  = rows.iloc[-1]
        drop = [c for c in ("fighter_id", "fight_id") if c in row.index]
        return row.drop(drop).to_dict()

    a_rm = _phantom_feats(rm_df, fighter_a_id)
    b_rm = _phantom_feats(rm_df, fighter_b_id)
    a_sf = _phantom_feats(sf_df, fighter_a_id)
    b_sf = _phantom_feats(sf_df, fighter_b_id)
    a_tf = _phantom_feats(tf_df, fighter_a_id)
    b_tf = _phantom_feats(tf_df, fighter_b_id)
    a_oq = _phantom_feats(oq_df, fighter_a_id)
    b_oq = _phantom_feats(oq_df, fighter_b_id)

    def _current_career(fid: str) -> dict:
        """Current career state from the fighter's phantom upcoming-fight row.

        The phantom row's win_streak / loss_streak / win_rate reflect ALL
        completed fights (the shift excludes only the phantom itself), so the
        most recent result IS included — unlike reading a real fight row,
        whose streak reflects the state BEFORE that fight.
        """
        sentinel = phantom_ids[fid]
        rows = career[
            (career["fighter_id"] == fid) & (career["fight_id"] == sentinel)
        ]
        if rows.empty:
            return {"total_fights_before": 0, "win_streak": 0,
                    "loss_streak": 0, "win_rate": None}
        r = rows.iloc[-1]
        return {
            "total_fights_before": int(r["total_fights_before"]),
            "win_streak":          int(r["win_streak"]),
            "loss_streak":         int(r["loss_streak"]),
            "win_rate":            (None if pd.isna(r["win_rate"]) else float(r["win_rate"])),
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
    feat["win_rate_diff"]      = _diff(a_career["win_rate"],    b_career["win_rate"])

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

    # ---- Guard + filter to selected features only -------------------------
    if _SEL_PATH.exists():
        with open(_SEL_PATH, encoding="utf-8") as f:
            sel = json.load(f)
        all_keys = sel["feature_names"] + sel["categorical_features"]

        # Guard against silent wrongness — the failure mode that hid win_rate_diff.
        # Every selected feature MUST be actively produced above.  A selected key
        # that is never assigned would fall through `feat.get(k)` to None and then
        # be imputed to the training median at predict time: a plausible-looking
        # wrong answer that never errors.  Fail loudly instead.
        missing = [k for k in all_keys if k not in feat]
        if missing:
            raise ValueError(
                "build_prediction_features: selected feature(s) not produced by the "
                f"pipeline and would be silently imputed: {sorted(missing)}. Wire them "
                "in build_prediction_features or remove them from selected_features.json."
            )

        # Null values can be legitimate (data sparsity, e.g. a fighter with no
        # takedown attempts), so warn rather than raise here — but surface it so a
        # feature that is null for well-established fighters is visible in logs.
        # A hard assertion on fully-populated fighters lives in
        # validate_inference_completeness(), run at retrain time.
        null_feats = [
            k for k in all_keys
            if feat.get(k) is None or (isinstance(feat.get(k), float) and pd.isna(feat.get(k)))
        ]
        if null_feats:
            logger.warning(
                "build_prediction_features(%s vs %s): %d selected feature(s) null, "
                "imputed at predict time: %s",
                fighter_a_id, fighter_b_id, len(null_feats), sorted(null_feats),
            )

        feat = {k: feat.get(k) for k in all_keys}

    return feat


def validate_inference_completeness(n_pairs: int = 8, min_fights: int = 12) -> None:
    """Fail loudly if a selected feature is *structurally* null at inference.

    Builds the inference feature vector for several matchups of veteran fighters
    (>= `min_fights` UFC bouts, known DOB and reach) and flags any selected
    feature that is null for **every** tested pair.  The all-pairs criterion is
    what separates a structural bug from legitimate data sparsity: win_rate_diff
    was null for every fighter (never produced), whereas a rate like
    diff_roll5_td_pct is null only for the occasional fighter who attempted no
    takedowns in the window.  Intended to run at retrain time (see
    ml/run_train.py) so a regression fails CI rather than shipping silently
    degraded predictions.

    Raises:
        RuntimeError if any selected feature is null across all tested pairs.
    """
    from sqlalchemy import text as _text
    from db.database import SessionLocal

    with open(_SEL_PATH, encoding="utf-8") as f:
        sel = json.load(f)
    all_keys = sel["feature_names"] + sel["categorical_features"]

    s = SessionLocal()
    try:
        rows = s.execute(_text("""
            SELECT fr.fighter_id
            FROM fight_results fr
            JOIN fighter_tott ft ON ft.fighter_id = fr.fighter_id
            WHERE ft.dob_date IS NOT NULL AND ft.reach_inches IS NOT NULL
            GROUP BY fr.fighter_id
            HAVING COUNT(*) >= :min_fights
            ORDER BY COUNT(*) DESC
            LIMIT :lim
        """), {"min_fights": min_fights, "lim": n_pairs * 2}).scalars().all()
    finally:
        s.close()

    if len(rows) < 4:
        logger.warning("validate_inference_completeness: not enough veteran fighters to check")
        return

    def _is_null(v) -> bool:
        return v is None or (isinstance(v, float) and pd.isna(v))

    null_counts = {k: 0 for k in all_keys}
    sparse_seen: dict[str, int] = {}
    n_tested = 0
    for i in range(0, len(rows) - 1, 2):
        a, b = rows[i], rows[i + 1]
        feat = build_prediction_features(a, b, "Lightweight")
        n_tested += 1
        for k in all_keys:
            if _is_null(feat.get(k)):
                null_counts[k] += 1

    # Structural = null for EVERY tested pair.  Sparse = null for some but not all.
    structural = {k: c for k, c in null_counts.items() if c == n_tested and n_tested > 0}
    sparse_seen = {k: c for k, c in null_counts.items() if 0 < c < n_tested}

    if structural:
        raise RuntimeError(
            "validate_inference_completeness: selected feature(s) null for ALL "
            f"{n_tested} veteran matchups — structural pipeline regression (the "
            f"win_rate_diff failure mode): {sorted(structural)}"
        )
    if sparse_seen:
        logger.info(
            "validate_inference_completeness: OK (%d pairs). Occasional data-sparsity "
            "nulls (not structural): %s", n_tested, sparse_seen,
        )
    else:
        logger.info(
            "validate_inference_completeness: OK — all %d selected features non-null "
            "across %d veteran matchups", len(all_keys), n_tested,
        )

"""features/differentials.py — Physical and experience differential features.

Computes fighter-A minus fighter-B differentials for each fight.
fighter_a / fighter_b ordering comes from fight_details (the BOUT string order),
which is arbitrary with respect to outcome — safe for ML training.

Public API
----------
build_differentials(matchups, fighters, fights) -> DataFrame

One row per fight_id.  Columns:
    fight_id, fighter_a_id, fighter_b_id, fighter_a_wins,
    height_diff_inches, weight_diff_lbs, reach_diff_inches,
    age_diff_days, experience_diff, win_streak_diff, loss_streak_diff
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _career_stats(fights: pd.DataFrame) -> pd.DataFrame:
    """Return per (fighter_id, fight_id): fights before, win streak, loss streak.

    All values reflect history BEFORE the current fight — no leakage.
    """
    df = fights[["fighter_id", "fight_id", "date_proper", "is_winner"]].copy()
    df["is_winner"] = df["is_winner"].astype(bool)
    df = df.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)

    # Total UFC fights before this one (0 for debut)
    df["total_fights_before"] = df.groupby("fighter_id").cumcount()

    # Previous fight result within each fighter's history (NaN for debut)
    df["prev_win"] = df.groupby("fighter_id")["is_winner"].shift(1)

    # Run-break flag: 1 where the streak changes or at the start of a fighter's record.
    # Using transform so the comparison stays within each fighter group.
    run_break = df.groupby("fighter_id")["prev_win"].transform(
        lambda x: x.ne(x.shift(1)).fillna(True).astype(int)
    )
    # Global run ID — unique across (fighter, streak-run) pairs because fighters
    # are contiguous after sorting by fighter_id.
    df["_run_id"] = run_break.cumsum()

    # 0-indexed position within each (fighter, run) group
    streak_pos = df.groupby(["fighter_id", "_run_id"]).cumcount()

    # streak_pos + 1 = actual streak length; 0 where not applicable
    df["win_streak"] = (
        (streak_pos + 1).where(df["prev_win"] == True, 0).fillna(0).astype(int)
    )
    df["loss_streak"] = (
        (streak_pos + 1).where(df["prev_win"] == False, 0).fillna(0).astype(int)
    )

    return df[["fighter_id", "fight_id", "total_fights_before", "win_streak", "loss_streak"]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_differentials(
    matchups: pd.DataFrame,
    fighters: pd.DataFrame,
    fights: pd.DataFrame,
) -> pd.DataFrame:
    """Build physical and experience differential features.

    Args:
        matchups:  One row per fight — fight_id, fighter_a_id, fighter_b_id,
                   date_proper, fighter_a_wins.  From get_matchups_df().
        fighters:  One row per fighter — id, height_inches, weight_lbs,
                   reach_inches, dob_date.  From get_fighters_df().
        fights:    Full fight history in long format — two rows per fight,
                   one per fighter.  fighter_id covers both winners and
                   losers.  From get_fights_long_df().
                   Must cover the full career history of every fighter.

    Returns:
        DataFrame with one row per fight_id.
    """
    career = _career_stats(fights)

    # ---- Merge career stats for fighter_a --------------------------------
    career_a = career.rename(columns={
        "fighter_id":         "fighter_a_id",
        "total_fights_before": "a_exp",
        "win_streak":         "a_win_streak",
        "loss_streak":        "a_loss_streak",
    })
    df = matchups.merge(career_a, on=["fighter_a_id", "fight_id"], how="left")

    # ---- Merge career stats for fighter_b --------------------------------
    career_b = career.rename(columns={
        "fighter_id":         "fighter_b_id",
        "total_fights_before": "b_exp",
        "win_streak":         "b_win_streak",
        "loss_streak":        "b_loss_streak",
    })
    df = df.merge(career_b, on=["fighter_b_id", "fight_id"], how="left")

    # ---- Merge physical stats for fighter_a ------------------------------
    phys_cols = ["id", "height_inches", "weight_lbs", "reach_inches", "dob_date"]
    phys_a = fighters[phys_cols].rename(columns={
        "id":            "fighter_a_id",
        "height_inches": "a_height",
        "weight_lbs":    "a_weight",
        "reach_inches":  "a_reach",
        "dob_date":      "a_dob",
    })
    df = df.merge(phys_a, on="fighter_a_id", how="left")

    # ---- Merge physical stats for fighter_b ------------------------------
    phys_b = fighters[phys_cols].rename(columns={
        "id":            "fighter_b_id",
        "height_inches": "b_height",
        "weight_lbs":    "b_weight",
        "reach_inches":  "b_reach",
        "dob_date":      "b_dob",
    })
    df = df.merge(phys_b, on="fighter_b_id", how="left")

    # ---- Age at fight date -----------------------------------------------
    df["date_proper"] = pd.to_datetime(df["date_proper"])
    df["a_dob"] = pd.to_datetime(df["a_dob"])
    df["b_dob"] = pd.to_datetime(df["b_dob"])
    df["a_age_days"] = (df["date_proper"] - df["a_dob"]).dt.days
    df["b_age_days"] = (df["date_proper"] - df["b_dob"]).dt.days

    # ---- Compute differentials (fighter_a minus fighter_b) ---------------
    result = pd.DataFrame({
        "fight_id":           df["fight_id"],
        "fighter_a_id":       df["fighter_a_id"],
        "fighter_b_id":       df["fighter_b_id"],
        "fighter_a_wins":     df["fighter_a_wins"],
        "height_diff_inches": df["a_height"]    - df["b_height"],
        "weight_diff_lbs":    df["a_weight"]    - df["b_weight"],
        "reach_diff_inches":  df["a_reach"]     - df["b_reach"],
        "age_diff_days":      df["a_age_days"]  - df["b_age_days"],
        "experience_diff":    df["a_exp"].fillna(0)        - df["b_exp"].fillna(0),
        "win_streak_diff":    df["a_win_streak"].fillna(0) - df["b_win_streak"].fillna(0),
        "loss_streak_diff":   df["a_loss_streak"].fillna(0) - df["b_loss_streak"].fillna(0),
    })

    logger.info("build_differentials: %d rows", len(result))
    return result

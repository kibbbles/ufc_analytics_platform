"""features/opponent_quality.py — Opponent quality / strength-of-schedule metrics.

For each fighter-fight pair, quantifies the historical quality of the opponents
faced using only records available before that fight (point-in-time correct).

Public API
----------
build_opponent_quality(fights) -> DataFrame

One row per (fighter_id, fight_id).  Columns:
    fighter_id, fight_id,
    avg_opponent_win_pct,    # expanding mean of opponent win% — past fights only
    strength_of_schedule,    # cumulative sum of opponent win% (absolute measure)
    avg_opponent_losses      # expanding mean of opponent loss count
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_opponent_quality(fights: pd.DataFrame) -> pd.DataFrame:
    """Build opponent quality features for every (fighter_id, fight_id).

    Args:
        fights: Long-format fight history — two rows per fight, one per
                fighter (is_winner=True for winner, False for loser).
                From get_fights_long_df().  Must be the full fight history
                (no date filter) so point-in-time opponent records are
                computed accurately for every fighter.

    Returns:
        DataFrame with one row per (fighter_id, fight_id).
    """
    df = (
        fights[["fighter_id", "fight_id", "opponent_id", "date_proper", "is_winner"]]
        .drop_duplicates(subset=["fighter_id", "fight_id"])
        .copy()
    )
    df["date_proper"] = pd.to_datetime(df["date_proper"])
    df["is_winner"] = df["is_winner"].astype(bool)
    df = df.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)

    # ---- Step 1: point-in-time win% and loss count per fighter -----------
    # For fighter X at position i (their i-th fight):
    #   wins_before   = wins in fights 0 … i-1  (shift removes current fight)
    #   fights_before = i  (0 for debut)
    #   win_pct       = wins_before / fights_before  (0 for debut → no history)
    #   losses_before = fights_before - wins_before

    pit = df[["fighter_id", "fight_id", "date_proper", "is_winner"]].copy()
    pit = pit.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)

    grp = pit.groupby("fighter_id")
    pit["fights_before"] = grp.cumcount()                                              # 0 for debut
    pit["wins_before"]   = grp["is_winner"].transform(lambda x: x.cumsum().shift(1)).fillna(0)
    pit["losses_before"] = pit["fights_before"] - pit["wins_before"]
    pit["win_pct"]       = (pit["wins_before"] / pit["fights_before"].replace(0, np.nan)).fillna(0)

    opp_stats = pit[["fighter_id", "fight_id", "win_pct", "losses_before"]].rename(
        columns={
            "fighter_id":    "opponent_id",
            "win_pct":       "opp_win_pct",
            "losses_before": "opp_losses",
        }
    )

    # ---- Step 2: attach opponent's point-in-time stats to each fight -----
    # Join on (opponent_id, fight_id) — opponent's record as of this specific
    # fight, which is inherently point-in-time correct.
    df = df.merge(opp_stats, on=["opponent_id", "fight_id"], how="left")

    # ---- Step 3: expanding averages of past opponents (shift excludes current) --
    # expanding().mean() at position i = mean of positions 0 … i  (inclusive)
    # .shift(1)          at position i = mean of positions 0 … i-1 (past only)
    df = df.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)

    def _expanding_shift(s: pd.Series) -> pd.Series:
        return s.expanding(min_periods=1).mean().shift(1)

    df["avg_opponent_win_pct"] = (
        df.groupby("fighter_id")["opp_win_pct"]
        .transform(_expanding_shift)
        .fillna(0)
    )
    df["avg_opponent_losses"] = (
        df.groupby("fighter_id")["opp_losses"]
        .transform(_expanding_shift)
        .fillna(0)
    )

    # strength_of_schedule = cumulative sum of opponent win% (unnormalized)
    # Grows with number of fights fought; distinct signal from the per-fight average
    def _cumsum_shift(s: pd.Series) -> pd.Series:
        return s.cumsum().shift(1).fillna(0)

    df["strength_of_schedule"] = (
        df.groupby("fighter_id")["opp_win_pct"]
        .transform(_cumsum_shift)
    )

    # ---- Assemble output -------------------------------------------------
    result = df[[
        "fighter_id",
        "fight_id",
        "avg_opponent_win_pct",
        "strength_of_schedule",
        "avg_opponent_losses",
    ]].copy()

    logger.info("build_opponent_quality: %d rows", len(result))
    return result

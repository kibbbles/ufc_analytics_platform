"""features/rolling_metrics.py — Rolling performance metrics.

Computes 3-fight rolling averages and exponentially weighted averages (EWA)
of per-fight striking and grappling statistics for every fighter.

No data leakage: values at position i reflect only fights 0 … i-1.
Implemented via roll-then-shift and ewm-then-shift within each fighter group.

Public API
----------
build_rolling_metrics(stats, fights) -> DataFrame

One row per (fighter_id, fight_id).  Columns:
    fighter_id, fight_id,
    roll3_sig_str_pct, roll3_td_pct, roll3_kd, roll3_ctrl_s,
    roll3_sig_str_landed, roll3_sig_str_att,
    roll3_total_str_landed, roll3_total_str_att,
    roll3_td_landed, roll3_td_att,
    ewa_sig_str_pct, ewa_td_pct, ewa_kd, ewa_ctrl_s
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Stat columns to aggregate (sum) across rounds per fight before rolling
_SUM_COLS = [
    "kd_int",
    "sig_str_landed",
    "sig_str_attempted",
    "total_str_landed",
    "total_str_attempted",
    "td_landed",
    "td_attempted",
    "ctrl_seconds",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _roll_then_shift(s: pd.Series, window: int = 3) -> pd.Series:
    """Rolling mean of `window` fights, shifted by 1 to exclude current fight.

    At position i: average of positions i-window … i-1.
    """
    return s.rolling(window, min_periods=1).mean().shift(1)


def _ewm_then_shift(s: pd.Series, alpha: float = 0.5) -> pd.Series:
    """Exponentially weighted mean (alpha=0.5), shifted by 1 to exclude current fight."""
    return s.ewm(alpha=alpha, adjust=False).mean().shift(1)


def _safe_pct(landed: pd.Series, attempted: pd.Series) -> pd.Series:
    """landed / attempted, returning NaN where attempted == 0."""
    return landed.div(attempted.replace(0, float("nan")))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_rolling_metrics(
    stats: pd.DataFrame,
) -> pd.DataFrame:
    """Build rolling performance features for every (fighter_id, fight_id).

    Args:
        stats:  fight_stats rows — fighter_id, fight_id, ROUND, date_proper,
                and all typed stat columns.  From get_stats_df().
                fight_stats contains rows for BOTH fighters in every fight,
                so winners and losers are both captured without any additional
                fight-results merge.

    Returns:
        DataFrame with one row per (fighter_id, fight_id).
    """
    # ---- 1. Filter to per-round rows (exclude any future "Totals" rows) --
    # DB values are "Round 1", "Round 2", etc.  Accept bare digits too as a
    # defensive fallback in case the ETL format ever changes.
    _round = stats["ROUND"].astype(str)
    numeric = stats[
        _round.str.match(r"^\d+$") | _round.str.match(r"^Round\s+\d+$")
    ].copy()

    # ---- 2. Aggregate per (fighter_id, fight_id) — sum across rounds -----
    # fight_stats contains rows for BOTH fighters in every fight, so winners
    # and losers are both represented here.  date_proper comes from stats_df
    # directly (via the event_details JOIN in get_stats_df), so no separate
    # all_pairs merge is needed.
    per_fight = (
        numeric.groupby(["fighter_id", "fight_id", "date_proper"], as_index=False)[_SUM_COLS]
        .sum()
    )

    # ---- 3. Sort chronologically within each fighter ---------------------
    per_fight = per_fight.sort_values(
        ["fighter_id", "date_proper", "fight_id"]
    ).reset_index(drop=True)

    # ---- 5. Rolling 3-fight averages (shift applied inside helper) -------
    rolled = per_fight.groupby("fighter_id")[_SUM_COLS].transform(_roll_then_shift)
    rolled.columns = [f"roll3_{c}" for c in _SUM_COLS]

    # Derive pct from rolled sums (more accurate than averaging raw pct columns)
    rolled["roll3_sig_str_pct"] = _safe_pct(
        rolled["roll3_sig_str_landed"], rolled["roll3_sig_str_attempted"]
    )
    rolled["roll3_td_pct"] = _safe_pct(
        rolled["roll3_td_landed"], rolled["roll3_td_attempted"]
    )

    # ---- 6. Exponentially weighted averages (shift applied inside helper) -
    ewa_base = [
        "kd_int", "sig_str_landed", "sig_str_attempted",
        "td_landed", "td_attempted", "ctrl_seconds",
    ]
    ewa = per_fight.groupby("fighter_id")[ewa_base].transform(_ewm_then_shift)
    ewa.columns = [f"ewa_{c}" for c in ewa_base]

    ewa["ewa_sig_str_pct"] = _safe_pct(ewa["ewa_sig_str_landed"], ewa["ewa_sig_str_attempted"])
    ewa["ewa_td_pct"]      = _safe_pct(ewa["ewa_td_landed"],      ewa["ewa_td_attempted"])

    # ---- 7. Assemble output ----------------------------------------------
    result = pd.concat(
        [
            per_fight[["fighter_id", "fight_id"]],
            rolled[[
                "roll3_sig_str_pct",    "roll3_td_pct",
                "roll3_kd_int",         "roll3_ctrl_seconds",
                "roll3_sig_str_landed", "roll3_sig_str_attempted",
                "roll3_total_str_landed", "roll3_total_str_attempted",
                "roll3_td_landed",      "roll3_td_attempted",
            ]],
            ewa[["ewa_sig_str_pct", "ewa_td_pct", "ewa_kd_int", "ewa_ctrl_seconds"]],
        ],
        axis=1,
    )

    result = result.rename(columns={
        "roll3_kd_int":       "roll3_kd",
        "roll3_ctrl_seconds": "roll3_ctrl_s",
        "roll3_sig_str_attempted": "roll3_sig_str_att",
        "roll3_total_str_attempted": "roll3_total_str_att",
        "roll3_td_attempted": "roll3_td_att",
        "ewa_kd_int":         "ewa_kd",
        "ewa_ctrl_seconds":   "ewa_ctrl_s",
    })

    logger.info("build_rolling_metrics: %d rows", len(result))
    return result

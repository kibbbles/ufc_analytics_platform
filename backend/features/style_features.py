"""features/style_features.py — Fighting style classification features.

Derives style metrics from a fighter's cumulative career statistics up to
(but not including) each fight.  All values are point-in-time correct.

Public API
----------
build_style_features(stats, fights) -> DataFrame

One row per (fighter_id, fight_id).  Columns:
    fighter_id, fight_id,
    striking_ratio,     # career sig_str_landed / total_str_landed
    grappling_ratio,    # career td_landed / (td_landed + sig_str_landed)
    aggression_score,   # career sig_str_attempted per minute of fight time
    defense_score,      # 1 − mean opponent sig_str accuracy against this fighter
    finish_rate,        # (KO + Sub wins) / total wins
    ko_rate,            # KO/TKO wins / total fights
    sub_rate,           # Submission wins / total fights
    decision_rate       # Decision wins / total fights
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# METHOD string patterns (case-insensitive)
_KO_PAT  = r"KO|TKO"
_SUB_PAT = r"[Ss]ubmission"
_DEC_PAT = r"[Dd]ecision"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cumsum_shift(s: pd.Series) -> pd.Series:
    """Cumulative sum of s, shifted by 1 to exclude the current row."""
    return s.cumsum().shift(1).fillna(0)


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    """num / den, returning NaN where den == 0."""
    return num.div(den.replace(0, float("nan")))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_style_features(
    stats: pd.DataFrame,
    fights: pd.DataFrame,
) -> pd.DataFrame:
    """Build style classification features for every (fighter_id, fight_id).

    Args:
        stats:  fight_stats rows — fighter_id, fight_id, ROUND, date_proper,
                sig_str_landed, sig_str_attempted, total_str_landed,
                total_str_attempted, td_landed.  From get_stats_df().
        fights: Long-format fight history — two rows per fight, one per
                fighter (is_winner=True / False).  From get_fights_long_df().
                Must include full fight history.

    Returns:
        DataFrame with one row per (fighter_id, fight_id).
    """
    # ====================================================================
    # Part A — stats-based features
    # (striking_ratio, grappling_ratio, aggression_score, defense_score)
    # ====================================================================

    # ---- A1. Aggregate fight_stats across rounds per (fighter, fight) ----
    # DB values are "Round 1", "Round 2", etc.  Accept bare digits too as a
    # defensive fallback in case the ETL format ever changes.
    _round = stats["ROUND"].astype(str)
    numeric = stats[
        _round.str.match(r"^\d+$") | _round.str.match(r"^Round\s+\d+$")
    ].copy()
    stat_agg_cols = [
        "sig_str_landed", "sig_str_attempted",
        "total_str_landed", "td_landed",
    ]
    # Aggregate on (fighter_id, fight_id) only — date_proper is taken from
    # fights so the merge key is stable and not subject to dtype drift.
    per_fight = (
        numeric.groupby(["fighter_id", "fight_id"], as_index=False)[stat_agg_cols]
        .sum()
    )

    # ---- A2. Attach fight duration and opponent_id from long-format fights --
    # fights has two rows per fight (both fighters), so both winners and losers
    # are covered here.  We use it as the canonical per-(fighter, fight) frame.
    fight_meta = fights[
        ["fighter_id", "fight_id", "date_proper", "opponent_id", "total_fight_time_seconds"]
    ].drop_duplicates(subset=["fighter_id", "fight_id"])
    per_fight = per_fight.merge(fight_meta, on=["fighter_id", "fight_id"], how="left")

    # ---- A4. Attach opponent's per-fight stats (for defense_score) -------
    opp_stat_cols = ["sig_str_landed", "sig_str_attempted"]
    opp_stats = (
        per_fight[["fighter_id", "fight_id"] + opp_stat_cols]
        .rename(columns={
            "fighter_id":       "opponent_id",
            "sig_str_landed":   "opp_sig_str_landed",
            "sig_str_attempted": "opp_sig_str_attempted",
        })
    )
    per_fight = per_fight.merge(opp_stats, on=["opponent_id", "fight_id"], how="left")

    # ---- A5. Sort chronologically within each fighter --------------------
    per_fight = per_fight.sort_values(
        ["fighter_id", "date_proper", "fight_id"]
    ).reset_index(drop=True)

    # ---- A6. Cumulative sums shifted by 1 --------------------------------
    grp = per_fight.groupby("fighter_id")

    cum_sig_str_landed   = grp["sig_str_landed"].transform(_cumsum_shift)
    cum_sig_str_att      = grp["sig_str_attempted"].transform(_cumsum_shift)
    cum_total_str_landed = grp["total_str_landed"].transform(_cumsum_shift)
    cum_td_landed        = grp["td_landed"].transform(_cumsum_shift)
    cum_fight_min        = grp["total_fight_time_seconds"].transform(_cumsum_shift) / 60.0

    # Per-fight opponent accuracy → expanding mean → shift (defense_score)
    per_fight["_opp_acc"] = _safe_div(
        per_fight["opp_sig_str_landed"].fillna(0),
        per_fight["opp_sig_str_attempted"].fillna(0),
    )
    cum_opp_acc = (
        grp["_opp_acc"]
        .transform(lambda x: x.expanding(min_periods=1).mean().shift(1))
        .fillna(0)
    )

    # ---- A7. Style ratios ------------------------------------------------
    striking_ratio   = _safe_div(cum_sig_str_landed, cum_total_str_landed)
    grappling_ratio  = _safe_div(cum_td_landed, cum_td_landed + cum_sig_str_landed)
    aggression_score = _safe_div(cum_sig_str_att, cum_fight_min)
    defense_score    = 1.0 - cum_opp_acc

    # ====================================================================
    # Part B — finish rate features (from fights_df METHOD + is_winner)
    # ====================================================================

    fin = (
        fights[["fighter_id", "fight_id", "date_proper", "is_winner", "method"]]
        .drop_duplicates(subset=["fighter_id", "fight_id"])
        .copy()
    )
    fin["is_winner"] = fin["is_winner"].astype(bool)
    fin["_is_ko"]  = fin["is_winner"] & fin["method"].str.contains(_KO_PAT,  na=False)
    fin["_is_sub"] = fin["is_winner"] & fin["method"].str.contains(_SUB_PAT, na=False)
    fin["_is_dec"] = fin["is_winner"] & fin["method"].str.contains(_DEC_PAT, na=False)
    fin["_is_win"] = fin["is_winner"]

    fin = fin.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)
    fgrp = fin.groupby("fighter_id")

    cum_ko_wins  = fgrp["_is_ko"].transform(_cumsum_shift)
    cum_sub_wins = fgrp["_is_sub"].transform(_cumsum_shift)
    cum_dec_wins = fgrp["_is_dec"].transform(_cumsum_shift)
    cum_wins     = fgrp["_is_win"].transform(_cumsum_shift)
    cum_fights   = fin.groupby("fighter_id").cumcount().astype(float)  # 0 for debut

    ko_rate       = _safe_div(cum_ko_wins,               cum_fights)
    sub_rate      = _safe_div(cum_sub_wins,              cum_fights)
    decision_rate = _safe_div(cum_dec_wins,              cum_fights)
    finish_rate   = _safe_div(cum_ko_wins + cum_sub_wins, cum_wins)

    # ====================================================================
    # Part C — assemble
    # ====================================================================

    # Align finish-rate features back onto per_fight index via merge
    fin_features = pd.DataFrame({
        "fighter_id":    fin["fighter_id"],
        "fight_id":      fin["fight_id"],
        "ko_rate":       ko_rate,
        "sub_rate":      sub_rate,
        "decision_rate": decision_rate,
        "finish_rate":   finish_rate,
    })

    result = pd.DataFrame({
        "fighter_id":      per_fight["fighter_id"],
        "fight_id":        per_fight["fight_id"],
        "striking_ratio":  striking_ratio,
        "grappling_ratio": grappling_ratio,
        "aggression_score": aggression_score,
        "defense_score":   defense_score,
    }).merge(fin_features, on=["fighter_id", "fight_id"], how="left")

    logger.info("build_style_features: %d rows", len(result))
    return result

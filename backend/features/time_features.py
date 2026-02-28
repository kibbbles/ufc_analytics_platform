"""features/time_features.py — Time-based contextual features.

Extracts temporal context for each fighter-fight pair using only information
available before the fight occurred (point-in-time correct).

Public API
----------
build_time_features(fights, fighters) -> DataFrame

One row per (fighter_id, fight_id).  Columns:
    fighter_id, fight_id,
    days_since_last_fight,   # NaN for debut → filled with 365
    career_length_days,      # 0 for debut
    age_at_fight,            # days; NaN if DOB unknown
    days_in_weight_class     # 0 for first fight in a weight class
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_time_features(
    fights: pd.DataFrame,
    fighters: pd.DataFrame,
) -> pd.DataFrame:
    """Build time-based features for every (fighter_id, fight_id).

    Args:
        fights:   fight_results rows — fighter_id, fight_id, date_proper,
                  weight_class.  From get_fights_df().
        fighters: fighter_details + tott — id, dob_date.
                  From get_fighters_df().

    Returns:
        DataFrame with one row per (fighter_id, fight_id).
    """
    # One row per fighter per fight; keep only the columns we need
    df = (
        fights[["fighter_id", "fight_id", "date_proper", "weight_class"]]
        .drop_duplicates(subset=["fighter_id", "fight_id"])
        .copy()
    )
    df["date_proper"] = pd.to_datetime(df["date_proper"])
    df = df.sort_values(["fighter_id", "date_proper", "fight_id"]).reset_index(drop=True)

    grp = df.groupby("fighter_id")

    # ---- days_since_last_fight -------------------------------------------
    # diff() at position i = date[i] - date[i-1]: gap to the previous fight.
    # This is already point-in-time correct — uses only past data.
    # Debut fights have no previous fight → encode as 365 (one year).
    df["days_since_last_fight"] = (
        grp["date_proper"]
        .diff()
        .dt.days
        .fillna(365)
    )

    # ---- career_length_days ----------------------------------------------
    # Days elapsed since the fighter's first UFC appearance.
    # 0 for the debut fight itself.
    first_fight_date = grp["date_proper"].transform("min")
    df["career_length_days"] = (df["date_proper"] - first_fight_date).dt.days

    # ---- age_at_fight ----------------------------------------------------
    # Exact age in days at fight date; NaN for fighters without a known DOB.
    dob = (
        fighters[["id", "dob_date"]]
        .rename(columns={"id": "fighter_id"})
        .copy()
    )
    dob["dob_date"] = pd.to_datetime(dob["dob_date"])
    df = df.merge(dob, on="fighter_id", how="left")
    df["age_at_fight"] = (df["date_proper"] - df["dob_date"]).dt.days
    # Remains NaN for fighters without a known DOB — imputed in 5.8

    # ---- days_in_weight_class --------------------------------------------
    # Days since the fighter's first appearance in the current weight class.
    # 0 for the first fight in a weight class; NaN where weight_class is NULL.
    wc_first = (
        df.groupby(["fighter_id", "weight_class"])["date_proper"]
        .transform("min")
    )
    df["days_in_weight_class"] = (df["date_proper"] - wc_first).dt.days

    # ---- Assemble output -------------------------------------------------
    result = df[[
        "fighter_id",
        "fight_id",
        "days_since_last_fight",
        "career_length_days",
        "age_at_fight",
        "days_in_weight_class",
    ]].copy()

    logger.info("build_time_features: %d rows", len(result))
    return result

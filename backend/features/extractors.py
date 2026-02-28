"""features/extractors.py — Raw data extraction layer.

Pulls fight data from the database into pandas DataFrames for use by
downstream feature engineering modules.  No transformation is done here;
all columns are returned with their original database names and types.

Public API
----------
get_fights_df(date_from, date_to)  -> DataFrame  fight_results + event date
get_stats_df(date_from, date_to)   -> DataFrame  fight_stats (all rounds)
get_fighters_df()                  -> DataFrame  fighter_details + fighter_tott
get_events_df(date_from, date_to)  -> DataFrame  event_details

Date filters
------------
date_from / date_to are optional datetime.date objects.  When supplied they
filter on event_details.date_proper so incremental builds can request only
new rows without re-reading the full dataset every time.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import text

from db.database import engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _date_where(
    alias: str,
    date_from: Optional[date],
    date_to: Optional[date],
    params: dict,
) -> str:
    """Return a WHERE/AND clause fragment for date_proper filtering.

    Args:
        alias:     Table alias used for date_proper in the calling query.
        date_from: Inclusive lower bound on event date.
        date_to:   Inclusive upper bound on event date.
        params:    Mutable dict that will be passed to pd.read_sql; date
                   bind parameters are added in-place.

    Returns:
        A string beginning with "AND " (or empty string) ready to embed
        in a larger WHERE clause.
    """
    clauses: list[str] = []
    if date_from is not None:
        clauses.append(f"{alias}.date_proper >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        clauses.append(f"{alias}.date_proper <= :date_to")
        params["date_to"] = date_to
    return ("AND " + " AND ".join(clauses)) if clauses else ""


# ---------------------------------------------------------------------------
# Public extractors
# ---------------------------------------------------------------------------

def get_fights_df(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Return one row per fighter per fight from fight_results.

    Joins event_details to supply date_proper and event name.  The result
    contains two rows per fight (one per fighter), matching the structure of
    the fight_results table.

    Columns returned
    ----------------
    fr.id, fr.fight_id, fr.event_id,
    fr.fighter_id, fr.opponent_id,
    fr.is_winner, fr."OUTCOME",
    fr.weight_class, fr."METHOD",
    fr."ROUND", fr."TIME",
    fr.is_title_fight, fr.is_interim_title, fr.is_championship_rounds,
    fr.fight_time_seconds, fr.total_fight_time_seconds,
    ed.date_proper, ed."EVENT" AS event_name
    """
    params: dict = {}
    date_filter = _date_where("ed", date_from, date_to, params)

    sql = text(f"""
        SELECT
            fr.id,
            fr.fight_id,
            fr.event_id,
            fr.fighter_id,
            fr.opponent_id,
            fr.is_winner,
            fr."OUTCOME",
            fr.weight_class,
            fr."METHOD",
            fr."ROUND",
            fr."TIME",
            fr.is_title_fight,
            fr.is_interim_title,
            fr.is_championship_rounds,
            fr.fight_time_seconds,
            fr.total_fight_time_seconds,
            ed.date_proper,
            ed."EVENT" AS event_name
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
        {date_filter}
        ORDER BY ed.date_proper, fr.fight_id, fr.fighter_id
    """)

    df = pd.read_sql(sql, engine, params=params)
    logger.info("get_fights_df: %d rows (date_from=%s, date_to=%s)", len(df), date_from, date_to)
    return df


def get_stats_df(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Return per-fighter per-round fight statistics from fight_stats.

    Includes both numeric-round rows AND the 'Totals' summary rows — callers
    are responsible for filtering.  Joins event_details for date_proper so
    stats can be ordered chronologically.

    Columns returned
    ----------------
    fs.id, fs.fight_id, fs.event_id, fs.fighter_id,
    fs."ROUND",
    fs.kd_int,
    fs.sig_str_landed, fs.sig_str_attempted, fs.sig_str_pct,
    fs.total_str_landed, fs.total_str_attempted,
    fs.td_landed, fs.td_attempted, fs.td_pct,
    fs.ctrl_seconds,
    fs.head_landed, fs.head_attempted,
    fs.body_landed, fs.body_attempted,
    fs.leg_landed, fs.leg_attempted,
    fs.distance_landed, fs.distance_attempted,
    fs.clinch_landed, fs.clinch_attempted,
    fs.ground_landed, fs.ground_attempted,
    ed.date_proper
    """
    params: dict = {}
    date_filter = _date_where("ed", date_from, date_to, params)

    sql = text(f"""
        SELECT
            fs.id,
            fs.fight_id,
            fs.event_id,
            fs.fighter_id,
            fs."ROUND",
            fs.kd_int,
            fs.sig_str_landed,
            fs.sig_str_attempted,
            fs.sig_str_pct,
            fs.total_str_landed,
            fs.total_str_attempted,
            fs.td_landed,
            fs.td_attempted,
            fs.td_pct,
            fs.ctrl_seconds,
            fs.head_landed,
            fs.head_attempted,
            fs.body_landed,
            fs.body_attempted,
            fs.leg_landed,
            fs.leg_attempted,
            fs.distance_landed,
            fs.distance_attempted,
            fs.clinch_landed,
            fs.clinch_attempted,
            fs.ground_landed,
            fs.ground_attempted,
            ed.date_proper
        FROM fight_stats fs
        JOIN event_details ed ON ed.id = fs.event_id
        WHERE fs.fighter_id IS NOT NULL
          AND ed.date_proper IS NOT NULL
        {date_filter}
        ORDER BY ed.date_proper, fs.fight_id, fs.fighter_id, fs."ROUND"
    """)

    df = pd.read_sql(sql, engine, params=params)
    logger.info("get_stats_df: %d rows (date_from=%s, date_to=%s)", len(df), date_from, date_to)
    return df


def get_fighters_df() -> pd.DataFrame:
    """Return one row per fighter combining fighter_details and fighter_tott.

    Left-joins fighter_tott so fighters without physical measurements are still
    included (tott columns will be NaN for those rows).

    Columns returned
    ----------------
    fd.id, fd."FIRST", fd."LAST", fd."NICKNAME",
    ft.height_inches, ft.weight_lbs, ft.reach_inches,
    ft."STANCE", ft.dob_date,
    ft.slpm, ft.str_acc, ft.sapm, ft.str_def,
    ft.td_avg, ft.td_acc, ft.td_def, ft.sub_avg
    """
    sql = text("""
        SELECT
            fd.id,
            fd."FIRST",
            fd."LAST",
            fd."NICKNAME",
            ft.height_inches,
            ft.weight_lbs,
            ft.reach_inches,
            ft."STANCE",
            ft.dob_date,
            ft.slpm,
            ft.str_acc,
            ft.sapm,
            ft.str_def,
            ft.td_avg,
            ft.td_acc,
            ft.td_def,
            ft.sub_avg
        FROM fighter_details fd
        LEFT JOIN fighter_tott ft ON ft.fighter_id = fd.id
        ORDER BY fd."LAST", fd."FIRST"
    """)

    df = pd.read_sql(sql, engine)
    logger.info("get_fighters_df: %d rows", len(df))
    return df


def get_events_df(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Return one row per event from event_details.

    Columns returned
    ----------------
    ed.id, ed."EVENT", ed.date_proper, ed."LOCATION"
    """
    params: dict = {}
    date_filter = _date_where("ed", date_from, date_to, params)

    # _date_where returns "AND ..." but this is the only filter,
    # so replace AND with WHERE when present.
    where = date_filter.replace("AND ", "WHERE ", 1) if date_filter else ""

    sql = text(f"""
        SELECT
            ed.id,
            ed."EVENT",
            ed.date_proper,
            ed."LOCATION"
        FROM event_details ed
        {where}
        ORDER BY ed.date_proper
    """)

    df = pd.read_sql(sql, engine, params=params)
    logger.info("get_events_df: %d rows (date_from=%s, date_to=%s)", len(df), date_from, date_to)
    return df

"""
Task 3.5 — Type Parsing

Adds parsed numeric columns alongside the original text columns.
Original text columns are preserved (never modified) so this is fully
reversible — just DROP the new columns if something goes wrong.

Columns added:

  fight_stats:
    sig_str_landed    INTEGER  ─┐ from "SIG.STR."   "X of Y"
    sig_str_attempted INTEGER  ─┘
    total_str_landed    INTEGER  ─┐ from "TOTAL STR." "X of Y"
    total_str_attempted INTEGER  ─┘
    td_landed           INTEGER  ─┐ from "TD"         "X of Y"
    td_attempted        INTEGER  ─┘
    head_landed         INTEGER  ─┐ from "HEAD"       "X of Y"
    head_attempted      INTEGER  ─┘
    body_landed         INTEGER  ─┐ from "BODY"       "X of Y"
    body_attempted      INTEGER  ─┘
    leg_landed          INTEGER  ─┐ from "LEG"        "X of Y"
    leg_attempted       INTEGER  ─┘
    distance_landed     INTEGER  ─┐ from "DISTANCE"   "X of Y"
    distance_attempted  INTEGER  ─┘
    clinch_landed       INTEGER  ─┐ from "CLINCH"     "X of Y"
    clinch_attempted    INTEGER  ─┘
    ground_landed       INTEGER  ─┐ from "GROUND"     "X of Y"
    ground_attempted    INTEGER  ─┘
    ctrl_seconds        INTEGER    from "CTRL"        "M:SS"
    sig_str_pct         NUMERIC    from "SIG.STR. %"  "NN%"
    td_pct              NUMERIC    from "TD %"         "NN%"
    kd_int              INTEGER    from "KD"           "N.0"

  fight_results:
    fight_time_seconds        INTEGER   from "TIME"  "M:SS"
    total_fight_time_seconds  INTEGER   (ROUND-1)*300 + fight_time_seconds

  fighter_tott:
    height_inches  NUMERIC   from "HEIGHT"  "F' I\""
    weight_lbs     NUMERIC   from "WEIGHT"  "NNN lbs."
    reach_inches   NUMERIC   from "REACH"   "NN\""
    dob_date       DATE      from "DOB"     "Mon DD, YYYY"

All UPDATEs are idempotent (WHERE parsed_col IS NULL).

Usage:
    cd backend/scraper
    python type_parsing.py
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure-Python parsing helpers (unit-testable without a DB connection)
# These mirror the SQL expressions used in the UPDATE statements below.
# ---------------------------------------------------------------------------

def parse_x_of_y_str(val):
    """Parse 'X of Y' string → (landed int, attempted int) or (None, None)."""
    if not val or not isinstance(val, str):
        return (None, None)
    val = val.strip()
    if not val or val in ('--', '---'):
        return (None, None)
    if ' of ' not in val:
        return (None, None)
    try:
        left, right = val.split(' of ', 1)
        return (int(left.strip()), int(right.strip()))
    except (ValueError, AttributeError):
        return (None, None)


def parse_ctrl_time_str(val):
    """Parse 'M:SS' string → total seconds as int, or None."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if not val or val in ('--', '---'):
        return None
    if ':' not in val:
        return None
    try:
        minutes, seconds = val.split(':', 1)
        return int(minutes) * 60 + int(seconds)
    except (ValueError, AttributeError):
        return None


def parse_height_inches_str(val):
    """Parse "F' I\"" → total inches as float, or None."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if not val or val in ('--', '---'):
        return None
    if "'" not in val:
        return None
    try:
        feet_str, rest = val.split("'", 1)
        inches_str = rest.strip().replace('"', '').strip()
        feet = int(feet_str.strip())
        inches = int(inches_str) if inches_str else 0
        return float(feet * 12 + inches)
    except (ValueError, AttributeError):
        return None


def parse_weight_lbs_str(val):
    """Parse "NNN lbs." → float lbs, or None."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if not val or val in ('--', '---'):
        return None
    try:
        return float(val.split()[0])
    except (ValueError, AttributeError, IndexError):
        return None


def parse_reach_inches_str(val):
    """Parse '74"' → float inches, or None."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if not val or val in ('--', '---'):
        return None
    try:
        return float(val.replace('"', '').strip())
    except ValueError:
        return None


def calc_total_fight_time(round_num, time_str):
    """Calculate total fight time in seconds from round number and time string.

    round_num: int or str (1-5), as stored in the ROUND column (TEXT in DB)
    time_str:  'M:SS' string, as stored in the TIME column
    Returns int seconds or None on any invalid input.
    """
    if round_num is None or time_str is None:
        return None
    try:
        round_int = int(round_num)
    except (ValueError, TypeError):
        return None
    time_secs = parse_ctrl_time_str(time_str)
    if time_secs is None:
        return None
    return (round_int - 1) * 300 + time_secs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_columns(conn, table, col_defs):
    """Add columns if they don't already exist."""
    existing = {
        r[0] for r in conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :tbl
        """), {"tbl": table}).fetchall()
    }
    for col, dtype in col_defs:
        if col not in existing:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN "{col}" {dtype}'))
            log.info(f"  + {table}.{col} ({dtype})")
        else:
            log.info(f"  = {table}.{col} already exists")
    conn.commit()


def parse_x_of_y(conn, src_col, landed_col, attempted_col):
    """Parse 'X of Y' text column into two INTEGER columns."""
    result = conn.execute(text(f"""
        UPDATE fight_stats
        SET "{landed_col}"   = SPLIT_PART("{src_col}", ' of ', 1)::INTEGER,
            "{attempted_col}" = SPLIT_PART("{src_col}", ' of ', 2)::INTEGER
        WHERE "{src_col}" LIKE '% of %'
          AND "{landed_col}" IS NULL
    """))
    conn.commit()
    return result.rowcount


# ---------------------------------------------------------------------------
# Step 1: fight_stats
# ---------------------------------------------------------------------------

def parse_fight_stats(conn):
    log.info("\n[1/3] fight_stats — adding and populating parsed columns")

    col_defs = [
        ("sig_str_landed",     "INTEGER"),
        ("sig_str_attempted",  "INTEGER"),
        ("total_str_landed",   "INTEGER"),
        ("total_str_attempted","INTEGER"),
        ("td_landed",          "INTEGER"),
        ("td_attempted",       "INTEGER"),
        ("head_landed",        "INTEGER"),
        ("head_attempted",     "INTEGER"),
        ("body_landed",        "INTEGER"),
        ("body_attempted",     "INTEGER"),
        ("leg_landed",         "INTEGER"),
        ("leg_attempted",      "INTEGER"),
        ("distance_landed",    "INTEGER"),
        ("distance_attempted", "INTEGER"),
        ("clinch_landed",      "INTEGER"),
        ("clinch_attempted",   "INTEGER"),
        ("ground_landed",      "INTEGER"),
        ("ground_attempted",   "INTEGER"),
        ("ctrl_seconds",       "INTEGER"),
        ("sig_str_pct",        "NUMERIC"),
        ("td_pct",             "NUMERIC"),
        ("kd_int",             "INTEGER"),
    ]
    add_columns(conn, "fight_stats", col_defs)

    # X of Y pairs
    xofy = [
        ("SIG.STR.",  "sig_str_landed",   "sig_str_attempted"),
        ("TOTAL STR.","total_str_landed",  "total_str_attempted"),
        ("TD",        "td_landed",         "td_attempted"),
        ("HEAD",      "head_landed",       "head_attempted"),
        ("BODY",      "body_landed",       "body_attempted"),
        ("LEG",       "leg_landed",        "leg_attempted"),
        ("DISTANCE",  "distance_landed",   "distance_attempted"),
        ("CLINCH",    "clinch_landed",     "clinch_attempted"),
        ("GROUND",    "ground_landed",     "ground_attempted"),
    ]
    total_xofy = 0
    for src, landed, attempted in xofy:
        n = parse_x_of_y(conn, src, landed, attempted)
        log.info(f"  {src:15s} → {landed}/{attempted}: {n:,} rows")
        total_xofy += n

    # CTRL: "M:SS" → seconds
    n = conn.execute(text("""
        UPDATE fight_stats
        SET ctrl_seconds =
            SPLIT_PART("CTRL", ':', 1)::INTEGER * 60 +
            SPLIT_PART("CTRL", ':', 2)::INTEGER
        WHERE "CTRL" IS NOT NULL
          AND "CTRL" LIKE '%:%'
          AND ctrl_seconds IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  CTRL → ctrl_seconds:         {n:,} rows")

    # SIG.STR. %: "47%" → 47.0
    n = conn.execute(text("""
        UPDATE fight_stats
        SET sig_str_pct = REPLACE("SIG.STR. %", '%', '')::NUMERIC
        WHERE "SIG.STR. %" IS NOT NULL
          AND sig_str_pct IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  SIG.STR. % → sig_str_pct:   {n:,} rows")

    # TD %: "29%" → 29.0
    n = conn.execute(text("""
        UPDATE fight_stats
        SET td_pct = REPLACE("TD %", '%', '')::NUMERIC
        WHERE "TD %" IS NOT NULL
          AND td_pct IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  TD % → td_pct:               {n:,} rows")

    # KD: "1.0" → 1
    n = conn.execute(text("""
        UPDATE fight_stats
        SET kd_int = "KD"::FLOAT::INTEGER
        WHERE "KD" IS NOT NULL
          AND kd_int IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  KD → kd_int:                 {n:,} rows")


# ---------------------------------------------------------------------------
# Step 2: fight_results
# ---------------------------------------------------------------------------

def parse_fight_results(conn):
    log.info("\n[2/3] fight_results — fight_time_seconds, total_fight_time_seconds")

    add_columns(conn, "fight_results", [
        ("fight_time_seconds",       "INTEGER"),
        ("total_fight_time_seconds", "INTEGER"),
    ])

    # TIME "M:SS" → seconds within round
    n = conn.execute(text("""
        UPDATE fight_results
        SET fight_time_seconds =
            SPLIT_PART("TIME", ':', 1)::INTEGER * 60 +
            SPLIT_PART("TIME", ':', 2)::INTEGER
        WHERE "TIME" IS NOT NULL
          AND "TIME" LIKE '%:%'
          AND fight_time_seconds IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  TIME → fight_time_seconds:   {n:,} rows")

    # total_fight_time_seconds = (ROUND - 1) * 300 + fight_time_seconds
    # Each UFC round is 5 minutes (300 seconds), regardless of title/non-title
    n = conn.execute(text("""
        UPDATE fight_results
        SET total_fight_time_seconds =
            ("ROUND"::INTEGER - 1) * 300 + fight_time_seconds
        WHERE fight_time_seconds IS NOT NULL
          AND "ROUND" IS NOT NULL
          AND total_fight_time_seconds IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  → total_fight_time_seconds:  {n:,} rows")


# ---------------------------------------------------------------------------
# Step 3: fighter_tott
# ---------------------------------------------------------------------------

def parse_fighter_tott(conn):
    log.info("\n[3/3] fighter_tott — height_inches, weight_lbs, reach_inches, dob_date")

    add_columns(conn, "fighter_tott", [
        ("height_inches", "NUMERIC"),
        ("weight_lbs",    "NUMERIC"),
        ("reach_inches",  "NUMERIC"),
        ("dob_date",      "DATE"),
    ])

    # HEIGHT: "5' 10\"" → (5*12 + 10) = 70.0 inches
    # SPLIT_PART on ' gives feet; strip " from second part for inches
    n = conn.execute(text(r"""
        UPDATE fighter_tott
        SET height_inches =
            SPLIT_PART("HEIGHT", '''', 1)::INTEGER * 12 +
            TRIM(REPLACE(SPLIT_PART("HEIGHT", '''', 2), '"', ''))::INTEGER
        WHERE "HEIGHT" IS NOT NULL
          AND "HEIGHT" LIKE '%''%'
          AND height_inches IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  HEIGHT → height_inches:      {n:,} rows")

    # WEIGHT: "170 lbs." → 170.0
    n = conn.execute(text("""
        UPDATE fighter_tott
        SET weight_lbs = SPLIT_PART("WEIGHT", ' ', 1)::NUMERIC
        WHERE "WEIGHT" IS NOT NULL
          AND "WEIGHT" LIKE '% lbs%'
          AND weight_lbs IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  WEIGHT → weight_lbs:         {n:,} rows")

    # REACH: "74\"" → 74.0
    n = conn.execute(text("""
        UPDATE fighter_tott
        SET reach_inches = REPLACE("REACH", '"', '')::NUMERIC
        WHERE "REACH" IS NOT NULL
          AND reach_inches IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  REACH → reach_inches:        {n:,} rows")

    # DOB: "Apr 01, 1988" → DATE
    n = conn.execute(text("""
        UPDATE fighter_tott
        SET dob_date = TO_DATE("DOB", 'Mon DD, YYYY')
        WHERE "DOB" IS NOT NULL
          AND dob_date IS NULL
    """)).rowcount
    conn.commit()
    log.info(f"  DOB → dob_date:              {n:,} rows")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(conn):
    log.info("\n" + "=" * 70)
    log.info("  VERIFICATION")
    log.info("=" * 70)

    # fight_stats spot check
    row = conn.execute(text("""
        SELECT "FIGHTER", "SIG.STR.", sig_str_landed, sig_str_attempted,
               "CTRL", ctrl_seconds, "KD", kd_int, sig_str_pct
        FROM fight_stats
        WHERE sig_str_landed IS NOT NULL
          AND "CTRL" IS NOT NULL
        LIMIT 3
    """)).fetchall()
    log.info("\n  fight_stats sample:")
    for r in row:
        log.info(f"    {r[0]:20s} SIG={r[1]} → {r[2]}/{r[3]}  "
                 f"CTRL={r[4]} → {r[5]}s  KD={r[6]} → {r[7]}  pct={r[8]}")

    # fight_results spot check
    row2 = conn.execute(text("""
        SELECT "BOUT", "ROUND", "TIME", fight_time_seconds, total_fight_time_seconds
        FROM fight_results
        WHERE fight_time_seconds IS NOT NULL
        LIMIT 4
    """)).fetchall()
    log.info("\n  fight_results sample:")
    for r in row2:
        log.info(f"    {r[0][:35]:35s} R{r[1]} {r[2]} → {r[3]}s  total={r[4]}s")

    # fighter_tott spot check
    row3 = conn.execute(text("""
        SELECT "FIGHTER", "HEIGHT", height_inches, "WEIGHT", weight_lbs,
               "REACH", reach_inches, "DOB", dob_date
        FROM fighter_tott
        WHERE height_inches IS NOT NULL
          AND reach_inches IS NOT NULL
        LIMIT 4
    """)).fetchall()
    log.info("\n  fighter_tott sample:")
    for r in row3:
        log.info(f"    {r[0]:22s} H={r[1]} → {r[2]}in  "
                 f"W={r[3]} → {r[4]}lbs  R={r[5]} → {r[6]}in  DOB={r[7]} → {r[8]}")

    # Coverage counts
    log.info("\n  Coverage summary:")
    fs_total = conn.execute(text("SELECT COUNT(*) FROM fight_stats")).scalar()
    for col in ["sig_str_landed", "ctrl_seconds", "sig_str_pct", "kd_int"]:
        cnt = conn.execute(text(f"SELECT COUNT({col}) FROM fight_stats")).scalar()
        log.info(f"    fight_stats.{col}: {cnt:,} / {fs_total:,}")

    fr_total = conn.execute(text("SELECT COUNT(*) FROM fight_results")).scalar()
    for col in ["fight_time_seconds", "total_fight_time_seconds"]:
        cnt = conn.execute(text(f"SELECT COUNT({col}) FROM fight_results")).scalar()
        log.info(f"    fight_results.{col}: {cnt:,} / {fr_total:,}")

    tott_total = conn.execute(text("SELECT COUNT(*) FROM fighter_tott")).scalar()
    for col in ["height_inches", "weight_lbs", "reach_inches", "dob_date"]:
        cnt = conn.execute(text(f"SELECT COUNT({col}) FROM fighter_tott")).scalar()
        log.info(f"    fighter_tott.{col}: {cnt:,} / {tott_total:,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_type_parsing():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.5 — Type Parsing")
    log.info("=" * 70)

    with engine.connect() as conn:
        parse_fight_stats(conn)
        parse_fight_results(conn)
        parse_fighter_tott(conn)
        verify(conn)

    log.info("\n  Done.")


if __name__ == "__main__":
    run_type_parsing()

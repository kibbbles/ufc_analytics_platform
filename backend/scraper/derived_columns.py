"""
Task 3.6 — Derived Columns

Adds four derived columns to fight_results. All are computed from existing
columns — no external data needed. Original columns are never modified.

Columns added to fight_results:
  weight_class          TEXT     canonical weight class extracted from WEIGHTCLASS
  is_title_fight        BOOLEAN  TRUE if WEIGHTCLASS contains 'Title'
  is_interim_title      BOOLEAN  TRUE if WEIGHTCLASS contains 'Interim' (subset of title)
  is_championship_rounds BOOLEAN TRUE if TIME FORMAT is '5 Rnd (5-5-5-5-5)'

Notes:
  - fight_bonus intentionally excluded: not tracked on UFCStats.com.
    Would require scraping UFC.com or Tapology separately.
  - 11 early-UFC tournament bouts (UFC 2-10, Ultimate Ultimate '95/'96)
    have no standard weight class — mapped to 'Open Weight' as they were
    genuinely open weight era events.
  - WEIGHTCLASS strings are complex (e.g. "Ultimate Fighter 33 Flyweight
    Tournament Title Bout") — weight_class is extracted via LIKE matching
    on the canonical class name within the string.

All operations are idempotent (WHERE col IS NULL).

Usage:
    cd backend/scraper
    python derived_columns.py
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Ordered most-specific → least-specific to avoid substring collisions
# e.g. 'Light Heavyweight' must come before 'Heavyweight'
WEIGHT_CLASS_CASE = """
    CASE
        WHEN "WEIGHTCLASS" LIKE '%Women''s Strawweight%'   THEN 'Women''s Strawweight'
        WHEN "WEIGHTCLASS" LIKE '%Women''s Flyweight%'     THEN 'Women''s Flyweight'
        WHEN "WEIGHTCLASS" LIKE '%Women''s Bantamweight%'  THEN 'Women''s Bantamweight'
        WHEN "WEIGHTCLASS" LIKE '%Women''s Featherweight%' THEN 'Women''s Featherweight'
        WHEN "WEIGHTCLASS" LIKE '%Light Heavyweight%'      THEN 'Light Heavyweight'
        WHEN "WEIGHTCLASS" LIKE '%Super Heavyweight%'      THEN 'Super Heavyweight'
        WHEN "WEIGHTCLASS" LIKE '%Heavyweight%'            THEN 'Heavyweight'
        WHEN "WEIGHTCLASS" LIKE '%Middleweight%'           THEN 'Middleweight'
        WHEN "WEIGHTCLASS" LIKE '%Welterweight%'           THEN 'Welterweight'
        WHEN "WEIGHTCLASS" LIKE '%Lightweight%'            THEN 'Lightweight'
        WHEN "WEIGHTCLASS" LIKE '%Featherweight%'          THEN 'Featherweight'
        WHEN "WEIGHTCLASS" LIKE '%Bantamweight%'           THEN 'Bantamweight'
        WHEN "WEIGHTCLASS" LIKE '%Flyweight%'              THEN 'Flyweight'
        WHEN "WEIGHTCLASS" LIKE '%Catch Weight%'           THEN 'Catch Weight'
        WHEN "WEIGHTCLASS" LIKE '%Open Weight%'            THEN 'Open Weight'
        WHEN "WEIGHTCLASS" LIKE '%Superfight%'             THEN 'Open Weight'
        ELSE 'Open Weight'  -- early UFC tournament bouts (UFC 2-10, no weight class)
    END
"""


def add_columns(conn):
    existing = {
        r[0] for r in conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'fight_results'
        """)).fetchall()
    }
    col_defs = [
        ("weight_class",           "TEXT"),
        ("is_title_fight",         "BOOLEAN"),
        ("is_interim_title",       "BOOLEAN"),
        ("is_championship_rounds", "BOOLEAN"),
    ]
    for col, dtype in col_defs:
        if col not in existing:
            conn.execute(text(f'ALTER TABLE fight_results ADD COLUMN "{col}" {dtype}'))
            log.info(f"  + fight_results.{col} ({dtype})")
        else:
            log.info(f"  = fight_results.{col} already exists")
    conn.commit()


def populate_weight_class(conn):
    n = conn.execute(text(f"""
        UPDATE fight_results
        SET weight_class = {WEIGHT_CLASS_CASE}
        WHERE weight_class IS NULL
          AND "WEIGHTCLASS" IS NOT NULL
    """)).rowcount
    conn.commit()
    log.info(f"  weight_class:            {n:,} rows populated")
    return n


def populate_is_title_fight(conn):
    n = conn.execute(text("""
        UPDATE fight_results
        SET is_title_fight = ("WEIGHTCLASS" LIKE '%Title%')
        WHERE is_title_fight IS NULL
          AND "WEIGHTCLASS" IS NOT NULL
    """)).rowcount
    conn.commit()
    log.info(f"  is_title_fight:          {n:,} rows populated")
    return n


def populate_is_interim_title(conn):
    n = conn.execute(text("""
        UPDATE fight_results
        SET is_interim_title = ("WEIGHTCLASS" LIKE '%Interim%')
        WHERE is_interim_title IS NULL
          AND "WEIGHTCLASS" IS NOT NULL
    """)).rowcount
    conn.commit()
    log.info(f"  is_interim_title:        {n:,} rows populated")
    return n


def populate_is_championship_rounds(conn):
    n = conn.execute(text("""
        UPDATE fight_results
        SET is_championship_rounds = ("TIME FORMAT" = '5 Rnd (5-5-5-5-5)')
        WHERE is_championship_rounds IS NULL
          AND "TIME FORMAT" IS NOT NULL
    """)).rowcount
    conn.commit()
    log.info(f"  is_championship_rounds:  {n:,} rows populated")
    return n


def verify(conn):
    log.info("\n" + "=" * 70)
    log.info("  VERIFICATION")
    log.info("=" * 70)

    # weight_class distribution
    log.info("\n  weight_class distribution:")
    rows = conn.execute(text("""
        SELECT weight_class, COUNT(*) as cnt
        FROM fight_results
        GROUP BY weight_class
        ORDER BY cnt DESC
    """)).fetchall()
    for r in rows:
        log.info(f"    {str(r[0]):30s} {r[1]:>5}")

    # title fight counts
    title = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE is_title_fight)         AS title,
            COUNT(*) FILTER (WHERE is_interim_title)       AS interim,
            COUNT(*) FILTER (WHERE is_championship_rounds) AS champ_rounds,
            COUNT(*)                                       AS total
        FROM fight_results
    """)).fetchone()
    log.info(f"\n  is_title_fight=TRUE:          {title[0]:,}")
    log.info(f"  is_interim_title=TRUE:        {title[1]:,}")
    log.info(f"  is_championship_rounds=TRUE:  {title[2]:,}")
    log.info(f"  total:                        {title[3]:,}")

    # Spot checks
    log.info("\n  Spot checks:")
    checks = conn.execute(text("""
        SELECT "BOUT", weight_class, is_title_fight, is_interim_title,
               is_championship_rounds
        FROM fight_results
        WHERE "BOUT" LIKE '%Khabib%' AND "BOUT" LIKE '%McGregor%'
        UNION ALL
        SELECT "BOUT", weight_class, is_title_fight, is_interim_title,
               is_championship_rounds
        FROM fight_results
        WHERE "BOUT" LIKE '%Jones%' AND "BOUT" LIKE '%Cormier%'
          AND is_title_fight = TRUE
        LIMIT 3
    """)).fetchall()
    for r in checks:
        log.info(f"    {r[0][:40]:40s} class={r[1]}  "
                 f"title={r[2]}  interim={r[3]}  5rnd={r[4]}")

    # Any NULL weight_class remaining?
    null_wc = conn.execute(text("""
        SELECT COUNT(*) FROM fight_results WHERE weight_class IS NULL
    """)).scalar()
    log.info(f"\n  weight_class NULL remaining: {null_wc}")


def run_derived_columns():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.6 — Derived Columns")
    log.info("=" * 70)

    with engine.connect() as conn:
        log.info("\n  Adding columns...")
        add_columns(conn)

        log.info("\n  Populating...")
        populate_weight_class(conn)
        populate_is_title_fight(conn)
        populate_is_interim_title(conn)
        populate_is_championship_rounds(conn)

        verify(conn)

    log.info("\n  Done.")


if __name__ == "__main__":
    run_derived_columns()

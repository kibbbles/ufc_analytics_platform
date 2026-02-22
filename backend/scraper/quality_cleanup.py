"""
Task 3.4 — Quality Cleanup

Three operations, all idempotent (safe to re-run):

1. Trim trailing spaces from fight_results."METHOD"
   Every value was scraped with a trailing space: 'KO/TKO ', 'Submission ', etc.

2. Replace '--' placeholder values with NULL in fighter_tott
   Columns: HEIGHT, WEIGHT, REACH, STANCE, DOB

3. Replace '--' placeholder values with NULL in fight_stats
   Columns: SIG.STR. %, TD %, CTRL
   (KD, SIG.STR., TOTAL STR., TD, SUB.ATT, REV., HEAD, BODY, LEG,
    DISTANCE, CLINCH, GROUND had no '--' values — confirmed by audit)

WEIGHTCLASS normalization intentionally excluded — handled in Task 3.6
alongside is_title_fight and weight_class derivation.

Usage:
    cd backend/scraper
    python quality_cleanup.py
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def trim_method(conn):
    """Strip trailing spaces from fight_results.METHOD."""
    # Count how many still need trimming
    needs_trim = conn.execute(text("""
        SELECT COUNT(*) FROM fight_results
        WHERE "METHOD" != TRIM("METHOD")
          AND "METHOD" IS NOT NULL
    """)).scalar()
    log.info(f"  METHOD rows needing trim: {needs_trim:,}")

    if needs_trim == 0:
        log.info("  Nothing to do.")
        return 0

    result = conn.execute(text("""
        UPDATE fight_results
        SET "METHOD" = TRIM("METHOD")
        WHERE "METHOD" != TRIM("METHOD")
          AND "METHOD" IS NOT NULL
    """))
    conn.commit()
    log.info(f"  Trimmed: {result.rowcount:,} rows")
    return result.rowcount


def null_fighter_tott_dashes(conn):
    """Replace '--' placeholders with NULL in fighter_tott."""
    cols = ['HEIGHT', 'WEIGHT', 'REACH', 'STANCE', 'DOB']
    total_updated = 0
    for col in cols:
        result = conn.execute(text(f"""
            UPDATE fighter_tott
            SET "{col}" = NULL
            WHERE "{col}" IN ('--', '---', '')
        """))
        conn.commit()
        if result.rowcount:
            log.info(f"  fighter_tott.{col}: {result.rowcount:,} rows → NULL")
            total_updated += result.rowcount
    if total_updated == 0:
        log.info("  Nothing to do.")
    return total_updated


def null_fight_stats_dashes(conn):
    """Replace '--' placeholders with NULL in fight_stats."""
    cols = ['SIG.STR. %', 'TD %', 'CTRL']
    total_updated = 0
    for col in cols:
        result = conn.execute(text(f"""
            UPDATE fight_stats
            SET "{col}" = NULL
            WHERE "{col}" IN ('--', '---', '')
        """))
        conn.commit()
        if result.rowcount:
            log.info(f"  fight_stats.{col}: {result.rowcount:,} rows → NULL")
            total_updated += result.rowcount
    if total_updated == 0:
        log.info("  Nothing to do.")
    return total_updated


def run_quality_cleanup():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.4 — Quality Cleanup")
    log.info("=" * 70)

    with engine.connect() as conn:
        # --- Step 1: METHOD trim ---
        log.info("\n[1/3] Trim fight_results.METHOD trailing spaces")
        trim_method(conn)

        # --- Step 2: fighter_tott '--' → NULL ---
        log.info("\n[2/3] fighter_tott: '--' → NULL")
        null_fighter_tott_dashes(conn)

        # --- Step 3: fight_stats '--' → NULL ---
        log.info("\n[3/3] fight_stats: '--' → NULL")
        null_fight_stats_dashes(conn)

        # --- Verification ---
        log.info("\n" + "=" * 70)
        log.info("  VERIFICATION")
        log.info("=" * 70)

        # METHOD should have no trailing spaces
        trailing = conn.execute(text("""
            SELECT COUNT(*) FROM fight_results
            WHERE "METHOD" != TRIM("METHOD") AND "METHOD" IS NOT NULL
        """)).scalar()
        log.info(f"  METHOD with trailing spaces remaining: {trailing}")

        # METHOD distinct values (should now be clean)
        log.info("  METHOD distinct values:")
        methods = conn.execute(text("""
            SELECT "METHOD", COUNT(*) FROM fight_results
            GROUP BY "METHOD" ORDER BY COUNT(*) DESC
        """)).fetchall()
        for m in methods:
            log.info(f"    {repr(m[0]):35s} {m[1]:>5}")

        # fighter_tott NULL counts
        log.info("\n  fighter_tott NULL counts (after cleanup):")
        for col in ['HEIGHT', 'WEIGHT', 'REACH', 'STANCE', 'DOB']:
            null_cnt = conn.execute(text(f"""
                SELECT COUNT(*) FROM fighter_tott WHERE "{col}" IS NULL
            """)).scalar()
            total = conn.execute(text("SELECT COUNT(*) FROM fighter_tott")).scalar()
            log.info(f"    {col:8s}: {null_cnt:,} / {total:,} NULL")

        # fight_stats NULL counts
        log.info("\n  fight_stats NULL counts (after cleanup):")
        for col in ['SIG.STR. %', 'TD %', 'CTRL']:
            null_cnt = conn.execute(text(f"""
                SELECT COUNT(*) FROM fight_stats WHERE "{col}" IS NULL
            """)).scalar()
            total = conn.execute(text("SELECT COUNT(*) FROM fight_stats")).scalar()
            log.info(f"    {col:12s}: {null_cnt:,} / {total:,} NULL")


if __name__ == "__main__":
    run_quality_cleanup()

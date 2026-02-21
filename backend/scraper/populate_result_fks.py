"""
Task 3.2 — Populate fight_results.fighter_id, opponent_id, is_winner

Uses the fighter_a_id / fighter_b_id now populated in fight_details (Task 3.1)
combined with fight_results.OUTCOME to determine winner and loser per fight.

OUTCOME encoding:
  'W/L'   → fighter A (from BOUT) won
  'L/W'   → fighter B (from BOUT) won
  'NC/NC' → No contest   (is_winner = FALSE, fighter_id = fighter_a)
  'D/D'   → Draw         (is_winner = FALSE, fighter_id = fighter_a)

fighter_id  = winner (or fighter_a for NC/Draw)
opponent_id = loser  (or fighter_b for NC/Draw)
is_winner   = TRUE for W/L and L/W, FALSE for NC and Draw

Only processes rows where fighter_id IS NULL (idempotent — safe to re-run).

Usage:
    cd backend/scraper
    python populate_result_fks.py
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def populate_result_fks():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.2 — Populate fight_results fighter_id / opponent_id / is_winner")
    log.info("=" * 70)

    with engine.connect() as conn:
        # Status before
        total, already_done = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_id) FROM fight_results
        """)).fetchone()
        log.info(f"\nBefore: {already_done:,} / {total:,} rows already have fighter_id")

        if already_done == total:
            log.info("  Nothing to do.")
            return

        # --- W/L: fighter A won ---
        result = conn.execute(text("""
            UPDATE fight_results fr
            SET fighter_id  = fd.fighter_a_id,
                opponent_id = fd.fighter_b_id,
                is_winner   = TRUE
            FROM fight_details fd
            WHERE fr.fight_id = fd.id
              AND fr."OUTCOME" = 'W/L'
              AND fd.fighter_a_id IS NOT NULL
              AND fr.fighter_id IS NULL
        """))
        conn.commit()
        wl_updated = result.rowcount
        log.info(f"\n  W/L  (fighter A won): {wl_updated:,} rows updated")

        # --- L/W: fighter B won ---
        result = conn.execute(text("""
            UPDATE fight_results fr
            SET fighter_id  = fd.fighter_b_id,
                opponent_id = fd.fighter_a_id,
                is_winner   = TRUE
            FROM fight_details fd
            WHERE fr.fight_id = fd.id
              AND fr."OUTCOME" = 'L/W'
              AND fd.fighter_b_id IS NOT NULL
              AND fr.fighter_id IS NULL
        """))
        conn.commit()
        lw_updated = result.rowcount
        log.info(f"  L/W  (fighter B won): {lw_updated:,} rows updated")

        # --- NC/NC and D/D: no winner ---
        result = conn.execute(text("""
            UPDATE fight_results fr
            SET fighter_id  = fd.fighter_a_id,
                opponent_id = fd.fighter_b_id,
                is_winner   = FALSE
            FROM fight_details fd
            WHERE fr.fight_id = fd.id
              AND fr."OUTCOME" IN ('NC/NC', 'D/D')
              AND fd.fighter_a_id IS NOT NULL
              AND fr.fighter_id IS NULL
        """))
        conn.commit()
        nc_updated = result.rowcount
        log.info(f"  NC/Draw (no winner):  {nc_updated:,} rows updated")

        # --- Rows that still couldn't be resolved (fight_details had NULL IDs) ---
        still_null = conn.execute(text("""
            SELECT COUNT(*) FROM fight_results WHERE fighter_id IS NULL
        """)).scalar()

        # Final status
        total_after, populated_after = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_id) FROM fight_results
        """)).fetchone()

        log.info("\n" + "=" * 70)
        log.info("  RESULTS")
        log.info("=" * 70)
        log.info(f"  fighter_id populated: {populated_after:,} / {total_after:,}")
        log.info(f"  is_winner = TRUE:     {wl_updated + lw_updated:,}")
        log.info(f"  is_winner = FALSE:    {nc_updated:,}  (NC/Draw)")
        log.info(f"  Still NULL:           {still_null:,}  (fight_details had no fighter IDs)")

        # Sanity check: verify a known fight
        log.info("\n  Sanity check — McGregor vs Poirier:")
        check = conn.execute(text("""
            SELECT fr."BOUT", fr."OUTCOME", fr.is_winner,
                   fw."FIRST" || ' ' || fw."LAST" AS winner,
                   fo."FIRST" || ' ' || fo."LAST" AS opponent
            FROM fight_results fr
            JOIN fighter_details fw ON fr.fighter_id  = fw.id
            JOIN fighter_details fo ON fr.opponent_id = fo.id
            WHERE fr."BOUT" LIKE '%McGregor%' AND fr."BOUT" LIKE '%Poirier%'
            LIMIT 3
        """)).fetchall()
        for r in check:
            log.info(f"    BOUT:     {r[0]}")
            log.info(f"    OUTCOME:  {r[1]}  is_winner={r[2]}")
            log.info(f"    winner:   {r[3]}  opponent: {r[4]}")


if __name__ == "__main__":
    populate_result_fks()

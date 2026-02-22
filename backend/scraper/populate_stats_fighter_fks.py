"""
Task 3.3 (Part 1) — Populate fight_stats.fighter_id

Every fight_stats row has a fight_id that links to fight_details, which already
has fighter_a_id and fighter_b_id populated (Task 3.1). So for each row we know
exactly 2 candidate fighters — we just need to match the "FIGHTER" text column
against those two names.

Two-pass strategy:
  Pass 1 (SQL)  — case-insensitive exact match.  Covers ~99%+ of rows.
  Pass 2 (Python/rapidfuzz) — for any still-NULL rows, fuzzy-match the
                               "FIGHTER" string against the 2 candidate names.
                               Score cutoff 80 (lower than global matching
                               because we only ever choose between 2 fighters).

Only processes rows where fighter_id IS NULL (idempotent — safe to re-run).

Usage:
    cd backend/scraper
    python populate_stats_fighter_fks.py
"""

import sys
import os
import logging
from sqlalchemy import text
from rapidfuzz import fuzz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

FUZZY_CUTOFF = 80  # Lower threshold — only 2 candidates, so risk of wrong match is low


def _fighter_display_name(first, last):
    """Build full display name, handling single-name fighters (NULL FIRST)."""
    if first and last:
        return f"{first} {last}".strip()
    return (last or "").strip()


def pass1_sql_exact(conn):
    """
    Pure SQL exact match (case-insensitive, whitespace-trimmed).
    Returns number of rows updated.
    """
    result = conn.execute(text("""
        UPDATE fight_stats fs
        SET fighter_id =
            CASE
                WHEN LOWER(TRIM(fs."FIGHTER")) = LOWER(TRIM(
                    CASE WHEN fa."FIRST" IS NOT NULL
                         THEN fa."FIRST" || ' ' || fa."LAST"
                         ELSE fa."LAST" END
                )) THEN fd.fighter_a_id
                WHEN LOWER(TRIM(fs."FIGHTER")) = LOWER(TRIM(
                    CASE WHEN fb."FIRST" IS NOT NULL
                         THEN fb."FIRST" || ' ' || fb."LAST"
                         ELSE fb."LAST" END
                )) THEN fd.fighter_b_id
                ELSE NULL
            END
        FROM fight_details fd
        JOIN fighter_details fa ON fa.id = fd.fighter_a_id
        JOIN fighter_details fb ON fb.id = fd.fighter_b_id
        WHERE fs.fight_id = fd.id
          AND fs.fighter_id IS NULL
          AND (
              LOWER(TRIM(fs."FIGHTER")) = LOWER(TRIM(
                  CASE WHEN fa."FIRST" IS NOT NULL
                       THEN fa."FIRST" || ' ' || fa."LAST"
                       ELSE fa."LAST" END
              ))
              OR
              LOWER(TRIM(fs."FIGHTER")) = LOWER(TRIM(
                  CASE WHEN fb."FIRST" IS NOT NULL
                       THEN fb."FIRST" || ' ' || fb."LAST"
                       ELSE fb."LAST" END
              ))
          )
    """))
    conn.commit()
    return result.rowcount


def pass2_fuzzy(conn):
    """
    Python-based fuzzy fallback for rows still NULL after the SQL pass.
    For each row we only compare against the 2 fighters from that fight.
    Returns (resolved, unresolved) counts.
    """
    # Load still-unresolved rows with their two candidate fighters
    rows = conn.execute(text("""
        SELECT
            fs.id             AS stats_id,
            fs."FIGHTER"      AS fighter_text,
            fd.fighter_a_id,
            fa."FIRST"        AS a_first,
            fa."LAST"         AS a_last,
            fd.fighter_b_id,
            fb."FIRST"        AS b_first,
            fb."LAST"         AS b_last
        FROM fight_stats fs
        JOIN fight_details fd ON fd.id = fs.fight_id
        JOIN fighter_details fa ON fa.id = fd.fighter_a_id
        JOIN fighter_details fb ON fb.id = fd.fighter_b_id
        WHERE fs.fighter_id IS NULL
          AND fs."FIGHTER" IS NOT NULL
    """)).fetchall()

    if not rows:
        return 0, 0

    log.info(f"  Pass 2: {len(rows):,} rows need fuzzy matching")

    resolved = 0
    unresolved = []
    updates = []

    for stats_id, fighter_text, a_id, a_first, a_last, b_id, b_first, b_last in rows:
        clean = (fighter_text or "").strip().lower()
        name_a = _fighter_display_name(a_first, a_last).lower()
        name_b = _fighter_display_name(b_first, b_last).lower()

        score_a = fuzz.WRatio(clean, name_a)
        score_b = fuzz.WRatio(clean, name_b)

        best_score = max(score_a, score_b)
        if best_score >= FUZZY_CUTOFF:
            chosen_id = a_id if score_a >= score_b else b_id
            updates.append({"stats_id": stats_id, "fighter_id": chosen_id})
            resolved += 1
        else:
            unresolved.append((stats_id, fighter_text, name_a, name_b, score_a, score_b))

    # Apply fuzzy updates in batches
    for batch_start in range(0, len(updates), 500):
        batch = updates[batch_start: batch_start + 500]
        for row in batch:
            conn.execute(text("""
                UPDATE fight_stats
                SET fighter_id = :fighter_id
                WHERE id = :stats_id
                  AND fighter_id IS NULL
            """), row)
        conn.commit()
        log.info(f"    Fuzzy batch committed: {batch_start + len(batch):,}")

    # Log unresolved
    if unresolved:
        log_path = os.path.join(os.path.dirname(__file__), "unresolved_stats_fighters.log")
        with open(log_path, "w") as f:
            f.write("stats_id\tfighter_text\tname_a\tname_b\tscore_a\tscore_b\n")
            for r in unresolved:
                f.write("\t".join(str(x) for x in r) + "\n")
        log.info(f"    Unresolved written to: unresolved_stats_fighters.log")

    return resolved, len(unresolved)


def populate_stats_fighter_fks():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.3 (Part 1) — Populate fight_stats.fighter_id")
    log.info("=" * 70)

    with engine.connect() as conn:
        # Status before
        total, already_done = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_id) FROM fight_stats
        """)).fetchone()
        log.info(f"\nBefore: {already_done:,} / {total:,} rows already have fighter_id")

        if already_done == total:
            log.info("  Nothing to do.")
            return

        todo = total - already_done
        log.info(f"  Rows to resolve: {todo:,}")

        # --- Pass 1: SQL exact match ---
        log.info("\n  Pass 1: SQL exact match...")
        p1_updated = pass1_sql_exact(conn)
        log.info(f"  Pass 1 resolved: {p1_updated:,} rows")

        # --- Pass 2: Python fuzzy fallback ---
        still_null = conn.execute(text(
            "SELECT COUNT(*) FROM fight_stats WHERE fighter_id IS NULL"
        )).scalar()

        if still_null > 0:
            log.info(f"\n  Pass 2: fuzzy fallback ({still_null:,} rows remaining)...")
            p2_resolved, p2_unresolved = pass2_fuzzy(conn)
            log.info(f"  Pass 2 resolved: {p2_resolved:,}  unresolved: {p2_unresolved:,}")
        else:
            p2_resolved, p2_unresolved = 0, 0
            log.info("\n  Pass 2 skipped — nothing left to resolve.")

        # Final status
        total_after, populated_after = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_id) FROM fight_stats
        """)).fetchone()
        final_null = total_after - populated_after

        log.info("\n" + "=" * 70)
        log.info("  RESULTS")
        log.info("=" * 70)
        log.info(f"  fighter_id populated: {populated_after:,} / {total_after:,}  "
                 f"({populated_after / total_after * 100:.2f}%)")
        log.info(f"  Pass 1 (SQL exact):   {p1_updated:,}")
        log.info(f"  Pass 2 (fuzzy):       {p2_resolved:,}")
        log.info(f"  Still NULL:           {final_null:,}")

        # Sanity check — spot-check a known fight
        log.info("\n  Sanity check — Khabib vs McGregor:")
        check = conn.execute(text("""
            SELECT fs."FIGHTER", fs."ROUND",
                   fd."FIRST" || ' ' || fd."LAST" AS resolved_name
            FROM fight_stats fs
            JOIN fighter_details fd ON fd.id = fs.fighter_id
            WHERE fs."BOUT" LIKE '%Khabib%' AND fs."BOUT" LIKE '%McGregor%'
            ORDER BY fs."ROUND"
            LIMIT 6
        """)).fetchall()
        for r in check:
            log.info(f"    FIGHTER='{r[0]}'  ROUND={r[1]}  → resolved='{r[2]}'")


if __name__ == "__main__":
    populate_stats_fighter_fks()

"""
Task 3.1 — Populate fight_details.fighter_a_id and fighter_b_id

Parses the BOUT text column ("Fighter A vs. Fighter B") in fight_details and
resolves each name against fighter_details using exact match first, then
rapidfuzz fuzzy matching as a fallback.

Only processes rows where fighter_a_id IS NULL (idempotent — safe to re-run).
Writes unresolved names to unresolved_fighter_names.log for manual review.

Usage:
    cd backend/scraper
    python populate_fighter_fks.py
"""

import sys
import os
import logging
from sqlalchemy import text
from rapidfuzz import process, fuzz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SCORE_CUTOFF = 88  # Minimum fuzzy match confidence (0-100)


def build_fighter_lookup(conn):
    """Build name → id lookup from fighter_details. Handles NULL FIRST names."""
    rows = conn.execute(text(
        'SELECT id, "FIRST", "LAST" FROM fighter_details'
    )).fetchall()

    lookup = {}
    for fighter_id, first, last in rows:
        if first and last:
            full = f"{first} {last}".strip().lower()
        elif last:
            full = last.strip().lower()
        else:
            continue
        # Primary key: full name. Keep first occurrence on collision.
        if full not in lookup:
            lookup[full] = fighter_id

    log.info(f"  Fighter lookup built: {len(lookup):,} entries")
    return lookup


def resolve_name(name, lookup, names_list):
    """
    Try exact match, then fuzzy. Returns (fighter_id, match_type) or (None, None).
    match_type is 'exact' or 'fuzzy'.
    """
    clean = name.strip().lower()

    # 1. Exact match
    if clean in lookup:
        return lookup[clean], "exact"

    # 2. Fuzzy match against all known names
    result = process.extractOne(
        clean, names_list, scorer=fuzz.WRatio, score_cutoff=SCORE_CUTOFF
    )
    if result:
        matched_name, score, _ = result
        return lookup[matched_name], "fuzzy"

    return None, None


def populate_fighter_a_b_ids():
    log.info("\n" + "=" * 70)
    log.info("  TASK 3.1 — Populate fight_details.fighter_a_id / fighter_b_id")
    log.info("=" * 70)

    with engine.connect() as conn:
        # Status before
        total, already_done = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_a_id) FROM fight_details
        """)).fetchone()
        todo = total - already_done
        log.info(f"\nBefore: {already_done:,} / {total:,} rows already have fighter_a_id")
        log.info(f"  Rows to process: {todo:,}")

        if todo == 0:
            log.info("  Nothing to do.")
            return

        # Build lookup
        log.info("\nBuilding fighter name lookup...")
        lookup = build_fighter_lookup(conn)
        names_list = list(lookup.keys())

        # Load all fight_details rows that need resolving
        # Skip placeholder rows "win vs. "
        rows = conn.execute(text("""
            SELECT id, "BOUT"
            FROM fight_details
            WHERE fighter_a_id IS NULL
              AND "BOUT" IS NOT NULL
              AND "BOUT" != 'win vs. '
        """)).fetchall()

        log.info(f"  Rows to resolve: {len(rows):,}")

        updates = []
        stats = {"exact": 0, "fuzzy": 0, "unresolved_a": 0, "unresolved_b": 0}
        unresolved = []

        for fight_id, bout in rows:
            if " vs. " not in bout:
                unresolved.append((fight_id, bout, "no_separator"))
                stats["unresolved_a"] += 1
                continue

            parts = bout.split(" vs. ", 1)
            name_a = parts[0].strip()
            name_b = parts[1].strip()

            id_a, type_a = resolve_name(name_a, lookup, names_list)
            id_b, type_b = resolve_name(name_b, lookup, names_list)

            if id_a is None:
                stats["unresolved_a"] += 1
                unresolved.append((fight_id, name_a, "fighter_a"))
            else:
                stats[type_a] += 1

            if id_b is None:
                stats["unresolved_b"] += 1
                unresolved.append((fight_id, name_b, "fighter_b"))
            else:
                stats[type_b] += 1

            if id_a is not None or id_b is not None:
                updates.append({
                    "fight_id": fight_id,
                    "fighter_a_id": id_a,
                    "fighter_b_id": id_b,
                })

        # Batch update
        log.info(f"\nApplying {len(updates):,} updates...")
        for batch_start in range(0, len(updates), 500):
            batch = updates[batch_start : batch_start + 500]
            for row in batch:
                conn.execute(text("""
                    UPDATE fight_details
                    SET fighter_a_id = :fighter_a_id,
                        fighter_b_id = :fighter_b_id
                    WHERE id = :fight_id
                """), row)
            conn.commit()
            log.info(f"  Committed batch ending at {batch_start + len(batch):,}")

        # Final status
        total_after, populated_after = conn.execute(text("""
            SELECT COUNT(*), COUNT(fighter_a_id) FROM fight_details
        """)).fetchone()
        both_populated = conn.execute(text("""
            SELECT COUNT(*) FROM fight_details
            WHERE fighter_a_id IS NOT NULL AND fighter_b_id IS NOT NULL
        """)).scalar()

        log.info("\n" + "=" * 70)
        log.info("  RESULTS")
        log.info("=" * 70)
        log.info(f"  fighter_a_id populated: {populated_after:,} / {total_after:,}")
        log.info(f"  Both a+b populated:     {both_populated:,} / {total_after:,}")
        log.info(f"  Exact matches:          {stats['exact']:,}")
        log.info(f"  Fuzzy matches:          {stats['fuzzy']:,}")
        log.info(f"  Unresolved fighter_a:   {stats['unresolved_a']:,}")
        log.info(f"  Unresolved fighter_b:   {stats['unresolved_b']:,}")

        # Write unresolved log
        if unresolved:
            log_path = os.path.join(os.path.dirname(__file__), "unresolved_fighter_names.log")
            with open(log_path, "w") as f:
                f.write("fight_id\tname\trole\n")
                for fight_id, name, role in unresolved:
                    f.write(f"{fight_id}\t{name}\t{role}\n")
            log.info(f"\n  Unresolved names written to: unresolved_fighter_names.log")
        else:
            log.info("\n  No unresolved names.")


if __name__ == "__main__":
    populate_fighter_a_b_ids()

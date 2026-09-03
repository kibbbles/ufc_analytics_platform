"""
merge_duplicate_fighters.py — collapse fighter_details rows that are the same person

A fighter's identity on UFCStats is their URL. Where two fighter_details rows
share one URL, they are one person recorded twice: one row accumulated part of
the career and the other accumulated the rest, or none at all. This script moves
every reference onto a single surviving row and deletes the duplicate.

It selects pairs by URL equality ONLY. That is deliberate: two rows with
DIFFERENT URLs are two different people who happen to share a name (there are
two UFC Bruno Silvas, two Mike Davises), and merging those would be the exact
data corruption this whole effort exists to undo. Those cases are out of scope
here and this script will never touch them.

Survivor selection is not a judgement call: the surviving id is the one derived
from the URL slug (first 8 hex characters), which is the scheme the original
import used. If neither id matches its own URL, the pair is skipped rather than
guessed at.

DRY RUN BY DEFAULT. Nothing is written without --apply.

Usage:
    python backend/scraper/merge_duplicate_fighters.py            # plan only
    python backend/scraper/merge_duplicate_fighters.py --apply    # execute
"""

import sys
import os
import argparse
import logging

from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# Every column anywhere in the schema that holds a fighter_details.id.
# Verified against information_schema; if a new one is added and not listed
# here, the post-merge verification below will catch the dangling reference.
REFERENCES = [
    ("fight_details",   ["fighter_a_id", "fighter_b_id"]),
    ("fight_results",   ["fighter_id", "opponent_id"]),
    ("fight_stats",     ["fighter_id"]),
    ("upcoming_fights", ["fighter_a_id", "fighter_b_id"]),
    ("past_predictions", ["fighter_a_id", "fighter_b_id"]),
]

# fighter_tott is handled separately: its FK to fighter_details is ON DELETE
# CASCADE, so deleting a duplicate row silently destroys that row's tale of the
# tape. Physical stats must be consolidated onto the survivor BEFORE any delete.
TOTT_TABLE = "fighter_tott"


def id_from_url(url):
    """The id this table would give a fighter with this URL, or None."""
    if not url:
        return None
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    candidate = slug[:8].lower()
    if len(candidate) == 8 and all(c in "0123456789abcdef" for c in candidate):
        return candidate
    return None


def find_duplicate_pairs(conn):
    """Return [(url, survivor, [losers])] for every URL held by >1 row."""
    rows = conn.execute(text("""
        SELECT "URL", array_agg(id ORDER BY id) AS ids
        FROM fighter_details
        WHERE "URL" IS NOT NULL
        GROUP BY "URL"
        HAVING COUNT(*) > 1
        ORDER BY "URL"
    """)).fetchall()

    pairs, skipped = [], []
    for url, ids in rows:
        canonical = id_from_url(url)
        if canonical is None or canonical not in [i.lower() for i in ids]:
            # No id derives from this URL, so there is no principled survivor.
            # Skip rather than pick one - a wrong merge is unrecoverable.
            skipped.append((url, ids, "no id matches the URL slug"))
            continue
        survivor = next(i for i in ids if i.lower() == canonical)
        losers = [i for i in ids if i != survivor]
        pairs.append((url, survivor, losers))

    return pairs, skipped


def count_references(conn, fighter_id):
    """How many rows in each table point at this id."""
    counts = {}
    for table, cols in REFERENCES:
        clause = " OR ".join(f"{c} = :fid" for c in cols)
        counts[table] = conn.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE {clause}"), {"fid": fighter_id}
        ).scalar()
    counts[TOTT_TABLE] = conn.execute(
        text(f"SELECT COUNT(*) FROM {TOTT_TABLE} WHERE fighter_id = :fid"),
        {"fid": fighter_id},
    ).scalar()
    return counts


def plan(conn):
    """Build and print the merge plan. Returns the list of pairs to act on."""
    pairs, skipped = find_duplicate_pairs(conn)

    log.info("=" * 78)
    log.info("  MERGE PLAN")
    log.info("=" * 78)

    if skipped:
        log.warning("\n  SKIPPED (no principled survivor, needs manual review):")
        for url, ids, why in skipped:
            log.warning(f"    {', '.join(ids)}  {url}  — {why}")

    if not pairs:
        log.info("\n  No duplicate-URL fighter rows found. Nothing to do.")
        return pairs

    total = {t: 0 for t, _ in REFERENCES}
    total[TOTT_TABLE] = 0

    log.info("")
    for url, survivor, losers in pairs:
        name = conn.execute(text(
            'SELECT trim(coalesce("FIRST", \'\') || \' \' || coalesce("LAST", \'\')) '
            "FROM fighter_details WHERE id = :i"
        ), {"i": survivor}).scalar()
        log.info(f"  {name}")
        log.info(f"    keep   {survivor}   {url}")
        for loser in losers:
            counts = count_references(conn, loser)
            moved = ", ".join(f"{t}:{n}" for t, n in counts.items() if n) or "no references"
            log.info(f"    merge  {loser}  ->  {moved}")
            for t, n in counts.items():
                total[t] += n

    log.info("")
    log.info("  Totals to move:")
    for t, n in total.items():
        log.info(f"    {t:<18} {n}")
    log.info(f"    duplicate rows to delete: {sum(len(l) for _, _, l in pairs)}")
    return pairs


def merge(conn, pairs):
    """Repoint every reference onto the survivor, then delete the duplicate."""
    for url, survivor, losers in pairs:
        for loser in losers:
            if loser == survivor:
                raise RuntimeError(f"survivor and loser are the same id: {loser}")

            # 1. Ordinary reference columns.
            for table, cols in REFERENCES:
                for col in cols:
                    conn.execute(
                        text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old"),
                        {"new": survivor, "old": loser},
                    )

            # 2. Tale of the tape. Repoint first so the CASCADE on delete cannot
            #    take a row with real measurements in it.
            conn.execute(
                text(f"UPDATE {TOTT_TABLE} SET fighter_id = :new WHERE fighter_id = :old"),
                {"new": survivor, "old": loser},
            )

            # 3. Now that both rows' tott sit on the survivor, keep only the
            #    most complete one. Ties break on ctid so the choice is stable.
            conn.execute(text(f"""
                DELETE FROM {TOTT_TABLE}
                WHERE fighter_id = :fid AND ctid NOT IN (
                    SELECT ctid FROM {TOTT_TABLE}
                    WHERE fighter_id = :fid
                    ORDER BY (("HEIGHT" IS NOT NULL)::int + ("WEIGHT" IS NOT NULL)::int
                            + ("REACH"  IS NOT NULL)::int + ("DOB"    IS NOT NULL)::int) DESC,
                             ctid ASC
                    LIMIT 1
                )
            """), {"fid": survivor})

            # 4. The duplicate row is now unreferenced.
            conn.execute(
                text("DELETE FROM fighter_details WHERE id = :old"), {"old": loser}
            )
            log.info(f"  merged {loser} into {survivor}")


def verify(conn, pairs):
    """Assert the merge left the database in a coherent state."""
    problems = []

    remaining = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT "URL" FROM fighter_details WHERE "URL" IS NOT NULL
            GROUP BY "URL" HAVING COUNT(*) > 1
        ) t
    """)).scalar()
    if remaining:
        problems.append(f"{remaining} duplicate URL group(s) still present")

    # Nothing may still point at a deleted id.
    for _, _, losers in pairs:
        for loser in losers:
            counts = count_references(conn, loser)
            dangling = {t: n for t, n in counts.items() if n}
            if dangling:
                problems.append(f"{loser} still referenced by {dangling}")
            if conn.execute(text("SELECT COUNT(*) FROM fighter_details WHERE id = :i"),
                            {"i": loser}).scalar():
                problems.append(f"{loser} still exists in fighter_details")

    # A merge must never put the same fighter on both sides of a bout.
    self_fights = conn.execute(text("""
        SELECT COUNT(*) FROM fight_details
        WHERE fighter_a_id IS NOT NULL AND fighter_a_id = fighter_b_id
    """)).scalar()
    if self_fights:
        problems.append(f"{self_fights} bout(s) now have one fighter on both sides")

    # Scoped to the survivors this run touched. A global count would also see
    # the pre-existing duplicate tott rows belonging to fighters this script is
    # not allowed to merge (the same-name-different-people cases), and would
    # roll back a perfectly good merge for someone else's problem.
    survivors = [s for _, s, _ in pairs]
    if survivors:
        dup_tott = conn.execute(text(f"""
            SELECT COUNT(*) FROM (
                SELECT fighter_id FROM {TOTT_TABLE}
                WHERE fighter_id = ANY(:ids)
                GROUP BY fighter_id HAVING COUNT(*) > 1
            ) t
        """), {"ids": survivors}).scalar()
        if dup_tott:
            problems.append(
                f"{dup_tott} merged fighter(s) still have duplicate tott rows")

    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="execute the merge (default is a dry run)")
    args = ap.parse_args()

    with engine.begin() as conn:
        pairs = plan(conn)
        if not pairs:
            return 0

        if not args.apply:
            log.info("")
            log.info("  DRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        log.info("")
        log.info("=" * 78)
        log.info("  APPLYING")
        log.info("=" * 78)
        merge(conn, pairs)

        problems = verify(conn, pairs)
        if problems:
            log.error("\n  VERIFICATION FAILED — rolling back:")
            for p in problems:
                log.error(f"    {p}")
            raise RuntimeError("merge verification failed; transaction rolled back")

        log.info("\n  Verification passed. Committing.")

    log.info("  Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

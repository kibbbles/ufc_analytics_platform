"""
Task 3.1 — Populate fight_details.fighter_a_id and fighter_b_id

Parses the BOUT text column ("Fighter A vs. Fighter B") in fight_details and
resolves each name against fighter_details using exact match first, then
rapidfuzz fuzzy matching as a fallback.

Names are not identities. Two different fighters can share a name (there are two
UFC Bruno Silvas, a flyweight and a middleweight), and when that happens this
script CANNOT tell them apart from a BOUT string alone - no fight table stores a
fighter URL. An earlier version resolved the ambiguity by keeping whichever row
Postgres returned first, which filed 36 bouts under the wrong human being and
reported every one of them as an "exact" match.

So an ambiguous name is now refused rather than guessed: the FK is left NULL and
the name is written to unresolved_fighter_names.log with reason "ambiguous". A
missing FK is visible and repairable; a confidently wrong one is neither.

Only processes rows where fighter_a_id IS NULL (idempotent — safe to re-run), so
running this does not revisit or repair FKs that were already written.

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
    """Build a name → id lookup from fighter_details.

    Returns (lookup, ambiguous):
        lookup    — name → id, for names owned by exactly one fighter
        ambiguous — name → [ids], for names shared by two or more fighters

    Ambiguous names are deliberately kept OUT of `lookup` so that neither the
    exact nor the fuzzy path can silently resolve to one of them.
    """
    rows = conn.execute(text(
        'SELECT id, "FIRST", "LAST" FROM fighter_details'
    )).fetchall()

    # Collect every id per name first — deciding as we go is what allowed a
    # collision to be resolved by row order.
    by_name = {}
    for fighter_id, first, last in rows:
        first = (first or "").strip()
        last  = (last  or "").strip()
        # Mononyms appear both ways round in this table: the Greko import wrote
        # them as LAST with a NULL FIRST, the live scraper wrote them as FIRST
        # with an empty LAST. Both are the same person and both must be
        # reachable, or the row can never receive an FK at all.
        full = f"{first} {last}".strip().lower()
        if not full:
            continue
        by_name.setdefault(full, []).append(fighter_id)

    lookup    = {n: ids[0] for n, ids in by_name.items() if len(ids) == 1}
    ambiguous = {n: ids    for n, ids in by_name.items() if len(ids) > 1}

    log.info(f"  Fighter lookup built: {len(lookup):,} entries")
    if ambiguous:
        log.warning(
            f"  {len(ambiguous)} name(s) shared by multiple fighters — these will "
            f"be refused, not guessed:"
        )
        for name, ids in sorted(ambiguous.items()):
            log.warning(f"    {name}: {', '.join(ids)}")

    return lookup, ambiguous


def resolve_name(name, lookup, names_list, ambiguous=None):
    """
    Try exact match, then fuzzy. Returns (fighter_id, match_type).

    match_type is 'exact', 'fuzzy', 'ambiguous' (name belongs to more than one
    fighter, refused on purpose) or None (no match at all). fighter_id is None
    for anything other than 'exact' and 'fuzzy'.
    """
    clean = name.strip().lower()

    # 0. Refuse shared names. This must come first: guessing here is the bug
    #    this function exists to not have.
    if ambiguous and clean in ambiguous:
        return None, "ambiguous"

    # 1. Exact match
    if clean in lookup:
        return lookup[clean], "exact"

    # 2. Fuzzy match against all known unambiguous names
    result = process.extractOne(
        clean, names_list, scorer=fuzz.WRatio, score_cutoff=SCORE_CUTOFF
    )
    if result:
        matched_name, score, _ = result
        # Log every fuzzy hit. There are only a handful across the whole table
        # and each one is a silent rename, so they should be readable in the
        # run output rather than buried in a count.
        log.info(f"    fuzzy: {clean!r} → {matched_name!r} (score {score:.0f})")
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
        lookup, ambiguous = build_fighter_lookup(conn)
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
        stats = {"exact": 0, "fuzzy": 0, "ambiguous": 0,
                 "unresolved_a": 0, "unresolved_b": 0}
        unresolved = []

        for fight_id, bout in rows:
            if " vs. " not in bout:
                unresolved.append((fight_id, bout, "no_separator"))
                stats["unresolved_a"] += 1
                continue

            parts = bout.split(" vs. ", 1)
            name_a = parts[0].strip()
            name_b = parts[1].strip()

            id_a, type_a = resolve_name(name_a, lookup, names_list, ambiguous)
            id_b, type_b = resolve_name(name_b, lookup, names_list, ambiguous)

            for side, name, fid_resolved, kind in (
                ("fighter_a", name_a, id_a, type_a),
                ("fighter_b", name_b, id_b, type_b),
            ):
                if fid_resolved is not None:
                    stats[kind] += 1
                    continue
                # Refused or unmatched: record why, and leave the FK NULL.
                if kind == "ambiguous":
                    stats["ambiguous"] += 1
                stats[f"unresolved_{side[-1]}"] += 1
                unresolved.append((fight_id, name, f"{side}:{kind or 'no_match'}"))

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
        log.info(f"  Refused (ambiguous):    {stats['ambiguous']:,}")
        if stats["ambiguous"]:
            log.warning(
                "\n  Some names belong to more than one fighter and were left "
                "NULL on purpose.\n  Resolve them by merging or disambiguating "
                "the fighter_details rows, then re-run."
            )

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

"""
Populate foreign key relationships in the database.

This script creates foreign key relationships that don't exist in Greko CSVs
by matching on text fields (EVENT names, BOUT descriptions, FIGHTER names).

Foreign keys to populate:
- fight_details.event_id -> event_details.id
- fight_results.event_id -> event_details.id
- fight_results.fight_id -> fight_details.id
- fight_stats.event_id -> event_details.id
- fight_stats.fight_id -> fight_details.id
- fighter_tott.fighter_id -> fighter_details.id

Usage:
    python populate_foreign_keys.py
"""

import sys
import os
from sqlalchemy import text
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine


def print_header(title):
    """Print section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def populate_fight_details_event_id():
    """Populate fight_details.event_id from event_details by matching EVENT name."""
    print_header("1. POPULATING fight_details.event_id")

    with engine.connect() as conn:
        # First, check current status
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_details
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have event_id")

        # Update event_id by matching EVENT name
        result = conn.execute(text("""
            UPDATE fight_details fd
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fd."EVENT") = TRIM(ed."EVENT")
            AND fd.event_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        # Check final status
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_details
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have event_id")

        if row[1] == row[0]:
            print("[OK] All fight_details rows have event_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing event_id")
            return False


def populate_fight_results_event_id():
    """Populate fight_results.event_id from event_details by matching EVENT name."""
    print_header("2. POPULATING fight_results.event_id")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_results
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have event_id")

        result = conn.execute(text("""
            UPDATE fight_results fr
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fr."EVENT") = TRIM(ed."EVENT")
            AND fr.event_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_results
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have event_id")

        if row[1] == row[0]:
            print("[OK] All fight_results rows have event_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing event_id")
            return False


def populate_fight_results_fight_id():
    """Populate fight_results.fight_id from fight_details by matching EVENT + BOUT."""
    print_header("3. POPULATING fight_results.fight_id")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fight_id) as populated
            FROM fight_results
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have fight_id")

        result = conn.execute(text("""
            UPDATE fight_results fr
            SET fight_id = fd.id
            FROM fight_details fd
            WHERE TRIM(fr."BOUT") = TRIM(fd."BOUT")
            AND TRIM(fr."EVENT") = TRIM(fd."EVENT")
            AND fr.fight_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fight_id) as populated
            FROM fight_results
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have fight_id")

        if row[1] == row[0]:
            print("[OK] All fight_results rows have fight_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing fight_id")
            return False


def populate_fight_stats_event_id():
    """Populate fight_stats.event_id from event_details by matching EVENT name."""
    print_header("4. POPULATING fight_stats.event_id")

    with engine.connect() as conn:
        # Disable trigger temporarily (references non-existent updated_at column)
        try:
            conn.execute(text("ALTER TABLE fight_stats DISABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
            print("Temporarily disabled trigger")
        except:
            pass  # Trigger might not exist
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_stats
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have event_id")

        result = conn.execute(text("""
            UPDATE fight_stats fs
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fs."EVENT") = TRIM(ed."EVENT")
            AND fs.event_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(event_id) as populated
            FROM fight_stats
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have event_id")

        # Re-enable trigger
        try:
            conn.execute(text("ALTER TABLE fight_stats ENABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
            print("Re-enabled trigger")
        except:
            pass

        if row[1] == row[0]:
            print("[OK] All fight_stats rows have event_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing event_id")
            return False


def populate_fight_stats_fight_id():
    """Populate fight_stats.fight_id from fight_details by matching EVENT + BOUT."""
    print_header("5. POPULATING fight_stats.fight_id")

    with engine.connect() as conn:
        # Disable trigger temporarily (references non-existent updated_at column)
        try:
            conn.execute(text("ALTER TABLE fight_stats DISABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
            print("Temporarily disabled trigger")
        except:
            pass  # Trigger might not exist
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fight_id) as populated
            FROM fight_stats
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have fight_id")

        result = conn.execute(text("""
            UPDATE fight_stats fs
            SET fight_id = fd.id
            FROM fight_details fd
            WHERE TRIM(fs."BOUT") = TRIM(fd."BOUT")
            AND TRIM(fs."EVENT") = TRIM(fd."EVENT")
            AND fs.fight_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fight_id) as populated
            FROM fight_stats
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have fight_id")

        # Re-enable trigger
        try:
            conn.execute(text("ALTER TABLE fight_stats ENABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
            print("Re-enabled trigger")
        except:
            pass

        if row[1] == row[0]:
            print("[OK] All fight_stats rows have fight_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing fight_id")
            return False


def populate_fighter_tott_fighter_id():
    """Link fighter_tott rows to fighter_details by identity, never by name alone.

    Names are not identifiers.  Seven UFCStats fighters share a name with
    another fighter, and `UPDATE ... FROM` with two matching rows resolves the
    collision arbitrarily and reports success.  That is how Michael McDonald
    (b. 1965) came to carry Michael McDonald's (b. 1991) height, reach and DOB.
    See db/migrations/007_fighter_tott_identity.sql for the repair.

    Resolution order, strongest key first:
      1. fighter_tott.id  = fighter_details.id   - the tott PK is the fighter id
      2. fighter_tott.URL = fighter_details.URL  - UFCStats identity
      3. full name, and only when that name belongs to exactly one fighter

    Ambiguous names are left NULL and reported, never guessed.  A NULL
    fighter_id is a visible gap that validation can see; a wrong one is not.
    """
    print_header("6. POPULATING fighter_tott.fighter_id")

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fighter_id) AS populated
            FROM fighter_tott
        """)).fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have fighter_id")

        # 1. Primary key match. The tott id IS the fighter id for every row
        #    loaded from UFCStats, which covers ~98% of the table.
        by_id = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = fd.id
            FROM fighter_details fd
            WHERE fd.id = ft.id
              AND ft.fighter_id IS DISTINCT FROM fd.id
        """)).rowcount
        conn.commit()
        print(f"Matched by id:   {by_id:,} rows")

        # 2. URL match. Distinct people always have distinct UFCStats URLs, so
        #    this is exact even when the names collide.
        by_url = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = fd.id
            FROM fighter_details fd
            WHERE fd."URL" = ft."URL"
              AND ft."URL" IS NOT NULL
              AND ft.fighter_id IS NULL
        """)).rowcount
        conn.commit()
        print(f"Matched by URL:  {by_url:,} rows")

        # 3. Name match, restricted to names owned by exactly one fighter.
        #    The HAVING COUNT(*) = 1 clause is what makes this safe: a shared
        #    name produces no candidate at all rather than an arbitrary one.
        by_name = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = u.id
            FROM (
                SELECT TRIM(CONCAT(fd."FIRST", ' ', fd."LAST")) AS nm, MIN(fd.id) AS id
                FROM fighter_details fd
                GROUP BY 1
                HAVING COUNT(*) = 1
            ) u
            WHERE TRIM(ft."FIGHTER") = u.nm
              AND ft.fighter_id IS NULL
        """)).rowcount
        conn.commit()
        print(f"Matched by name: {by_name:,} rows (unambiguous names only)")

        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fighter_id) AS populated
            FROM fighter_tott
        """)).fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have fighter_id")

        if row[1] == row[0]:
            print("[OK] All fighter_tott rows have fighter_id")
            return True

        # Report what was deliberately not guessed, so the gap is actionable.
        unresolved = conn.execute(text("""
            SELECT ft.id, ft."FIGHTER",
                   (SELECT COUNT(*) FROM fighter_details fd
                     WHERE TRIM(CONCAT(fd."FIRST", ' ', fd."LAST")) = TRIM(ft."FIGHTER")) AS candidates
            FROM fighter_tott ft
            WHERE ft.fighter_id IS NULL
            ORDER BY candidates DESC, ft."FIGHTER"
        """)).fetchall()

        ambiguous = [r for r in unresolved if r[2] > 1]
        unknown   = [r for r in unresolved if r[2] == 0]
        print(f"[WARN] {len(unresolved)} rows unlinked "
              f"({len(ambiguous)} ambiguous, {len(unknown)} no candidate)")
        for tid, name, n in ambiguous[:10]:
            print(f"    ambiguous: {tid} {name} -> {n} fighters share this name")
        for tid, name, _ in unknown[:10]:
            print(f"    no match : {tid} {name}")

        return False


def verify_relationships():
    """Verify all foreign key relationships are properly populated."""
    print_header("VERIFICATION")

    with engine.connect() as conn:
        # Check Petr Yan's fights with joins
        result = conn.execute(text("""
            SELECT
                fr."BOUT",
                ed."EVENT",
                ed.date_proper,
                fr."OUTCOME"
            FROM fight_results fr
            JOIN event_details ed ON fr.event_id = ed.id
            JOIN fight_details fd ON fr.fight_id = fd.id
            WHERE fr."BOUT" ILIKE '%Petr Yan%'
            AND fr."BOUT" NOT ILIKE '%Petrosyan%'
            ORDER BY ed.date_proper
            LIMIT 5
        """))

        rows = result.fetchall()

        if rows:
            print("\n[OK] Sample Petr Yan fights with foreign key joins:")
            for bout, event, date, outcome in rows:
                print(f"  - {bout} | {event} | {date} | {outcome}")
            return True
        else:
            print("[FAIL] Could not retrieve Petr Yan fights using foreign keys")
            return False


def main():
    """Run all foreign key population steps."""
    print("\n" + "="*70)
    print("  FOREIGN KEY POPULATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    results = {
        'fight_details.event_id': populate_fight_details_event_id(),
        'fight_results.event_id': populate_fight_results_event_id(),
        'fight_results.fight_id': populate_fight_results_fight_id(),
        'fight_stats.event_id': populate_fight_stats_event_id(),
        'fight_stats.fight_id': populate_fight_stats_fight_id(),
        'fighter_tott.fighter_id': populate_fighter_tott_fighter_id(),
        'verification': verify_relationships()
    }

    # Summary
    print_header("SUMMARY")

    all_passed = all(results.values())

    for key, passed in results.items():
        status = "[OK]" if passed else "[WARN]"
        print(f"{status} {key}")

    print("\n" + "="*70)
    if all_passed:
        print("  [OK] ALL FOREIGN KEYS POPULATED SUCCESSFULLY")
        print("  Database is ready for use with relational queries!")
    else:
        print("  [WARN] SOME FOREIGN KEYS MAY BE INCOMPLETE")
        print("  Check warnings above for details")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

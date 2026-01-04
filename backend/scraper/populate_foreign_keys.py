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
    """Populate fighter_tott.fighter_id from fighter_details by matching FIGHTER name."""
    print_header("6. POPULATING fighter_tott.fighter_id")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fighter_id) as populated
            FROM fighter_tott
        """))
        row = result.fetchone()
        print(f"Before: {row[1]:,} / {row[0]:,} rows have fighter_id")

        # Match by combining FIRST + LAST name
        result = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = fd.id
            FROM fighter_details fd
            WHERE TRIM(ft."FIGHTER") = TRIM(CONCAT(fd."FIRST", ' ', fd."LAST"))
            AND ft.fighter_id IS NULL
        """))
        conn.commit()

        updated = result.rowcount
        print(f"Updated: {updated:,} rows")

        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(fighter_id) as populated
            FROM fighter_tott
        """))
        row = result.fetchone()
        print(f"After: {row[1]:,} / {row[0]:,} rows have fighter_id")

        if row[1] == row[0]:
            print("[OK] All fighter_tott rows have fighter_id")
            return True
        else:
            print(f"[WARN] {row[0] - row[1]} rows still missing fighter_id")
            # Try to match remaining by LAST name only (for fighters with NULL first name)
            result = conn.execute(text("""
                UPDATE fighter_tott ft
                SET fighter_id = fd.id
                FROM fighter_details fd
                WHERE TRIM(ft."FIGHTER") = TRIM(fd."LAST")
                AND ft.fighter_id IS NULL
                AND fd."FIRST" IS NULL
            """))
            conn.commit()

            if result.rowcount > 0:
                print(f"Matched {result.rowcount} more by LAST name only (for NULL first names)")

            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(fighter_id) as populated
                FROM fighter_tott
            """))
            row = result.fetchone()
            print(f"Final: {row[1]:,} / {row[0]:,} rows have fighter_id")

            return row[1] == row[0]


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

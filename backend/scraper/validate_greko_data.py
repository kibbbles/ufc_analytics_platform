"""
Validate Greko CSV data loaded into Supabase database.

Checks:
1. Row counts match between CSV files and database tables
2. No duplicate IDs or records
3. Key fields are populated (no unexpected NULLs)
4. Spot checks on known fighters (Petr Yan, etc.)
5. Data integrity - all text relationships can be joined

Usage:
    python validate_greko_data.py
"""

import os
import sys
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, engine

# CSV file paths
CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scrape_ufc_stats')

CSV_FILES = {
    'event_details': 'ufc_event_details.csv',
    'fighter_details': 'ufc_fighter_details.csv',
    'fight_details': 'ufc_fight_details.csv',
    'fight_results': 'ufc_fight_results.csv',
    'fighter_tott': 'ufc_fighter_tott.csv',
    'fight_stats': 'ufc_fight_stats.csv'
}


def print_header(title):
    """Print section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def check_row_counts():
    """Compare CSV row counts with database table row counts."""
    print_header("1. ROW COUNT VALIDATION")

    session = SessionLocal()
    all_match = True

    try:
        for table, csv_file in CSV_FILES.items():
            csv_path = os.path.join(CSV_DIR, csv_file)

            if not os.path.exists(csv_path):
                print(f"[FAIL] {table}: CSV file not found at {csv_path}")
                all_match = False
                continue

            # Count CSV rows (excluding header)
            csv_df = pd.read_csv(csv_path)
            csv_count = len(csv_df)

            # Count database rows
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            db_count = result.scalar()

            match = "[OK]" if csv_count == db_count else "[FAIL]"
            print(f"{match} {table:20} | CSV: {csv_count:6,} | DB: {db_count:6,}")

            if csv_count != db_count:
                all_match = False
                diff = abs(csv_count - db_count)
                print(f"   > MISMATCH: Difference of {diff:,} rows")

        return all_match

    finally:
        session.close()


def check_duplicate_ids():
    """Check for duplicate IDs in each table."""
    print_header("2. DUPLICATE ID CHECK")

    session = SessionLocal()
    no_duplicates = True

    try:
        for table in CSV_FILES.keys():
            result = session.execute(text(f"""
                SELECT id, COUNT(*) as count
                FROM {table}
                GROUP BY id
                HAVING COUNT(*) > 1
            """))
            duplicates = result.fetchall()

            if duplicates:
                print(f"[FAIL] {table}: Found {len(duplicates)} duplicate IDs")
                for dup_id, count in duplicates[:5]:  # Show first 5
                    print(f"   - ID '{dup_id}' appears {count} times")
                if len(duplicates) > 5:
                    print(f"   - ... and {len(duplicates) - 5} more")
                no_duplicates = False
            else:
                print(f"[OK] {table}: No duplicate IDs")

        return no_duplicates

    finally:
        session.close()


def check_null_fields():
    """Check for unexpected NULL values in key fields."""
    print_header("3. NULL VALUE CHECK")

    session = SessionLocal()
    no_issues = True

    try:
        # Define critical fields that should not be NULL
        checks = {
            'event_details': ['"EVENT"', '"URL"'],
            'fighter_details': ['"FIRST"', '"LAST"', '"URL"'],
            'fight_details': ['"EVENT"', '"BOUT"', '"URL"'],
            'fight_results': ['"EVENT"', '"BOUT"', '"OUTCOME"', '"URL"'],
            'fighter_tott': ['"FIGHTER"', '"URL"'],
            'fight_stats': ['"EVENT"', '"BOUT"', '"FIGHTER"', '"ROUND"']
        }

        for table, fields in checks.items():
            for field in fields:
                result = session.execute(text(f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE {field} IS NULL
                """))
                null_count = result.scalar()

                if null_count > 0:
                    print(f"[FAIL] {table}.{field}: {null_count:,} NULL values")
                    no_issues = False

        if no_issues:
            print("[OK] No unexpected NULL values in critical fields")

        return no_issues

    finally:
        session.close()


def spot_check_fighters():
    """Spot check known fighters to verify data accuracy."""
    print_header("4. SPOT CHECK - KNOWN FIGHTERS")

    session = SessionLocal()
    all_correct = True

    try:
        # Test Case 1: Petr Yan (should have 16 UFC fights, 12 wins, 4 losses)
        print("\n>> Petr Yan Verification:")

        result = session.execute(text("""
            SELECT COUNT(*) as total_fights,
                   SUM(CASE
                       WHEN ("BOUT" ILIKE 'Petr Yan%' AND "OUTCOME" LIKE 'W/%') OR
                            ("BOUT" ILIKE '%vs. Petr Yan' AND "OUTCOME" LIKE '%/W') OR
                            ("BOUT" ILIKE 'Yan vs.%' AND "OUTCOME" LIKE 'W/%') OR
                            ("BOUT" ILIKE '%vs. Yan' AND "OUTCOME" LIKE '%/W')
                       THEN 1 ELSE 0 END) as wins
            FROM fight_results
            WHERE ("BOUT" ILIKE '%Petr Yan%'
                   OR "BOUT" ILIKE '% Yan vs.%'
                   OR "BOUT" ILIKE '%vs. Yan')
            AND "BOUT" NOT ILIKE '%Petrosyan%'
        """))

        petr_data = result.fetchone()
        fights = petr_data[0]
        wins = petr_data[1]
        losses = fights - wins

        print(f"   Total UFC Fights: {fights} (Expected: 16)")
        print(f"   Wins: {wins} (Expected: 12)")
        print(f"   Losses: {losses} (Expected: 4)")

        if fights == 16 and wins == 12:
            print("   [OK] Petr Yan data is correct")
        else:
            print("   [FAIL] Petr Yan data does not match expected values")
            all_correct = False

        # Test Case 2: Check for a recent event
        print("\n>> Recent Event Check (UFC 310):")
        result = session.execute(text("""
            SELECT "EVENT", date_proper, "LOCATION"
            FROM event_details
            WHERE "EVENT" ILIKE '%UFC 310%'
            LIMIT 1
        """))
        event = result.fetchone()

        if event:
            print(f"   Event: {event[0]}")
            print(f"   Date: {event[1]}")
            print(f"   Location: {event[2]}")
            print("   [OK] Recent event found")
        else:
            print("   [WARN] UFC 310 not found (may not be in dataset yet)")

        return all_correct

    finally:
        session.close()


def check_text_relationships():
    """Verify that text-based relationships can be joined properly."""
    print_header("5. TEXT RELATIONSHIP INTEGRITY")

    session = SessionLocal()
    all_valid = True

    try:
        # Check 1: All fight_results events exist in event_details
        print("\n>> Checking fight_results -> event_details:")
        result = session.execute(text("""
            SELECT COUNT(DISTINCT fr."EVENT") as total_events,
                   COUNT(DISTINCT CASE WHEN ed."EVENT" IS NULL THEN fr."EVENT" END) as orphaned_events
            FROM fight_results fr
            LEFT JOIN event_details ed ON fr."EVENT" = ed."EVENT"
        """))
        row = result.fetchone()

        if row[1] > 0:
            print(f"   [FAIL] Found {row[1]} events in fight_results not in event_details")
            all_valid = False
        else:
            print(f"   [OK] All {row[0]} events found in event_details")

        # Check 2: All fight_results bouts exist in fight_details
        print("\n>> Checking fight_results -> fight_details:")
        result = session.execute(text("""
            SELECT COUNT(*) as total_results,
                   COUNT(CASE WHEN fd."BOUT" IS NULL THEN 1 END) as orphaned_results
            FROM fight_results fr
            LEFT JOIN fight_details fd
              ON fr."BOUT" = fd."BOUT"
              AND fr."EVENT" = fd."EVENT"
        """))
        row = result.fetchone()

        if row[1] > 0:
            print(f"   [FAIL] Found {row[1]} fight results without matching fight_details")
            all_valid = False
        else:
            print(f"   [OK] All {row[0]} fight results have matching fight_details")

        # Check 3: All fight_stats bouts exist in fight_details
        print("\n>> Checking fight_stats -> fight_details:")
        result = session.execute(text("""
            SELECT COUNT(DISTINCT fs."EVENT" || '|' || fs."BOUT") as total_unique_fights,
                   COUNT(DISTINCT CASE
                       WHEN fd."BOUT" IS NULL
                       THEN fs."EVENT" || '|' || fs."BOUT"
                   END) as orphaned_stats
            FROM fight_stats fs
            LEFT JOIN fight_details fd
              ON fs."BOUT" = fd."BOUT"
              AND fs."EVENT" = fd."EVENT"
        """))
        row = result.fetchone()

        if row[1] and row[1] > 0:
            print(f"   [FAIL] Found {row[1]} fights in fight_stats not in fight_details")
            all_valid = False
        else:
            print(f"   [OK] All {row[0]} fights in fight_stats have matching fight_details")

        return all_valid

    finally:
        session.close()


def check_duplicate_records():
    """Check for duplicate records (same data, different IDs)."""
    print_header("6. DUPLICATE RECORD CHECK")

    session = SessionLocal()
    no_duplicates = True

    try:
        # Check for duplicate events (same EVENT name, different IDs)
        print("\n>> Checking duplicate events:")
        result = session.execute(text("""
            SELECT "EVENT", COUNT(*) as count
            FROM event_details
            GROUP BY "EVENT"
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()

        if duplicates:
            print(f"   [FAIL] Found {len(duplicates)} duplicate event names:")
            for event_name, count in duplicates[:5]:
                print(f"      '{event_name}' appears {count} times")
            no_duplicates = False
        else:
            print("   [OK] No duplicate event names")

        # Check for duplicate fights (same BOUT + EVENT, different IDs)
        print("\n>> Checking duplicate fights:")
        result = session.execute(text("""
            SELECT "EVENT", "BOUT", COUNT(*) as count
            FROM fight_details
            GROUP BY "EVENT", "BOUT"
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()

        if duplicates:
            print(f"   [FAIL] Found {len(duplicates)} duplicate fight records")
            no_duplicates = False
        else:
            print("   [OK] No duplicate fight records")

        # Check for duplicate fight results
        print("\n>> Checking duplicate fight results:")
        result = session.execute(text("""
            SELECT "EVENT", "BOUT", COUNT(*) as count
            FROM fight_results
            GROUP BY "EVENT", "BOUT"
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()

        if duplicates:
            print(f"   [FAIL] Found {len(duplicates)} duplicate fight result records:")
            # Show a few examples
            for event, bout, count in duplicates[:3]:
                print(f"      {event} | {bout} ({count} times)")
            if len(duplicates) > 3:
                print(f"      ... and {len(duplicates) - 3} more")
            no_duplicates = False
        else:
            print("   [OK] No duplicate fight result records")

        return no_duplicates

    finally:
        session.close()


def main():
    """Run all validation checks."""
    print("\n" + "="*70)
    print("  GREKO DATA VALIDATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    results = {
        'row_counts': check_row_counts(),
        'duplicate_ids': check_duplicate_ids(),
        'null_fields': check_null_fields(),
        'spot_checks': spot_check_fighters(),
        'text_relationships': check_text_relationships(),
        'duplicate_records': check_duplicate_records()
    }

    # Final summary
    print_header("VALIDATION SUMMARY")

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {check.replace('_', ' ').title()}")

    print("\n" + "="*70)
    if all_passed:
        print("  [PASS] ALL VALIDATION CHECKS PASSED")
        print("  Data is ready for foreign key population!")
    else:
        print("  [FAIL] SOME VALIDATION CHECKS FAILED")
        print("  Please review issues above before proceeding")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

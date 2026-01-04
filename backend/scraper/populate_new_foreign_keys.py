"""
Populate foreign keys for newly scraped data.

This script only updates rows where foreign keys are NULL,
making it safe and fast to run after weekly scraping.

Used by GitHub Actions weekly-ufc-scraper.yml workflow.

Usage:
    python populate_new_foreign_keys.py
"""

import sys
import os
from sqlalchemy import text
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine


def populate_foreign_keys():
    """Populate all foreign key relationships for rows with NULL values."""

    print("\n" + "="*70)
    print("  POPULATING NEW FOREIGN KEYS")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    stats = {
        'fight_details.event_id': 0,
        'fight_results.event_id': 0,
        'fight_results.fight_id': 0,
        'fight_stats.event_id': 0,
        'fight_stats.fight_id': 0,
        'fighter_tott.fighter_id': 0
    }

    with engine.connect() as conn:

        # 1. fight_details.event_id
        print("\n[1/6] Populating fight_details.event_id...")
        result = conn.execute(text("""
            UPDATE fight_details fd
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fd."EVENT") = TRIM(ed."EVENT")
            AND fd.event_id IS NULL
        """))
        conn.commit()
        stats['fight_details.event_id'] = result.rowcount
        print(f"      Updated {result.rowcount} rows")

        # 2. fight_results.event_id
        print("\n[2/6] Populating fight_results.event_id...")
        result = conn.execute(text("""
            UPDATE fight_results fr
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fr."EVENT") = TRIM(ed."EVENT")
            AND fr.event_id IS NULL
        """))
        conn.commit()
        stats['fight_results.event_id'] = result.rowcount
        print(f"      Updated {result.rowcount} rows")

        # 3. fight_results.fight_id
        print("\n[3/6] Populating fight_results.fight_id...")
        result = conn.execute(text("""
            UPDATE fight_results fr
            SET fight_id = fd.id
            FROM fight_details fd
            WHERE TRIM(fr."BOUT") = TRIM(fd."BOUT")
            AND TRIM(fr."EVENT") = TRIM(fd."EVENT")
            AND fr.fight_id IS NULL
        """))
        conn.commit()
        stats['fight_results.fight_id'] = result.rowcount
        print(f"      Updated {result.rowcount} rows")

        # 4. fight_stats.event_id (disable trigger temporarily)
        print("\n[4/6] Populating fight_stats.event_id...")
        try:
            conn.execute(text("ALTER TABLE fight_stats DISABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
        except:
            pass  # Trigger might not exist or already disabled

        result = conn.execute(text("""
            UPDATE fight_stats fs
            SET event_id = ed.id
            FROM event_details ed
            WHERE TRIM(fs."EVENT") = TRIM(ed."EVENT")
            AND fs.event_id IS NULL
        """))
        conn.commit()
        stats['fight_stats.event_id'] = result.rowcount
        print(f"      Updated {result.rowcount} rows")

        try:
            conn.execute(text("ALTER TABLE fight_stats ENABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
        except:
            pass

        # 5. fight_stats.fight_id (disable trigger temporarily)
        print("\n[5/6] Populating fight_stats.fight_id...")
        try:
            conn.execute(text("ALTER TABLE fight_stats DISABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
        except:
            pass

        result = conn.execute(text("""
            UPDATE fight_stats fs
            SET fight_id = fd.id
            FROM fight_details fd
            WHERE TRIM(fs."BOUT") = TRIM(fd."BOUT")
            AND TRIM(fs."EVENT") = TRIM(fd."EVENT")
            AND fs.fight_id IS NULL
        """))
        conn.commit()
        stats['fight_stats.fight_id'] = result.rowcount
        print(f"      Updated {result.rowcount} rows")

        try:
            conn.execute(text("ALTER TABLE fight_stats ENABLE TRIGGER update_fight_stats_updated_at"))
            conn.commit()
        except:
            pass

        # 6. fighter_tott.fighter_id
        print("\n[6/6] Populating fighter_tott.fighter_id...")

        # First try full name match
        result = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = fd.id
            FROM fighter_details fd
            WHERE TRIM(ft."FIGHTER") = TRIM(CONCAT(fd."FIRST", ' ', fd."LAST"))
            AND ft.fighter_id IS NULL
        """))
        conn.commit()
        count1 = result.rowcount

        # Then try last name only (for fighters with NULL first name)
        result = conn.execute(text("""
            UPDATE fighter_tott ft
            SET fighter_id = fd.id
            FROM fighter_details fd
            WHERE TRIM(ft."FIGHTER") = TRIM(fd."LAST")
            AND ft.fighter_id IS NULL
            AND fd."FIRST" IS NULL
        """))
        conn.commit()
        count2 = result.rowcount

        stats['fighter_tott.fighter_id'] = count1 + count2
        print(f"      Updated {count1 + count2} rows ({count1} full name, {count2} last name only)")

    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70)

    total_updated = sum(stats.values())

    for key, count in stats.items():
        if count > 0:
            print(f"[OK] {key}: {count} rows updated")
        else:
            print(f"[--] {key}: no updates needed")

    print("\n" + "="*70)
    if total_updated > 0:
        print(f"  [OK] Updated {total_updated} foreign key relationships")
    else:
        print("  [OK] All foreign keys already populated")
    print("="*70 + "\n")

    return True


def main():
    """Main execution."""
    try:
        success = populate_foreign_keys()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Foreign key population failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

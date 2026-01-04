"""
Load Greko's UFC Stats CSVs into Supabase database.

This script:
1. Clears existing data from all tables (in correct order to avoid FK violations)
2. Loads latest CSVs from scrape_ufc_stats directory
3. Verifies data integrity after load

Usage:
    python load_greko_csvs.py
"""

import os
import sys
import pandas as pd
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine, SessionLocal

# CSV file paths (relative to scrape_ufc_stats directory)
CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scrape_ufc_stats')

CSV_FILES = {
    'event_details': 'ufc_event_details.csv',
    'fighter_details': 'ufc_fighter_details.csv',
    'fight_details': 'ufc_fight_details.csv',
    'fight_results': 'ufc_fight_results.csv',
    'fighter_tott': 'ufc_fighter_tott.csv',
    'fight_stats': 'ufc_fight_stats.csv'
}

def clear_database():
    """Clear all tables in correct order to avoid foreign key violations."""
    print("\n" + "="*60)
    print("CLEARING DATABASE")
    print("="*60)

    session = SessionLocal()
    try:
        # Delete in reverse dependency order
        tables = ['fight_stats', 'fight_results', 'fighter_tott', 'fight_details', 'fighter_details', 'event_details']

        for table in tables:
            result = session.execute(text(f"DELETE FROM {table}"))
            session.commit()
            print(f"[OK] Cleared {table} ({result.rowcount} rows deleted)")

        print("[OK] Database cleared successfully")

    except Exception as e:
        print(f"[ERROR] Error clearing database: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def extract_id_from_url(url):
    """Extract ID from UFCStats URL (first 8 characters)."""
    if pd.isna(url) or not url:
        return None
    full_id = url.split('/')[-1]
    return full_id[:8] if full_id else None

def load_csv_to_table(table_name, csv_filename):
    """Load a CSV file into a database table."""
    csv_path = os.path.join(CSV_DIR, csv_filename)

    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"\n{table_name}:")
        print(f"  Reading CSV: {csv_filename}")
        print(f"  Rows in CSV: {len(df)}")

        # Extract ID from URL for tables that need it
        if 'URL' in df.columns and table_name in ['event_details', 'fighter_details', 'fight_details', 'fight_results', 'fighter_tott']:
            df['id'] = df['URL'].apply(extract_id_from_url)
            # Reorder columns to put id first
            cols = ['id'] + [col for col in df.columns if col != 'id']
            df = df[cols]
            print(f"  Extracted IDs from URLs")
        elif table_name == 'fight_stats':
            # fight_stats doesn't have URL column, generate sequential IDs
            import hashlib
            def generate_stat_id(idx, row):
                # Create hash from EVENT + BOUT + ROUND + FIGHTER + INDEX to ensure uniqueness
                unique_str = f"{row['EVENT']}-{row['BOUT']}-{row['ROUND']}-{row['FIGHTER']}-{idx}"
                hash_obj = hashlib.md5(unique_str.encode())
                return hash_obj.hexdigest()[:8]

            df['id'] = [generate_stat_id(i, row) for i, row in df.iterrows()]
            # Reorder columns to put id first
            cols = ['id'] + [col for col in df.columns if col != 'id']
            df = df[cols]
            print(f"  Generated IDs from hash of EVENT+BOUT+ROUND+FIGHTER+INDEX")

        # Load to database using pandas to_sql
        # if_exists='append' since we already cleared the table
        df.to_sql(table_name, engine, if_exists='append', index=False, method='multi', chunksize=1000)

        # Verify rows were inserted
        session = SessionLocal()
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  Rows in DB: {count}")

            if count == len(df):
                print(f"  [OK] Successfully loaded {table_name}")
                return True
            else:
                print(f"  [ERROR] Row count mismatch! CSV: {len(df)}, DB: {count}")
                return False
        finally:
            session.close()

    except Exception as e:
        print(f"  [ERROR] Error loading {table_name}: {e}")
        return False

def verify_petr_yan():
    """Verify Petr Yan has 16 UFC fights."""
    print("\n" + "="*60)
    print("VERIFICATION: PETR YAN")
    print("="*60)

    session = SessionLocal()
    try:
        # Get Petr Yan's fighter ID
        result = session.execute(text("""
            SELECT id, "FIRST", "LAST"
            FROM fighter_details
            WHERE "FIRST" = 'Petr' AND "LAST" = 'Yan'
        """))
        fighter = result.fetchone()

        if not fighter:
            print("[ERROR] Petr Yan not found in fighter_details")
            return False

        fighter_id = fighter[0]
        print(f"Fighter ID: {fighter_id}")
        print(f"Name: {fighter[1]} {fighter[2]}")

        # Count fights in fight_results
        result = session.execute(text("""
            SELECT COUNT(*)
            FROM fight_results
            WHERE "BOUT" LIKE '%Petr Yan%'
        """))
        fight_count = result.scalar()

        print(f"UFC Fights: {fight_count}")

        if fight_count == 16:
            print("[OK] Petr Yan has correct number of UFC fights (16)")
            return True
        else:
            print(f"[ERROR] Expected 16 fights, found {fight_count}")
            return False

    except Exception as e:
        print(f"[ERROR] Error verifying Petr Yan: {e}")
        return False
    finally:
        session.close()

def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("LOADING GREKO CSVs TO SUPABASE")
    print("="*60)
    print(f"CSV Directory: {CSV_DIR}")

    # Verify CSV directory exists
    if not os.path.exists(CSV_DIR):
        print(f"\n[ERROR] CSV directory not found: {CSV_DIR}")
        return

    # Step 1: Clear database
    clear_database()

    # Step 2: Load CSVs in correct order (respecting foreign keys)
    print("\n" + "="*60)
    print("LOADING CSVs")
    print("="*60)

    load_order = [
        'event_details',
        'fighter_details',
        'fight_details',
        'fight_results',
        'fighter_tott',
        'fight_stats'
    ]

    success = True
    for table in load_order:
        if not load_csv_to_table(table, CSV_FILES[table]):
            success = False
            break

    if not success:
        print("\n[ERROR] CSV loading failed")
        return

    # Step 3: Verify Petr Yan data
    verify_petr_yan()

    # Step 4: Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    session = SessionLocal()
    try:
        for table in load_order:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"{table}: {count:,} rows")
    finally:
        session.close()

    print("\n[OK] Database successfully loaded with Greko CSVs!")

if __name__ == "__main__":
    main()

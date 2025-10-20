"""
Daily Supabase Keepalive Ping
Prevents Supabase free tier from auto-pausing after 7 days of inactivity
Run this script at least once every 7 days (recommended: daily)
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from sqlalchemy import text
    from db.database import engine

    print(f"\n{'='*60}")
    print(f"Supabase Keepalive Ping - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    with engine.connect() as conn:
        # Lightweight query - just checks database is alive
        result = conn.execute(text("SELECT COUNT(*) FROM event_details"))
        count = result.scalar()

        print(f"[SUCCESS] Database connection active")
        print(f"[SUCCESS] Database contains {count} UFC events")
        print(f"[SUCCESS] Supabase project will remain active\n")

        # Log to file for monitoring
        log_file = os.path.join(os.path.dirname(__file__), 'keepalive.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - SUCCESS - {count} events\n")

        exit(0)

except Exception as e:
    print(f"[ERROR] Keepalive ping failed!")
    print(f"[ERROR] Error details: {e}\n")
    print(f"[WARNING] Database may pause if not resolved!\n")

    # Log error
    log_file = os.path.join(os.path.dirname(__file__), 'keepalive.log')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - FAILED - {str(e)}\n")
    except:
        pass

    exit(1)

"""
Keep Supabase database active to prevent 7-day pause
Run this weekly or add to your scheduler
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine
from sqlalchemy import text

def keep_database_active():
    """Run a simple query to keep database active"""
    try:
        with engine.connect() as conn:
            # Simple query to keep connection active
            result = conn.execute(text("SELECT COUNT(*) FROM event_details"))
            count = result.scalar()

            # Log activity
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Database keep-alive: {count:,} events found")

            return True
    except Exception as e:
        print(f"Keep-alive failed: {e}")
        return False

if __name__ == "__main__":
    load_dotenv()
    keep_database_active()
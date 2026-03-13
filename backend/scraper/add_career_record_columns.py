"""
One-time migration: add career_wins, career_losses, career_draws to fighter_tott.

Run once from the backend/scraper directory:
    python add_career_record_columns.py
"""

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE fighter_tott ADD COLUMN IF NOT EXISTS career_wins INTEGER'))
    conn.execute(text('ALTER TABLE fighter_tott ADD COLUMN IF NOT EXISTS career_losses INTEGER'))
    conn.execute(text('ALTER TABLE fighter_tott ADD COLUMN IF NOT EXISTS career_draws INTEGER'))
    conn.commit()

    total = conn.execute(text('SELECT COUNT(*) FROM fighter_tott')).scalar()
    populated = conn.execute(text('SELECT COUNT(*) FROM fighter_tott WHERE career_wins IS NOT NULL')).scalar()
    print(f"Migration complete. {populated}/{total} rows already have career_wins set.")

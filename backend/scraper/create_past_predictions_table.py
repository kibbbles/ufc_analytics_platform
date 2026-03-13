"""create_past_predictions_table.py — One-time migration to create past_predictions table.

Usage:
    cd backend && python scraper/create_past_predictions_table.py
"""

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from db.database import engine


def create_table() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS past_predictions (
                id                  VARCHAR(8)    PRIMARY KEY,
                fight_id            VARCHAR(8)    REFERENCES fight_details(id),
                event_id            VARCHAR(8),
                event_name          TEXT,
                event_date          DATE,
                fighter_a_id        VARCHAR(8),
                fighter_b_id        VARCHAR(8),
                fighter_a_name      TEXT,
                fighter_b_name      TEXT,
                weight_class        TEXT,
                model_version       TEXT          DEFAULT 'win_loss_v1',
                win_prob_a          FLOAT,
                win_prob_b          FLOAT,
                pred_method_ko_tko  FLOAT,
                pred_method_sub     FLOAT,
                pred_method_dec     FLOAT,
                predicted_winner_id VARCHAR(8),
                predicted_method    TEXT,
                actual_winner_id    VARCHAR(8),
                actual_method       TEXT,
                is_correct          BOOLEAN,
                confidence          FLOAT,
                is_upset            BOOLEAN,
                computed_at         TIMESTAMPTZ   DEFAULT now()
            )
        """))

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS past_predictions_fight_id_idx
            ON past_predictions(fight_id)
        """))

    print("Table 'past_predictions' and unique index on fight_id created (or already existed).")


if __name__ == "__main__":
    create_table()

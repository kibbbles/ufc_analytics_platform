"""archive_completed_predictions.py — Freeze pre-fight predictions before retrain.

Copies upcoming_predictions rows into past_predictions (prediction_source =
'pre_fight_archive') for any upcoming_fight whose event has already occurred
AND whose fighters now appear in a completed fight_details row.

Run this AFTER the weekly scraper ingests new completed fight data but BEFORE
the feature-engineering pipeline rebuilds training_data.parquet.  That ordering
guarantees the archived features_json snapshot is free of look-ahead bias.

Usage:
    cd backend && python scraper/archive_completed_predictions.py
    cd backend && python scraper/archive_completed_predictions.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import string
import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from sqlalchemy import text

from db.database import engine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ID generation (same pattern as compute_past_predictions.py)
# ---------------------------------------------------------------------------

def _load_existing_ids() -> set:
    existing: set = set()
    tables = [
        "event_details", "fighter_details", "fight_details",
        "fight_results", "fight_stats", "fighter_tott",
        "upcoming_events", "upcoming_fights", "upcoming_predictions",
        "past_predictions",
    ]
    with engine.connect() as conn:
        for table in tables:
            try:
                for row in conn.execute(text(f"SELECT id FROM {table}")):
                    existing.add(row[0])
            except Exception:
                continue
    return existing


def _new_id(existing_ids: set) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(random.choices(chars, k=8))
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            return candidate


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> None:
    # ------------------------------------------------------------------
    # 1. Find upcoming fights whose event has passed and that have a
    #    prediction, matched bidirectionally against completed fight_details.
    # ------------------------------------------------------------------
    logger.info("Querying completed upcoming fights with predictions...")

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                uf.id                AS upcoming_fight_id,
                uf.fighter_a_id,
                uf.fighter_b_id,
                uf.fighter_a_name,
                uf.fighter_b_name,
                uf.weight_class      AS uf_weight_class,
                up.win_prob_a,
                up.win_prob_b,
                up.method_ko_tko     AS pred_method_ko_tko,
                up.method_sub        AS pred_method_sub,
                up.method_dec        AS pred_method_dec,
                up.model_version,
                up.features_json,
                up.predicted_at      AS pre_fight_predicted_at,
                fd.id                AS fight_id,
                fd.event_id,
                e."EVENT"            AS event_name,
                e.date_proper        AS event_date,
                fr."METHOD"          AS actual_method,
                fr.fighter_id        AS actual_winner_id,
                fr.weight_class      AS fr_weight_class
            FROM upcoming_fights uf
            JOIN upcoming_events ue ON ue.id = uf.event_id
            JOIN upcoming_predictions up ON up.fight_id = uf.id
            -- Match against completed fights, either fighter order
            JOIN fight_details fd ON (
                (fd.fighter_a_id = uf.fighter_a_id AND fd.fighter_b_id = uf.fighter_b_id)
                OR
                (fd.fighter_a_id = uf.fighter_b_id AND fd.fighter_b_id = uf.fighter_a_id)
            )
            JOIN event_details e ON e.id = fd.event_id
            LEFT JOIN fight_results fr ON fr.fight_id = fd.id
            WHERE ue.date_proper < CURRENT_DATE
              AND uf.fighter_a_id IS NOT NULL
              AND uf.fighter_b_id IS NOT NULL
              AND (uf.archived IS NULL OR uf.archived = FALSE)
        """)).mappings().all()

    if not rows:
        logger.info("No completed upcoming fights found to archive.")
        return

    logger.info("Found %d fight(s) eligible for archiving.", len(rows))

    existing_ids = _load_existing_ids()
    archived_count = 0
    skipped_count  = 0

    for r in rows:
        fight_id         = r["fight_id"]
        upcoming_id      = r["upcoming_fight_id"]
        fighter_a_id     = r["fighter_a_id"]
        fighter_b_id     = r["fighter_b_id"]
        win_prob_a       = r["win_prob_a"]
        win_prob_b       = r["win_prob_b"]
        actual_winner_id = r["actual_winner_id"]

        # ------------------------------------------------------------------
        # 2. Idempotency: skip if already archived for this fight
        # ------------------------------------------------------------------
        with engine.connect() as conn:
            exists = conn.execute(text("""
                SELECT 1 FROM past_predictions
                WHERE fight_id = :fight_id
                  AND prediction_source = 'pre_fight_archive'
                LIMIT 1
            """), {"fight_id": fight_id}).first()

        if exists:
            logger.info("Fight %s already archived — skipping.", fight_id)
            skipped_count += 1
            continue

        # ------------------------------------------------------------------
        # 3. Derive correctness metrics
        # ------------------------------------------------------------------
        predicted_winner_id = fighter_a_id if (win_prob_a or 0) >= 0.5 else fighter_b_id
        is_correct          = (predicted_winner_id == actual_winner_id) if actual_winner_id else None
        confidence          = max(win_prob_a or 0, win_prob_b or 0)
        is_upset            = (not is_correct) and (confidence >= 0.65) if is_correct is not None else None

        methods = {
            "KO/TKO":     r["pred_method_ko_tko"] or 0,
            "Submission": r["pred_method_sub"]     or 0,
            "Decision":   r["pred_method_dec"]     or 0,
        }
        predicted_method = max(methods, key=methods.get)

        weight_class = r["fr_weight_class"] or r["uf_weight_class"]

        archive_row = {
            "id":                    _new_id(existing_ids),
            "fight_id":              fight_id,
            "event_id":              r["event_id"],
            "event_name":            r["event_name"],
            "event_date":            r["event_date"],
            "fighter_a_id":          fighter_a_id,
            "fighter_b_id":          fighter_b_id,
            "fighter_a_name":        r["fighter_a_name"],
            "fighter_b_name":        r["fighter_b_name"],
            "weight_class":          weight_class,
            "model_version":         r["model_version"],
            "win_prob_a":            win_prob_a,
            "win_prob_b":            win_prob_b,
            "pred_method_ko_tko":    r["pred_method_ko_tko"],
            "pred_method_sub":       r["pred_method_sub"],
            "pred_method_dec":       r["pred_method_dec"],
            "predicted_winner_id":   predicted_winner_id,
            "predicted_method":      predicted_method,
            "actual_winner_id":      actual_winner_id,
            "actual_method":         r["actual_method"],
            "is_correct":            is_correct,
            "confidence":            confidence,
            "is_upset":              is_upset,
            "prediction_source":     "pre_fight_archive",
            "pre_fight_predicted_at": r["pre_fight_predicted_at"],
            "features_json":         r["features_json"],
        }

        if dry_run:
            logger.info(
                "[DRY RUN] Would archive fight %s (upcoming_fight=%s, correct=%s)",
                fight_id, upcoming_id, is_correct,
            )
            archived_count += 1
            continue

        # ------------------------------------------------------------------
        # 4. Insert into past_predictions + soft-delete upcoming_fight
        # ------------------------------------------------------------------
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO past_predictions (
                    id, fight_id, event_id, event_name, event_date,
                    fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
                    weight_class, model_version,
                    win_prob_a, win_prob_b,
                    pred_method_ko_tko, pred_method_sub, pred_method_dec,
                    predicted_winner_id, predicted_method,
                    actual_winner_id, actual_method,
                    is_correct, confidence, is_upset,
                    prediction_source, pre_fight_predicted_at, features_json
                ) VALUES (
                    :id, :fight_id, :event_id, :event_name, :event_date,
                    :fighter_a_id, :fighter_b_id, :fighter_a_name, :fighter_b_name,
                    :weight_class, :model_version,
                    :win_prob_a, :win_prob_b,
                    :pred_method_ko_tko, :pred_method_sub, :pred_method_dec,
                    :predicted_winner_id, :predicted_method,
                    :actual_winner_id, :actual_method,
                    :is_correct, :confidence, :is_upset,
                    :prediction_source, :pre_fight_predicted_at, :features_json
                )
                ON CONFLICT (fight_id, prediction_source) DO NOTHING
            """), archive_row)

            conn.execute(text("""
                UPDATE upcoming_fights SET archived = TRUE WHERE id = :id
            """), {"id": upcoming_id})

        logger.info(
            "Archived fight %s (upcoming_fight=%s, correct=%s)",
            fight_id, upcoming_id, is_correct,
        )
        archived_count += 1

    suffix = " [DRY RUN]" if dry_run else ""
    logger.info(
        "Archive complete%s: %d archived, %d skipped (already done).",
        suffix, archived_count, skipped_count,
    )
    print(
        f"\n=== Prediction Archive Complete{suffix} ===\n"
        f"  Archived : {archived_count}\n"
        f"  Skipped  : {skipped_count} (already archived)\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Archive pre-fight predictions from upcoming_predictions into past_predictions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be archived without writing to DB",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)

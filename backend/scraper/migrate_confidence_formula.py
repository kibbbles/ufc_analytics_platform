"""migrate_confidence_formula.py — Recompute confidence in past_predictions.

Old formula: confidence = max(win_prob_a, win_prob_b)
             This is just the predicted winner's win probability — redundant with
             the win_prob columns and not a meaningful confidence signal.

New formula: confidence = (max(win_prob_a, win_prob_b) - 0.5) * 2
             This is the model's distance from a coin flip, normalized to [0, 1].
             A 70/30 prediction yields confidence = 0.40 (40%), not 0.70.
             Consistent with the live predictor (predictor.py line ~72).

Also recomputes is_upset, which depends on confidence >= 0.65.
With the new formula, >= 0.65 confidence means the model predicted
someone with >= 82.5% win probability.

Usage:
    cd backend && python scraper/migrate_confidence_formula.py
    cd backend && python scraper/migrate_confidence_formula.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from db.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    # ── Preview ──────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        total = conn.execute(text("""
            SELECT COUNT(*) FROM past_predictions
            WHERE win_prob_a IS NOT NULL AND win_prob_b IS NOT NULL
        """)).scalar() or 0

        sample = conn.execute(text("""
            SELECT fight_id, fighter_a_name, fighter_b_name,
                   win_prob_a, win_prob_b,
                   confidence AS old_confidence,
                   (GREATEST(win_prob_a, win_prob_b) - 0.5) * 2 AS new_confidence,
                   is_correct, is_upset
            FROM past_predictions
            WHERE win_prob_a IS NOT NULL AND win_prob_b IS NOT NULL
            ORDER BY confidence DESC
            LIMIT 10
        """)).mappings().all()

        upset_old = conn.execute(text("""
            SELECT COUNT(*) FROM past_predictions WHERE is_upset = TRUE
        """)).scalar() or 0

        upset_new = conn.execute(text("""
            SELECT COUNT(*) FROM past_predictions
            WHERE is_correct = FALSE
              AND (GREATEST(win_prob_a, win_prob_b) - 0.5) * 2 >= 0.65
              AND is_correct IS NOT NULL
        """)).scalar() or 0

    logger.info("Rows to update: %d", total)
    logger.info("is_upset rows currently: %d  →  after migration: %d", upset_old, upset_new)
    logger.info("")
    logger.info("%-20s  %-15s  old_conf  new_conf", "Fight", "Fighters")
    for r in sample:
        fighters = f"{r['fighter_a_name'] or '?'} vs {r['fighter_b_name'] or '?'}"
        logger.info(
            "%-20s  %-30s  %.3f  →  %.3f",
            r["fight_id"], fighters[:30],
            float(r["old_confidence"] or 0),
            float(r["new_confidence"] or 0),
        )

    if dry_run:
        logger.info("\n[DRY RUN] No changes written.")
        print(f"\n=== Dry run complete ===\n  Would update {total} rows\n  is_upset: {upset_old} → {upset_new}\n")
        return

    # ── Apply ────────────────────────────────────────────────────────────────
    with engine.begin() as conn:
        # Step 1: recompute confidence
        updated = conn.execute(text("""
            UPDATE past_predictions
            SET confidence = (GREATEST(win_prob_a, win_prob_b) - 0.5) * 2
            WHERE win_prob_a IS NOT NULL AND win_prob_b IS NOT NULL
        """)).rowcount

        # Step 2: recompute is_upset using new confidence values
        conn.execute(text("""
            UPDATE past_predictions
            SET is_upset = (is_correct = FALSE AND confidence >= 0.65)
            WHERE is_correct IS NOT NULL AND confidence IS NOT NULL
        """))

    logger.info("\nMigration complete: %d rows updated.", updated)
    print(f"\n=== Migration complete ===\n  Updated: {updated} rows\n  is_upset: {upset_old} → {upset_new}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recompute confidence in past_predictions to use |prob - 0.5| * 2 formula"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)

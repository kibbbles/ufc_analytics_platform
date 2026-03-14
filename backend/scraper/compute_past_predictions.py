"""compute_past_predictions.py — Backfill past_predictions table from training parquet.

Loads the pre-computed training_data.parquet, filters to test period (>= date_from),
runs inference for each fight, then upserts results into past_predictions.

Usage:
    cd backend && python scraper/compute_past_predictions.py
    cd backend && python scraper/compute_past_predictions.py --date-from 2022-01-01
"""

import sys
import os
import json
import math
import random
import string
import argparse
import logging
from pathlib import Path
from datetime import date

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

import pandas as pd
from sqlalchemy import text

from db.database import engine
from ml.loader import ModelStore
from ml.predictor import predict

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PARQUET_PATH = Path(__file__).parent.parent / 'features' / 'training_data.parquet'
SEL_PATH     = Path(__file__).parent.parent / 'features' / 'selected_features.json'

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _load_existing_ids() -> set:
    existing = set()
    tables = [
        'event_details', 'fighter_details', 'fight_details',
        'fight_results', 'fight_stats', 'fighter_tott',
        'upcoming_events', 'upcoming_fights', 'upcoming_predictions',
        'past_predictions',
    ]
    with engine.connect() as conn:
        for table in tables:
            try:
                for row in conn.execute(text(f'SELECT id FROM {table}')):
                    existing.add(row[0])
            except Exception:
                continue
    return existing


def _new_id(existing_ids: set) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        candidate = ''.join(random.choices(chars, k=8))
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            return candidate


# ---------------------------------------------------------------------------
# NaN handling
# ---------------------------------------------------------------------------

def _clean_feat(feat: dict) -> dict:
    """Replace NaN float values with None so sklearn doesn't choke."""
    cleaned = {}
    for k, v in feat.items():
        if isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


# ---------------------------------------------------------------------------
# Bulk metadata fetch
# ---------------------------------------------------------------------------

def _fetch_fight_meta(fight_ids: list[str]) -> dict:
    """One bulk query returning metadata keyed by fight_id."""
    if not fight_ids:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                fd.id                AS fight_id,
                e.id                 AS event_id,
                e."EVENT"            AS event_name,
                e.date_proper        AS event_date,
                fr."METHOD"          AS actual_method,
                fr.weight_class
            FROM fight_details fd
            JOIN event_details e   ON e.id  = fd.event_id
            LEFT JOIN fight_results fr ON fr.fight_id = fd.id
            WHERE fd.id = ANY(:ids)
        """), {"ids": fight_ids}).mappings().all()
    return {r["fight_id"]: dict(r) for r in rows}


def _fetch_fighter_names() -> dict:
    """Load all fighter names as {id: 'First Last'}."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id,
                   TRIM(COALESCE("FIRST", '') || ' ' || COALESCE("LAST", '')) AS full_name
            FROM fighter_details
        """)).mappings().all()
    return {r["id"]: r["full_name"] for r in rows}


# ---------------------------------------------------------------------------
# Main backfill
# ---------------------------------------------------------------------------

def run(date_from: str = "2022-01-01") -> None:
    # ---- 1. Load parquet ----------------------------------------------------
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Training parquet not found at {PARQUET_PATH}. "
            "Run the feature engineering pipeline first:\n"
            "  cd backend && python features/pipeline.py"
        )

    logger.info("Loading training parquet from %s", PARQUET_PATH)
    df = pd.read_parquet(PARQUET_PATH)
    logger.info("Parquet loaded: %d rows", len(df))

    # ---- 2. Filter to test period -------------------------------------------
    df['event_date'] = pd.to_datetime(df['event_date'])
    cutoff = pd.Timestamp(date_from)
    df = df[df['event_date'] >= cutoff].copy()
    logger.info("Filtered to >= %s: %d rows", date_from, len(df))

    if len(df) == 0:
        logger.warning("No rows after date filter — nothing to compute.")
        return

    # ---- 3. Load models and selected features --------------------------------
    logger.info("Loading models...")
    store = ModelStore.load()

    with open(SEL_PATH, encoding="utf-8") as f:
        sel = json.load(f)

    feature_names  = sel["feature_names"]
    categorical    = sel["categorical_features"]
    all_cols       = feature_names + categorical

    # ---- 4. Bulk metadata fetch ---------------------------------------------
    fight_ids = df['fight_id'].dropna().unique().tolist()
    logger.info("Fetching metadata for %d fights...", len(fight_ids))
    fight_meta    = _fetch_fight_meta(fight_ids)
    fighter_names = _fetch_fighter_names()
    existing_ids  = _load_existing_ids()

    logger.info("Metadata ready. Starting inference...")

    # ---- 5. Iterate and compute predictions ---------------------------------
    upserts: list[dict] = []
    skipped = 0

    for i, (_, row) in enumerate(df.iterrows(), 1):
        fight_id = row.get('fight_id')
        if not fight_id or pd.isna(fight_id):
            skipped += 1
            continue

        meta = fight_meta.get(fight_id, {})

        # Build feature dict from parquet row
        feat_raw = {c: row.get(c) for c in all_cols}
        feat     = _clean_feat(feat_raw)

        try:
            result = predict(store, feat, sel=sel)
        except Exception as exc:
            logger.warning("predict() failed for fight %s: %s", fight_id, exc)
            skipped += 1
            continue

        win_prob_a = result['win_probability']
        win_prob_b = 1.0 - win_prob_a

        # IDs from parquet (post-perspective-flip)
        fa_id = row.get('fighter_a_id')
        fb_id = row.get('fighter_b_id')
        fighter_a_wins = row.get('fighter_a_wins')

        if pd.isna(fa_id) or pd.isna(fb_id):
            skipped += 1
            continue

        actual_winner_id    = fa_id if fighter_a_wins == 1 else fb_id
        predicted_winner_id = fa_id if win_prob_a >= 0.5 else fb_id
        is_correct          = (predicted_winner_id == actual_winner_id)
        confidence          = max(win_prob_a, win_prob_b)
        is_upset            = (not is_correct) and (confidence >= 0.65)

        methods = {
            'KO/TKO':     result['ko_tko'],
            'Submission': result['submission'],
            'Decision':   result['decision'],
        }
        predicted_method = max(methods, key=methods.get)

        fa_name = fighter_names.get(fa_id, fa_id)
        fb_name = fighter_names.get(fb_id, fb_id)

        event_id   = meta.get('event_id')
        event_name = meta.get('event_name')
        event_date = meta.get('event_date')
        if hasattr(event_date, 'date'):
            event_date = event_date.date()

        actual_method = meta.get('actual_method')
        weight_class  = meta.get('weight_class') or row.get('weight_class')

        upserts.append({
            "id":                  _new_id(existing_ids),
            "fight_id":            fight_id,
            "event_id":            event_id,
            "event_name":          event_name,
            "event_date":          event_date,
            "fighter_a_id":        fa_id,
            "fighter_b_id":        fb_id,
            "fighter_a_name":      fa_name,
            "fighter_b_name":      fb_name,
            "weight_class":        weight_class,
            "model_version":       "win_loss_v1",
            "win_prob_a":          win_prob_a,
            "win_prob_b":          win_prob_b,
            "pred_method_ko_tko":  result['ko_tko'],
            "pred_method_sub":     result['submission'],
            "pred_method_dec":     result['decision'],
            "predicted_winner_id": predicted_winner_id,
            "predicted_method":    predicted_method,
            "actual_winner_id":    actual_winner_id,
            "actual_method":       actual_method,
            "is_correct":          is_correct,
            "confidence":          confidence,
            "is_upset":            is_upset,
            "prediction_source":   "backfill",
        })

        if i % 50 == 0:
            logger.info("  Processed %d / %d fights...", i, len(df))

    # ---- 6. Upsert into past_predictions ------------------------------------
    logger.info("Upserting %d rows into past_predictions...", len(upserts))

    upsert_sql = text("""
        INSERT INTO past_predictions (
            id, fight_id, event_id, event_name, event_date,
            fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
            weight_class, model_version,
            win_prob_a, win_prob_b,
            pred_method_ko_tko, pred_method_sub, pred_method_dec,
            predicted_winner_id, predicted_method,
            actual_winner_id, actual_method,
            is_correct, confidence, is_upset,
            prediction_source
        ) VALUES (
            :id, :fight_id, :event_id, :event_name, :event_date,
            :fighter_a_id, :fighter_b_id, :fighter_a_name, :fighter_b_name,
            :weight_class, :model_version,
            :win_prob_a, :win_prob_b,
            :pred_method_ko_tko, :pred_method_sub, :pred_method_dec,
            :predicted_winner_id, :predicted_method,
            :actual_winner_id, :actual_method,
            :is_correct, :confidence, :is_upset,
            :prediction_source
        )
        ON CONFLICT (fight_id, prediction_source) DO UPDATE SET
            event_id            = EXCLUDED.event_id,
            event_name          = EXCLUDED.event_name,
            event_date          = EXCLUDED.event_date,
            fighter_a_id        = EXCLUDED.fighter_a_id,
            fighter_b_id        = EXCLUDED.fighter_b_id,
            fighter_a_name      = EXCLUDED.fighter_a_name,
            fighter_b_name      = EXCLUDED.fighter_b_name,
            weight_class        = EXCLUDED.weight_class,
            model_version       = EXCLUDED.model_version,
            win_prob_a          = EXCLUDED.win_prob_a,
            win_prob_b          = EXCLUDED.win_prob_b,
            pred_method_ko_tko  = EXCLUDED.pred_method_ko_tko,
            pred_method_sub     = EXCLUDED.pred_method_sub,
            pred_method_dec     = EXCLUDED.pred_method_dec,
            predicted_winner_id = EXCLUDED.predicted_winner_id,
            predicted_method    = EXCLUDED.predicted_method,
            actual_winner_id    = EXCLUDED.actual_winner_id,
            actual_method       = EXCLUDED.actual_method,
            is_correct          = EXCLUDED.is_correct,
            confidence          = EXCLUDED.confidence,
            is_upset            = EXCLUDED.is_upset,
            computed_at         = now()
    """)

    BATCH = 200
    total_upserted = 0
    with engine.begin() as conn:
        for start in range(0, len(upserts), BATCH):
            batch = upserts[start:start + BATCH]
            conn.execute(upsert_sql, batch)
            total_upserted += len(batch)
            logger.info("  Upserted batch: %d / %d", total_upserted, len(upserts))

    correct   = sum(1 for u in upserts if u["is_correct"])
    accuracy  = correct / len(upserts) * 100 if upserts else 0.0
    hc        = [u for u in upserts if u["confidence"] >= 0.65]
    hc_correct= sum(1 for u in hc if u["is_correct"])
    hc_acc    = hc_correct / len(hc) * 100 if hc else 0.0

    print(f"\n=== Past Predictions Backfill Complete ===")
    print(f"  Date range : >= {date_from}")
    print(f"  Total rows : {len(upserts)}  (skipped {skipped})")
    print(f"  Accuracy   : {correct}/{len(upserts)} = {accuracy:.1f}%")
    print(f"  High-conf  : {hc_correct}/{len(hc)} = {hc_acc:.1f}% (confidence >= 65%)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill past_predictions from training parquet")
    parser.add_argument(
        "--date-from",
        default="2022-01-01",
        help="Include fights from this date onwards (YYYY-MM-DD, default: 2022-01-01)",
    )
    args = parser.parse_args()
    run(date_from=args.date_from)

"""compute_predictions.py — Task 14

Compute ML predictions for all upcoming fights with matched fighters and
upsert results into upcoming_predictions.

For each row in upcoming_fights where both fighter_a_id and fighter_b_id
are set, calls build_prediction_features() + predict() and upserts into
upcoming_predictions.  Fights with NULL fighter IDs are skipped (new
fighters not yet in fighter_details).

Idempotent: re-running updates existing rows only when the feature hash
changes (i.e. fighter stats have been updated since last run).

Usage (from backend/):
    python scraper/compute_predictions.py
    python scraper/compute_predictions.py --dry-run
    python scraper/compute_predictions.py --fight-id <id>   # single fight
"""

import argparse
import hashlib
import json
import logging
import math
import os
import random
import string
import sys
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from sqlalchemy import text

from db.database import engine
from features.pipeline import build_prediction_features
from ml.loader import ModelStore
from ml.predictor import predict

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('compute_predictions.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id(existing: set) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        candidate = ''.join(random.choices(chars, k=6))
        if candidate not in existing:
            existing.add(candidate)
            return candidate


def _sanitize(feat: dict) -> dict:
    """Replace NaN/Inf float values with None (null in JSON)."""
    out = {}
    for k, v in feat.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        else:
            out[k] = v
    return out


def _feature_hash(feat: dict) -> str:
    """Stable SHA-256 hex digest of a feature dict (None/NaN-safe)."""
    clean = _sanitize(feat)
    serialised = json.dumps(
        {k: (round(v, 6) if isinstance(v, float) else v) for k, v in sorted(clean.items())},
        default=str,
    )
    return hashlib.sha256(serialised.encode()).hexdigest()[:16]


def _load_existing_ids(conn) -> set:
    tables = [
        'event_details', 'fighter_details', 'fight_details', 'fight_results',
        'fight_stats', 'fighter_tott', 'upcoming_events', 'upcoming_fights',
        'upcoming_predictions',
    ]
    ids: set = set()
    for table in tables:
        try:
            for row in conn.execute(text(f'SELECT id FROM {table}')):
                ids.add(row[0])
        except Exception:
            continue
    return ids


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def compute_for_fight(
    store: ModelStore,
    fight: dict,
    dry_run: bool,
    existing_ids: set,
    conn,
) -> bool:
    """Compute and upsert prediction for one fight. Returns True on success."""
    fa_id   = fight['fighter_a_id']
    fb_id   = fight['fighter_b_id']
    wc      = fight['weight_class'] or None
    fight_id = fight['id']

    name = f"{fight['fighter_a_name']} vs {fight['fighter_b_name']}"

    try:
        feat   = build_prediction_features(fa_id, fb_id, weight_class=wc)
        result = predict(store, feat)
        fhash  = _feature_hash(feat)
    except Exception as e:
        logger.error(f'  Feature build failed for {name}: {e}')
        return False

    win_prob_a    = result['win_probability']
    win_prob_b    = round(1.0 - win_prob_a, 6)
    method_ko_tko = result['ko_tko']
    method_sub    = result['submission']
    method_dec    = result['decision']

    print(
        f'  {name[:45]:<45}  '
        f'A: {win_prob_a:.0%}  '
        f'KO:{method_ko_tko:.0%} Sub:{method_sub:.0%} Dec:{method_dec:.0%}'
    )

    if dry_run:
        return True

    # Check if prediction already exists with same hash (skip if unchanged)
    existing = conn.execute(
        text('SELECT id, feature_hash FROM upcoming_predictions WHERE fight_id = :fid'),
        {'fid': fight_id}
    ).fetchone()

    if existing and existing[1] == fhash:
        logger.debug(f'  Skipped (hash unchanged): {name}')
        return True

    if existing:
        conn.execute(text("""
            UPDATE upcoming_predictions
            SET win_prob_a    = :wpa,
                win_prob_b    = :wpb,
                method_ko_tko = :ko,
                method_sub    = :sub,
                method_dec    = :dec,
                features_json = :feat,
                feature_hash  = :hash,
                predicted_at  = now()
            WHERE fight_id = :fid
        """), {
            'wpa': win_prob_a, 'wpb': win_prob_b,
            'ko': method_ko_tko, 'sub': method_sub, 'dec': method_dec,
            'feat': json.dumps(_sanitize(feat), default=str),
            'hash': fhash,
            'fid': fight_id,
        })
        logger.info(f'  Updated prediction: {name}')
    else:
        pred_id = _new_id(existing_ids)
        conn.execute(text("""
            INSERT INTO upcoming_predictions
                (id, fight_id, model_version, win_prob_a, win_prob_b,
                 method_ko_tko, method_sub, method_dec,
                 features_json, feature_hash)
            VALUES
                (:id, :fid, :ver, :wpa, :wpb,
                 :ko, :sub, :dec,
                 :feat, :hash)
        """), {
            'id': pred_id,
            'fid': fight_id,
            'ver': 'win_loss_v1',
            'wpa': win_prob_a, 'wpb': win_prob_b,
            'ko': method_ko_tko, 'sub': method_sub, 'dec': method_dec,
            'feat': json.dumps(_sanitize(feat), default=str),
            'hash': fhash,
        })
        logger.info(f'  Inserted prediction: {name} ({pred_id})')

    return True


def run(dry_run: bool = False, fight_id_filter: str | None = None) -> bool:
    print('=' * 60)
    print('UFC UPCOMING PREDICTIONS')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    if dry_run:
        print('[DRY RUN - no DB writes]')
    print('=' * 60)

    # Load models
    try:
        store = ModelStore.load()
        logger.info('Models loaded OK')
    except FileNotFoundError as e:
        print(f'ERROR: models not found — {e}')
        return False

    ok_count   = 0
    skip_count = 0
    fail_count = 0

    with engine.connect() as conn:
        existing_ids = _load_existing_ids(conn)

        # Fetch fights to predict
        where = 'WHERE uf.fighter_a_id IS NOT NULL AND uf.fighter_b_id IS NOT NULL'
        if fight_id_filter:
            where += ' AND uf.id = :fight_id'

        params = {'fight_id': fight_id_filter} if fight_id_filter else {}

        fights = conn.execute(text(f"""
            SELECT
                uf.id,
                uf.event_id,
                uf.fighter_a_name,
                uf.fighter_b_name,
                uf.fighter_a_id,
                uf.fighter_b_id,
                uf.weight_class,
                uf.is_title_fight,
                ue.event_name,
                ue.date_proper
            FROM upcoming_fights uf
            JOIN upcoming_events ue ON ue.id = uf.event_id
            {where}
            ORDER BY ue.date_proper ASC, uf.id ASC
        """), params).mappings().all()

        # Count skippable fights (NULL fighter IDs)
        total_skipped = conn.execute(text("""
            SELECT COUNT(*) FROM upcoming_fights
            WHERE fighter_a_id IS NULL OR fighter_b_id IS NULL
        """)).scalar() or 0

        logger.info(f'{len(fights)} fights to predict, {total_skipped} skipped (unmatched fighters)')

        current_event = None
        for fight in fights:
            if fight['event_name'] != current_event:
                current_event = fight['event_name']
                print(f'\n>> {current_event}  ({fight["date_proper"]})')

            success = compute_for_fight(
                store=store,
                fight=dict(fight),
                dry_run=dry_run,
                existing_ids=existing_ids,
                conn=conn,
            )
            if success:
                ok_count += 1
            else:
                fail_count += 1

        if not dry_run:
            conn.commit()

    print('\n' + '=' * 60)
    print(f'Done  -  {ok_count} predicted, {total_skipped} skipped (no fighter match), {fail_count} errors')
    if dry_run:
        print('[DRY RUN - nothing written]')
    print(f'Finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    return fail_count == 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Compute ML predictions for upcoming fights')
    parser.add_argument('--dry-run',  action='store_true', help='Print predictions without writing to DB')
    parser.add_argument('--fight-id', default=None,        help='Only predict for this upcoming_fights.id')
    args = parser.parse_args()

    success = run(dry_run=args.dry_run, fight_id_filter=args.fight_id)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

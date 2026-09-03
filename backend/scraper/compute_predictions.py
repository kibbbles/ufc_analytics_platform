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
from features.pipeline import (build_prediction_features,
                               build_prediction_features_batch,
                               PIPELINE_VERSION)
from ml.loader import ModelStore
from ml.predictor import predict

# Model family. Combined with the artefact fingerprint by _model_version().
MODEL_NAME = 'win_loss_v1' 

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


def _model_version(store) -> str:
    """Identify the exact artefacts that produced a prediction.

    'win_loss_v1' on its own names the model family, not the fitted weights, and
    it never changes: retraining rewrites the .joblib files and leaves that
    string alone, as it does PIPELINE_VERSION. Appending the artefact
    fingerprint makes the column answer the question it looks like it answers -
    which model produced this row - and lets a stale prediction be detected.
    """
    return f'{MODEL_NAME}@{getattr(store, "fingerprint", "unknown")}'


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

def _build_features_bulk(fights: list) -> dict:
    """Build every fight's feature vector up front, in as few passes as possible.

    Each build_prediction_features call runs every feature module across the
    whole fights and stats tables and reads two rows out of the result, so
    calling it per fight repeated that full-table pass once per fight: about 25
    seconds each, roughly half an hour for a card. Batched it is one pass for
    the entire card, measured at 29.5 seconds for 71 matchups.

    Phantom fight ids are derived from the fighter id, so a fighter booked twice
    cannot share a batch. Matchups are grouped so no fighter repeats within a
    group, which is normally a single group.

    Returns {fight_id: feature_dict}. A fight missing from the mapping failed to
    build and is handled by the caller.
    """
    groups: list[list] = []
    for fight in fights:
        for group in groups:
            if all(fight['fighter_a_id'] not in (f['fighter_a_id'], f['fighter_b_id'])
                   and fight['fighter_b_id'] not in (f['fighter_a_id'], f['fighter_b_id'])
                   for f in group):
                group.append(fight)
                break
        else:
            groups.append([fight])

    if len(groups) > 1:
        logger.info(f'  {len(groups)} batch groups (a fighter appears on more than one card)')

    feats: dict = {}
    for group in groups:
        matchups = [(f['fighter_a_id'], f['fighter_b_id'], f['weight_class'] or None)
                    for f in group]
        try:
            for fight, feat in zip(group, build_prediction_features_batch(matchups)):
                feats[fight['id']] = feat
        except Exception as e:
            # One unbuildable matchup must not cost the whole group, so fall
            # back to per-fight builds and let the bad one fail alone.
            logger.warning(f'  Batch feature build failed ({e}); falling back per fight')
            for fight in group:
                try:
                    feats[fight['id']] = build_prediction_features(
                        fight['fighter_a_id'], fight['fighter_b_id'],
                        weight_class=fight['weight_class'] or None)
                except Exception as inner:
                    logger.error(
                        f'  Feature build failed for {fight["fighter_a_name"]} vs '
                        f'{fight["fighter_b_name"]}: {inner}')
    return feats


def compute_for_fight(
    store: ModelStore,
    fight: dict,
    dry_run: bool,
    existing_ids: set,
    conn,
    feat: dict | None = None,
) -> str:
    """Compute and upsert one fight's prediction.

    Returns 'written', 'skipped' (features and models both unchanged) or
    'failed'. The caller counts these separately so a run that changed nothing
    cannot be mistaken for one that refreshed everything.
    """
    fa_id   = fight['fighter_a_id']
    fb_id   = fight['fighter_b_id']
    wc      = fight['weight_class'] or None
    fight_id = fight['id']

    name = f"{fight['fighter_a_name']} vs {fight['fighter_b_name']}"

    try:
        if feat is None:
            feat = build_prediction_features(fa_id, fb_id, weight_class=wc)
        result = predict(store, feat)
        fhash  = _feature_hash(feat)
    except Exception as e:
        logger.error(f'  Feature build failed for {name}: {e}')
        return 'failed' 

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

    # Skip only when BOTH the inputs and the models are unchanged. Comparing the
    # feature hash alone meant a retrain never reached this table: the features
    # are identical, so every fight was skipped and the site kept serving
    # predictions from the previous model with no error and no visible log line.
    #
    # This runs before the dry-run return on purpose. It is a read-only lookup,
    # and a dry run that reported every fight as a write would be useless for
    # deciding whether a recompute is worth running.
    mver = _model_version(store)
    existing = conn.execute(
        text('SELECT id, feature_hash, model_version FROM upcoming_predictions '
             'WHERE fight_id = :fid'),
        {'fid': fight_id}
    ).fetchone()
    unchanged = bool(existing and existing[1] == fhash and existing[2] == mver)

    if dry_run:
        return 'skipped' if unchanged else 'written'

    if unchanged:
        logger.debug(f'  Skipped (features and model unchanged): {name}')
        return 'skipped' 

    if existing:
        conn.execute(text("""
            UPDATE upcoming_predictions
            SET model_version = :ver,
                win_prob_a    = :wpa,
                win_prob_b    = :wpb,
                method_ko_tko = :ko,
                method_sub    = :sub,
                method_dec    = :dec,
                features_json = :feat,
                feature_hash  = :hash,
                pipeline_version = :pver,
                predicted_at  = now()
            WHERE fight_id = :fid
        """), {
            'ver': mver,
            'wpa': win_prob_a, 'wpb': win_prob_b,
            'ko': method_ko_tko, 'sub': method_sub, 'dec': method_dec,
            'feat': json.dumps(_sanitize(feat), default=str),
            'hash': fhash,
            'pver': PIPELINE_VERSION,
            'fid': fight_id,
        })
        logger.info(f'  Updated prediction: {name}')
    else:
        pred_id = _new_id(existing_ids)
        conn.execute(text("""
            INSERT INTO upcoming_predictions
                (id, fight_id, model_version, win_prob_a, win_prob_b,
                 method_ko_tko, method_sub, method_dec,
                 features_json, feature_hash, pipeline_version)
            VALUES
                (:id, :fid, :ver, :wpa, :wpb,
                 :ko, :sub, :dec,
                 :feat, :hash, :pver)
        """), {
            'id': pred_id,
            'fid': fight_id,
            'ver': mver,
            'wpa': win_prob_a, 'wpb': win_prob_b,
            'ko': method_ko_tko, 'sub': method_sub, 'dec': method_dec,
            'feat': json.dumps(_sanitize(feat), default=str),
            'hash': fhash,
            'pver': PIPELINE_VERSION,
        })
        logger.info(f'  Inserted prediction: {name} ({pred_id})')

    return 'written' 


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
        logger.info('Models loaded OK  (%s)', _model_version(store))
    except FileNotFoundError as e:
        print(f'ERROR: models not found — {e}')
        return False

    written_count = 0
    skip_count    = 0
    fail_count    = 0

    with engine.connect() as conn:
        existing_ids = _load_existing_ids(conn)

        # Fetch fights to predict
        where = 'WHERE uf.fighter_a_id IS NOT NULL AND uf.fighter_b_id IS NOT NULL'
        if fight_id_filter:
            where += ' AND uf.id = :fight_id'
        else:
            # Never recompute a bulk run over events that have already happened.
            # Recomputing a past event overwrites its frozen pre-fight snapshot
            # with an after-the-event vector (this permanently destroyed the
            # UFC 329 pre-fight record in 2026-07). The same-day workflow still
            # runs because today's card satisfies date_proper >= CURRENT_DATE.
            # An explicit single-fight recompute (fight_id_filter) bypasses this,
            # since that is a deliberate, targeted action.
            where += ' AND ue.date_proper >= CURRENT_DATE'

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

        prebuilt = _build_features_bulk([dict(f) for f in fights])

        current_event = None
        for fight in fights:
            if fight['event_name'] != current_event:
                current_event = fight['event_name']
                print(f'\n>> {current_event}  ({fight["date_proper"]})')

            outcome = compute_for_fight(
                store=store,
                fight=dict(fight),
                dry_run=dry_run,
                existing_ids=existing_ids,
                conn=conn,
                feat=prebuilt.get(fight['id']),
            )
            if outcome == 'written':
                written_count += 1
            elif outcome == 'skipped':
                skip_count += 1
            else:
                fail_count += 1

        if not dry_run:
            conn.commit()

    print('\n' + '=' * 60)
    # A run that writes nothing must not look like a run that refreshed
    # everything. Both counts are printed even when zero.
    print(f'Done  -  {written_count} written, {skip_count} unchanged, '
          f'{fail_count} errors, {total_skipped} not predicted (no fighter match)')
    print(f'Model    -  {_model_version(store)}')
    if written_count == 0 and skip_count:
        print('Note     -  nothing changed: same features, same model artefacts')
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

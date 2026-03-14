-- Migration 002: Prediction archive — prevent look-ahead bias in model scorecard
-- Adds prediction_source tracking to past_predictions so pre-fight frozen
-- predictions (archived from upcoming_predictions before retrain) can be
-- distinguished from retrospectively-computed backfill rows.

-- ---------------------------------------------------------------------------
-- 1. Add new columns to past_predictions
-- ---------------------------------------------------------------------------

ALTER TABLE past_predictions
    ADD COLUMN IF NOT EXISTS prediction_source TEXT
        CHECK (prediction_source IN ('pre_fight_archive', 'backfill'));

-- Original predicted_at from upcoming_predictions (null for backfill rows)
ALTER TABLE past_predictions
    ADD COLUMN IF NOT EXISTS pre_fight_predicted_at TIMESTAMPTZ;

-- Frozen pre-fight feature snapshot (null for backfill rows)
ALTER TABLE past_predictions
    ADD COLUMN IF NOT EXISTS features_json JSONB;

-- ---------------------------------------------------------------------------
-- 2. Replace the single-column unique index with a composite constraint
--    Old: UNIQUE INDEX on (fight_id) alone — allows only one row per fight
--    New: UNIQUE on (fight_id, prediction_source) — allows one pre_fight_archive
--         row and one backfill row per fight
-- ---------------------------------------------------------------------------

DROP INDEX IF EXISTS past_predictions_fight_id_idx;

ALTER TABLE past_predictions
    ADD CONSTRAINT uq_past_predictions_fight_source
    UNIQUE (fight_id, prediction_source);

-- ---------------------------------------------------------------------------
-- 3. Backfill existing rows as 'backfill' source
-- ---------------------------------------------------------------------------

UPDATE past_predictions
SET prediction_source = 'backfill'
WHERE prediction_source IS NULL;

-- ---------------------------------------------------------------------------
-- 4. Add archived flag to upcoming_fights for soft-delete after archiving
-- ---------------------------------------------------------------------------

ALTER TABLE upcoming_fights
    ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_upcoming_fights_archived
    ON upcoming_fights (archived);

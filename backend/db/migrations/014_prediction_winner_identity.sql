-- 014_prediction_winner_identity.sql
-- Re-points stale winner ids on past_predictions to the fighter rows that
-- fight_results and fight_details already use, and logs every change.
--
-- Found on 2026-11-24. The identity repair in c0cd5d5 (fighters resolved by
-- UFCStats URL, not by name) and the merges after it moved bouts between
-- same-named fighter rows, and gave some fighters new ids. past_predictions
-- had its fighter_a_id/fighter_b_id updated, but 21 rows kept the old id in
-- actual_winner_id or predicted_winner_id:
--   - 17 rows store an actual_winner_id that is neither fighter in the row:
--     the other Bruno Silva, Jean Silva or Mike Davis, or an id that no
--     longer exists (QYXLMV, 04F7SD, DXHY54). Two are live pre-fight rows
--     (UVRF98, G3S2OK).
--   - 11 rows store a predicted_winner_id that is neither fighter in the row,
--     always the other same-named fighter.
--
-- What this does not change: no prediction. Both writers derive
-- predicted_winner_id from the stored probability (fighter_a_id when
-- win_prob_a >= 0.5, else fighter_b_id), and that rule holds for every other
-- row in the table. The corrected id is the side the stored probability
-- already names, under the same person's current id. win_prob_a, win_prob_b,
-- confidence, is_correct and is_upset are untouched, and the assertions below
-- prove is_correct still agrees with the corrected ids.
--
-- What it does change: anything that reads "A won" from
-- actual_winner_id = fighter_a_id (Brier, ROC-AUC, betting win/loss) now sees
-- the real winner for these rows. Before, they were counted as B wins.
--
-- Every change is written to prediction_record_corrections with the old and
-- new value, so the original record can be reconstructed.
--
-- Safe to run twice: a second run finds the corrections already logged and
-- changes nothing.

BEGIN;

CREATE TABLE IF NOT EXISTS prediction_record_corrections (
    id                 BIGSERIAL PRIMARY KEY,
    past_prediction_id VARCHAR(8)  NOT NULL,
    fight_id           VARCHAR(8)  NOT NULL,
    prediction_source  TEXT        NOT NULL,
    column_name        TEXT        NOT NULL
        CHECK (column_name IN ('actual_winner_id', 'predicted_winner_id')),
    old_value          VARCHAR(8),
    new_value          VARCHAR(8)  NOT NULL,
    old_name           TEXT,  -- NULL when the old id has no fighter_details row
    new_name           TEXT        NOT NULL,
    reason             TEXT        NOT NULL,
    migration          TEXT        NOT NULL,
    corrected_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE prediction_record_corrections IS
    'Audit log of corrections to past_predictions identity columns. One row per changed column, with the old and new value.';

DO $$
DECLARE
    n_actual    INT;
    n_predicted INT;
    n_left      INT;
BEGIN
    IF EXISTS (SELECT 1 FROM prediction_record_corrections
               WHERE migration = '014_prediction_winner_identity') THEN
        RAISE NOTICE '014 already applied; nothing to do';
        RETURN;
    END IF;

    -- Snapshot of every column that must not move.
    CREATE TEMP TABLE pp_014_before ON COMMIT DROP AS
    SELECT id, win_prob_a, win_prob_b, confidence, is_correct, is_upset
    FROM past_predictions;

    -- actual_winner_id: the winner fight_results records, which must be one of
    -- the two fighters in the row.
    INSERT INTO prediction_record_corrections
        (past_prediction_id, fight_id, prediction_source, column_name,
         old_value, new_value, old_name, new_name, reason, migration)
    SELECT pp.id, pp.fight_id, pp.prediction_source, 'actual_winner_id',
           pp.actual_winner_id, fr.fighter_id,
           (SELECT trim(coalesce(f."FIRST", '') || ' ' || coalesce(f."LAST", ''))
              FROM fighter_details f WHERE f.id = pp.actual_winner_id),
           (SELECT trim(coalesce(f."FIRST", '') || ' ' || coalesce(f."LAST", ''))
              FROM fighter_details f WHERE f.id = fr.fighter_id),
           'stored winner was neither fighter in the row; replaced with fight_results.fighter_id',
           '014_prediction_winner_identity'
    FROM past_predictions pp
    JOIN fight_results fr ON fr.fight_id = pp.fight_id
    WHERE pp.actual_winner_id IS NOT NULL
      AND pp.actual_winner_id NOT IN (pp.fighter_a_id, pp.fighter_b_id)
      AND fr.fighter_id IN (pp.fighter_a_id, pp.fighter_b_id);
    GET DIAGNOSTICS n_actual = ROW_COUNT;

    -- predicted_winner_id: the side the stored probability picks. Accepted only
    -- when the old id names the same person (same name), so this can only
    -- re-point an alias, never move a pick to the other fighter.
    INSERT INTO prediction_record_corrections
        (past_prediction_id, fight_id, prediction_source, column_name,
         old_value, new_value, old_name, new_name, reason, migration)
    SELECT pp.id, pp.fight_id, pp.prediction_source, 'predicted_winner_id',
           pp.predicted_winner_id, side.id, old_f.name, side.name,
           'stored pick was neither fighter in the row; replaced with the side win_prob_a picks',
           '014_prediction_winner_identity'
    FROM past_predictions pp
    CROSS JOIN LATERAL (
        SELECT f.id, trim(coalesce(f."FIRST", '') || ' ' || coalesce(f."LAST", '')) AS name
        FROM fighter_details f
        WHERE f.id = CASE WHEN pp.win_prob_a >= 0.5 THEN pp.fighter_a_id ELSE pp.fighter_b_id END
    ) side
    CROSS JOIN LATERAL (
        SELECT trim(coalesce(f."FIRST", '') || ' ' || coalesce(f."LAST", '')) AS name
        FROM fighter_details f WHERE f.id = pp.predicted_winner_id
    ) old_f
    WHERE pp.predicted_winner_id IS NOT NULL
      AND pp.predicted_winner_id NOT IN (pp.fighter_a_id, pp.fighter_b_id)
      AND pp.win_prob_a IS NOT NULL
      AND lower(old_f.name) = lower(side.name);
    GET DIAGNOSTICS n_predicted = ROW_COUNT;

    -- Counted on 2026-11-24. A different count means the data moved since the
    -- audit, and the corrections need a human to look again.
    IF n_actual <> 17 OR n_predicted <> 11 THEN
        RAISE EXCEPTION '014: expected 17 actual and 11 predicted corrections, found % and %',
            n_actual, n_predicted;
    END IF;

    UPDATE past_predictions pp
    SET actual_winner_id = c.new_value
    FROM prediction_record_corrections c
    WHERE c.migration = '014_prediction_winner_identity'
      AND c.column_name = 'actual_winner_id'
      AND c.past_prediction_id = pp.id
      AND pp.actual_winner_id IS NOT DISTINCT FROM c.old_value;

    UPDATE past_predictions pp
    SET predicted_winner_id = c.new_value
    FROM prediction_record_corrections c
    WHERE c.migration = '014_prediction_winner_identity'
      AND c.column_name = 'predicted_winner_id'
      AND c.past_prediction_id = pp.id
      AND pp.predicted_winner_id IS NOT DISTINCT FROM c.old_value;

    -- No stale id may remain.
    SELECT COUNT(*) INTO n_left
    FROM past_predictions
    WHERE (actual_winner_id IS NOT NULL AND actual_winner_id NOT IN (fighter_a_id, fighter_b_id))
       OR (predicted_winner_id IS NOT NULL AND predicted_winner_id NOT IN (fighter_a_id, fighter_b_id));
    IF n_left <> 0 THEN
        RAISE EXCEPTION '014: % row(s) still store a winner outside the pair', n_left;
    END IF;

    -- Every stored winner now agrees with fight_results.
    SELECT COUNT(*) INTO n_left
    FROM past_predictions pp
    JOIN fight_results fr ON fr.fight_id = pp.fight_id
    WHERE pp.actual_winner_id IS DISTINCT FROM fr.fighter_id;
    IF n_left <> 0 THEN
        RAISE EXCEPTION '014: % row(s) disagree with fight_results on the winner', n_left;
    END IF;

    -- No prediction or score moved.
    SELECT COUNT(*) INTO n_left
    FROM past_predictions pp
    JOIN pp_014_before b ON b.id = pp.id
    WHERE pp.win_prob_a IS DISTINCT FROM b.win_prob_a
       OR pp.win_prob_b IS DISTINCT FROM b.win_prob_b
       OR pp.confidence IS DISTINCT FROM b.confidence
       OR pp.is_correct IS DISTINCT FROM b.is_correct
       OR pp.is_upset   IS DISTINCT FROM b.is_upset;
    IF n_left <> 0 THEN
        RAISE EXCEPTION '014: % row(s) changed a prediction or score column', n_left;
    END IF;

    -- is_correct still means what it says for the corrected rows.
    SELECT COUNT(*) INTO n_left
    FROM past_predictions pp
    WHERE pp.id IN (SELECT past_prediction_id FROM prediction_record_corrections
                    WHERE migration = '014_prediction_winner_identity')
      AND pp.predicted_winner_id IS NOT NULL
      AND pp.is_correct IS DISTINCT FROM (pp.predicted_winner_id = pp.actual_winner_id);
    IF n_left <> 0 THEN
        RAISE EXCEPTION '014: % corrected row(s) where is_correct disagrees with the ids', n_left;
    END IF;

    RAISE NOTICE '014: corrected % actual_winner_id and % predicted_winner_id values',
        n_actual, n_predicted;
END $$;

COMMIT;

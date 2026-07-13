-- 006_upcoming_pipeline_version.sql
-- Records the feature-pipeline version at the moment an upcoming prediction is
-- computed, so archive_completed_predictions.py can carry it forward into
-- past_predictions verbatim rather than stamping the archive-time version.
--
-- Why compute-time and not archive-time: a prediction is frozen (archived) up to
-- a week after it is computed. Stamping at archive time relies on the ordering
-- "recompute all pending predictions after any pipeline change, before they
-- archive" holding forever. Recording the version at compute time makes the
-- provenance exact regardless of ordering.
--
-- Additive and safe: existing rows keep pipeline_version = NULL until the next
-- recompute stamps them.

ALTER TABLE upcoming_predictions
    ADD COLUMN IF NOT EXISTS pipeline_version TEXT;

COMMENT ON COLUMN upcoming_predictions.pipeline_version IS
    'Feature-pipeline version that produced this prediction (e.g. streak_phantom_v2), stamped at compute time. Carried into past_predictions on archive.';

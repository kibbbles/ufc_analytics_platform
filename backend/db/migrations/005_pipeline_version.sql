-- 005_pipeline_version.sql
-- Records which feature-pipeline version produced each past_predictions row.
--
-- Motivation: a feature bug (win/loss streak computed with a one-fight lag at
-- inference, plus win_rate_diff silently null) was fixed in 2026-07.  Live
-- predictions frozen before the fix used the buggy pipeline; predictions after
-- it use the corrected one.  Recording the version lets the scorecard split the
-- live track record by pre-/post-fix once the post-fix sample is large enough,
-- without reconstructing that boundary from timestamps alone.
--
-- Additive and safe: existing rows keep pipeline_version = NULL (pre-versioning).
-- Does not alter any stored prediction value.

ALTER TABLE past_predictions
    ADD COLUMN IF NOT EXISTS pipeline_version TEXT;

COMMENT ON COLUMN past_predictions.pipeline_version IS
    'Feature-pipeline version that produced this row (e.g. streak_phantom_v2). NULL = pre-versioning, before the 2026-07 streak/win_rate fix.';

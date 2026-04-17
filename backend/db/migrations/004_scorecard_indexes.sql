-- Migration 004 — Indexes for scorecard (/past-predictions) query performance
--
-- Problem: every scorecard route runs at least one
--
--     DISTINCT ON (fight_id)
--     FROM past_predictions
--     ORDER BY fight_id,
--              CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
--
-- CTE. Without an index PostgreSQL sorts the full table on every request.
-- Additionally, several routes execute correlated scalar subqueries of the form:
--
--     (SELECT fr.is_title_fight FROM fight_results fr
--      WHERE fr.fight_id = past_predictions.fight_id LIMIT 1)
--
-- which do a sequential scan of fight_results per row if fight_id is unindexed.
--
-- Run this file once in the Supabase SQL editor.
-- No ETL refresh needed — indexes are maintained automatically by PostgreSQL.

-- ─────────────────────────────────────────────────────────────────────────────
-- Index 1: past_predictions — composite on (fight_id, prediction_source)
--
-- Supports the DISTINCT ON dedup pattern used across every scorecard CTE.
-- PostgreSQL can satisfy `ORDER BY fight_id, <expr on prediction_source>` with
-- an index scan instead of a full sort once fight_id is indexed; the source
-- column being included avoids a heap fetch for the CASE expression.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_pp_fight_id_source
    ON past_predictions (fight_id, prediction_source);

-- ─────────────────────────────────────────────────────────────────────────────
-- Index 2: past_predictions — event_date for date-range filters
--
-- Several endpoints filter by event_date (test_from window, year filter).
-- Without this index those filters scan the full table.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_pp_event_date
    ON past_predictions (event_date);

-- ─────────────────────────────────────────────────────────────────────────────
-- Index 3: fight_results — fight_id for correlated subquery lookups
--
-- The scorecard routes use correlated scalar subqueries to pull is_title_fight
-- and is_interim_title from fight_results per fight_id. fight_results.id is
-- the PK but the correlated lookup is on fight_results.fight_id (the FK column
-- back to fight_details), which has no index by default.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_fr_fight_id
    ON fight_results (fight_id);

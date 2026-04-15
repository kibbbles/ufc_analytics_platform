-- Migration 003 — Materialized views for style-evolution analytics
--
-- These views pre-compute all 8 aggregate queries run by
-- GET /api/v1/analytics/style-evolution so that the endpoint
-- reads pre-computed rows instead of re-aggregating raw tables on
-- every request.
--
-- Refresh cadence: REFRESH MATERIALIZED VIEW is called in
-- post_scrape_clean.py Phase 5 after every Sunday ETL run.
--
-- All views include data for ALL years including the current partial year.
-- The current year's rows are slightly stale between weekly scrapes (≤6 days),
-- which is acceptable for an analytics showcase.
--
-- Run this file once in the Supabase SQL editor to create the views.
-- After that, Phase 5 of the ETL handles all future refreshes.

-- ─────────────────────────────────────────────────────────────────────────────
-- Weight-class shortlist used across multiple views
-- ─────────────────────────────────────────────────────────────────────────────

-- Defined inline per view (no shared constant in SQL); matches _UFC_WEIGHT_CLASSES
-- in analytics.py.

-- ─────────────────────────────────────────────────────────────────────────────
-- View 1: mv_finish_rates
-- Source query: Query 1 in analytics.py (FinishRateChart)
-- Grain: year × weight_class  (weight_class IS NULL = all divisions combined)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_finish_rates AS
-- All-divisions rows (weight_class = NULL)
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int          AS year,
    NULL::text                                      AS weight_class,
    COUNT(*)                                        AS total_fights,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS ko_tko_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS submission_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS decision_rate
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
GROUP BY year

UNION ALL

-- Per-weight-class rows
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int          AS year,
    fr.weight_class,
    COUNT(*)                                        AS total_fights,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS ko_tko_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS submission_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                        AS decision_rate
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
  AND fr.weight_class IS NOT NULL
GROUP BY year, fr.weight_class

ORDER BY year, weight_class NULLS FIRST;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 2: mv_fighter_output
-- Source query: Query 2 in analytics.py (FighterOutputChart)
-- Grain: year × weight_class  (weight_class IS NULL = all divisions combined)
-- Covers 2015+ only (fight_stats coverage starts there)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_fighter_output AS
-- All-divisions rows
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int              AS year,
    NULL::text                                          AS weight_class,
    COUNT(DISTINCT per_fighter.fight_id)                AS total_fights,
    ROUND(AVG(per_fighter.sig_str_total)::numeric, 1)::float
                                                        AS avg_sig_str_per_fight,
    ROUND(AVG(per_fighter.td_attempted_total)::numeric, 1)::float
                                                        AS avg_td_attempts_per_fight,
    ROUND(AVG(per_fighter.ctrl_seconds_total)::numeric, 0)::float
                                                        AS avg_ctrl_seconds_per_fight
FROM (
    SELECT
        fs.fight_id,
        fs.fighter_id,
        SUM(fs.sig_str_landed)  AS sig_str_total,
        SUM(fs.td_attempted)    AS td_attempted_total,
        SUM(fs.ctrl_seconds)    AS ctrl_seconds_total
    FROM fight_stats fs
    WHERE fs."ROUND" NOT ILIKE '%total%'
      AND fs.sig_str_landed IS NOT NULL
    GROUP BY fs.fight_id, fs.fighter_id
) per_fighter
JOIN fight_details fdet ON fdet.id = per_fighter.fight_id
JOIN fight_results fr   ON fr.fight_id = per_fighter.fight_id
JOIN event_details ed   ON ed.id = fdet.event_id
WHERE ed.date_proper >= '2015-01-01'
GROUP BY year

UNION ALL

-- Per-weight-class rows
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int              AS year,
    fr.weight_class,
    COUNT(DISTINCT per_fighter.fight_id)                AS total_fights,
    ROUND(AVG(per_fighter.sig_str_total)::numeric, 1)::float
                                                        AS avg_sig_str_per_fight,
    ROUND(AVG(per_fighter.td_attempted_total)::numeric, 1)::float
                                                        AS avg_td_attempts_per_fight,
    ROUND(AVG(per_fighter.ctrl_seconds_total)::numeric, 0)::float
                                                        AS avg_ctrl_seconds_per_fight
FROM (
    SELECT
        fs.fight_id,
        fs.fighter_id,
        SUM(fs.sig_str_landed)  AS sig_str_total,
        SUM(fs.td_attempted)    AS td_attempted_total,
        SUM(fs.ctrl_seconds)    AS ctrl_seconds_total
    FROM fight_stats fs
    WHERE fs."ROUND" NOT ILIKE '%total%'
      AND fs.sig_str_landed IS NOT NULL
    GROUP BY fs.fight_id, fs.fighter_id
) per_fighter
JOIN fight_details fdet ON fdet.id = per_fighter.fight_id
JOIN fight_results fr   ON fr.fight_id = per_fighter.fight_id
JOIN event_details ed   ON ed.id = fdet.event_id
WHERE ed.date_proper >= '2015-01-01'
  AND fr.weight_class IS NOT NULL
GROUP BY year, fr.weight_class

ORDER BY year, weight_class NULLS FIRST;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 3: mv_round_distribution
-- Source query: Query 3 in analytics.py (RoundDistributionChart)
-- Grain: year × weight_class  (weight_class IS NULL = all divisions combined)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_round_distribution AS
-- All-divisions rows
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int  AS year,
    NULL::text                              AS weight_class,
    COUNT(*)                                AS total_finishes,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 1 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r1_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 2 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r2_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 3 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r3_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" >= 4 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r4plus_pct
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
  AND fr."METHOD" NOT ILIKE '%decision%'
  AND fr."METHOD" NOT ILIKE '%no contest%'
  AND fr."METHOD" NOT ILIKE '%dq%'
  AND fr."ROUND" IS NOT NULL
GROUP BY year

UNION ALL

-- Per-weight-class rows
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int  AS year,
    fr.weight_class,
    COUNT(*)                                AS total_finishes,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 1 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r1_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 2 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r2_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" = 3 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r3_pct,
    ROUND(
        COUNT(CASE WHEN fr."ROUND" >= 4 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS r4plus_pct
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
  AND fr."METHOD" NOT ILIKE '%decision%'
  AND fr."METHOD" NOT ILIKE '%no contest%'
  AND fr."METHOD" NOT ILIKE '%dq%'
  AND fr."ROUND" IS NOT NULL
  AND fr.weight_class IS NOT NULL
GROUP BY year, fr.weight_class

ORDER BY year, weight_class NULLS FIRST;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 4: mv_heatmap
-- Source query: Query 4 in analytics.py (WeightClassHeatmap)
-- Grain: year × weight_class (always all 13 UFC divisions — no filter variant)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_heatmap AS
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int  AS year,
    fr.weight_class,
    COUNT(*)                                AS total_fights,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS ko_tko_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS submission_rate,
    ROUND(
        COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                   THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
    )::float                                AS decision_rate
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
  AND fr.weight_class IN (
    'Heavyweight','Light Heavyweight','Middleweight','Welterweight',
    'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
    'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'
  )
GROUP BY year, fr.weight_class
ORDER BY year, fr.weight_class;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 5: mv_physical_stats
-- Source query: Query 5 in analytics.py (PhysicalStatsChart)
-- Grain: year × weight_class (always all UFC divisions — no filter variant)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_physical_stats AS
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int              AS year,
    fr.weight_class,
    ROUND(AVG(ft.height_inches)::numeric, 1)::float     AS avg_height_inches,
    ROUND(AVG(ft.reach_inches)::numeric, 1)::float      AS avg_reach_inches,
    COUNT(DISTINCT fr.fighter_id)                       AS fighter_count
FROM fight_results fr
JOIN event_details ed   ON ed.id = fr.event_id
JOIN fighter_tott ft    ON ft.fighter_id = fr.fighter_id
WHERE ft.height_inches IS NOT NULL
  AND ft.reach_inches IS NOT NULL
  AND fr.weight_class IN (
    'Heavyweight','Light Heavyweight','Middleweight','Welterweight',
    'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
    'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'
  )
GROUP BY year, fr.weight_class
HAVING COUNT(DISTINCT fr.fighter_id) >= 5
ORDER BY year, fr.weight_class;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 6: mv_age_data
-- Source query: Query 6 in analytics.py (AgeByWeightClassChart)
-- Grain: year × weight_class (always all UFC divisions — no filter variant)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_age_data AS
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int  AS year,
    fr.weight_class,
    ROUND(AVG(
        EXTRACT(YEAR  FROM AGE(ed.date_proper, ft.dob_date)) +
        EXTRACT(MONTH FROM AGE(ed.date_proper, ft.dob_date)) / 12.0
    )::numeric, 1)::float                  AS avg_age,
    COUNT(DISTINCT fr.fighter_id)          AS fighter_count
FROM fight_results fr
JOIN event_details ed ON ed.id = fr.event_id
JOIN fighter_tott ft  ON ft.fighter_id = fr.fighter_id
WHERE ft.dob_date IS NOT NULL
  AND ed.date_proper IS NOT NULL
  AND fr.weight_class IN (
    'Heavyweight','Light Heavyweight','Middleweight','Welterweight',
    'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
    'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'
  )
GROUP BY year, fr.weight_class
HAVING COUNT(DISTINCT fr.fighter_id) >= 5
ORDER BY year, fr.weight_class;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 7: mv_fighter_stats_by_wc
-- Source query: Query 7 in analytics.py (FighterStatsByWeightClassTable)
-- Grain: weight_class only (no year — career averages snapshot)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_fighter_stats_by_wc AS
SELECT
    fr.weight_class,
    ROUND(AVG(ft.slpm)::numeric,  2)::float AS avg_slpm,
    ROUND(AVG(NULLIF(REPLACE(ft.str_acc, '%', ''), '')::numeric / 100), 4)::float AS avg_str_acc,
    ROUND(AVG(ft.sapm)::numeric,  2)::float AS avg_sapm,
    ROUND(AVG(NULLIF(REPLACE(ft.str_def, '%', ''), '')::numeric / 100), 4)::float AS avg_str_def,
    ROUND(AVG(ft.td_avg)::numeric, 2)::float AS avg_td_avg,
    ROUND(AVG(NULLIF(REPLACE(ft.td_acc, '%', ''), '')::numeric / 100), 4)::float AS avg_td_acc,
    ROUND(AVG(NULLIF(REPLACE(ft.td_def, '%', ''), '')::numeric / 100), 4)::float AS avg_td_def,
    ROUND(AVG(ft.sub_avg)::numeric, 2)::float AS avg_sub_avg,
    COUNT(DISTINCT fr.fighter_id)             AS fighter_count
FROM fight_results fr
JOIN fighter_tott ft ON ft.fighter_id = fr.fighter_id
WHERE ft.slpm IS NOT NULL
  AND fr.weight_class IN (
    'Heavyweight','Light Heavyweight','Middleweight','Welterweight',
    'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
    'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'
  )
GROUP BY fr.weight_class
HAVING COUNT(DISTINCT fr.fighter_id) >= 10
ORDER BY fr.weight_class;

-- ─────────────────────────────────────────────────────────────────────────────
-- View 8: mv_style_stats
-- Source query: Query 8 in analytics.py (FighterStatsTimeSeriesChart)
-- Grain: year × weight_class (always all UFC divisions — no filter variant)
-- Most complex view: self-join on fight_stats to derive opponent-based metrics
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_style_stats AS
SELECT
    EXTRACT(YEAR FROM ed.date_proper)::int                  AS year,
    fr.weight_class,
    ROUND(AVG(
        pf.sig_str_landed::float / NULLIF(fr.total_fight_time_seconds / 60.0, 0)
    )::numeric, 2)::float                                   AS avg_slpm,
    ROUND(AVG(
        CASE WHEN pf.sig_str_attempted > 0
             THEN pf.sig_str_landed::float / pf.sig_str_attempted
             ELSE NULL END
    )::numeric, 4)::float                                   AS avg_str_acc,
    ROUND(AVG(
        pf.opp_sig_str_landed::float / NULLIF(fr.total_fight_time_seconds / 60.0, 0)
    )::numeric, 2)::float                                   AS avg_sapm,
    ROUND(AVG(
        CASE WHEN pf.opp_sig_str_attempted > 0
             THEN 1.0 - pf.opp_sig_str_landed::float / pf.opp_sig_str_attempted
             ELSE NULL END
    )::numeric, 4)::float                                   AS avg_str_def,
    ROUND(AVG(pf.td_landed)::numeric, 2)::float             AS avg_td_per_fight,
    ROUND(AVG(
        CASE WHEN pf.td_attempted > 0
             THEN pf.td_landed::float / pf.td_attempted
             ELSE NULL END
    )::numeric, 4)::float                                   AS avg_td_acc,
    ROUND(AVG(
        CASE WHEN pf.opp_td_attempted > 0
             THEN 1.0 - pf.opp_td_landed::float / pf.opp_td_attempted
             ELSE NULL END
    )::numeric, 4)::float                                   AS avg_td_def,
    ROUND(AVG(pf.sub_attempts)::numeric, 2)::float          AS avg_sub_per_fight,
    ROUND(AVG(pf.ctrl_seconds_total)::numeric, 0)::float    AS avg_ctrl_seconds,
    COUNT(DISTINCT pf.fight_id)                             AS fight_count
FROM (
    SELECT
        fs.fight_id,
        fs.fighter_id,
        SUM(fs.sig_str_landed)    AS sig_str_landed,
        SUM(fs.sig_str_attempted) AS sig_str_attempted,
        SUM(fs.td_landed)         AS td_landed,
        SUM(fs.td_attempted)      AS td_attempted,
        SUM(fs.ctrl_seconds)      AS ctrl_seconds_total,
        SUM(CASE WHEN TRIM(COALESCE(fs."SUB.ATT", '')) ~ '^[0-9]+(\.[0-9]*)?$'
                 THEN FLOOR(TRIM(fs."SUB.ATT")::numeric)::integer ELSE 0 END) AS sub_attempts,
        SUM(opp.sig_str_landed)    AS opp_sig_str_landed,
        SUM(opp.sig_str_attempted) AS opp_sig_str_attempted,
        SUM(opp.td_landed)         AS opp_td_landed,
        SUM(opp.td_attempted)      AS opp_td_attempted
    FROM fight_stats fs
    JOIN fight_stats opp ON opp.fight_id = fs.fight_id
        AND opp.fighter_id != fs.fighter_id
        AND opp.fighter_id IS NOT NULL
        AND opp."ROUND" NOT ILIKE '%total%'
    WHERE fs."ROUND" NOT ILIKE '%total%'
      AND fs.sig_str_landed IS NOT NULL
      AND fs.fighter_id IS NOT NULL
    GROUP BY fs.fight_id, fs.fighter_id
) pf
JOIN fight_results fr ON fr.fight_id = pf.fight_id
JOIN event_details ed  ON ed.id = fr.event_id
WHERE ed.date_proper IS NOT NULL
  AND fr.total_fight_time_seconds > 0
  AND fr.weight_class IN (
    'Heavyweight','Light Heavyweight','Middleweight','Welterweight',
    'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
    'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'
  )
GROUP BY year, fr.weight_class
HAVING COUNT(DISTINCT pf.fight_id) >= 5
ORDER BY year, fr.weight_class;

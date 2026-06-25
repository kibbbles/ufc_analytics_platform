-- Migration 004 — Materialized views for betting insights analytics
--
-- Powers GET /api/v1/analytics/betting-insights
-- Refresh cadence: added to post_scrape_clean.py phase 5 alongside existing views.
--
-- Run once in the Supabase SQL editor to create the views.
-- After that, Phase 5 of the ETL handles all future refreshes.

-- ─────────────────────────────────────────────────────────────────────────────
-- View 1: mv_betting_roi
-- Grain: one row per preset betting strategy
-- Source: past_predictions WHERE implied_prob_a IS NOT NULL (Vegas odds window)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_betting_roi AS
WITH base AS (
    SELECT DISTINCT ON (pp.fight_id)
        pp.fight_id,
        pp.win_prob_a,
        pp.win_prob_b,
        pp.implied_prob_a,
        pp.implied_prob_b,
        pp.odds_a,
        pp.odds_b,
        pp.actual_winner_id,
        pp.fighter_a_id,
        pp.is_correct,
        pp.confidence
    FROM past_predictions pp
    WHERE pp.implied_prob_a IS NOT NULL
      AND pp.actual_winner_id IS NOT NULL
      AND pp.is_correct IS NOT NULL
      AND pp.odds_a IS NOT NULL
      AND pp.odds_b IS NOT NULL
    ORDER BY pp.fight_id,
             CASE WHEN pp.prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
),
enriched AS (
    SELECT *,
        CASE WHEN win_prob_a >= 0.5 THEN odds_a ELSE odds_b END     AS model_odds,
        is_correct                                                    AS model_won,
        CASE WHEN implied_prob_a > 0.5 THEN odds_a ELSE odds_b END  AS vegas_fav_odds,
        CASE WHEN (implied_prob_a > 0.5 AND actual_winner_id = fighter_a_id)
                  OR (implied_prob_a <= 0.5 AND actual_winner_id != fighter_a_id)
             THEN TRUE ELSE FALSE END                                 AS vegas_fav_won,
        CASE WHEN implied_prob_a <= 0.5 THEN odds_a ELSE odds_b END AS vegas_dog_odds,
        CASE WHEN (implied_prob_a <= 0.5 AND actual_winner_id = fighter_a_id)
                  OR (implied_prob_a > 0.5 AND actual_winner_id != fighter_a_id)
             THEN TRUE ELSE FALSE END                                 AS vegas_dog_won,
        CASE WHEN win_prob_a >= 0.5 THEN win_prob_a ELSE win_prob_b END       AS model_prob_pick,
        CASE WHEN win_prob_a >= 0.5 THEN implied_prob_a ELSE implied_prob_b END AS vegas_implied_pick,
        (win_prob_a >= 0.5) = (implied_prob_a > 0.5)                 AS model_agrees_vegas
    FROM base
)

-- Strategy 1: Always bet model pick
SELECT 'model_pick'::text          AS strategy_key,
       'Always Bet Model Pick'     AS strategy_name,
       1                           AS strategy_order,
       COUNT(*)                    AS bets,
       SUM(CASE WHEN model_won THEN 1 ELSE 0 END) AS wins,
       ROUND(SUM(
           CASE WHEN model_won
               THEN CASE WHEN model_odds > 0 THEN model_odds::float / 100.0 ELSE 100.0 / ABS(model_odds)::float END
               ELSE -1.0
           END
       )::numeric, 4)::float       AS pnl
FROM enriched

UNION ALL

-- Strategy 2: Always bet Vegas favourite
SELECT 'vegas_fav',
       'Always Bet Vegas Favourite',
       2,
       COUNT(*),
       SUM(CASE WHEN vegas_fav_won THEN 1 ELSE 0 END),
       ROUND(SUM(
           CASE WHEN vegas_fav_won
               THEN CASE WHEN vegas_fav_odds > 0 THEN vegas_fav_odds::float / 100.0 ELSE 100.0 / ABS(vegas_fav_odds)::float END
               ELSE -1.0
           END
       )::numeric, 4)::float
FROM enriched

UNION ALL

-- Strategy 3: Always bet Vegas underdog
SELECT 'vegas_dog',
       'Always Bet Vegas Underdog',
       3,
       COUNT(*),
       SUM(CASE WHEN vegas_dog_won THEN 1 ELSE 0 END),
       ROUND(SUM(
           CASE WHEN vegas_dog_won
               THEN CASE WHEN vegas_dog_odds > 0 THEN vegas_dog_odds::float / 100.0 ELSE 100.0 / ABS(vegas_dog_odds)::float END
               ELSE -1.0
           END
       )::numeric, 4)::float
FROM enriched

UNION ALL

-- Strategy 4: Model pick when disagrees with Vegas
SELECT 'model_vs_vegas',
       'Model Pick vs Vegas',
       4,
       COUNT(*) FILTER (WHERE NOT model_agrees_vegas),
       SUM(CASE WHEN NOT model_agrees_vegas AND model_won THEN 1 ELSE 0 END),
       ROUND(SUM(
           CASE WHEN NOT model_agrees_vegas
               THEN CASE WHEN model_won
                       THEN CASE WHEN model_odds > 0 THEN model_odds::float / 100.0 ELSE 100.0 / ABS(model_odds)::float END
                       ELSE -1.0
                    END
               ELSE 0.0
           END
       )::numeric, 4)::float
FROM enriched

UNION ALL

-- Strategy 5: Model pick when model has 5–15% edge over Vegas implied prob
SELECT 'model_edge_5_15',
       'Model Edge 5–15% Over Vegas',
       5,
       COUNT(*) FILTER (WHERE (model_prob_pick - vegas_implied_pick) BETWEEN 0.05 AND 0.15),
       SUM(CASE WHEN (model_prob_pick - vegas_implied_pick) BETWEEN 0.05 AND 0.15 AND model_won THEN 1 ELSE 0 END),
       ROUND(SUM(
           CASE WHEN (model_prob_pick - vegas_implied_pick) BETWEEN 0.05 AND 0.15
               THEN CASE WHEN model_won
                       THEN CASE WHEN model_odds > 0 THEN model_odds::float / 100.0 ELSE 100.0 / ABS(model_odds)::float END
                       ELSE -1.0
                    END
               ELSE 0.0
           END
       )::numeric, 4)::float
FROM enriched;

CREATE UNIQUE INDEX ON mv_betting_roi (strategy_key);


-- ─────────────────────────────────────────────────────────────────────────────
-- View 2: mv_vegas_calibration
-- Grain: one row per Vegas implied probability bucket (favourite's side)
-- Answers: do Vegas implied probs match actual win rates?
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_vegas_calibration AS
WITH base AS (
    SELECT DISTINCT ON (fight_id)
        implied_prob_a,
        actual_winner_id,
        fighter_a_id
    FROM past_predictions
    WHERE implied_prob_a IS NOT NULL
      AND actual_winner_id IS NOT NULL
    ORDER BY fight_id,
             CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
),
bucketed AS (
    SELECT *,
        -- Flip so we always look at the favourite's side (implied > 0.5)
        CASE WHEN implied_prob_a > 0.5 THEN implied_prob_a ELSE 1 - implied_prob_a END AS fav_implied,
        CASE WHEN (implied_prob_a > 0.5 AND actual_winner_id = fighter_a_id)
                  OR (implied_prob_a <= 0.5 AND actual_winner_id != fighter_a_id)
             THEN TRUE ELSE FALSE END AS fav_won
    FROM base
    WHERE implied_prob_a != 0.5  -- exclude true pick'ems
)
SELECT
    CASE
        WHEN fav_implied >= 0.80 THEN '80%+'
        WHEN fav_implied >= 0.70 THEN '70–80%'
        WHEN fav_implied >= 0.60 THEN '60–70%'
        ELSE '50–60%'
    END                                                AS bucket,
    CASE
        WHEN fav_implied >= 0.80 THEN 4
        WHEN fav_implied >= 0.70 THEN 3
        WHEN fav_implied >= 0.60 THEN 2
        ELSE 1
    END                                                AS bucket_order,
    ROUND(AVG(fav_implied)::numeric, 3)::float         AS avg_implied_prob,
    COUNT(*)::int                                      AS fights,
    SUM(CASE WHEN fav_won THEN 1 ELSE 0 END)::int     AS wins,
    ROUND(AVG(CASE WHEN fav_won THEN 1.0 ELSE 0.0 END)::numeric, 4)::float AS actual_win_rate
FROM bucketed
GROUP BY bucket, bucket_order
ORDER BY bucket_order;

CREATE UNIQUE INDEX ON mv_vegas_calibration (bucket);


-- ─────────────────────────────────────────────────────────────────────────────
-- View 3: mv_upset_rates
-- Grain: one row per weight class
-- Uses ALL past_predictions (not Vegas-only) for larger sample.
-- is_upset = model was wrong AND confidence >= 0.30 (high-conviction miss)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_upset_rates AS
WITH best AS (
    SELECT DISTINCT ON (fight_id)
        fight_id, weight_class, is_upset, is_correct
    FROM past_predictions
    WHERE is_correct IS NOT NULL
      AND weight_class IS NOT NULL
    ORDER BY fight_id,
             CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
)
SELECT
    weight_class,
    CASE weight_class
        WHEN 'Heavyweight'            THEN 1
        WHEN 'Light Heavyweight'      THEN 2
        WHEN 'Middleweight'           THEN 3
        WHEN 'Welterweight'           THEN 4
        WHEN 'Lightweight'            THEN 5
        WHEN 'Featherweight'          THEN 6
        WHEN 'Bantamweight'           THEN 7
        WHEN 'Flyweight'              THEN 8
        WHEN 'Women''s Featherweight' THEN 9
        WHEN 'Women''s Bantamweight'  THEN 10
        WHEN 'Women''s Flyweight'     THEN 11
        WHEN 'Women''s Strawweight'   THEN 12
        ELSE 99
    END                                                AS weight_class_order,
    COUNT(*)::int                                      AS total_fights,
    SUM(CASE WHEN is_upset = TRUE THEN 1 ELSE 0 END)::int AS upset_count,
    ROUND(
        SUM(CASE WHEN is_upset = TRUE THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)
    , 4)::float                                        AS upset_rate
FROM best
GROUP BY weight_class
ORDER BY upset_rate DESC;

CREATE UNIQUE INDEX ON mv_upset_rates (weight_class);


-- ─────────────────────────────────────────────────────────────────────────────
-- View 4: mv_roi_over_time
-- Grain: one row per event (model-pick strategy, Vegas fights only)
-- Includes cumulative P&L running total for the trend chart.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mv_roi_over_time AS
WITH base AS (
    SELECT DISTINCT ON (pp.fight_id)
        pp.event_id,
        pp.event_name,
        pp.event_date,
        pp.is_correct,
        CASE WHEN pp.win_prob_a >= 0.5 THEN pp.odds_a ELSE pp.odds_b END AS picked_odds
    FROM past_predictions pp
    WHERE pp.implied_prob_a IS NOT NULL
      AND pp.actual_winner_id IS NOT NULL
      AND pp.is_correct IS NOT NULL
      AND pp.odds_a IS NOT NULL
      AND pp.odds_b IS NOT NULL
    ORDER BY pp.fight_id,
             CASE WHEN pp.prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
),
event_pnl AS (
    SELECT
        event_id,
        MAX(event_name)  AS event_name,
        MAX(event_date)  AS event_date,
        COUNT(*)::int    AS bets,
        ROUND(SUM(
            CASE WHEN is_correct
                THEN CASE WHEN picked_odds > 0 THEN picked_odds::float / 100.0 ELSE 100.0 / ABS(picked_odds)::float END
                ELSE -1.0
            END
        )::numeric, 4)::float AS pnl
    FROM base
    GROUP BY event_id
)
SELECT
    event_id,
    event_name,
    event_date,
    bets,
    pnl,
    ROUND(SUM(pnl) OVER (ORDER BY event_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::numeric, 4)::float
        AS cumulative_pnl,
    SUM(bets) OVER (ORDER BY event_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::int
        AS cumulative_bets
FROM event_pnl
ORDER BY event_date;

CREATE UNIQUE INDEX ON mv_roi_over_time (event_id);

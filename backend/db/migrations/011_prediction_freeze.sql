-- 011_prediction_freeze.sql
-- Freezes each prediction and its odds when the fight's card section starts,
-- and flags archived rows that were written after that point.
--
-- Found on 2026-11-23. The Saturday predictions job is scheduled for 15:00 UTC,
-- but GitHub Actions started it between 17:43 and 20:44 UTC on recent
-- Saturdays, often after the card had begun. compute_predictions.py rewrote
-- any prediction whose features or model had changed, and fetch_odds.py wrote
-- any odds that had moved, with no check on whether the fight had started.
-- The archive only refused predictions dated after the event day, so a
-- same-day rewrite was archived as a "pre-fight" prediction.
--
-- Audit of all 355 archived pre-fight predictions (2026-03-14 to 2026-11-21)
-- against section start times from UFC.com's event feed:
--   - 16 predictions were written after their section started, across 6
--     events. For 11 of them the bout itself had already begun.
--   - 5 rows had their odds written after their section started, proved by
--     the job logs. Two are in-play or post-fight prices: Cornolle vs. Sygula
--     at -100000/+4000, written 30 minutes into the bout, and Prochazka vs.
--     Stirling at +179/-212, written two minutes after the knockout, against
--     +128/-150 a week earlier.
--   - 14 rows have odds that a post-start run could have rewritten, but that
--     run's log has expired, so when they were captured cannot be proved.
--
-- Nothing is deleted. backfill_prediction_integrity.py fills the new columns
-- for existing rows from backend/scraper/reports/prediction_integrity_audit.json.
--
-- After this migration:
--   - prediction_freeze_at() is the one definition of "the fight has started":
--     the section's scheduled start from UFC.com, or 12:00 UTC on the day
--     before the event when that is unknown (an early start in Asia or
--     Australia can fall on the previous UTC day).
--   - Triggers refuse any write to upcoming_predictions, and any change to
--     upcoming_fights odds, once a fight is frozen. The scripts skip frozen
--     fights themselves; the triggers are the backstop.
--   - scored_predictions is past_predictions without the rows written after
--     the start, and with odds blanked unless they are known to predate it.
--     Every scorecard, ROI and Vegas comparison reads it instead of the table.
--
-- Run once in the Supabase SQL editor, then:
--     python backend/scraper/backfill_prediction_integrity.py
--     python backend/scraper/post_scrape_clean.py --phase 5

BEGIN;

ALTER TABLE upcoming_events ADD COLUMN IF NOT EXISTS ufc_event_fmid INTEGER;
ALTER TABLE upcoming_fights ADD COLUMN IF NOT EXISTS section_start_at TIMESTAMPTZ;
ALTER TABLE past_predictions
    ADD COLUMN IF NOT EXISTS section_start_at       TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS prediction_after_start BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS odds_after_start       BOOLEAN;   -- NULL: capture time unknown

COMMENT ON COLUMN past_predictions.prediction_after_start IS
    'A live (pre_fight_archive) prediction written at or after its card section started. Excluded from every scorecard and ROI figure. Backfill rows are never flagged: they are labelled as computed after the fact.';
COMMENT ON COLUMN past_predictions.odds_after_start IS
    'TRUE: odds written at or after the section start. FALSE: written before it. NULL: unknown. Only FALSE odds are scored.';

CREATE OR REPLACE FUNCTION prediction_freeze_at(section_start TIMESTAMPTZ, event_date DATE)
RETURNS TIMESTAMPTZ
LANGUAGE sql IMMUTABLE AS $$
    SELECT COALESCE(section_start, (event_date::timestamp AT TIME ZONE 'UTC') - INTERVAL '12 hours')
$$;

CREATE OR REPLACE FUNCTION refuse_frozen_prediction() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    frozen_at TIMESTAMPTZ;
BEGIN
    SELECT prediction_freeze_at(uf.section_start_at, ue.date_proper) INTO frozen_at
    FROM upcoming_fights uf
    JOIN upcoming_events ue ON ue.id = uf.event_id
    WHERE uf.id = NEW.fight_id;
    IF frozen_at IS NOT NULL AND now() >= frozen_at THEN
        RAISE EXCEPTION 'prediction for upcoming fight % is frozen since % (section started)', NEW.fight_id, frozen_at;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS upcoming_predictions_freeze ON upcoming_predictions;
CREATE TRIGGER upcoming_predictions_freeze
    BEFORE INSERT OR UPDATE ON upcoming_predictions
    FOR EACH ROW EXECUTE FUNCTION refuse_frozen_prediction();

CREATE OR REPLACE FUNCTION refuse_frozen_odds() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    frozen_at TIMESTAMPTZ;
BEGIN
    IF (NEW.odds_a, NEW.odds_b, NEW.implied_prob_a, NEW.implied_prob_b)
       IS NOT DISTINCT FROM (OLD.odds_a, OLD.odds_b, OLD.implied_prob_a, OLD.implied_prob_b) THEN
        RETURN NEW;
    END IF;
    SELECT prediction_freeze_at(NEW.section_start_at, ue.date_proper) INTO frozen_at
    FROM upcoming_events ue
    WHERE ue.id = NEW.event_id;
    IF frozen_at IS NOT NULL AND now() >= frozen_at THEN
        RAISE EXCEPTION 'odds for upcoming fight % are frozen since % (section started)', NEW.id, frozen_at;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS upcoming_fights_odds_freeze ON upcoming_fights;
CREATE TRIGGER upcoming_fights_odds_freeze
    BEFORE UPDATE OF odds_a, odds_b, implied_prob_a, implied_prob_b ON upcoming_fights
    FOR EACH ROW EXECUTE FUNCTION refuse_frozen_odds();

-- The betting views will read scored_predictions, so they are rebuilt after it.
DROP MATERIALIZED VIEW IF EXISTS mv_betting_roi, mv_vegas_calibration, mv_upset_rates, mv_roi_over_time;

CREATE OR REPLACE VIEW scored_predictions AS
SELECT
    id,
    fight_id,
    event_id,
    event_name,
    event_date,
    fighter_a_id,
    fighter_b_id,
    fighter_a_name,
    fighter_b_name,
    weight_class,
    model_version,
    win_prob_a,
    win_prob_b,
    pred_method_ko_tko,
    pred_method_sub,
    pred_method_dec,
    predicted_winner_id,
    predicted_method,
    actual_winner_id,
    actual_method,
    is_correct,
    confidence,
    is_upset,
    computed_at,
    prediction_source,
    pre_fight_predicted_at,
    features_json,
    CASE WHEN odds_after_start IS FALSE THEN odds_a END AS odds_a,
    CASE WHEN odds_after_start IS FALSE THEN odds_b END AS odds_b,
    CASE WHEN odds_after_start IS FALSE THEN implied_prob_a END AS implied_prob_a,
    CASE WHEN odds_after_start IS FALSE THEN implied_prob_b END AS implied_prob_b,
    CASE WHEN odds_after_start IS FALSE THEN odds_scraped_at END AS odds_scraped_at,
    pipeline_version,
    section_start_at,
    prediction_after_start,
    odds_after_start
FROM past_predictions
WHERE NOT prediction_after_start;

COMMENT ON VIEW scored_predictions IS
    'past_predictions as scored: rows written after the section start removed, odds kept only when known to predate it.';

-- Betting views, as live on 2026-11-23, now reading scored_predictions.
CREATE MATERIALIZED VIEW mv_betting_roi AS
 WITH base AS (
         SELECT DISTINCT ON (pp.fight_id) pp.fight_id,
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
           FROM scored_predictions pp
          WHERE pp.implied_prob_a IS NOT NULL AND pp.actual_winner_id IS NOT NULL AND pp.is_correct IS NOT NULL AND pp.odds_a IS NOT NULL AND pp.odds_b IS NOT NULL
          ORDER BY pp.fight_id, (
                CASE
                    WHEN pp.prediction_source = 'pre_fight_archive'::text THEN 0
                    ELSE 1
                END)
        ), enriched AS (
         SELECT base.fight_id,
            base.win_prob_a,
            base.win_prob_b,
            base.implied_prob_a,
            base.implied_prob_b,
            base.odds_a,
            base.odds_b,
            base.actual_winner_id,
            base.fighter_a_id,
            base.is_correct,
            base.confidence,
                CASE
                    WHEN base.win_prob_a >= 0.5::double precision THEN base.odds_a
                    ELSE base.odds_b
                END AS model_odds,
            base.is_correct AS model_won,
                CASE
                    WHEN base.implied_prob_a > 0.5::double precision THEN base.odds_a
                    ELSE base.odds_b
                END AS vegas_fav_odds,
                CASE
                    WHEN base.implied_prob_a > 0.5::double precision AND base.actual_winner_id::text = base.fighter_a_id::text OR base.implied_prob_a <= 0.5::double precision AND base.actual_winner_id::text <> base.fighter_a_id::text THEN true
                    ELSE false
                END AS vegas_fav_won,
                CASE
                    WHEN base.implied_prob_a <= 0.5::double precision THEN base.odds_a
                    ELSE base.odds_b
                END AS vegas_dog_odds,
                CASE
                    WHEN base.implied_prob_a <= 0.5::double precision AND base.actual_winner_id::text = base.fighter_a_id::text OR base.implied_prob_a > 0.5::double precision AND base.actual_winner_id::text <> base.fighter_a_id::text THEN true
                    ELSE false
                END AS vegas_dog_won,
                CASE
                    WHEN base.win_prob_a >= 0.5::double precision THEN base.win_prob_a
                    ELSE base.win_prob_b
                END AS model_prob_pick,
                CASE
                    WHEN base.win_prob_a >= 0.5::double precision THEN base.implied_prob_a
                    ELSE base.implied_prob_b
                END AS vegas_implied_pick,
            (base.win_prob_a >= 0.5::double precision) = (base.implied_prob_a > 0.5::double precision) AS model_agrees_vegas
           FROM base
        )
 SELECT 'model_pick'::text AS strategy_key,
    'Always Bet Model Pick'::text AS strategy_name,
    1 AS strategy_order,
    count(*) AS bets,
    sum(
        CASE
            WHEN enriched.model_won THEN 1
            ELSE 0
        END) AS wins,
    round(sum(
        CASE
            WHEN enriched.model_won THEN
            CASE
                WHEN enriched.model_odds > 0 THEN enriched.model_odds::double precision / 100.0::double precision
                ELSE 100.0::double precision / abs(enriched.model_odds)::double precision
            END
            ELSE '-1.0'::numeric::double precision
        END)::numeric, 4)::double precision AS pnl
   FROM enriched
UNION ALL
 SELECT 'vegas_fav'::text AS strategy_key,
    'Always Bet Vegas Favourite'::text AS strategy_name,
    2 AS strategy_order,
    count(*) AS bets,
    sum(
        CASE
            WHEN enriched.vegas_fav_won THEN 1
            ELSE 0
        END) AS wins,
    round(sum(
        CASE
            WHEN enriched.vegas_fav_won THEN
            CASE
                WHEN enriched.vegas_fav_odds > 0 THEN enriched.vegas_fav_odds::double precision / 100.0::double precision
                ELSE 100.0::double precision / abs(enriched.vegas_fav_odds)::double precision
            END
            ELSE '-1.0'::numeric::double precision
        END)::numeric, 4)::double precision AS pnl
   FROM enriched
UNION ALL
 SELECT 'vegas_dog'::text AS strategy_key,
    'Always Bet Vegas Underdog'::text AS strategy_name,
    3 AS strategy_order,
    count(*) AS bets,
    sum(
        CASE
            WHEN enriched.vegas_dog_won THEN 1
            ELSE 0
        END) AS wins,
    round(sum(
        CASE
            WHEN enriched.vegas_dog_won THEN
            CASE
                WHEN enriched.vegas_dog_odds > 0 THEN enriched.vegas_dog_odds::double precision / 100.0::double precision
                ELSE 100.0::double precision / abs(enriched.vegas_dog_odds)::double precision
            END
            ELSE '-1.0'::numeric::double precision
        END)::numeric, 4)::double precision AS pnl
   FROM enriched
UNION ALL
 SELECT 'model_vs_vegas'::text AS strategy_key,
    'Model Pick vs Vegas'::text AS strategy_name,
    4 AS strategy_order,
    count(*) FILTER (WHERE NOT enriched.model_agrees_vegas) AS bets,
    sum(
        CASE
            WHEN NOT enriched.model_agrees_vegas AND enriched.model_won THEN 1
            ELSE 0
        END) AS wins,
    round(sum(
        CASE
            WHEN NOT enriched.model_agrees_vegas THEN
            CASE
                WHEN enriched.model_won THEN
                CASE
                    WHEN enriched.model_odds > 0 THEN enriched.model_odds::double precision / 100.0::double precision
                    ELSE 100.0::double precision / abs(enriched.model_odds)::double precision
                END
                ELSE '-1.0'::numeric::double precision
            END
            ELSE 0.0::double precision
        END)::numeric, 4)::double precision AS pnl
   FROM enriched
UNION ALL
 SELECT 'model_edge_5_15'::text AS strategy_key,
    'Model Edge 5–15% Over Vegas'::text AS strategy_name,
    5 AS strategy_order,
    count(*) FILTER (WHERE (enriched.model_prob_pick - enriched.vegas_implied_pick) >= 0.05::double precision AND (enriched.model_prob_pick - enriched.vegas_implied_pick) <= 0.15::double precision) AS bets,
    sum(
        CASE
            WHEN (enriched.model_prob_pick - enriched.vegas_implied_pick) >= 0.05::double precision AND (enriched.model_prob_pick - enriched.vegas_implied_pick) <= 0.15::double precision AND enriched.model_won THEN 1
            ELSE 0
        END) AS wins,
    round(sum(
        CASE
            WHEN (enriched.model_prob_pick - enriched.vegas_implied_pick) >= 0.05::double precision AND (enriched.model_prob_pick - enriched.vegas_implied_pick) <= 0.15::double precision THEN
            CASE
                WHEN enriched.model_won THEN
                CASE
                    WHEN enriched.model_odds > 0 THEN enriched.model_odds::double precision / 100.0::double precision
                    ELSE 100.0::double precision / abs(enriched.model_odds)::double precision
                END
                ELSE '-1.0'::numeric::double precision
            END
            ELSE 0.0::double precision
        END)::numeric, 4)::double precision AS pnl
   FROM enriched;
CREATE UNIQUE INDEX mv_betting_roi_strategy_key_idx ON mv_betting_roi (strategy_key);

CREATE MATERIALIZED VIEW mv_vegas_calibration AS
 WITH base AS (
         SELECT DISTINCT ON (scored_predictions.fight_id) scored_predictions.implied_prob_a,
            scored_predictions.actual_winner_id,
            scored_predictions.fighter_a_id
           FROM scored_predictions
          WHERE scored_predictions.implied_prob_a IS NOT NULL AND scored_predictions.actual_winner_id IS NOT NULL
          ORDER BY scored_predictions.fight_id, (
                CASE
                    WHEN scored_predictions.prediction_source = 'pre_fight_archive'::text THEN 0
                    ELSE 1
                END)
        ), bucketed AS (
         SELECT base.implied_prob_a,
            base.actual_winner_id,
            base.fighter_a_id,
                CASE
                    WHEN base.implied_prob_a > 0.5::double precision THEN base.implied_prob_a
                    ELSE 1::double precision - base.implied_prob_a
                END AS fav_implied,
                CASE
                    WHEN base.implied_prob_a > 0.5::double precision AND base.actual_winner_id::text = base.fighter_a_id::text OR base.implied_prob_a <= 0.5::double precision AND base.actual_winner_id::text <> base.fighter_a_id::text THEN true
                    ELSE false
                END AS fav_won
           FROM base
          WHERE base.implied_prob_a <> 0.5::double precision
        )
 SELECT
        CASE
            WHEN fav_implied >= 0.80::double precision THEN '80%+'::text
            WHEN fav_implied >= 0.70::double precision THEN '70–80%'::text
            WHEN fav_implied >= 0.60::double precision THEN '60–70%'::text
            ELSE '50–60%'::text
        END AS bucket,
        CASE
            WHEN fav_implied >= 0.80::double precision THEN 4
            WHEN fav_implied >= 0.70::double precision THEN 3
            WHEN fav_implied >= 0.60::double precision THEN 2
            ELSE 1
        END AS bucket_order,
    round(avg(fav_implied)::numeric, 3)::double precision AS avg_implied_prob,
    count(*)::integer AS fights,
    sum(
        CASE
            WHEN fav_won THEN 1
            ELSE 0
        END)::integer AS wins,
    round(avg(
        CASE
            WHEN fav_won THEN 1.0
            ELSE 0.0
        END), 4)::double precision AS actual_win_rate
   FROM bucketed
  GROUP BY (
        CASE
            WHEN fav_implied >= 0.80::double precision THEN '80%+'::text
            WHEN fav_implied >= 0.70::double precision THEN '70–80%'::text
            WHEN fav_implied >= 0.60::double precision THEN '60–70%'::text
            ELSE '50–60%'::text
        END), (
        CASE
            WHEN fav_implied >= 0.80::double precision THEN 4
            WHEN fav_implied >= 0.70::double precision THEN 3
            WHEN fav_implied >= 0.60::double precision THEN 2
            ELSE 1
        END)
  ORDER BY (
        CASE
            WHEN fav_implied >= 0.80::double precision THEN 4
            WHEN fav_implied >= 0.70::double precision THEN 3
            WHEN fav_implied >= 0.60::double precision THEN 2
            ELSE 1
        END);
CREATE UNIQUE INDEX mv_vegas_calibration_bucket_idx ON mv_vegas_calibration (bucket);

CREATE MATERIALIZED VIEW mv_upset_rates AS
 WITH best AS (
         SELECT DISTINCT ON (scored_predictions.fight_id) scored_predictions.fight_id,
            scored_predictions.weight_class,
            scored_predictions.is_upset,
            scored_predictions.is_correct
           FROM scored_predictions
          WHERE scored_predictions.is_correct IS NOT NULL AND scored_predictions.weight_class IS NOT NULL
          ORDER BY scored_predictions.fight_id, (
                CASE
                    WHEN scored_predictions.prediction_source = 'pre_fight_archive'::text THEN 0
                    ELSE 1
                END)
        )
 SELECT weight_class,
        CASE weight_class
            WHEN 'Heavyweight'::text THEN 1
            WHEN 'Light Heavyweight'::text THEN 2
            WHEN 'Middleweight'::text THEN 3
            WHEN 'Welterweight'::text THEN 4
            WHEN 'Lightweight'::text THEN 5
            WHEN 'Featherweight'::text THEN 6
            WHEN 'Bantamweight'::text THEN 7
            WHEN 'Flyweight'::text THEN 8
            WHEN 'Women''s Featherweight'::text THEN 9
            WHEN 'Women''s Bantamweight'::text THEN 10
            WHEN 'Women''s Flyweight'::text THEN 11
            WHEN 'Women''s Strawweight'::text THEN 12
            ELSE 99
        END AS weight_class_order,
    count(*)::integer AS total_fights,
    sum(
        CASE
            WHEN is_upset = true THEN 1
            ELSE 0
        END)::integer AS upset_count,
    round(sum(
        CASE
            WHEN is_upset = true THEN 1.0
            ELSE 0.0
        END) / NULLIF(count(*), 0)::numeric, 4)::double precision AS upset_rate
   FROM best
  GROUP BY weight_class
  ORDER BY (round(sum(
        CASE
            WHEN is_upset = true THEN 1.0
            ELSE 0.0
        END) / NULLIF(count(*), 0)::numeric, 4)::double precision) DESC;
CREATE UNIQUE INDEX mv_upset_rates_weight_class_idx ON mv_upset_rates (weight_class);

CREATE MATERIALIZED VIEW mv_roi_over_time AS
 WITH base AS (
         SELECT DISTINCT ON (pp.fight_id) pp.event_id,
            pp.event_name,
            pp.event_date,
            pp.is_correct,
                CASE
                    WHEN pp.win_prob_a >= 0.5::double precision THEN pp.odds_a
                    ELSE pp.odds_b
                END AS picked_odds
           FROM scored_predictions pp
          WHERE pp.implied_prob_a IS NOT NULL AND pp.actual_winner_id IS NOT NULL AND pp.is_correct IS NOT NULL AND pp.odds_a IS NOT NULL AND pp.odds_b IS NOT NULL
          ORDER BY pp.fight_id, (
                CASE
                    WHEN pp.prediction_source = 'pre_fight_archive'::text THEN 0
                    ELSE 1
                END)
        ), event_pnl AS (
         SELECT base.event_id,
            max(base.event_name) AS event_name,
            max(base.event_date) AS event_date,
            count(*)::integer AS bets,
            round(sum(
                CASE
                    WHEN base.is_correct THEN
                    CASE
                        WHEN base.picked_odds > 0 THEN base.picked_odds::double precision / 100.0::double precision
                        ELSE 100.0::double precision / abs(base.picked_odds)::double precision
                    END
                    ELSE '-1.0'::numeric::double precision
                END)::numeric, 4)::double precision AS pnl
           FROM base
          GROUP BY base.event_id
        )
 SELECT event_id,
    event_name,
    event_date,
    bets,
    pnl,
    round(sum(pnl) OVER (ORDER BY event_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::numeric, 4)::double precision AS cumulative_pnl,
    sum(bets) OVER (ORDER BY event_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::integer AS cumulative_bets
   FROM event_pnl
  ORDER BY event_date;
CREATE UNIQUE INDEX mv_roi_over_time_event_id_idx ON mv_roi_over_time (event_id);

COMMIT;

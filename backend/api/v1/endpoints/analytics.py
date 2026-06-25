"""api/v1/endpoints/analytics.py — Analytics endpoints.

Routes:
    GET /analytics/style-evolution              Finish rates by year (Product 2)
    GET /analytics/fighter-endurance/{id}       Round-by-round performance (Product 3)
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.analytics import (
    AgeByWeightClassPoint,
    BettingInsightsResponse,
    BettingRoiResponse,
    EnduranceRoundData,
    FighterEnduranceResponse,
    FighterOutputPoint,
    FighterStatsByWeightClass,
    PhysicalStatPoint,
    RoundDistributionPoint,
    RoiOverTimeRow,
    StrategyRoiRow,
    StyleEvolutionPoint,
    StyleEvolutionResponse,
    StyleStatsByWeightClassPoint,
    UpsetRateRow,
    VegasCalibrationRow,
    WeightClassYearPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/style-evolution",
    response_model=StyleEvolutionResponse,
    summary="Style evolution timeline",
)
def style_evolution(
    weight_class: str | None = Query(None, description="Filter by weight class"),
    db: Session = Depends(get_db),
):
    params: dict = {}
    # Queries 1–3 filter by weight_class; the materialized views encode the
    # all-divisions aggregate as weight_class IS NULL and per-division rows with
    # the actual weight class string.
    if weight_class:
        wc_clause_filtered = "WHERE weight_class = :weight_class"
        params["weight_class"] = weight_class
    else:
        wc_clause_filtered = "WHERE weight_class IS NULL"

    # ── Query 1: finish rates by year (mv_finish_rates) ──────────────────────────
    finish_rows = db.execute(text(f"""
        SELECT year, total_fights, ko_tko_rate, submission_rate, decision_rate
        FROM mv_finish_rates
        {wc_clause_filtered}
        ORDER BY year
    """), params).mappings().all()

    # ── Query 2: avg fighter outputs per fight by year (mv_fighter_output) ───────
    output_rows = db.execute(text(f"""
        SELECT year, total_fights, avg_sig_str_per_fight,
               avg_td_attempts_per_fight, avg_ctrl_seconds_per_fight
        FROM mv_fighter_output
        {wc_clause_filtered}
        ORDER BY year
    """), params).mappings().all()

    # ── Query 3: finish round distribution by year (mv_round_distribution) ───────
    round_rows = db.execute(text(f"""
        SELECT year, total_finishes, r1_pct, r2_pct, r3_pct, r4plus_pct
        FROM mv_round_distribution
        {wc_clause_filtered}
        ORDER BY year
    """), params).mappings().all()

    # ── Query 4: finish rates by weight class × year (mv_heatmap) ────────────────
    heatmap_rows = db.execute(text("""
        SELECT year, weight_class, total_fights,
               ko_tko_rate, submission_rate, decision_rate
        FROM mv_heatmap
        ORDER BY year, weight_class
    """)).mappings().all()

    # ── Query 5: avg height/reach by weight class × year (mv_physical_stats) ─────
    physical_rows = db.execute(text("""
        SELECT year, weight_class, avg_height_inches, avg_reach_inches, fighter_count
        FROM mv_physical_stats
        ORDER BY year, weight_class
    """)).mappings().all()

    # ── Query 6: avg fighter age by weight class × year (mv_age_data) ────────────
    age_rows = db.execute(text("""
        SELECT year, weight_class, avg_age, fighter_count
        FROM mv_age_data
        ORDER BY year, weight_class
    """)).mappings().all()

    # ── Query 7: career stats by weight class (mv_fighter_stats_by_wc) ───────────
    stats_rows = db.execute(text("""
        SELECT weight_class, avg_slpm, avg_str_acc, avg_sapm, avg_str_def,
               avg_td_avg, avg_td_acc, avg_td_def, avg_sub_avg, fighter_count
        FROM mv_fighter_stats_by_wc
        ORDER BY weight_class
    """)).mappings().all()

    # ── Query 8: per-year style metrics by weight class (mv_style_stats) ─────────
    style_rows = db.execute(text("""
        SELECT year, weight_class, avg_slpm, avg_str_acc, avg_sapm, avg_str_def,
               avg_td_per_fight, avg_td_acc, avg_td_def, avg_sub_per_fight,
               avg_ctrl_seconds, fight_count
        FROM mv_style_stats
        ORDER BY year, weight_class
    """)).mappings().all()

    current_year = date.today().year
    return StyleEvolutionResponse(
        data=[
            StyleEvolutionPoint(
                year=r["year"],
                ko_tko_rate=r["ko_tko_rate"] or 0.0,
                submission_rate=r["submission_rate"] or 0.0,
                decision_rate=r["decision_rate"] or 0.0,
                finish_rate=round((r["ko_tko_rate"] or 0.0) + (r["submission_rate"] or 0.0), 4),
                total_fights=r["total_fights"],
                is_partial_year=r["year"] == current_year,
                weight_class=weight_class,
            )
            for r in finish_rows
        ],
        fighter_outputs=[
            FighterOutputPoint(
                year=r["year"],
                avg_sig_str_per_fight=r["avg_sig_str_per_fight"] or 0.0,
                avg_td_attempts_per_fight=r["avg_td_attempts_per_fight"] or 0.0,
                avg_ctrl_seconds_per_fight=r["avg_ctrl_seconds_per_fight"] or 0.0,
                total_fights=r["total_fights"],
                is_partial_year=r["year"] == current_year,
            )
            for r in output_rows
        ],
        round_distribution=[
            RoundDistributionPoint(
                year=r["year"],
                r1_pct=r["r1_pct"] or 0.0,
                r2_pct=r["r2_pct"] or 0.0,
                r3_pct=r["r3_pct"] or 0.0,
                r4plus_pct=r["r4plus_pct"] or 0.0,
                total_finishes=r["total_finishes"],
                is_partial_year=r["year"] == current_year,
            )
            for r in round_rows
        ],
        heatmap_data=[
            WeightClassYearPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                finish_rate=round((r["ko_tko_rate"] or 0.0) + (r["submission_rate"] or 0.0), 4),
                ko_tko_rate=r["ko_tko_rate"] or 0.0,
                submission_rate=r["submission_rate"] or 0.0,
                decision_rate=r["decision_rate"] or 0.0,
                total_fights=r["total_fights"],
            )
            for r in heatmap_rows
        ],
        physical_stats=[
            PhysicalStatPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_height_inches=r["avg_height_inches"] or 0.0,
                avg_reach_inches=r["avg_reach_inches"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in physical_rows
        ],
        age_data=[
            AgeByWeightClassPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_age=r["avg_age"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in age_rows
        ],
        fighter_stats=[
            FighterStatsByWeightClass(
                weight_class=r["weight_class"],
                avg_slpm=r["avg_slpm"] or 0.0,
                avg_str_acc=r["avg_str_acc"] or 0.0,
                avg_sapm=r["avg_sapm"] or 0.0,
                avg_str_def=r["avg_str_def"] or 0.0,
                avg_td_avg=r["avg_td_avg"] or 0.0,
                avg_td_acc=r["avg_td_acc"] or 0.0,
                avg_td_def=r["avg_td_def"] or 0.0,
                avg_sub_avg=r["avg_sub_avg"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in stats_rows
        ],
        style_stats=[
            StyleStatsByWeightClassPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_slpm=r["avg_slpm"] or 0.0,
                avg_str_acc=r["avg_str_acc"] or 0.0,
                avg_sapm=r["avg_sapm"] or 0.0,
                avg_str_def=r["avg_str_def"] or 0.0,
                avg_td_per_fight=r["avg_td_per_fight"] or 0.0,
                avg_td_acc=r["avg_td_acc"] or 0.0,
                avg_td_def=r["avg_td_def"] or 0.0,
                avg_sub_per_fight=r["avg_sub_per_fight"] or 0.0,
                avg_ctrl_seconds=r["avg_ctrl_seconds"] or 0.0,
                fight_count=r["fight_count"],
            )
            for r in style_rows
        ],
        weight_class=weight_class,
    )


@router.get(
    "/betting-insights",
    response_model=BettingInsightsResponse,
    summary="Betting insights — strategy ROI, Vegas calibration, upset rates, ROI over time",
)
def betting_insights(db: Session = Depends(get_db)) -> BettingInsightsResponse:
    strategy_rows = db.execute(text("""
        SELECT strategy_key, strategy_name, strategy_order, bets, wins, pnl
        FROM mv_betting_roi
        ORDER BY strategy_order
    """)).mappings().all()

    calibration_rows = db.execute(text("""
        SELECT bucket, bucket_order, avg_implied_prob, fights, wins, actual_win_rate
        FROM mv_vegas_calibration
        ORDER BY bucket_order
    """)).mappings().all()

    upset_rows = db.execute(text("""
        SELECT weight_class, weight_class_order, total_fights, upset_count, upset_rate
        FROM mv_upset_rates
        ORDER BY upset_rate DESC
    """)).mappings().all()

    time_rows = db.execute(text("""
        SELECT event_id, event_name, event_date::text, bets, pnl, cumulative_pnl, cumulative_bets
        FROM mv_roi_over_time
        ORDER BY event_date
    """)).mappings().all()

    sample_size: int = db.execute(text("""
        SELECT COUNT(DISTINCT fight_id)
        FROM past_predictions
        WHERE implied_prob_a IS NOT NULL AND actual_winner_id IS NOT NULL
    """)).scalar() or 0

    def _roi(bets: int, pnl: float) -> float:
        return round(pnl / bets, 4) if bets else 0.0

    return BettingInsightsResponse(
        sample_size=sample_size,
        strategies=[
            StrategyRoiRow(
                strategy_key=r["strategy_key"],
                strategy_name=r["strategy_name"],
                strategy_order=r["strategy_order"],
                bets=int(r["bets"]),
                wins=int(r["wins"]),
                pnl=float(r["pnl"]),
                roi=_roi(int(r["bets"]), float(r["pnl"])),
            )
            for r in strategy_rows
        ],
        calibration=[
            VegasCalibrationRow(
                bucket=r["bucket"],
                bucket_order=int(r["bucket_order"]),
                avg_implied_prob=float(r["avg_implied_prob"]),
                fights=int(r["fights"]),
                wins=int(r["wins"]),
                actual_win_rate=float(r["actual_win_rate"]),
            )
            for r in calibration_rows
        ],
        upset_rates=[
            UpsetRateRow(
                weight_class=r["weight_class"],
                weight_class_order=int(r["weight_class_order"]),
                total_fights=int(r["total_fights"]),
                upset_count=int(r["upset_count"]),
                upset_rate=float(r["upset_rate"]),
            )
            for r in upset_rows
        ],
        roi_over_time=[
            RoiOverTimeRow(
                event_id=r["event_id"],
                event_name=r["event_name"],
                event_date=r["event_date"],
                bets=int(r["bets"]),
                pnl=float(r["pnl"]),
                cumulative_pnl=float(r["cumulative_pnl"]),
                cumulative_bets=int(r["cumulative_bets"]),
            )
            for r in time_rows
        ],
    )


@router.get(
    "/betting-roi",
    response_model=BettingRoiResponse,
    summary="Live strategy builder — parameterized ROI query over past_predictions",
)
def betting_roi(
    side: str = Query("model_pick", description="model_pick | vegas_fav | vegas_dog"),
    conviction_min: float | None = Query(None, ge=0.0, le=0.5),
    conviction_max: float | None = Query(None, ge=0.0, le=0.5),
    weight_class: str | None = Query(None),
    edge_min: float | None = Query(None, ge=-1.0, le=1.0),
    edge_max: float | None = Query(None, ge=-1.0, le=1.0),
    upset_filter: str = Query("all", description="all | upsets_only | non_upsets"),
    title_filter: str = Query("all", description="all | title | non_title"),
    db: Session = Depends(get_db),
) -> BettingRoiResponse:
    if side not in ("model_pick", "vegas_fav", "vegas_dog"):
        side = "model_pick"
    if upset_filter not in ("all", "upsets_only", "non_upsets"):
        upset_filter = "all"
    if title_filter not in ("all", "title", "non_title"):
        title_filter = "all"

    if side == "model_pick":
        bet_odds_expr   = "CASE WHEN pp.win_prob_a >= 0.5 THEN pp.odds_a ELSE pp.odds_b END"
        bet_won_expr    = "pp.is_correct"
        model_prob_expr = "CASE WHEN pp.win_prob_a >= 0.5 THEN pp.win_prob_a ELSE pp.win_prob_b END"
        vegas_prob_expr = "CASE WHEN pp.win_prob_a >= 0.5 THEN pp.implied_prob_a ELSE pp.implied_prob_b END"
    elif side == "vegas_fav":
        bet_odds_expr   = "CASE WHEN pp.implied_prob_a > 0.5 THEN pp.odds_a ELSE pp.odds_b END"
        bet_won_expr    = """(
            (pp.implied_prob_a > 0.5 AND pp.actual_winner_id = pp.fighter_a_id)
            OR (pp.implied_prob_a <= 0.5 AND pp.actual_winner_id != pp.fighter_a_id)
        )"""
        model_prob_expr = "CASE WHEN pp.implied_prob_a > 0.5 THEN pp.win_prob_a ELSE pp.win_prob_b END"
        vegas_prob_expr = "CASE WHEN pp.implied_prob_a > 0.5 THEN pp.implied_prob_a ELSE pp.implied_prob_b END"
    else:  # vegas_dog
        bet_odds_expr   = "CASE WHEN pp.implied_prob_a <= 0.5 THEN pp.odds_a ELSE pp.odds_b END"
        bet_won_expr    = """(
            (pp.implied_prob_a <= 0.5 AND pp.actual_winner_id = pp.fighter_a_id)
            OR (pp.implied_prob_a > 0.5 AND pp.actual_winner_id != pp.fighter_a_id)
        )"""
        model_prob_expr = "CASE WHEN pp.implied_prob_a <= 0.5 THEN pp.win_prob_a ELSE pp.win_prob_b END"
        vegas_prob_expr = "CASE WHEN pp.implied_prob_a <= 0.5 THEN pp.implied_prob_a ELSE pp.implied_prob_b END"

    params: dict = {
        "conviction_min": conviction_min,
        "conviction_max": conviction_max,
        "weight_class":   weight_class,
        "edge_min":       edge_min,
        "edge_max":       edge_max,
    }

    title_join = ""
    title_clause = ""
    if title_filter != "all":
        title_join   = "LEFT JOIN fight_results fr ON fr.fight_id = pp.fight_id"
        title_clause = f"AND fr.is_title_fight = {'TRUE' if title_filter == 'title' else 'FALSE'}"

    row = db.execute(text(f"""
        WITH base AS (
            SELECT DISTINCT ON (pp.fight_id)
                pp.fight_id,
                pp.confidence,
                pp.is_upset,
                pp.weight_class,
                ({bet_odds_expr})   AS bet_odds,
                ({bet_won_expr})    AS bet_won,
                ({model_prob_expr}) AS model_prob,
                ({vegas_prob_expr}) AS vegas_prob
            FROM past_predictions pp
            {title_join}
            WHERE pp.implied_prob_a IS NOT NULL
              AND pp.actual_winner_id IS NOT NULL
              AND pp.is_correct IS NOT NULL
              AND pp.odds_a IS NOT NULL
              AND pp.odds_b IS NOT NULL
              {title_clause}
            ORDER BY pp.fight_id,
                     CASE WHEN pp.prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT
            COUNT(*)::int AS bets,
            SUM(CASE WHEN bet_won THEN 1 ELSE 0 END)::int AS wins,
            ROUND(SUM(
                CASE WHEN bet_won
                    THEN CASE WHEN bet_odds > 0 THEN bet_odds::float / 100.0 ELSE 100.0 / ABS(bet_odds)::float END
                    ELSE -1.0
                END
            )::numeric, 4)::float AS pnl
        FROM base
        WHERE (:conviction_min IS NULL OR confidence >= :conviction_min)
          AND (:conviction_max IS NULL OR confidence < :conviction_max)
          AND (:weight_class IS NULL OR weight_class = :weight_class)
          AND (:edge_min IS NULL OR (model_prob - vegas_prob) >= :edge_min)
          AND (:edge_max IS NULL OR (model_prob - vegas_prob) < :edge_max)
          AND (
              '{upset_filter}' = 'all'
              OR ('{upset_filter}' = 'upsets_only' AND is_upset = TRUE)
              OR ('{upset_filter}' = 'non_upsets' AND (is_upset = FALSE OR is_upset IS NULL))
          )
    """), params).mappings().first()

    bets = int(row["bets"] or 0)
    wins = int(row["wins"] or 0)
    pnl  = float(row["pnl"] or 0.0)
    roi  = round(pnl / bets, 4) if bets else 0.0

    return BettingRoiResponse(bets=bets, wins=wins, pnl=pnl, roi=roi)


@router.get(
    "/fighter-endurance/{fighter_id}",
    response_model=FighterEnduranceResponse,
    summary="Fighter endurance profile",
)
def fighter_endurance(fighter_id: str, db: Session = Depends(get_db)):
    fighter = db.execute(text("""
        SELECT
            fd.id,
            fd."FIRST" || ' ' || fd."LAST" AS full_name
        FROM fighter_details fd
        WHERE fd.id = :fighter_id
    """), {"fighter_id": fighter_id}).mappings().first()

    if fighter is None:
        raise HTTPException(status_code=404, detail=f"Fighter '{fighter_id}' not found")

    rows = db.execute(text("""
        SELECT
            "ROUND"::int                           AS round,
            ROUND(AVG(sig_str_landed)::numeric, 2)::float
                                                   AS avg_sig_str_landed,
            ROUND(
                AVG(
                    CASE WHEN sig_str_attempted > 0
                         THEN sig_str_landed::float / sig_str_attempted
                         ELSE NULL END
                )::numeric, 4
            )::float                               AS avg_sig_str_pct,
            ROUND(AVG(ctrl_seconds)::numeric, 2)::float
                                                   AS avg_ctrl_seconds,
            ROUND(AVG(kd_int)::numeric, 4)::float  AS avg_kd,
            COUNT(*)::int                          AS fight_count
        FROM fight_stats
        WHERE fighter_id = :fighter_id
          AND "ROUND" ~ '^[0-9]+$'
        GROUP BY "ROUND"::int
        ORDER BY "ROUND"::int
    """), {"fighter_id": fighter_id}).mappings().all()

    note = None
    if not rows:
        note = "No detailed round-by-round stats available (pre-2015 career or no fight_stats data)"

    return FighterEnduranceResponse(
        fighter_id=fighter_id,
        fighter_name=fighter["full_name"],
        rounds=[EnduranceRoundData(**dict(r)) for r in rows],
        note=note,
    )

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
    BettingFightRow,
    BettingFightsResponse,
    BettingInsightsResponse,
    BettingRoiResponse,
    BettingUpsetsResponse,
    EnduranceRoundData,
    FighterEnduranceResponse,
    FighterOutputPoint,
    FighterStatsByWeightClass,
    PhysicalStatPoint,
    RoiEventEntry,
    RoiOverTimeResponse,
    RoiOverTimeRow,
    RoundDistributionPoint,
    StrategyRoiRow,
    StyleEvolutionPoint,
    StyleEvolutionResponse,
    StyleStatsByWeightClassPoint,
    UpsetFightCard,
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

    avg_edge: float = float(db.execute(text("""
        SELECT AVG(
            CASE WHEN win_prob_a >= 0.5
                THEN win_prob_a - implied_prob_a
                ELSE win_prob_b - implied_prob_b
            END
        )
        FROM past_predictions
        WHERE implied_prob_a IS NOT NULL
          AND actual_winner_id IS NOT NULL
          AND (
            CASE WHEN win_prob_a >= 0.5
                THEN win_prob_a - implied_prob_a
                ELSE win_prob_b - implied_prob_b
            END
          ) BETWEEN 0.05 AND 0.15
    """)).scalar() or 0.0)

    # ── Extra strategies computed on-the-fly from raw past_predictions ───────────
    raw_fights = db.execute(text("""
        SELECT DISTINCT ON (fight_id)
            fighter_a_id, actual_winner_id,
            win_prob_a, win_prob_b,
            implied_prob_a, implied_prob_b,
            odds_a, odds_b,
            confidence, is_correct
        FROM past_predictions
        WHERE implied_prob_a IS NOT NULL
          AND actual_winner_id IS NOT NULL
          AND odds_a IS NOT NULL AND odds_b IS NOT NULL
        ORDER BY fight_id,
                 CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
    """)).mappings().all()

    def _payout(odds: int | None) -> float:
        if not odds: return 0.0
        return odds / 100.0 if odds > 0 else 100.0 / abs(odds)

    def _model_pl(r: dict) -> float:
        pick_odds = r["odds_a"] if (r["win_prob_a"] or 0) >= 0.5 else r["odds_b"]
        return _payout(pick_odds) if r["is_correct"] else -1.0

    def _model_edge(r: dict) -> float:
        if (r["win_prob_a"] or 0) >= 0.5:
            return float(r["win_prob_a"] or 0) - float(r["implied_prob_a"] or 0)
        return float(r["win_prob_b"] or 0) - float(r["implied_prob_b"] or 0)

    def _is_disagree(r: dict) -> bool:
        return ((r["win_prob_a"] or 0) >= 0.5) != ((r["implied_prob_a"] or 0) > (r["implied_prob_b"] or 0))

    def _extra_strategy(rows: list, key: str, name: str, order: int) -> StrategyRoiRow:
        bets = len(rows)
        wins = sum(1 for r in rows if r["is_correct"])
        pnl  = round(sum(_model_pl(r) for r in rows), 4)
        roi  = round(pnl / bets, 4) if bets else 0.0
        return StrategyRoiRow(strategy_key=key, strategy_name=name, strategy_order=order,
                              bets=bets, wins=wins, pnl=pnl, roi=roi)

    disagree_rows   = [r for r in raw_fights if _is_disagree(r)]
    conv20_rows     = [r for r in raw_fights if (r["confidence"] or 0) >= 0.20]
    edge_conv_rows  = [r for r in raw_fights
                       if (r["confidence"] or 0) >= 0.20 and 0.05 <= _model_edge(r) <= 0.15]

    extra_strategies = [
        _extra_strategy(disagree_rows,  "model_disagree",     "Model Pick on Vegas Disagreements", 5),
        _extra_strategy(conv20_rows,    "high_conviction_20", "High Conviction 20pp+",              6),
        _extra_strategy(edge_conv_rows, "edge_5_15_conv_20",  "Edge 5-15pp + Conviction 20pp+",     7),
    ]

    # ── Upset rate at 20pp threshold (full past_predictions, not Vegas-filtered) ─
    upset_stats = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN NOT is_correct AND confidence >= 0.20 THEN 1 ELSE 0 END) AS upset_count
        FROM (
            SELECT DISTINCT ON (fight_id) is_correct, confidence
            FROM past_predictions
            WHERE actual_winner_id IS NOT NULL
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        ) deduped
    """)).mappings().first()

    upset_total    = int(upset_stats["total"] or 0)
    upset_count_20 = int(upset_stats["upset_count"] or 0)
    upset_rate_20  = round(upset_count_20 / upset_total, 4) if upset_total else 0.0

    # Canonical display names — avoids encoding issues with stored MV strings
    _strategy_names = {
        "model_pick":      "Always Bet Model Pick",
        "vegas_fav":       "Always Bet Vegas Favorite",
        "vegas_dog":       "Always Bet Vegas Underdog",
        "model_edge_5_15": "Model Edge 5-15% Over Vegas",
    }

    def _roi(bets: int, pnl: float) -> float:
        return round(pnl / bets, 4) if bets else 0.0

    return BettingInsightsResponse(
        sample_size=sample_size,
        avg_edge_qualifying=round(avg_edge, 4),
        upset_count_20pp=upset_count_20,
        upset_rate_20pp=upset_rate_20,
        strategies=[
            StrategyRoiRow(
                strategy_key=r["strategy_key"],
                strategy_name=_strategy_names.get(r["strategy_key"], r["strategy_name"]),
                strategy_order=r["strategy_order"],
                bets=int(r["bets"]),
                wins=int(r["wins"]),
                pnl=float(r["pnl"]),
                roi=_roi(int(r["bets"]), float(r["pnl"])),
            )
            for r in strategy_rows
        ] + extra_strategies,
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
    "/betting-insights/fights",
    response_model=BettingFightsResponse,
    summary="Per-fight payload for client-side filtering in the Overview tab (~132 rows)",
)
def betting_insights_fights(db: Session = Depends(get_db)) -> BettingFightsResponse:
    rows = db.execute(text("""
        SELECT DISTINCT ON (pp.fight_id)
            pp.fight_id,
            pp.event_id,
            pp.event_name,
            pp.event_date::text            AS event_date,
            pp.weight_class,
            pp.fighter_a_id,
            pp.fighter_b_id,
            pp.fighter_a_name,
            pp.fighter_b_name,
            pp.win_prob_a,
            pp.win_prob_b,
            pp.implied_prob_a,
            pp.implied_prob_b,
            pp.odds_a,
            pp.odds_b,
            pp.is_correct,
            pp.confidence,
            pp.actual_winner_id,
            pp.actual_method,
            COALESCE(fr.is_title_fight, FALSE) AS is_title,
            ta.dob_date AS dob_a,
            tb.dob_date AS dob_b
        FROM past_predictions pp
        LEFT JOIN fight_results fr ON fr.fight_id = pp.fight_id
        LEFT JOIN fighter_tott ta ON ta.fighter_id = pp.fighter_a_id
        LEFT JOIN fighter_tott tb ON tb.fighter_id = pp.fighter_b_id
        WHERE pp.implied_prob_a IS NOT NULL
          AND pp.actual_winner_id IS NOT NULL
          AND pp.odds_a IS NOT NULL
          AND pp.odds_b IS NOT NULL
        ORDER BY pp.fight_id,
                 CASE WHEN pp.prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
    """)).mappings().all()

    def _payout_f(odds: int | None) -> float:
        if not odds: return 0.0
        return odds / 100.0 if odds > 0 else 100.0 / abs(odds)

    def _pl(won: bool, payout: float) -> float:
        return payout if won else -1.0

    fights: list[BettingFightRow] = []
    for r in rows:
        wa = float(r["win_prob_a"] or 0.5)
        wb = float(r["win_prob_b"] or 0.5)
        ia = float(r["implied_prob_a"] or 0.5)
        ib = float(r["implied_prob_b"] or 0.5)
        oa = int(r["odds_a"]) if r["odds_a"] is not None else None
        ob = int(r["odds_b"]) if r["odds_b"] is not None else None

        is_pick_a = wa >= 0.5
        pick      = r["fighter_a_name"] if is_pick_a else r["fighter_b_name"]
        opponent  = r["fighter_b_name"] if is_pick_a else r["fighter_a_name"]
        pick_prob = wa if is_pick_a else wb
        opp_prob  = wb if is_pick_a else wa
        pick_imp  = ia if is_pick_a else ib
        model_odds = oa if is_pick_a else ob

        fav_is_a  = ia > ib
        fav_odds  = oa if fav_is_a else ob
        dog_odds  = ob if fav_is_a else oa

        winner_is_a  = r["actual_winner_id"] == r["fighter_a_id"]
        model_won    = bool(r["is_correct"])
        fav_won      = winner_is_a == fav_is_a
        dog_won      = not fav_won
        winner_name  = r["fighter_a_name"] if winner_is_a else r["fighter_b_name"]

        # Younger-fighter baseline: later DOB = younger. Undefined when either
        # DOB is missing or the two fighters share a birthdate (no younger one).
        dob_a, dob_b = r["dob_a"], r["dob_b"]
        pl_younger = age_diff = younger_name = None
        if dob_a is not None and dob_b is not None and dob_a != dob_b:
            age_diff      = round(abs((dob_a - dob_b).days) / 365.25, 1)
            younger_is_a  = dob_a > dob_b
            younger_odds  = oa if younger_is_a else ob
            younger_won   = winner_is_a == younger_is_a
            younger_name  = r["fighter_a_name"] if younger_is_a else r["fighter_b_name"]
            pl_younger    = _pl(younger_won, _payout_f(younger_odds))

        fights.append(BettingFightRow(
            fight_id=r["fight_id"],
            event_id=r["event_id"],
            event_name=r["event_name"],
            event_date=r["event_date"],
            weight_class=r["weight_class"],
            is_title=bool(r["is_title"]),
            fighter_a_name=r["fighter_a_name"],
            fighter_b_name=r["fighter_b_name"],
            win_prob_a=wa,
            win_prob_b=wb,
            pick=pick,
            opponent=opponent,
            pick_prob=round(pick_prob, 4),
            opp_prob=round(opp_prob, 4),
            conviction_pp=round((pick_prob - 0.5) * 100, 1),
            edge_pp=round((pick_prob - pick_imp) * 100, 1),
            vegas_implied_pct=round(pick_imp * 100, 1),
            model_pick_odds=model_odds,
            is_correct=model_won,
            actual_winner_name=winner_name,
            result_method=r["actual_method"],
            pl_model=_pl(model_won,  _payout_f(model_odds)),
            pl_fav  =_pl(fav_won,   _payout_f(fav_odds)),
            pl_dog  =_pl(dog_won,   _payout_f(dog_odds)),
            pl_younger=pl_younger,
            age_diff=age_diff,
            younger_name=younger_name,
        ))

    return BettingFightsResponse(fights=fights, total=len(fights))


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
    "/roi-over-time",
    response_model=RoiOverTimeResponse,
    summary="Per-event P&L for a given strategy (client computes cumulative + time slice)",
)
def roi_over_time(
    strategy: str = Query("model_pick", description="model_pick | vegas_fav | vegas_dog | model_edge_5_15"),
    db: Session = Depends(get_db),
) -> RoiOverTimeResponse:
    if strategy not in ("model_pick", "vegas_fav", "vegas_dog", "model_edge_5_15"):
        strategy = "model_pick"

    if strategy == "model_pick":
        bet_odds_expr = "CASE WHEN win_prob_a >= 0.5 THEN odds_a ELSE odds_b END"
        bet_won_expr  = "is_correct"
        extra_filter  = ""
    elif strategy == "vegas_fav":
        bet_odds_expr = "CASE WHEN implied_prob_a > 0.5 THEN odds_a ELSE odds_b END"
        bet_won_expr  = """(
            (implied_prob_a > 0.5 AND actual_winner_id = fighter_a_id)
            OR (implied_prob_a <= 0.5 AND actual_winner_id != fighter_a_id)
        )"""
        extra_filter  = ""
    elif strategy == "vegas_dog":
        bet_odds_expr = "CASE WHEN implied_prob_a <= 0.5 THEN odds_a ELSE odds_b END"
        bet_won_expr  = """(
            (implied_prob_a <= 0.5 AND actual_winner_id = fighter_a_id)
            OR (implied_prob_a > 0.5 AND actual_winner_id != fighter_a_id)
        )"""
        extra_filter  = ""
    else:  # model_edge_5_15
        bet_odds_expr = "CASE WHEN win_prob_a >= 0.5 THEN odds_a ELSE odds_b END"
        bet_won_expr  = "is_correct"
        extra_filter  = """AND (
            CASE WHEN win_prob_a >= 0.5
                THEN win_prob_a - implied_prob_a
                ELSE win_prob_b - implied_prob_b
            END
        ) BETWEEN 0.05 AND 0.15"""

    rows = db.execute(text(f"""
        WITH base AS (
            SELECT DISTINCT ON (fight_id)
                event_id,
                event_name,
                event_date,
                ({bet_odds_expr}) AS bet_odds,
                ({bet_won_expr})  AS bet_won
            FROM past_predictions
            WHERE implied_prob_a IS NOT NULL
              AND actual_winner_id IS NOT NULL
              AND is_correct IS NOT NULL
              AND odds_a IS NOT NULL
              AND odds_b IS NOT NULL
              {extra_filter}
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT
            event_id,
            MAX(event_name)  AS event_name,
            MAX(event_date)::text  AS event_date,
            COUNT(*)::int    AS bets,
            ROUND(SUM(
                CASE WHEN bet_won
                    THEN CASE WHEN bet_odds > 0 THEN bet_odds::float/100.0 ELSE 100.0/ABS(bet_odds)::float END
                    ELSE -1.0
                END
            )::numeric, 4)::float AS pnl
        FROM base
        GROUP BY event_id
        ORDER BY MAX(event_date)
    """)).mappings().all()

    return RoiOverTimeResponse(
        strategy=strategy,
        events=[
            RoiEventEntry(
                event_id=r["event_id"],
                event_name=r["event_name"],
                event_date=r["event_date"],
                bets=int(r["bets"]),
                pnl=float(r["pnl"]),
            )
            for r in rows
        ],
    )


@router.get(
    "/betting-upsets",
    response_model=BettingUpsetsResponse,
    summary="Individual upset fight cards — model high-conviction wrong",
)
def betting_upsets(
    weight_class: str | None = Query(None),
    conviction_min: float = Query(0.20, ge=0.0, le=0.5),
    db: Session = Depends(get_db),
) -> BettingUpsetsResponse:
    rows = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (pp.fight_id)
                pp.fight_id,
                pp.event_id,
                pp.event_name,
                pp.event_date::text            AS event_date,
                pp.weight_class,
                pp.fighter_a_name,
                pp.fighter_b_name,
                pp.fighter_a_id,
                pp.actual_winner_id,
                pp.confidence,
                pp.win_prob_a,
                pp.win_prob_b,
                pp.odds_a,
                pp.odds_b,
                fr."METHOD"                    AS method,
                CASE WHEN pp.win_prob_a >= 0.5 THEN pp.fighter_a_name ELSE pp.fighter_b_name END
                    AS model_pick_name,
                CASE WHEN pp.actual_winner_id = pp.fighter_a_id THEN pp.fighter_a_name ELSE pp.fighter_b_name END
                    AS winner_name,
                CASE WHEN pp.win_prob_a >= 0.5 THEN pp.odds_a ELSE pp.odds_b END
                    AS model_pick_odds
            FROM past_predictions pp
            LEFT JOIN fight_results fr ON fr.fight_id = pp.fight_id
            WHERE NOT pp.is_correct
              AND pp.confidence >= :conviction_min
              AND pp.actual_winner_id IS NOT NULL
              AND (:weight_class IS NULL OR pp.weight_class = :weight_class)
            ORDER BY pp.fight_id,
                     CASE WHEN pp.prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT * FROM best ORDER BY event_date DESC NULLS LAST
    """), {"conviction_min": conviction_min, "weight_class": weight_class}).mappings().all()

    cards = [
        UpsetFightCard(
            fight_id=r["fight_id"],
            event_id=r["event_id"],
            event_name=r["event_name"],
            event_date=r["event_date"],
            weight_class=r["weight_class"],
            fighter_a_name=r["fighter_a_name"],
            fighter_b_name=r["fighter_b_name"],
            model_pick_name=r["model_pick_name"],
            winner_name=r["winner_name"],
            method=r["method"],
            conviction=float(r["confidence"]),
            model_pick_odds=int(r["model_pick_odds"]) if r["model_pick_odds"] is not None else None,
        )
        for r in rows
    ]
    return BettingUpsetsResponse(fights=cards, total=len(cards))


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

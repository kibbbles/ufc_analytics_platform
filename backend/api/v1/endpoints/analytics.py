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
    EnduranceRoundData,
    FighterEnduranceResponse,
    FighterOutputPoint,
    FighterStatsByWeightClass,
    PhysicalStatPoint,
    RoundDistributionPoint,
    StyleEvolutionPoint,
    StyleEvolutionResponse,
    StyleStatsByWeightClassPoint,
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

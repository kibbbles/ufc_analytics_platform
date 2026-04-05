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
    EnduranceRoundData,
    FighterEnduranceResponse,
    FighterOutputPoint,
    StyleEvolutionPoint,
    StyleEvolutionResponse,
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
    wc_filter_fr = ""
    wc_filter_fs = ""
    if weight_class:
        wc_filter_fr = "AND fr.weight_class = :weight_class"
        wc_filter_fs = "AND fr.weight_class = :weight_class"
        params["weight_class"] = weight_class

    rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            COUNT(*)                               AS total_fights,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS ko_tko_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS submission_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS decision_rate
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
          AND EXTRACT(YEAR FROM ed.date_proper) >= 2001
          {wc_filter_fr}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

    # ── Second query: avg fighter outputs per fight by year (fight_stats, 2015+) ──
    output_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int          AS year,
            COUNT(DISTINCT per_fighter.fight_id)            AS total_fights,
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
          {wc_filter_fs}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

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
            for r in rows
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
        weight_class=weight_class,
    )


@router.get(
    "/fighter-endurance/{fighter_id}",
    response_model=FighterEnduranceResponse,
    summary="Fighter endurance profile",
)
def fighter_endurance(fighter_id: str, db: Session = Depends(get_db)):
    # Verify fighter exists
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

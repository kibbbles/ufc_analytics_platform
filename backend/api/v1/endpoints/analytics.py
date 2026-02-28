"""api/v1/endpoints/analytics.py — Analytics endpoints.

Routes:
    GET /analytics/style-evolution              Finish rates by year (Product 2)
    GET /analytics/fighter-endurance/{id}       Round-by-round performance (Product 3)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.analytics import (
    EnduranceRoundData,
    FighterEnduranceResponse,
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
    wc_filter = ""
    if weight_class:
        wc_filter = "AND fr.weight_class = :weight_class"
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
          {wc_filter}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

    return StyleEvolutionResponse(
        data=[
            StyleEvolutionPoint(
                year=r["year"],
                ko_tko_rate=r["ko_tko_rate"] or 0.0,
                submission_rate=r["submission_rate"] or 0.0,
                decision_rate=r["decision_rate"] or 0.0,
                total_fights=r["total_fights"],
                weight_class=weight_class,
            )
            for r in rows
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

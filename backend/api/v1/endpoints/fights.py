"""api/v1/endpoints/fights.py — Fight endpoints.

Routes:
    GET /fights             Paginated list; optional filters: event_id, fighter_id,
                            weight_class, method
    GET /fights/{id}        Single fight + round-by-round stats for both fighters
"""

from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.fight import FightListItem, FightListResponse, FightResponse, FightStatsResponse
from schemas.shared import PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=FightListResponse, summary="List fights")
def list_fights(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_id: str | None = Query(None, description="Filter by event ID"),
    fighter_id: str | None = Query(None, description="Filter to fights involving a fighter"),
    weight_class: str | None = Query(None, description="Filter by weight class"),
    method: str | None = Query(None, description="Filter by finish method (partial match)"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    conditions: list[str] = []
    params: dict = {"limit": page_size, "offset": offset}

    if event_id:
        conditions.append("fd.event_id = :event_id")
        params["event_id"] = event_id
    if fighter_id:
        conditions.append(
            "(fd.fighter_a_id = :fighter_id OR fd.fighter_b_id = :fighter_id)"
        )
        params["fighter_id"] = fighter_id
    if weight_class:
        conditions.append("fr.weight_class = :weight_class")
        params["weight_class"] = weight_class
    if method:
        conditions.append('fr."METHOD" ILIKE :method')
        params["method"] = f"%{method}%"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = db.execute(
        text(f"""
            SELECT COUNT(*)
            FROM fight_details fd
            LEFT JOIN fight_results fr ON fr.fight_id = fd.id
            {where}
        """),
        params,
    ).scalar() or 0

    rows = db.execute(text(f"""
        SELECT
            fd.id,
            fd.event_id,
            fd."BOUT"          AS bout,
            fd.fighter_a_id,
            fd.fighter_b_id,
            CASE WHEN fr.is_winner = TRUE THEN fr.fighter_id ELSE NULL END AS winner_id,
            fr.weight_class,
            fr."METHOD"        AS method,
            fr."ROUND"::int    AS round,
            fr."TIME"          AS time,
            fr.is_title_fight,
            fr.is_interim_title,
            fr.is_championship_rounds
        FROM fight_details fd
        LEFT JOIN fight_results fr ON fr.fight_id = fd.id
        {where}
        ORDER BY fd.event_id DESC, fd.id
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    return FightListResponse(
        data=[FightListItem(**dict(r)) for r in rows],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if total else 0,
        ),
    )


@router.get("/{fight_id}", response_model=FightResponse, summary="Get fight")
def get_fight(fight_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT
            fd.id,
            fd.event_id,
            fd."BOUT"                    AS bout,
            fd.fighter_a_id,
            fd.fighter_b_id,
            CASE WHEN fr.is_winner = TRUE THEN fr.fighter_id ELSE NULL END AS winner_id,
            fr.weight_class,
            fr."METHOD"                  AS method,
            fr."ROUND"::int              AS round,
            fr."TIME"                    AS time,
            fr.is_title_fight,
            fr.is_interim_title,
            fr.is_championship_rounds,
            fr.total_fight_time_seconds
        FROM fight_details fd
        LEFT JOIN fight_results fr ON fr.fight_id = fd.id
        WHERE fd.id = :fight_id
    """), {"fight_id": fight_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Fight '{fight_id}' not found")

    stats_rows = db.execute(text("""
        SELECT
            fighter_id,
            "ROUND"::int               AS round,
            kd_int,
            sig_str_landed,
            sig_str_attempted,
            sig_str_pct,
            total_str_landed,
            total_str_attempted,
            td_landed,
            td_attempted,
            td_pct,
            ctrl_seconds,
            head_landed,
            head_attempted,
            body_landed,
            body_attempted,
            leg_landed,
            leg_attempted,
            distance_landed,
            distance_attempted,
            clinch_landed,
            clinch_attempted,
            ground_landed,
            ground_attempted
        FROM fight_stats
        WHERE fight_id = :fight_id
          AND "ROUND" ~ '^[0-9]+$'
        ORDER BY fighter_id, "ROUND"::int
    """), {"fight_id": fight_id}).mappings().all()

    return FightResponse(
        **dict(row),
        stats=[FightStatsResponse(**dict(s)) for s in stats_rows],
    )

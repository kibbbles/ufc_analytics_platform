"""api/v1/endpoints/fighters.py — Fighter endpoints.

Routes:
    GET /fighters           Paginated list; optional filters: search, weight_class
    GET /fighters/{id}      Full fighter profile + tale of the tape + record
"""

from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.fighter import FighterListItem, FighterListResponse, FighterResponse
from schemas.shared import PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter()

# Inline subquery that resolves each fighter's most recent weight class.
# Used in both the COUNT and data queries so weight_class filtering works correctly.
_LATEST_WC = """(
    SELECT DISTINCT ON (fighter_id)
        fighter_id,
        weight_class
    FROM (
        SELECT
            fdet.fighter_a_id  AS fighter_id,
            fr.weight_class,
            ed.date_proper
        FROM fight_details fdet
        JOIN fight_results  fr ON fr.fight_id = fdet.id
        JOIN event_details  ed ON ed.id        = fr.event_id
        WHERE fr.weight_class IS NOT NULL
          AND fdet.fighter_a_id IS NOT NULL
        UNION ALL
        SELECT
            fdet.fighter_b_id  AS fighter_id,
            fr.weight_class,
            ed.date_proper
        FROM fight_details fdet
        JOIN fight_results  fr ON fr.fight_id = fdet.id
        JOIN event_details  ed ON ed.id        = fr.event_id
        WHERE fr.weight_class IS NOT NULL
          AND fdet.fighter_b_id IS NOT NULL
    ) all_wc
    ORDER BY fighter_id, date_proper DESC
) lwc"""


@router.get("", response_model=FighterListResponse, summary="List fighters")
def list_fighters(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    search: str | None = Query(None, description="Partial name match"),
    weight_class: str | None = Query(None, description="Filter by most recent weight class"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    params: dict = {"limit": page_size, "offset": offset}
    conditions: list[str] = []

    if search:
        conditions.append('LOWER(fd."FIRST" || \' \' || fd."LAST") LIKE LOWER(:search)')
        params["search"] = f"%{search}%"
    if weight_class:
        conditions.append("lwc.weight_class = :weight_class")
        params["weight_class"] = weight_class

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = db.execute(text(f"""
        SELECT COUNT(*)
        FROM fighter_details fd
        LEFT JOIN {_LATEST_WC} ON lwc.fighter_id = fd.id
        {where}
    """), params).scalar() or 0

    rows = db.execute(text(f"""
        WITH wins AS (
            SELECT fighter_id, COUNT(*) AS n
            FROM fight_results
            WHERE is_winner = TRUE
            GROUP BY fighter_id
        ),
        losses AS (
            SELECT opponent_id AS fighter_id, COUNT(*) AS n
            FROM fight_results
            WHERE is_winner = TRUE
            GROUP BY opponent_id
        )
        SELECT
            fd.id,
            fd."FIRST"    AS first_name,
            fd."LAST"     AS last_name,
            fd."NICKNAME" AS nickname,
            lwc.weight_class,
            COALESCE(w.n, 0)::int AS wins,
            COALESCE(l.n, 0)::int AS losses
        FROM fighter_details fd
        LEFT JOIN wins      w   ON w.fighter_id  = fd.id
        LEFT JOIN losses    l   ON l.fighter_id  = fd.id
        LEFT JOIN {_LATEST_WC} ON lwc.fighter_id = fd.id
        {where}
        ORDER BY fd."LAST", fd."FIRST"
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    return FighterListResponse(
        data=[FighterListItem(**dict(r)) for r in rows],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if total else 0,
        ),
    )


@router.get("/{fighter_id}", response_model=FighterResponse, summary="Get fighter")
def get_fighter(fighter_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT
            fd.id,
            fd."FIRST"    AS first_name,
            fd."LAST"     AS last_name,
            fd."NICKNAME" AS nickname,
            ft.height_inches,
            ft.weight_lbs,
            ft.reach_inches,
            ft."STANCE"   AS stance,
            ft.dob_date,
            ft.slpm,
            ft.str_acc,
            ft.sapm,
            ft.str_def,
            ft.td_avg,
            ft.td_acc,
            ft.td_def,
            ft.sub_avg,
            (
                SELECT COUNT(*)::int
                FROM fight_results
                WHERE fighter_id = fd.id AND is_winner = TRUE
            ) AS wins,
            (
                SELECT COUNT(*)::int
                FROM fight_results
                WHERE opponent_id = fd.id AND is_winner = TRUE
            ) AS losses,
            (
                SELECT COUNT(*)::int
                FROM fight_results
                WHERE (fighter_id = fd.id OR opponent_id = fd.id)
                  AND "OUTCOME" = 'D/D'
            ) AS draws,
            (
                SELECT COUNT(*)::int
                FROM fight_results
                WHERE (fighter_id = fd.id OR opponent_id = fd.id)
                  AND "OUTCOME" = 'NC/NC'
            ) AS no_contests
        FROM fighter_details fd
        LEFT JOIN fighter_tott ft ON ft.fighter_id = fd.id
        WHERE fd.id = :fighter_id
    """), {"fighter_id": fighter_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Fighter '{fighter_id}' not found")

    return FighterResponse(**dict(row))

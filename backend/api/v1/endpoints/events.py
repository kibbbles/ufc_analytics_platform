"""api/v1/endpoints/events.py — Event endpoints.

Routes:
    GET /events             Paginated list; filters: name, location, year, date_from, date_to
    GET /events/{id}        Single event + full fight card
"""

from __future__ import annotations

import logging
import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.event import EventListResponse, EventResponse, EventWithFightsResponse
from schemas.fight import FightListItem
from schemas.shared import PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=EventListResponse, summary="List events")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = Query(None, description="Partial event name match (e.g. 'UFC 300')"),
    location: str | None = Query(None, description="Partial location match (e.g. 'Las Vegas')"),
    year: int | None = Query(None, description="Filter by year (e.g. 2023)"),
    date_from: date | None = Query(None, description="Events on or after this date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Events on or before this date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    params: dict = {"limit": page_size, "offset": offset}
    conditions: list[str] = []

    if name:
        conditions.append('ed."EVENT" ILIKE :name')
        params["name"] = f"%{name}%"
    if location:
        conditions.append('ed."LOCATION" ILIKE :location')
        params["location"] = f"%{location}%"
    if year:
        conditions.append("EXTRACT(YEAR FROM ed.date_proper) = :year")
        params["year"] = year
    if date_from:
        conditions.append("ed.date_proper >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("ed.date_proper <= :date_to")
        params["date_to"] = date_to

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM event_details ed {where}"),
        params,
    ).scalar() or 0

    rows = db.execute(text(f"""
        SELECT
            ed.id,
            ed."EVENT"       AS name,
            ed.date_proper   AS event_date,
            ed."LOCATION"    AS location
        FROM event_details ed
        {where}
        ORDER BY ed.date_proper DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    return EventListResponse(
        data=[EventResponse(**dict(r)) for r in rows],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if total else 0,
        ),
    )


@router.get("/{event_id}", response_model=EventWithFightsResponse, summary="Get event")
def get_event(event_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT
            ed.id,
            ed."EVENT"     AS name,
            ed.date_proper AS event_date,
            ed."LOCATION"  AS location
        FROM event_details ed
        WHERE ed.id = :event_id
    """), {"event_id": event_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")

    fights = db.execute(text("""
        SELECT
            fd.id,
            fd.event_id,
            fd."BOUT"       AS bout,
            fd.fighter_a_id,
            fd.fighter_b_id,
            CASE WHEN fr.is_winner = TRUE THEN fr.fighter_id ELSE NULL END AS winner_id,
            fr.weight_class,
            fr."METHOD"     AS method,
            fr."ROUND"::int AS round,
            fr.is_title_fight
        FROM fight_details fd
        LEFT JOIN fight_results fr ON fr.fight_id = fd.id
        WHERE fd.event_id = :event_id
        ORDER BY fd.id
    """), {"event_id": event_id}).mappings().all()

    return EventWithFightsResponse(
        **dict(row),
        fights=[FightListItem(**dict(f)) for f in fights],
    )

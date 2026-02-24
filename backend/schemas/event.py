"""schemas/event.py — Event request/response schemas.

DB source: event_details — id, EVENT, date_proper, LOCATION
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.shared import PaginationMeta
from schemas.fight import FightListItem


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: str
    name: Optional[str] = None
    event_date: Optional[date] = None
    location: Optional[str] = None


class EventWithFightsResponse(EventResponse):
    """Single event detail — includes the full fight card."""
    fights: list[FightListItem] = []


class EventListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[EventResponse]
    meta: PaginationMeta

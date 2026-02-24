"""schemas/fighter.py — Fighter request/response schemas.

DB sources:
    fighter_details  — id, FIRST, LAST, NICKNAME
    fighter_tott     — physical stats + career averages (typed columns)
    fight_results    — record (wins/losses/draws/no_contests) computed at query time
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.shared import PaginationMeta


class FighterBase(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None


class FighterResponse(FighterBase):
    # Physical stats (fighter_tott typed columns)
    height_inches: Optional[float] = None
    weight_lbs: Optional[float] = None
    reach_inches: Optional[float] = None
    stance: Optional[str] = None
    dob_date: Optional[date] = None

    # Career averages (fighter_tott)
    slpm: Optional[float] = None       # significant strikes landed per minute
    str_acc: Optional[str] = None      # striking accuracy %
    sapm: Optional[float] = None       # significant strikes absorbed per minute
    str_def: Optional[str] = None      # striking defence %
    td_avg: Optional[float] = None     # takedowns per 15 min
    td_acc: Optional[str] = None       # takedown accuracy %
    td_def: Optional[str] = None       # takedown defence %
    sub_avg: Optional[float] = None    # submission attempts per 15 min

    # Record (computed from fight_results)
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    no_contests: Optional[int] = None


class FighterListItem(BaseModel):
    """Lightweight schema used in paginated list responses."""
    model_config = ConfigDict(from_attributes=False)

    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    weight_class: Optional[str] = None  # most recent weight class
    wins: Optional[int] = None
    losses: Optional[int] = None


class FighterListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[FighterListItem]
    meta: PaginationMeta

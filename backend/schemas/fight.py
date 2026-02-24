"""schemas/fight.py — Fight request/response schemas.

DB sources:
    fight_details   — id, event_id, bout, fighter_a_id, fighter_b_id
    fight_results   — method, round, time, weight_class, is_title_fight, etc.
    fight_stats     — per-round typed integer columns (sig_str_landed, etc.)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.shared import PaginationMeta


class FightStatsResponse(BaseModel):
    """Round-by-round stats for one fighter in one fight (fight_stats typed cols)."""
    model_config = ConfigDict(from_attributes=False)

    fighter_id: Optional[str] = None
    round: Optional[str] = None
    kd_int: Optional[int] = None
    sig_str_landed: Optional[int] = None
    sig_str_attempted: Optional[int] = None
    sig_str_pct: Optional[float] = None
    total_str_landed: Optional[int] = None
    total_str_attempted: Optional[int] = None
    td_landed: Optional[int] = None
    td_attempted: Optional[int] = None
    td_pct: Optional[float] = None
    ctrl_seconds: Optional[int] = None
    head_landed: Optional[int] = None
    head_attempted: Optional[int] = None
    body_landed: Optional[int] = None
    body_attempted: Optional[int] = None
    leg_landed: Optional[int] = None
    leg_attempted: Optional[int] = None
    distance_landed: Optional[int] = None
    distance_attempted: Optional[int] = None
    clinch_landed: Optional[int] = None
    clinch_attempted: Optional[int] = None
    ground_landed: Optional[int] = None
    ground_attempted: Optional[int] = None


class FightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: str
    event_id: Optional[str] = None
    bout: Optional[str] = None
    fighter_a_id: Optional[str] = None
    fighter_b_id: Optional[str] = None
    winner_id: Optional[str] = None
    weight_class: Optional[str] = None
    method: Optional[str] = None
    round: Optional[int] = None
    time: Optional[str] = None
    is_title_fight: Optional[bool] = None
    is_interim_title: Optional[bool] = None
    is_championship_rounds: Optional[bool] = None
    total_fight_time_seconds: Optional[int] = None
    stats: list[FightStatsResponse] = []


class FightListItem(BaseModel):
    """Lightweight schema for paginated fight lists."""
    model_config = ConfigDict(from_attributes=False)

    id: str
    event_id: Optional[str] = None
    bout: Optional[str] = None
    weight_class: Optional[str] = None
    method: Optional[str] = None
    round: Optional[int] = None
    winner_id: Optional[str] = None
    is_title_fight: Optional[bool] = None


class FightListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[FightListItem]
    meta: PaginationMeta

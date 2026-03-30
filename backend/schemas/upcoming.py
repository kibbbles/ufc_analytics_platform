"""schemas/upcoming.py — Upcoming events/fights request/response schemas.

DB sources: upcoming_events, upcoming_fights, upcoming_predictions
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class UpcomingFightPrediction(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    win_prob_a:    Optional[float] = None
    win_prob_b:    Optional[float] = None
    method_ko_tko: Optional[float] = None
    method_sub:    Optional[float] = None
    method_dec:    Optional[float] = None
    model_version: Optional[str]  = None
    features_json: Optional[dict[str, Any]] = None


class UpcomingFightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id:             str
    event_id:       str
    fighter_a_name: Optional[str]  = None
    fighter_b_name: Optional[str]  = None
    fighter_a_id:   Optional[str]  = None
    fighter_b_id:   Optional[str]  = None
    weight_class:   Optional[str]   = None
    is_title_fight:  bool            = False
    is_interim_title: bool           = False
    odds_a:         Optional[int]   = None
    odds_b:         Optional[int]   = None
    implied_prob_a: Optional[float] = None
    implied_prob_b: Optional[float] = None
    prediction:     Optional[UpcomingFightPrediction] = None


class UpcomingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id:          str
    event_name:  Optional[str]  = None
    event_date:  Optional[date] = None
    location:    Optional[str]  = None
    is_numbered: Optional[bool] = None
    fight_count: int            = 0


class UpcomingEventWithFightsResponse(UpcomingEventResponse):
    fights: list[UpcomingFightResponse] = []


class UpcomingEventListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[UpcomingEventResponse]

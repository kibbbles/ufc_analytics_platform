"""schemas/past_prediction.py — Pydantic v2 schemas for past predictions endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class PastPredictionItem(BaseModel):
    # Fight context
    fight_id: str
    event_id: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[date] = None
    fighter_a_id: Optional[str] = None
    fighter_b_id: Optional[str] = None
    fighter_a_name: Optional[str] = None
    fighter_b_name: Optional[str] = None
    weight_class: Optional[str] = None
    # Prediction
    win_prob_a: Optional[float] = None
    win_prob_b: Optional[float] = None
    pred_method_ko_tko: Optional[float] = None
    pred_method_sub: Optional[float] = None
    pred_method_dec: Optional[float] = None
    predicted_winner_id: Optional[str] = None
    predicted_method: Optional[str] = None
    # Actual result
    actual_winner_id: Optional[str] = None
    actual_method: Optional[str] = None
    # Metrics
    is_correct: Optional[bool] = None
    confidence: Optional[float] = None
    is_upset: Optional[bool] = None
    # Data quality / provenance
    prediction_source: Optional[str] = None          # 'pre_fight_archive' | 'backfill'
    pre_fight_predicted_at: Optional[datetime] = None # when the pre-fight prediction was made

    model_config = {"from_attributes": True}


class PastPredictionSummary(BaseModel):
    total_fights: int
    correct: int
    accuracy: float
    high_conf_fights: int     # confidence >= 0.65
    high_conf_correct: int
    high_conf_accuracy: float
    date_from: str
    date_to: str
    available_years: list[int] = []
    # Pre-fight only stats (prediction_source = 'pre_fight_archive')
    pre_fight_total: int = 0
    pre_fight_correct: int = 0
    pre_fight_accuracy: float = 0.0
    pre_fight_avg_confidence: float = 0.0
    pre_fight_high_conf_fights: int = 0
    pre_fight_high_conf_correct: int = 0
    pre_fight_high_conf_accuracy: float = 0.0


class PastPredictionsResponse(BaseModel):
    summary: PastPredictionSummary
    recent: list[PastPredictionItem]


class PastPredictionEventItem(BaseModel):
    event_id: str
    event_name: Optional[str] = None
    event_date: Optional[date] = None
    fight_count: int
    correct_count: int
    accuracy: float


class PastPredictionEventsResponse(BaseModel):
    data: list[PastPredictionEventItem]
    total: int
    total_pages: int
    page: int
    page_size: int


class PastPredictionEventDetail(BaseModel):
    event_id: str
    event_name: Optional[str] = None
    event_date: Optional[date] = None
    fight_count: int
    correct_count: int
    accuracy: float
    fights: list[PastPredictionItem]


class PastPredictionFightsResponse(BaseModel):
    data: list[PastPredictionItem]
    total: int
    total_pages: int
    page: int
    page_size: int


# ── Modal stats ───────────────────────────────────────────────────────────────

class ConfBucket(BaseModel):
    label: str
    fights: int
    correct: int
    accuracy: float


class WeightClassStat(BaseModel):
    weight_class: str
    fights: int
    correct: int
    accuracy: float


class ModalStatsSection(BaseModel):
    conf_buckets: list[ConfBucket]
    weight_classes: list[WeightClassStat]
    avg_conf_correct: Optional[float] = None
    avg_conf_incorrect: Optional[float] = None


class PastPredictionModalStats(BaseModel):
    all: ModalStatsSection
    pre_fight: ModalStatsSection

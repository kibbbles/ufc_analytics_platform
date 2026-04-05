"""schemas/analytics.py — Analytics response schemas.

Powers Product 2 (Style Evolution Timeline) and Product 3 (Fighter Endurance).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Product 2: Style Evolution Timeline ───────────────────────────────────────

class StyleEvolutionPoint(BaseModel):
    """Finish-rate breakdown for a single year (optionally filtered by weight class)."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    ko_tko_rate: float
    submission_rate: float
    decision_rate: float
    finish_rate: float          # ko_tko_rate + submission_rate
    total_fights: int
    is_partial_year: bool = False
    weight_class: Optional[str] = None  # None = all weight classes combined


class FighterOutputPoint(BaseModel):
    """Average per-fighter outputs per fight, aggregated by year (fight_stats, 2015+)."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    avg_sig_str_per_fight: float        # significant strikes landed
    avg_td_attempts_per_fight: float    # takedown attempts
    avg_ctrl_seconds_per_fight: float   # control time in seconds
    total_fights: int
    is_partial_year: bool = False


class RoundDistributionPoint(BaseModel):
    """Share of finishes by round for a given year."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    r1_pct: float       # % of finishes that ended in round 1
    r2_pct: float
    r3_pct: float
    r4plus_pct: float   # round 4 or 5 (championship rounds)
    total_finishes: int
    is_partial_year: bool = False


class WeightClassYearPoint(BaseModel):
    """Finish rates for one weight class in one year — used for the heatmap."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    weight_class: str
    finish_rate: float
    ko_tko_rate: float
    submission_rate: float
    decision_rate: float
    total_fights: int


class PhysicalStatPoint(BaseModel):
    """Average height and reach for fighters active in a given weight class and year."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    weight_class: str
    avg_height_inches: float
    avg_reach_inches: float
    fighter_count: int


class StyleEvolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[StyleEvolutionPoint]             # finish rates by year (all years, filtered by wc)
    fighter_outputs: list[FighterOutputPoint]   # avg fighter outputs by year (2015+, filtered by wc)
    round_distribution: list[RoundDistributionPoint]  # finish round breakdown by year (filtered by wc)
    heatmap_data: list[WeightClassYearPoint]    # finish rates by wc × year (always all wcs)
    physical_stats: list[PhysicalStatPoint]     # avg height/reach by wc × year (always all wcs)
    weight_class: Optional[str] = None          # echoes the filter applied


# ── Product 3: Fighter Endurance & Pacing ─────────────────────────────────────

class EnduranceRoundData(BaseModel):
    """Average per-round performance metrics for one fighter across all their fights."""
    model_config = ConfigDict(from_attributes=False)

    round: int
    avg_sig_str_landed: Optional[float] = None
    avg_sig_str_pct: Optional[float] = None
    avg_ctrl_seconds: Optional[float] = None
    avg_kd: Optional[float] = None
    fight_count: Optional[int] = None  # how many fights contributed to this round


class FighterEnduranceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fighter_id: str
    fighter_name: Optional[str] = None
    rounds: list[EnduranceRoundData]
    note: Optional[str] = None

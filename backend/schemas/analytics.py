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


class AgeByWeightClassPoint(BaseModel):
    """Average fighter age per weight class per year."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    weight_class: str
    avg_age: float
    fighter_count: int


class FighterStatsByWeightClass(BaseModel):
    """Average career stats (from fighter_tott) for fighters in a given weight class."""
    model_config = ConfigDict(from_attributes=False)

    weight_class: str
    avg_slpm: float             # sig strikes landed per minute
    avg_str_acc: float          # striking accuracy (0–1)
    avg_sapm: float             # sig strikes absorbed per minute
    avg_str_def: float          # striking defence (0–1)
    avg_td_avg: float           # takedowns per 15 min
    avg_td_acc: float           # takedown accuracy (0–1)
    avg_td_def: float           # takedown defence (0–1)
    avg_sub_avg: float          # submission attempts per 15 min
    fighter_count: int


class StyleStatsByWeightClassPoint(BaseModel):
    """Per-year striking/grappling metrics by weight class, computed from fight_stats."""
    model_config = ConfigDict(from_attributes=False)

    year: int
    weight_class: str
    avg_slpm: float           # sig strikes landed per minute
    avg_str_acc: float        # striking accuracy (0–1)
    avg_sapm: float           # sig strikes absorbed per minute (opponent's landed)
    avg_str_def: float        # striking defence (0–1): % of opponent strikes avoided
    avg_td_per_fight: float   # takedowns landed per fight per fighter
    avg_td_acc: float         # takedown accuracy (0–1)
    avg_td_def: float         # takedown defence (0–1): % of opponent attempts stuffed
    avg_sub_per_fight: float  # submission attempts per fight per fighter
    avg_ctrl_seconds: float   # avg ctrl seconds per fight per fighter
    fight_count: int


class StyleEvolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[StyleEvolutionPoint]                       # finish rates by year (all years, filtered by wc)
    fighter_outputs: list[FighterOutputPoint]             # avg fighter outputs by year (2015+, filtered by wc)
    round_distribution: list[RoundDistributionPoint]      # finish round breakdown by year (filtered by wc)
    heatmap_data: list[WeightClassYearPoint]              # finish rates by wc × year (always all wcs)
    physical_stats: list[PhysicalStatPoint]               # avg height/reach by wc × year (always all wcs)
    age_data: list[AgeByWeightClassPoint]                 # avg age by wc × year (always all wcs)
    fighter_stats: list[FighterStatsByWeightClass]        # career stats snapshot by wc (always all wcs)
    style_stats: list[StyleStatsByWeightClassPoint]       # per-year style metrics by wc (always all wcs)
    weight_class: Optional[str] = None                    # echoes the filter applied


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


# ── Betting Insights (Task 31) ────────────────────────────────────────────────

class StrategyRoiRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    strategy_key: str
    strategy_name: str
    strategy_order: int
    bets: int
    wins: int
    pnl: float
    roi: float          # pnl / bets


class VegasCalibrationRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    bucket: str
    bucket_order: int
    avg_implied_prob: float
    fights: int
    wins: int
    actual_win_rate: float


class UpsetRateRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    weight_class: str
    weight_class_order: int
    total_fights: int
    upset_count: int
    upset_rate: float


class RoiOverTimeRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    event_id: str
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    bets: int
    pnl: float
    cumulative_pnl: float
    cumulative_bets: int


class BettingInsightsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    sample_size: int
    avg_edge_qualifying: float
    upset_count_20pp: int = 0
    upset_rate_20pp: float = 0.0
    strategies: list[StrategyRoiRow]
    calibration: list[VegasCalibrationRow]
    upset_rates: list[UpsetRateRow]
    roi_over_time: list[RoiOverTimeRow]


class BettingRoiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    bets: int
    wins: int
    pnl: float
    roi: float


class RoiEventEntry(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    event_id: str
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    bets: int
    pnl: float                          # per-event P&L, $1 unit


class RoiOverTimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    strategy: str
    events: list[RoiEventEntry]


class UpsetFightCard(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fight_id: str
    event_id: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    weight_class: Optional[str] = None
    fighter_a_name: Optional[str] = None
    fighter_b_name: Optional[str] = None
    model_pick_name: Optional[str] = None
    winner_name: Optional[str] = None
    method: Optional[str] = None
    conviction: float
    model_pick_odds: Optional[int] = None


class BettingUpsetsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fights: list[UpsetFightCard]
    total: int


class BettingFightRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fight_id: str
    event_id: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    weight_class: Optional[str] = None
    is_title: bool = False
    fighter_a_name: Optional[str] = None
    fighter_b_name: Optional[str] = None
    win_prob_a: float
    win_prob_b: float
    pick: Optional[str] = None          # model's pick fighter name
    opponent: Optional[str] = None      # other fighter name
    pick_prob: float                    # model prob for pick (0–1)
    opp_prob: float
    conviction_pp: float                # (pick_prob − 0.5) × 100
    edge_pp: float                      # (pick_prob − vegas_implied) × 100
    vegas_implied_pct: float            # vegas implied for model's pick (0–100)
    model_pick_odds: Optional[int] = None
    is_correct: bool
    actual_winner_name: Optional[str] = None
    result_method: Optional[str] = None
    pl_model: float                     # net P&L per $1 bet — model pick strategy
    pl_fav: float                       # net P&L per $1 bet — always bet favorite
    pl_dog: float                       # net P&L per $1 bet — always bet underdog
    pl_younger: Optional[float] = None  # net P&L per $1 bet — always bet younger fighter (None if age unknown)
    age_diff: Optional[float] = None    # |age_a − age_b| in years at fight time (None if either DOB unknown)
    younger_name: Optional[str] = None  # younger fighter's name (None if age unknown / equal)


class BettingFightsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    fights: list[BettingFightRow]
    total: int

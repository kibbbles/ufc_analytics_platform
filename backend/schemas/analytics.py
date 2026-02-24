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
    total_fights: int
    weight_class: Optional[str] = None  # None = all weight classes combined


class StyleEvolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    data: list[StyleEvolutionPoint]
    weight_class: Optional[str] = None  # echoes the filter applied


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
    # Surfaced in the UI for fighters with pre-2015 careers
    note: Optional[str] = None

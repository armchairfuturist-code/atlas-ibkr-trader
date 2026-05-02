"""Data classes for multi-agent research system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.schemas import SignalRating


@dataclass
class ResearchNote:
    """Research note from a bull or bear researcher."""

    thesis: str
    confidence: int  # 1-100
    key_points: list[str] = field(default_factory=list)
    persona: str = ""  # "bull" or "bear"
    supporting_indicators: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InvestmentPlan:
    """Final investment plan from research manager judge."""

    ticker: str
    rating: SignalRating
    conviction: int  # 1-100
    thesis: str
    key_insights: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    bull_contribution: float = 0.0  # 0-1, how much bull thesis contributed
    bear_contribution: float = 0.0  # 0-1, how much bear thesis contributed
    timestamp: datetime = field(default_factory=datetime.now)

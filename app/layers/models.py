"""Shared layer output models for ATLAS decision stack."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MacroAgentOutput:
    """Output from a single macro agent in Layer 1."""
    agent_name: str
    config_version: str
    regime_vote: str  # RISK_ON, RISK_OFF, NEUTRAL
    confidence: float  # 0.0-1.0
    features: dict[str, float] = field(default_factory=dict)


@dataclass
class SectorDeskOutput:
    """Output from a sector desk in Layer 2."""
    sector: str
    etf_ticker: str
    score: float  # 0.0-1.0
    is_etf: bool
    config_version: str


@dataclass
class SuperinvestorOutput:
    """Output from a superinvestor filter in Layer 3."""
    source_etf: str
    source_sector: str
    reweighted_score: float  # 0.0-1.0
    filter_name: str
    config_version: str


@dataclass
class DecisionLayerResult:
    """Final decision output from Layer 4."""
    proposals: list[dict[str, Any]]
    rationale: str
    config_version: str

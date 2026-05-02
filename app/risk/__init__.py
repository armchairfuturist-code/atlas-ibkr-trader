"""Risk management with multi-persona debate.

Inspired by TradingAgents' 3-way risk debate between Aggressive,
Conservative, and Neutral analysts before final portfolio approval.
"""

from app.risk.personas import (
    RiskPersona,
    RiskPersonaView,
    AggressiveAnalyst,
    ConservativeAnalyst,
    NeutralAnalyst,
)
from app.risk.debate_risk_manager import DebateRiskManager

__all__ = [
    "RiskPersona",
    "RiskPersonaView",
    "AggressiveAnalyst",
    "ConservativeAnalyst",
    "NeutralAnalyst",
    "DebateRiskManager",
]

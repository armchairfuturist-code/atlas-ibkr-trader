"""Multi-agent debate system for investment research.

Inspired by TradingAgents - bull/bear researchers debate investment thesis,
research manager judges and creates investment plan.

Enhanced with:
- GeopoliticalSentimentAgent for prediction market integration
- TechnicalAnalysisAgent for SHORT signals (QuantAgent-inspired)
"""

from app.agents.research_note import ResearchNote, InvestmentPlan
from app.agents.bull_researcher import BullResearcher
from app.agents.bear_researcher import BearResearcher
from app.agents.research_manager import ResearchManager
from app.agents.debate_orchestrator import DebateOrchestrator
from app.agents.geopolitical_agent import GeopoliticalSentimentAgent, GeopoliticalSignal
from app.agents.technical_agent import (
    TechnicalAnalysisAgent,
    TechnicalSignal,
    TechnicalAnalysisResult,
)

__all__ = [
    "ResearchNote",
    "InvestmentPlan",
    "BullResearcher",
    "BearResearcher",
    "ResearchManager",
    "DebateOrchestrator",
    "GeopoliticalSentimentAgent",
    "GeopoliticalSignal",
    "TechnicalAnalysisAgent",
    "TechnicalSignal",
    "TechnicalAnalysisResult",
]

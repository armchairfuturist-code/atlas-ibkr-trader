"""Debate orchestrator - runs multi-round debate between bull/bear researchers.

Inspired by TradingAgents' multi-agent debate system where bull and bear
researchers argue their cases before a manager judges.

Enhanced with GeopoliticalSentimentAgent for prediction market integration.
"""

import logging
from typing import Optional

from app.agents.research_note import ResearchNote, InvestmentPlan
from app.agents.bull_researcher import BullResearcher
from app.agents.bear_researcher import BearResearcher
from app.agents.research_manager import ResearchManager
from app.agents.geopolitical_agent import GeopoliticalSentimentAgent, GeopoliticalSignal

logger = logging.getLogger(__name__)


class DebateOrchestrator:
    """Runs multi-round debate between bull/bear agents.

    Optionally includes geopolitical sentiment from prediction markets
    as additional context for the debate.
    """

    def __init__(
        self,
        max_rounds: int = 2,
        include_geopolitics: bool = False,
        geopolitical_agent: Optional[GeopoliticalSentimentAgent] = None,
    ):
        """Initialize debate orchestrator.

        Args:
            max_rounds: Number of debate rounds (default: 2)
            include_geopolitics: Whether to include geopolitical sentiment (default: False)
            geopolitical_agent: Optional pre-configured geopolitical agent
        """
        self.max_rounds = max_rounds
        self.include_geopolitics = include_geopolitics
        self.bull_researcher = BullResearcher()
        self.bear_researcher = BearResearcher()
        self.research_manager = ResearchManager()
        self.geopolitical_agent = geopolitical_agent or GeopoliticalSentimentAgent()

    def run_debate(
        self,
        ticker: str,
        data: dict,
        sector_filter: Optional[list[str]] = None,
    ) -> InvestmentPlan:
        """Run multi-round debate and return final investment plan.

        Args:
            ticker: Stock symbol to analyze
            data: Market data dict with keys:
                  - price_history: list of recent prices
                  - volume: trading volume
                  - indicators: dict with rsi, macd, etc.
                  - news: list of news items
                  - fundamentals: dict with pe_ratio, etc.
            sector_filter: Optional list of sectors to filter geopolitical analysis

        Returns:
            InvestmentPlan with final rating, conviction, and thesis
        """
        logger.info(f"Starting debate for {ticker}")

        # Optionally include geopolitical sentiment
        geopolitical_signal: Optional[GeopoliticalSignal] = None
        if self.include_geopolitics:
            logger.debug(f"Fetching geopolitical sentiment for {ticker}")
            try:
                geopolitical_signal = self.geopolitical_agent.analyze(sector_filter)
                if geopolitical_signal is not None:
                    logger.info(
                        f"Geopolitical sentiment: {geopolitical_signal.confidence:.0%} confidence, "
                        f"{len(geopolitical_signal.sector_weights)} sectors weighted"
                    )
            except Exception as e:
                logger.warning(f"Failed to get geopolitical sentiment: {e}")

        # Enrich data with geopolitical context
        enriched_data = self._enrich_with_geopolitics(data, geopolitical_signal)

        # Round 1: Initial bull/bear analysis
        logger.debug(f"Round 1: Initial analysis for {ticker}")
        bull_note = self.bull_researcher.analyze(ticker, enriched_data)
        bear_note = self.bear_researcher.analyze(ticker, enriched_data)

        debate_history = [{"round": 1, "bull": bull_note, "bear": bear_note}]

        # Round 2: Each agent responds to other's points (if max_rounds > 1)
        if self.max_rounds > 1:
            logger.debug(f"Round 2: Rebuttal analysis for {ticker}")

            # Build context from opposing view
            bull_context = self._build_rebuttal_context(ticker, bear_note, "bull")
            bear_context = self._build_rebuttal_context(ticker, bull_note, "bear")

            # Update data with context for rebuttal
            data_with_context = {**enriched_data, "rebuttal_context": bull_context}
            bull_note_rebuttal = self.bull_researcher.analyze(ticker, data_with_context)

            data_with_context = {**enriched_data, "rebuttal_context": bear_context}
            bear_note_rebuttal = self.bear_researcher.analyze(ticker, data_with_context)

            # Use rebuttal notes if they're stronger
            if bull_note_rebuttal.confidence > bull_note.confidence:
                bull_note = bull_note_rebuttal
            if bear_note_rebuttal.confidence > bear_note.confidence:
                bear_note = bear_note_rebuttal

            debate_history.append({"round": 2, "bull": bull_note, "bear": bear_note})

        # Research Manager judges
        logger.debug(f"Research manager judging for {ticker}")
        investment_plan = self.research_manager.judge(
            bull_note, bear_note, geopolitical_signal
        )

        # Log result
        logger.info(
            f"Debate complete for {ticker}: {investment_plan.rating.value} "
            f"(conviction: {investment_plan.conviction})"
        )

        return investment_plan

    def _enrich_with_geopolitics(
        self, data: dict, signal: Optional[GeopoliticalSignal]
    ) -> dict:
        """Enrich market data with geopolitical sentiment."""
        if signal is None:
            return data

        enriched = {**data}
        enriched["geopolitical"] = {
            "event": signal.event,
            "probability": signal.probability,
            "confidence": signal.confidence,
            "sector_weights": signal.sector_weights,
            "thesis": signal.thesis,
            "markets_analyzed": signal.markets_analyzed,
        }
        return enriched

    def _build_rebuttal_context(
        self, ticker: str, opposing_note: ResearchNote, my_persona: str
    ) -> str:
        """Build context string for rebuttal round."""
        persona = "bearish" if my_persona == "bull" else "bullish"
        return (
            f"The {persona} case argues: {opposing_note.thesis}. "
            f"Key points: {'; '.join(opposing_note.key_points[:2])}. "
            f"Consider addressing these concerns in your analysis."
        )

    def get_debate_summary(self) -> dict:
        """Get summary of the debate (for audit/debugging)."""
        return {
            "max_rounds": self.max_rounds,
            "include_geopolitics": self.include_geopolitics,
            "researcher_types": [
                "BullResearcher",
                "BearResearcher",
                "ResearchManager",
                "GeopoliticalSentimentAgent (optional)",
            ],
            "note": "Debate history stored in orchestrator instance if needed",
        }

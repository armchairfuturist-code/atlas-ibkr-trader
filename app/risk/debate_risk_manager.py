"""Debate-based risk manager - 3-way risk debate before final approval.

Inspired by TradingAgents' risk debate where Aggressive, Conservative,
and Neutral personas advocate their views before Portfolio Manager decides.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.schemas import Recommendation, RiskVerdict, RiskVerdictEvent, RejectCode
from app.config import Config
from app.universe import ETFUniverse
from app.risk_engine import PortfolioState
from app.risk.personas import (
    RiskPersonaView,
    AggressiveAnalyst,
    ConservativeAnalyst,
    NeutralAnalyst,
)

logger = logging.getLogger(__name__)


class DebateRiskManager:
    """3-way risk debate manager before final approval.

    Runs debate between three personas and synthesizes their views
    into a final RiskVerdictEvent.

    Example:
        manager = DebateRiskManager(config, universe)
        verdict = manager.evaluate_with_debate(recommendation, portfolio)
    """

    def __init__(self, config: Config, universe: ETFUniverse):
        """Initialize debate risk manager.

        Args:
            config: System configuration
            universe: ETF universe for lookups
        """
        self.config = config
        self.universe = universe
        self.personas = [
            AggressiveAnalyst(),
            ConservativeAnalyst(),
            NeutralAnalyst(),
        ]

    def evaluate_with_debate(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> RiskVerdictEvent:
        """Evaluate recommendation through persona debate.

        Args:
            recommendation: Trading recommendation to evaluate
            portfolio: Current portfolio state

        Returns:
            RiskVerdictEvent with final decision and reasoning
        """
        logger.debug(f"Running risk debate for {recommendation.ticker}")

        # Step 1: Each persona evaluates independently
        persona_views = []
        for persona in self.personas:
            view = persona.evaluate(recommendation, portfolio)
            persona_views.append(view)
            logger.debug(f"  {persona.name}: {view.verdict} - {view.reasoning}")

        # Step 2: Synthesize views into final verdict
        verdict = self._synthesize_verdict(recommendation, portfolio, persona_views)

        return verdict

    def _synthesize_verdict(
        self,
        recommendation: Recommendation,
        portfolio: PortfolioState,
        persona_views: list[RiskPersonaView],
    ) -> RiskVerdictEvent:
        """Synthesize persona views into final RiskVerdictEvent.

        Decision rules:
        - If any persona says REJECT → REJECT (unless others say approve)
        - If all personas say APPROVE → PASS
        - If mixed (CAUTION + APPROVE) → PASS with REVIEW flag
        - If majority CAUTION or any REJECT → REVIEW or REJECT
        """
        verdicts = [v.verdict for v in persona_views]
        approve_count = verdicts.count("approve")
        caution_count = verdicts.count("caution")
        reject_count = verdicts.count("reject")

        # Collect all concerns
        all_concerns = []
        adjusted_sizes = []
        for view in persona_views:
            all_concerns.extend(view.risk_concerns)
            adjusted_sizes.append(view.adjusted_size_pct)

        # Calculate weighted average adjusted size
        # Weight by persona's risk tolerance
        weights = [0.8, 0.3, 0.5]  # Aggressive, Conservative, Neutral
        if sum(weights) > 0:
            weighted_size = sum(w * s for w, s in zip(weights, adjusted_sizes)) / sum(
                weights
            )
        else:
            weighted_size = recommendation.position_size_pct

        # Decision logic
        if reject_count >= 2:
            # Strong rejection
            return RiskVerdictEvent(
                recommendation_id=recommendation.id,
                verdict=RiskVerdict.REJECT,
                reject_code=RejectCode.RISK_VERDICT_REQUIRED,
                reason=f"Risk debate rejected ({reject_count}/3 personas): {', '.join(all_concerns[:3])}",
                metrics={
                    "persona_verdicts": verdicts,
                    "adjusted_size_pct": weighted_size,
                    "concerns": all_concerns[:5],
                },
            )

        if reject_count == 1 and approve_count == 0:
            # Sole dissenter, everyone else cautious
            return RiskVerdictEvent(
                recommendation_id=recommendation.id,
                verdict=RiskVerdict.REVIEW,
                reject_code=RejectCode.RISK_VERDICT_REQUIRED,
                reason=f"Mixed signals ({verdicts}): {all_concerns[0] if all_concerns else 'Review required'}",
                metrics={
                    "persona_verdicts": verdicts,
                    "adjusted_size_pct": weighted_size,
                    "concerns": all_concerns[:3],
                },
            )

        if approve_count >= 2:
            # Majority approval
            if caution_count > 0:
                # Mixed but leaning positive
                return RiskVerdictEvent(
                    recommendation_id=recommendation.id,
                    verdict=RiskVerdict.PASS,
                    reason=f"Approved with caution ({approve_count} personas): {', '.join(all_concerns[:2]) if all_concerns else 'Some concerns noted'}",
                    metrics={
                        "persona_verdicts": verdicts,
                        "adjusted_size_pct": weighted_size,
                        "concerns": all_concerns[:3],
                    },
                )
            else:
                # Unanimous or near-unanimous approval
                return RiskVerdictEvent(
                    recommendation_id=recommendation.id,
                    verdict=RiskVerdict.PASS,
                    reason=f"Approved ({approve_count}/3 personas) - risk debate passed",
                    metrics={
                        "persona_verdicts": verdicts,
                        "adjusted_size_pct": weighted_size,
                    },
                )

        # Default: caution / review
        return RiskVerdictEvent(
            recommendation_id=recommendation.id,
            verdict=RiskVerdict.REVIEW,
            reject_code=RejectCode.RISK_VERDICT_REQUIRED,
            reason=f"Mixed risk views ({verdicts}): review recommended",
            metrics={
                "persona_verdicts": verdicts,
                "adjusted_size_pct": weighted_size,
                "concerns": all_concerns[:3],
            },
        )

    def get_debate_summary(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> dict:
        """Get a summary of the debate for a recommendation.

        Useful for logging/auditing.
        """
        persona_views = []
        for persona in self.personas:
            view = persona.evaluate(recommendation, portfolio)
            persona_views.append(
                {
                    "persona": view.persona,
                    "verdict": view.verdict,
                    "reasoning": view.reasoning,
                    "adjusted_size_pct": view.adjusted_size_pct,
                    "concerns": view.risk_concerns,
                }
            )

        return {
            "ticker": recommendation.ticker,
            "rating": recommendation.rating.value,
            "conviction": recommendation.conviction,
            "persona_views": persona_views,
        }

"""Signal orchestrator: 4-layer ATLAS decision pipeline.

Generates buy/sell/hold signals across the ETF universe by running:
  Layer 1: Macro regime detection (10 agents, real yfinance data)
  Layer 2: Sector ranking (7 sectors)
  Layer 3: Superinvestor reweighting (4 filters)
  Layer 4: Decision aggregation (CRO, Alpha, Execution, CIO)
"""
import logging
from typing import Optional

from app.schemas import SignalRating, SignalDirection, Recommendation
from app.layers.layer1_macro import MacroLayer
from app.layers.layer2_sector import SectorLayer
from app.layers.layer3_superinvestors import SuperinvestorLayer
from app.layers.layer4_decision import DecisionLayer
from app.universe import ETFUniverse

logger = logging.getLogger(__name__)


class SignalOrchestrator:
    """Orchestrates the 4-layer ATLAS decision pipeline."""

    def __init__(self, universe: ETFUniverse, config=None):
        self.universe = universe
        if hasattr(config, "get"):
            # Raw dict config (from tests or manual construction)
            self.config = config or {}
            layer_configs = self.config
        else:
            # Pydantic Config object (from daily_runner)
            self.config = vars(config) if config else {}
            layer_configs = self.config
        self.macro_layer = MacroLayer(layer_configs.get("layer1_macro"))
        self.sector_layer = SectorLayer(layer_configs.get("layer2_sector"))
        self.superinvestor_layer = SuperinvestorLayer(layer_configs.get("layer3_superinvestors"))
        self.decision_layer = DecisionLayer(layer_configs.get("layer4_decision"))

    def generate_signals(self, tickers: Optional[list[str]] = None) -> list[Recommendation]:
        """Run the full 4-layer pipeline and return ranked signals.

        Args:
            tickers: Optional list of tickers to scan. If None, scans universe.

        Returns:
            List of Recommendation objects sorted by conviction descending.
        """
        # Layer 1: Macro regime
        macro_outputs = self.macro_layer.evaluate()
        logger.info(f"Layer 1 (Macro): {len(macro_outputs)} agent outputs")

        # Layer 2: Sector ranking
        sector_outputs = self.sector_layer.evaluate(macro_outputs)
        logger.info(f"Layer 2 (Sector): {len(sector_outputs)} sectors ranked")

        # Layer 3: Superinvestor filters
        investor_outputs = self.superinvestor_layer.evaluate(sector_outputs)
        logger.info(f"Layer 3 (Superinvestors): {len(investor_outputs)} filter outputs")

        # Layer 4: Decision aggregation
        decision = self.decision_layer.evaluate(investor_outputs)
        logger.info(f"Layer 4 (Decision): {len(decision.proposals)} proposals")

        # Convert proposals to Recommendation objects
        recommendations = []
        for proposal in decision.proposals:
            rating = (SignalRating.BUY if proposal.get("conviction", 50) >= 70 else
                      SignalRating.OVERWEIGHT if proposal.get("conviction", 50) >= 55 else
                      SignalRating.HOLD if proposal.get("conviction", 50) >= 40 else
                      SignalRating.UNDERWEIGHT)

            direction_str = proposal.get("direction", "NEUTRAL").upper()
            direction = next((d for d in SignalDirection if d.value == direction_str), SignalDirection.NEUTRAL)

            recommendations.append(Recommendation(
                ticker=proposal["ticker"],
                rating=rating,
                conviction=proposal.get("conviction", 50),
                direction=direction,
                position_size_pct=proposal.get("size_pct", 0),
                thesis=decision.rationale,
                sector=proposal.get("sector", ""),
            ))

        # Sort by conviction descending
        recommendations.sort(key=lambda r: r.conviction, reverse=True)
        return recommendations

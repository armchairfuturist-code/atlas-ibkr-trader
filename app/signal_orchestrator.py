"""Signal orchestrator: 4-layer ATLAS decision pipeline.

Generates buy/sell/hold signals across the ETF universe by running:
  Layer 1: Macro regime detection (10 agents)
  Layer 2: Sector ranking (7 sectors)
  Layer 3: Superinvestor reweighting (4 filters)
  Layer 4: Decision aggregation (CRO, Alpha, Execution, CIO)
"""
import logging
from typing import Optional

from app.schemas import SignalRating
from app.layers.layer1_macro import MacroLayer
from app.layers.layer2_sector import SectorLayer
from app.layers.layer3_superinvestors import SuperinvestorLayer
from app.layers.layer4_decision import DecisionLayer

logger = logging.getLogger(__name__)


class SignalOrchestrator:
    """Orchestrates the 4-layer ATLAS decision pipeline."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.macro_layer = MacroLayer(self.config.get("layer1_macro"))
        self.sector_layer = SectorLayer(self.config.get("layer2_sector"))
        self.superinvestor_layer = SuperinvestorLayer(self.config.get("layer3_superinvestors"))
        self.decision_layer = DecisionLayer(self.config.get("layer4_decision"))

    def generate_signals(self, tickers: Optional[list[str]] = None) -> list[dict]:
        """Run the full 4-layer pipeline and return ranked signals.

        Args:
            tickers: Optional list of tickers to scan. If None, scans universe.

        Returns:
            List of signal dicts with keys: ticker, rating, conviction, rationale
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

        # Convert proposals to signal format
        signals = []
        for proposal in decision.proposals:
            rating = SignalRating.BUY if proposal.get("conviction", 50) >= 70 else \
                     SignalRating.OVERWEIGHT if proposal.get("conviction", 50) >= 55 else \
                     SignalRating.HOLD if proposal.get("conviction", 50) >= 40 else \
                     SignalRating.UNDERWEIGHT
            signals.append({
                "ticker": proposal["ticker"],
                "rating": rating.value,
                "conviction": proposal.get("conviction", 50),
                "direction": proposal.get("direction", "NEUTRAL"),
                "size_pct": proposal.get("size_pct", 0),
                "source_filter": proposal.get("source_filter", ""),
                "rationale": getattr(decision, "rationale", ""),
            })

        # Sort by conviction descending
        signals.sort(key=lambda s: s["conviction"], reverse=True)
        return signals

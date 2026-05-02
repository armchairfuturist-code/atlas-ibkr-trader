"""ATLAS-inspired layered signal orchestrator."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import random

from app.schemas import Recommendation, SignalDirection, SignalRating
from app.universe import ETFUniverse, Sector
from app.config import Config

# Layer imports
from app.layers.layer1_macro import MacroLayer
from app.layers.layer2_sector import SectorLayer
from app.layers.layer3_superinvestors import SuperinvestorLayer
from app.layers.layer4_decision import DecisionLayer
from app.layers.config_loader import load_layer_config


# Default base position size (percentage of portfolio)
DEFAULT_BASE_POSITION_SIZE = 10.0


@dataclass
class MacroContext:
    """Macro regime context from Layer 1."""

    regime: str = "NEUTRAL"  # RISK_ON, RISK_OFF, NEUTRAL
    conviction: int = 50
    key_factors: list[str] = None

    def __post_init__(self):
        if self.key_factors is None:
            self.key_factors = []


@dataclass
class SectorSignal:
    """Sector-level signal from Layer 2."""

    sector: Sector
    direction: SignalDirection
    conviction: int
    top_pick: Optional[str] = None


class SignalOrchestrator:
    """
    Multi-layer signal orchestrator inspired by ATLAS architecture.

    Layer 1: Macro context assessment
    Layer 2: Sector selection
    Layer 3: Philosophy filtering (simplified)
    Layer 4: Final ranking
    """

    def __init__(self, universe: ETFUniverse, config: Config):
        self.universe = universe
        self.config = config
        self._random_seed = 42
        self._base_position_size = DEFAULT_BASE_POSITION_SIZE

        # Initialize layers
        self._macro_layer = MacroLayer()
        self._sector_layer = SectorLayer()
        self._investor_layer = SuperinvestorLayer()
        self._decision_layer = DecisionLayer()

    def _conviction_to_rating(self, conviction: int) -> SignalRating:
        """Map conviction (1-100) to 5-tier rating."""
        if conviction >= 80:
            return SignalRating.BUY
        elif conviction >= 65:
            return SignalRating.OVERWEIGHT
        elif conviction >= 45:
            return SignalRating.HOLD
        elif conviction >= 30:
            return SignalRating.UNDERWEIGHT
        else:
            return SignalRating.SELL

    def _calculate_position_size(
        self, conviction: int, base_size: float = None
    ) -> float:
        """Calculate position size based on conviction.

        Higher conviction = larger position (up to 1.5x base)
        Lower conviction = smaller position (down to 0.5x base)
        """
        if base_size is None:
            base_size = self._base_position_size

        # Scale factor: conviction/50 gives 0.5x at 25 conviction, 1.0x at 50, 1.5x at 75
        scale = conviction / 50.0
        scale = max(0.5, min(1.5, scale))  # Clamp to [0.5, 1.5]

        return round(base_size * scale, 2)

    def generate_signals(
        self, macro_context: Optional[MacroContext] = None
    ) -> list[Recommendation]:
        """Generate trading signals through all layers."""
        # Use new layered approach
        return self._generate_signals_layered()

    def _generate_signals_layered(self) -> list[Recommendation]:
        """Generate signals using the new four-layer architecture."""
        # Sample market context (would come from data provider in production)
        market_context = self._sample_market_context()

        # Layer 1: Macro regime assessment
        macro_outputs = self._macro_layer.evaluate(market_context)

        # Layer 2: Sector ranking
        sector_outputs = self._sector_layer.evaluate(macro_outputs)

        # Layer 3: Superinvestor reweighting
        investor_outputs = self._investor_layer.evaluate(sector_outputs)

        # Layer 4: Decision aggregation
        decision_result = self._decision_layer.evaluate(investor_outputs)

        # Convert to Recommendations
        recommendations = []
        for proposal in decision_result.proposals:
            direction = (
                SignalDirection.LONG
                if proposal.get("direction") == "LONG"
                else SignalDirection.NEUTRAL
            )
            conviction = proposal.get("conviction", 50)
            rating = self._conviction_to_rating(conviction)
            position_size = self._calculate_position_size(conviction)

            recommendations.append(
                Recommendation(
                    ticker=proposal["ticker"],
                    direction=direction,
                    conviction=conviction,
                    thesis=decision_result.rationale,
                    sector=proposal.get("source_filter", "unknown"),
                    rating=rating,
                    position_size_pct=position_size,
                )
            )

        return recommendations

    def _sample_market_context(self) -> dict:
        """Sample market context - simplified for now."""
        random.seed(self._random_seed)
        return {
            "fed_bias": random.uniform(-0.5, 0.5),
            "rate_path": random.uniform(-0.3, 0.3),
            "cpi_trend": random.uniform(-0.3, 0.3),
            "gdp_growth": random.uniform(0, 0.3),
            "vix_level": random.uniform(10, 30),
        }

    def generate_signals(
        self, macro_context: Optional[MacroContext] = None
    ) -> list[Recommendation]:
        """Generate trading signals through all layers."""
        if macro_context is None:
            macro_context = self._assess_macro()

        sector_signals = self._assess_sectors(macro_context)

        recommendations = self._rank_signals(sector_signals)

        return recommendations

    def _assess_macro(self) -> MacroContext:
        """Layer 1: Macro regime assessment."""
        # Simplified macro assessment
        # In production, this would query external data
        random.seed(self._random_seed)

        regimes = ["RISK_ON", "RISK_OFF", "NEUTRAL"]
        weights = [0.4, 0.3, 0.3]

        regime = random.choices(regimes, weights=weights)[0]

        return MacroContext(
            regime=regime,
            conviction=random.randint(60, 90),
            key_factors=["earnings_season", "fed_expectations", "volatility_regime"],
        )

    def _assess_sectors(self, macro: MacroContext) -> list[SectorSignal]:
        """Layer 2: Sector assessment based on macro regime."""
        random.seed(self._random_seed + 1)

        signals = []

        # Map regime to sector bias
        regime_sector_bias = {
            "RISK_ON": [Sector.TECHNOLOGY, Sector.CONSUMER, Sector.INDUSTRIALS],
            "RISK_OFF": [Sector.UTILITIES, Sector.BROAD_MARKET, Sector.BONDS],
            "NEUTRAL": [Sector.FINANCIALS, Sector.ENERGY, Sector.HEALTHCARE],
        }

        favored = regime_sector_bias.get(macro.regime, [Sector.BROAD_MARKET])

        # Generate signals for each sector
        all_sectors = list(Sector)
        for sector in all_sectors[:8]:  # Limit to 8 sectors
            if sector in favored:
                direction = SignalDirection.LONG
                conviction = random.randint(65, 90)
            else:
                direction = (
                    SignalDirection.SHORT
                    if random.random() > 0.5
                    else SignalDirection.NEUTRAL
                )
                conviction = random.randint(30, 55)

            # Find best ETF in sector
            sector_etfs = self.universe.get_by_sector(sector)
            top_pick = sector_etfs[0].ticker if sector_etfs else None

            signals.append(
                SectorSignal(
                    sector=sector,
                    direction=direction,
                    conviction=conviction,
                    top_pick=top_pick,
                )
            )

        return signals

    def _rank_signals(self, sector_signals: list[SectorSignal]) -> list[Recommendation]:
        """Layer 3-4: Filter and rank into recommendations."""
        random.seed(self._random_seed + 2)

        recommendations = []

        for ss in sector_signals:
            if ss.direction == SignalDirection.NEUTRAL or ss.conviction < 40:
                continue

            if ss.top_pick:
                rating = self._conviction_to_rating(ss.conviction)
                position_size = self._calculate_position_size(ss.conviction)

                rec = Recommendation(
                    ticker=ss.top_pick,
                    direction=ss.direction,
                    conviction=ss.conviction,
                    thesis=f"{ss.sector.value} sector {ss.direction.value} based on macro regime",
                    sector=ss.sector.value,
                    rating=rating,
                    position_size_pct=position_size,
                )
                recommendations.append(rec)

        # Sort by conviction (highest first)
        recommendations.sort(key=lambda r: r.conviction, reverse=True)

        # Limit to top recommendations
        return recommendations[:5]

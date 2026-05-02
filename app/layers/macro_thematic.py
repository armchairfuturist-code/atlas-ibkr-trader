"""Macro-Thematic Layer for geopolitical event analysis.

Connects prediction market odds to commodity/sector impacts.
Provides thematic recommendations for trading decisions.

This is the integration point between:
- Polymarket odds (geopolitical events)
- Sector impacts (Iran → Energy bullish)
- Debate system (final recommendations)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional
from enum import Enum

from app.agents.geopolitical_agent import GeopoliticalSentimentAgent, GeopoliticalSignal
from app.data.polymarket_client import PolymarketClient


logger = logging.getLogger(__name__)


class ThematicDirection(Enum):
    """Direction of thematic recommendation."""

    LONG = "LONG"  # Buy/overweight
    SHORT = "SHORT"  # Sell/underweight or enter short position
    NEUTRAL = "NEUTRAL"  # No clear directional bias


@dataclass
class SectorRecommendation:
    """Recommendation for a specific sector."""

    sector: str
    direction: ThematicDirection
    conviction: int  # 1-100
    thesis: str
    etf_tickers: list[str]  # Relevant ETFs
    risk_factors: list[str]


@dataclass
class MacroThematicReport:
    """Complete macro-thematic analysis report."""

    theme: str
    probability: float
    overall_direction: ThematicDirection
    confidence: int
    sector_recommendations: list[SectorRecommendation]
    key_events: list[str]
    thesis: str


# Sector to ETF mappings
SECTOR_ETFS: dict[str, dict[str, list[str]]] = {
    "ENERGY": {
        "long": ["XLE", "VDE", "IXC", "XOP"],  # Energy ETFs
        "short": ["ERY", "DUG"],  # Inverse energy ETFs
    },
    "DEFENSE": {
        "long": ["XAR", "ITA", "PPA"],  # Defense ETFs
        "short": [],  # Limited short options
    },
    "TECH": {
        "long": ["QQQ", "XLK", "VGT"],  # Tech ETFs
        "short": ["PSQ", "SQQQ"],  # Inverse tech ETFs
    },
    "FINANCIAL": {
        "long": ["XLF", "VFH", "KBE"],  # Financial ETFs
        "short": ["SEF", "SKF"],  # Inverse financial ETFs
    },
    "COMMODITIES": {
        "long": ["DBC", "GSG", "USCI"],  # Broad commodity ETFs
        "short": [],  # Limited short options
    },
    "AGRICULTURE": {
        "long": ["DBA", "WEAT", "CORN"],  # Agriculture ETFs
        "short": [],  # Limited short options
    },
    "METALS": {
        "long": ["GLD", "IAU", "SLV"],  # Gold/Silver ETFs
        "short": ["GLL", "ZSL"],  # Inverse metal ETFs
    },
    "OIL": {
        "long": ["USO", "BNO", "XLE"],  # Oil ETFs
        "short": ["DNO", "USO puts"],  # Inverse oil
    },
}

# Event to thematic mapping (enhanced from GeopoliticalSentimentAgent)
EVENT_THEMES: dict[str, dict[str, Any]] = {
    "iran": {
        "theme": "Iran Geopolitical Tension",
        "description": "Iran conflict, sanctions, or regime change affecting energy markets",
        "primary_sectors": ["ENERGY", "OIL", "DEFENSE"],
        "secondary_sectors": ["TECH", "FINANCIAL"],
        "key_etfs": ["XLE", "USO", "XAR"],
        "impact_multiplier": 1.5,
    },
    "china": {
        "theme": "China Trade/Geopolitical",
        "description": "China-US tensions, Taiwan, trade wars affecting tech and manufacturing",
        "primary_sectors": ["TECH", "COMMODITIES"],
        "secondary_sectors": ["FINANCIAL"],
        "key_etfs": ["QQQ", "DBC"],
        "impact_multiplier": 1.2,
    },
    "russia": {
        "theme": "Russia/Ukraine Conflict",
        "description": "Eastern European conflict affecting energy and agriculture",
        "primary_sectors": ["ENERGY", "AGRICULTURE", "DEFENSE"],
        "secondary_sectors": ["FINANCIAL"],
        "key_etfs": ["XLE", "WEAT", "XAR"],
        "impact_multiplier": 1.3,
    },
    "oil": {
        "theme": "Oil Supply Shock",
        "description": "OPEC decisions, supply disruptions, energy crisis",
        "primary_sectors": ["ENERGY", "OIL"],
        "secondary_sectors": ["COMMODITIES", "FINANCIAL"],
        "key_etfs": ["USO", "XLE"],
        "impact_multiplier": 1.4,
    },
    "inflation": {
        "theme": "Inflation/Rate Policy",
        "description": "Fed policy, inflation data, interest rate decisions",
        "primary_sectors": ["FINANCIAL", "TECH"],
        "secondary_sectors": ["COMMODITIES"],
        "key_etfs": ["XLF", "QQQ", "GLD"],
        "impact_multiplier": 1.0,
    },
    "recession": {
        "theme": "Economic Recession Risk",
        "description": "GDP contraction, unemployment, recession indicators",
        "primary_sectors": ["DEFENSE", "COMMODITIES"],
        "secondary_sectors": ["TECH", "FINANCIAL"],
        "key_etfs": ["GLD", "XAR"],
        "impact_multiplier": 1.1,
    },
}


class MacroThematicLayer:
    """Macro-thematic analysis layer.

    Integrates prediction market odds with sector impacts
    to produce thematic trading recommendations.
    """

    def __init__(
        self,
        geopolitical_agent: Optional[GeopoliticalSentimentAgent] = None,
        polymarket_client: Optional[PolymarketClient] = None,
    ):
        """Initialize macro-thematic layer."""
        self.geo_agent = geopolitical_agent or GeopoliticalSentimentAgent()
        self.polymarket = polymarket_client or PolymarketClient()

    def analyze(self, theme: Optional[str] = None) -> MacroThematicReport:
        """Analyze macro-thematic conditions.

        Args:
            theme: Optional specific theme to analyze (e.g., "iran", "oil")
                  If None, analyzes all available themes.

        Returns:
            MacroThematicReport with sector recommendations
        """
        # Get geopolitical signals
        if theme:
            signal = self.geo_agent.analyze_specific(theme)
            signals = [signal]
        else:
            signal = self.geo_agent.analyze()
            signals = [signal]

        # Get trending geopolitical markets
        try:
            markets = self.polymarket.get_geopolitical_markets()
        except Exception as e:
            logger.warning(f"Failed to get Polymarket data: {e}")
            markets = []

        # Determine overall direction
        overall_direction = self._determine_overall_direction(signals)

        # Generate sector recommendations
        sector_recs = self._generate_sector_recommendations(signals)

        # Extract key events
        key_events = self._extract_key_events(markets)

        # Build thesis
        thesis = self._build_thesis(signals, sector_recs, key_events)

        # Calculate confidence
        confidence = self._calculate_confidence(signals)

        return MacroThematicReport(
            theme=theme or "Global Geopolitical",
            probability=signals[0].probability if signals else 0.5,
            overall_direction=overall_direction,
            confidence=confidence,
            sector_recommendations=sector_recs,
            key_events=key_events,
            thesis=thesis,
        )

    def recommend_etf(
        self,
        sector: str,
        direction: ThematicDirection,
    ) -> list[str]:
        """Get ETF recommendations for a sector and direction.

        Args:
            sector: Target sector (e.g., "ENERGY", "OIL")
            direction: LONG or SHORT

        Returns:
            List of recommended ETF tickers
        """
        sector_upper = sector.upper()
        if sector_upper not in SECTOR_ETFS:
            logger.warning(f"Unknown sector: {sector}")
            return []

        etf_map = SECTOR_ETFS[sector_upper]
        direction_key = "long" if direction == ThematicDirection.LONG else "short"

        return etf_map.get(direction_key, [])

    def get_best_plays(self, max_plays: int = 3) -> list[dict[str, Any]]:
        """Get top trading plays for current conditions.

        Args:
            max_plays: Maximum number of plays to return

        Returns:
            List of top plays with sector, direction, ETFs, and confidence
        """
        report = self.analyze()

        # Sort by conviction
        sorted_recs = sorted(
            report.sector_recommendations,
            key=lambda r: (r.direction != ThematicDirection.NEUTRAL, r.conviction),
            reverse=True,
        )

        plays = []
        for rec in sorted_recs[:max_plays]:
            if rec.direction == ThematicDirection.NEUTRAL:
                continue

            etfs = self.recommend_etf(rec.sector, rec.direction)
            if not etfs:
                # Fallback to long ETFs if short not available
                etfs = self.recommend_etf(rec.sector, ThematicDirection.LONG)

            plays.append(
                {
                    "sector": rec.sector,
                    "direction": rec.direction.value,
                    "conviction": rec.conviction,
                    "etfs": etfs[:2],  # Top 2 ETFs
                    "thesis": rec.thesis,
                }
            )

        return plays

    def _determine_overall_direction(
        self, signals: list[GeopoliticalSignal]
    ) -> ThematicDirection:
        """Determine overall thematic direction from signals."""
        if not signals:
            return ThematicDirection.NEUTRAL

        # Weight by confidence
        weighted_sum = 0.0
        total_weight = 0.0

        for signal in signals:
            if not signal.sector_weights:
                continue

            # Calculate average sector weight
            avg_weight = sum(signal.sector_weights.values()) / len(
                signal.sector_weights
            )
            weighted_sum += avg_weight * signal.confidence
            total_weight += signal.confidence

        if total_weight == 0:
            return ThematicDirection.NEUTRAL

        avg_direction = weighted_sum / total_weight

        if avg_direction > 0.5:
            return ThematicDirection.LONG
        elif avg_direction < -0.5:
            return ThematicDirection.SHORT
        else:
            return ThematicDirection.NEUTRAL

    def _generate_sector_recommendations(
        self, signals: list[GeopoliticalSignal]
    ) -> list[SectorRecommendation]:
        """Generate sector-specific recommendations."""
        recommendations = []

        # Aggregate sector weights from all signals
        sector_weights: dict[str, list[float]] = {}
        for signal in signals:
            if not signal.sector_weights:
                continue
            for sector, weight in signal.sector_weights.items():
                if sector not in sector_weights:
                    sector_weights[sector] = []
                sector_weights[sector].append(weight * signal.confidence)

        # Calculate average weight per sector
        for sector, weights in sector_weights.items():
            avg_weight = sum(weights) / len(weights)

            # Determine direction
            if avg_weight > 0.3:
                direction = ThematicDirection.LONG
                thesis = f"{sector} benefits from geopolitical tension (weight: {avg_weight:+.2f})"
            elif avg_weight < -0.3:
                direction = ThematicDirection.SHORT
                thesis = f"{sector} negatively impacted by geopolitical tension (weight: {avg_weight:+.2f})"
            else:
                direction = ThematicDirection.NEUTRAL
                thesis = f"{sector} has mixed impact from geopolitical tension (weight: {avg_weight:+.2f})"

            # Get ETF tickers
            etfs = self.recommend_etf(sector, direction)

            # Risk factors
            risk_factors = [
                f"Geopolitical events are unpredictable",
                f"Probability: {signals[0].probability:.0%}"
                if signals
                else "Unknown probability",
            ]
            if direction == ThematicDirection.SHORT:
                risk_factors.append("Short positions have unlimited downside risk")

            recommendations.append(
                SectorRecommendation(
                    sector=sector,
                    direction=direction,
                    conviction=min(95, max(20, int(abs(avg_weight) * 100))),
                    thesis=thesis,
                    etf_tickers=etfs,
                    risk_factors=risk_factors,
                )
            )

        # Sort by conviction
        recommendations.sort(key=lambda r: r.conviction, reverse=True)

        return recommendations

    def _extract_key_events(self, markets: list[dict[str, Any]]) -> list[str]:
        """Extract key events from Polymarket data."""
        events = []

        for market in markets[:5]:
            question = market.get("question", "")
            prob = market.get("yes_probability", 0)

            if prob > 0.6:
                events.append(f"High probability: {question[:60]}... ({prob:.0%})")
            elif prob > 0.4:
                events.append(f"Possible: {question[:60]}... ({prob:.0%})")

        return events[:5]

    def _build_thesis(
        self,
        signals: list[GeopoliticalSignal],
        sector_recs: list[SectorRecommendation],
        key_events: list[str],
    ) -> str:
        """Build comprehensive thesis."""
        parts = []

        # Overall assessment
        if signals:
            parts.append(
                f"Geopolitical tension probability: {signals[0].probability:.0%}"
            )
            parts.append(f"Confidence: {signals[0].confidence:.0%}")

        # Top sectors
        long_sectors = [r for r in sector_recs if r.direction == ThematicDirection.LONG]
        short_sectors = [
            r for r in sector_recs if r.direction == ThematicDirection.SHORT
        ]

        if long_sectors:
            parts.append(
                f"\nLong opportunities: {', '.join(r.sector for r in long_sectors[:2])}"
            )
        if short_sectors:
            parts.append(
                f"Short opportunities: {', '.join(r.sector for r in short_sectors[:2])}"
            )

        # Key events
        if key_events:
            parts.append(f"\nKey events: {key_events[0]}")

        return "\n".join(parts)

    def _calculate_confidence(self, signals: list[GeopoliticalSignal]) -> int:
        """Calculate overall confidence."""
        if not signals:
            return 20

        # Average confidence weighted by probability
        total_confidence = 0.0
        total_weight = 0.0

        for signal in signals:
            weight = signal.markets_analyzed + 1
            total_confidence += signal.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 20

        return min(95, max(20, int(total_confidence / total_weight * 100)))


# Singleton instance
macro_thematic_layer = MacroThematicLayer()

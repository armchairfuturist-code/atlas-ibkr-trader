"""Geopolitical sentiment agent using Polymarket prediction markets.

Analyzes prediction market odds for geopolitical events (war, Iran crisis, oilshortages)
to provide leading sentiment indicators for trading decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional

from app.agents.research_note import ResearchNote
from app.data.polymarket_client import PolymarketClient, polymarket_client


logger = logging.getLogger(__name__)


# Sector impact mappings for geopolitical events
EVENT_SECTOR_IMPACT: dict[str, dict[str, float]] = {
    # "event_pattern": {"sector": impact_weight, ...}
    "iran": {
        "ENERGY": 1.5,  # Strong bullish for energy
        "DEFENSE": 0.8,  # Moderately bullish for defense
        "TECH": -0.3,  # Slightly bearish (supply chain concerns)
        "FINANCIAL": -0.2,  # Slightly bearish (volatility)
    },
    "war": {
        "ENERGY": 1.3,
        "DEFENSE": 1.2,
        "TECH": -0.2,
        "FINANCIAL": -0.3,
    },
    "ceasefire": {
        "ENERGY": -0.5,  # Bearish for energy (peace = less price spike)
        "DEFENSE": -0.4,  # Bearish for defense
        "TECH": 0.2,  # Bullish for tech (stability)
    },
    "oil": {
        "ENERGY": 1.0,
        "INDUSTRIAL": -0.3,  # Bearish (higher input costs)
        "CONSUMER": -0.2,  # Bearish (lower discretionary spending)
    },
    "sanctions": {
        "ENERGY": 1.2,
        "FINANCIAL": -0.4,  # Bearish (cross-border issues)
        "TECH": -0.3,
    },
    "regime": {
        "ENERGY": 1.4,  # High uncertainty = bullish for energy
        "DEFENSE": 0.9,
        "FINANCIAL": -0.5,
    },
}

# Probability thresholds for sentiment scoring
PROB_THRESHOLD_HIGH = 0.7  # High probability = strong signal
PROB_THRESHOLD_MEDIUM = 0.55  # Medium probability = moderate signal
PROB_THRESHOLD_LOW = 0.45  # Below this = opposite signal


@dataclass
class GeopoliticalSignal:
    """Signal from prediction market analysis."""

    event: str
    probability: float
    sector_weights: dict[str, float]
    confidence: float
    thesis: str
    markets_analyzed: int
    raw_markets: list[dict[str, Any]] | None = None


class GeopoliticalSentimentAgent:
    """Analyzes prediction market odds for geopolitical sentiment.

    Uses Polymarket data to detect:
    - War/conflict probabilities
    - Energy supply disruption odds
    - Commodity shortage signals
    - Market-moving event likelihoods

    These are leading indicators - often shift before traditional markets react.
    """

    def __init__(self, client: PolymarketClient | None = None):
        self.client = client or polymarket_client

    def analyze(self, sector_filter: list[str] | None = None) -> GeopoliticalSignal:
        """Analyze geopolitical sentiment from prediction markets.

        Args:
            sector_filter: Optional list of sectors to focus analysis on.
                          If None, analyzes all sectors.

        Returns:
            GeopoliticalSignal with sector weights and thesis.
        """
        # Collect markets for geopolitical keywords
        markets = self.client.get_geopolitical_markets()

        if not markets:
            logger.warning("No geopolitical markets found, using fallback")
            return self._fallback_signal()

        # Aggregate sector weights from markets
        sector_weights: dict[str, list[float]] = {}
        market_count = 0

        for market in markets:
            question = market.get("question", "").lower()
            prob = market.get("yes_probability", 0.5)

            # Match event patterns to sector impacts
            for event_pattern, impacts in EVENT_SECTOR_IMPACT.items():
                if event_pattern in question:
                    market_count += 1
                    for sector, base_weight in impacts.items():
                        if sector_filter and sector not in sector_filter:
                            continue
                        # Weight by probability - high prob = strong signal
                        weight_multiplier = self._probability_to_multiplier(prob)
                        weighted_impact = base_weight * weight_multiplier
                        if sector not in sector_weights:
                            sector_weights[sector] = []
                        sector_weights[sector].append(weighted_impact)
                    break  # Only match first pattern per market

        # Average sector weights
        final_weights: dict[str, float] = {}
        for sector, weights in sector_weights.items():
            if weights:
                final_weights[sector] = sum(weights) / len(weights)

        # Calculate overall confidence
        confidence = min(1.0, market_count / 10.0)  # Max confidence with 10+ markets

        # Generate thesis
        thesis = self._generate_thesis(final_weights, markets)

        return GeopoliticalSignal(
            event="geopolitical_aggregate",
            probability=self._aggregate_probability(markets),
            sector_weights=final_weights,
            confidence=confidence,
            thesis=thesis,
            markets_analyzed=market_count,
            raw_markets=markets,
        )

    def analyze_specific(
        self, event_pattern: str, sector_filter: list[str] | None = None
    ) -> GeopoliticalSignal:
        """Analyze specific event pattern (e.g., "iran", "oil").

        Args:
            event_pattern: Keyword to search for in markets.
            sector_filter: Optional sector filter.

        Returns:
            GeopoliticalSignal for the specific event.
        """
        markets = self.client.search_markets(event_pattern, limit=20)

        if not markets:
            logger.warning("No markets found for pattern: %s", event_pattern)
            return self._fallback_signal()

        # Find matching impact weights
        impacts = EVENT_SECTOR_IMPACT.get(event_pattern.lower(), {})
        if not impacts:
            # Try partial match
            for pattern, weights in EVENT_SECTOR_IMPACT.items():
                if pattern in event_pattern.lower() or event_pattern.lower() in pattern:
                    impacts = weights
                    break

        sector_weights: dict[str, float] = {}
        probabilities: list[float] = []

        for market in markets:
            question = market.get("question", "").lower()
            prob = market.get("yes_probability", 0.5)
            probabilities.append(prob)

            for sector, base_weight in impacts.items():
                if sector_filter and sector not in sector_filter:
                    continue
                weight_multiplier = self._probability_to_multiplier(prob)
                weighted_impact = base_weight * weight_multiplier
                if sector not in sector_weights:
                    sector_weights[sector] = 0.0
                sector_weights[sector] += weighted_impact / len(markets)

        confidence = min(1.0, len(markets) / 5.0)
        avg_prob = sum(probabilities) / len(probabilities) if probabilities else 0.5

        thesis = self._generate_thesis_for_event(
            event_pattern, avg_prob, sector_weights
        )

        return GeopoliticalSignal(
            event=event_pattern,
            probability=avg_prob,
            sector_weights=sector_weights,
            confidence=confidence,
            thesis=thesis,
            markets_analyzed=len(markets),
            raw_markets=markets,
        )

    def create_research_note(self, signal: GeopoliticalSignal) -> ResearchNote:
        """Convert GeopoliticalSignal to ResearchNote for debate system.

        Args:
            signal: GeopoliticalSignal from analysis.

        Returns:
            ResearchNote compatible with debate orchestrator.
        """
        # Determine overall bias from sector weights
        avg_weight = (
            sum(signal.sector_weights.values()) / len(signal.sector_weights)
            if signal.sector_weights
            else 0.0
        )

        if avg_weight > 0.3:
            bias = "bullish"
            thesis_direction = (
                "Geopolitical tensions support higher commodity and defense prices."
            )
        elif avg_weight < -0.3:
            bias = "bearish"
            thesis_direction = "Geopolitical stability suggests lower risk premium."
        else:
            bias = "neutral"
            thesis_direction = "Mixed geopolitical signals, no clear directional bias."

        # Format thesis with market data
        thesis_parts = [
            f"**Geopolitical Analysis** ({signal.confidence:.0%} confidence)",
            "",
            f"Event: {signal.event}",
            f"Probability: {signal.probability:.1%}",
            f"Markets analyzed: {signal.markets_analyzed}",
            "",
            "**Sector Impact:**",
        ]

        for sector, weight in sorted(
            signal.sector_weights.items(), key=lambda x: abs(x[1]), reverse=True
        ):
            direction = "BULLISH" if weight > 0 else "BEARISH"
            thesis_parts.append(f"  - {sector}: {direction} ({weight:+.2f})")

        thesis_parts.extend(["", signal.thesis, "", thesis_direction])

        return ResearchNote(
            thesis=signal.thesis,
            confidence=int(signal.confidence * 100),
            key_points=[
                f"{sector}: {'BULLISH' if weight > 0 else 'BEARISH'} ({weight:+.2f})"
                for sector, weight in sorted(
                    signal.sector_weights.items(), key=lambda x: abs(x[1]), reverse=True
                )[:3]
            ],
            persona="geopolitical",
            supporting_indicators={
                "event": signal.event,
                "probability": signal.probability,
                "sector_weights": signal.sector_weights,
                "markets_analyzed": signal.markets_analyzed,
            },
        )

    def _probability_to_multiplier(self, prob: float) -> float:
        """Convert probability to impact multiplier.

        High probability (>70%) = strong signal (1.0)
        Medium probability (55-70%) = moderate signal (0.7)
        Low probability (<45%) = weak/contrarian signal (0.3-0.5)
        """
        if prob >= PROB_THRESHOLD_HIGH:
            return 1.0
        elif prob >= PROB_THRESHOLD_MEDIUM:
            return 0.7
        elif prob <= PROB_THRESHOLD_LOW:
            return 0.3
        else:
            return 0.5

    def _aggregate_probability(self, markets: list[dict[str, Any]]) -> float:
        """Calculate aggregate probability from multiple markets."""
        if not markets:
            return 0.5
        probabilities = [m.get("yes_probability", 0.5) for m in markets]
        return sum(probabilities) / len(probabilities)

    def _generate_thesis(
        self, sector_weights: dict[str, float], markets: list[dict[str, Any]]
    ) -> str:
        """Generate human-readable thesis from analysis."""
        if not sector_weights:
            return "No significant geopolitical signals detected.Prediction markets show balanced views."

        # Find strongest signals
        sorted_sectors = sorted(
            sector_weights.items(), key=lambda x: abs(x[1]), reverse=True
        )
        top_bullish = [s for s in sorted_sectors if s[1] > 0][:2]
        top_bearish = [s for s in sorted_sectors if s[1] < 0][:2]

        parts = []

        if top_bullish:
            bullish_str = ", ".join(f"{s[0]} ({s[1]:+.2f})" for s in top_bullish)
            parts.append(f"**Bullish sectors:** {bullish_str}")

        if top_bearish:
            bearish_str = ", ".join(f"{s[0]} ({s[1]:+.2f})" for s in top_bearish)
            parts.append(f"**Bearish sectors:** {bearish_str}")

        # Add context from markets
        high_prob_markets = [
            m for m in markets if m.get("yes_probability", 0) > PROB_THRESHOLD_HIGH
        ][:3]

        if high_prob_markets:
            parts.append("**High-probability events:**")
            for m in high_prob_markets:
                parts.append(
                    f"  - {m.get('question', 'Unknown')[:80]}... ({m.get('yes_probability', 0):.0%})"
                )

        return (
            "\n".join(parts) if parts else "Mixed signals, no clear directional bias."
        )

    def _generate_thesis_for_event(
        self,
        event_pattern: str,
        avg_prob: float,
        sector_weights: dict[str, float],
    ) -> str:
        """Generate thesis for specific event pattern."""
        direction = "bullish" if avg_prob > 0.5 else "bearish"
        confidence_desc = (
            "high confidence"
            if avg_prob > PROB_THRESHOLD_HIGH or avg_prob < PROB_THRESHOLD_LOW
            else "moderate confidence"
            if avg_prob > PROB_THRESHOLD_MEDIUM or avg_prob < 0.45
            else "low confidence"
        )

        sector_impacts = []
        for sector, weight in sorted(
            sector_weights.items(), key=lambda x: abs(x[1]), reverse=True
        ):
            impact_dir = "BULLISH" if weight > 0 else "BEARISH"
            sector_impacts.append(f"{sector}: {impact_dir} impact ({weight:+.2f})")

        return (
            f"**{event_pattern.upper()} Analysis** ({confidence_desc})\n"
            f"Average probability: {avg_prob:.1%}\n"
            f"Directional bias: {direction}\n\n"
            f"Sector impacts:\n" + "\n".join(f"  - {i}" for i in sector_impacts)
        )

    def _fallback_signal(self) -> GeopoliticalSignal:
        """Return fallback signal when no data available."""
        return GeopoliticalSignal(
            event="fallback",
            probability=0.5,
            sector_weights={},
            confidence=0.0,
            thesis="Unable to fetch geopolitical market data. Using neutral bias.",
            markets_analyzed=0,
            raw_markets=None,
        )


# Singleton instance
geopolitical_agent = GeopoliticalSentimentAgent()

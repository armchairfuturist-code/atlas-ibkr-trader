"""Research manager - judges bull/bear debate and creates investment plan.

Inspired by TradingAgents' research manager that synthesizes bull/bear
research into a final investment recommendation.

Enhanced with geopolitical sentiment integration from prediction markets.
"""

import logging
from typing import Optional

from app.agents.research_note import ResearchNote, InvestmentPlan
from app.agents.geopolitical_agent import GeopoliticalSignal
from app.schemas import SignalRating

logger = logging.getLogger(__name__)


class ResearchManager:
    """Judges bull/bear debate, creates investment plan."""

    def judge(
        self,
        bull_note: ResearchNote,
        bear_note: ResearchNote,
        geopolitical_signal: Optional[GeopoliticalSignal] = None,
    ) -> InvestmentPlan:
        """Evaluate bull and bear notes, produce investment plan.

        Args:
            bull_note: Research note from bull researcher
            bear_note: Research note from bear researcher
            geopolitical_signal: Optional geopolitical sentiment from prediction markets

        Returns:
            InvestmentPlan with rating, conviction, and thesis
        """
        ticker = self._extract_ticker(bull_note.thesis)

        # Calculate conviction based on relative confidence
        confidence_diff = bull_note.confidence - bear_note.confidence
        abs_avg_confidence = (bull_note.confidence + bear_note.confidence) / 2

        # Adjust conviction based on geopolitical signal
        geo_adjustment = 0
        if geopolitical_signal:
            geo_adjustment = self._calculate_geopolitical_adjustment(
                geopolitical_signal
            )

        # Determine bull/bear contribution weights
        if confidence_diff > 10:
            # Bullish case stronger
            bull_contribution = 0.7
            bear_contribution = 0.3
        elif confidence_diff < -10:
            # Bearish case stronger
            bull_contribution = 0.3
            bear_contribution = 0.7
        else:
            # Roughly balanced
            bull_contribution = 0.5
            bear_contribution = 0.5

        # Calculate conviction
        conviction = int(abs_avg_confidence + abs(confidence_diff) * 0.3)
        conviction = min(95, max(20, conviction))

        # Apply geopolitical adjustment to conviction
        conviction = int(conviction + geo_adjustment * 10)
        conviction = min(95, max(20, conviction))

        # Determine rating
        rating = self._determine_rating(
            conviction, confidence_diff, bull_note, bear_note, geopolitical_signal
        )

        # Build thesis
        thesis = self._build_thesis(rating, bull_note, bear_note, geopolitical_signal)

        # Extract insights and risk factors
        key_insights = self._extract_insights(bull_note, bear_note, geopolitical_signal)
        risk_factors = self._extract_risk_factors(
            bull_note, bear_note, geopolitical_signal
        )

        return InvestmentPlan(
            ticker=ticker,
            rating=rating,
            conviction=conviction,
            thesis=thesis,
            key_insights=key_insights,
            risk_factors=risk_factors,
            bull_contribution=bull_contribution,
            bear_contribution=bear_contribution,
        )

    def _calculate_geopolitical_adjustment(self, signal: GeopoliticalSignal) -> float:
        """Calculate conviction adjustment from geopolitical signal.

        Returns:
            Adjustment value (-1 to +1) to add to conviction.
        """
        if not signal.sector_weights:
            return 0.0

        # Average sector weight indicates directional bias
        avg_weight = sum(signal.sector_weights.values()) / len(signal.sector_weights)

        # Confidence moderates the adjustment
        adjustment = avg_weight * signal.confidence

        return max(-1.0, min(1.0, adjustment))

    def _extract_ticker(self, thesis: str) -> str:
        """Extract ticker from thesis string."""
        parts = thesis.split(":")
        if len(parts) > 0:
            # Assume first word after any prefix is the ticker
            first_part = parts[0].strip()
            words = first_part.split()
            if words:
                return words[-1]  # Last word before colon is usually ticker
        return "UNKNOWN"

    def _determine_rating(
        self,
        conviction: int,
        confidence_diff: float,
        bull_note: ResearchNote,
        bear_note: ResearchNote,
        geopolitical_signal: Optional[GeopoliticalSignal] = None,
    ) -> SignalRating:
        """Determine the 5-tier rating based on analysis.

        Incorporates geopolitical sentiment as a modifier.
        """
        # Adjust confidence_diff based on geopolitical signal
        adjusted_diff = confidence_diff
        if geopolitical_signal:
            # If geopolitical signal supports bullish case, boost diff
            avg_weight = (
                sum(geopolitical_signal.sector_weights.values())
                / len(geopolitical_signal.sector_weights)
                if geopolitical_signal.sector_weights
                else 0.0
            )
            # Add geopolitical bias to confidence diff
            adjusted_diff += avg_weight * 10 * geopolitical_signal.confidence

        if adjusted_diff > 15 and conviction >= 60:
            return SignalRating.BUY
        elif adjusted_diff > 5 and conviction >= 55:
            return SignalRating.OVERWEIGHT
        elif adjusted_diff < -15 and conviction >= 60:
            return SignalRating.SELL
        elif adjusted_diff < -5 and conviction >= 55:
            return SignalRating.UNDERWEIGHT
        elif conviction >= 45:
            return SignalRating.HOLD
        elif conviction < 35:
            # Low conviction on the down side
            if adjusted_diff < -10:
                return SignalRating.UNDERWEIGHT
            return SignalRating.HOLD
        else:
            return SignalRating.HOLD

    def _build_thesis(
        self,
        rating: SignalRating,
        bull_note: ResearchNote,
        bear_note: ResearchNote,
        geopolitical_signal: Optional[GeopoliticalSignal] = None,
    ) -> str:
        """Build human-readable thesis including geopolitical context."""
        rating_str = rating.value

        # Get top bull and bear points
        top_bull = bull_note.key_points[:2] if bull_note.key_points else []
        top_bear = bear_note.key_points[:2] if bear_note.key_points else []

        thesis_parts = [f"{rating_str} rating based on:"]

        if top_bull:
            thesis_parts.append(f"Bull case: {'; '.join(top_bull)}")
        if top_bear:
            thesis_parts.append(f"Bear case: {'; '.join(top_bear)}")

        # Add geopolitical context if available
        if geopolitical_signal and geopolitical_signal.confidence > 0.3:
            thesis_parts.append("")
            thesis_parts.append("**Geopolitical Context:**")
            thesis_parts.append(geopolitical_signal.thesis[:200])

        return " ".join(thesis_parts)

    def _extract_insights(
        self,
        bull_note: ResearchNote,
        bear_note: ResearchNote,
        geopolitical_signal: Optional[GeopoliticalSignal] = None,
    ) -> list[str]:
        """Extract key insights from both notes."""
        insights = []

        # Take top 2 insights from each
        for point in bull_note.key_points[:2]:
            if point not in insights:
                insights.append(f"Bull: {point}")

        for point in bear_note.key_points[:2]:
            if point not in insights:
                insights.append(f"Bear: {point}")

        # Add geopolitical insight if significant
        if geopolitical_signal and geopolitical_signal.confidence > 0.5:
            for sector, weight in sorted(
                geopolitical_signal.sector_weights.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:1]:
                direction = "BULLISH" if weight > 0 else "BEARISH"
                insights.append(f"Geo: {sector} {direction} ({weight:+.2f})")

        return insights[:5]  # Max 5 insights

    def _extract_risk_factors(
        self,
        bull_note: ResearchNote,
        bear_note: ResearchNote,
        geopolitical_signal: Optional[GeopoliticalSignal] = None,
    ) -> list[str]:
        """Extract risk factors from the analysis."""
        # In a real system, would analyze indicators for risks
        # For now, derive from bear thesis points
        risks = []

        for point in bear_note.key_points[:3]:
            if "risk" in point.lower() or "concern" in point.lower():
                risks.append(point)

        # Add geopolitical risk if high probability events
        if geopolitical_signal:
            if geopolitical_signal.probability > 0.7:
                risks.append(
                    f"High geopolitical probability ({geopolitical_signal.probability:.0%}): {geopolitical_signal.event}"
                )
            elif geopolitical_signal.probability > 0.5:
                risks.append(
                    f"Elevated geopolitical risk: {geopolitical_signal.markets_analyzed} markets indicate concern"
                )

        return risks if risks else ["General market risk applies"]

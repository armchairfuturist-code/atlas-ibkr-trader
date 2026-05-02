"""Risk persona definitions for multi-persona debate.

Three personas evaluate trades from different risk perspectives:
- Aggressive: Higher risk tolerance, larger position sizes
- Conservative: Lower risk tolerance, smaller positions
- Neutral: Balanced approach
"""

from dataclasses import dataclass
from typing import Optional

from app.schemas import Recommendation, SignalRating
from app.risk_engine import PortfolioState


@dataclass
class RiskPersona:
    """Base class for risk personas."""

    name: str
    risk_tolerance: float  # 0-1 scale
    position_size_mult: float  # Multiplier on base position size
    max_leverage: float = 1.5  # Max leverage they're comfortable with

    def evaluate(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> "RiskPersonaView":
        """Evaluate a recommendation from this persona's perspective."""
        raise NotImplementedError


@dataclass
class RiskPersonaView:
    """A persona's view on a recommended trade."""

    persona: str
    verdict: str  # "approve", "caution", "reject"
    reasoning: str
    adjusted_size_pct: float  # Persona-adjusted position size
    risk_concerns: list[str]  # Specific concerns from this persona


class AggressiveAnalyst(RiskPersona):
    """Aggressive risk persona - high conviction, large positions."""

    def __init__(self):
        super().__init__(
            name="Aggressive",
            risk_tolerance=0.8,
            position_size_mult=1.3,
            max_leverage=1.5,
        )

    def evaluate(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> RiskPersonaView:
        """Evaluate from aggressive perspective."""
        concerns = []
        adjusted_size = recommendation.position_size_pct * self.position_size_mult

        # High conviction with BUY rating is ideal
        if (
            recommendation.rating == SignalRating.BUY
            and recommendation.conviction >= 75
        ):
            verdict = "approve"
            reasoning = f"High conviction BUY - aggressive sizing warranted"
        elif recommendation.rating == SignalRating.SELL:
            verdict = "reject"
            reasoning = "Aggressive but not contrarian - avoiding SELL signals"
            adjusted_size = 0
        elif recommendation.conviction < 50:
            verdict = "caution"
            reasoning = "Conviction too low for aggressive stance"
            adjusted_size *= 0.5
            concerns.append("Low conviction limits aggressive positioning")
        else:
            verdict = "approve"
            reasoning = "Favorable setup for aggressive position"

        # Check leverage constraints
        projected_leverage = portfolio.gross_leverage
        if projected_leverage > self.max_leverage:
            verdict = "caution"
            concerns.append(
                f"Portfolio leverage {projected_leverage:.2f}x exceeds {self.max_leverage}x threshold"
            )
            adjusted_size *= 0.7

        # Check if already heavily exposed to sector
        sector_exposure = self._get_sector_exposure(recommendation.sector, portfolio)
        if sector_exposure > 25:
            concerns.append(
                f"Heavy sector exposure ({sector_exposure:.1f}%) - concentration risk"
            )
            adjusted_size *= 0.8

        return RiskPersonaView(
            persona=self.name,
            verdict=verdict,
            reasoning=reasoning,
            adjusted_size_pct=round(adjusted_size, 2),
            risk_concerns=concerns,
        )

    def _get_sector_exposure(self, sector: str, portfolio: PortfolioState) -> float:
        """Get current sector exposure percentage."""
        if portfolio.equity <= 0:
            return 0

        sector_value = sum(
            p.current_value for p in portfolio.positions if p.sector == sector
        )
        return (sector_value / portfolio.equity) * 100


class ConservativeAnalyst(RiskPersona):
    """Conservative risk persona - capital preservation focus."""

    def __init__(self):
        super().__init__(
            name="Conservative",
            risk_tolerance=0.3,
            position_size_mult=0.7,
            max_leverage=1.1,
        )

    def evaluate(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> RiskPersonaView:
        """Evaluate from conservative perspective."""
        concerns = []
        adjusted_size = recommendation.position_size_pct * self.position_size_mult

        # Conservative approach: require strong signals
        if (
            recommendation.rating == SignalRating.BUY
            and recommendation.conviction >= 85
        ):
            verdict = "approve"
            reasoning = "Very high conviction required for conservative approval"
        elif recommendation.rating in [SignalRating.UNDERWEIGHT, SignalRating.SELL]:
            verdict = "approve"
            reasoning = "Conservative stance - reducing exposure aligns with thesis"
            # For reduce/sell, conservatively close or avoid
            if recommendation.direction.value == "LONG":
                adjusted_size = 0
        elif recommendation.rating == SignalRating.HOLD:
            verdict = "caution"
            reasoning = "Hold rating suggests waiting for better entry"
            adjusted_size *= 0.5
            concerns.append("Hold rating - patience may be rewarded")
        elif recommendation.conviction >= 70:
            verdict = "approve"
            reasoning = "Good conviction but conservative sizing"
        else:
            verdict = "reject"
            reasoning = "Insufficient conviction for conservative allocation"
            adjusted_size = 0
            concerns.append("Conviction below conservative threshold")

        # Strict leverage check
        projected_leverage = portfolio.gross_leverage
        if projected_leverage > self.max_leverage:
            verdict = "reject"
            concerns.append(
                f"Leverage {projected_leverage:.2f}x exceeds conservative {self.max_leverage}x limit"
            )
            adjusted_size = 0

        # Daily loss check
        if portfolio.daily_pnl_pct < -1.5:
            verdict = "reject"
            concerns.append(
                f"Daily loss {portfolio.daily_pnl_pct:.2f}% - conservative stop triggered"
            )
            adjusted_size = 0

        # Sector concentration
        sector_exposure = self._get_sector_exposure(recommendation.sector, portfolio)
        if sector_exposure > 20:
            concerns.append(
                f"Sector exposure {sector_exposure:.1f}% exceeds 20% conservative limit"
            )
            adjusted_size *= 0.7

        return RiskPersonaView(
            persona=self.name,
            verdict=verdict,
            reasoning=reasoning,
            adjusted_size_pct=round(adjusted_size, 2),
            risk_concerns=concerns,
        )

    def _get_sector_exposure(self, sector: str, portfolio: PortfolioState) -> float:
        """Get current sector exposure percentage."""
        if portfolio.equity <= 0:
            return 0

        sector_value = sum(
            p.current_value for p in portfolio.positions if p.sector == sector
        )
        return (sector_value / portfolio.equity) * 100


class NeutralAnalyst(RiskPersona):
    """Neutral risk persona - balanced approach."""

    def __init__(self):
        super().__init__(
            name="Neutral",
            risk_tolerance=0.5,
            position_size_mult=1.0,
            max_leverage=1.25,
        )

    def evaluate(
        self, recommendation: Recommendation, portfolio: PortfolioState
    ) -> RiskPersonaView:
        """Evaluate from neutral perspective."""
        concerns = []
        adjusted_size = recommendation.position_size_pct * self.position_size_mult

        # Neutral takes the rating at face value with minor adjustments
        if recommendation.rating in [SignalRating.BUY, SignalRating.OVERWEIGHT]:
            verdict = "approve"
            reasoning = f"{recommendation.rating.value} rating is actionable"
        elif recommendation.rating == SignalRating.HOLD:
            verdict = "caution"
            reasoning = "Hold rating - consider smaller size or waiting"
            adjusted_size *= 0.6
            concerns.append("Hold rating suggests reduced conviction")
        elif recommendation.rating in [SignalRating.UNDERWEIGHT, SignalRating.SELL]:
            verdict = "caution"
            reasoning = f"{recommendation.rating.value} rating - avoid new longs"
            if recommendation.direction.value == "LONG":
                adjusted_size = 0
                concerns.append("Avoiding new LONG in UNDERWEIGHT/SELL environment")
        else:
            verdict = "caution"
            reasoning = "Insufficient signal for neutral stance"
            adjusted_size *= 0.5

        # Standard leverage check
        projected_leverage = portfolio.gross_leverage
        if projected_leverage > self.max_leverage:
            verdict = "caution"
            concerns.append(f"Portfolio leverage {projected_leverage:.2f}x elevated")
            adjusted_size *= 0.8

        # Daily loss check
        if portfolio.daily_pnl_pct < -2.0:
            verdict = "caution"
            concerns.append(
                f"Daily loss {portfolio.daily_pnl_pct:.2f}% - risk management activated"
            )
            adjusted_size *= 0.7

        return RiskPersonaView(
            persona=self.name,
            verdict=verdict,
            reasoning=reasoning,
            adjusted_size_pct=round(adjusted_size, 2),
            risk_concerns=concerns,
        )

"""Correlation-adjusted risk management system.

Inspired by ai-hedge-fund's risk management agent.
Calculates position limits based on:
1. Volatility (60-day rolling)
2. Correlation with existing portfolio positions
3. Sector concentration limits

This prevents over-concentration in correlated assets.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Portfolio position."""

    ticker: str
    sector: str
    shares: int
    current_price: float
    entry_price: float
    direction: str = "LONG"  # "LONG" or "SHORT"


@dataclass
class RiskLimits:
    """Risk limits for a potential new position."""

    ticker: str
    max_position_value: float  # Maximum $ value allowed
    max_shares: int
    volatility_multiplier: float
    correlation_multiplier: float
    sector_multiplier: float
    reasoning: str


@dataclass
class PortfolioRiskProfile:
    """Risk profile of current portfolio."""

    total_value: float
    positions: list[Position]
    sector_exposure: dict[str, float]  # sector -> % of portfolio
    volatility_60d: dict[str, float]  # ticker -> annualized volatility
    correlations: dict[tuple[str, str], float]  # (t1, t2) -> correlation
    timestamp: datetime = field(default_factory=datetime.now)


class CorrelationAdjustedRiskManager:
    """Risk manager with volatility and correlation adjustments.

    Based on ai-hedge-fund's risk management implementation.
    Prevents portfolio over-concentration in correlated assets.
    """

    def __init__(
        self,
        max_position_pct: float = 0.20,  # Max 20% in single position
        max_sector_pct: float = 0.30,  # Max 30% in single sector
        base_volatility_threshold: float = 0.30,  # 30% annualized vol
        correlation_threshold_high: float = 0.80,
        correlation_threshold_medium: float = 0.60,
    ):
        """Initialize risk manager with thresholds."""
        self.max_position_pct = max_position_pct
        self.max_sector_pct = max_sector_pct
        self.base_volatility_threshold = base_volatility_threshold
        self.correlation_threshold_high = correlation_threshold_high
        self.correlation_threshold_medium = correlation_threshold_medium

    def calculate_position_limits(
        self,
        ticker: str,
        sector: str,
        portfolio: PortfolioRiskProfile,
        proposed_price: float,
    ) -> RiskLimits:
        """Calculate position limits for a new trade.

        Args:
            ticker: Ticker symbol
            sector: Sector classification
            portfolio: Current portfolio risk profile
            proposed_price: Proposed entry price

        Returns:
            RiskLimits with maximum position size and multipliers
        """
        # 1. Calculate base position limit (20% of portfolio)
        base_limit = portfolio.total_value * self.max_position_pct

        # 2. Volatility adjustment
        vol_mult = self._calculate_volatility_multiplier(
            portfolio.volatility_60d.get(ticker, self.base_volatility_threshold)
        )

        # 3. Correlation adjustment with existing positions
        corr_mult = self._calculate_correlation_multiplier(
            ticker, portfolio.positions, portfolio.correlations
        )

        # 4. Sector concentration adjustment
        sector_mult = self._calculate_sector_multiplier(
            sector, portfolio.sector_exposure
        )

        # Apply all multipliers
        adjusted_limit = base_limit * vol_mult * corr_mult * sector_mult

        # Calculate max shares
        max_shares = int(adjusted_limit / proposed_price) if proposed_price > 0 else 0

        # Build reasoning
        reasoning_parts = [
            f"Base limit (20%): ${base_limit:,.0f}",
            f"Volatility multiplier: {vol_mult:.2f}",
            f"Correlation multiplier: {corr_mult:.2f}",
            f"Sector multiplier: {sector_mult:.2f}",
            f"Adjusted limit: ${adjusted_limit:,.0f}",
        ]

        return RiskLimits(
            ticker=ticker,
            max_position_value=adjusted_limit,
            max_shares=max_shares,
            volatility_multiplier=vol_mult,
            correlation_multiplier=corr_mult,
            sector_multiplier=sector_mult,
            reasoning="\n".join(reasoning_parts),
        )

    def _calculate_volatility_multiplier(self, annualized_volatility: float) -> float:
        """Calculate position size multiplier based on volatility.

        Higher volatility = smaller position size.

        Args:
            annualized_volatility: 60-day annualized volatility (e.g., 0.30 for 30%)

        Returns:
            Multiplier between 0.5 and 1.25
        """
        if annualized_volatility < 0.15:  # Low vol (< 15%)
            # Allow up to 25% position (multiplier 1.25)
            return 1.25
        elif annualized_volatility < 0.30:  # Medium vol (15-30%)
            # Linear reduction from 1.25 to 1.0
            reduction = (annualized_volatility - 0.15) * 0.5  # 0 to 0.075
            return 1.25 - reduction
        elif annualized_volatility < 0.50:  # High vol (30-50%)
            # Linear reduction from 1.0 to 0.75
            reduction = (annualized_volatility - 0.30) * 0.5  # 0 to 0.10
            return 1.0 - reduction
        else:  # Very high vol (> 50%)
            # Cap at 50% of base limit
            return 0.50

    def _calculate_correlation_multiplier(
        self,
        new_ticker: str,
        existing_positions: list[Position],
        correlations: dict[tuple[str, str], float],
    ) -> float:
        """Calculate position size multiplier based on correlation.

        High correlation with existing positions = smaller new position.

        Args:
            new_ticker: Ticker of proposed position
            existing_positions: Current portfolio positions
            correlations: Correlation matrix

        Returns:
            Multiplier between 0.5 and 1.0
        """
        if not existing_positions:
            return 1.0  # No correlation concerns with empty portfolio

        # Get correlations with all existing positions
        position_correlations = []
        for pos in existing_positions:
            # Try both orderings of the ticker pair
            corr = correlations.get((new_ticker, pos.ticker))
            if corr is None:
                corr = correlations.get((pos.ticker, new_ticker))
            if corr is None:
                # Estimate based on sector similarity
                corr = 0.5 if pos.sector == self._estimate_sector(new_ticker) else 0.2

            # Weight by position size
            position_value = pos.shares * pos.current_price
            weight = position_value  # Will normalize later
            position_correlations.append((corr, weight))

        if not position_correlations:
            return 1.0

        # Calculate weighted average correlation
        total_weight = sum(w for _, w in position_correlations)
        if total_weight == 0:
            return 1.0

        avg_correlation = sum(c * w for c, w in position_correlations) / total_weight

        # Apply correlation multiplier
        if avg_correlation >= self.correlation_threshold_high:  # > 80% correlated
            return 0.70  # Sharp reduction
        elif avg_correlation >= self.correlation_threshold_medium:  # 60-80% correlated
            # Linear from 0.85 to 0.70
            return 0.85 - (avg_correlation - 0.60) * 0.75
        else:  # < 60% correlated
            return 1.0

    def _calculate_sector_multiplier(
        self, sector: str, sector_exposure: dict[str, float]
    ) -> float:
        """Calculate position size multiplier based on sector concentration.

        Prevents over-concentration in single sector.

        Args:
            sector: Sector of proposed position
            sector_exposure: Current sector allocations (% of portfolio)

        Returns:
            Multiplier between 0.5 and 1.0
        """
        current_exposure = sector_exposure.get(sector, 0.0)

        if current_exposure >= self.max_sector_pct:  # Already at limit
            return 0.50  # Strong reduction
        elif current_exposure >= self.max_sector_pct * 0.8:  # Near limit (24%)
            # Linear reduction from 0.85 to 0.50
            excess = current_exposure - (self.max_sector_pct * 0.8)
            return 0.85 - (excess / (self.max_sector_pct * 0.2)) * 0.35
        else:  # Well below limit
            return 1.0

    def calculate_portfolio_risk_profile(
        self, positions: list[Position], price_history: dict[str, list[float]]
    ) -> PortfolioRiskProfile:
        """Calculate risk profile for current portfolio.

        Args:
            positions: Current positions
            price_history: Historical prices for each ticker

        Returns:
            PortfolioRiskProfile with volatilities and correlations
        """
        # Calculate total portfolio value
        total_value = sum(pos.shares * pos.current_price for pos in positions)

        # Calculate sector exposures
        sector_exposure: dict[str, float] = {}
        for pos in positions:
            position_value = pos.shares * pos.current_price
            sector_exposure[pos.sector] = (
                sector_exposure.get(pos.sector, 0.0) + position_value
            )

        # Convert to percentages
        if total_value > 0:
            sector_exposure = {s: v / total_value for s, v in sector_exposure.items()}

        # Calculate 60-day volatilities
        volatilities: dict[str, float] = {}
        for ticker, prices in price_history.items():
            if len(prices) >= 20:
                vol = self._calculate_annualized_volatility(
                    prices[-60:] if len(prices) >= 60 else prices
                )
                volatilities[ticker] = vol
            else:
                volatilities[ticker] = self.base_volatility_threshold

        # Calculate correlations between all position pairs
        correlations: dict[tuple[str, str], float] = {}
        tickers = list(price_history.keys())
        for i, t1 in enumerate(tickers):
            for t2 in tickers[i + 1 :]:
                corr = self._calculate_correlation(
                    price_history[t1][-60:]
                    if len(price_history[t1]) >= 60
                    else price_history[t1],
                    price_history[t2][-60:]
                    if len(price_history[t2]) >= 60
                    else price_history[t2],
                )
                correlations[(t1, t2)] = corr

        return PortfolioRiskProfile(
            total_value=total_value,
            positions=positions,
            sector_exposure=sector_exposure,
            volatility_60d=volatilities,
            correlations=correlations,
        )

    def check_portfolio_health(self, portfolio: PortfolioRiskProfile) -> dict:
        """Check portfolio health and return warnings.

        Args:
            portfolio: Current portfolio risk profile

        Returns:
            Dictionary with health metrics and warnings
        """
        warnings = []

        # Check sector concentration
        for sector, exposure in portfolio.sector_exposure.items():
            if exposure > self.max_sector_pct:
                warnings.append(
                    f"SECTOR_CONCENTRATION: {sector} at {exposure:.1%} (max {self.max_sector_pct:.0%})"
                )

        # Check individual position sizes
        for pos in portfolio.positions:
            position_value = pos.shares * pos.current_price
            position_pct = (
                position_value / portfolio.total_value
                if portfolio.total_value > 0
                else 0
            )
            if position_pct > self.max_position_pct:
                warnings.append(
                    f"POSITION_SIZE: {pos.ticker} at {position_pct:.1%} (max {self.max_position_pct:.0%})"
                )

        # Check high volatility positions
        high_vol_positions = [
            (t, v) for t, v in portfolio.volatility_60d.items() if v > 0.50
        ]
        if high_vol_positions:
            warnings.append(
                f"HIGH_VOLATILITY: {len(high_vol_positions)} positions with >50% vol"
            )

        return {
            "total_value": portfolio.total_value,
            "num_positions": len(portfolio.positions),
            "sector_count": len(portfolio.sector_exposure),
            "avg_volatility": sum(portfolio.volatility_60d.values())
            / len(portfolio.volatility_60d)
            if portfolio.volatility_60d
            else 0,
            "warnings": warnings,
            "is_healthy": len(warnings) == 0,
        }

    def _calculate_annualized_volatility(self, prices: list[float]) -> float:
        """Calculate annualized volatility from price series."""
        if len(prices) < 2:
            return self.base_volatility_threshold

        # Calculate daily returns
        returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices))
            if prices[i - 1] > 0
        ]

        if len(returns) < 2:
            return self.base_volatility_threshold

        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)

        # Annualize (assuming daily data, multiply by sqrt(252))
        annualized_vol = daily_vol * math.sqrt(252)

        return annualized_vol

    def _calculate_correlation(
        self, prices1: list[float], prices2: list[float]
    ) -> float:
        """Calculate correlation between two price series."""
        if len(prices1) != len(prices2) or len(prices1) < 5:
            return 0.0

        # Calculate returns
        returns1 = [
            (prices1[i] - prices1[i - 1]) / prices1[i - 1]
            for i in range(1, len(prices1))
            if prices1[i - 1] > 0
        ]
        returns2 = [
            (prices2[i] - prices2[i - 1]) / prices2[i - 1]
            for i in range(1, len(prices2))
            if prices2[i - 1] > 0
        ]

        if len(returns1) != len(returns2) or len(returns1) < 3:
            return 0.0

        # Calculate correlation
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)

        numerator = sum(
            (r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2)
        )

        var1 = sum((r - mean1) ** 2 for r in returns1)
        var2 = sum((r - mean2) ** 2 for r in returns2)

        denominator = math.sqrt(var1 * var2)

        if denominator == 0:
            return 0.0

        correlation = numerator / denominator
        return max(-1.0, min(1.0, correlation))

    def _estimate_sector(self, ticker: str) -> str:
        """Estimate sector for a ticker (simplified)."""
        # This would ideally use a mapping or API
        # For now, return UNKNOWN
        return "UNKNOWN"


# Singleton instance
correlation_risk_manager = CorrelationAdjustedRiskManager()

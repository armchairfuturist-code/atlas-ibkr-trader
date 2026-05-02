"""Multi-DCF valuation layer.

Inspired by ai-hedge-fund's valuation analyst agent.
Calculates intrinsic value using multiple methodologies:
1. Discounted Cash Flow (DCF)
2. Owner Earnings (Buffett method)
3. EV/EBITDA Multiple
4. Residual Income Model
5. Dividend Discount Model (for income stocks)

Provides valuation-based signals for long-term investments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ValuationMethod(Enum):
    """Valuation methodologies."""

    DCF = "dcf"
    OWNER_EARNINGS = "owner_earnings"
    EV_EBITDA = "ev_ebitda"
    RESIDUAL_INCOME = "residual_income"
    DIVIDEND_DISCOUNT = "dividend_discount"


class ValuationSignal(Enum):
    """Signal from valuation analysis."""

    STRONG_VALUE = "STRONG_VALUE"  # > 30% undervalued
    VALUE = "VALUE"  # 15-30% undervalued
    FAIR = "FAIR"  # -15% to +15%
    OVERVALUED = "OVERVALUED"  # 15-30% overvalued
    STRONG_SELL = "STRONG_SELL"  # > 30% overvalued


@dataclass
class ValuationResult:
    """Result from a specific valuation method."""

    method: ValuationMethod
    intrinsic_value: float
    current_price: float
    upside_downside: float  # Percentage
    signal: ValuationSignal
    assumptions: dict
    confidence: float  # 0-1


@dataclass
class CompositeValuation:
    """Composite valuation from multiple methods."""

    ticker: str
    current_price: float
    intrinsic_value_range: tuple[float, float]  # (low, high)
    composite_signal: ValuationSignal
    composite_upside: float
    method_results: list[ValuationResult]
    reasoning: str


class MultiDCFValuationAnalyzer:
    """Multi-methodology valuation analyzer.

    Based on ai-hedge-fund's valuation analyst agent.
    Combines multiple valuation approaches for robust intrinsic value estimate.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.04,  # 4% risk-free rate
        market_risk_premium: float = 0.05,  # 5% equity risk premium
        tax_rate: float = 0.21,  # 21% corporate tax
    ):
        """Initialize with valuation parameters."""
        self.risk_free_rate = risk_free_rate
        self.market_risk_premium = market_risk_premium
        self.tax_rate = tax_rate

    def analyze(
        self,
        ticker: str,
        current_price: float,
        fundamentals: dict,
    ) -> CompositeValuation:
        """Run multi-methodology valuation analysis.

        Args:
            ticker: Ticker symbol
            current_price: Current market price
            fundamentals: Dict with financial metrics
                Required keys: revenue, net_income, ebitda, fcf, shares_outstanding,
                              total_debt, cash, beta, growth_rate

        Returns:
            CompositeValuation with range of intrinsic values
        """
        results = []

        # 1. DCF Valuation
        dcf_result = self._calculate_dcf(ticker, current_price, fundamentals)
        if dcf_result:
            results.append(dcf_result)

        # 2. Owner Earnings (Buffett Method)
        oe_result = self._calculate_owner_earnings(ticker, current_price, fundamentals)
        if oe_result:
            results.append(oe_result)

        # 3. EV/EBITDA Multiple
        evebitda_result = self._calculate_ev_ebitda(ticker, current_price, fundamentals)
        if evebitda_result:
            results.append(evebitda_result)

        # 4. Residual Income Model
        ri_result = self._calculate_residual_income(ticker, current_price, fundamentals)
        if ri_result:
            results.append(ri_result)

        # 5. Dividend Discount Model (if applicable)
        ddm_result = self._calculate_ddm(ticker, current_price, fundamentals)
        if ddm_result:
            results.append(ddm_result)

        if not results:
            return self._fallback_valuation(ticker, current_price)

        # Calculate composite
        intrinsic_values = [r.intrinsic_value for r in results]
        low_value = min(intrinsic_values)
        high_value = max(intrinsic_values)
        avg_value = sum(intrinsic_values) / len(intrinsic_values)

        composite_upside = (avg_value - current_price) / current_price
        composite_signal = self._upside_to_signal(composite_upside)

        reasoning = self._build_reasoning(ticker, results, composite_upside)

        return CompositeValuation(
            ticker=ticker,
            current_price=current_price,
            intrinsic_value_range=(low_value, high_value),
            composite_signal=composite_signal,
            composite_upside=composite_upside,
            method_results=results,
            reasoning=reasoning,
        )

    def _calculate_dcf(
        self, ticker: str, current_price: float, fundamentals: dict
    ) -> Optional[ValuationResult]:
        """Calculate intrinsic value using Discounted Cash Flow."""
        try:
            fcf = fundamentals.get("fcf", 0)
            growth_rate = fundamentals.get("growth_rate", 0.05)
            beta = fundamentals.get("beta", 1.0)
            shares = fundamentals.get("shares_outstanding", 1)

            if fcf <= 0 or shares <= 0:
                return None

            # Calculate discount rate (WACC approximation)
            cost_of_equity = self.risk_free_rate + (beta * self.market_risk_premium)

            # Project FCF for 10 years
            projected_fcfs = []
            current_fcf = fcf

            for year in range(1, 11):
                # Gradually reduce growth rate to terminal rate
                if year <= 5:
                    g = growth_rate
                else:
                    g = max(0.02, growth_rate * (0.8 ** (year - 5)))

                current_fcf = current_fcf * (1 + g)
                projected_fcfs.append(current_fcf)

            # Discount projected FCFs
            terminal_growth = 0.025  # 2.5% terminal growth
            terminal_value = (
                projected_fcfs[-1]
                * (1 + terminal_growth)
                / (cost_of_equity - terminal_growth)
            )

            pv_fcfs = sum(
                fcf / ((1 + cost_of_equity) ** (i + 1))
                for i, fcf in enumerate(projected_fcfs)
            )
            pv_terminal = terminal_value / ((1 + cost_of_equity) ** 10)

            enterprise_value = pv_fcfs + pv_terminal

            # Adjust for net debt
            net_debt = fundamentals.get("total_debt", 0) - fundamentals.get("cash", 0)
            equity_value = enterprise_value - net_debt

            intrinsic_value = equity_value / shares
            upside = (intrinsic_value - current_price) / current_price
            signal = self._upside_to_signal(upside)

            return ValuationResult(
                method=ValuationMethod.DCF,
                intrinsic_value=round(intrinsic_value, 2),
                current_price=current_price,
                upside_downside=round(upside * 100, 1),
                signal=signal,
                assumptions={
                    "growth_rate": growth_rate,
                    "cost_of_equity": round(cost_of_equity, 3),
                    "terminal_growth": terminal_growth,
                    "projection_years": 10,
                },
                confidence=0.7 if growth_rate > 0.03 else 0.5,
            )
        except Exception as e:
            logger.warning(f"DCF calculation failed for {ticker}: {e}")
            return None

    def _calculate_owner_earnings(
        self, ticker: str, current_price: float, fundamentals: dict
    ) -> Optional[ValuationResult]:
        """Calculate intrinsic value using Buffett's Owner Earnings method."""
        try:
            net_income = fundamentals.get("net_income", 0)
            depreciation = fundamentals.get("depreciation", 0)
            capex = fundamentals.get("capex", 0)
            growth_rate = fundamentals.get("growth_rate", 0.05)
            shares = fundamentals.get("shares_outstanding", 1)
            beta = fundamentals.get("beta", 1.0)

            if net_income <= 0 or shares <= 0:
                return None

            # Owner Earnings = Net Income + Depreciation - Maintenance CapEx
            # Simplified: Use 70% of CapEx as maintenance
            maintenance_capex = capex * 0.7 if capex > 0 else 0
            owner_earnings = net_income + depreciation - maintenance_capex

            # Apply growth
            future_oe = owner_earnings * ((1 + growth_rate) ** 10)

            # Discount rate
            discount_rate = self.risk_free_rate + (beta * self.market_risk_premium)

            # Perpetuity value
            terminal_growth = 0.025
            value = future_oe / (discount_rate - terminal_growth)

            intrinsic_value = value / shares
            upside = (intrinsic_value - current_price) / current_price
            signal = self._upside_to_signal(upside)

            return ValuationResult(
                method=ValuationMethod.OWNER_EARNINGS,
                intrinsic_value=round(intrinsic_value, 2),
                current_price=current_price,
                upside_downside=round(upside * 100, 1),
                signal=signal,
                assumptions={
                    "owner_earnings": round(owner_earnings, 0),
                    "growth_rate": growth_rate,
                    "discount_rate": round(discount_rate, 3),
                    "maintenance_capex_pct": 0.7,
                },
                confidence=0.65,
            )
        except Exception as e:
            logger.warning(f"Owner earnings calculation failed for {ticker}: {e}")
            return None

    def _calculate_ev_ebitda(
        self, ticker: str, current_price: float, fundamentals: dict
    ) -> Optional[ValuationResult]:
        """Calculate intrinsic value using EV/EBITDA multiple."""
        try:
            ebitda = fundamentals.get("ebitda", 0)
            total_debt = fundamentals.get("total_debt", 0)
            cash = fundamentals.get("cash", 0)
            shares = fundamentals.get("shares_outstanding", 1)
            growth_rate = fundamentals.get("growth_rate", 0.05)

            if ebitda <= 0 or shares <= 0:
                return None

            # Determine appropriate multiple based on growth
            if growth_rate > 0.15:  # High growth
                ev_ebitda_multiple = 12.0
            elif growth_rate > 0.08:  # Medium growth
                ev_ebitda_multiple = 9.0
            else:  # Low growth
                ev_ebitda_multiple = 6.0

            enterprise_value = ebitda * ev_ebitda_multiple
            equity_value = enterprise_value - total_debt + cash
            intrinsic_value = equity_value / shares

            upside = (intrinsic_value - current_price) / current_price
            signal = self._upside_to_signal(upside)

            return ValuationResult(
                method=ValuationMethod.EV_EBITDA,
                intrinsic_value=round(intrinsic_value, 2),
                current_price=current_price,
                upside_downside=round(upside * 100, 1),
                signal=signal,
                assumptions={
                    "ebitda": ebitda,
                    "ev_ebitda_multiple": ev_ebitda_multiple,
                    "growth_tier": "high"
                    if growth_rate > 0.15
                    else "medium"
                    if growth_rate > 0.08
                    else "low",
                },
                confidence=0.6,
            )
        except Exception as e:
            logger.warning(f"EV/EBITDA calculation failed for {ticker}: {e}")
            return None

    def _calculate_residual_income(
        self, ticker: str, current_price: float, fundamentals: dict
    ) -> Optional[ValuationResult]:
        """Calculate intrinsic value using Residual Income Model."""
        try:
            book_value = fundamentals.get("book_value", 0)
            net_income = fundamentals.get("net_income", 0)
            shares = fundamentals.get("shares_outstanding", 1)
            beta = fundamentals.get("beta", 1.0)
            growth_rate = fundamentals.get("growth_rate", 0.05)

            if book_value <= 0 or shares <= 0 or net_income <= 0:
                return None

            book_value_per_share = book_value / shares
            roe = net_income / book_value

            cost_of_equity = self.risk_free_rate + (beta * self.market_risk_premium)

            # Residual income = Net Income - (Book Value * Cost of Equity)
            residual_income = net_income - (book_value * cost_of_equity)

            # Project for 5 years
            pv_ri = 0
            for year in range(1, 6):
                ri = residual_income * ((1 + growth_rate) ** year)
                pv_ri += ri / ((1 + cost_of_equity) ** year)

            # Terminal value
            terminal_ri = (
                residual_income
                * ((1 + growth_rate) ** 5)
                * 1.025
                / (cost_of_equity - 0.025)
            )
            pv_terminal = terminal_ri / ((1 + cost_of_equity) ** 5)

            intrinsic_value = book_value_per_share + (pv_ri + pv_terminal) / shares
            upside = (intrinsic_value - current_price) / current_price
            signal = self._upside_to_signal(upside)

            return ValuationResult(
                method=ValuationMethod.RESIDUAL_INCOME,
                intrinsic_value=round(intrinsic_value, 2),
                current_price=current_price,
                upside_downside=round(upside * 100, 1),
                signal=signal,
                assumptions={
                    "book_value_per_share": round(book_value_per_share, 2),
                    "roe": round(roe, 3),
                    "cost_of_equity": round(cost_of_equity, 3),
                    "residual_income": round(residual_income, 0),
                },
                confidence=0.65 if roe > cost_of_equity else 0.5,
            )
        except Exception as e:
            logger.warning(f"Residual income calculation failed for {ticker}: {e}")
            return None

    def _calculate_ddm(
        self, ticker: str, current_price: float, fundamentals: dict
    ) -> Optional[ValuationResult]:
        """Calculate intrinsic value using Dividend Discount Model."""
        try:
            dividend_per_share = fundamentals.get("dividend_per_share", 0)
            growth_rate = fundamentals.get("growth_rate", 0.03)
            beta = fundamentals.get("beta", 1.0)

            if dividend_per_share <= 0:
                return None

            cost_of_equity = self.risk_free_rate + (beta * self.market_risk_premium)

            # Gordon Growth Model
            if cost_of_equity <= growth_rate:
                return None

            intrinsic_value = (
                dividend_per_share * (1 + growth_rate) / (cost_of_equity - growth_rate)
            )
            upside = (intrinsic_value - current_price) / current_price
            signal = self._upside_to_signal(upside)

            return ValuationResult(
                method=ValuationMethod.DIVIDEND_DISCOUNT,
                intrinsic_value=round(intrinsic_value, 2),
                current_price=current_price,
                upside_downside=round(upside * 100, 1),
                signal=signal,
                assumptions={
                    "dividend_per_share": dividend_per_share,
                    "growth_rate": growth_rate,
                    "cost_of_equity": round(cost_of_equity, 3),
                },
                confidence=0.6,
            )
        except Exception as e:
            logger.warning(f"DDM calculation failed for {ticker}: {e}")
            return None

    def _upside_to_signal(self, upside: float) -> ValuationSignal:
        """Convert upside percentage to signal."""
        if upside > 0.30:
            return ValuationSignal.STRONG_VALUE
        elif upside > 0.15:
            return ValuationSignal.VALUE
        elif upside < -0.30:
            return ValuationSignal.STRONG_SELL
        elif upside < -0.15:
            return ValuationSignal.OVERVALUED
        else:
            return ValuationSignal.FAIR

    def _build_reasoning(
        self, ticker: str, results: list[ValuationResult], composite_upside: float
    ) -> str:
        """Build human-readable reasoning."""
        lines = [
            f"Valuation Analysis for {ticker}",
            f"Composite Upside/Downside: {composite_upside:+.1%}",
            "",
            "Methodology Results:",
        ]

        for r in results:
            lines.append(f"\n{r.method.value}:")
            lines.append(f"  Intrinsic Value: ${r.intrinsic_value:.2f}")
            lines.append(f"  Upside/Downside: {r.upside_downside:+.1f}%")
            lines.append(f"  Signal: {r.signal.value}")
            lines.append(f"  Confidence: {r.confidence:.0%}")

        return "\n".join(lines)

    def _fallback_valuation(
        self, ticker: str, current_price: float
    ) -> CompositeValuation:
        """Return fallback valuation when calculations fail."""
        return CompositeValuation(
            ticker=ticker,
            current_price=current_price,
            intrinsic_value_range=(current_price * 0.9, current_price * 1.1),
            composite_signal=ValuationSignal.FAIR,
            composite_upside=0.0,
            method_results=[],
            reasoning="Insufficient data for valuation analysis",
        )


# Singleton instance
valuation_analyzer = MultiDCFValuationAnalyzer()

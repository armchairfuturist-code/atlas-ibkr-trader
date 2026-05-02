"""Portfolio manager with LLM coordination.

Coordinates all analysis layers:
- SophisticatedTechnicalAnalyzer (5-strategy ensemble)
- GeopoliticalSentimentAgent (Polymarket integration)
- MultiDCFValuationAnalyzer (valuation models)
- CorrelationAdjustedRiskManager (position sizing)
- MacroThematicLayer (event → sector mapping)

Produces actionable portfolio recommendations with position sizing.
Integrates with existing IBKR paper trading adapter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum

from app.agents.sophisticated_technical import (
    SophisticatedTechnicalAnalyzer,
    EnsembleResult,
)
from app.agents.qlib_model_adapter import QlibModelAdapter
from app.agents.geopolitical_agent import GeopoliticalSentimentAgent
from app.valuation.multi_dcf import MultiDCFValuationAnalyzer, CompositeValuation
from app.risk.correlation_risk_manager import (
    CorrelationAdjustedRiskManager,
    PortfolioRiskProfile,
)
from app.layers.macro_thematic import MacroThematicLayer
from app.schemas import SignalDirection


logger = logging.getLogger(__name__)


class PortfolioAction(Enum):
    """Portfolio action types."""

    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
    HOLD = "HOLD"


@dataclass
class PositionRecommendation:
    """Recommendation for a single position."""

    ticker: str
    action: PortfolioAction
    shares: int
    confidence: float  # 0-100
    conviction_score: float  # Composite score

    # Analysis components
    technical_score: float
    geopolitical_score: float
    valuation_score: float
    macro_score: float
    risk_adjusted_size: int

    # Metadata
    reasoning: str
    entry_price: float
    stop_loss: Optional[float]
    target_price: Optional[float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PortfolioRecommendation:
    """Complete portfolio recommendation."""

    positions: list[PositionRecommendation]
    total_positions: int
    avg_confidence: float
    macro_theme: str
    risk_warnings: list[str]
    portfolio_thesis: str
    timestamp: datetime = field(default_factory=datetime.now)


class LLMCoordinatedPortfolioManager:
    """Portfolio manager coordinating all analysis layers.

    Inspired by ai-hedge-fund's portfolio management approach.
    Integrates multiple signal sources for robust recommendations.
    """

    def __init__(
        self,
        technical_analyzer: Optional[SophisticatedTechnicalAnalyzer] = None,
        geopolitical_agent: Optional[GeopoliticalSentimentAgent] = None,
        valuation_analyzer: Optional[MultiDCFValuationAnalyzer] = None,
        risk_manager: Optional[CorrelationAdjustedRiskManager] = None,
        macro_layer: Optional[MacroThematicLayer] = None,
        use_qlib: bool = True,
    ):
        """Initialize with analysis components.

        Args:
            technical_analyzer: Override for technical analyzer (default: QlibModelAdapter or fallback)
            use_qlib: Whether to attempt Qlib integration (default: True)
        """
        if use_qlib:
            self.technical = technical_analyzer or QlibModelAdapter()
        else:
            self.technical = technical_analyzer or SophisticatedTechnicalAnalyzer()
        self.geopolitical = geopolitical_agent or GeopoliticalSentimentAgent()
        self.valuation = valuation_analyzer or MultiDCFValuationAnalyzer()
        self.risk = risk_manager or CorrelationAdjustedRiskManager()
        self.macro = macro_layer or MacroThematicLayer()

    def analyze_tickers(
        self,
        tickers: list[str],
        price_data: dict[str, dict],
        fundamentals: dict[str, dict],
        current_portfolio: PortfolioRiskProfile,
        theme: Optional[str] = None,
    ) -> PortfolioRecommendation:
        """Analyze multiple tickers and generate portfolio recommendations.

        Args:
            tickers: List of tickers to analyze
            price_data: Dict of ticker -> price/volume data
            fundamentals: Dict of ticker -> fundamental data
            current_portfolio: Current portfolio state
            theme: Optional macro theme to focus on

        Returns:
            PortfolioRecommendation with position sizes
        """
        logger.info(
            f"Analyzing {len(tickers)} tickers with theme: {theme or 'general'}"
        )

        # Get macro thematic context
        macro_report = self.macro.analyze(theme)

        # Get geopolitical sentiment
        geo_signal = self.geopolitical.analyze() if theme else None

        # Analyze each ticker
        recommendations = []

        for ticker in tickers:
            try:
                rec = self._analyze_single_ticker(
                    ticker=ticker,
                    price_data=price_data.get(ticker, {}),
                    fundamentals=fundamentals.get(ticker, {}),
                    current_portfolio=current_portfolio,
                    macro_report=macro_report,
                    geo_signal=geo_signal,
                )

                if (
                    rec and rec.confidence > 50
                ):  # Only include high-confidence recommendations
                    recommendations.append(rec)

            except Exception as e:
                logger.warning(f"Analysis failed for {ticker}: {e}")
                continue

        # Sort by conviction score
        recommendations.sort(key=lambda x: x.conviction_score, reverse=True)

        # Build portfolio thesis
        thesis = self._build_portfolio_thesis(recommendations, macro_report)

        # Get risk warnings
        risk_check = self.risk.check_portfolio_health(current_portfolio)

        return PortfolioRecommendation(
            positions=recommendations[:5],  # Top 5 recommendations
            total_positions=len(recommendations),
            avg_confidence=sum(r.confidence for r in recommendations)
            / len(recommendations)
            if recommendations
            else 0,
            macro_theme=macro_report.theme if macro_report else "none",
            risk_warnings=risk_check.get("warnings", []),
            portfolio_thesis=thesis,
        )

    def _analyze_single_ticker(
        self,
        ticker: str,
        price_data: dict,
        fundamentals: dict,
        current_portfolio: PortfolioRiskProfile,
        macro_report,
        geo_signal,
    ) -> Optional[PositionRecommendation]:
        """Analyze a single ticker across all dimensions."""

        # 1. Technical Analysis (5-strategy ensemble)
        prices = price_data.get("prices", [])
        volumes = price_data.get("volumes", [])
        highs = price_data.get("highs")
        lows = price_data.get("lows")
        current_price = prices[-1] if prices else 0

        if len(prices) < 30:
            logger.debug(f"Insufficient price data for {ticker}")
            return None

        tech_result = self.technical.analyze(prices, volumes, highs, lows)
        technical_score = self._technical_to_score(
            tech_result.composite_signal, tech_result.composite_confidence
        )

        # 2. Geopolitical Analysis
        geo_score = 0.0
        if geo_signal and geo_signal.sector_weights:
            # Check if ticker sector matches bullish geopolitical signals
            sector = fundamentals.get("sector", "UNKNOWN")
            sector_weight = geo_signal.sector_weights.get(sector, 0)
            geo_score = sector_weight * geo_signal.confidence * 100

        # 3. Valuation Analysis
        valuation_score = 0.0
        if fundamentals:
            val_result = self.valuation.analyze(ticker, current_price, fundamentals)
            valuation_score = self._valuation_to_score(
                val_result.composite_signal, val_result.composite_upside
            )

        # 4. Macro Thematic Score
        macro_score = 0.0
        if macro_report and macro_report.sector_recommendations:
            sector = fundamentals.get("sector", "UNKNOWN")
            for rec in macro_report.sector_recommendations:
                if rec.sector == sector:
                    macro_score = (
                        rec.conviction
                        if rec.direction.value in ["LONG", "BUY"]
                        else -rec.conviction
                    )
                    break

        # 5. Composite Conviction Score
        # Weight: Technical 30%, Geopolitical 20%, Valuation 25%, Macro 25%
        conviction_score = (
            technical_score * 0.30
            + geo_score * 0.20
            + valuation_score * 0.25
            + macro_score * 0.25
        )

        # 6. Determine Action
        action, confidence = self._conviction_to_action(conviction_score)

        if action == PortfolioAction.HOLD or confidence < 50:
            return None

        # 7. Risk-Adjusted Position Sizing
        sector = fundamentals.get("sector", "UNKNOWN")
        risk_limits = self.risk.calculate_position_limits(
            ticker=ticker,
            sector=sector,
            portfolio=current_portfolio,
            proposed_price=current_price,
        )

        # Adjust shares based on confidence
        base_shares = risk_limits.max_shares
        confidence_adjusted_shares = int(base_shares * (confidence / 100))
        final_shares = max(1, confidence_adjusted_shares)

        # 8. Build Reasoning
        reasoning = self._build_position_reasoning(
            ticker=ticker,
            action=action,
            tech_result=tech_result,
            valuation_result=val_result if fundamentals else None,
            conviction_score=conviction_score,
            risk_limits=risk_limits,
        )

        # Calculate stop loss and target
        stop_loss = (
            current_price * 0.92
            if action in [PortfolioAction.BUY, PortfolioAction.COVER]
            else current_price * 1.08
        )
        target_price = (
            current_price * 1.15
            if action in [PortfolioAction.BUY, PortfolioAction.COVER]
            else current_price * 0.85
        )

        return PositionRecommendation(
            ticker=ticker,
            action=action,
            shares=final_shares,
            confidence=confidence,
            conviction_score=conviction_score,
            technical_score=technical_score,
            geopolitical_score=geo_score,
            valuation_score=valuation_score,
            macro_score=macro_score,
            risk_adjusted_size=final_shares,
            reasoning=reasoning,
            entry_price=current_price,
            stop_loss=round(stop_loss, 2),
            target_price=round(target_price, 2),
        )

    def _technical_to_score(self, signal, confidence: float) -> float:
        """Convert technical signal to score (-100 to +100)."""
        from app.agents.technical_agent import TechnicalSignal

        signal_map = {
            TechnicalSignal.STRONG_BUY: 90,
            TechnicalSignal.BUY: 60,
            TechnicalSignal.HOLD: 0,
            TechnicalSignal.SELL: -60,
            TechnicalSignal.STRONG_SELL: -90,
            TechnicalSignal.SHORT: -75,
        }

        base_score = signal_map.get(signal, 0)
        return base_score * confidence

    def _valuation_to_score(self, signal, upside: float) -> float:
        """Convert valuation signal to score (-100 to +100)."""
        from app.valuation.multi_dcf import ValuationSignal

        signal_map = {
            ValuationSignal.STRONG_VALUE: 80,
            ValuationSignal.VALUE: 50,
            ValuationSignal.FAIR: 0,
            ValuationSignal.OVERVALUED: -50,
            ValuationSignal.STRONG_SELL: -80,
        }

        base_score = signal_map.get(signal, 0)
        # Adjust by actual upside
        return base_score + (upside * 100)

    def _conviction_to_action(
        self, conviction_score: float
    ) -> tuple[PortfolioAction, float]:
        """Convert conviction score to action and confidence."""
        if conviction_score > 60:
            return PortfolioAction.BUY, min(95, 60 + (conviction_score - 60) * 0.8)
        elif conviction_score > 30:
            return PortfolioAction.BUY, min(75, 50 + (conviction_score - 30))
        elif conviction_score < -60:
            return PortfolioAction.SHORT, min(95, 60 + abs(conviction_score + 60) * 0.8)
        elif conviction_score < -30:
            return PortfolioAction.SELL, min(75, 50 + abs(conviction_score + 30))
        else:
            return PortfolioAction.HOLD, 40

    def _build_position_reasoning(
        self,
        ticker: str,
        action: PortfolioAction,
        tech_result: EnsembleResult,
        valuation_result: Optional[CompositeValuation],
        conviction_score: float,
        risk_limits,
    ) -> str:
        """Build human-readable reasoning for position."""
        lines = [
            f"{action.value} Recommendation: {ticker}",
            f"Conviction Score: {conviction_score:.1f}",
            "",
            "Technical Analysis:",
            f"  Composite Signal: {tech_result.composite_signal.value}",
            f"  Confidence: {tech_result.composite_confidence:.0%}",
        ]

        for sig in tech_result.strategy_signals[:3]:
            lines.append(
                f"  {sig.strategy.value}: {sig.signal.value} ({sig.confidence:.0%})"
            )

        if valuation_result:
            lines.extend(
                [
                    "",
                    "Valuation Analysis:",
                    f"  Signal: {valuation_result.composite_signal.value}",
                    f"  Upside: {valuation_result.composite_upside:+.1%}",
                    f"  Range: ${valuation_result.intrinsic_value_range[0]:.2f} - ${valuation_result.intrinsic_value_range[1]:.2f}",
                ]
            )

        lines.extend(
            [
                "",
                "Risk Management:",
                f"  Max Position: ${risk_limits.max_position_value:,.0f}",
                f"  Correlation Adjustment: {risk_limits.correlation_multiplier:.2f}x",
                f"  Volatility Adjustment: {risk_limits.volatility_multiplier:.2f}x",
            ]
        )

        return "\n".join(lines)

    def _build_portfolio_thesis(
        self,
        recommendations: list[PositionRecommendation],
        macro_report,
    ) -> str:
        """Build portfolio-level thesis."""
        if not recommendations:
            return "No high-conviction recommendations generated."

        lines = [
            f"Portfolio Thesis ({len(recommendations)} positions)",
            f"Macro Theme: {macro_report.theme if macro_report else 'General'}",
            "",
            "Top Recommendations:",
        ]

        for i, rec in enumerate(recommendations[:3], 1):
            lines.append(
                f"{i}. {rec.ticker}: {rec.action.value} {rec.shares} shares (confidence: {rec.confidence:.0f}%)"
            )

        if macro_report and macro_report.thesis:
            lines.extend(["", "Macro Context:", macro_report.thesis[:200]])

        return "\n".join(lines)


# Singleton instance
portfolio_manager = LLMCoordinatedPortfolioManager()

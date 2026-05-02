"""Sophisticated technical analysis with 5-strategy ensemble.

Inspired by ai-hedge-fund's technical analysis agent.
Combines multiple technical strategies with weighted ensemble scoring.

Strategies:
1. Trend Following - EMA cross, ADX, trend strength
2. Mean Reversion - Bollinger Bands, RSI, z-score
3. Momentum - Price momentum, volume confirmation
4. Volatility Regime - Volatility state, ATR, regime detection
5. Statistical Arbitrage - Hurst exponent, skewness, autocorrelation
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from app.agents.technical_agent import TechnicalSignal, TechnicalIndicators


logger = logging.getLogger(__name__)


class TechnicalStrategy(Enum):
    """Technical analysis strategies."""

    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    STAT_ARB = "stat_arb"


@dataclass
class StrategySignal:
    """Signal from a specific technical strategy."""

    strategy: TechnicalStrategy
    signal: TechnicalSignal
    confidence: float  # 0-1
    metrics: dict


@dataclass
class EnsembleResult:
    """Result from ensemble of technical strategies."""

    composite_signal: TechnicalSignal
    composite_confidence: float
    strategy_signals: list[StrategySignal]
    weights: dict[TechnicalStrategy, float]
    reasoning: str


class SophisticatedTechnicalAnalyzer:
    """Advanced technical analysis with 5-strategy ensemble.

    Based on ai-hedge-fund's technical analysis implementation.
    Each strategy is weighted and combined for composite signal.
    """

    # Strategy weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        TechnicalStrategy.TREND: 0.25,
        TechnicalStrategy.MEAN_REVERSION: 0.20,
        TechnicalStrategy.MOMENTUM: 0.25,
        TechnicalStrategy.VOLATILITY: 0.15,
        TechnicalStrategy.STAT_ARB: 0.15,
    }

    def __init__(self, weights: Optional[dict[TechnicalStrategy, float]] = None):
        """Initialize with strategy weights."""
        self.weights = weights or self.DEFAULT_WEIGHTS
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def analyze(
        self,
        prices: list[float],
        volumes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> EnsembleResult:
        """Run ensemble analysis on price data.

        Args:
            prices: List of closing prices
            volumes: List of volume data
            highs: Optional list of high prices
            lows: Optional list of low prices

        Returns:
            EnsembleResult with composite signal and strategy breakdown
        """
        if len(prices) < 50:
            logger.warning(
                "Insufficient data for sophisticated analysis (< 50 periods)"
            )
            return self._fallback_result()

        strategy_signals = []

        # 1. Trend Following Strategy
        trend_signal = self._analyze_trend(prices)
        strategy_signals.append(trend_signal)

        # 2. Mean Reversion Strategy
        mr_signal = self._analyze_mean_reversion(prices)
        strategy_signals.append(mr_signal)

        # 3. Momentum Strategy
        mom_signal = self._analyze_momentum(prices, volumes)
        strategy_signals.append(mom_signal)

        # 4. Volatility Regime Strategy
        vol_signal = self._analyze_volatility(prices, highs, lows)
        strategy_signals.append(vol_signal)

        # 5. Statistical Arbitrage Strategy
        stat_signal = self._analyze_stat_arb(prices)
        strategy_signals.append(stat_signal)

        # Combine signals using weighted ensemble
        composite_signal, composite_confidence = self._combine_signals(strategy_signals)

        # Build reasoning
        reasoning = self._build_reasoning(strategy_signals, composite_signal)

        return EnsembleResult(
            composite_signal=composite_signal,
            composite_confidence=composite_confidence,
            strategy_signals=strategy_signals,
            weights=self.weights,
            reasoning=reasoning,
        )

    def _analyze_trend(self, prices: list[float]) -> StrategySignal:
        """Trend following strategy using EMA cross and ADX."""
        if len(prices) < 30:
            return StrategySignal(
                strategy=TechnicalStrategy.TREND,
                signal=TechnicalSignal.HOLD,
                confidence=0.3,
                metrics={"error": "insufficient_data"},
            )

        # Calculate EMAs
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)

        # EMA cross
        ema_bullish = ema_12 > ema_26
        ema_bearish = ema_12 < ema_26

        # Simple trend strength (simplified ADX proxy)
        price_change_20 = (
            (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0
        )
        trend_strength = abs(price_change_20)

        metrics = {
            "ema_12": round(ema_12, 2),
            "ema_26": round(ema_26, 2),
            "ema_cross": "bullish" if ema_bullish else "bearish",
            "trend_strength": round(trend_strength, 4),
        }

        # Determine signal
        if ema_bullish and trend_strength > 0.05:
            signal = TechnicalSignal.BUY
            confidence = min(0.9, 0.5 + trend_strength * 5)
        elif ema_bearish and trend_strength > 0.05:
            signal = TechnicalSignal.SELL
            confidence = min(0.9, 0.5 + trend_strength * 5)
        else:
            signal = TechnicalSignal.HOLD
            confidence = 0.4

        return StrategySignal(
            strategy=TechnicalStrategy.TREND,
            signal=signal,
            confidence=confidence,
            metrics=metrics,
        )

    def _analyze_mean_reversion(self, prices: list[float]) -> StrategySignal:
        """Mean reversion strategy using Bollinger Bands and RSI."""
        if len(prices) < 20:
            return StrategySignal(
                strategy=TechnicalStrategy.MEAN_REVERSION,
                signal=TechnicalSignal.HOLD,
                confidence=0.3,
                metrics={"error": "insufficient_data"},
            )

        # Bollinger Bands (20-period)
        sma_20 = sum(prices[-20:]) / 20
        std_20 = (sum((p - sma_20) ** 2 for p in prices[-20:]) / 20) ** 0.5
        upper_band = sma_20 + (2 * std_20)
        lower_band = sma_20 - (2 * std_20)

        current_price = prices[-1]
        bb_position = (
            (current_price - lower_band) / (upper_band - lower_band)
            if upper_band != lower_band
            else 0.5
        )

        # RSI (14-period)
        rsi = self._calculate_rsi(prices, 14)

        # Z-score
        z_score = (current_price - sma_20) / std_20 if std_20 > 0 else 0

        metrics = {
            "bb_position": round(bb_position, 2),
            "bb_upper": round(upper_band, 2),
            "bb_lower": round(lower_band, 2),
            "rsi": round(rsi, 1),
            "z_score": round(z_score, 2),
        }

        # Mean reversion signals (counter-trend)
        oversold = rsi < 30 or bb_position < 0.1 or z_score < -2
        overbought = rsi > 70 or bb_position > 0.9 or z_score > 2

        if oversold:
            signal = TechnicalSignal.BUY
            confidence = min(0.85, 0.6 + (30 - rsi) / 100)
        elif overbought:
            signal = TechnicalSignal.SELL
            confidence = min(0.85, 0.6 + (rsi - 70) / 100)
        else:
            signal = TechnicalSignal.HOLD
            confidence = 0.4

        return StrategySignal(
            strategy=TechnicalStrategy.MEAN_REVERSION,
            signal=signal,
            confidence=confidence,
            metrics=metrics,
        )

    def _analyze_momentum(
        self, prices: list[float], volumes: list[float]
    ) -> StrategySignal:
        """Momentum strategy using price momentum and volume confirmation."""
        if len(prices) < 30 or len(volumes) < 30:
            return StrategySignal(
                strategy=TechnicalStrategy.MOMENTUM,
                signal=TechnicalSignal.HOLD,
                confidence=0.3,
                metrics={"error": "insufficient_data"},
            )

        # Price momentum (1m, 3m, 6m equivalent)
        periods = [5, 15, 30]
        momentum_scores = []

        for period in periods:
            if len(prices) >= period + 1:
                change = (prices[-1] - prices[-period - 1]) / prices[-period - 1]
                momentum_scores.append(change)

        avg_momentum = (
            sum(momentum_scores) / len(momentum_scores) if momentum_scores else 0
        )

        # Volume trend
        recent_vol = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else volumes[-1]
        older_vol = sum(volumes[-15:-5]) / 10 if len(volumes) >= 15 else recent_vol
        volume_trend = recent_vol / older_vol if older_vol > 0 else 1.0

        # Rate of change
        roc_10 = (
            ((prices[-1] - prices[-11]) / prices[-11]) * 100 if len(prices) >= 11 else 0
        )

        metrics = {
            "avg_momentum": round(avg_momentum, 4),
            "momentum_1m": round(momentum_scores[0], 4)
            if len(momentum_scores) > 0
            else 0,
            "momentum_3m": round(momentum_scores[1], 4)
            if len(momentum_scores) > 1
            else 0,
            "volume_trend": round(volume_trend, 2),
            "roc_10": round(roc_10, 2),
        }

        # Momentum signal with volume confirmation
        strong_momentum = avg_momentum > 0.03 and volume_trend > 1.2
        weak_momentum = avg_momentum < -0.03 and volume_trend > 1.2

        if strong_momentum:
            signal = TechnicalSignal.BUY
            confidence = min(0.9, 0.55 + avg_momentum * 5)
        elif weak_momentum:
            signal = TechnicalSignal.SELL
            confidence = min(0.9, 0.55 + abs(avg_momentum) * 5)
        else:
            signal = TechnicalSignal.HOLD
            confidence = 0.4

        return StrategySignal(
            strategy=TechnicalStrategy.MOMENTUM,
            signal=signal,
            confidence=confidence,
            metrics=metrics,
        )

    def _analyze_volatility(
        self,
        prices: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> StrategySignal:
        """Volatility regime strategy using ATR and volatility state."""
        if len(prices) < 14:
            return StrategySignal(
                strategy=TechnicalStrategy.VOLATILITY,
                signal=TechnicalSignal.HOLD,
                confidence=0.3,
                metrics={"error": "insufficient_data"},
            )

        # Calculate ATR (Average True Range)
        if highs and lows and len(highs) == len(prices) and len(lows) == len(prices):
            atr = self._calculate_atr(highs, lows, prices, 14)
        else:
            # Proxy using price range
            ranges = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
            atr = (
                sum(ranges[-14:]) / 14
                if len(ranges) >= 14
                else sum(ranges) / len(ranges)
            )

        # Volatility regime (current vs historical)
        recent_volatility = atr / prices[-1] if prices[-1] > 0 else 0

        # Historical volatility (20-period std)
        if len(prices) >= 20:
            hist_mean = sum(prices[-20:]) / 20
            hist_std = (sum((p - hist_mean) ** 2 for p in prices[-20:]) / 20) ** 0.5
            hist_volatility = hist_std / hist_mean if hist_mean > 0 else 0
        else:
            hist_volatility = recent_volatility

        vol_regime = (
            "high"
            if recent_volatility > hist_volatility * 1.2
            else "low"
            if recent_volatility < hist_volatility * 0.8
            else "normal"
        )

        metrics = {
            "atr": round(atr, 4),
            "atr_pct": round(recent_volatility * 100, 2),
            "volatility_regime": vol_regime,
            "historical_vol": round(hist_volatility * 100, 2),
        }

        # Volatility signals
        # High vol + price near support = potential reversal (buy)
        # High vol + price near resistance = potential reversal (sell)
        # Low vol = expect breakout, direction unclear

        if vol_regime == "high":
            # High volatility creates opportunities but also risk
            signal = TechnicalSignal.HOLD
            confidence = 0.5
        elif vol_regime == "low":
            # Low volatility suggests breakout coming
            signal = TechnicalSignal.HOLD
            confidence = 0.4
        else:
            signal = TechnicalSignal.HOLD
            confidence = 0.5

        return StrategySignal(
            strategy=TechnicalStrategy.VOLATILITY,
            signal=signal,
            confidence=confidence,
            metrics=metrics,
        )

    def _analyze_stat_arb(self, prices: list[float]) -> StrategySignal:
        """Statistical arbitrage using Hurst exponent and skewness."""
        if len(prices) < 50:
            return StrategySignal(
                strategy=TechnicalStrategy.STAT_ARB,
                signal=TechnicalSignal.HOLD,
                confidence=0.3,
                metrics={"error": "insufficient_data"},
            )

        # Calculate returns
        returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))
        ]

        # Skewness (simplified)
        if len(returns) >= 20:
            mean_ret = sum(returns[-20:]) / 20
            variance = sum((r - mean_ret) ** 2 for r in returns[-20:]) / 20
            std_ret = variance**0.5

            if std_ret > 0:
                skewness = sum((r - mean_ret) ** 3 for r in returns[-20:]) / (
                    20 * std_ret**3
                )
            else:
                skewness = 0
        else:
            skewness = 0

        # Simplified Hurst exponent (RS method approximation)
        hurst = self._estimate_hurst(prices[-50:])

        # Autocorrelation (lag-1)
        if len(returns) >= 20:
            mean_r = sum(returns[-20:]) / 20
            numerator = sum(
                (returns[-i] - mean_r) * (returns[-i - 1] - mean_r)
                for i in range(1, min(20, len(returns)))
            )
            denominator = sum((r - mean_r) ** 2 for r in returns[-20:])
            autocorr = numerator / denominator if denominator > 0 else 0
        else:
            autocorr = 0

        metrics = {
            "skewness": round(skewness, 3),
            "hurst": round(hurst, 3),
            "autocorr": round(autocorr, 3),
        }

        # Interpretation
        # Hurst > 0.5: Trending (momentum)
        # Hurst < 0.5: Mean-reverting
        # Hurst ≈ 0.5: Random walk

        if hurst > 0.6 and autocorr > 0.1:
            signal = TechnicalSignal.BUY
            confidence = min(0.7, 0.5 + (hurst - 0.5))
        elif hurst < 0.4 and autocorr < -0.1:
            signal = TechnicalSignal.SELL
            confidence = min(0.7, 0.5 + (0.5 - hurst))
        else:
            signal = TechnicalSignal.HOLD
            confidence = 0.4

        return StrategySignal(
            strategy=TechnicalStrategy.STAT_ARB,
            signal=signal,
            confidence=confidence,
            metrics=metrics,
        )

    def _combine_signals(
        self, strategy_signals: list[StrategySignal]
    ) -> Tuple[TechnicalSignal, float]:
        """Combine strategy signals using weighted ensemble."""
        weighted_bull = 0.0
        weighted_bear = 0.0
        weighted_neutral = 0.0

        for sig in strategy_signals:
            weight = self.weights.get(sig.strategy, 0.2)

            if sig.signal in [TechnicalSignal.BUY, TechnicalSignal.STRONG_BUY]:
                weighted_bull += sig.confidence * weight
            elif sig.signal in [
                TechnicalSignal.SELL,
                TechnicalSignal.STRONG_SELL,
                TechnicalSignal.SHORT,
            ]:
                weighted_bear += sig.confidence * weight
            else:
                weighted_neutral += sig.confidence * weight

        # Determine composite signal
        threshold = 0.3
        if (
            weighted_bull > weighted_bear + threshold
            and weighted_bull > weighted_neutral
        ):
            if weighted_bull > 0.7:
                composite = TechnicalSignal.STRONG_BUY
            else:
                composite = TechnicalSignal.BUY
            confidence = weighted_bull
        elif (
            weighted_bear > weighted_bull + threshold
            and weighted_bear > weighted_neutral
        ):
            if weighted_bear > 0.7:
                composite = TechnicalSignal.STRONG_SELL
            else:
                composite = TechnicalSignal.SELL
            confidence = weighted_bear
        else:
            composite = TechnicalSignal.HOLD
            confidence = max(weighted_neutral, 0.4)

        return composite, min(0.95, confidence)

    def _build_reasoning(
        self, strategy_signals: list[StrategySignal], composite: TechnicalSignal
    ) -> str:
        """Build human-readable reasoning."""
        lines = [f"Composite Signal: {composite.value}", ""]

        for sig in strategy_signals:
            lines.append(f"{sig.strategy.value}:")
            lines.append(
                f"  Signal: {sig.signal.value} (confidence: {sig.confidence:.0%})"
            )
            for key, val in list(sig.metrics.items())[:3]:
                lines.append(f"  {key}: {val}")

        return "\n".join(lines)

    def _fallback_result(self) -> EnsembleResult:
        """Return fallback result for insufficient data."""
        return EnsembleResult(
            composite_signal=TechnicalSignal.HOLD,
            composite_confidence=0.3,
            strategy_signals=[],
            weights=self.weights,
            reasoning="Insufficient data for sophisticated technical analysis",
        )

    # Helper methods
    def _calculate_ema(self, prices: list[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _calculate_rsi(self, prices: list[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int = 14,
    ) -> float:
        """Calculate Average True Range."""
        true_ranges = []

        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(high_low, high_close, low_close))

        if len(true_ranges) >= period:
            return sum(true_ranges[-period:]) / period
        elif true_ranges:
            return sum(true_ranges) / len(true_ranges)
        else:
            return 0.0

    def _estimate_hurst(self, prices: list[float]) -> float:
        """Estimate Hurst exponent using simplified RS method."""
        if len(prices) < 20:
            return 0.5

        # Use log returns
        returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i - 1] > 0
        ]

        if len(returns) < 10:
            return 0.5

        # Simplified: use variance ratio
        var_1 = sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(
            returns
        )

        # Aggregate returns (2-period)
        agg_returns = [
            (returns[i] + returns[i + 1]) / 2 for i in range(0, len(returns) - 1, 2)
        ]
        if len(agg_returns) > 1:
            var_2 = sum(
                (r - sum(agg_returns) / len(agg_returns)) ** 2 for r in agg_returns
            ) / len(agg_returns)
        else:
            var_2 = var_1

        # Hurst ≈ 0.5 * log(var_2/var_1) / log(2) + 0.5
        if var_1 > 0 and var_2 > 0:
            hurst = 0.5 * math.log(var_2 / var_1) / math.log(2) + 0.5
            return max(0.1, min(0.9, hurst))

        return 0.5


# Singleton instance
sophisticated_technical_analyzer = SophisticatedTechnicalAnalyzer()

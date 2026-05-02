"""Technical analysis agent with SHORT signal capability.

Inspired by QuantAgent's indicator and decision agents.
Provides technical signals including SHORT recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional
from enum import Enum

from app.agents.research_note import ResearchNote


logger = logging.getLogger(__name__)


class TechnicalSignal(Enum):
    """Technical signal ratings including SHORT."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    SHORT = "SHORT"  # Enter SHORT position
    COVER = "COVER"  # Exit SHORT position


@dataclass
class TechnicalIndicators:
    """Technical indicators computed from price data."""

    rsi: float
    macd_signal: float
    macd_histogram: float
    williams_r: float
    roc: float  # Rate of Change
    stochastic_k: float
    stochastic_d: float
    volume_ratio: float  # Current volume / avg volume
    price_position: float  # Price relative to range (0-1)


@dataclass
class TechnicalAnalysisResult:
    """Result of technical analysis."""

    signal: TechnicalSignal
    conviction: int  # 1-100
    indicators: TechnicalIndicators
    thesis: str
    support_level: Optional[float]
    resistance_level: Optional[float]
    trend_direction: str  # "up", "down", "sideways"
    key_points: list[str]


class TechnicalAnalysisAgent:
    """Analyzes technical indicators to produce trading signals including SHORT.

    Based on QuantAgent's approach:
    - Computes RSI, MACD, Stochastic, Williams %R, ROC
    - Identifies overbought/oversold conditions
    - Detects trend direction
    - Can recommend SHORT positions (unlike bull/bear researchers)

    Key difference from bull/bear researchers:
    - Produces SHORT signals when conditions are bearish
    - Uses pure technical analysis, no fundamental/news data
    - Works on any timeframe (configured via parameters)
    """

    def __init__(
        self,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        williams_r_oversold: float = -80.0,
        williams_r_overbought: float = -20.0,
        min_volume_ratio: float = 0.5,
        short_threshold: float = 0.7,  # Confidence threshold for SHORT
    ):
        """Initialize with configurable thresholds."""
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.williams_r_oversold = williams_r_oversold
        self.williams_r_overbought = williams_r_overbought
        self.min_volume_ratio = min_volume_ratio
        self.short_threshold = short_threshold

    def analyze(
        self,
        ticker: str,
        data: dict,
        enable_short: bool = True,
    ) -> TechnicalAnalysisResult:
        """Analyze ticker using technical indicators.

        Args:
            ticker: Stock symbol
            data: Market data dict with:
                  - price_history: list of closing prices
                  - volume: list of volumes or single volume value
                  - high: list of highs (for Williams %R)
                  - low: list of lows (for Williams %R)
            enable_short: Whether to generate SHORT signals (default True)

        Returns:
            TechnicalAnalysisResult with signal, conviction, and thesis
        """
        # Compute technical indicators
        indicators = self._compute_indicators(data)

        # Analyze trend
        trend = self._analyze_trend(data.get("price_history", []))

        # Calculate support/resistance
        support, resistance = self._compute_support_resistance(
            data.get("price_history", []),
            data.get("high", []),
            data.get("low", []),
        )

        # Generate signal
        signal, conviction, key_points = self._generate_signal(
            indicators, trend, enable_short
        )

        # Build thesis
        thesis = self._build_thesis(ticker, signal, indicators, key_points, trend)

        return TechnicalAnalysisResult(
            signal=signal,
            conviction=conviction,
            indicators=indicators,
            thesis=thesis,
            support_level=support,
            resistance_level=resistance,
            trend_direction=trend,
            key_points=key_points,
        )

    def _compute_indicators(self, data: dict) -> TechnicalIndicators:
        """Compute all technical indicators from price data."""
        prices = data.get("price_history", [])
        volumes = data.get("volume", [])
        highs = data.get("high", [])
        lows = data.get("low", [])

        # Default values
        rsi = 50.0
        macd_signal = 0.0
        macd_histogram = 0.0
        williams_r = -50.0
        roc = 0.0
        stoch_k = 50.0
        stoch_d = 50.0
        volume_ratio = 1.0
        price_position = 0.5

        if len(prices) >= 14:
            # RSI (14-period)
            rsi = self._compute_rsi(prices, period=14)

            # MACD (12, 26, 9)
            macd_signal, macd_histogram = self._compute_macd(prices)

            # Rate of Change (10-period)
            if len(prices) >= 10:
                roc = ((prices[-1] - prices[-10]) / prices[-10]) * 100

            # Stochastic (14, 3, 3)
            if len(prices) >= 14:
                stoch_k, stoch_d = self._compute_stochastic(prices, highs, lows)

            # Price position in range
            if len(prices) >= 20:
                high_20 = max(prices[-20:])
                low_20 = min(prices[-20:])
                if high_20 != low_20:
                    price_position = (prices[-1] - low_20) / (high_20 - low_20)

        if highs and lows and len(highs) >= 14 and len(lows) >= 14:
            # Williams %R (14-period)
            williams_r = self._compute_williams_r(prices, highs, lows, period=14)

        if volumes:
            if isinstance(volumes, list) and len(volumes) >= 20:
                avg_volume = sum(volumes[-20:]) / 20
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            elif isinstance(volumes, (int, float)):
                # Single volume value provided
                volume_ratio = volumes / 10_000_000  # Normalize to expected volume

        return TechnicalIndicators(
            rsi=rsi,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            williams_r=williams_r,
            roc=roc,
            stochastic_k=stoch_k,
            stochastic_d=stoch_d,
            volume_ratio=volume_ratio,
            price_position=price_position,
        )

    def _compute_rsi(self, prices: list, period: int = 14) -> float:
        """Compute RSI indicator."""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _compute_macd(self, prices: list) -> tuple[float, float]:
        """Compute MACD signal and histogram."""
        if len(prices) < 26:
            return 0.0, 0.0

        # EMA 12
        ema_12 = self._compute_ema(prices, 12)
        # EMA 26
        ema_26 = self._compute_ema(prices, 26)

        macd_line = ema_12 - ema_26
        signal_line = macd_line * 0.8  # Simplified signal
        histogram = macd_line - signal_line

        return round(signal_line, 4), round(histogram, 4)

    def _compute_ema(self, prices: list, period: int) -> float:
        """Compute Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _compute_stochastic(
        self, prices: list, highs: list, lows: list, period: int = 14
    ) -> tuple[float, float]:
        """Compute Stochastic oscillator."""
        if len(prices) < period:
            return 50.0, 50.0

        recent_high = max(highs[-period:] if highs else prices[-period:])
        recent_low = min(lows[-period:] if lows else prices[-period:])

        if recent_high == recent_low:
            return 50.0, 50.0

        k = ((prices[-1] - recent_low) / (recent_high - recent_low)) * 100
        # Simplified %D as 3-period SMA of %K
        d = k  # In practice, would average last 3 %K values

        return round(k, 2), round(d, 2)

    def _compute_williams_r(
        self, prices: list, highs: list, lows: list, period: int = 14
    ) -> float:
        """Compute Williams %R."""
        if len(highs) < period or len(lows) < period:
            return -50.0

        recent_high = max(highs[-period:])
        recent_low = min(lows[-period:])

        if recent_high == recent_low:
            return -50.0

        wr = ((recent_high - prices[-1]) / (recent_high - recent_low)) * -100
        return round(wr, 2)

    def _analyze_trend(self, prices: list) -> str:
        """Analyze trend direction."""
        if len(prices) < 20:
            return "sideways"

        # Simple trend: compare first half to second half average
        first_half = sum(prices[:10]) / 10
        second_half = sum(prices[-10:]) / 10

        change_pct = ((second_half - first_half) / first_half) * 100

        if change_pct > 5:
            return "up"
        elif change_pct < -5:
            return "down"
        else:
            return "sideways"

    def _compute_support_resistance(
        self,
        prices: list,
        highs: list,
        lows: list,
    ) -> tuple[Optional[float], Optional[float]]:
        """Compute support and resistance levels."""
        if len(prices) < 20:
            return None, None

        # Support: recent low
        support = min(lows[-20:]) if lows and len(lows) >= 20 else min(prices[-20:])

        # Resistance: recent high
        resistance = (
            max(highs[-20:]) if highs and len(highs) >= 20 else max(prices[-20:])
        )

        return round(support, 2), round(resistance, 2)

    def _generate_signal(
        self,
        indicators: TechnicalIndicators,
        trend: str,
        enable_short: bool,
    ) -> tuple[TechnicalSignal, int, list[str]]:
        """Generate trading signal from indicators."""
        score = 50  # Start neutral
        key_points = []

        # RSI analysis
        if indicators.rsi > self.rsi_overbought:
            score -= 15
            key_points.append(f"RSI overbought at {indicators.rsi:.1f}")
        elif indicators.rsi < self.rsi_oversold:
            score += 15
            key_points.append(f"RSI oversold at {indicators.rsi:.1f}")

        # MACD analysis
        if indicators.macd_histogram > 0:
            score += 10
            key_points.append("MACD histogram positive")
        elif indicators.macd_histogram < 0:
            score -= 10
            key_points.append("MACD histogram negative")

        # Williams %R analysis
        if indicators.williams_r > self.williams_r_overbought:
            score -= 10
            key_points.append(f"Williams %R overbought at {indicators.williams_r:.1f}")
        elif indicators.williams_r < self.williams_r_oversold:
            score += 10
            key_points.append(f"Williams %R oversold at {indicators.williams_r:.1f}")

        # Rate of Change
        if indicators.roc > 10:
            score += 10
            key_points.append(f"Strong momentum: ROC {indicators.roc:.1f}%")
        elif indicators.roc < -10:
            score -= 10
            key_points.append(f"Weak momentum: ROC {indicators.roc:.1f}%")

        # Stochastic
        if indicators.stochastic_k > 80:
            score -= 5
            key_points.append(f"Stochastic overbought: K={indicators.stochastic_k:.1f}")
        elif indicators.stochastic_k < 20:
            score += 5
            key_points.append(f"Stochastic oversold: K={indicators.stochastic_k:.1f}")

        # Trend alignment
        if trend == "up" and score > 50:
            score += 5
        elif trend == "down" and score < 50:
            score -= 5

        # Volume confirmation
        if indicators.volume_ratio > 1.5:
            score += 5 if score > 50 else -5
            key_points.append(f"High volume: {indicators.volume_ratio:.1f}x avg")

        # Determine signal
        conviction = min(95, max(20, abs(score)))

        if score >= 75:
            signal = TechnicalSignal.STRONG_BUY
        elif score >= 60:
            signal = TechnicalSignal.BUY
        elif score >= 40:
            signal = TechnicalSignal.HOLD
        elif score >= 25:
            signal = TechnicalSignal.SELL
        else:
            # Strong bearish - potential SHORT
            if enable_short and conviction >= 70:
                signal = TechnicalSignal.SHORT
            else:
                signal = TechnicalSignal.STRONG_SELL

        return signal, conviction, key_points

    def _build_thesis(
        self,
        ticker: str,
        signal: TechnicalSignal,
        indicators: TechnicalIndicators,
        key_points: list[str],
        trend: str,
    ) -> str:
        """Build human-readable thesis."""
        signal_desc = signal.value.replace("_", " ")

        thesis_parts = [f"{signal_desc} signal for {ticker}"]

        if key_points:
            thesis_parts.append("; ".join(key_points[:3]))

        thesis_parts.append(
            f"RSI: {indicators.rsi:.1f}, MACD: {indicators.macd_histogram:+.2f}"
        )
        thesis_parts.append(f"Trend: {trend.upper()}")

        if signal == TechnicalSignal.SHORT:
            thesis_parts.append(
                "SHORT recommendation - conditions favor downward movement"
            )

        return ". ".join(thesis_parts)

    def create_research_note(self, result: TechnicalAnalysisResult) -> ResearchNote:
        """Convert TechnicalAnalysisResult to ResearchNote for debate system."""
        # Map technical signal to bias
        if result.signal in (TechnicalSignal.STRONG_BUY, TechnicalSignal.BUY):
            bias = "bullish"
        elif result.signal in (
            TechnicalSignal.SHORT,
            TechnicalSignal.STRONG_SELL,
            TechnicalSignal.SELL,
        ):
            bias = "bearish"
        else:
            bias = "neutral"

        return ResearchNote(
            thesis=result.thesis,
            confidence=result.conviction,
            key_points=result.key_points,
            persona=f"technical_{bias}",
            supporting_indicators={
                "rsi": result.indicators.rsi,
                "macd_histogram": result.indicators.macd_histogram,
                "williams_r": result.indicators.williams_r,
                "roc": result.indicators.roc,
                "stochastic_k": result.indicators.stochastic_k,
                "trend": result.trend_direction,
                "signal": result.signal.value,
            },
        )


# Singleton instance
technical_analysis_agent = TechnicalAnalysisAgent()

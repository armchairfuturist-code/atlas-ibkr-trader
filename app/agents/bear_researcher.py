"""Bear researcher agent - argues bearish case for a ticker.

Uses heuristic pattern matching on market data to identify bearish signals.
In production, this would use LLM analysis.
"""

import logging
from typing import Optional

from app.agents.research_note import ResearchNote

logger = logging.getLogger(__name__)


class BearResearcher:
    """Agent that argues bearish case for a ticker."""

    def analyze(self, ticker: str, data: dict) -> ResearchNote:
        """Analyze ticker and return bearish research note.

        Args:
            ticker: Stock symbol
            data: Dict with keys like 'price', 'volume', 'indicators',
                  'news', 'fundamentals'

        Returns:
            ResearchNote with bearish thesis
        """
        key_points = []
        supporting_indicators = {}
        confidence = 50  # Base confidence

        # Analyze price momentum
        if "price_history" in data and len(data["price_history"]) >= 20:
            prices = data["price_history"]
            if prices[-1] < prices[-20]:  # Price down over 20 periods
                key_points.append("Price momentum negative over lookback period")
                confidence += 10
                supporting_indicators["momentum"] = "negative"
            else:
                supporting_indicators["momentum"] = "positive"

        # Analyze volume
        if "volume" in data:
            vol = data["volume"]
            if vol < 5_000_000:  # Low volume
                key_points.append("Below-average trading volume - lack of conviction")
                confidence += 5
                supporting_indicators["volume"] = "low"
            else:
                supporting_indicators["volume"] = "healthy"

        # Analyze RSI (if available)
        if "indicators" in data and "rsi" in data["indicators"]:
            rsi = data["indicators"]["rsi"]
            supporting_indicators["rsi"] = rsi
            if rsi > 70:
                key_points.append(
                    f"RSI overbought at {rsi:.1f} - potential pullback risk"
                )
                confidence += 15
            elif rsi > 60:
                key_points.append(f"RSI neutral-bearish at {rsi:.1f}")
                confidence += 5

        # Analyze MACD (if available)
        if "indicators" in data and "macd" in data["indicators"]:
            macd = data["indicators"]["macd"]
            supporting_indicators["macd"] = macd
            if isinstance(macd, dict) and macd.get("histogram", 0) < 0:
                key_points.append("MACD histogram negative - bearish momentum building")
                confidence += 10

        # Analyze news sentiment (if available)
        if "news" in data and data["news"]:
            negative_count = sum(1 for n in data["news"] if self._is_negative_news(n))
            if negative_count > len(data["news"]) * 0.5:
                key_points.append(
                    f"Negative news sentiment ({negative_count}/{len(data['news'])} articles)"
                )
                confidence += 10
                supporting_indicators["news_sentiment"] = "negative"

        # Analyze fundamentals (if available)
        if "fundamentals" in data:
            funds = data["fundamentals"]
            supporting_indicators["fundamentals"] = funds

            pe = funds.get("pe_ratio", 0)
            if pe > 35:
                key_points.append(f"Stretched P/E ratio of {pe:.1f} - valuation risk")
                confidence += 10
            elif pe < 0:
                key_points.append("Negative P/E ratio - unprofitable")
                confidence += 15

            earnings_yield = funds.get("earnings_yield", 0)
            if earnings_yield < 0:
                key_points.append(f"Negative earnings yield - profitability concerns")
                confidence += 10

        # Check for high volatility
        if "indicators" in data and "volatility" in data["indicators"]:
            vol = data["indicators"]["volatility"]
            supporting_indicators["volatility"] = vol
            if vol > 30:
                key_points.append(f"High volatility at {vol:.1f}% - elevated risk")
                confidence += 5

        # Clamp confidence
        confidence = min(95, max(20, confidence))

        # Build thesis
        if key_points:
            thesis = f"Bearish on {ticker}: " + "; ".join(key_points[:3])
        else:
            thesis = f"Cautiously bearish on {ticker} - insufficient bearish signals"
            confidence = max(30, confidence - 20)

        return ResearchNote(
            thesis=thesis,
            confidence=confidence,
            key_points=key_points[:5],  # Limit to top 5
            persona="bear",
            supporting_indicators=supporting_indicators,
        )

    def _is_negative_news(self, news_item: dict) -> bool:
        """Check if news item is negative."""
        negative_keywords = [
            "miss",
            "missed",
            "below",
            "loss",
            "cut",
            "downgrade",
            "sell",
            "weak",
            "decline",
            "fell",
            "drop",
            "layoff",
            "investigation",
            "lawsuit",
            "fraud",
            "warning",
            "warned",
            "risk",
            "risks",
            "concern",
            "slowdown",
            "weakness",
        ]
        positive_keywords = [
            "beat",
            "beats",
            "exceeded",
            "exceeds",
            "growth",
            "profit",
            "surge",
            "surged",
            "rally",
            "upgrade",
            "buy",
            "strong",
        ]

        text = str(news_item.get("title", "")).lower()
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        pos_count = sum(1 for kw in positive_keywords if kw in text)

        return neg_count > pos_count

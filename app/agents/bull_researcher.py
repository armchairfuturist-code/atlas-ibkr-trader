"""Bull researcher agent - argues bullish case for a ticker.

Uses heuristic pattern matching on market data to identify bullish signals.
In production, this would use LLM analysis.
"""

import logging
from typing import Optional

from app.agents.research_note import ResearchNote

logger = logging.getLogger(__name__)


class BullResearcher:
    """Agent that argues bullish case for a ticker."""

    def analyze(self, ticker: str, data: dict) -> ResearchNote:
        """Analyze ticker and return bullish research note.

        Args:
            ticker: Stock symbol
            data: Dict with keys like 'price', 'volume', 'indicators',
                  'news', 'fundamentals'

        Returns:
            ResearchNote with bullish thesis
        """
        key_points = []
        supporting_indicators = {}
        confidence = 50  # Base confidence

        # Analyze price momentum
        if "price_history" in data and len(data["price_history"]) >= 20:
            prices = data["price_history"]
            if prices[-1] > prices[-20]:  # Price up over 20 periods
                key_points.append("Price momentum positive over lookback period")
                confidence += 10
                supporting_indicators["momentum"] = "positive"
            else:
                supporting_indicators["momentum"] = "negative"

        # Analyze volume
        if "volume" in data:
            vol = data["volume"]
            if vol > 10_000_000:  # Healthy volume
                key_points.append(
                    "Above-average trading volume suggests institutional interest"
                )
                confidence += 5
                supporting_indicators["volume"] = "healthy"
            else:
                supporting_indicators["volume"] = "low"

        # Analyze RSI (if available)
        if "indicators" in data and "rsi" in data["indicators"]:
            rsi = data["indicators"]["rsi"]
            supporting_indicators["rsi"] = rsi
            if rsi < 30:
                key_points.append(f"RSI oversold at {rsi:.1f} - potential bounce setup")
                confidence += 15
            elif rsi < 50:
                key_points.append(f"RSI neutral-bullish at {rsi:.1f}")
                confidence += 5

        # Analyze MACD (if available)
        if "indicators" in data and "macd" in data["indicators"]:
            macd = data["indicators"]["macd"]
            supporting_indicators["macd"] = macd
            if isinstance(macd, dict) and macd.get("histogram", 0) > 0:
                key_points.append("MACD histogram positive - bullish momentum building")
                confidence += 10

        # Analyze news sentiment (if available)
        if "news" in data and data["news"]:
            positive_count = sum(1 for n in data["news"] if self._is_positive_news(n))
            if positive_count > len(data["news"]) * 0.6:
                key_points.append(
                    f"Positive news sentiment ({positive_count}/{len(data['news'])} articles)"
                )
                confidence += 10
                supporting_indicators["news_sentiment"] = "positive"

        # Analyze fundamentals (if available)
        if "fundamentals" in data:
            funds = data["fundamentals"]
            supporting_indicators["fundamentals"] = funds

            pe = funds.get("pe_ratio", 0)
            if 0 < pe < 25:
                key_points.append(f"Attractive P/E ratio of {pe:.1f}")
                confidence += 10

            earnings_yield = funds.get("earnings_yield", 0)
            if earnings_yield > 0.05:
                key_points.append(
                    f"Strong earnings yield of {earnings_yield * 100:.1f}%"
                )
                confidence += 5

        # Clamp confidence
        confidence = min(95, max(20, confidence))

        # Build thesis
        if key_points:
            thesis = f"Bullish on {ticker}: " + "; ".join(key_points[:3])
        else:
            thesis = f"Cautiously bullish on {ticker} - insufficient bullish signals"
            confidence = max(30, confidence - 20)

        return ResearchNote(
            thesis=thesis,
            confidence=confidence,
            key_points=key_points[:5],  # Limit to top 5
            persona="bull",
            supporting_indicators=supporting_indicators,
        )

    def _is_positive_news(self, news_item: dict) -> bool:
        """Check if news item is positive."""
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
            "upgrade",
            "buy",
            "strong",
            "recovery",
            "gain",
            "gains",
            "high",
            "highs",
        ]
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
        ]

        text = str(news_item.get("title", "")).lower()
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)

        return pos_count > neg_count

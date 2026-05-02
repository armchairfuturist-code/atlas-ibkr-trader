"""Market data provider that works with or without TWS.

- When TWS is running: use real-time IBKR data
- When TWS is closed: fall back to yfinance (free, no TWS needed)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import random

logger = logging.getLogger(__name__)

# Try to import yfinance
YFINANCE_AVAILABLE = False
try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not installed. Run: pip install yfinance")


class MarketDataProvider:
    """
    Unified market data provider.

    Automatically uses:
    1. IBKR (real-time) when connected
    2. yfinance (delayed) when IBKR unavailable

    Usage:
        provider = MarketDataProvider(ibkr_adapter)  # Pass IBKR adapter for live mode
        # OR
        provider = MarketDataProvider()  # yfinance only, no TWS needed

        quote = provider.get_quote('SPY')
        hist = provider.get_historical('SPY', '3 M')
    """

    def __init__(self, ibkr_adapter=None):
        """Initialize with optional IBKR adapter.

        Args:
            ibkr_adapter: IBKRAdapter instance. If None or not connected,
                         will use yfinance.
        """
        self._ibkr = ibkr_adapter
        self._use_yfinance = True  # Default to yfinance

    def _should_use_ibkr(self) -> bool:
        """Check if IBKR is connected and should be used."""
        if self._ibkr is None:
            return False
        if not self._ibkr.is_connected():
            return False
        if self._ibkr.is_stub_mode():
            return False  # Stub mode doesn't have real data
        return True

    def get_quote(self, ticker: str) -> Optional[dict]:
        """Get real-time quote.

        Returns dict with: ticker, bid, ask, last, volume, timestamp
        """
        # Try IBKR first
        if self._should_use_ibkr():
            quote = self._ibkr.get_quote(ticker)
            if quote:
                quote["source"] = "IBKR"
                return quote

        # Fall back to yfinance
        if YFINANCE_AVAILABLE:
            return self._get_yfinance_quote(ticker)

        # No data source available
        return None

    def _get_yfinance_quote(self, ticker: str) -> Optional[dict]:
        """Get quote from yfinance (delayed ~15min)."""
        try:
            t = yf.Ticker(ticker)
            info = t.info

            last = info.get("regularMarketPrice") or info.get("currentPrice")
            if not last:
                return None

            bid = info.get("bid", last)
            ask = info.get("ask", last)
            volume = info.get("regularMarketVolume", 0)

            return {
                "ticker": ticker,
                "bid": bid,
                "ask": ask,
                "last": last,
                "volume": volume,
                "timestamp": datetime.now().isoformat(),
                "source": "yfinance",
            }
        except Exception as e:
            logger.error(f"yfinance quote failed for {ticker}: {e}")
            return None

    def get_historical(
        self, ticker: str, duration: str = "3 M", bar_size: str = "1d"
    ) -> Optional[list[dict]]:
        """Get historical bars.

        Args:
            ticker: Stock/ETF symbol
            duration: Duration string (e.g., '3 M', '1 Y', '1 W')
            bar_size: Bar size (e.g., '1d', '1wk', '1h')

        Returns:
            List of dicts with: date, open, high, low, close, volume
        """
        # Try IBKR first
        if self._should_use_ibkr():
            bars = self._ibkr.get_historical(ticker, duration, bar_size)
            if bars:
                return bars

        # Fall back to yfinance
        if YFINANCE_AVAILABLE:
            return self._get_yfinance_historical(ticker, duration)

        return None

    def _get_yfinance_historical(
        self, ticker: str, duration: str
    ) -> Optional[list[dict]]:
        """Get historical data from yfinance."""
        # Parse duration to yfinance format
        duration_map = {
            "1 W": "5d",
            "2 W": "14d",
            "1 M": "1mo",
            "3 M": "3mo",
            "6 M": "6mo",
            "1 Y": "1y",
            "2 Y": "2y",
            "5 Y": "5y",
        }

        period = duration_map.get(duration, "3mo")

        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period)

            if df.empty:
                return None

            bars = []
            for idx, row in df.iterrows():
                bars.append(
                    {
                        "date": idx.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                )

            return bars
        except Exception as e:
            logger.error(f"yfinance historical failed for {ticker}: {e}")
            return None

    def get_info(self, ticker: str) -> Optional[dict]:
        """Get fundamental info from yfinance."""
        if YFINANCE_AVAILABLE:
            try:
                t = yf.Ticker(ticker)
                return t.info
            except Exception as e:
                logger.error(f"yfinance info failed for {ticker}: {e}")
        return None

    def is_live_data(self) -> bool:
        """Check if we're using live (IBKR) data."""
        return self._should_use_ibkr()


# Standalone provider (yfinance only, no IBKR)
class YFinanceProvider(MarketDataProvider):
    """yfinance-only provider when IBKR is not available."""

    def __init__(self):
        super().__init__(None)
        self._use_yfinance = True

    def _should_use_ibkr(self) -> bool:
        return False

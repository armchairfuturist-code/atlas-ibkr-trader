"""Vendor abstraction layer for market data providers.

Inspired by TradingAgents' route_to_vendor pattern - allows switching
between different data sources (IBKR, yfinance, Alpha Vantage) without
changing the interface.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataVendor(ABC):
    """Abstract base class for market data vendors."""

    @abstractmethod
    def get_stock_data(self, symbol: str, start: date, end: date) -> dict:
        """Get OHLCV stock data."""
        pass

    @abstractmethod
    def get_indicators(self, symbol: str) -> dict:
        """Get technical indicators (RSI, MACD, etc.)."""
        pass

    @abstractmethod
    def get_news(self, symbol: str, days: int = 7) -> list[dict]:
        """Get recent news for symbol."""
        pass

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict:
        """Get fundamental data (earnings, balance sheet, etc.)."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if vendor is currently available."""
        pass


class IBKRVendor(DataVendor):
    """IBKR vendor - wraps the IBKR data provider."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._connected = False

    def get_stock_data(self, symbol: str, start: date, end: date) -> dict:
        """Get OHLCV data from IBKR (mock for now)."""
        # TODO: Integrate with real IBKR API
        logger.warning(
            f"IBKRVendor.get_stock_data called - returning mock data for {symbol}"
        )
        return {
            "symbol": symbol,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": [],
            "source": "ibkr_mock",
        }

    def get_indicators(self, symbol: str) -> dict:
        """Get technical indicators from IBKR (mock for now)."""
        logger.warning(
            f"IBKRVendor.get_indicators called - returning mock data for {symbol}"
        )
        return {
            "symbol": symbol,
            "rsi": 50.0,
            "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
            "source": "ibkr_mock",
        }

    def get_news(self, symbol: str, days: int = 7) -> list[dict]:
        """Get news from IBKR (mock for now)."""
        logger.warning(f"IBKRVendor.get_news called - returning mock data for {symbol}")
        return []

    def get_fundamentals(self, symbol: str) -> dict:
        """Get fundamentals from IBKR (mock for now)."""
        logger.warning(
            f"IBKRVendor.get_fundamentals called - returning mock data for {symbol}"
        )
        return {
            "symbol": symbol,
            "pe_ratio": 20.0,
            "earnings_yield": 0.05,
            "source": "ibkr_mock",
        }

    def is_available(self) -> bool:
        """Check if IBKR is connected."""
        return self._connected


class YFinanceVendor(DataVendor):
    """Yahoo Finance vendor - free alternative data source."""

    def __init__(self):
        self._available = True
        self._yfinance = None  # Lazy import

    def _get_yfinance(self):
        """Lazy import yfinance."""
        if self._yfinance is None:
            try:
                import yfinance

                self._yfinance = yfinance
            except ImportError:
                logger.error("yfinance not installed. Run: pip install yfinance")
                self._available = False
                return None
        return self._yfinance

    def get_stock_data(self, symbol: str, start: date, end: date) -> dict:
        """Get OHLCV data from yfinance."""
        yf = self._get_yfinance()
        if yf is None:
            return {}

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)

            if df.empty:
                return {"symbol": symbol, "data": [], "source": "yfinance"}

            return {
                "symbol": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "data": df.to_dict("records"),
                "source": "yfinance",
            }
        except Exception as e:
            logger.error(f"yfinance error for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "source": "yfinance"}

    def get_indicators(self, symbol: str) -> dict:
        """Calculate technical indicators from stock data."""
        # For now, return basic RSI calculation
        # In production, would use stockstats or ta-lib
        return {
            "symbol": symbol,
            "rsi": 50.0,  # Placeholder
            "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
            "source": "yfinance_calculated",
        }

    def get_news(self, symbol: str, days: int = 7) -> list[dict]:
        """Get news from yfinance."""
        yf = self._get_yfinance()
        if yf is None:
            return []

        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            return [
                {
                    "title": n.get("title", ""),
                    "link": n.get("link", ""),
                    "pubDate": n.get("pubDate", ""),
                }
                for n in news[:days]
                if news
            ] or []
        except Exception as e:
            logger.error(f"yfinance news error for {symbol}: {e}")
            return []

    def get_fundamentals(self, symbol: str) -> dict:
        """Get fundamentals from yfinance."""
        yf = self._get_yfinance()
        if yf is None:
            return {}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "pe_ratio": info.get("trailingPE", 0),
                "earnings_yield": info.get("earningsYield", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "source": "yfinance",
            }
        except Exception as e:
            logger.error(f"yfinance fundamentals error for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "source": "yfinance"}

    def is_available(self) -> bool:
        """Check if yfinance is available."""
        return self._get_yfinance() is not None


# Vendor registry - maps vendor names to instances
VENDOR_REGISTRY: dict[str, DataVendor] = {
    "ibkr": IBKRVendor(),
    "yfinance": YFinanceVendor(),
}


def route_to_vendor(method: str, vendor: str = "yfinance", *args, **kwargs):
    """Route a data request to the appropriate vendor with fallback.

    Args:
        method: Method name to call (e.g., "get_stock_data")
        vendor: Primary vendor name (default: yfinance)
        *args, **kwargs: Arguments to pass to the vendor method

    Returns:
        Result from vendor method, or {} on failure

    Example:
        data = route_to_vendor("get_stock_data", "yfinance", "AAPL", start, end)
    """
    # Try primary vendor
    primary = VENDOR_REGISTRY.get(vendor.lower())
    if primary and hasattr(primary, method):
        try:
            result = getattr(primary, method)(*args, **kwargs)
            if result:  # Got valid data
                return result
        except Exception as e:
            logger.warning(f"Primary vendor {vendor}.{method} failed: {e}")

    # Fallback chain
    fallbacks = [k for k in VENDOR_REGISTRY.keys() if k != vendor.lower()]
    for fallback_name in fallbacks:
        fallback = VENDOR_REGISTRY.get(fallback_name)
        if fallback and hasattr(fallback, method):
            try:
                result = getattr(fallback, method)(*args, **kwargs)
                if result:
                    logger.info(f"Fallback to {fallback_name}.{method} succeeded")
                    return result
            except Exception as e:
                logger.warning(f"Fallback vendor {fallback_name}.{method} failed: {e}")

    # All vendors failed
    logger.error(f"All vendors failed for {method}")
    return {}


def get_vendor(name: str) -> Optional[DataVendor]:
    """Get a vendor instance by name."""
    return VENDOR_REGISTRY.get(name.lower())


def list_vendors() -> list[str]:
    """List available vendor names."""
    return list(VENDOR_REGISTRY.keys())

"""Market data provider abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import random
import time


@dataclass
class Quote:
    """Market quote for a security."""
    ticker: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime
    
    @property
    def spread(self) -> float:
        """Bid-ask spread in dollars."""
        return self.ask - self.bid
    
    @property
    def spread_bps(self) -> float:
        """Bid-ask spread in basis points."""
        if self.last == 0:
            return 0
        return (self.spread / self.last) * 10000
    
    @property
    def mid(self) -> float:
        """Mid price."""
        return (self.bid + self.ask) / 2


@dataclass
class OHLCV:
    """OHLCV bar data."""
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime


class DataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Get real-time quote for a ticker."""
        pass
    
    @abstractmethod
    def get_historical(self, ticker: str, days: int) -> list[OHLCV]:
        """Get historical OHLCV bars."""
        pass
    
    @abstractmethod
    def is_fresh(self, ticker: str, max_age_seconds: int = 60) -> bool:
        """Check if quote data is fresh."""
        pass
    
    @abstractmethod
    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect to provider."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from provider."""
        pass


class FixtureProvider(DataProvider):
    """Fixture-based provider for testing."""
    
    def __init__(self, fixtures: dict[str, Quote]):
        self._fixtures = fixtures
    
    def get_quote(self, ticker: str) -> Optional[Quote]:
        return self._fixtures.get(ticker.upper())
    
    def get_historical(self, ticker: str, days: int) -> list[OHLCV]:
        return []
    
    def is_fresh(self, ticker: str, max_age_seconds: int = 60) -> bool:
        quote = self.get_quote(ticker)
        if quote is None:
            return False
        age = time.time() - quote.timestamp.timestamp()
        return age < max_age_seconds
    
    def connect(self) -> tuple[bool, Optional[str]]:
        return True, None
    
    def disconnect(self) -> None:
        pass


# Fixture data for testing
def create_fresh_fixture() -> dict[str, Quote]:
    """Create a fresh quote fixture."""
    return {
        "SPY": Quote(
            ticker="SPY", bid=500.00, ask=500.10, last=500.05,
            volume=80000000, timestamp=datetime.now()
        ),
        "QQQ": Quote(
            ticker="QQQ", bid=420.00, ask=420.05, last=420.02,
            volume=40000000, timestamp=datetime.now()
        ),
        "XLF": Quote(
            ticker="XLF", bid=40.00, ask=40.05, last=40.02,
            volume=25000000, timestamp=datetime.now()
        ),
        "XLK": Quote(
            ticker="XLK", bid=200.00, ask=200.10, last=200.05,
            volume=20000000, timestamp=datetime.now()
        ),
        "XLE": Quote(
            ticker="XLE", bid=85.00, ask=85.05, last=85.02,
            volume=15000000, timestamp=datetime.now()
        ),
    }


def create_stale_fixture() -> dict[str, Quote]:
    """Create a stale quote fixture (old timestamp)."""
    from datetime import timedelta
    stale_time = datetime.now() - timedelta(seconds=120)
    return {
        "SPY": Quote(
            ticker="SPY", bid=500.00, ask=500.10, last=500.05,
            volume=80000000, timestamp=stale_time
        ),
    }


class IBKRDataProvider(DataProvider):
    """Real-time data provider - REALISTIC MOCK for demo.
    
    Note: Real IBKR integration requires proper async handling.
    This mock provides realistic prices that change each second.
    """
    
    # Base prices for common ETFs (realistic values)
    BASE_PRICES = {
        "SPY": 500.0,
        "QQQ": 420.0,
        "XLF": 40.0,
        "XLK": 200.0,
        "XLE": 85.0,
        "XLV": 145.0,
        "XLY": 195.0,
        "XLI": 125.0,
        "XLB": 85.0,
        "IWM": 200.0,
        "DIA": 400.0,
        "EEM": 40.0,
    }
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._connected = False
        self._cache: dict[str, Quote] = {}
        self._rng = random.Random()
    
    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect - mock with realistic data."""
        self._connected = True
        return True, None
    
    def disconnect(self) -> None:
        """Disconnect."""
        self._connected = False
    
    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Get quote with realistic time-based variation."""
        if not self._connected:
            return None
        
        ticker = ticker.upper()
        
        # Get base price or default
        base_price = self.BASE_PRICES.get(ticker, 100.0)
        
        # Add variation based on current time (changes every second)
        # Use a local Random seeded by time+ticker so each call produces
        # different values without poisoning the global RNG.
        now = datetime.now()
        self._rng.seed(now.hour * 3600 + now.minute * 60 + now.second + hash(ticker) % 1000)

        variation = self._rng.uniform(-0.015, 0.015)  # +/- 1.5%
        price = base_price * (1 + variation)

        # Create realistic bid/ask spread
        spread_pct = self._rng.uniform(0.0005, 0.0015)  # 0.05% to 0.15%
        spread = price * spread_pct
        bid = round(price - spread/2, 2)
        ask = round(price + spread/2, 2)

        quote = Quote(
            ticker=ticker,
            bid=bid,
            ask=ask,
            last=round(price, 2),
            volume=self._rng.randint(5000000, 50000000),
            timestamp=datetime.now()
        )
        
        self._cache[ticker] = quote
        return quote
    
    def get_historical(self, ticker: str, days: int) -> list[OHLCV]:
        """Get historical - mock returns empty."""
        return []
    
    def is_fresh(self, ticker: str, max_age_seconds: int = 60) -> bool:
        """Check if cached quote is fresh."""
        quote = self._cache.get(ticker.upper())
        if quote is None:
            return False
        age = (datetime.now() - quote.timestamp).total_seconds()
        return age < max_age_seconds

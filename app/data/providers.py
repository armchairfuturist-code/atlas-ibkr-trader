"""Market data provider abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
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


class FixtureProvider(DataProvider):
    """Fixture-based provider for testing."""
    
    def __init__(self, fixtures: dict[str, Quote]):
        self._fixtures = fixtures
    
    def get_quote(self, ticker: str) -> Optional[Quote]:
        return self._fixtures.get(ticker.upper())
    
    def get_historical(self, ticker: str, days: int) -> list[OHLCV]:
        # Return empty for fixture
        return []
    
    def is_fresh(self, ticker: str, max_age_seconds: int = 60) -> bool:
        quote = self.get_quote(ticker)
        if quote is None:
            return False
        age = time.time() - quote.timestamp.timestamp()
        return age < max_age_seconds


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
    """Real-time data provider using ib_insync."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._ib = None
        self._connected = False
        self._cache: dict[str, Quote] = {}
    
    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect to IBKR."""
        try:
            import asyncio
            
            async def _connect():
                import nest_asyncio
                nest_asyncio.apply()
                from ib_insync import IB
                self._ib = IB()
                self._ib.connect(self.host, self.port, clientId=self.client_id)
                return self._ib.isConnected()
            
            # Run async connect
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_connect())
                if result:
                    self._connected = True
                    return True, None
                return False, "Connection returned false"
            finally:
                loop.close()
                
        except Exception as e:
            return False, str(e)
    
    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self._ib and self._connected:
            self._ib.disconnect()
            self._connected = False
    
    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Get real-time quote from IBKR."""
        if not self._connected:
            return None
        
        try:
            contract = self._ib.reqContractDetails(
                self._ib.compileContractId(ticker, "STK")
            )[0].contract
            
            # Request live tickers
            ticker_obj = self._ib.reqMktData(contract, "", False, False)
            self._ib.sleep(0.5)  # Wait for data
            
            quote = Quote(
                ticker=ticker,
                bid=ticker_obj.bid or 0,
                ask=ticker_obj.ask or 0,
                last=ticker_obj.last or 0,
                volume=ticker_obj.volume or 0,
                timestamp=datetime.now()
            )
            
            # Cancel the subscription
            self._ib.cancelMktData(ticker_obj)
            
            # Cache it
            self._cache[ticker.upper()] = quote
            return quote
            
        except Exception as e:
            # Fall back to cache
            return self._cache.get(ticker.upper())
    
    def get_historical(self, ticker: str, days: int) -> list[OHLCV]:
        """Get historical bars from IBKR."""
        if not self._connected:
            return []
        
        try:
            contract = self._ib.reqContractDetails(
                self._ib.compileContractId(ticker, "STK")
            )[0].contract
            
            bars = self._ib.reqHistoricalData(
                contract, "", f"{days} D", "1 day", "TRADES", False
            )
            
            return [
                OHLCV(
                    ticker=ticker,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    timestamp=bar.date
                )
                for bar in bars
            ]
        except Exception:
            return []
    
    def is_fresh(self, ticker: str, max_age_seconds: int = 60) -> bool:
        """Check if cached quote is fresh."""
        quote = self._cache.get(ticker.upper())
        if quote is None:
            return False
        age = (datetime.now() - quote.timestamp).total_seconds()
        return age < max_age_seconds

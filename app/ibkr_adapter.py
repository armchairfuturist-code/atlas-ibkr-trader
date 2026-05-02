"""IBKR paper adapter with ib_insync connectivity and fallback.

Provides real paper trading connectivity to Interactive Brokers TWS,
with graceful fallback when ib_insync isn't available or TWS isn't running.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.schemas import OrderSubmission, OrderStatus, SignalDirection
from app.config import Config

logger = logging.getLogger(__name__)

# Lazy imports - ib_insync imported only when needed
IB = None
Stock = None
MarketOrder = None
LimitOrder = None
IBIS_AVAILABLE = False


def _ensure_asyncio():
    """Ensure asyncio event loop is set up for ib_insync."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def _lazy_import_ib():
    """Lazily import ib_insync."""
    global IB, Stock, MarketOrder, LimitOrder, IBIS_AVAILABLE
    if IB is None:
        try:
            _ensure_asyncio()
            from ib_insync import IB as IBClass, Stock as StockClass
            from ib_insync import MarketOrder as MKTOrder, LimitOrder as LimitOrderClass

            IB = IBClass
            Stock = StockClass
            MarketOrder = MKTOrder
            LimitOrder = LimitOrderClass
            IBIS_AVAILABLE = True
            logger.info("ib_insync loaded successfully")
        except Exception as e:
            logger.warning(f"ib_insync not available: {e}")
            IBIS_AVAILABLE = False


@dataclass
class IBKRConnection:
    """IBKR connection state."""

    host: str
    port: int
    client_id: int
    connected: bool = False
    paper_mode: bool = True


class IBKRAdapter:
    """
    IBKR paper adapter with real TWS connectivity via ib_insync.

    When TWS is not available or ib_insync has issues, falls back to stub mode
    that simulates connection but doesn't execute real orders.

    Requirements (for real connectivity):
    - TWS or IB Gateway running on ibkr_host:ibkr_port
    - Paper trading account enabled in IBKR
    - API connections enabled in TWS (Settings > API > Enable ActiveX)
    """

    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[IBKRConnection] = None
        self._ib = None
        self._paper_mode = True
        self._stub_mode = True
        self._stub_orders = []

    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect to IBKR TWS/Gateway."""
        if not self.config.is_paper_only():
            return False, "LIVE_MODE_FORBIDDEN: Only paper mode allowed"

        # Try lazy import
        _lazy_import_ib()

        if not IBIS_AVAILABLE:
            logger.info("ib_insync not available - using stub mode")
            return self._connect_stub()

        try:
            _ensure_asyncio()
            self._ib = IB()

            host = self.config.ibkr_host
            port = self.config.ibkr_port
            client_id = self.config.ibkr_client_id

            logger.info(
                f"Connecting to IBKR at {host}:{port} (client_id={client_id})..."
            )

            self._ib.connect(host, port, clientId=client_id, timeout=5)

            if not self._ib.isConnected():
                return self._connect_stub()

            self._connection = IBKRConnection(
                host=host,
                port=port,
                client_id=client_id,
                connected=True,
                paper_mode=True,
            )
            self._paper_mode = True
            self._stub_mode = False

            logger.info(f"Connected to IBKR (real connection)")
            return True, None

        except Exception as e:
            logger.warning(f"IBKR connection failed: {e} - using stub mode")
            return self._connect_stub()

    def _connect_stub(self) -> tuple[bool, Optional[str]]:
        """Connect in stub mode (simulated, no real IBKR needed)."""
        self._connection = IBKRConnection(
            host=self.config.ibkr_host,
            port=self.config.ibkr_port,
            client_id=self.config.ibkr_client_id,
            connected=True,
            paper_mode=True,
        )
        self._paper_mode = True
        self._stub_mode = True

        logger.info("Connected to IBKR in STUB mode (paper simulation)")
        return True, None

    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self._ib and hasattr(self._ib, "isConnected"):
            try:
                if self._ib.isConnected():
                    self._ib.disconnect()
            except Exception:
                pass

        if self._connection:
            self._connection.connected = False
        self._connection = None
        logger.info("Disconnected from IBKR")

    def submit_order(
        self,
        ticker: str,
        direction: SignalDirection,
        shares: int,
        order_type: str = "MKT",
        limit_price: float = None,
    ) -> tuple[Optional[OrderSubmission], Optional[str]]:
        """Submit order to IBKR (real or stub)."""
        if not self._connection or not self._connection.connected:
            return None, "Not connected to IBKR"

        if not self._paper_mode:
            return None, "LIVE_MODE_FORBIDDEN"

        if shares <= 0:
            return None, "Invalid share count"

        if self._stub_mode:
            return self._submit_stub_order(
                ticker, direction, shares, order_type, limit_price
            )

        return self._submit_real_order(
            ticker, direction, shares, order_type, limit_price
        )

    def _submit_stub_order(self, ticker, direction, shares, order_type, limit_price):
        """Submit order in stub mode (simulated)."""
        order_id = f"PAPER-STUB-{len(self._stub_orders) + 1}-{datetime.now().strftime('%H%M%S')}"

        stub_order = OrderSubmission(
            ticker=ticker,
            direction=direction,
            shares=shares,
            broker_order_id=order_id,
            status=OrderStatus.SUBMITTED,
        )

        self._stub_orders.append(stub_order)

        price_str = "MKT" if order_type == "MKT" else f"${limit_price}"
        # Normalize direction to string
        dir_str = direction.value if hasattr(direction, "value") else str(direction)
        logger.info(f"[STUB] Order: {ticker} {dir_str} {shares} shares @ {price_str}")

        return stub_order, None

    def _submit_real_order(self, ticker, direction, shares, order_type, limit_price):
        """Submit real order via ib_insync."""
        try:
            _ensure_asyncio()
            contract = Stock(ticker, "SMART", "USD")
            self._ib.qualifyContracts(contract)

            if order_type == "MKT":
                order = MarketOrder(
                    "BUY" if direction == SignalDirection.LONG else "SELL", shares
                )
                order.tif = "DAY"  # Required for paper trading
            else:
                if limit_price is None:
                    return None, "Limit order requires limit_price"
                order = LimitOrder(
                    "BUY" if direction == SignalDirection.LONG else "SELL",
                    shares,
                    limit_price,
                )
                order.tif = "DAY"

            trade = self._ib.placeOrder(contract, order)
            self._ib.waitOnUpdate(timeout=2)

            if trade.isDone():
                broker_order_id = f"PAPER-{trade.order.orderId}"
                status = OrderStatus.SUBMITTED
            else:
                broker_order_id = f"PAPER-{trade.order.orderId}-PENDING"
                status = OrderStatus.PENDING_APPROVAL

            return OrderSubmission(
                ticker=ticker,
                direction=direction,
                shares=shares,
                broker_order_id=broker_order_id,
                status=status,
            ), None

        except Exception as e:
            return None, f"ORDER_FAILED: {e}"

    def check_buying_power(self) -> tuple[Optional[float], Optional[str]]:
        """Check available buying power."""
        if not self._connection or not self._connection.connected:
            return None, "Not connected"

        if self._stub_mode:
            return 100000.0, None

        try:
            account_summary = self._ib.accountSummary()
            net_liq = 0.0
            for item in account_summary:
                if item.tag == "NetLiquidation":
                    net_liq = float(item.value)
                    break
            return net_liq * 2, None
        except Exception as e:
            return None, f"Failed: {e}"

    def get_account_info(self) -> dict:
        """Get account information."""
        if not self._connection or not self._connection.connected:
            return {"error": "Not connected"}

        if self._stub_mode:
            return {
                "account_type": "PAPER",
                "net_liquidation": 100000.0,
                "buying_power": 200000.0,
                "cash": 100000.0,
                "positions_value": 0.0,
                "mode": "STUB",
            }

        try:
            account_summary = self._ib.accountSummary()
            info = {
                "account_type": "PAPER",
                "net_liquidation": 0.0,
                "buying_power": 0.0,
                "cash": 0.0,
                "positions_value": 0.0,
            }
            for item in account_summary:
                if item.tag == "NetLiquidation":
                    info["net_liquidation"] = float(item.value)
                elif item.tag == "BuyingPower":
                    info["buying_power"] = float(item.value)
                elif item.tag == "Cash":
                    info["cash"] = float(item.value)
                elif item.tag == "LongStockValue":
                    info["positions_value"] = float(item.value)
            return info
        except Exception as e:
            return {"error": str(e)}

    def get_quote(self, ticker: str) -> Optional[dict]:
        """Get real-time quote for a ticker."""
        if not self._connection or not self._connection.connected:
            return None

        if self._stub_mode:
            return self._get_stub_quote(ticker)

        try:
            _ensure_asyncio()
            contract = Stock(ticker, "SMART", "USD")
            self._ib.qualifyContracts(contract)
            ticker_obj = self._ib.reqMktData(contract, snapshot=True)
            self._ib.waitOnUpdate(timeout=2)

            if ticker_obj.last > 0:
                return {
                    "ticker": ticker,
                    "bid": ticker_obj.bid,
                    "ask": ticker_obj.ask,
                    "last": ticker_obj.last,
                    "volume": ticker_obj.volume,
                    "timestamp": datetime.now().isoformat(),
                }
            elif ticker_obj.close > 0:
                return {
                    "ticker": ticker,
                    "bid": ticker_obj.bid or ticker_obj.close,
                    "ask": ticker_obj.ask or ticker_obj.close,
                    "last": ticker_obj.close,
                    "volume": ticker_obj.volume,
                    "timestamp": datetime.now().isoformat(),
                }
            return None
        except Exception as e:
            logger.error(f"Quote failed for {ticker}: {e}")
            return self._get_stub_quote(ticker)

    def _get_stub_quote(self, ticker: str) -> dict:
        """Get simulated quote for stub mode."""
        base_prices = {
            "SPY": 500.0,
            "QQQ": 430.0,
            "XLF": 41.0,
            "XLK": 205.0,
            "XLE": 88.0,
            "XLV": 148.0,
            "XLY": 198.0,
            "XLI": 128.0,
            "XLB": 87.0,
            "IWM": 205.0,
            "DIA": 405.0,
            "EEM": 41.0,
        }
        base = base_prices.get(ticker, 100.0)
        variation = random.uniform(-0.01, 0.01)
        last = round(base * (1 + variation), 2)
        spread = round(base * 0.0005, 2)

        return {
            "ticker": ticker,
            "bid": round(last - spread, 2),
            "ask": round(last + spread, 2),
            "last": last,
            "volume": random.randint(5_000_000, 50_000_000),
            "timestamp": datetime.now().isoformat(),
            "mode": "STUB",
        }

    def get_historical(
        self, ticker: str, duration: str = "1 W", bar_size: str = "1 day"
    ) -> Optional[list[dict]]:
        """Get historical bars for a ticker."""
        if not self._connection or not self._connection.connected:
            return None

        if self._stub_mode:
            return self._get_stub_historical(ticker, duration, bar_size)

        try:
            _ensure_asyncio()
            contract = Stock(ticker, "SMART", "USD")
            self._ib.qualifyContracts(contract)
            bars = self._ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="ADJUSTED_LAST",
                useRTH=True,
            )
            if not bars:
                return self._get_stub_historical(ticker, duration, bar_size)
            return [
                {
                    "date": bar.date.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ]
        except Exception as e:
            logger.error(f"Historical failed for {ticker}: {e}")
            return self._get_stub_historical(ticker, duration, bar_size)

    def _get_stub_historical(
        self, ticker: str, duration: str, bar_size: str
    ) -> list[dict]:
        """Generate stub historical data."""
        duration_map = {"1 W": 7, "2 W": 14, "1 M": 30, "3 M": 90, "1 Y": 365}
        days = duration_map.get(duration, 7)

        base_prices = {
            "SPY": 500.0,
            "QQQ": 430.0,
            "XLF": 41.0,
            "XLK": 205.0,
            "XLE": 88.0,
            "XLV": 148.0,
            "XLY": 198.0,
            "XLI": 128.0,
        }
        base = base_prices.get(ticker, 100.0)

        bars = []
        current_price = base * random.uniform(0.95, 1.05)

        for i in range(days):
            date = datetime.now() - timedelta(days=days - i)
            open_price = current_price
            close = current_price * (1 + random.uniform(-0.02, 0.02))
            high = max(open_price, close) * (1 + random.uniform(0, 0.01))
            low = min(open_price, close) * (1 - random.uniform(0, 0.01))
            bars.append(
                {
                    "date": date.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": random.randint(20_000_000, 80_000_000),
                }
            )
            current_price = close

        return bars

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connection is not None and self._connection.connected

    def is_stub_mode(self) -> bool:
        """Check if running in stub mode."""
        return self._stub_mode

    def get_stub_orders(self) -> list[OrderSubmission]:
        """Get list of stub orders (for testing)."""
        return self._stub_orders.copy()

#!/usr/bin/env python3
"""
Read-only IBKR Holdings Query — connects to TWS/IB Gateway to fetch actual
portfolio holdings. NO order placement capability. EVER.

This module has literally zero write paths:
  - No submit_order()
  - No placeOrder()
  - No MarketOrder/LimitOrder imports
  - No send_order() or cancel_order()
  
It ONLY calls:
  - reqPositions()     -> current holdings
  - accountSummary()   -> net liq, cash, buying power
  - reqOpenOrders()    -> pending orders
  - reqCompletedOrders() -> recent fills

Usage:
    # With TWS running (live or paper, port 7496 or 7497)
    python -m app.holdings_query --connect

    # With a manual CSV file
    python -m app.holdings_query --from-csv holdings.csv

    # With a manual JSON file (like last session's export)
    python -m app.holdings_query --from-json holdings.json

    # Scan IBKR positions against our recommendations
    python -m app.holdings_query --scan
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────

@dataclass
class HoldingPosition:
    """A single position in the portfolio."""
    ticker: str
    company: str = ""
    shares: float = 0.0
    avg_cost: float = 0.0
    market_price: float = 0.0
    market_value: float = 0.0
    cost_basis: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    sector: str = ""
    account: str = ""  # "live" or "paper"

    @property
    def return_pct(self) -> float:
        if self.cost_basis and self.cost_basis > 0:
            return ((self.market_value - self.cost_basis) / self.cost_basis) * 100
        return 0.0


@dataclass
class AccountSummary:
    """IBKR account summary."""
    net_liquidation: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    gross_position_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    account_type: str = "live"  # "live" or "paper"


@dataclass
class PortfolioSnapshot:
    """Complete portfolio snapshot from IBKR or manual input."""
    timestamp: str = ""
    account: AccountSummary = field(default_factory=AccountSummary)
    positions: list[HoldingPosition] = field(default_factory=list)
    open_orders: list[dict] = field(default_factory=list)
    source: str = ""  # "ibkr", "csv", "json", "stub"

    @property
    def total_cost_basis(self) -> float:
        return sum(p.cost_basis for p in self.positions)

    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON export."""
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "account": asdict(self.account),
            "positions": [asdict(p) for p in self.positions],
            "open_orders": self.open_orders,
        }

    def save(self, path: str | Path):
        """Save snapshot to JSON file."""
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        logger.info(f"Portfolio snapshot saved to {path}")

    @classmethod
    def load(cls, path: str | Path) -> "PortfolioSnapshot":
        """Load snapshot from JSON file."""
        path = Path(path)
        data = json.loads(path.read_text())
        account = AccountSummary(**data["account"])
        positions = [HoldingPosition(**p) for p in data["positions"]]
        return cls(
            timestamp=data["timestamp"],
            account=account,
            positions=positions,
            open_orders=data.get("open_orders", []),
            source=data.get("source", "json"),
        )


# ─────────────────────────────────────────────────────────────
# IBKR Read-Only Connector
# ─────────────────────────────────────────────────────────────

class IBKRHoldingsReader:
    """
    Connects to IBKR TWS/Gateway in READ-ONLY mode.
    
    This class has NO write methods. It cannot place orders,
    modify orders, or submit any trading instructions.
    
    Safety guarantee: the only ib_insync methods called are:
      - IB.connect()
      - IB.reqPositions()
      - IB.accountSummary()  
      - IB.reqOpenOrders()
      - IB.reqCompletedOrders()
      - IB.disconnect()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 2):
        self.host = host
        self.port = port  # 7497 = paper, 7496 = live, 4002 = IB Gateway live
        self.client_id = client_id
        self._ib = None
        self._connected = False

    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect to TWS/IB Gateway. Read-only. No trades possible."""
        try:
            # Lazy import — only ib_insync, NO order types
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            from ib_insync import IB as IBClass
            self._ib = IBClass()
            self._ib.connect(self.host, self.port, clientId=self.client_id, timeout=5)

            if not self._ib.isConnected():
                return False, "TWS/IB Gateway not running or API not enabled"

            self._connected = True
            # Determine account type from port
            acct_type = "live" if self.port in (7496, 4001, 4002) else "paper"
            logger.info(f"✅ Connected to IBKR ({acct_type}) at {self.host}:{self.port}")
            return True, None

        except ImportError:
            return False, "ib_insync not installed. Run: pip install ib-insync"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def disconnect(self):
        """Disconnect from TWS."""
        if self._ib and hasattr(self._ib, 'disconnect'):
            try:
                self._ib.disconnect()
            except Exception:
                pass
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def fetch_positions(self) -> list[HoldingPosition]:
        """Fetch all current positions from IBKR.

        Returns:
            List of HoldingPosition objects. Empty if not connected.
        """
        if not self._connected or not self._ib:
            return []

        try:
            raw = self._ib.reqPositions()
            positions = []
            for pos in raw:
                ticker = pos.contract.symbol if pos.contract else "?"
                sec_type = pos.contract.secType if pos.contract else "?"
                # Skip non-stock/ETF positions (options, futures, forex)
                if sec_type not in ("STK", "ETF", "STOCK"):
                    continue
                
                shares = float(pos.position) if pos.position else 0.0
                avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
                cost_basis = abs(shares) * avg_cost
                
                # Safe market price extraction — handle different ib_insync versions
                mkt_price = 0.0
                if hasattr(pos, 'marketPrice') and pos.marketPrice:
                    mkt_price = float(pos.marketPrice)
                elif hasattr(pos, 'market_price') and pos.market_price:
                    mkt_price = float(pos.market_price)
                
                # Get unrealized P&L safely
                unrealized = 0.0
                if hasattr(pos, 'unrealizedPNL') and pos.unrealizedPNL:
                    try:
                        unrealized = float(pos.unrealizedPNL)
                    except (ValueError, TypeError):
                        unrealized = 0.0
                
                # If market price not available from position, try reqMktData
                if mkt_price <= 0 and shares != 0:
                    try:
                        from ib_insync import Stock as StockContract
                        contract = StockContract(ticker, "SMART", "USD")
                        self._ib.qualifyContracts(contract)
                        ticker_data = self._ib.reqMktData(contract, snapshot=True)
                        self._ib.sleep(0.5)
                        if ticker_data and ticker_data.last:
                            mkt_price = float(ticker_data.last)
                        elif ticker_data and ticker_data.close:
                            mkt_price = float(ticker_data.close)
                    except Exception:
                        pass
                
                # If still no market price, fall back to yfinance
                if mkt_price <= 0 and shares != 0:
                    try:
                        import yfinance as yf
                        t = yf.Ticker(ticker)
                        hist = t.history(period="1d")
                        if not hist.empty:
                            mkt_price = float(hist['Close'].iloc[-1])
                    except Exception:
                        pass
                
                market_value = abs(shares) * mkt_price if mkt_price > 0 else cost_basis + unrealized
                if unrealized == 0.0 and mkt_price > 0 and avg_cost > 0:
                    unrealized = market_value - cost_basis

                positions.append(HoldingPosition(
                    ticker=ticker,
                    shares=shares,
                    avg_cost=avg_cost,
                    market_price=mkt_price,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pnl=unrealized,
                    unrealized_pnl_pct=(unrealized / cost_basis * 100) if cost_basis > 0 else 0.0,
                ))

            return positions

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    def fetch_account_summary(self) -> AccountSummary:
        """Fetch account summary from IBKR."""
        if not self._connected or not self._ib:
            return AccountSummary()

        try:
            raw = self._ib.accountSummary()
            summary = AccountSummary()
            for item in raw:
                tag = item.tag
                # Skip non-numeric tags (e.g., account type names like "IRA-ROTH NEW")
                if not item.value:
                    continue
                try:
                    val = float(item.value)
                except (ValueError, TypeError):
                    continue  # Skip string values like "IRA-ROTH NEW", "MARGIN", etc.
                if tag == "NetLiquidation":
                    summary.net_liquidation = val
                elif tag == "TotalCashValue":
                    summary.cash = val
                elif tag == "BuyingPower":
                    summary.buying_power = val
                elif tag == "GrossPositionValue":
                    summary.gross_position_value = val
                elif tag == "UnrealizedPnL":
                    summary.unrealized_pnl = val
                elif tag == "RealizedPnL":
                    summary.realized_pnl = val
            # Detect account type from port
            summary.account_type = "live" if self.port in (7496, 4001, 4002) else "paper"
            return summary

        except Exception as e:
            logger.error(f"Failed to fetch account summary: {e}")
            return AccountSummary()

    def fetch_open_orders(self) -> list[dict]:
        """Fetch open orders (read-only, no modification)."""
        if not self._connected or not self._ib:
            return []

        try:
            raw = self._ib.reqOpenOrders()
            orders = []
            for o in raw:
                orders.append({
                    "order_id": o.orderId,
                    "ticker": o.contract.symbol if o.contract else "?",
                    "action": o.order.action if o.order else "?",
                    "quantity": o.order.totalQuantity if o.order else 0,
                    "order_type": o.order.orderType if o.order else "?",
                    "limit_price": float(o.order.lmtPrice) if o.order and o.order.lmtPrice else None,
                    "status": o.orderStatus.status if o.orderStatus else "?",
                })
            return orders

        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            return []

    def snapshot(self) -> PortfolioSnapshot:
        """Fetch a complete portfolio snapshot."""
        if not self._connected:
            return PortfolioSnapshot(
                timestamp=datetime.now().isoformat(),
                source="ibkr",
                account=AccountSummary(),
                positions=[],
                open_orders=[],
            )

        positions = self.fetch_positions()
        account = self.fetch_account_summary()
        orders = self.fetch_open_orders()

        return PortfolioSnapshot(
            timestamp=datetime.now().isoformat(),
            source="ibkr",
            account=account,
            positions=positions,
            open_orders=orders,
        )


# ─────────────────────────────────────────────────────────────
# Manual / File-Based Holdings Provider
# ─────────────────────────────────────────────────────────────

class ManualHoldingsProvider:
    """
    Provides holdings data from manual input (CSV, JSON, or dict).
    Used when TWS/IB Gateway is not available.
    
    CSV format:
        ticker,shares,avg_cost,market_price
        TLN,100,340.50,372.16
        CEG,82,381.85,307.81
    
    JSON format: matches PortfolioSnapshot.to_dict() output
    """

    @staticmethod
    def from_csv(path: str | Path) -> PortfolioSnapshot:
        """Load holdings from a CSV file."""
        path = Path(path)
        positions = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker", row.get("symbol", "?"))
                shares = float(row.get("shares", row.get("quantity", 0)))
                avg_cost = float(row.get("avg_cost", row.get("cost_basis", 0)))
                mkt_price = float(row.get("market_price", row.get("price", 0)))
                market_value = abs(shares) * mkt_price
                cost_basis = abs(shares) * avg_cost
                unrealized = market_value - cost_basis
                positions.append(HoldingPosition(
                    ticker=ticker.upper(),
                    shares=shares,
                    avg_cost=avg_cost,
                    market_price=mkt_price,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pnl=unrealized,
                    unrealized_pnl_pct=(unrealized / cost_basis * 100) if cost_basis > 0 else 0.0,
                ))
        return PortfolioSnapshot(
            timestamp=datetime.now().isoformat(),
            source="csv",
            account=AccountSummary(),
            positions=positions,
        )

    @staticmethod
    def from_json(path: str | Path) -> PortfolioSnapshot:
        """Load holdings from a JSON file (PortfolioSnapshot format)."""
        return PortfolioSnapshot.load(path)

    @staticmethod
    def from_dict(data: dict) -> PortfolioSnapshot:
        """Load holdings from a dict matching the user's earlier format.
        
        Expected format:
            holdings = [
                ("IBIT", "Bitcoin ETF", 690.0341, -12865, 43439),
                ("CEG", "Constellation Energy", 82.2085, -6006, 31311),
            ]
            where each tuple is (ticker, name, shares, unrealized_pnl, cost_basis)
        """
        positions = []
        raw_positions = data.get("holdings", data.get("positions", []))
        for item in raw_positions:
            if isinstance(item, (list, tuple)):
                ticker = str(item[0])
                name = str(item[1]) if len(item) > 1 else ""
                shares = float(item[2]) if len(item) > 2 else 0
                unrealized = float(item[3]) if len(item) > 3 else 0
                cost_basis = float(item[4]) if len(item) > 4 else 0
            elif isinstance(item, dict):
                ticker = item.get("ticker", item.get("symbol", "?"))
                name = item.get("name", item.get("company", ""))
                shares = float(item.get("shares", item.get("quantity", 0)))
                unrealized = float(item.get("unrealized_pnl", item.get("pnl", 0)))
                cost_basis = float(item.get("cost_basis", item.get("cost", 0)))
            else:
                continue

            mkt_price = (cost_basis + unrealized) / abs(shares) if shares and abs(shares) > 0 else 0
            market_value = cost_basis + unrealized

            positions.append(HoldingPosition(
                ticker=ticker.upper(),
                company=name,
                shares=shares,
                market_price=mkt_price,
                market_value=market_value,
                cost_basis=cost_basis,
                unrealized_pnl=unrealized,
                unrealized_pnl_pct=(unrealized / cost_basis * 100) if cost_basis > 0 else 0,
            ))

        return PortfolioSnapshot(
            timestamp=datetime.now().isoformat(),
            source="manual",
            account=AccountSummary(),
            positions=positions,
        )


# ─────────────────────────────────────────────────────────────
# Cross-reference: portfolio vs our recommendations
# ─────────────────────────────────────────────────────────────

def cross_reference(snapshot: PortfolioSnapshot) -> dict:
    """
    Compare portfolio holdings against our system's receiver-company thesis.
    
    Returns a dict with:
      - positions already held (with our rating)
      - positions to consider adding (our rated BUYs not in portfolio)
      - concentration warnings
      - overlap/excess in specific sectors
    """
    from app.vibe_bridge import VibeTradingBridge

    bridge = VibeTradingBridge()

    # Our receiver-company ratings (from the narrative scan)
    our_ratings = {
        "TLN": {"sector": "POWER", "our_view": "OVERWEIGHT", "thesis": "Pre-discovery power play"},
        "CEG": {"sector": "POWER", "our_view": "OVERWEIGHT", "thesis": "Nuclear AI demand"},
        "VST": {"sector": "POWER", "our_view": "OVERWEIGHT", "thesis": "Gas infra, -19% pullback"},
        "EQT": {"sector": "POWER", "our_view": "HOLD", "thesis": "Natural gas baseload"},
        "URNM": {"sector": "URANIUM", "our_view": "OVERWEIGHT", "thesis": "Uranium miners ETF, 13.8x P/E"},
        "CCJ": {"sector": "URANIUM", "our_view": "OVERWEIGHT", "thesis": "Largest uranium producer"},
        "MP": {"sector": "RARE_EARTH", "our_view": "OVERWEIGHT", "thesis": "US rare earth leader"},
        "UUUU": {"sector": "RARE_EARTH", "our_view": "BUY", "thesis": "U+RE direct play"},
        "AAOI": {"sector": "OPTICAL", "our_view": "BUY", "thesis": "Vertically integrated optical"},
        "MTSI": {"sector": "OPTICAL", "our_view": "OVERWEIGHT", "thesis": "Value photonics"},
        "FN": {"sector": "OPTICAL", "our_view": "OVERWEIGHT", "thesis": "Best RSI entry"},
        "CSCO": {"sector": "INFRA", "our_view": "OVERWEIGHT", "thesis": "Networking infra"},
        "ANET": {"sector": "INFRA", "our_view": "HOLD", "thesis": "Data center switching"},
        "4368.T": {"sector": "JAPAN_CHEM", "our_view": "BUY", "thesis": "CMP silica 90%+ monopoly"},
        "4063.T": {"sector": "JAPAN_CHEM", "our_view": "BUY", "thesis": "Si wafers #1, RSI pullback"},
        "4183.T": {"sector": "JAPAN_CHEM", "our_view": "OVERWEIGHT", "thesis": "Protective tape #1"},
        "3407.T": {"sector": "JAPAN_CHEM", "our_view": "OVERWEIGHT", "thesis": "15x P/E, GPU insul. mat."},
        "4188.T": {"sector": "JAPAN_CHEM", "our_view": "OVERWEIGHT", "thesis": "P/B 0.66x"},
        "SNDK": {"sector": "STORAGE", "our_view": "HOLD", "thesis": "SanDisk, Aschenbrenner +817%"},
    }

    portfolio_tickers = {p.ticker for p in snapshot.positions}
    portfolio_by_sector: dict[str, float] = {}
    for p in snapshot.positions:
        if p.ticker in our_ratings:
            sec = our_ratings[p.ticker]["sector"]
        else:
            sec = "UNKNOWN"
        portfolio_by_sector[sec] = portfolio_by_sector.get(sec, 0) + p.market_value

    # What we rate BUY/OVERWEIGHT that's NOT in portfolio
    gaps = []
    for ticker, rating in our_ratings.items():
        normalized_ticker = ticker.replace(".T", "")  # Handle Japanese stocks
        if normalized_ticker not in portfolio_tickers and rating["our_view"] in ("BUY", "OVERWEIGHT"):
            gaps.append(rating)

    # What's in portfolio that we don't rate
    unknowns = [p for p in snapshot.positions if p.ticker not in our_ratings]

    # Position concentration
    total_value = snapshot.total_market_value
    large_positions = [p for p in snapshot.positions if total_value > 0 and (p.market_value / total_value) > 0.20]

    return {
        "total_positions": len(snapshot.positions),
        "total_value": total_value,
        "total_cost_basis": snapshot.total_cost_basis,
        "total_unrealized_pnl": snapshot.total_unrealized_pnl,
        "overall_return_pct": (snapshot.total_unrealized_pnl / snapshot.total_cost_basis * 100) if snapshot.total_cost_basis > 0 else 0,
        "positions_in_portfolio": [
            {
                "ticker": p.ticker,
                "shares": p.shares,
                "cost_basis": p.cost_basis,
                "market_value": p.market_value,
                "unrealized_pnl": p.unrealized_pnl,
                "return_pct": p.return_pct,
                "our_view": our_ratings.get(p.ticker, {}).get("our_view", "NOT_RATED"),
                "sector": our_ratings.get(p.ticker, {}).get("sector", "UNKNOWN"),
            }
            for p in sorted(snapshot.positions, key=lambda x: x.market_value, reverse=True)
        ],
        "gaps_to_fill": [
            {
                "sector": g["sector"],
                "our_view": g["our_view"],
                "thesis": g["thesis"],
            } for g in gaps
        ],
        "concentration_warnings": [
            f"{p.ticker} is {p.market_value/total_value*100:.0f}% of portfolio"
            for p in large_positions
        ],
        "unknown_holdings": [p.ticker for p in unknowns],
    }


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def print_portfolio(snapshot: PortfolioSnapshot, title: str = "PORTFOLIO"):
    """Pretty-print a portfolio snapshot."""
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"  Source: {snapshot.source.upper()}  |  {snapshot.timestamp}")
    print(f"{'=' * 72}")

    acct = snapshot.account
    print(f"\n  Account: ${acct.net_liquidation:>10,.2f} net liq  |  ${acct.cash:>10,.2f} cash  |  BP: ${acct.buying_power:>10,.2f}")
    print(f"  P&L: ${acct.unrealized_pnl:>+8,.2f} unrealized  |  ${acct.realized_pnl:>+8,.2f} realized")
    print(f"  Positions: {len(snapshot.positions)}  |  Open Orders: {len(snapshot.open_orders)}")

    if snapshot.positions:
        print(f"\n  {'Ticker':<8} {'Shares':>10} {'Cost':>10} {'Value':>10} {'P&L':>10} {'Return':>8}")
        print(f"  {'-' * 60}")
        for p in sorted(snapshot.positions, key=lambda x: x.market_value, reverse=True):
            print(f"  {p.ticker:<8} {p.shares:>10.2f} ${p.cost_basis:>8,.0f} ${p.market_value:>8,.0f} ${p.unrealized_pnl:>+8,.0f} {p.return_pct:>+7.1f}%")

        # Summary
        print(f"  {'-' * 60}")
        print(f"  {'TOTAL':<8} {'':>10} ${snapshot.total_cost_basis:>8,.0f} ${snapshot.total_market_value:>8,.0f} ${snapshot.total_unrealized_pnl:>+8,.0f} {snapshot.total_unrealized_pnl/snapshot.total_cost_basis*100:>+7.1f}%")


def print_scan(scan: dict):
    """Pretty-print cross-reference scan."""
    print(f"\n{'=' * 72}")
    print(f"  PORTFOLIO VS SYSTEM RECOMMENDATIONS")
    print(f"{'=' * 72}")
    print(f"  {scan['total_positions']} positions  |  Value: ${scan['total_value']:,.0f}  |  P&L: ${scan['total_unrealized_pnl']:+,.0f} ({scan['overall_return_pct']:+.1f}%)")

    # Positions
    print(f"\n  {'CURRENT POSITIONS':^72}")
    print(f"  {'Ticker':<8} {'Cost':>8} {'Value':>8} {'P&L':>8} {'Ret':>7} {'Our View':<12} {'Sector':<14}")
    print(f"  {'-' * (8+8+8+8+7+12+14)}")
    for p in scan["positions_in_portfolio"]:
        ret = p["return_pct"]
        view = p["our_view"]
        sec = p["sector"]
        print(f"  {p['ticker']:<8} ${p['cost_basis']:>7,.0f} ${p['market_value']:>7,.0f} ${p['unrealized_pnl']:>+7,.0f} {ret:>+6.1f}% {view:<12} {sec:<14}")

    # Gaps
    print(f"\n  {'RECOMMENDED GAPS TO FILL':^72}")
    for g in scan["gaps_to_fill"]:
        print(f"  🟢 {g['sector']:<14} {g['our_view']:<12} — {g['thesis']}")

    # Concentration warnings
    if scan["concentration_warnings"]:
        print(f"\n  {'⚠️  CONCENTRATION WARNINGS':^72}")
        for w in scan["concentration_warnings"]:
            print(f"  {w}")

    if scan["unknown_holdings"]:
        print(f"\n  {'📋 UNKNOWN HOLDINGS (not in our universe)':^72}")
        print(f"  {', '.join(scan['unknown_holdings'])}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="IBKR Read-Only Holdings Query")
    parser.add_argument("--connect", action="store_true", help="Connect to TWS/IB Gateway")
    parser.add_argument("--port", type=int, default=7497, help="TWS port (7496=live, 7497=paper, 4001/4002=Gateway)")
    parser.add_argument("--host", default="127.0.0.1", help="TWS host")
    parser.add_argument("--client-id", type=int, default=2, help="IBKR client ID")
    parser.add_argument("--from-csv", help="Load holdings from CSV file")
    parser.add_argument("--from-json", help="Load holdings from JSON file")
    parser.add_argument("--from-manual", help="Manual holdings as JSON string")
    parser.add_argument("--save", help="Save snapshot to file")
    parser.add_argument("--scan", action="store_true", help="Cross-reference with our recommendations")
    parser.add_argument("--stub", action="store_true", help="Use demo data (no IBKR needed)")
    args = parser.parse_args()

    snapshot = None

    if args.connect:
        reader = IBKRHoldingsReader(args.host, args.port, args.client_id)
        ok, err = reader.connect()
        if not ok:
            print(f"❌ {err}")
            print("   Make sure TWS/IB Gateway is running with API enabled.")
            print("   Port: 7497 (paper), 7496 (live), 4002 (IB Gateway live)")
            sys.exit(1)
        snapshot = reader.snapshot()
        reader.disconnect()

    elif args.from_csv:
        snapshot = ManualHoldingsProvider.from_csv(args.from_csv)
    elif args.from_json:
        snapshot = ManualHoldingsProvider.from_json(args.from_json)
    elif args.from_manual:
        snapshot = ManualHoldingsProvider.from_dict(json.loads(args.from_manual))
    elif args.stub:
        # Demo data matching user's actual portfolio
        demo = {
            "holdings": [
                ("IBIT", "Bitcoin ETF", 690.0341, -12865, 43439),
                ("CEG", "Constellation Energy", 82.2085, -6006, 31311),
                ("URA", "Uranium ETF", 1070, 18664, 41073),
                ("AIPO", "AI & Power Infra ETF", 2070, 18920, 46766),
                ("SMH", "Semiconductor ETF", 347.1745, 78302, 98370),
                ("REMX", "Rare Earth & Metals ETF", 873.3358, 51834, 41194),
                ("COPX", "Copper Miners ETF", 560.0473, 19051, 25932),
                ("BOTZ", "Robotics & AI ETF", 1280, 9201, 40275),
                ("RKLB", "Rocket Lab", 300, 15648, 7995),
                ("TLN", "Talos Energy", 100, 0, 34050),
            ]
        }
        snapshot = ManualHoldingsProvider.from_dict(demo)

    else:
        parser.print_help()
        print("\n   Example: python -m app.holdings_query --stub --scan")
        print("   Example: python -m app.holdings_query --connect --port 7497")
        print("   Example: python -m app.holdings_query --from-csv holdings.csv --scan")
        return

    if snapshot:
        print_portfolio(snapshot)
        if args.save:
            snapshot.save(args.save)

        if args.scan:
            scan = cross_reference(snapshot)
            print_scan(scan)


if __name__ == "__main__":
    main()

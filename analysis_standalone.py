#!/usr/bin/env python3
"""Standalone trading analysis - no TWS required.

Uses yfinance for market data, works completely offline.

Usage:
    python analysis_standalone.py --ticker SPY --duration "3 M"
    python analysis_standalone.py --signal
    python analysis_standalone.py --weekly-pay
    python analysis_standalone.py --income
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.debate_orchestrator import DebateOrchestrator
from app.memory.financial_memory import FinancialSituationMemory
from app.memory.reflection import reflect_and_remember, get_memory


def load_memory() -> FinancialSituationMemory:
    """Load persistent memory from disk."""
    mem = FinancialSituationMemory()
    mem_file = os.path.join(os.path.dirname(__file__), "memory.json")

    if os.path.exists(mem_file):
        try:
            with open(mem_file) as f:
                data = json.load(f)
                # Re-populate memory
                for entry in data.get("entries", []):
                    mem.add_memory(
                        situation=entry["situation"],
                        outcome=entry["outcome"],
                        lesson=entry["lesson"],
                        tags=entry.get("tags", []),
                    )
            print(f"Loaded {len(mem)} memories from disk")
        except Exception as e:
            print(f"Warning: Could not load memory: {e}")

    return mem


def save_memory(mem: FinancialSituationMemory):
    """Save memory to disk."""
    mem_file = os.path.join(os.path.dirname(__file__), "memory.json")

    try:
        entries = []
        for entry in mem.entries:
            entries.append(
                {
                    "situation": entry.situation,
                    "outcome": entry.outcome,
                    "lesson": entry.lesson,
                    "tags": entry.tags,
                    "timestamp": entry.timestamp.isoformat(),
                }
            )

        with open(mem_file, "w") as f:
            json.dump(
                {"entries": entries, "saved_at": datetime.now().isoformat()},
                f,
                indent=2,
            )

        print(f"Saved {len(entries)} memories to disk")
    except Exception as e:
        print(f"Warning: Could not save memory: {e}")


def get_market_data():
    """Get market data provider that works without TWS."""
    from app.data.market_data import YFinanceProvider

    return YFinanceProvider()


def analyze_ticker(ticker: str, provider=None) -> dict:
    """Run full analysis on a ticker."""
    if provider is None:
        provider = get_market_data()

    print(f"\n{'=' * 60}")
    print(f"ANALYSIS: {ticker}")
    print(f"{'=' * 60}")

    # Get data
    quote = provider.get_quote(ticker)
    hist_1m = provider.get_historical(ticker, "1 M")
    hist_3m = provider.get_historical(ticker, "3 M")
    info = provider.get_info(ticker)

    if not hist_1m and not quote:
        print(f"Could not fetch data for {ticker}")
        return None

    price = quote["last"] if quote else hist_1m[-1]["close"]

    print(f"\nPrice: ${price:.2f}" if price else "Price: N/A")

    if info:
        pe = info.get("trailingPE", "N/A")
        dividend = info.get("dividendYield", 0)
        if dividend and dividend > 0:
            print(f"P/E: {pe} | Dividend Yield: {dividend * 100:.2f}%")
        elif pe and pe != "N/A":
            print(f"P/E: {pe}")

    # Calculate returns
    if hist_1m and len(hist_1m) >= 2:
        ret_1m = (
            (hist_1m[-1]["close"] - hist_1m[0]["close"]) / hist_1m[0]["close"] * 100
        )
        print(f"1M Return: {ret_1m:+.2f}%")

    if hist_3m and len(hist_3m) >= 2:
        ret_3m = (
            (hist_3m[-1]["close"] - hist_3m[0]["close"]) / hist_3m[0]["close"] * 100
        )
        vol = calculate_volatility(hist_3m)
        print(f"3M Return: {ret_3m:+.2f}% | Volatility: {vol:.1f}%")

    # Run debate
    print(f"\n--- Multi-Agent Debate ---")
    debate = DebateOrchestrator(max_rounds=2)

    data = {
        "price_history": [h["close"] for h in hist_3m] if hist_3m else [price],
        "volume": quote["volume"] if quote else 20000000,
        "indicators": {"rsi": 50, "macd": {"histogram": 0.0}},
        "fundamentals": {
            "pe_ratio": info.get("trailingPE", 20) if info else 20,
            "earnings_yield": info.get("earningsYield", 0.05) if info else 0.05,
        },
    }

    plan = debate.run_debate(ticker, data)

    print(f"Rating: {plan.rating.value}")
    print(f"Conviction: {plan.conviction}")
    print(f"Bull/Bear: {plan.bull_contribution:.0%}/{plan.bear_contribution:.0%}")
    print(f"Thesis: {plan.thesis}")

    # Check memory for similar situations
    print(f"\n--- Similar Past Experiences ---")
    mem = load_memory()
    similar = mem.get_memories(f"{ticker}", n=3)
    if similar:
        for s in similar:
            print(f"  {s.outcome} → {s.lesson[:60]}...")
    else:
        print("  No prior experiences on record")

    return {
        "ticker": ticker,
        "price": price,
        "rating": plan.rating.value,
        "conviction": plan.conviction,
        "bull_contribution": plan.bull_contribution,
        "bear_contribution": plan.bear_contribution,
        "thesis": plan.thesis,
    }


def calculate_volatility(bars: list) -> float:
    """Calculate volatility from price bars."""
    if len(bars) < 2:
        return 0

    returns = [
        (bars[i]["close"] - bars[i - 1]["close"]) / bars[i - 1]["close"] * 100
        for i in range(1, len(bars))
    ]

    if not returns:
        return 0

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    return variance**0.5


def analyze_income_etfs():
    """Analyze income ETF candidates."""
    provider = get_market_data()

    income_etfs = [
        ("JEPI", "JPMorgan Equity Premium Income"),
        ("JEPQ", "JPMorgan Nasdaq Equity Premium"),
        ("SCHD", "Schwab Dividend Equity"),
        ("VYM", "Vanguard High Dividend Yield"),
        ("HDV", "iShares High Dividend"),
        ("QYLD", "Global X Nasdaq Covered Call"),
        ("XYLD", "Global X S&P Covered Call"),
        ("DGRO", "iShares Dividend Growth"),
    ]

    print("\n" + "=" * 70)
    print("INCOME ETF ANALYSIS (No TWS Required)")
    print("=" * 70)

    results = []

    for ticker, name in income_etfs:
        hist_1m = provider.get_historical(ticker, "1 M")
        hist_3m = provider.get_historical(ticker, "3 M")
        quote = provider.get_quote(ticker)

        price = quote["last"] if quote else 0

        if not hist_1m and not price:
            continue

        ret_1m = (
            (hist_1m[-1]["close"] - hist_1m[0]["close"]) / hist_1m[0]["close"] * 100
            if hist_1m
            else 0
        )
        ret_3m = (
            (hist_3m[-1]["close"] - hist_3m[0]["close"]) / hist_3m[0]["close"] * 100
            if hist_3m
            else 0
        )
        vol = calculate_volatility(hist_3m) if hist_3m else 0

        # Run debate
        debate = DebateOrchestrator(max_rounds=2)
        data = {
            "price_history": [h["close"] for h in hist_3m] if hist_3m else [price],
            "volume": quote["volume"] if quote else 10000000,
            "indicators": {"rsi": 50, "macd": {"histogram": 0}},
            "fundamentals": {"pe_ratio": 18, "earnings_yield": 0.05},
        }
        plan = debate.run_debate(ticker, data)

        sharpe = ret_3m / vol if vol > 0 else 0

        results.append(
            {
                "ticker": ticker,
                "name": name,
                "price": price,
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "vol": vol,
                "sharpe": sharpe,
                "rating": plan.rating.value,
                "conviction": plan.conviction,
            }
        )

    # Sort by Sharpe
    results.sort(key=lambda x: x["sharpe"], reverse=True)

    print(
        f"\n{'TICKER':<8} {'PRICE':>8} {'1M':>8} {'3M':>8} {'VOL':>8} {'SHARPE':>8} {'RATING':<12} {'CONV':>4}"
    )
    print("-" * 80)

    for r in results:
        print(
            f"{r['ticker']:<8} ${r['price']:>7.2f} {r['ret_1m']:>+7.2f}% {r['ret_3m']:>+7.2f}% {r['vol']:>7.1f}% {r['sharpe']:>+7.2f} {r['rating']:<12} {r['conviction']:>4}"
        )

    return results


def analyze_weekly_payers():
    """Analyze weekly paying ETFs."""
    provider = get_market_data()

    weekly_payers = [
        ("QYLD", "Nasdaq 100 Covered Call"),
        ("XYLD", "S&P 500 Covered Call"),
        ("SPYD", "High Dividend"),
        ("DIV", "Global X Super Dividend"),
        ("MSTY", "MSFT Options"),
        ("NVDY", "NVDA Options"),
        ("TSLY", "Tesla Options"),
        ("AMZY", "Amazon Options"),
    ]

    print("\n" + "=" * 70)
    print("WEEKLY PAYER ETF ANALYSIS (No TWS Required)")
    print("=" * 70)

    results = []

    for ticker, name in weekly_payers:
        hist_1m = provider.get_historical(ticker, "1 M")
        hist_3m = provider.get_historical(ticker, "3 M")
        quote = provider.get_quote(ticker)

        price = quote["last"] if quote else 0

        if not hist_1m and not price:
            continue

        ret_1m = (
            (hist_1m[-1]["close"] - hist_1m[0]["close"]) / hist_1m[0]["close"] * 100
            if hist_1m
            else 0
        )
        ret_3m = (
            (hist_3m[-1]["close"] - hist_3m[0]["close"]) / hist_3m[0]["close"] * 100
            if hist_3m
            else 0
        )
        vol = calculate_volatility(hist_3m) if hist_3m else 0

        # Run debate
        debate = DebateOrchestrator(max_rounds=2)
        data = {
            "price_history": [h["close"] for h in hist_3m] if hist_3m else [price],
            "volume": quote["volume"] if quote else 5000000,
            "indicators": {"rsi": 45, "macd": {"histogram": -0.1}},
            "fundamentals": {"pe_ratio": 20, "earnings_yield": 0.06},
        }
        plan = debate.run_debate(ticker, data)

        sharpe = ret_3m / vol if vol > 0 else 0

        results.append(
            {
                "ticker": ticker,
                "name": name,
                "price": price,
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "vol": vol,
                "sharpe": sharpe,
                "rating": plan.rating.value,
                "conviction": plan.conviction,
            }
        )

    # Sort by risk-adjusted return
    results.sort(key=lambda x: x["sharpe"], reverse=True)

    print(
        f"\n{'TICKER':<8} {'PRICE':>8} {'1M':>8} {'3M':>8} {'VOL':>8} {'SHARPE':>8} {'RATING':<12} {'CONV':>4}"
    )
    print("-" * 80)

    for r in results:
        print(
            f"{r['ticker']:<8} ${r['price']:>7.2f} {r['ret_1m']:>+7.2f}% {r['ret_3m']:>+7.2f}% {r['vol']:>7.1f}% {r['sharpe']:>+7.2f} {r['rating']:<12} {r['conviction']:>4}"
        )

    return results


def log_trade(
    ticker: str,
    direction: str,
    rating: str,
    conviction: int,
    pnl_pct: float,
    holding_days: int,
    notes: str = "",
):
    """Manually log a trade outcome for learning."""
    from app.schemas import SignalDirection

    trade_result = {
        "ticker": ticker,
        "direction": direction,
        "rating": rating,
        "conviction": conviction,
        "macro_regime": "UNKNOWN",  # Would need market context
        "sector": "UNKNOWN",
        "pnl_pct": pnl_pct,
        "holding_days": holding_days,
        "entry_price": 0,
        "exit_price": 0,
    }

    entry = reflect_and_remember(trade_result)

    if entry:
        # Save to disk
        mem = get_memory()
        # The memory was already updated by reflect_and_remember
        save_memory(mem)
        print(f"Logged trade: {ticker} {direction} {pnl_pct:+.2f}%")
    else:
        print("Failed to log trade")


def show_memory():
    """Show all stored learnings."""
    mem = load_memory()

    print("\n" + "=" * 60)
    print("LEARNED EXPERIENCES")
    print("=" * 60)

    if len(mem) == 0:
        print("No experiences logged yet.")
        print("Use: python analysis_standalone.py --log-trade")
        return

    print(f"\nTotal experiences: {len(mem)}")
    print(f"Stats: {mem.get_statistics()}")

    print("\n--- Recent ---")
    for m in mem.get_recent_memories(10):
        print(f"\n{m.situation[:60]}...")
        print(f"  {m.outcome}")
        print(f"  → {m.lesson[:80]}...")


def _run_signal_scan():
    """Run the full 4-layer ATLAS signal pipeline across the ETF universe."""
    import yaml

    from app.signal_orchestrator import SignalOrchestrator
    from app.data.market_data import MarketDataProvider

    print("=" * 72)
    print("  ATLAS SIGNAL SCAN — Full 4-Layer Pipeline")
    print("=" * 72)

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "fixtures", "config.paper.yaml")
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Load universe
    universe_path = os.path.join(os.path.dirname(__file__), "fixtures", "universe.valid.yaml")
    with open(universe_path) as f:
        universe = yaml.safe_load(f)

    # Run the 4-layer pipeline
    orchestrator = SignalOrchestrator(config)
    signals = orchestrator.generate_signals(tickers=universe.get("all", []))

    print(f"\nScanned {len(signals)} tickers across 4 layers")
    print()

    # Print results table
    print(f"{'Ticker':<8} {'Rating':<14} {'Conviction':<12} {'Direction':<10} {'Size%':<8} {'Filter/Source'}")
    print("-" * 72)
    for s in signals:
        ticker = s.get("ticker", "?")
        rating = s.get("rating", "?")
        conv = s.get("conviction", 0)
        direction = s.get("direction", "?")
        size_pct = s.get("size_pct", 0)
        source = s.get("source_filter", "")
        print(f"{ticker:<8} {rating:<14} {conv:<12} {direction:<10} {size_pct:<8} {source}")

    print()
    print("Macro Regime Summary:")
    # Layer 1 already ran; show the macro regime from the orchestator
    if hasattr(orchestrator, "macro_layer") and hasattr(orchestrator.macro_layer, "evaluate"):
        macro_out = orchestrator.macro_layer.evaluate()
        risk_on = sum(1 for o in macro_out if o.regime_vote == "RISK_ON")
        risk_off = sum(1 for o in macro_out if o.regime_vote == "RISK_OFF")
        neutral = sum(1 for o in macro_out if o.regime_vote == "NEUTRAL")
        print(f"  RISK_ON={risk_on}  RISK_OFF={risk_off}  NEUTRAL={neutral}  "
              f"(based on {len(macro_out)} macro agents)")

    print()
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Trading Analysis (No TWS Required)")
    parser.add_argument("--ticker", help="Ticker to analyze")
    parser.add_argument(
        "--duration", default="3 M", help="Historical duration (e.g., 3 M)"
    )
    parser.add_argument("--signal", action="store_true", help="Generate trading signal")
    parser.add_argument("--income", action="store_true", help="Analyze income ETFs")
    parser.add_argument("--weekly", action="store_true", help="Analyze weekly payers")
    parser.add_argument(
        "--memory", action="store_true", help="Show learned experiences"
    )
    parser.add_argument(
        "--log-trade",
        nargs=6,
        metavar=("TICKER", "DIRECTION", "RATING", "CONVICTION", "PNL", "DAYS"),
        help="Log a trade: TICKER DIRECTION RATING CONVICTION PNL_PCT HOLDING_DAYS",
    )
    parser.add_argument(
        "--save-memory", action="store_true", help="Save memory to disk"
    )

    args = parser.parse_args()

    if args.income:
        analyze_income_etfs()
    elif args.weekly:
        analyze_weekly_payers()
    elif args.ticker:
        analyze_ticker(args.ticker.upper())
    elif args.memory:
        show_memory()
    elif args.signal:
        _run_signal_scan()
    elif args.log_trade:
        ticker, direction, rating, conviction, pnl, days = args.log_trade
        log_trade(
            ticker=ticker.upper(),
            direction=direction.upper(),
            rating=rating.upper(),
            conviction=int(conviction),
            pnl_pct=float(pnl),
            holding_days=int(days),
        )
    elif args.save_memory:
        mem = load_memory()
        save_memory(mem)
    else:
        # Default: show menu
        print("Trading Analysis (No TWS Required)")
        print()
        print("Options:")
        print("  --ticker SPY        Analyze a single ticker")
        print("  --income            Analyze income ETFs")
        print("  --weekly            Analyze weekly payers")
        print("  --memory            Show learned experiences")
        print("  --log-trade TICKER DIRECTION RATING CONVICTION PNL% DAYS")
        print("                      Log a trade for learning")
        print("  --save-memory       Save learnings to disk")


if __name__ == "__main__":
    main()

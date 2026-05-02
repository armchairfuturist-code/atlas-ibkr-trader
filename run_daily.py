#!/usr/bin/env python3
"""Simple daily paper trading runner.

Usage:
    python run_daily.py

Requirements:
    - TWS or IB Gateway running with API enabled
    - Paper trading account
"""

import os
import sys

# Ensure app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pipeline.daily_runner import DailyPipeline
from app.agents.debate_orchestrator import DebateOrchestrator
from app.schemas import SignalDirection


def main():
    print("=" * 60)
    print("ATLAS Paper Trading - Daily Runner")
    print("=" * 60)

    # Initialize pipeline
    pipeline = DailyPipeline()

    # Connection status
    if pipeline.ibkr_adapter.is_stub_mode():
        print("WARNING: Running in STUB mode (TWS not connected)")
        print("Start TWS with API enabled for live trading")
    else:
        print(f"Connected to TWS (Paper Mode)")
        info = pipeline.ibkr_adapter.get_account_info()
        print(f"  Net Liquidation: ${info.get('net_liquidation', 0):,.2f}")
        print(f"  Buying Power: ${info.get('buying_power', 0):,.2f}")

    print()

    # Run pipeline stages
    print("Running pipeline...")
    result = pipeline.run("full")

    print(f"\nResult: {result.status}")
    for log in result.logs:
        print(f"  {log}")

    # Show signals
    signals = pipeline.orchestrator.generate_signals()
    if signals:
        print(f"\n{len(signals)} Signals Generated:")
        for s in signals:
            print(
                f"  {s.ticker}: {s.direction.value} @ conviction={s.conviction} ({s.rating.value})"
            )

        # Run debate on top signal
        print("\nTop Signal Analysis (Multi-Agent Debate):")
        top = signals[0]

        debate = DebateOrchestrator(max_rounds=2)
        hist = pipeline.ibkr_adapter.get_historical(top.ticker, "1 W")

        data = {
            "price_history": [h["close"] for h in hist] if hist else [],
            "volume": 30000000,
            "indicators": {"rsi": 50, "macd": {"histogram": 0.1}},
            "fundamentals": {"pe_ratio": 20, "earnings_yield": 0.05},
        }

        plan = debate.run_debate(top.ticker, data)
        print(f"  {plan.ticker}: {plan.rating.value} (conviction={plan.conviction})")
        print(f"  Bull/Bear: {plan.bull_contribution:.0%}/{plan.bear_contribution:.0%}")
        print(f"  Thesis: {plan.thesis}")

        # Ask to submit order
        print(f"\n>>> Submit paper order for {top.ticker}? (y/n)")
        response = input().strip().lower() if sys.stdin.isatty() else "n"

        if response == "y":
            # Calculate shares based on conviction and position size
            shares = max(1, int(top.position_size_pct))  # Min 1 share
            order, err = pipeline.ibkr_adapter.submit_order(
                top.ticker, SignalDirection.LONG, shares
            )
            if err:
                print(f"Order error: {err}")
            else:
                print(f"ORDER SUBMITTED: {order.broker_order_id}")
                print(f"  {order.ticker} {order.direction.value} {order.shares} shares")
                print(f"  Check TWS to approve/fill order")
    else:
        print("\nNo signals generated - market conditions not favorable")

    print("\n" + "=" * 60)
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Integrated trading system with ai-hedge-fund enhancements.

Complete end-to-end pipeline:
1. Multi-dimensional analysis (technical, geopolitical, valuation, macro)
2. LLM-coordinated portfolio management
3. Correlation-adjusted risk management
4. Paper trading execution via IBKR TWS

Usage:
    python integrated_trading_system.py --tickers XLE XAR USO --theme iran --paper
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
from datetime import datetime

from app.portfolio.llm_portfolio_manager import (
    LLMCoordinatedPortfolioManager,
    PortfolioAction,
)
from app.agents.qlib_model_adapter import QlibModelAdapter
from app.risk.correlation_risk_manager import (
    CorrelationAdjustedRiskManager,
    PortfolioRiskProfile,
    Position,
)
from app.ibkr_adapter import IBKRAdapter
from app.config import Config
from app.schemas import SignalDirection


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_sample_price_data(ticker: str) -> dict:
    """Generate sample price data for demonstration."""
    import random

    random.seed(hash(ticker) % 10000)

    base_price = {
        "XLE": 85.0,
        "XAR": 110.0,
        "USO": 78.0,
        "XLI": 128.0,
        "XLF": 41.0,
        "QQQ": 430.0,
    }.get(ticker, 100.0)

    # Generate 60 days of price data
    prices = [base_price]
    for _ in range(59):
        change = random.gauss(0, 0.015)
        prices.append(prices[-1] * (1 + change))

    volumes = [random.randint(10_000_000, 30_000_000) for _ in range(60)]
    highs = [p * (1 + random.uniform(0, 0.02)) for p in prices]
    lows = [p * (1 - random.uniform(0, 0.02)) for p in prices]

    return {
        "prices": prices,
        "volumes": volumes,
        "highs": highs,
        "lows": lows,
    }


def get_sample_fundamentals(ticker: str) -> dict:
    """Generate sample fundamental data for demonstration."""
    fundamentals = {
        "XLE": {
            "sector": "ENERGY",
            "revenue": 500_000_000_000,
            "net_income": 50_000_000_000,
            "ebitda": 80_000_000_000,
            "fcf": 40_000_000_000,
            "shares_outstanding": 500_000_000,
            "total_debt": 20_000_000_000,
            "cash": 15_000_000_000,
            "beta": 1.2,
            "growth_rate": 0.08,
            "book_value": 200_000_000_000,
        },
        "XAR": {
            "sector": "DEFENSE",
            "revenue": 80_000_000_000,
            "net_income": 8_000_000_000,
            "ebitda": 12_000_000_000,
            "fcf": 6_000_000_000,
            "shares_outstanding": 80_000_000,
            "total_debt": 5_000_000_000,
            "cash": 2_000_000_000,
            "beta": 1.0,
            "growth_rate": 0.06,
            "book_value": 30_000_000_000,
        },
        "USO": {
            "sector": "OIL",
            "revenue": 10_000_000_000,
            "net_income": 5_000_000_000,
            "ebitda": 5_000_000_000,
            "fcf": 4_000_000_000,
            "shares_outstanding": 200_000_000,
            "total_debt": 1_000_000_000,
            "cash": 500_000_000,
            "beta": 1.5,
            "growth_rate": 0.12,
            "book_value": 8_000_000_000,
        },
    }
    return fundamentals.get(
        ticker,
        {
            "sector": "UNKNOWN",
            "revenue": 1_000_000_000,
            "net_income": 100_000_000,
            "ebitda": 150_000_000,
            "fcf": 80_000_000,
            "shares_outstanding": 10_000_000,
            "total_debt": 50_000_000,
            "cash": 20_000_000,
            "beta": 1.0,
            "growth_rate": 0.05,
            "book_value": 200_000_000,
        },
    )


def main():
    parser = argparse.ArgumentParser(description="Integrated AI Trading System")
    parser.add_argument(
        "--tickers", nargs="+", default=["XLE", "XAR", "USO"], help="Tickers to analyze"
    )
    parser.add_argument("--theme", default="iran", help="Macro theme to focus on")
    parser.add_argument(
        "--paper", action="store_true", default=True, help="Use paper trading mode"
    )
    parser.add_argument(
        "--portfolio-value",
        type=float,
        default=100000,
        help="Portfolio value for sizing",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute trades (default: analyze only)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("INTEGRATED AI TRADING SYSTEM")
    print("Qlib-enhanced with paper trading")
    print("=" * 80)
    print(f"\nAnalysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tickers: {', '.join(args.tickers)}")
    print(f"Theme: {args.theme}")
    print(f"Portfolio Value: ${args.portfolio_value:,.0f}")
    print(f"Execution Mode: {'LIVE' if args.execute else 'ANALYSIS ONLY'}")

    # Initialize components
    print("\n[1] Initializing Portfolio Manager (Qlib-enhanced)...")
    portfolio_manager = LLMCoordinatedPortfolioManager(use_qlib=True)

    # Check Qlib status
    tech_type = type(portfolio_manager.technical).__name__
    if isinstance(portfolio_manager.technical, QlibModelAdapter):
        qlib_status = (
            "Qlib ML Active"
            if portfolio_manager.technical._qlib_available
            else "Qlib Fallback (Rule-based)"
        )
    else:
        qlib_status = "Rule-based (Qlib disabled)"
    print(f"    Technical Engine: {tech_type} — {qlib_status}")

    print("[2] Preparing Market Data...")
    price_data = {ticker: get_sample_price_data(ticker) for ticker in args.tickers}
    fundamentals = {ticker: get_sample_fundamentals(ticker) for ticker in args.tickers}

    print("[3] Building Portfolio Risk Profile...")
    # Start with empty portfolio
    current_portfolio = PortfolioRiskProfile(
        total_value=args.portfolio_value,
        positions=[],
        sector_exposure={},
        volatility_60d={},
        correlations={},
    )

    # Calculate volatilities for each ticker
    risk_manager = CorrelationAdjustedRiskManager()
    for ticker, data in price_data.items():
        vol = risk_manager._calculate_annualized_volatility(data["prices"])
        current_portfolio.volatility_60d[ticker] = vol

    # Calculate correlations between tickers
    for i, t1 in enumerate(args.tickers):
        for t2 in args.tickers[i + 1 :]:
            corr = risk_manager._calculate_correlation(
                price_data[t1]["prices"], price_data[t2]["prices"]
            )
            current_portfolio.correlations[(t1, t2)] = corr

    print("[4] Running Multi-Dimensional Analysis...")
    print("    - Sophisticated Technical (5-strategy ensemble)")
    print("    - Geopolitical Sentiment (Polymarket)")
    print("    - Multi-DCF Valuation")
    print("    - Macro-Thematic Mapping")
    print("    - Correlation-Adjusted Risk")

    # Generate recommendations
    recommendation = portfolio_manager.analyze_tickers(
        tickers=args.tickers,
        price_data=price_data,
        fundamentals=fundamentals,
        current_portfolio=current_portfolio,
        theme=args.theme,
    )

    # Display results
    print("\n" + "=" * 80)
    print("PORTFOLIO RECOMMENDATIONS")
    print("=" * 80)

    print(f"\nMacro Theme: {recommendation.macro_theme}")
    print(f"Total Recommendations: {recommendation.total_positions}")
    print(f"Average Confidence: {recommendation.avg_confidence:.0f}%")

    if recommendation.risk_warnings:
        print("\n⚠️  Risk Warnings:")
        for warning in recommendation.risk_warnings:
            print(f"  - {warning}")

    print("\n" + "-" * 80)
    print("TOP POSITIONS:")
    print("-" * 80)

    for i, pos in enumerate(recommendation.positions, 1):
        print(f"\n{i}. {pos.ticker} - {pos.action.value}")
        print(f"   Shares: {pos.shares}")
        print(f"   Entry: ${pos.entry_price:.2f}")
        print(f"   Stop Loss: ${pos.stop_loss:.2f}")
        print(f"   Target: ${pos.target_price:.2f}")
        print(f"   Confidence: {pos.confidence:.0f}%")
        print(f"   Conviction Score: {pos.conviction_score:.1f}")
        print(f"\n   Component Scores:")
        print(f"     Technical: {pos.technical_score:+.1f}")
        print(f"     Geopolitical: {pos.geopolitical_score:+.1f}")
        print(f"     Valuation: {pos.valuation_score:+.1f}")
        print(f"     Macro: {pos.macro_score:+.1f}")
        print(f"\n   Reasoning:")
        for line in pos.reasoning.split("\n")[:10]:
            print(f"     {line}")

    print("\n" + "=" * 80)
    print("PORTFOLIO THESIS")
    print("=" * 80)
    print(recommendation.portfolio_thesis)

    # Execute trades if requested
    if args.execute and recommendation.positions:
        print("\n" + "=" * 80)
        print("EXECUTING TRADES (Paper Trading)")
        print("=" * 80)

        config = Config()
        adapter = IBKRAdapter(config)

        print("\n[5] Connecting to IBKR...")
        connected, error = adapter.connect()

        if not connected:
            print(f"❌ Connection failed: {error}")
            print("   Using stub mode (simulated execution)")
        else:
            mode = "STUB" if adapter.is_stub_mode() else "LIVE PAPER"
            print(f"✓ Connected ({mode} mode)")

        print("\n[6] Submitting Orders...")
        executed_orders = []

        for pos in recommendation.positions:
            if pos.action == PortfolioAction.BUY:
                direction = SignalDirection.LONG
            elif pos.action == PortfolioAction.SHORT:
                direction = SignalDirection.SHORT
            else:
                continue  # Skip SELL/COVER for now

            print(
                f"\n   Submitting: {pos.ticker} {direction.value} {pos.shares} shares..."
            )

            order, error = adapter.submit_order(
                ticker=pos.ticker,
                direction=direction,
                shares=pos.shares,
                order_type="MKT",
            )

            if order:
                print(f"   ✓ Order submitted: {order.broker_order_id}")
                executed_orders.append(
                    {
                        "ticker": pos.ticker,
                        "action": pos.action.value,
                        "shares": pos.shares,
                        "order_id": order.broker_order_id,
                    }
                )
            else:
                print(f"   ❌ Failed: {error}")

        print(f"\n✓ Execution complete: {len(executed_orders)} orders submitted")

        # Show account info
        print("\n[7] Account Summary:")
        account = adapter.get_account_info()
        for key, value in account.items():
            if isinstance(value, float):
                print(f"   {key}: ${value:,.2f}")
            else:
                print(f"   {key}: {value}")

        adapter.disconnect()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    # Show which engine was used
    tech_type = type(portfolio_manager.technical).__name__
    if isinstance(portfolio_manager.technical, QlibModelAdapter):
        if portfolio_manager.technical._qlib_available:
            engine_desc = "Qlib ML (LightGBM) + Rule-based Hybrid"
        else:
            engine_desc = "Rule-based Technical Analysis (Qlib unavailable)"
    else:
        engine_desc = "Rule-based Technical Analysis"

    print(f"\nKey Capabilities Demonstrated:")
    print(f"  ✓ {engine_desc}")
    print("  ✓ Geopolitical Sentiment (Polymarket integration)")
    print("  ✓ Multi-DCF Valuation (5 methodologies)")
    print("  ✓ Correlation-Adjusted Risk Management")
    print("  ✓ Macro-Thematic Portfolio Construction")
    print("  ✓ IBKR Paper Trading Execution")
    print("\nQlib Setup (for ML-enhanced predictions):")
    print("  1. Install Python 3.12 (Qlib doesn't support 3.14)")
    print("  2. pip install pyqlib pandas numpy lightgbm")
    print("  3. python scripts/prepare_qlib_data.py")
    print("  4. python scripts/train_qlib_model.py")
    print("  5. python scripts/backtest_qlib.py")


if __name__ == "__main__":
    main()

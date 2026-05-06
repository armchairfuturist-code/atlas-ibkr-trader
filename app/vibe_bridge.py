#!/usr/bin/env python3
"""
Vibe-Trading Bridge — Connects our system's recommendations to Vibe-Trading's
backtesting engines, strategy generation, and multi-platform export.

Architecture:
  Our System (recommendation + risk + narrative) 
    → Vibe-Trading (backtest + strategy + export)
    → Browser / TradingView / MT5

Usage:
    python -m app.vibe_bridge backtest --ticker TLN --start 2024-01-01 --end 2026-05-01
    python -m app.vibe_bridge run-swarm --preset investment_committee --target "TLN energy transition"
    python -m app.vibe_bridge serve   # Start Vibe-Trading API server
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


@dataclass
class BacktestRequest:
    """Request to backtest a ticker strategy via Vibe-Trading."""
    ticker: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    strategy_description: str = "Buy on RSI < 30, sell on RSI > 70"  # natural language strategy
    data_source: str = "yfinance"  # yfinance, akshare, okx, etc.
    confidence: int = 50  # our system's conviction score [1-100]


@dataclass
class BacktestResult:
    """Parsed backtest results from Vibe-Trading."""
    ticker: str
    run_id: str
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    num_trades: int = 0
    strategy_code: str = ""
    pine_script: str = ""
    error: Optional[str] = None
    raw_output: str = ""


@dataclass
class SwarmRequest:
    """Request to run a Vibe-Trading swarm preset."""
    preset: str  # e.g., "investment_committee", "technical_analysis_panel"
    target: str  # ticker or description
    variables: dict[str, str] = field(default_factory=dict)
    max_iterations: int = 30


@dataclass
class SwarmResult:
    """Parsed swarm results."""
    run_id: str
    preset: str
    conclusion: str = ""
    agent_outputs: dict = field(default_factory=dict)
    error: Optional[str] = None
    raw_output: str = ""


class VibeTradingBridge:
    """
    Bridge to Vibe-Trading's CLI and programmatic API.
    
    Can operate in two modes:
    1. CLI subprocess mode: calls `vibe-trading` CLI for backtesting and swarms
    2. Direct import mode: imports Vibe-Trading modules directly (when available)
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".vibe-trading"
        self._check_available()

    def _check_available(self) -> bool:
        """Check if Vibe-Trading is installed."""
        try:
            result = subprocess.run(
                ["vibe-trading", "--version"],
                capture_output=True, text=True, timeout=5
            )
            available = result.returncode == 0
            if available:
                logger.info(f"Vibe-Trading available: {result.stdout.strip()}")
            return available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Vibe-Trading CLI not found")
            return False

    @property
    def available(self) -> bool:
        return self._check_available()

    def backtest(self, request: BacktestRequest) -> BacktestResult:
        """
        Run a backtest via Vibe-Trading CLI.
        
        Uses a natural language prompt that Vibe-Trading's agent
        translates into a backtestable strategy.
        """
        prompt = (
            f"Backtest {request.ticker} from {request.start_date} to {request.end_date} "
            f"using {request.data_source}. "
            f"Strategy: {request.strategy_description}. "
            f"Provide: total return, Sharpe ratio, max drawdown, "
            f"win rate, number of trades, and the full strategy code."
        )

        logger.info(f"Running Vibe-Trading backtest for {request.ticker}...")

        try:
            result = subprocess.run(
                ["vibe-trading", "run", "-p", prompt, "--json"],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "VIBE_TRADING_ENABLE_SHELL_TOOLS": "1"}
            )

            output = result.stdout if result.stdout else result.stderr

            # Try to parse JSON output
            run_id = "unknown"
            try:
                data = json.loads(output) if output.startswith("{") else None
                if data:
                    run_id = data.get("run_id", "unknown")
            except json.JSONDecodeError:
                pass

            # Extract run ID from text output
            if run_id == "unknown":
                for line in output.split("\n"):
                    if "run_id" in line.lower() or "id" in line.lower():
                        parts = line.split(":")
                        if len(parts) > 1:
                            run_id = parts[-1].strip()
                            break

            return BacktestResult(
                ticker=request.ticker,
                run_id=run_id,
                raw_output=output,
            )

        except subprocess.TimeoutExpired:
            return BacktestResult(
                ticker=request.ticker,
                run_id="timeout",
                error="Backtest timed out after 120s",
            )
        except Exception as e:
            return BacktestResult(
                ticker=request.ticker,
                run_id="error",
                error=str(e),
            )

    def backtest_our_recommendation(
        self,
        ticker: str,
        conviction: int,
        sector: str,
        thesis: str,
        days_back: int = 365,
    ) -> BacktestResult:
        """
        Backtest one of our system's recommendations.
        
        Generates a strategy description based on our narrative context.
        """
        # Build strategy description from our thesis
        strategy_map = {
            "POWER": "Buy on dips with RSI < 35 in an AI infrastructure bull trend. "
                     "Hold for medium-term as power demand increases from data centers.",
            "RARE_EARTH": "Buy on policy catalyst pullbacks. "
                          "Trend-follow with 50-day EMA as support.",
            "URANIUM": "Buy on weakness with RSI < 30. "
                       "Nuclear power demand is structural, not cyclical.",
            "JAPAN_CHEM": "Buy and hold. Japanese chemical monopolies "
                          "have pricing power and no competition.",
            "OPTICAL": "Mean reversion strategy. Buy when RSI < 30 after pullback.",
            "INFRA": "Trend-follow with 20-day EMA. "
                     "Data center infrastructure spending is accelerating.",
            "STORAGE": "Momentum strategy. Follow institutional accumulation patterns.",
        }
        strategy = strategy_map.get(sector, "Trend-follow with moving average crossover.")

        return self.backtest(BacktestRequest(
            ticker=ticker,
            start_date=f"{datetime.now().strftime('%Y-%m-%d')[:-6]}01-01",
            end_date=datetime.now().strftime("%Y-%m-%d"),
            strategy_description=strategy,
            confidence=conviction,
        ))

    def run_swarm(self, request: SwarmRequest) -> SwarmResult:
        """
        Run a Vibe-Trading swarm preset.
        
        Swarm presets are multi-agent teams that research and debate.
        Useful for: investment_committee, technical_analysis_panel,
        portfolio_review_board, etc.
        """
        # Build CLI args
        var_args = []
        for k, v in request.variables.items():
            var_args.extend(["--vars", f"{k}={v}"])

        cmd = [
            "vibe-trading", "--swarm-run", request.preset,
            request.target,
            *var_args,
            "--json"
        ]

        logger.info(f"Running swarm: {request.preset} on {request.target}...")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
                env={**os.environ, "VIBE_TRADING_ENABLE_SHELL_TOOLS": "1"}
            )

            output = result.stdout if result.stdout else result.stderr

            return SwarmResult(
                run_id="swarm-" + datetime.now().strftime("%H%M%S"),
                preset=request.preset,
                raw_output=output,
            )

        except subprocess.TimeoutExpired:
            return SwarmResult(
                run_id="timeout",
                preset=request.preset,
                error="Swarm timed out after 180s",
            )
        except Exception as e:
            return SwarmResult(
                run_id="error",
                preset=request.preset,
                error=str(e),
            )

    def export_to_pine(self, run_id: str) -> Optional[str]:
        """Export a backtest strategy to Pine Script for TradingView."""
        try:
            result = subprocess.run(
                ["vibe-trading", "--pine", run_id],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            logger.error(f"Pine export failed: {e}")
            return None

    def show_backtest_code(self, run_id: str) -> Optional[str]:
        """Show the generated Python code from a backtest run."""
        try:
            result = subprocess.run(
                ["vibe-trading", "--code", run_id],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            logger.error(f"Code display failed: {e}")
            return None

    def start_api_server(self, port: int = 8899, host: str = "127.0.0.1", dev: bool = False):
        """Start Vibe-Trading API server (blocking)."""
        cmd = ["vibe-trading", "serve", "--host", host, "--port", str(port)]
        if dev:
            cmd.append("--dev")
        logger.info(f"Starting Vibe-Trading API server on {host}:{port}...")
        subprocess.run(cmd)


# Singleton
vibe_bridge = VibeTradingBridge()


def main():
    """CLI entry point for the bridge."""
    import argparse
    parser = argparse.ArgumentParser(description="Vibe-Trading Bridge")
    sub = parser.add_subparsers(dest="command")

    # backtest command
    bt = sub.add_parser("backtest", help="Backtest a ticker via Vibe-Trading")
    bt.add_argument("--ticker", required=True)
    bt.add_argument("--start", default="2024-01-01")
    bt.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    bt.add_argument("--strategy", default="Buy on RSI < 30, sell on RSI > 70")
    bt.add_argument("--source", default="yfinance")

    # swarm command
    sw = sub.add_parser("swarm", help="Run a swarm preset")
    sw.add_argument("--preset", required=True)
    sw.add_argument("--target", required=True)
    sw.add_argument("--vars", nargs="*", default=[])

    # recommend command (backtest our top picks)
    rc = sub.add_parser("recommend", help="Backtest our receiver-company picks")
    rc.add_argument("--ticker", required=True)
    rc.add_argument("--conviction", type=int, default=50)
    rc.add_argument("--sector", default="POWER")

    # serve command
    sv = sub.add_parser("serve", help="Start Vibe-Trading API server")
    sv.add_argument("--port", type=int, default=8899)
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--dev", action="store_true")

    args = parser.parse_args()

    bridge = VibeTradingBridge()

    if not bridge.available:
        print("⚠️  Vibe-Trading is not installed. Run: pip install vibe-trading-ai")
        sys.exit(1)

    if args.command == "backtest":
        req = BacktestRequest(args.ticker, args.start, args.end, args.strategy, args.source)
        result = bridge.backtest(req)
        print(f"\n{'='*60}")
        print(f"  BACKTEST: {result.ticker}")
        print(f"  Run ID: {result.run_id}")
        print(f"{'='*60}")
        if result.error:
            print(f"  Error: {result.error}")
        else:
            print(f"\n  Raw output:")
            print(f"  {result.raw_output[:2000]}")

    elif args.command == "swarm":
        vars_dict = {}
        for v in args.vars:
            if "=" in v:
                k, val = v.split("=", 1)
                vars_dict[k] = val
        req = SwarmRequest(args.preset, args.target, vars_dict)
        result = bridge.run_swarm(req)
        print(f"\n{'='*60}")
        print(f"  SWARM: {result.preset} → {req.target}")
        print(f"  Run ID: {result.run_id}")
        print(f"{'='*60}")
        if result.error:
            print(f"  Error: {result.error}")
        else:
            print(f"\n  Raw output:")
            print(f"  {result.raw_output[:2000]}")

    elif args.command == "recommend":
        result = bridge.backtest_our_recommendation(
            args.ticker, args.conviction, args.sector,
            f"Our system rates {args.ticker} as a receiver-company play in {args.sector}"
        )
        print(f"\n{'='*60}")
        print(f"  RECOMMENDATION BACKTEST: {result.ticker}")
        print(f"  Run ID: {result.run_id}")
        print(f"{'='*60}")
        if result.error:
            print(f"  Error: {result.error}")
        else:
            print(f"\n  Raw output:")
            print(f"  {result.raw_output[:2000]}")

    elif args.command == "serve":
        bridge.start_api_server(args.port, args.host, args.dev)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

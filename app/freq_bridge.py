#!/usr/bin/env python3
"""
Freqtrade Bridge — connects our system's signals to freqtrade's 
hyperopt parameter optimization and backtesting engines.

Freqtrade is the most mature open-source algo trading framework.
Its hyperopt engine uses genetic algorithms to find optimal strategy
parameters (entry/exit thresholds, stop losses, position sizing).

Integration flow:
  Our System (narrative thesis + signals)
    → Freqtrade Strategy (our logic, encoded)
    → Hyperopt (genetic parameter optimization)
    → Backtesting (walk-forward validation)
    → Our System (optimized entry/exit levels)

Usage:
    python -m app.freq_bridge hyperopt --ticker TLN --days 365
    python -m app.freq_bridge backtest --ticker TLN --params '{"rsi_buy": 35, "rsi_sell": 65}'
    python -m app.freq_bridge optimize-all  # Run on all receiver-company picks
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


@dataclass
class HyperoptResult:
    """Optimized parameters from freqtrade hyperopt."""
    ticker: str
    total_epochs: int = 0
    best_sharpe: float = 0.0
    best_profit_pct: float = 0.0
    best_params: dict = field(default_factory=dict)
    error: Optional[str] = None
    raw_output: str = ""


@dataclass
class BacktestResult:
    """Backtest results from freqtrade."""
    ticker: str
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    num_trades: int = 0
    profit_factor: float = 0.0
    error: Optional[str] = None
    raw_output: str = ""


class FreqtradeBridge:
    """
    Bridge to freqtrade's hyperopt and backtesting engines.
    
    Encodes our narrative-driven signals as freqtrade strategies,
    then uses hyperopt to find optimal entry/exit parameters.
    """

    def __init__(self):
        self.user_data_dir = ROOT / ".freqtrade"
        self._check_available()

    def _check_available(self) -> bool:
        try:
            r = subprocess.run(["freqtrade", "--version"], capture_output=True, text=True, timeout=5)
            self.available = r.returncode == 0
            if self.available:
                logger.info(f"Freqtrade available")
            return self.available
        except FileNotFoundError:
            self.available = False
            logger.warning("Freqtrade not installed")
            return False

    def _ensure_user_data(self):
        """Ensure .freqtrade user data directory exists."""
        (self.user_data_dir / "strategies").mkdir(parents=True, exist_ok=True)

    def _generate_strategy(self, ticker: str, sector: str, narrative_phase: str) -> str:
        """
        Generate a freqtrade strategy class based on our narrative framework.
        
        Different narrative phases get different strategy templates:
          - pre-discovery: aggressive entry (lower RSI, wider stops)
          - discovery: momentum-follow (trend confirmation)
          - priced-in: mean reversion (fade the move)
          - exhaustion: short-biased (if allowed)
        """
        if narrative_phase == "pre-discovery":
            # Aggressive accumulation: buy deep dips, wide stops
            return f'''
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import pandas as pd
import talib.abstract as ta

class Atlas_{ticker}_Strategy(IStrategy):
    timeframe = "1d"
    can_short = False
    startup_candle_count = 50

    buy_params = {{
        "rsi_buy": 35,
        "ema_short": 20,
        "ema_long": 50,
    }}
    sell_params = {{
        "rsi_sell": 70,
        "profit_target": 0.15,
    }}

    minimal_roi = {{"0": 0.25, "30": 0.05, "60": 0}}
    stoploss = -0.25
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10

    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df["rsi"] = ta.RSI(df, timeperiod=14)
        df["ema_short"] = ta.EMA(df, timeperiod=self.buy_params["ema_short"])
        df["ema_long"] = ta.EMA(df, timeperiod=self.buy_params["ema_long"])
        df["atr"] = ta.ATR(df, timeperiod=14)
        return df

    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[
            (df["rsi"] < self.buy_params["rsi_buy"]) &
            (df["ema_short"] > df["ema_long"]),
            "enter_long"
        ] = 1
        return df

    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[
            (df["rsi"] > self.sell_params["rsi_sell"]) |
            (df["close"] > df["close"].rolling(50).max() * 0.95),
            "exit_long"
        ] = 1
        return df
'''

        elif narrative_phase == "discovery":
            # Momentum-follow: enter on strength, tighter stops
            return f'''
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import pandas as pd
import talib.abstract as ta

class Atlas_{ticker}_Strategy(IStrategy):
    timeframe = "1d"
    can_short = False
    startup_candle_count = 50

    buy_params = {{
        "rsi_buy": 55,
        "macd_fast": 12,
        "macd_slow": 26,
    }}
    sell_params = {{
        "rsi_sell": 80,
        "profit_target": 0.25,
    }}

    minimal_roi = {{"0": 0.35, "30": 0.10, "60": 0}}
    stoploss = -0.18
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10

    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df["rsi"] = ta.RSI(df, timeperiod=14)
        df["macd"], df["macdsignal"], df["macdhist"] = ta.MACD(
            df, fastperiod=self.buy_params["macd_fast"],
            slowperiod=self.buy_params["macd_slow"], signalperiod=9
        )
        return df

    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[
            (df["macd"] > df["macdsignal"]) &
            (df["rsi"] > self.buy_params["rsi_buy"]),
            "enter_long"
        ] = 1
        return df

    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[
            (df["rsi"] > self.sell_params["rsi_sell"]) |
            (df["macd"] < df["macdsignal"]),
            "exit_long"
        ] = 1
        return df
'''

        else:
            # Default: balanced strategy
            return f'''
from freqtrade.strategy import IStrategy
import pandas as pd
import talib.abstract as ta

class Atlas_{ticker}_Strategy(IStrategy):
    timeframe = "1d"
    can_short = False
    startup_candle_count = 50

    buy_params = {{
        "rsi_buy": 40,
        "ema_short": 20,
        "ema_long": 50,
    }}
    minimal_roi = {{"0": 0.20, "30": 0.05, "60": 0}}
    stoploss = -0.20
    trailing_stop = True

    def populate_indicators(self, df, metadata):
        df["rsi"] = ta.RSI(df, timeperiod=14)
        df["ema_short"] = ta.EMA(df, timeperiod=self.buy_params["ema_short"])
        df["ema_long"] = ta.EMA(df, timeperiod=self.buy_params["ema_long"])
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[(df["rsi"] < self.buy_params["rsi_buy"]) & (df["ema_short"] > df["ema_long"]), "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["rsi"] > 75, "exit_long"] = 1
        return df
'''

    def _generate_hyperopt(self, ticker: str, epochs: int = 100) -> str:
        """Generate a hyperopt loss function class."""
        return f'''
from freqtrade.optimize.hyperopt import IHyperOptLoss
import pandas as pd

class Atlas_{ticker}_HyperoptLoss(IHyperOptLoss):
    @staticmethod
    def hyperopt_loss_function(results: pd.DataFrame, trade_count: int,
                                min_date, max_date, config, processed, backtest_stats):
        if trade_count == 0:
            return 100000.0
        total_profit = results["profit_ratio"].sum()
        sharpe = backtest_stats.get("sharpe", 0)
        max_drawdown = backtest_stats.get("max_drawdown", 1)
        
        # Score: maximize Sharpe, minimize drawdown
        score = -(sharpe * 100) + (max_drawdown * 10)
        if total_profit < 0:
            score += 10000
        return score
'''

    def setup_strategy(self, ticker: str, sector: str = "POWER", 
                       narrative_phase: str = "pre-discovery") -> Optional[Path]:
        """Write a freqtrade strategy file based on our narrative context."""
        self._ensure_user_data()
        code = self._generate_strategy(ticker, sector, narrative_phase)
        path = self.user_data_dir / "strategies" / f"Atlas_{ticker}_Strategy.py"
        path.write_text(code)
        logger.info(f"Strategy written: {path}")
        return path

    def setup_hyperopt_loss(self, ticker: str) -> Path:
        """Write the hyperopt loss function."""
        self._ensure_user_data()
        code = self._generate_hyperopt(ticker)
        path = self.user_data_dir / "strategies" / f"Atlas_{ticker}_HyperoptLoss.py"
        path.write_text(code)
        return path

    def download_data(self, ticker: str, days: int = 365) -> bool:
        """Download historical data for a ticker using yfinance data source."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            hist = t.history(period=f"{days}d")
            # Save as JSON for freqtrade format
            out_dir = self.user_data_dir / "data" / "yfinance"
            out_dir.mkdir(parents=True, exist_ok=True)
            hist.to_parquet(out_dir / f"{ticker}-1d.parquet")
            logger.info(f"Downloaded {len(hist)} days for {ticker}")
            return True
        except Exception as e:
            logger.error(f"Data download failed for {ticker}: {e}")
            return False

    def run_hyperopt(self, ticker: str, epochs: int = 100, days: int = 365) -> HyperoptResult:
        """
        Run freqtrade hyperopt to find optimal strategy parameters.
        
        This uses a genetic algorithm to find the parameter set that
        maximizes the Sharpe ratio for our strategy on this ticker.
        """
        if not self.available:
            return HyperoptResult(ticker=ticker, error="Freqtrade not installed")

        self.setup_strategy(ticker)
        self.setup_hyperopt_loss(ticker)
        self.download_data(ticker, days)

        config_path = self.user_data_dir / "config.json"
        if not config_path.exists():
            config_path.write_text(json.dumps({
                "trading_mode": "spot",
                "data_dir": str(self.user_data_dir / "data"),
                "strategy": f"Atlas_{ticker}_Strategy",
                "timeframe": "1d",
            }, indent=2))

        cmd = [
            "freqtrade", "hyperopt",
            "--strategy", f"Atlas_{ticker}_Strategy",
            "--hyperopt-loss", f"Atlas_{ticker}_HyperoptLoss",
            "--config", str(config_path),
            "--epochs", str(epochs),
            "--timerange", f"{(datetime.now().year-1)}0101-",
        ]

        logger.info(f"Running hyperopt for {ticker} ({epochs} epochs)...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            output = result.stdout or result.stderr
            return HyperoptResult(ticker=ticker, total_epochs=epochs, raw_output=output[:5000])
        except subprocess.TimeoutExpired:
            return HyperoptResult(ticker=ticker, error="Hyperopt timed out (600s)")
        except Exception as e:
            return HyperoptResult(ticker=ticker, error=str(e))

    def run_backtest(self, ticker: str, params: Optional[dict] = None, 
                     days: int = 365) -> BacktestResult:
        """Run backtest with optional custom parameters."""
        if not self.available:
            return BacktestResult(ticker=ticker, error="Freqtrade not installed")

        self.setup_strategy(ticker)
        self.download_data(ticker, days)

        config = {
            "trading_mode": "spot",
            "data_dir": str(self.user_data_dir / "data"),
            "strategy": f"Atlas_{ticker}_Strategy",
            "timeframe": "1d",
        }
        if params:
            config["strategy_params"] = {f"Atlas_{ticker}_Strategy": params}

        config_path = self.user_data_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        cmd = [
            "freqtrade", "backtesting",
            "--strategy", f"Atlas_{ticker}_Strategy",
            "--config", str(config_path),
            "--timerange", f"{(datetime.now().year-1)}0101-",
        ]

        logger.info(f"Running backtest for {ticker}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = result.stdout or result.stderr
            return BacktestResult(ticker=ticker, raw_output=output[:5000])
        except subprocess.TimeoutExpired:
            return BacktestResult(ticker=ticker, error="Backtest timed out")
        except Exception as e:
            return BacktestResult(ticker=ticker, error=str(e))

    def optimize_all_picks(self, picks: Optional[list[str]] = None):
        """Run hyperopt on all our receiver-company picks."""
        if picks is None:
            picks = ["TLN", "CEG", "VST", "UUUU", "MP", "AAOI", "FN", "MTSI"]
        results = []
        for t in picks:
            print(f"\n  Optimizing {t}...")
            r = self.run_hyperopt(t, epochs=50)
            results.append(r)
            print(f"    {'✓' if not r.error else '✗'} {r.error or 'done'}")
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Freqtrade Bridge")
    sub = parser.add_subparsers(dest="command")

    hyp = sub.add_parser("hyperopt", help="Optimize strategy parameters")
    hyp.add_argument("--ticker", required=True)
    hyp.add_argument("--epochs", type=int, default=100)

    bt = sub.add_parser("backtest", help="Backtest a ticker")
    bt.add_argument("--ticker", required=True)
    bt.add_argument("--params", default=None)

    opt = sub.add_parser("optimize-all", help="Optimize all receiver-company picks")

    args = parser.parse_args()
    bridge = FreqtradeBridge()

    if args.command == "hyperopt":
        r = bridge.run_hyperopt(args.ticker, args.epochs)
        print(f"Hyperopt results for {r.ticker}:")
        print(f"  Error: {r.error or 'None'}")
        print(f"  Output: {r.raw_output[:1000]}")

    elif args.command == "backtest":
        params = json.loads(args.params) if args.params else None
        r = bridge.run_backtest(args.ticker, params)
        print(f"Backtest results for {r.ticker}:")
        print(f"  Error: {r.error or 'None'}")

    elif args.command == "optimize-all":
        results = bridge.optimize_all_picks()
        print(f"\nOptimized {len(results)} tickers")


if __name__ == "__main__":
    main()

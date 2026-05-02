"""Backtest Qlib model vs rule-based vs hybrid approach.

Compares three strategies on historical data:
1. Rule-based (current SophisticatedTechnicalAnalyzer)
2. Qlib ML model (if available)
3. Hybrid (Qlib 60% + Rule-based 40%)

Usage:
    python scripts/backtest_qlib.py [--data qlib_data] [--model models/qlib_technical_model]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_market_data(data_path: Path) -> dict:
    """Load market data from JSON."""
    json_path = data_path / "market_data.json"
    if not json_path.exists():
        logger.error(f"No market data at {json_path}")
        logger.error("Run: python scripts/prepare_qlib_data.py first")
        return {}

    with open(json_path) as f:
        return json.load(f)


def load_model(model_path: Path):
    """Load trained LightGBM model."""
    try:
        import joblib

        model_file = model_path / "model.pkl"
        if not model_file.exists():
            logger.warning(f"No model at {model_file}")
            return None
        return joblib.load(model_file)
    except ImportError:
        logger.warning("joblib not installed")
        return None


def load_feature_names(model_path: Path) -> list:
    """Load feature names for model inference."""
    features_file = model_path / "feature_names.json"
    if not features_file.exists():
        return []
    with open(features_file) as f:
        return json.load(f)


def compute_features_for_row(df, idx: int) -> dict:
    """Compute features for a single row index."""
    import pandas as pd

    window = df.iloc[: idx + 1]
    features = {}

    if len(window) < 20:
        return features

    close = window["close"]
    volume = window["volume"]

    # Returns
    for p in [5, 10, 20, 30, 60]:
        if len(close) >= p:
            features[f"ret_{p}"] = (close.iloc[-1] - close.iloc[-p]) / close.iloc[-p]

    # MA ratios
    for p in [5, 10, 20, 60]:
        if len(close) >= p:
            ma = close.rolling(p).mean().iloc[-1]
            features[f"ma_{p}_ratio"] = close.iloc[-1] / ma if ma > 0 else 1.0

    # Volatility
    for p in [10, 20, 60]:
        if len(close) >= p:
            features[f"vol_{p}"] = close.pct_change().rolling(p).std().iloc[-1]

    # Volume ratio
    if len(volume) >= 20:
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ma20 = volume.rolling(20).mean().iloc[-1]
        features["volume_ratio"] = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0

    # RSI
    if len(close) >= 14:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        features["rsi_14"] = 100 - (100 / (1 + gain / loss)) if loss > 0 else 100

    # MACD
    if len(close) >= 26:
        ema_12 = close.ewm(span=12).mean().iloc[-1]
        ema_26 = close.ewm(span=26).mean().iloc[-1]
        features["macd"] = ema_12 - ema_26

    # BB position
    if len(close) >= 20:
        sma_20 = close.rolling(20).mean().iloc[-1]
        std_20 = close.rolling(20).std().iloc[-1]
        if std_20 > 0:
            features["bb_position"] = (close.iloc[-1] - (sma_20 - 2 * std_20)) / (
                4 * std_20
            )

    # Price position
    if len(close) >= 20:
        high_20 = close.rolling(20).max().iloc[-1]
        low_20 = close.rolling(20).min().iloc[-1]
        if high_20 != low_20:
            features["price_position"] = (close.iloc[-1] - low_20) / (high_20 - low_20)

    return features


def rule_based_signal(prices: list[float]) -> float:
    """Generate rule-based signal (-1 to +1)."""
    if len(prices) < 30:
        return 0

    # Simple ensemble
    score = 0

    # EMA cross
    ema_12 = prices[-12:]
    ema_26 = prices[-26:]
    if len(ema_12) >= 12 and len(ema_26) >= 26:
        avg_12 = sum(ema_12) / 12
        avg_26 = sum(ema_26) / 26
        if avg_12 > avg_26:
            score += 0.3
        else:
            score -= 0.3

    # RSI
    if len(prices) >= 14:
        deltas = [
            prices[i] - prices[i - 1] for i in range(len(prices) - 14, len(prices))
        ]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains) / 14 if len(gains) > 0 else 0
        avg_loss = sum(losses) / 14 if len(losses) > 0 else 0
        if avg_loss > 0:
            rsi = 100 - (100 / (1 + avg_gain / avg_loss))
            if rsi < 30:
                score += 0.3
            elif rsi > 70:
                score -= 0.3

    # Momentum
    if len(prices) >= 20:
        mom = (prices[-1] - prices[-20]) / prices[-20]
        score += mom * 2

    return max(-1, min(1, score))


def run_backtest(data: dict, model=None, feature_names: list = None):
    """Run backtest comparing strategies."""
    import pandas as pd
    import numpy as np

    results = {
        "rule_based": {"returns": [], "trades": 0, "win_rate": 0},
        "ml_only": {"returns": [], "trades": 0, "win_rate": 0},
        "hybrid": {"returns": [], "trades": 0, "win_rate": 0},
        "buy_hold": {"returns": [], "trades": 0, "win_rate": 0},
    }

    for ticker, bars in data.items():
        if len(bars) < 80:  # Need enough data for warmup + test
            continue

        df = pd.DataFrame(bars)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Test on last 20% of data
        test_start = int(len(df) * 0.8)

        prices_all = df["close"].tolist()

        # Buy & Hold baseline
        bh_return = (prices_all[-1] - prices_all[test_start]) / prices_all[test_start]
        results["buy_hold"]["returns"].append(bh_return)

        # Walk-forward test
        for i in range(test_start, len(df) - 5):  # -5 for forward return
            prices = prices_all[: i + 1]

            if len(prices) < 60:
                continue

            # Rule-based signal
            rb_signal = rule_based_signal(prices)

            # ML signal
            ml_signal = 0
            if model and feature_names:
                features = compute_features_for_row(df, i)
                if features:
                    feature_vec = [features.get(f, 0) for f in feature_names]
                    if len(feature_vec) == len(feature_names):
                        ml_pred = model.predict([feature_vec])[0]
                        ml_signal = max(-1, min(1, ml_pred * 10))  # Scale to -1 to 1

            # Hybrid signal
            hybrid_signal = (
                ml_signal * 0.6 + rb_signal * 0.4 if ml_signal != 0 else rb_signal
            )

            # Forward return (5-day)
            if i + 5 < len(df):
                forward_return = (
                    df.iloc[i + 5]["close"] - df.iloc[i]["close"]
                ) / df.iloc[i]["close"]
            else:
                continue

            # Rule-based trade
            if abs(rb_signal) > 0.1:
                direction = 1 if rb_signal > 0 else -1
                results["rule_based"]["returns"].append(direction * forward_return)
                results["rule_based"]["trades"] += 1
                if direction * forward_return > 0:
                    results["rule_based"]["win_rate"] += 1

            # ML-only trade
            if abs(ml_signal) > 0.1:
                direction = 1 if ml_signal > 0 else -1
                results["ml_only"]["returns"].append(direction * forward_return)
                results["ml_only"]["trades"] += 1
                if direction * forward_return > 0:
                    results["ml_only"]["win_rate"] += 1

            # Hybrid trade
            if abs(hybrid_signal) > 0.1:
                direction = 1 if hybrid_signal > 0 else -1
                results["hybrid"]["returns"].append(direction * forward_return)
                results["hybrid"]["trades"] += 1
                if direction * forward_return > 0:
                    results["hybrid"]["win_rate"] += 1

    # Calculate final metrics
    for strategy in results:
        rets = results[strategy]["returns"]
        if rets:
            results[strategy]["total_return"] = sum(rets)
            results[strategy]["avg_return"] = np.mean(rets)
            results[strategy]["sharpe"] = (
                np.mean(rets) / np.std(rets) if np.std(rets) > 0 else 0
            )
            results[strategy]["max_drawdown"] = min(
                0, min(np.cumsum(rets) - np.maximum.accumulate(np.cumsum(rets)))
            )
            trades = results[strategy]["trades"]
            wins = results[strategy]["win_rate"]
            results[strategy]["win_rate"] = wins / trades if trades > 0 else 0
        else:
            results[strategy]["total_return"] = 0
            results[strategy]["avg_return"] = 0
            results[strategy]["sharpe"] = 0
            results[strategy]["max_drawdown"] = 0

    return results


def print_results(results: dict):
    """Print backtest results in a clean table."""
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)

    header = f"{'Strategy':<15} {'Total Return':>12} {'Avg Return':>12} {'Sharpe':>10} {'Win Rate':>10} {'Trades':>8} {'Max DD':>10}"
    print(header)
    print("-" * 77)

    for strategy, metrics in results.items():
        name = strategy.replace("_", " ").title()
        print(
            f"{name:<15} "
            f"{metrics['total_return']:>+11.2%} "
            f"{metrics['avg_return']:>+11.4%} "
            f"{metrics['sharpe']:>+10.3f} "
            f"{metrics['win_rate']:>9.1%} "
            f"{metrics['trades']:>8d} "
            f"{metrics['max_drawdown']:>+9.2%}"
        )

    print("=" * 70)

    # Winner announcement
    strategies_with_trades = {
        k: v for k, v in results.items() if v["trades"] > 0 and k != "buy_hold"
    }

    if strategies_with_trades:
        best = max(
            strategies_with_trades,
            key=lambda x: x[1]["sharpe"] if x[1]["sharpe"] else 0,
        )
        print(f"\n🏆 Best Sharpe Ratio: {best.replace('_', ' ').title()}")


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Qlib vs Rule-based vs Hybrid"
    )
    parser.add_argument("--data", default="qlib_data", help="Path to market data")
    parser.add_argument(
        "--model", default="models/qlib_technical_model", help="Path to trained model"
    )

    args = parser.parse_args()

    data_path = Path(args.data)
    model_path = Path(args.model)

    print("=" * 60)
    print("Qlib Backtest Comparison")
    print("=" * 60)

    # Load data
    data = load_market_data(data_path)
    if not data:
        sys.exit(1)

    print(f"Loaded {len(data)} tickers")

    # Load model
    model = load_model(model_path)
    feature_names = load_feature_names(model_path) if model else None

    if model:
        print(f"Model loaded: {model_path}")
        print(f"Features: {len(feature_names)}")
    else:
        print("No ML model found — running rule-based vs buy/hold only")

    # Run backtest
    print("\nRunning backtest...")
    results = run_backtest(data, model, feature_names)

    # Print results
    print_results(results)

    # Save results
    output_path = (
        model_path / "backtest_results.json"
        if model
        else data_path / "backtest_results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert numpy types for JSON serialization
    serializable = {}
    for strategy, metrics in results.items():
        serializable[strategy] = {
            k: float(v)
            if isinstance(v, (float, int, bool)) and not isinstance(v, bool)
            else v
            for k, v in metrics.items()
        }

    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)

    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()

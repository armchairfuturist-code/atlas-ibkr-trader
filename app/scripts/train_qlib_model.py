"""Train Qlib ML model on prepared market data.

Trains a LightGBM model using Alpha158 features to predict future returns.

Usage:
    python scripts/train_qlib_model.py [--data qlib_data] [--model models/qlib_technical_model]
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


def check_qlib_available() -> bool:
    """Check if Qlib is installed and compatible."""
    try:
        import qlib

        logger.info(
            f"Qlib available: {qlib.__version__ if hasattr(qlib, '__version__') else 'unknown'}"
        )
        return True
    except ImportError:
        logger.error("Qlib not installed!")
        logger.error("")
        logger.error("Qlib requires Python 3.8-3.12. Your system has Python 3.14.")
        logger.error("")
        logger.error("Options:")
        logger.error("  1. Install Python 3.12: https://www.python.org/downloads/")
        logger.error("  2. Then: pip install pyqlib")
        logger.error("  3. Run this script again")
        logger.error("")
        logger.error("The trading system works fine without Qlib — it uses")
        logger.error("rule-based technical analysis as a fallback.")
        return False


def train_from_json(data_path: Path, model_path: Path):
    """Train model using JSON data (no Qlib binary format needed).

    This is a lightweight approach that:
    1. Loads JSON market data
    2. Computes Alpha158-style features
    3. Trains LightGBM directly (no Qlib init needed)
    """
    try:
        import pandas as pd
        import numpy as np
        from lightgbm import LGBMRegressor
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("pip install pandas numpy lightgbm")
        return False

    # Load data
    json_path = data_path / "market_data.json"
    if not json_path.exists():
        logger.error(f"No market data found at {json_path}")
        logger.error("Run: python scripts/prepare_qlib_data.py first")
        return False

    with open(json_path) as f:
        data = json.load(f)

    logger.info(f"Loaded data for {len(data)} tickers")

    # Build feature matrix
    features_list = []
    labels_list = []

    for ticker, bars in data.items():
        if len(bars) < 60:
            logger.warning(f"Skipping {ticker}: only {len(bars)} bars (need 60+)")
            continue

        df = pd.DataFrame(bars)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Compute features
        close = df["close"]
        volume = df["volume"]

        for i in range(60, len(df)):
            window = df.iloc[:i]
            w_close = window["close"]
            w_vol = window["volume"]

            if len(w_close) < 20:
                continue

            features = {}

            # Returns
            for p in [5, 10, 20, 30, 60]:
                if len(w_close) >= p:
                    features[f"ret_{p}"] = (
                        w_close.iloc[-1] - w_close.iloc[-p]
                    ) / w_close.iloc[-p]

            # Moving averages
            for p in [5, 10, 20, 60]:
                if len(w_close) >= p:
                    ma = w_close.rolling(p).mean().iloc[-1]
                    features[f"ma_{p}_ratio"] = w_close.iloc[-1] / ma if ma > 0 else 1.0

            # Volatility
            for p in [10, 20, 60]:
                if len(w_close) >= p:
                    features[f"vol_{p}"] = (
                        w_close.pct_change().rolling(p).std().iloc[-1]
                    )

            # Volume
            if len(w_vol) >= 20:
                vol_ma5 = w_vol.rolling(5).mean().iloc[-1]
                vol_ma20 = w_vol.rolling(20).mean().iloc[-1]
                features["volume_ratio"] = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0

            # RSI
            if len(w_close) >= 14:
                delta = w_close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                features["rsi_14"] = (
                    100 - (100 / (1 + gain / loss)) if loss > 0 else 100
                )

            # MACD
            if len(w_close) >= 26:
                ema_12 = w_close.ewm(span=12).mean().iloc[-1]
                ema_26 = w_close.ewm(span=26).mean().iloc[-1]
                features["macd"] = ema_12 - ema_26

            # Bollinger Band position
            if len(w_close) >= 20:
                sma_20 = w_close.rolling(20).mean().iloc[-1]
                std_20 = w_close.rolling(20).std().iloc[-1]
                if std_20 > 0:
                    features["bb_position"] = (
                        w_close.iloc[-1] - (sma_20 - 2 * std_20)
                    ) / (4 * std_20)

            # Price position in range
            if len(w_close) >= 20:
                high_20 = w_close.rolling(20).max().iloc[-1]
                low_20 = w_close.rolling(20).min().iloc[-1]
                if high_20 != low_20:
                    features["price_position"] = (w_close.iloc[-1] - low_20) / (
                        high_20 - low_20
                    )

            # Label: 5-day forward return
            if i + 5 < len(df):
                forward_return = (
                    df.iloc[i + 5]["close"] - df.iloc[i]["close"]
                ) / df.iloc[i]["close"]
            else:
                continue

            features_list.append(features)
            labels_list.append(forward_return)

    if not features_list:
        logger.error("No features generated. Check your data.")
        return False

    # Build DataFrame
    feature_df = pd.DataFrame(features_list).fillna(0)
    label_series = pd.Series(labels_list)

    logger.info(f"Feature matrix: {feature_df.shape}")
    logger.info(f"Label range: [{label_series.min():.4f}, {label_series.max():.4f}]")

    # Train/test split (80/20 chronological)
    split_idx = int(len(feature_df) * 0.8)
    X_train = feature_df.iloc[:split_idx]
    X_test = feature_df.iloc[split_idx:]
    y_train = label_series.iloc[:split_idx]
    y_test = label_series.iloc[split_idx:]

    # Train LightGBM
    logger.info("Training LightGBM model...")
    model = LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=8,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
    )

    # Evaluate
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Directional accuracy
    correct_direction = sum(
        1 for actual, pred in zip(y_test, y_pred) if (actual > 0) == (pred > 0)
    )
    directional_accuracy = correct_direction / len(y_test) if len(y_test) > 0 else 0

    logger.info(f"Test MSE:  {mse:.6f}")
    logger.info(f"Test MAE:  {mae:.6f}")
    logger.info(f"Test R²:   {r2:.4f}")
    logger.info(f"Directional Accuracy: {directional_accuracy:.1%}")

    # Save model
    import joblib

    model_path.mkdir(parents=True, exist_ok=True)
    model_file = model_path / "model.pkl"
    joblib.dump(model, model_file)
    logger.info(f"Model saved to {model_file}")

    # Save feature names
    feature_names = list(feature_df.columns)
    features_file = model_path / "feature_names.json"
    with open(features_file, "w") as f:
        json.dump(feature_names, f)
    logger.info(f"Feature names saved to {features_file}")

    # Save evaluation metrics
    metrics = {
        "mse": mse,
        "mae": mae,
        "r2": r2,
        "directional_accuracy": directional_accuracy,
        "n_samples": len(feature_df),
        "n_features": len(feature_df.columns),
        "n_tickers": len(data),
    }
    metrics_file = model_path / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics saved to {metrics_file}")

    # Feature importance
    importance = dict(zip(feature_df.columns, model.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
    logger.info("\nTop 15 Feature Importances:")
    for feat, imp in top_features:
        logger.info(f"  {feat}: {imp}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Train Qlib ML model")
    parser.add_argument(
        "--data", default="qlib_data", help="Path to prepared data directory"
    )
    parser.add_argument(
        "--model", default="models/qlib_technical_model", help="Path to save model"
    )
    parser.add_argument(
        "--qlib-mode",
        action="store_true",
        help="Use full Qlib pipeline (requires Qlib installed)",
    )

    args = parser.parse_args()

    data_path = Path(args.data)
    model_path = Path(args.model)

    print("=" * 60)
    print("Qlib Model Training")
    print("=" * 60)
    print(f"Data: {data_path}")
    print(f"Model output: {model_path}")
    print()

    if args.qlib_mode:
        # Full Qlib pipeline
        if not check_qlib_available():
            sys.exit(1)

        from app.models.qlib_trainer import QlibModelTrainer

        trainer = QlibModelTrainer(model_path=str(model_path))
        model = trainer.train_model(verbose=True)

        if model:
            trainer.save_model()
            print("\n✓ Qlib model trained and saved!")
        else:
            print("\n✗ Training failed")
            sys.exit(1)
    else:
        # Lightweight training (no Qlib needed, just LightGBM)
        print("Using lightweight training mode (LightGBM only)")
        print("(No Qlib binary format required)")
        print()

        success = train_from_json(data_path, model_path)

        if success:
            print("\n✓ Model trained and saved!")
            print(f"\nNext step: Run the trading system")
            print(
                f"  python integrated_trading_system.py --tickers XLE XAR --theme iran"
            )
        else:
            print("\n✗ Training failed")
            sys.exit(1)


if __name__ == "__main__":
    main()

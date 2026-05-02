"""Qlib model trainer — trains ML models for price prediction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class QlibModelTrainer:
    """Trains Qlib LightGBM model for technical price prediction.

    Uses Qlib's Alpha158 feature set (158 pre-built alpha factors)
    to predict future returns. Falls back gracefully if Qlib is unavailable.
    """

    def __init__(
        self,
        model_path: str = "models/qlib_technical_model",
        instruments: str = "SP500",
        train_start: str = "2020-01-01",
        train_end: str = "2023-12-31",
        valid_end: str = "2024-06-30",
        test_end: str = "2025-12-31",
    ):
        """Initialize trainer with configuration.

        Args:
            model_path: Where to save/load the trained model
            instruments: Qlib instrument universe
            train_start: Training start date
            train_end: Training end date
            valid_end: Validation end date
            test_end: Test end date
        """
        self.model_path = model_path
        self.instruments = instruments
        self.train_start = train_start
        self.train_end = train_end
        self.valid_end = valid_end
        self.test_end = test_end
        self._model = None
        self._dataset = None
        self._qlib_available = False

    def _check_qlib(self) -> bool:
        """Check if Qlib is available."""
        try:
            import qlib

            return True
        except ImportError:
            logger.warning(
                "Qlib not installed. pip install pyqlib (requires Python 3.8-3.12)"
            )
            return False

    def prepare_dataset(self):
        """Prepare Qlib dataset with Alpha158 features.

        Returns:
            DatasetH instance or None if Qlib unavailable
        """
        if not self._check_qlib():
            return None

        try:
            from qlib.data.dataset import DatasetH
            from qlib.contrib.data.handler import Alpha158

            handler = Alpha158(
                instruments=self.instruments,
                start_time=self.train_start,
                end_time=self.test_end,
                fit_start_time=self.train_start,
                fit_end_time=self.train_end,
            )

            dataset = DatasetH(
                handler=handler,
                segments={
                    "train": (self.train_start, self.train_end),
                    "valid": (self.train_end, self.valid_end),
                    "test": (self.valid_end, self.test_end),
                },
            )

            self._dataset = dataset
            logger.info(f"Dataset prepared: {len(handler)} samples")
            return dataset

        except Exception as e:
            logger.error(f"Failed to prepare dataset: {e}")
            return None

    def train_model(self, dataset=None, verbose: bool = True):
        """Train LightGBM model on prepared dataset.

        Args:
            dataset: Qlib DatasetH (prepared if None)
            verbose: Whether to print training progress

        Returns:
            Trained model or None if training failed
        """
        if dataset is None:
            dataset = self.prepare_dataset()

        if dataset is None:
            logger.warning("No dataset available, skipping training")
            return None

        try:
            from qlib.contrib.model.gbdt import LGBModel

            model = LGBModel(
                loss="mse",
                num_leaves=64,
                learning_rate=0.05,
                max_depth=8,
                num_boost_round=1000,
                early_stopping_rounds=50,
                verbose_eval=10 if verbose else 0,
            )

            logger.info("Training LightGBM model...")
            model.fit(dataset, verbose_eval=10 if verbose else 0)

            self._model = model
            logger.info("Training complete")
            return model

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return None

    def predict(self, tickers: list[str], dataset=None):
        """Get predictions for specific tickers.

        Args:
            tickers: List of stock symbols
            dataset: Qlib DatasetH (uses cached if None)

        Returns:
            pandas.Series with MultiIndex (instrument, datetime) of predicted returns
        """
        if self._model is None:
            logger.warning("No trained model available")
            return None

        if dataset is None:
            dataset = self._dataset

        if dataset is None:
            logger.warning("No dataset available")
            return None

        try:
            predictions = self._model.predict(dataset, segment="test")

            # Filter to requested tickers
            if predictions is not None and hasattr(
                predictions.index, "get_level_values"
            ):
                all_instruments = (
                    predictions.index.get_level_values(0).unique().tolist()
                )
                matching = [t for t in tickers if t in all_instruments]
                if matching:
                    return predictions.loc[matching]
                return predictions

            return predictions

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def save_model(self, path: Optional[str] = None):
        """Save trained model to disk."""
        if self._model is None:
            logger.warning("No model to save")
            return False

        save_path = path or self.model_path
        try:
            Path(save_path).mkdir(parents=True, exist_ok=True)
            self._model.save(save_path)
            logger.info(f"Model saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, path: Optional[str] = None):
        """Load trained model from disk."""
        load_path = path or self.model_path

        if not self._check_qlib():
            return False

        if not Path(load_path).exists():
            logger.warning(f"No model found at {load_path}")
            return False

        try:
            from qlib.contrib.model.gbdt import LGBModel

            model = LGBModel()
            model.load(load_path)
            self._model = model
            logger.info(f"Model loaded from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def evaluate(self, dataset=None):
        """Evaluate model performance on test set.

        Returns:
            Dict with evaluation metrics or None
        """
        if self._model is None:
            return None

        if dataset is None:
            dataset = self._dataset

        if dataset is None:
            return None

        try:
            from qlib.contrib.evaluate import backtest_daily, risk_analysis

            # Get predictions
            pred = self._model.predict(dataset, segment="test")

            if pred is None:
                return None

            # Run backtest
            report = backtest_daily(
                start_time=self.valid_end,
                end_time=self.test_end,
                strategy={"class": "TopkDropoutStrategy"},
                benchmark="SH000300",
            )

            # Calculate risk metrics
            risk = risk_analysis(report["return"])

            return {
                "annualized_return": risk.get("annualized_return", 0),
                "information_ratio": risk.get("information_ratio", 0),
                "max_drawdown": risk.get("max_drawdown", 0),
            }

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return None

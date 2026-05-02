"""Qlib ML model adapter — drop-in replacement for SophisticatedTechnicalAnalyzer.

Uses Microsoft Qlib's trained LightGBM model for price prediction.
Falls back to rule-based SophisticatedTechnicalAnalyzer when Qlib is unavailable.

Interface: Identical to SophisticatedTechnicalAnalyzer.analyze()
Output: EnsembleResult (same dataclass)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum
from pathlib import Path

from app.agents.technical_agent import TechnicalSignal
from app.agents.sophisticated_technical import (
    SophisticatedTechnicalAnalyzer,
    EnsembleResult,
    StrategySignal,
    TechnicalStrategy,
)

logger = logging.getLogger(__name__)


class QlibModelAdapter:
    """Qlib-based technical analysis with graceful fallback.

    Drop-in replacement for SophisticatedTechnicalAnalyzer.
    When Qlib is available and trained: uses ML predictions.
    When Qlib is unavailable: falls back to rule-based ensemble.
    """

    def __init__(
        self,
        model_path: str = "models/qlib_technical_model",
        qlib_provider_uri: Optional[str] = None,
        fallback_weight: float = 0.4,
        qlib_weight: float = 0.6,
    ):
        """Initialize Qlib adapter.

        Args:
            model_path: Path to trained Qlib model
            qlib_provider_uri: Path to Qlib binary data store
            fallback_weight: Weight for rule-based fallback (0-1)
            qlib_weight: Weight for Qlib ML predictions (0-1)
        """
        self.model_path = model_path
        self.qlib_provider_uri = qlib_provider_uri
        self.fallback_weight = fallback_weight
        self.qlib_weight = qlib_weight
        self._qlib_available = False
        self._model = None
        self._fallback = SophisticatedTechnicalAnalyzer()

        # Try to initialize Qlib
        self._try_init_qlib()

    def _try_init_qlib(self):
        """Attempt to initialize Qlib. Sets _qlib_available flag."""
        try:
            import qlib

            provider_uri = self.qlib_provider_uri or str(
                Path(__file__).parent.parent.parent / "qlib_data"
            )
            if Path(provider_uri).exists():
                qlib.init(provider_uri=provider_uri, region="us")
                self._qlib_available = True
                logger.info("Qlib initialized successfully")

                # Try to load trained model
                if Path(self.model_path).exists():
                    try:
                        from qlib.contrib.model.gbdt import LGBModel

                        model = LGBModel()
                        model.load(self.model_path)
                        self._model = model
                        logger.info(f"Qlib model loaded from {self.model_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load Qlib model: {e}")
                else:
                    logger.info(
                        "No trained Qlib model found at %s — using Qlib features with fallback",
                        self.model_path,
                    )
            else:
                logger.info(
                    "Qlib data directory not found at %s — using fallback mode",
                    provider_uri,
                )
        except ImportError:
            logger.info(
                "Qlib not installed (requires Python 3.8-3.12). Using rule-based fallback."
            )
        except Exception as e:
            logger.warning(f"Qlib init failed: {e}. Using rule-based fallback.")

    def analyze(
        self,
        prices: list[float],
        volumes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> EnsembleResult:
        """Run technical analysis on price data.

        Hybrid approach:
        - Qlib prediction (60% weight) + Rule-based fallback (40% weight)
        - If Qlib unavailable: 100% rule-based

        Args:
            prices: List of closing prices
            volumes: List of volume data
            highs: Optional list of high prices
            lows: Optional list of low prices

        Returns:
            EnsembleResult with composite signal and confidence
        """
        # Always get fallback result (rule-based baseline)
        fallback_result = self._fallback.analyze(prices, volumes, highs, lows)

        if not self._qlib_available or self._model is None:
            # Qlib unavailable — return pure rule-based result
            return fallback_result

        # Try Qlib prediction
        qlib_result = self._qlib_analyze(prices, volumes, highs, lows)

        if qlib_result is None:
            # Qlib prediction failed — return fallback
            return fallback_result

        # Hybrid: blend Qlib + rule-based
        return self._hybrid_ensemble(qlib_result, fallback_result)

    def _qlib_analyze(
        self,
        prices: list[float],
        volumes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> Optional[EnsembleResult]:
        """Run Qlib ML prediction on price data.

        Converts price data to Qlib features, runs model inference,
        and maps predicted return to TechnicalSignal.
        """
        try:
            import pandas as pd

            # Build feature DataFrame
            n = len(prices)
            if n < 60:
                return None

            dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)

            df = pd.DataFrame(
                {
                    "close": prices,
                    "volume": volumes,
                    "high": highs if highs else [p * 1.01 for p in prices],
                    "low": lows if lows else [p * 0.99 for p in prices],
                    "open": prices,
                },
                index=dates,
            )

            # Compute Alpha158-style features manually (since we may not have full Qlib data)
            features = self._compute_alpha_features(df)

            # Predict using model
            if self._model is None:
                return None

            # Use model's predict method
            feature_df = pd.DataFrame([features])
            prediction = self._model.predict(feature_df)

            if prediction is None or len(prediction) == 0:
                return None

            predicted_return = (
                float(prediction.iloc[-1])
                if hasattr(prediction, "iloc")
                else float(prediction)
            )

            # Map predicted return to signal
            signal, confidence = self._return_to_signal(predicted_return, prices)

            # Build strategy signals (simulate Qlib's internal breakdown)
            strategy_signals = self._build_qlib_strategy_signals(predicted_return, df)

            reasoning = (
                f"Qlib ML Prediction: {predicted_return:+.2%} expected return\n"
                f"  Signal: {signal.value} (confidence: {confidence:.0%})\n"
                f"  Model: LightGBM on Alpha158 features"
            )

            return EnsembleResult(
                composite_signal=signal,
                composite_confidence=confidence,
                strategy_signals=strategy_signals,
                weights={TechnicalStrategy.TREND: self.qlib_weight},
                reasoning=reasoning,
            )

        except Exception as e:
            logger.warning(f"Qlib prediction failed: {e}")
            return None

    def _compute_alpha_features(self, df) -> dict:
        """Compute Alpha158-style features from price DataFrame.

        These mimic Qlib's Alpha158 feature set for model compatibility.
        """
        close = df["close"]
        volume = df["volume"]

        features = {}

        # Price-based features
        for period in [5, 10, 20, 30, 60]:
            if len(close) >= period:
                # Returns
                features[f"RET_{period}"] = close.pct_change(period).iloc[-1]
                # Moving averages
                features[f"MA_{period}"] = close.rolling(period).mean().iloc[-1]
                # Volatility
                features[f"STD_{period}"] = (
                    close.pct_change().rolling(period).std().iloc[-1]
                )

        # Volume features
        for period in [5, 10, 20]:
            if len(volume) >= period:
                features[f"VOLUME_MA_{period}"] = volume.rolling(period).mean().iloc[-1]

        # Price-position features
        if len(close) >= 20:
            high_20 = close.rolling(20).max().iloc[-1]
            low_20 = close.rolling(20).min().iloc[-1]
            if high_20 != low_20:
                features["PRICE_POSITION"] = (close.iloc[-1] - low_20) / (
                    high_20 - low_20
                )

        # Momentum features
        if len(close) >= 10:
            features["MOM_10"] = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
            features["MOM_20"] = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]

        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            if loss > 0:
                features["RSI_14"] = 100 - (100 / (1 + gain / loss))
            else:
                features["RSI_14"] = 100

        # MACD
        if len(close) >= 26:
            ema_12 = close.ewm(span=12).mean().iloc[-1]
            ema_26 = close.ewm(span=26).mean().iloc[-1]
            features["MACD"] = ema_12 - ema_26

        # Volume ratio
        if len(volume) >= 20:
            vol_ma_5 = volume.rolling(5).mean().iloc[-1]
            vol_ma_20 = volume.rolling(20).mean().iloc[-1]
            if vol_ma_20 > 0:
                features["VOLUME_RATIO"] = vol_ma_5 / vol_ma_20

        # Label (target): future return (for training context)
        features["LABEL"] = 0  # Placeholder for inference

        return features

    def _return_to_signal(
        self, predicted_return: float, prices: list[float]
    ) -> Tuple[TechnicalSignal, float]:
        """Map predicted return to TechnicalSignal and confidence.

        Args:
            predicted_return: Expected return from Qlib model (e.g., 0.05 = +5%)
            prices: Current price series

        Returns:
            (TechnicalSignal, confidence 0-1)
        """
        abs_return = abs(predicted_return)

        # Scale confidence based on prediction magnitude
        # Qlib predictions are typically small (-0.1 to +0.1)
        # Map to confidence: 0.01 → 0.3, 0.05 → 0.7, 0.10 → 0.9
        confidence = min(0.95, 0.3 + abs_return * 8)
        confidence = max(0.3, confidence)

        # Map to signal
        if predicted_return > 0.05:
            signal = TechnicalSignal.STRONG_BUY
        elif predicted_return > 0.02:
            signal = TechnicalSignal.BUY
        elif predicted_return > 0.005:
            signal = TechnicalSignal.BUY
            confidence *= 0.7  # Reduce confidence for weak signals
        elif predicted_return < -0.05:
            signal = TechnicalSignal.STRONG_SELL
        elif predicted_return < -0.02:
            signal = TechnicalSignal.SELL
        elif predicted_return < -0.005:
            signal = TechnicalSignal.SELL
            confidence *= 0.7
        else:
            signal = TechnicalSignal.HOLD
            confidence = max(0.3, confidence * 0.5)

        return signal, confidence

    def _build_qlib_strategy_signals(
        self, predicted_return: float, df
    ) -> list[StrategySignal]:
        """Build strategy signal breakdown from Qlib prediction.

        Simulates the multi-strategy breakdown that the portfolio manager expects.
        """
        close = df["close"]
        abs_ret = abs(predicted_return)

        # Decompose prediction into strategy-like components
        signals = []

        # Trend component (based on recent momentum)
        if len(close) >= 20:
            mom_20 = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]
            trend_signal = TechnicalSignal.BUY if mom_20 > 0 else TechnicalSignal.SELL
            trend_conf = min(0.9, 0.4 + abs(mom_20) * 5)
            signals.append(
                StrategySignal(
                    strategy=TechnicalStrategy.TREND,
                    signal=trend_signal,
                    confidence=trend_conf,
                    metrics={
                        "predicted_return": round(predicted_return, 4),
                        "momentum_20": round(mom_20, 4),
                    },
                )
            )

        # Mean reversion component
        if len(close) >= 20:
            sma_20 = close.rolling(20).mean().iloc[-1]
            z_score = (
                (close.iloc[-1] - sma_20) / close.rolling(20).std().iloc[-1]
                if close.rolling(20).std().iloc[-1] > 0
                else 0
            )
            mr_signal = (
                TechnicalSignal.BUY
                if z_score < -1
                else (TechnicalSignal.SELL if z_score > 1 else TechnicalSignal.HOLD)
            )
            signals.append(
                StrategySignal(
                    strategy=TechnicalStrategy.MEAN_REVERSION,
                    signal=mr_signal,
                    confidence=min(0.8, 0.3 + abs(z_score) * 0.15),
                    metrics={"z_score": round(z_score, 2)},
                )
            )

        # Momentum component
        if len(close) >= 10:
            mom_10 = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
            mom_signal = (
                TechnicalSignal.BUY
                if mom_10 > 0.02
                else (TechnicalSignal.SELL if mom_10 < -0.02 else TechnicalSignal.HOLD)
            )
            signals.append(
                StrategySignal(
                    strategy=TechnicalStrategy.MOMENTUM,
                    signal=mom_signal,
                    confidence=min(0.85, 0.4 + abs(mom_10) * 5),
                    metrics={"momentum_10": round(mom_10, 4)},
                )
            )

        # Volatility component
        if len(close) >= 20:
            vol_20 = close.pct_change().rolling(20).std().iloc[-1]
            vol_signal = TechnicalSignal.HOLD
            vol_conf = 0.5
            signals.append(
                StrategySignal(
                    strategy=TechnicalStrategy.VOLATILITY,
                    signal=vol_signal,
                    confidence=vol_conf,
                    metrics={"volatility_20d": round(vol_20 * 100, 2)},
                )
            )

        # Statistical arb component
        if len(close) >= 50:
            returns = close.pct_change().dropna()
            skew = returns.skew()
            signals.append(
                StrategySignal(
                    strategy=TechnicalStrategy.STAT_ARB,
                    signal=TechnicalSignal.HOLD,
                    confidence=0.4,
                    metrics={"skewness": round(skew, 3) if not math.isnan(skew) else 0},
                )
            )

        return signals

    def _hybrid_ensemble(
        self,
        qlib_result: EnsembleResult,
        fallback_result: EnsembleResult,
    ) -> EnsembleResult:
        """Blend Qlib ML prediction with rule-based fallback.

        Weighted combination:
        - Qlib weight (default 60%): ML-powered prediction
        - Fallback weight (default 40%): Rule-based safety net
        """
        # Map signals to numeric scores
        signal_scores = {
            TechnicalSignal.STRONG_BUY: 90,
            TechnicalSignal.BUY: 60,
            TechnicalSignal.HOLD: 0,
            TechnicalSignal.SELL: -60,
            TechnicalSignal.STRONG_SELL: -90,
            TechnicalSignal.SHORT: -75,
        }

        qlib_score = (
            signal_scores.get(qlib_result.composite_signal, 0)
            * qlib_result.composite_confidence
        )
        fallback_score = (
            signal_scores.get(fallback_result.composite_signal, 0)
            * fallback_result.composite_confidence
        )

        # Weighted blend
        hybrid_score = (
            qlib_score * self.qlib_weight + fallback_score * self.fallback_weight
        )

        # Map back to signal
        abs_score = abs(hybrid_score)
        confidence = min(0.95, abs_score / 90)

        if hybrid_score > 45:
            composite = TechnicalSignal.STRONG_BUY
        elif hybrid_score > 20:
            composite = TechnicalSignal.BUY
        elif hybrid_score < -45:
            composite = TechnicalSignal.STRONG_SELL
        elif hybrid_score < -20:
            composite = TechnicalSignal.SELL
        else:
            composite = TechnicalSignal.HOLD
            confidence = max(0.3, confidence * 0.5)

        # Combine reasoning
        reasoning = (
            f"Hybrid Signal (Qlib {self.qlib_weight:.0%} + Rule-based {self.fallback_weight:.0%})\n"
            f"\n--- Qlib ML ---\n{qlib_result.reasoning}"
            f"\n\n--- Rule-Based Fallback ---\n{fallback_result.reasoning}"
            f"\n\n--- Hybrid Result ---\n"
            f"Composite Score: {hybrid_score:+.1f}\n"
            f"Signal: {composite.value} (confidence: {confidence:.0%})"
        )

        # Combine strategy signals (Qlib + fallback)
        combined_signals = (
            qlib_result.strategy_signals + fallback_result.strategy_signals
        )

        # Combined weights
        combined_weights = {**qlib_result.weights, **fallback_result.weights}

        return EnsembleResult(
            composite_signal=composite,
            composite_confidence=confidence,
            strategy_signals=combined_signals,
            weights=combined_weights,
            reasoning=reasoning,
        )

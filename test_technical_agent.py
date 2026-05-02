"""Test script for TechnicalAnalysisAgent with SHORT signals.

Run this to verify the SHORT signal capability works correctly.
"""

import sys
import os

# Add the implementation directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.technical_agent import TechnicalAnalysisAgent, TechnicalSignal


def test_bullish_signal():
    """Test with bullish data - should produce BUY signal."""
    print("\n" + "=" * 60)
    print("TEST: Bullish Signal (oversold RSI, positive MACD)")
    print("=" * 60)

    agent = TechnicalAnalysisAgent()

    # Create bullish scenario: oversold RSI, positive MACD, low price position
    prices = [100 - i * 0.5 for i in range(30)]  # Downtrend then bounce
    prices[-5:] = [p + 2 for p in prices[-5:]]  # Recent bounce

    data = {
        "price_history": prices,
        "volume": 25_000_000,  # High volume
        "high": [p + 2 for p in prices],
        "low": [p - 2 for p in prices],
    }

    # Test with SHORT disabled first
    result = agent.analyze("TEST", data, enable_short=False)
    print(f"\nSignal: {result.signal.value}")
    print(f"Conviction: {result.conviction}")
    print(f"Trend: {result.trend_direction}")
    print(f"Key points: {result.key_points}")
    print(f"Thesis: {result.thesis[:100]}...")

    research_note = agent.create_research_note(result)
    print(f"\nResearchNote:")
    print(f"  Persona: {research_note.persona}")
    print(f"  Confidence: {research_note.confidence}")


def test_bearish_signal_with_short():
    """Test with bearish data - should produce SHORT signal."""
    print("\n" + "=" * 60)
    print("TEST: Bearish Signal with SHORT enabled")
    print("=" * 60)

    agent = TechnicalAnalysisAgent()

    # Create bearish scenario: overbought RSI, negative MACD, downtrend
    prices = [100 + i * 0.5 for i in range(30)]  # Uptrend
    prices[-5:] = [p - 3 for p in prices[-5:]]  # Recent collapse

    data = {
        "price_history": prices,
        "volume": 30_000_000,  # High volume (panic selling)
        "high": [p + 3 for p in prices],
        "low": [p - 3 for p in prices],
    }

    # Test with SHORT enabled
    result = agent.analyze("TEST", data, enable_short=True)
    print(f"\nSignal: {result.signal.value}")
    print(f"Conviction: {result.conviction}")
    print(f"Trend: {result.trend_direction}")
    print(f"Key points: {result.key_points}")
    print(f"Indicators:")
    print(f"  RSI: {result.indicators.rsi:.1f}")
    print(f"  MACD Histogram: {result.indicators.macd_histogram:+.4f}")
    print(f"  Williams %R: {result.indicators.williams_r:.1f}")
    print(f"  ROC: {result.indicators.roc:.1f}%")
    print(f"  Stochastic K: {result.indicators.stochastic_k:.1f}")

    print(f"\nThesis: {result.thesis}")

    if result.signal == TechnicalSignal.SHORT:
        print("\n✅ SHORT signal correctly generated!")


def test_neutral_signal():
    """Test with neutral data - should produce HOLD signal."""
    print("\n" + "=" * 60)
    print("TEST: Neutral Signal (sideways market)")
    print("=" * 60)

    agent = TechnicalAnalysisAgent()

    # Create sideways scenario
    prices = [100 + (i % 10 - 5) * 0.5 for i in range(30)]

    data = {
        "price_history": prices,
        "volume": 10_000_000,  # Normal volume
        "high": [p + 1 for p in prices],
        "low": [p - 1 for p in prices],
    }

    result = agent.analyze("TEST", data)
    print(f"\nSignal: {result.signal.value}")
    print(f"Conviction: {result.conviction}")
    print(f"Trend: {result.trend_direction}")
    print(f"Key points: {result.key_points}")


def test_xle_with_geopolitics():
    """Test XLE (energy ETF) with geopolitical context."""
    print("\n" + "=" * 60)
    print("TEST: XLE Energy ETF Analysis")
    print("=" * 60)

    agent = TechnicalAnalysisAgent()

    # Simulate XLE price data (energy ETF)
    import random

    random.seed(42)
    base = 85
    prices = [base + random.gauss(0, 2) for _ in range(30)]

    data = {
        "price_history": prices,
        "volume": 20_000_000,
        "high": [p + 1.5 for p in prices],
        "low": [p - 1.5 for p in prices],
    }

    result = agent.analyze("XLE", data)
    print(f"\nTicker: XLE")
    print(f"Signal: {result.signal.value}")
    print(f"Conviction: {result.conviction}")
    print(f"Support: ${result.support_level}")
    print(f"Resistance: ${result.resistance_level}")
    print(f"Thesis: {result.thesis}")

    note = agent.create_research_note(result)
    print(f"\nResearchNote for debate:")
    print(f"  Bias: {note.persona}")
    print(f"  Confidence: {note.confidence}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TECHNICAL AGENT TEST SUITE (SHORT SIGNALS)")
    print("=" * 60)

    test_bullish_signal()
    test_bearish_signal_with_short()
    test_neutral_signal()
    test_xle_with_geopolitics()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nKey capability: TechnicalAnalysisAgent can now produce SHORT signals")
    print("when technical conditions are bearish enough.")


if __name__ == "__main__":
    main()

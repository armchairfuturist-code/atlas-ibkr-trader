"""Test script for GeopoliticalSentimentAgent integration.

Run this to verify the Polymarket integration works correctly.
"""

import sys
import os

# Add the implementation directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.debate_orchestrator import DebateOrchestrator
from app.agents.geopolitical_agent import GeopoliticalSentimentAgent, geopolitical_agent
from app.data.polymarket_client import PolymarketClient


def test_polymarket_client():
    """Test the Polymarket client can fetch data."""
    print("\n" + "=" * 60)
    print("TEST: Polymarket Client")
    print("=" * 60)

    client = PolymarketClient()

    # Test search
    print("\n1. Testing market search for 'Iran'...")
    try:
        markets = client.search_markets("Iran", limit=5)
        if markets:
            print(f"   Found {len(markets)} markets:")
            for m in markets[:3]:
                print(f"   - {m.get('question', 'Unknown')[:60]}...")
                print(f"     YES: {m.get('yes_probability', 0):.1%}")
        else:
            print("   No markets found (API might be rate-limited)")
    except Exception as e:
        print(f"   Error: {e}")

    # Test geopolitical markets
    print("\n2. Testing geopolitical markets fetch...")
    try:
        geo_markets = client.get_geopolitical_markets()
        if geo_markets:
            print(f"   Found {len(geo_markets)} geopolitical markets")
        else:
            print("   No geopolitical markets found")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n   Client test complete.")


def test_geopolitical_agent():
    """Test the GeopoliticalSentimentAgent."""
    print("\n" + "=" * 60)
    print("TEST: Geopolitical Sentiment Agent")
    print("=" * 60)

    agent = GeopoliticalSentimentAgent()

    print("\n1. Testing analyze()...")
    try:
        signal = agent.analyze()
        print(f"   Event: {signal.event}")
        print(f"   Probability: {signal.probability:.1%}")
        print(f"   Confidence: {signal.confidence:.1%}")
        print(f"   Markets analyzed: {signal.markets_analyzed}")
        if signal.sector_weights:
            print(f"   Sector weights:")
            for sector, weight in sorted(
                signal.sector_weights.items(), key=lambda x: abs(x[1]), reverse=True
            ):
                direction = "BULLISH" if weight > 0 else "BEARISH"
                print(f"     - {sector}: {direction} ({weight:+.2f})")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n2. Testing analyze_specific('iran')...")
    try:
        signal = agent.analyze_specific("iran")
        print(f"   Event: {signal.event}")
        print(f"   Thesis: {signal.thesis[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")


def test_debate_orchestrator_with_geopolitics():
    """Test DebateOrchestrator with geopolitical integration."""
    print("\n" + "=" * 60)
    print("TEST: Debate Orchestrator with Geopolitics")
    print("=" * 60)

    # Create orchestrator with geopolitics enabled
    orchestrator = DebateOrchestrator(
        max_rounds=1,
        include_geopolitics=True,
    )

    print("\n1. Testing get_debate_summary()...")
    summary = orchestrator.get_debate_summary()
    print(f"   Max rounds: {summary['max_rounds']}")
    print(f"   Include geopolitics: {summary['include_geopolitics']}")
    print(f"   Researcher types: {summary['researcher_types']}")

    print("\n2. Testing run_debate() with mock data...")
    # Mock data for testing (matching expected format)
    mock_data = {
        "price_history": [100 + i for i in range(30)],  # 30 days of prices
        "volume": 15_000_000,  # Single value for volume
        "indicators": {
            "rsi": 55,
            "macd": {"signal": 1.2, "histogram": 0.3},
        },
        "news": [
            {"title": "Iran tensions rise", "sentiment": "negative"},
            {"title": "Oil prices stabilize", "sentiment": "neutral"},
        ],
        "fundamentals": {
            "pe_ratio": 15.5,
            "market_cap": 1000000000,
        },
    }

    try:
        plan = orchestrator.run_debate("XLE", mock_data, sector_filter=["ENERGY"])
        print(f"   Ticker: {plan.ticker}")
        print(f"   Rating: {plan.rating.value}")
        print(f"   Conviction: {plan.conviction}")
        print(f"   Thesis: {plan.thesis[:200]}...")
        print(f"   Key insights: {plan.key_insights[:2]}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test without geopolitics for comparison
    print("\n3. Testing run_debate() WITHOUT geopolitics...")
    orchestrator_no_geo = DebateOrchestrator(
        max_rounds=1,
        include_geopolitics=False,
    )
    try:
        plan = orchestrator_no_geo.run_debate("XLE", mock_data)
        print(f"   Ticker: {plan.ticker}")
        print(f"   Rating: {plan.rating.value}")
        print(f"   Conviction: {plan.conviction}")
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GEOPOLITICAL INTEGRATION TEST SUITE")
    print("=" * 60)

    test_polymarket_client()
    test_geopolitical_agent()
    test_debate_orchestrator_with_geopolitics()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

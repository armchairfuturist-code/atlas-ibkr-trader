"""Test script for autopredict adapter integration.

Run this to verify the Polymarket execution integration works correctly.
"""

import sys
import os

# Add the implementation directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.execution.autopredict_adapter import (
    AutopredictAdapter,
    FairProbabilityEstimate,
    TradeDecision,
)


def test_fair_probability_estimates():
    """Test generating fair probability estimates."""
    print("\n" + "=" * 60)
    print("TEST: Fair Probability Estimates")
    print("=" * 60)

    adapter = AutopredictAdapter()

    print("\n1. Testing generate_fair_prob_estimates()...")
    estimates = adapter.generate_fair_prob_estimates()

    if estimates:
        print(f"   Generated {len(estimates)} estimates:")
        for est in estimates[:3]:
            print(f"   - {est.question[:50]}...")
            print(
                f"     Fair: {est.fair_prob:.1%}, Market: {est.market_prob:.1%}, Edge: {est.edge:+.1%}"
            )
    else:
        print("   No estimates generated (may need Polymarket data)")


def test_trade_evaluation():
    """Test trade evaluation logic."""
    print("\n" + "=" * 60)
    print("TEST: Trade Evaluation Logic")
    print("=" * 60)

    adapter = AutopredictAdapter()

    # Test case 1: Strong buy signal
    print("\n1. Testing BUY YES (positive edge)...")
    estimate1 = FairProbabilityEstimate(
        market_id="test_1",
        question="Test market: Will X happen?",
        fair_prob=0.70,  # Our estimate
        market_prob=0.55,  # Market price
        edge=0.15,  # Strong positive edge
        confidence=80,
        thesis="Strong bullish signal",
        source="test",
    )
    execution1 = adapter.evaluate_trade(estimate1, bankroll=10000)
    print(f"   Decision: {execution1.decision.value}")
    print(f"   Size: ${execution1.size_usd:.0f}")
    print(f"   Order type: {execution1.order_type}")
    print(f"   Rationale:\n   {execution1.rationale}")

    # Test case 2: Buy NO (negative edge)
    print("\n2. Testing BUY NO (negative edge)...")
    estimate2 = FairProbabilityEstimate(
        market_id="test_2",
        question="Test market: Will Y happen?",
        fair_prob=0.40,  # Our estimate
        market_prob=0.65,  # Market overpricing
        edge=-0.25,  # Strong negative edge
        confidence=75,
        thesis="Market overpricing event",
        source="test",
    )
    execution2 = adapter.evaluate_trade(estimate2, bankroll=10000)
    print(f"   Decision: {execution2.decision.value}")
    print(f"   Size: ${execution2.size_usd:.0f}")
    print(f"   Rationale:\n   {execution2.rationale}")

    # Test case 3: Skip (low edge)
    print("\n3. Testing SKIP (insufficient edge)...")
    estimate3 = FairProbabilityEstimate(
        market_id="test_3",
        question="Test market: Will Z happen?",
        fair_prob=0.52,
        market_prob=0.50,
        edge=0.02,  # Below minimum
        confidence=60,
        thesis="Weak signal",
        source="test",
    )
    execution3 = adapter.evaluate_trade(estimate3, bankroll=10000)
    print(f"   Decision: {execution3.decision.value}")
    print(f"   Rationale: {execution3.rationale}")


def test_execution_plan():
    """Test complete execution plan generation."""
    print("\n" + "=" * 60)
    print("TEST: Execution Plan Generation")
    print("=" * 60)

    adapter = AutopredictAdapter()

    print("\n1. Testing get_execution_plan()...")
    plan = adapter.get_execution_plan(theme="iran", bankroll=50000, max_trades=3)

    if plan:
        print(f"\n   Generated {len(plan)} trade recommendations:")
        for i, trade in enumerate(plan, 1):
            print(f"\n   Trade {i}:")
            print(f"     Question: {trade['estimate']['question'][:60]}...")
            print(f"     Decision: {trade['execution']['decision']}")
            print(f"     Size: ${trade['execution']['size_usd']:.0f}")
            print(f"     Edge: {trade['estimate']['edge']:+.1%}")
            print(f"     Score: {trade['combined_score']:.2f}")
    else:
        print(
            "   No trades recommended (may need Polymarket data or insufficient edge)"
        )


def test_position_sizing():
    """Test position sizing logic."""
    print("\n" + "=" * 60)
    print("TEST: Position Sizing")
    print("=" * 60)

    adapter = AutopredictAdapter(min_edge=0.05, bankroll_fraction=0.02)

    print("\n1. Testing position sizing at different bankroll levels...")

    # Small bankroll
    est = FairProbabilityEstimate(
        market_id="test",
        question="Test",
        fair_prob=0.70,
        market_prob=0.55,
        edge=0.15,
        confidence=80,
        thesis="Test",
        source="test",
    )

    for bankroll in [1000, 10000, 100000]:
        exec = adapter.evaluate_trade(est, bankroll=bankroll)
        print(
            f"   Bankroll ${bankroll:,}: Size ${exec.size_usd:.0f} ({exec.size_usd / bankroll * 100:.1f}%)"
        )


def test_edge_calibration():
    """Test edge calibration for different scenarios."""
    print("\n" + "=" * 60)
    print("TEST: Edge Calibration")
    print("=" * 60)

    adapter = AutopredictAdapter()

    print("\n1. Testing fair probability estimation...")

    # Test different question types
    test_questions = [
        ("Will there be a ceasefire in Iran by June?", 0.58),
        ("Will oil hit $100 by March?", 0.75),
        ("Will the US enter Iran by April?", 0.62),
    ]

    for question, market_prob in test_questions:
        fair_prob, confidence, thesis = adapter._estimate_fair_prob(
            question, market_prob
        )
        if fair_prob:
            edge = fair_prob - market_prob
            print(f"\n   Question: {question[:50]}...")
            print(
                f"   Market: {market_prob:.0%}, Fair: {fair_prob:.0%}, Edge: {edge:+.0%}"
            )
            print(f"   Confidence: {confidence}%")
            print(f"   Thesis: {thesis[:60]}...")
        else:
            print(f"\n   Question: {question[:50]}...")
            print(f"   No adjustment (market-conservative)")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AUTOPREDICT ADAPTER TEST SUITE")
    print("=" * 60)

    test_fair_probability_estimates()
    test_trade_evaluation()
    test_execution_plan()
    test_position_sizing()
    test_edge_calibration()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nKey capabilities:")
    print("1. Generates fair_prob estimates from thematic analysis")
    print("2. Evaluates trade opportunities using autopredict logic")
    print("3. Decides BUY_YES, BUY_NO, SKIP, or WAIT")
    print("4. Calculates position sizing based on edge and bankroll")
    print("5. Provides complete execution plans")


if __name__ == "__main__":
    main()

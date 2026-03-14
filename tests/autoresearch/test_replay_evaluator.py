"""Tests for replay evaluator."""
import pytest
from app.autoresearch.replay_evaluator import ReplayEvaluator, ReplayVerdict


def test_replay_evaluator_compares_baseline_and_candidate():
    """ReplayEvaluator should compare baseline vs candidate and return keep/revert."""
    evaluator = ReplayEvaluator()
    
    # Simulated replay results
    baseline_result = {"return_pct": 1.5, "sharpe": 1.2}
    candidate_result = {"return_pct": 2.0, "sharpe": 1.5}
    
    verdict = evaluator.compare(baseline_result, candidate_result)
    
    assert verdict.decision in ["keep", "revert"]
    assert verdict.baseline_return == 1.5
    assert verdict.candidate_return == 2.0


def test_replay_evaluator_rejects_worse_performance():
    """ReplayEvaluator should revert if candidate underperforms."""
    evaluator = ReplayEvaluator()
    
    baseline_result = {"return_pct": 2.0, "sharpe": 1.5}
    candidate_result = {"return_pct": 1.0, "sharpe": 0.8}
    
    verdict = evaluator.compare(baseline_result, candidate_result)
    
    assert verdict.decision == "revert"

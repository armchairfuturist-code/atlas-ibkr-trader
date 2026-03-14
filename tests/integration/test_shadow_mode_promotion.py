"""Tests for shadow mode promotion flow."""
import pytest
from pathlib import Path

from app.autoresearch.decision_memory import DecisionMemory, RunRecord
from app.autoresearch.scorecard import ScorecardEngine
from app.autoresearch.policy_updater import PolicyUpdater
from app.autoresearch.replay_evaluator import ReplayEvaluator


def test_shadow_mode_promotion_flow():
    """Integration test: memory -> scorecard -> mutation -> replay -> verdict."""
    # Step 1: Record runs in memory
    memory = DecisionMemory(Path("/tmp/test_memory.jsonl"))
    
    record = RunRecord(
        run_id="run_001",
        config_version="v1",
        proposals=[{"ticker": "XLK", "direction": "LONG"}],
        rationale="test",
        outcomes={"XLK": {"return_pct": 2.0}},
    )
    memory.append_run(record)
    
    # Step 2: Scorecard evaluates performance
    engine = ScorecardEngine()
    runs = memory.load_runs()
    metrics = engine.score(runs)
    
    assert "XLK" in metrics
    assert metrics["XLK"].hit_rate == 1.0
    
    # Step 3: Policy updater proposes mutation
    updater = PolicyUpdater()
    base_config = {"layer1_macro": {"version": "v1", "agents": {"central_bank": {"weight": 1.0}}}}
    mutation = updater.propose(base_config, "v1")
    
    assert mutation is not None
    
    # Step 4: Replay evaluator decides
    evaluator = ReplayEvaluator()
    verdict = evaluator.compare(
        {"return_pct": 1.5},
        {"return_pct": 2.0}
    )
    
    assert verdict.decision == "keep"

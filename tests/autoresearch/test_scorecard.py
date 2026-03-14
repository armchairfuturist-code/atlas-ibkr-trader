"""Tests for scorecard metrics and versioning."""
import pytest

from app.autoresearch.scorecard import ScorecardEngine, AgentScore
from app.autoresearch.decision_memory import RunRecord


def test_scorecard_computes_agent_hit_rate():
    """Scorecard should compute hit rate per agent from run records."""
    engine = ScorecardEngine()
    
    # Create sample records with outcomes
    records = [
        RunRecord(
            run_id="run_001",
            config_version="v1",
            proposals=[{"ticker": "XLK", "direction": "LONG"}],
            rationale="test",
            outcomes={"XLK": {"return_pct": 2.0}},
        ),
        RunRecord(
            run_id="run_002", 
            config_version="v1",
            proposals=[{"ticker": "XLK", "direction": "LONG"}],
            rationale="test",
            outcomes={"XLK": {"return_pct": -1.0}},
        ),
    ]
    
    metrics = engine.score(records)
    
    # Should have metrics for XLK
    assert "XLK" in metrics
    # Hit rate: 1 out of 2 positive = 0.5
    assert metrics["XLK"].hit_rate == 0.5


def test_versioning_increments_version():
    """Versioning should increment version on promotion."""
    from app.autoresearch.versioning import bump_version, get_version_info
    
    v1 = "v1"
    v2 = bump_version(v1)
    assert v2 == "v2"
    
    info = get_version_info(v2)
    assert info["major"] == 2  # v2 has major=2

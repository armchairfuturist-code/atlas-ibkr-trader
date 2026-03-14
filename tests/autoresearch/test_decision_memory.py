"""Tests for decision memory persistence."""
import pytest
from pathlib import Path

from app.autoresearch.decision_memory import DecisionMemory, RunRecord


def test_decision_memory_persists_run_outputs(tmp_path):
    """DecisionMemory should append and load run records."""
    memory_path = tmp_path / "memory.jsonl"
    memory = DecisionMemory(memory_path)
    
    # Create a sample run record
    record = RunRecord(
        run_id="run_001",
        config_version="v1",
        proposals=[{"ticker": "XLK", "direction": "LONG", "size_pct": 10.0}],
        rationale="Test run",
    )
    
    # Append record
    memory.append_run(record)
    
    # Load and verify
    runs = memory.load_runs()
    assert len(runs) == 1
    assert runs[0].run_id == "run_001"
    assert runs[0].config_version == "v1"


def test_decision_memory_appends_outcomes(tmp_path):
    """DecisionMemory should allow appending realized outcomes."""
    memory_path = tmp_path / "memory.jsonl"
    memory = DecisionMemory(memory_path)
    
    # Add run
    record = RunRecord(
        run_id="run_001",
        config_version="v1",
        proposals=[{"ticker": "XLK", "direction": "LONG"}],
        rationale="Test",
    )
    memory.append_run(record)
    
    # Add outcome
    memory.append_outcome("run_001", {"ticker": "XLK", "return_pct": 2.5})
    
    # Verify
    runs = memory.load_runs()
    assert runs[0].outcomes is not None

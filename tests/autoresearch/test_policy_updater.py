"""Tests for bounded policy updater."""
import pytest
from app.autoresearch.policy_updater import PolicyUpdater, PolicyMutation


def test_policy_updater_proposes_single_mutation():
    """PolicyUpdater should propose exactly one bounded change."""
    updater = PolicyUpdater()
    
    base_config = {
        "layer1_macro": {"version": "v1", "agents": {"central_bank": {"weight": 1.0}}}
    }
    
    mutation = updater.propose(base_config, "v1")
    
    assert mutation is not None
    assert mutation.parameter_path  # Has a parameter path
    assert mutation.old_value is not None
    assert mutation.new_value is not None
    # Bounded change
    assert abs(mutation.new_value - mutation.old_value) <= 0.1


def test_policy_updater_respects_bounds():
    """PolicyUpdater should not exceed min/max bounds."""
    updater = PolicyUpdater()
    
    # Test with extreme values
    base_config = {
        "layer1_macro": {"version": "v1", "agents": {"central_bank": {"weight": 0.05}}}
    }
    
    mutation = updater.propose(base_config, "v1")
    
    # Should not go below min bound
    assert mutation.new_value >= 0.01

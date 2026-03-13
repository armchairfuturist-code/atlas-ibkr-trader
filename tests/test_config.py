"""Tests for config model and paper-only lock."""
import sys
from pathlib import Path
import subprocess

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config, ExecutionMode, load_config_from_file


def test_paper_mode_accepted():
    """Test that paper mode config is accepted."""
    config = load_config_from_file("fixtures/config.paper.yaml")
    assert config.mode == ExecutionMode.PAPER
    assert config.is_paper_only() is True
    
    is_valid, error = config.validate_for_submission()
    assert is_valid is True
    assert error is None


def test_live_mode_blocked():
    """Test that live mode blocks submission."""
    config = load_config_from_file("fixtures/config.live.yaml")
    assert config.mode == ExecutionMode.LIVE
    
    is_valid, error = config.validate_for_submission()
    assert is_valid is False
    assert "live mode blocked" in error


def test_invalid_config_fails():
    """Test that invalid config fails schema validation."""
    import yaml
    from pydantic import ValidationError
    
    # Create invalid config (missing required fields would fail)
    bad_config = """
mode: paper
risk_limits:
  max_gross_leverage: 999  # Invalid - too high
"""
    import io
    try:
        data = yaml.safe_load(io.StringIO(bad_config))
        config = Config(**data)
        # Should have failed validation
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "max_gross_leverage" in str(e)


def test_validate_config_script_paper():
    """Test the validate_config script with paper mode."""
    result = subprocess.run(
        [sys.executable, "-m", "app.tools.validate_config", 
         "--config", "fixtures/config.paper.yaml"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Paper config should pass: {result.stderr}"
    assert "Paper lock enabled: True" in result.stdout


def test_validate_config_script_live():
    """Test the validate_config script with live mode."""
    result = subprocess.run(
        [sys.executable, "-m", "app.tools.validate_config", 
         "--config", "fixtures/config.live.yaml"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode != 0, "Live config should fail"
    assert "live mode blocked" in result.stderr

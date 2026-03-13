"""Tests for ETF universe catalog."""
import sys
import subprocess
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.universe import load_universe, ETFUniverse, ETF, ETFType, Sector


def test_universe_loads():
    """Test that valid universe loads."""
    universe = load_universe("fixtures/universe.valid.yaml")
    assert len(universe.etfs) > 0
    assert universe.version == "1.0"


def test_unlevered_and_levered_present():
    """Test that both unlevered and leveraged ETFs exist."""
    universe = load_universe("fixtures/universe.valid.yaml")
    
    unlevered = [e for e in universe.etfs if e.etf_type == ETFType.UNLEVERED]
    leveraged = [e for e in universe.etfs if "levered" in e.etf_type.value]
    
    assert len(unlevered) > 0, "Need at least one unlevered ETF"
    assert len(leveraged) > 0, "Need at least one leveraged ETF"


def test_get_by_ticker():
    """Test finding ETF by ticker."""
    universe = load_universe("fixtures/universe.valid.yaml")
    
    etf = universe.get_by_ticker("SPY")
    assert etf is not None
    assert etf.name == "SPDR S&P 500 ETF"
    
    # Case insensitive
    etf = universe.get_by_ticker("spy")
    assert etf is not None


def test_get_by_sector():
    """Test filtering by sector."""
    universe = load_universe("fixtures/universe.valid.yaml")
    
    tech_etfs = universe.get_by_sector(Sector.TECHNOLOGY)
    assert len(tech_etfs) > 0


def test_effective_exposure():
    """Test leverage exposure calculation."""
    universe = load_universe("fixtures/universe.valid.yaml")
    
    tqqq = universe.get_by_ticker("TQQQ")
    assert tqqq is not None
    assert tqqq.leverage_factor == 3.0
    
    exposure = tqqq.effective_exposure(10000)
    assert exposure == 30000


def test_check_universe_command():
    """Test the check_universe command."""
    result = subprocess.run(
        [sys.executable, "-m", "app.tools.check_universe",
         "--file", "fixtures/universe.valid.yaml"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0, f"Should pass: {result.stderr}"
    assert "PASSED" in result.stdout


def test_invalid_universe_fails():
    """Test that invalid universe fails with clear error."""
    result = subprocess.run(
        [sys.executable, "-m", "app.tools.check_universe",
         "--file", "fixtures/universe.invalid.yaml"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    # Should fail due to invalid ETF type
    assert result.returncode != 0

"""Test harness and deterministic fixtures."""
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a fixture file by name."""
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {name}")
    
    if path.suffix == ".json":
        with open(path) as f:
            return json.load(f)
    elif path.suffix in (".yaml", ".yml"):
        with open(path) as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported fixture format: {path.suffix}")


def save_fixture(name: str, data: dict) -> None:
    """Save a fixture file."""
    path = FIXTURES_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.suffix == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    elif path.suffix in (".yaml", ".yml"):
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported fixture format: {path.suffix}")


def create_market_snapshot(tickers: list[str], base_price: float = 100.0) -> dict:
    """Create a deterministic market snapshot fixture."""
    import random
    random.seed(42)  # Deterministic
    
    quotes = {}
    for ticker in tickers:
        spread = base_price * 0.001  # 10 bps
        quotes[ticker] = {
            "ticker": ticker,
            "bid": round(base_price - spread/2, 2),
            "ask": round(base_price + spread/2, 2),
            "last": round(base_price, 2),
            "volume": random.randint(1000000, 10000000),
            "timestamp": datetime.now().isoformat()
        }
        base_price *= 1.01  # Slight price variation
    
    return {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "quotes": quotes
    }


# Pre-built fixtures for common scenarios
def get_day_ok_fixture() -> dict:
    """Good scenario fixture."""
    return {
        "mode": "paper",
        "market_snapshot": create_market_snapshot(["SPY", "QQQ", "XLF", "XLK"]),
        "recommendations": [
            {"ticker": "SPY", "direction": "LONG", "conviction": 75},
            {"ticker": "XLF", "direction": "LONG", "conviction": 60},
        ]
    }


def get_day_stale_fixture() -> dict:
    """Stale data fixture."""
    stale_time = (datetime.now() - timedelta(seconds=120)).isoformat()
    return {
        "mode": "paper",
        "market_snapshot": {
            "timestamp": stale_time,
            "quotes": {
                "SPY": {
                    "ticker": "SPY", "bid": 500.0, "ask": 500.1,
                    "last": 500.05, "volume": 80000000, "timestamp": stale_time
                }
            }
        }
    }


def get_day_loss_stop_fixture() -> dict:
    """Daily loss stop triggered fixture."""
    return {
        "mode": "paper",
        "daily_pnl_pct": -3.0,  # Exceeds 2.5% stop
        "positions": [
            {"ticker": "SPY", "pnl_pct": -2.5},
            {"ticker": "QQQ", "pnl_pct": -0.5}
        ]
    }

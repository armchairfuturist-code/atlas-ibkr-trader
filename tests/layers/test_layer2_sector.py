"""Tests for Layer 2 sector desk."""
import pytest

from app.layers.layer2_sector import SectorLayer
from app.layers.config_loader import load_layer_config
from app.layers.models import MacroAgentOutput


def test_sector_layer_returns_etf_preferred_outputs():
    """SectorLayer should map macro outputs to sector-ranked ETF candidates."""
    layer = SectorLayer(load_layer_config("layer2_sector"))
    
    # Sample macro outputs from Layer 1
    macro_outputs = [
        MacroAgentOutput(
            agent_name="central_bank",
            config_version="v1",
            regime_vote="RISK_ON",
            confidence=0.8,
            features={"fed_bias": 0.4},
        ),
    ]
    
    outputs = layer.evaluate(macro_outputs)
    
    # Should return sector desk outputs
    assert len(outputs) > 0
    # ETF tickers should be set
    assert all(o.etf_ticker for o in outputs)
    # All should have is_etf=True
    assert all(o.is_etf for o in outputs)

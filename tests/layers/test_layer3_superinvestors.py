"""Tests for Layer 3 superinvestor filters."""
import pytest

from app.layers.layer3_superinvestors import SuperinvestorLayer
from app.layers.config_loader import load_layer_config
from app.layers.models import SectorDeskOutput


def test_superinvestor_layer_reweights_sector_candidates():
    """SuperinvestorLayer should reweight sector outputs with filter provenance."""
    layer = SuperinvestorLayer(load_layer_config("layer3_superinvestors"))
    
    # Sample sector outputs from Layer 2
    sector_outputs = [
        SectorDeskOutput(
            sector="technology",
            etf_ticker="XLK",
            score=0.85,
            is_etf=True,
            config_version="v1",
        ),
        SectorDeskOutput(
            sector="healthcare",
            etf_ticker="XLV",
            score=0.75,
            is_etf=True,
            config_version="v1",
        ),
    ]
    
    outputs = layer.evaluate(sector_outputs)
    
    # Should return reweighted outputs with filter provenance
    assert len(outputs) > 0
    # Each should have filter_name and config_version
    assert all(o.filter_name for o in outputs)
    assert all(o.config_version for o in outputs)

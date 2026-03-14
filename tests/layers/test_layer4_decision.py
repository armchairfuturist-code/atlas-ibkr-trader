"""Tests for Layer 4 decision aggregation."""
import pytest

from app.layers.layer4_decision import DecisionLayer
from app.layers.config_loader import load_layer_config
from app.layers.models import SuperinvestorOutput


def test_decision_layer_returns_final_cio_proposals():
    """DecisionLayer should aggregate all layers and return CIO proposals."""
    layer = DecisionLayer(load_layer_config("layer4_decision"))
    
    # Sample superinvestor outputs from Layer 3
    superinvestor_outputs = [
        SuperinvestorOutput(
            source_etf="XLK",
            source_sector="technology",
            reweighted_score=0.88,
            filter_name="buffett_style",
            config_version="v1",
        ),
    ]
    
    result = layer.evaluate(superinvestor_outputs)
    
    # Should return DecisionLayerResult with proposals
    assert isinstance(result.rationale, str)
    assert result.config_version
    # Proposals should have required fields
    for p in result.proposals:
        assert "ticker" in p
        assert "direction" in p

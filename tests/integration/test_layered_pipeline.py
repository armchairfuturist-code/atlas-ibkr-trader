"""Tests for layered pipeline integration."""
import pytest

from app.pipeline.daily_runner import DailyPipeline
from app.signal_orchestrator import SignalOrchestrator
from app.layers.layer1_macro import MacroLayer
from app.layers.layer2_sector import SectorLayer
from app.layers.layer3_superinvestors import SuperinvestorLayer
from app.layers.layer4_decision import DecisionLayer
from app.layers.config_loader import load_layer_config


def test_daily_pipeline_runs_all_four_layers():
    """Pipeline should execute all four layers and produce proposals."""
    # Test layer integration
    macro_layer = MacroLayer(load_layer_config("layer1_macro"))
    sector_layer = SectorLayer(load_layer_config("layer2_sector"))
    investor_layer = SuperinvestorLayer(load_layer_config("layer3_superinvestors"))
    decision_layer = DecisionLayer(load_layer_config("layer4_decision"))
    
    # Sample market context
    market_context = {
        "fed_bias": 0.3,
        "rate_path": 0.2,
        "cpi_trend": -0.1,
    }
    
    # Run all layers
    macro_outputs = macro_layer.evaluate(market_context)
    sector_outputs = sector_layer.evaluate(macro_outputs)
    investor_outputs = investor_layer.evaluate(sector_outputs)
    decision_result = decision_layer.evaluate(investor_outputs)
    
    # Verify outputs
    assert len(macro_outputs) == 10  # Layer 1: 10 macro agents
    assert len(sector_outputs) == 7   # Layer 2: 7 sectors
    assert len(investor_outputs) > 0  # Layer 3: reweighted
    assert decision_result.proposals  # Layer 4: proposals
    assert decision_result.rationale  # Has rationale

"""Tests for layer output models and config loader."""
import pytest
from pathlib import Path

from app.layers.models import MacroAgentOutput, SectorDeskOutput, SuperinvestorOutput, DecisionLayerResult
from app.layers.config_loader import load_layer_config


def test_config_loader_reads_macro_agent_weights():
    """Config loader should read base layer config and return version, agents, and weights."""
    config = load_layer_config("layer1_macro")
    assert "version" in config
    assert "agents" in config
    assert "central_bank" in config["agents"]


def test_macro_agent_output_has_agent_and_config_versions():
    """MacroAgentOutput should have agent_name, config_version, regime_vote, confidence, and features."""
    output = MacroAgentOutput(
        agent_name="central_bank",
        config_version="v1",
        regime_vote="RISK_ON",
        confidence=0.8,
        features={"fed_bias": 0.3},
    )
    assert output.agent_name == "central_bank"
    assert output.config_version == "v1"
    assert output.regime_vote == "RISK_ON"
    assert output.confidence == 0.8
    assert output.features["fed_bias"] == 0.3


def test_sector_desk_output_has_sector_and_etf_tags():
    """SectorDeskOutput should include sector, etf_ticker, score, is_etf, and config_version."""
    output = SectorDeskOutput(
        sector="technology",
        etf_ticker="XLK",
        score=0.75,
        is_etf=True,
        config_version="v1",
    )
    assert output.sector == "technology"
    assert output.etf_ticker == "XLK"
    assert output.score == 0.75
    assert output.is_etf is True
    assert output.config_version == "v1"


def test_superinvestor_output_has_provenance():
    """SuperinvestorOutput should track source sector/etf and have config_version."""
    output = SuperinvestorOutput(
        source_etf="XLK",
        source_sector="technology",
        reweighted_score=0.82,
        filter_name="buffett_style",
        config_version="v1",
    )
    assert output.source_etf == "XLK"
    assert output.source_sector == "technology"
    assert output.reweighted_score == 0.82
    assert output.filter_name == "buffett_style"
    assert output.config_version == "v1"


def test_decision_layer_result_has_proposals():
    """DecisionLayerResult should contain CIO proposals with rationale."""
    result = DecisionLayerResult(
        proposals=[{"ticker": "XLK", "direction": "LONG", "size_pct": 10.0, "conviction": 80}],
        rationale="Three layer consensus: risk_on, tech sector, value filter",
        config_version="v1",
    )
    assert len(result.proposals) == 1
    assert result.proposals[0]["ticker"] == "XLK"
    assert result.rationale == "Three layer consensus: risk_on, tech sector, value filter"
    assert result.config_version == "v1"

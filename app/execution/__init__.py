"""Execution module for trade execution.

- autopredict_adapter: Bridges thematic analysis to Polymarket execution
"""

from app.execution.autopredict_adapter import (
    AutopredictAdapter,
    AutopredictExecution,
    FairProbabilityEstimate,
    TradeDecision,
    autopredict_adapter,
)

__all__ = [
    "AutopredictAdapter",
    "AutopredictExecution",
    "FairProbabilityEstimate",
    "TradeDecision",
    "autopredict_adapter",
]

"""Scorecard engine for evaluating agent performance."""
from dataclasses import dataclass
from typing import Any

from app.autoresearch.decision_memory import RunRecord


@dataclass
class AgentScore:
    """Score metrics for a single agent/ticker."""
    name: str
    hit_rate: float  # Percentage of positive return trades
    mean_return: float  # Average return percentage
    total_trades: int
    config_version: str


class ScorecardEngine:
    """Evaluates agent performance from stored run records."""
    
    def score(self, records: list[RunRecord]) -> dict[str, AgentScore]:
        """Score each agent/ticker based on historical performance.
        
        Args:
            records: List of RunRecord with realized outcomes
            
        Returns:
            Dict mapping agent name to AgentScore
        """
        agent_stats: dict[str, dict[str, Any]] = {}
        
        for record in records:
            if not record.outcomes:
                continue
            
            version = record.config_version
            
            for proposal in record.proposals:
                ticker = proposal.get("ticker", "unknown")
                if ticker not in agent_stats:
                    agent_stats[ticker] = {
                        "hits": 0,
                        "total": 0,
                        "returns": [],
                        "version": version,
                    }
                
                # Get outcome for this ticker
                outcome = record.outcomes.get(ticker)
                if outcome:
                    ret = outcome.get("return_pct", 0)
                    agent_stats[ticker]["total"] += 1
                    agent_stats[ticker]["returns"].append(ret)
                    if ret > 0:
                        agent_stats[ticker]["hits"] += 1
        
        # Compute scores
        scores = {}
        for name, stats in agent_stats.items():
            total = stats["total"]
            if total > 0:
                hit_rate = stats["hits"] / total
                mean_return = sum(stats["returns"]) / total
            else:
                hit_rate = 0.0
                mean_return = 0.0
            
            scores[name] = AgentScore(
                name=name,
                hit_rate=hit_rate,
                mean_return=mean_return,
                total_trades=total,
                config_version=stats["version"],
            )
        
        return scores

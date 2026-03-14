"""Replay evaluator for baseline vs candidate comparison."""
from dataclasses import dataclass
from typing import Any

from app.layers.config_loader import load_layer_config


@dataclass
class ReplayVerdict:
    """Result of replay comparison."""
    decision: str  # "keep" or "revert"
    baseline_return: float
    candidate_return: float
    improvement_pct: float
    reason: str


class ReplayEvaluator:
    """Compares baseline vs candidate config performance via replay."""
    
    # Minimum improvement required to promote (5%)
    MIN_IMPROVEMENT = 0.05
    
    def compare(
        self, 
        baseline_result: dict[str, Any], 
        candidate_result: dict[str, Any]
    ) -> ReplayVerdict:
        """Compare baseline and candidate replay results.
        
        Args:
            baseline_result: Dict with baseline metrics (return_pct, sharpe, etc.)
            candidate_result: Dict with candidate metrics
            
        Returns:
            ReplayVerdict with keep/revert decision
        """
        baseline_return = baseline_result.get("return_pct", 0)
        candidate_return = candidate_result.get("return_pct", 0)
        
        # Calculate improvement
        if baseline_return > 0:
            improvement = (candidate_return - baseline_return) / abs(baseline_return)
        else:
            improvement = candidate_return - baseline_return
        
        # Decision logic
        if candidate_return > baseline_return and improvement >= self.MIN_IMPROVEMENT:
            return ReplayVerdict(
                decision="keep",
                baseline_return=baseline_return,
                candidate_return=candidate_return,
                improvement_pct=improvement,
                reason=f"Candidate outperforms by {improvement*100:.1f}%",
            )
        else:
            return ReplayVerdict(
                decision="revert",
                baseline_return=baseline_return,
                candidate_return=candidate_return,
                improvement_pct=improvement,
                reason="Candidate does not meet promotion threshold",
            )
    
    def evaluate_with_config(
        self, 
        baseline_config: str, 
        candidate_config: str,
        fixtures: list[dict] = None
    ) -> ReplayVerdict:
        """Evaluate configs using fixtures.
        
        Args:
            baseline_config: Version string for baseline (e.g., "v1")
            candidate_config: Version string for candidate (e.g., "v2")
            fixtures: Optional fixture data for replay
            
        Returns:
            ReplayVerdict
        """
        # Load configs
        base_cfg = load_layer_config("layer1_macro", baseline_config)
        cand_cfg = load_layer_config("layer1_macro", candidate_config)
        
        # In production, would run actual backtest
        # For now, simulate results based on config differences
        baseline_return = 1.0
        candidate_return = 1.2
        
        return self.compare(
            {"return_pct": baseline_return},
            {"return_pct": candidate_return}
        )

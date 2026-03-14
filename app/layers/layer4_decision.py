"""Layer 4: Decision aggregation - CRO, Alpha, Execution, CIO."""
from app.layers.models import SuperinvestorOutput, DecisionLayerResult
from app.layers.config_loader import load_layer_config


class DecisionLayer:
    """Layer 4 - Final decision aggregation producing CIO proposals."""
    
    def __init__(self, config: dict = None):
        """Initialize with layer config.
        
        Args:
            config: Layer configuration dict. If None, loads from base YAML.
        """
        self.config = config or load_layer_config("layer4_decision")
        self.version = self.config.get("version", "v1")
        self.agents = self.config.get("agents", {})
        self.aggregation = self.config.get("aggregation", {})
    
    def evaluate(self, superinvestor_outputs: list[SuperinvestorOutput]) -> DecisionLayerResult:
        """Aggregate all layers into final CIO proposals.
        
        Args:
            superinvestor_outputs: List of SuperinvestorOutput from Layer 3
            
        Returns:
            DecisionLayerResult with final proposals
        """
        # CRO review - apply risk parameters
        cro_config = self.agents.get("cro", {})
        max_position_pct = cro_config.get("parameters", {}).get("max_position_pct", 12.5)
        
        # Alpha discovery - score and rank
        proposals = self._generate_proposals(
            superinvestor_outputs, max_position_pct
        )
        
        # Build rationale
        rationale = self._build_rationale(superinvestor_outputs, proposals)
        
        return DecisionLayerResult(
            proposals=proposals,
            rationale=rationale,
            config_version=self.version,
        )
    
    def _generate_proposals(
        self, 
        outputs: list[SuperinvestorOutput], 
        max_position_pct: float
    ) -> list[dict]:
        """Generate trading proposals from superinvestor outputs."""
        proposals = []
        
        # Take top candidates
        for output in outputs[:3]:
            # Calculate position size (scaled by score)
            size_pct = min(output.reweighted_score * max_position_pct, max_position_pct)
            
            # Determine direction based on score
            direction = "LONG" if output.reweighted_score > 0.5 else "NEUTRAL"
            
            # Calculate conviction (0-100)
            conviction = int(output.reweighted_score * 100)
            
            proposals.append({
                "ticker": output.source_etf,
                "direction": direction,
                "size_pct": round(size_pct, 2),
                "conviction": conviction,
                "source_filter": output.filter_name,
            })
        
        return proposals
    
    def _build_rationale(
        self, 
        outputs: list[SuperinvestorOutput], 
        proposals: list[dict]
    ) -> str:
        """Build human-readable rationale for the decision."""
        if not outputs:
            return "No sector candidates passed layer filters."
        
        # Find dominant regime
        top_filters = [o.filter_name for o in outputs[:3]]
        filter_summary = ", ".join(set(top_filters))
        
        return f"Layer consensus: {len(outputs)} candidates filtered to {len(proposals)} proposals. Top filters: {filter_summary}"

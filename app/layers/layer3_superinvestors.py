"""Layer 3: Superinvestor reweighting filters."""
from app.layers.models import SectorDeskOutput, SuperinvestorOutput
from app.layers.config_loader import load_layer_config


class SuperinvestorLayer:
    """Layer 3 - Applies investor-style filters to reweight sector candidates."""
    
    def __init__(self, config: dict = None):
        """Initialize with layer config.
        
        Args:
            config: Layer configuration dict. If None, loads from base YAML.
        """
        self.config = config or load_layer_config("layer3_superinvestors")
        self.version = self.config.get("version", "v1")
        self.filters = self.config.get("filters", {})
    
    def evaluate(self, sector_outputs: list[SectorDeskOutput]) -> list[SuperinvestorOutput]:
        """Apply superinvestor filters to reweight sector outputs.
        
        Args:
            sector_outputs: List of SectorDeskOutput from Layer 2
            
        Returns:
            List of SuperinvestorOutput with reweighted scores
        """
        outputs = []
        
        for sector in sector_outputs:
            for filter_key, filter_config in self.filters.items():
                # Apply filter-specific reweighting
                reweighted = self._apply_filter(
                    sector, filter_key, filter_config
                )
                outputs.append(reweighted)
        
        # Sort by reweighted score descending
        outputs.sort(key=lambda x: x.reweighted_score, reverse=True)
        
        return outputs
    
    def _apply_filter(
        self, sector: SectorDeskOutput, filter_key: str, filter_config: dict
    ) -> SuperinvestorOutput:
        """Apply a specific filter to reweight a sector output."""
        bounds = filter_config.get("weight_bounds", [0.9, 1.1])
        min_weight, max_weight = bounds
        
        # Apply bounded weight adjustment
        # In production would evaluate criteria; here we use base score
        adjustment = 1.0
        if filter_key == "buffett_style":
            adjustment = 1.05  # Quality bias
        elif filter_key == "graham_style":
            adjustment = 0.95  # Value bias may reduce tech
        elif filter_key == "lynch_style":
            adjustment = 1.0
        elif filter_key == "simons_style":
            adjustment = 1.02  # Slight momentum tilt
        
        # Clamp to bounds
        adjustment = max(min_weight, min(max_weight, adjustment))
        
        reweighted_score = min(sector.score * adjustment, 1.0)
        
        return SuperinvestorOutput(
            source_etf=sector.etf_ticker,
            source_sector=sector.sector,
            reweighted_score=reweighted_score,
            filter_name=filter_key,
            config_version=self.version,
        )

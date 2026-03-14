"""Layer 2: Sector desks for ETF-first sector ranking."""
from app.layers.models import MacroAgentOutput, SectorDeskOutput
from app.layers.config_loader import load_layer_config


class SectorLayer:
    """Layer 2 - Maps macro regime to sector-scored ETF candidates."""
    
    def __init__(self, config: dict = None):
        """Initialize with layer config.
        
        Args:
            config: Layer configuration dict. If None, loads from base YAML.
        """
        self.config = config or load_layer_config("layer2_sector")
        self.version = self.config.get("version", "v1")
        self.sectors = self.config.get("sectors", {})
        self.scoring = self.config.get("scoring", {})
    
    def evaluate(self, macro_outputs: list[MacroAgentOutput]) -> list[SectorDeskOutput]:
        """Evaluate sector rankings based on macro layer outputs.
        
        Args:
            macro_outputs: List of MacroAgentOutput from Layer 1
            
        Returns:
            List of SectorDeskOutput, ranked by score
        """
        # Determine overall regime from macro layer
        regime = self._aggregate_regime(macro_outputs)
        
        outputs = []
        
        for sector_key, sector_config in self.sectors.items():
            # Calculate score based on regime alignment
            score = self._calculate_sector_score(sector_key, regime, sector_config)
            
            outputs.append(SectorDeskOutput(
                sector=sector_key,
                etf_ticker=sector_config.get("etf", ""),
                score=score,
                is_etf=self.scoring.get("etf_preference", True),
                config_version=self.version,
            ))
        
        # Sort by score descending
        outputs.sort(key=lambda x: x.score, reverse=True)
        
        return outputs
    
    def _aggregate_regime(self, macro_outputs: list[MacroAgentOutput]) -> str:
        """Aggregate regime from macro layer outputs."""
        risk_on_count = sum(1 for o in macro_outputs if o.regime_vote == "RISK_ON")
        risk_off_count = sum(1 for o in macro_outputs if o.regime_vote == "RISK_OFF")
        
        if risk_on_count > risk_off_count:
            return "RISK_ON"
        elif risk_off_count > risk_on_count:
            return "RISK_OFF"
        return "NEUTRAL"
    
    def _calculate_sector_score(self, sector: str, regime: str, sector_config: dict) -> float:
        """Calculate sector score based on regime alignment and weight."""
        base_weight = sector_config.get("weight", 0.5)
        
        # Risk-on sectors: tech, consumer, financials
        # Risk-off sectors: utilities, consumer staples, healthcare
        risk_on_sectors = {"technology", "consumer_discretionary", "financials"}
        risk_off_sectors = {"healthcare", "consumer_staples", "utilities"}
        
        if regime == "RISK_ON" and sector in risk_on_sectors:
            return min(base_weight * 1.2, 1.0)
        elif regime == "RISK_OFF" and sector in risk_off_sectors:
            return min(base_weight * 1.2, 1.0)
        elif regime == "NEUTRAL":
            return base_weight
        
        return base_weight * 0.7

"""Layer 1: Macro agents for regime detection."""
from app.layers.models import MacroAgentOutput
from app.layers.config_loader import load_layer_config


class MacroLayer:
    """Layer 1 - Evaluates 10 macro agents to determine market regime."""
    
    def __init__(self, config: dict = None):
        """Initialize with layer config.
        
        Args:
            config: Layer configuration dict. If None, loads from base YAML.
        """
        self.config = config or load_layer_config("layer1_macro")
        self.version = self.config.get("version", "v1")
        self.agents = self.config.get("agents", {})
    
    def evaluate(self, market_context: dict) -> list[MacroAgentOutput]:
        """Evaluate all macro agents given current market context.
        
        Args:
            market_context: Dict of market features (e.g., fed_bias, cpi_trend)
            
        Returns:
            List of MacroAgentOutput, one per configured agent
        """
        outputs = []
        
        for agent_key, agent_config in self.agents.items():
            # Determine regime vote based on agent type and context
            regime_vote = self._determine_regime(agent_key, market_context)
            
            # Calculate confidence based on feature availability
            confidence = self._calculate_confidence(agent_config, market_context)
            
            # Extract relevant features
            features = self._extract_features(agent_config, market_context)
            
            outputs.append(MacroAgentOutput(
                agent_name=agent_key,
                config_version=self.version,
                regime_vote=regime_vote,
                confidence=confidence,
                features=features,
            ))
        
        return outputs
    
    def _determine_regime(self, agent_key: str, context: dict) -> str:
        """Determine RISK_ON/RISK_OFF/NEUTRAL based on agent and context."""
        # Simplified regime detection - in production would use actual model/heuristics
        if agent_key == "central_bank":
            fed_bias = context.get("fed_bias", 0)
            if fed_bias > 0.3:
                return "RISK_ON"
            elif fed_bias < -0.3:
                return "RISK_OFF"
        elif agent_key == "inflation":
            cpi = context.get("cpi_trend", 0)
            if cpi < 0:
                return "RISK_ON"  # Inflation declining
            elif cpi > 0.5:
                return "RISK_OFF"
        
        # Default to neutral
        return "NEUTRAL"
    
    def _calculate_confidence(self, agent_config: dict, context: dict) -> float:
        """Calculate confidence based on weight and feature availability."""
        base_weight = agent_config.get("weight", 0.5)
        required_features = agent_config.get("features", [])
        
        # Confidence increases with available features
        available = sum(1 for f in required_features if f in context)
        feature_ratio = available / max(len(required_features), 1)
        
        return min(base_weight * feature_ratio * 1.2, 1.0)
    
    def _extract_features(self, agent_config: dict, context: dict) -> dict:
        """Extract relevant features from context for this agent."""
        required = agent_config.get("features", [])
        return {f: context.get(f, 0.0) for f in required}

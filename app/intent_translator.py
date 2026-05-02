"""Recommendation-to-proposed-intent translator."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.schemas import (
    Recommendation, ProposedIntent, SignalDirection, 
    OrderStatus, RiskVerdictEvent, RiskVerdict
)
from app.universe import ETFUniverse
from app.config import Config


@dataclass
class IntentTranslator:
    """
    Translates recommendations into proposed order intents.
    
    Applies:
    - Position sizing based on conviction
    - Sector priority (unlevered preferred for tie-break)
    - Risk verdict requirement
    """
    
    def __init__(self, config: Config, universe: ETFUniverse):
        self.config = config
        self.universe = universe
    
    def translate(
        self,
        recommendation: Recommendation,
        risk_verdict: RiskVerdictEvent,
        proposed_shares: Optional[int] = None,
        estimated_price: float = 100.0
    ) -> tuple[Optional[ProposedIntent], Optional[str]]:
        """
        Translate recommendation to proposed intent.
        Returns (intent, error)
        """
        # Must have PASS risk verdict
        if risk_verdict.verdict != RiskVerdict.PASS:
            return None, f"RISK_VERDICT_REQUIRED: {risk_verdict.reason}"
        
        # Get ETF info
        etf = self.universe.get_by_ticker(recommendation.ticker)
        if etf is None:
            return None, f"Unknown ticker: {recommendation.ticker}"
        
        if proposed_shares is not None:
            shares = proposed_shares
        else:
            # Calculate position size based on conviction
            # Higher conviction = larger position
            base_size = self._calculate_size(recommendation.conviction)
            
            # Determine shares (round to nearest 100 for ETFs)
            shares = (base_size // 100) * 100
            if shares < 100:
                shares = 100  # Minimum 100 shares
        
        # Calculate estimated value
        estimated_value = shares * estimated_price
        
        # Create proposed intent
        intent = ProposedIntent(
            recommendation_id=recommendation.id,
            risk_verdict_id=risk_verdict.id,
            ticker=recommendation.ticker,
            direction=recommendation.direction,
            shares=shares,
            estimated_value=estimated_value,
            status=OrderStatus.PENDING_APPROVAL
        )
        
        return intent, None
    
    def _calculate_size(self, conviction: int) -> int:
        """Calculate position size based on conviction (1-100)."""
        # Map conviction to dollar amount
        # 100 conviction = full position, 0 = no position
        max_position = 12500  # 12.5% of $100k account
        
        # Linear scale
        size = int((conviction / 100.0) * max_position)
        
        return max(size, 0)  # Ensure non-negative
    
    def translate_batch(
        self,
        recommendations: list[Recommendation],
        risk_verdicts: dict[str, RiskVerdictEvent],
        proposed_shares_map: Optional[dict[str, int]] = None,
        prices_map: Optional[dict[str, float]] = None
    ) -> list[ProposedIntent]:
        """Translate multiple recommendations to intents."""
        intents = []
        
        for rec in recommendations:
            verdict = risk_verdicts.get(rec.id)
            if verdict is None:
                continue
            
            shares = proposed_shares_map.get(rec.id) if proposed_shares_map else None
            price = prices_map.get(rec.ticker, 100.0) if prices_map else 100.0
            
            intent, error = self.translate(rec, verdict, proposed_shares=shares, estimated_price=price)
            if intent:
                intents.append(intent)
        
        return intents

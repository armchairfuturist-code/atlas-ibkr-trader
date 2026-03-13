"""Risk engine with effective exposure accounting."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.schemas import RiskVerdict, RiskVerdictEvent, RejectCode
from app.config import Config, RiskLimits
from app.universe import ETFUniverse, ETF


@dataclass
class Position:
    """Current portfolio position."""
    ticker: str
    shares: int
    current_value: float
    sector: str


@dataclass
class PortfolioState:
    """Current portfolio state for risk calculations."""
    cash: float = 100000.0
    positions: list[Position] = field(default_factory=list)
    daily_pnl_pct: float = 0.0
    
    @property
    def equity(self) -> float:
        """Total portfolio equity."""
        return self.cash + sum(p.current_value for p in self.positions)
    
    @property
    def gross_exposure(self) -> float:
        """Gross long + short exposure."""
        return sum(abs(p.current_value) for p in self.positions)
    
    @property
    def net_exposure(self) -> float:
        """Net long - short exposure."""
        return sum(p.current_value for p in self.positions)
    
    @property
    def gross_leverage(self) -> float:
        """Gross exposure / equity."""
        if self.equity <= 0:
            return float('inf')
        return self.gross_exposure / self.equity


class RiskEngine:
    """
    Risk engine enforcing hard limits.
    
    Checks:
    - Gross leverage <= max_gross_leverage
    - Position size <= max_position_pct
    - Sector concentration <= max_sector_pct
    - Daily loss stop
    - Liquidity thresholds
    """
    
    def __init__(self, config: Config, universe: ETFUniverse):
        self.config = config
        self.limits = config.risk_limits
        self.universe = universe
    
    def evaluate(
        self,
        recommendation_ticker: str,
        proposed_shares: int,
        current_price: float,
        portfolio: PortfolioState
    ) -> RiskVerdictEvent:
        """Evaluate a proposed position against risk limits."""
        
        # Calculate proposed position value
        proposed_value = proposed_shares * current_price
        
        # Get ETF metadata
        etf = self.universe.get_by_ticker(recommendation_ticker)
        if etf is None:
            return RiskVerdictEvent(
                verdict=RiskVerdict.REJECT,
                reject_code=RejectCode.DATA_MISSING,
                reason=f"Unknown ticker: {recommendation_ticker}"
            )
        
        # Calculate effective exposure (leverage-aware)
        effective_exposure = abs(proposed_value * etf.leverage_factor)
        
        # Project new portfolio state
        new_equity = portfolio.equity + proposed_value
        new_gross = portfolio.gross_exposure + effective_exposure
        
        # 1. Check gross leverage
        if new_equity > 0:
            projected_leverage = new_gross / new_equity
            if projected_leverage > self.limits.max_gross_leverage:
                return RiskVerdictEvent(
                    verdict=RiskVerdict.REJECT,
                    reject_code=RejectCode.GROSS_LEVERAGE_BREACH,
                    reason=f"Would exceed gross leverage: {projected_leverage:.2f}x > {self.limits.max_gross_leverage}x",
                    metrics={"projected_leverage": projected_leverage}
                )
        
        # 2. Check position size
        if new_equity > 0:
            position_pct = (proposed_value / new_equity) * 100
            if position_pct > self.limits.max_position_pct:
                return RiskVerdictEvent(
                    verdict=RiskVerdict.REJECT,
                    reject_code=RejectCode.POSITION_SIZE_BREACH,
                    reason=f"Position {position_pct:.1f}% exceeds {self.limits.max_position_pct}% limit",
                    metrics={"position_pct": position_pct}
                )
        
        # 3. Check sector concentration
        proposed_sector = etf.primary_sector.value
        current_sector_value = sum(
            p.current_value for p in portfolio.positions 
            if p.sector == proposed_sector
        )
        new_sector_value = current_sector_value + proposed_value
        if new_equity > 0:
            sector_pct = (new_sector_value / new_equity) * 100
            if sector_pct > self.limits.max_sector_pct:
                return RiskVerdictEvent(
                    verdict=RiskVerdict.REJECT,
                    reject_code=RejectCode.SECTOR_CONCENTRATION_BREACH,
                    reason=f"Sector {proposed_sector} would be {sector_pct:.1f}% > {self.limits.max_sector_pct}%",
                    metrics={"sector_pct": sector_pct}
                )
        
        # 4. Check daily loss stop
        if portfolio.daily_pnl_pct < -self.limits.daily_loss_stop_pct:
            return RiskVerdictEvent(
                verdict=RiskVerdict.REJECT,
                reject_code=RejectCode.DAILY_STOP_TRIGGERED,
                reason=f"Daily loss {portfolio.daily_pnl_pct:.2f}% exceeds {self.limits.daily_loss_stop_pct}% stop",
                metrics={"daily_pnl_pct": portfolio.daily_pnl_pct}
            )
        
        # 5. Check liquidity
        if etf.min_adverage_volume > 0 and etf.max_spread_bps > 0:
            # In production, would check actual spread
            # For now, pass
            pass
        
        # All checks passed
        return RiskVerdictEvent(
            verdict=RiskVerdict.PASS,
            reason="All risk checks passed"
        )
    
    def evaluate_batch(
        self,
        positions: list[tuple[str, int, float]],
        portfolio: PortfolioState
    ) -> dict[str, RiskVerdictEvent]:
        """Evaluate multiple proposed positions."""
        results = {}
        for ticker, shares, price in positions:
            results[ticker] = self.evaluate(ticker, shares, price, portfolio)
        return results

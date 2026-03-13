"""Stale/missing data fail-closed and no-trade controller."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.data.providers import DataProvider, Quote


@dataclass
class NoTradeDecision:
    """No-trade decision with reason."""
    should_trade: bool = False
    reason_code: str = ""
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class NoTradeController:
    """
    Fail-closed controller for stale/missing data.
    
    If critical data is missing or stale, always choose NO_TRADE.
    """
    
    def __init__(
        self,
        provider: DataProvider,
        max_stale_seconds: int = 60
    ):
        self.provider = provider
        self.max_stale_seconds = max_stale_seconds
    
    def check(
        self,
        tickers: list[str]
    ) -> NoTradeDecision:
        """
        Check if trading should proceed based on data quality.
        Returns NoTradeDecision with should_trade=False if any issue.
        """
        for ticker in tickers:
            # Check if quote exists
            quote = self.provider.get_quote(ticker)
            if quote is None:
                return NoTradeDecision(
                    should_trade=False,
                    reason_code="DATA_MISSING",
                    reason=f"No quote data for {ticker}"
                )
            
            # Check if quote is fresh
            if not self.provider.is_fresh(ticker, self.max_stale_seconds):
                return NoTradeDecision(
                    should_trade=False,
                    reason_code="DATA_STALE",
                    reason=f"Quote for {ticker} is stale (> {self.max_stale_seconds}s)"
                )
        
        # All checks passed
        return NoTradeDecision(
            should_trade=True,
            reason_code="OK",
            reason="All data fresh"
        )
    
    def check_single(self, ticker: str) -> NoTradeDecision:
        """Check a single ticker."""
        return self.check([ticker])

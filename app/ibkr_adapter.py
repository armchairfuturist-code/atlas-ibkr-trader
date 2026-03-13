"""IBKR paper adapter for order submission."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import socket

from app.schemas import OrderSubmission, OrderStatus, SignalDirection
from app.config import Config


@dataclass
class IBKRConnection:
    """IBKR connection state."""
    host: str
    port: int
    client_id: int
    connected: bool = False
    paper_mode: bool = True


class IBKRAdapter:
    """
    IBKR paper adapter with pre-trade safety checks.
    
    Note: This is a stub implementation. In production,
    would use ib_insync or IB API directly.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[IBKRConnection] = None
    
    def connect(self) -> tuple[bool, Optional[str]]:
        """Connect to IBKR."""
        # Safety: Only allow paper mode
        if not self.config.is_paper_only():
            return False, "LIVE_MODE_FORBIDDEN: Only paper mode allowed"
        
        # Stub connection
        self._connection = IBKRConnection(
            host=self.config.ibkr_host,
            port=self.config.ibkr_port,
            client_id=self.config.ibkr_client_id,
            connected=True,
            paper_mode=True
        )
        
        return True, None
    
    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self._connection:
            self._connection.connected = False
    
    def submit_order(
        self,
        ticker: str,
        direction: SignalDirection,
        shares: int
    ) -> tuple[Optional[OrderSubmission], Optional[str]]:
        """
        Submit order to IBKR.
        Returns (order, error)
        """
        # Pre-flight checks
        if not self._connection or not self._connection.connected:
            return None, "Not connected to IBKR"
        
        if not self._connection.paper_mode:
            return None, "LIVE_MODE_FORBIDDEN"
        
        # Validate inputs
        if shares <= 0:
            return None, "Invalid share count"
        
        if not ticker:
            return None, "Missing ticker"
        
        # Create order submission (stub)
        order = OrderSubmission(
            ticker=ticker,
            direction=direction,
            shares=shares,
            broker_order_id=f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status=OrderStatus.SUBMITTED
        )
        
        return order, None
    
    def check_buying_power(self) -> tuple[Optional[float], Optional[str]]:
        """Check available buying power."""
        if not self._connection or not self._connection.connected:
            return None, "Not connected"
        
        # Stub: Return simulated buying power
        return 100000.0, None
    
    def get_account_info(self) -> dict:
        """Get account information."""
        if not self._connection or not self._connection.connected:
            return {"error": "Not connected"}
        
        return {
            "account_type": "PAPER" if self._connection.paper_mode else "LIVE",
            "buying_power": 100000.0,
            "cash": 100000.0,
            "positions_value": 0.0
        }

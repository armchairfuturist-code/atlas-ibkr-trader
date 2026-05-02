"""Decision, risk, and audit event schemas."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class SignalDirection(str, Enum):
    """Trading signal direction."""

    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalRating(str, Enum):
    """5-tier rating scale from TradingAgents.

    - BUY: Strong conviction to enter/add position
    - OVERWEIGHT: Favorable, gradually increase exposure
    - HOLD: Maintain current position
    - UNDERWEIGHT: Reduce exposure, partial profits
    - SELL: Exit position or avoid entry
    """

    BUY = "BUY"
    OVERWEIGHT = "OVERWEIGHT"
    HOLD = "HOLD"
    UNDERWEIGHT = "UNDERWEIGHT"
    SELL = "SELL"


class RiskVerdict(str, Enum):
    """Risk engine verdict."""

    PASS = "PASS"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"


class RejectCode(str, Enum):
    """Machine-readable reject codes."""

    GROSS_LEVERAGE_BREACH = "GROSS_LEVERAGE_BREACH"
    POSITION_SIZE_BREACH = "POSITION_SIZE_BREACH"
    SECTOR_CONCENTRATION_BREACH = "SECTOR_CONCENTRATION_BREACH"
    DAILY_STOP_TRIGGERED = "DAILY_STOP_TRIGGERED"
    LIQUIDITY_INSUFFICIENT = "LIQUIDITY_INSUFFICIENT"
    SPREAD_EXCEEDS_LIMIT = "SPREAD_EXCEEDS_LIMIT"
    DATA_STALE = "DATA_STALE"
    DATA_MISSING = "DATA_MISSING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    LIVE_MODE_FORBIDDEN = "LIVE_MODE_FORBIDDEN"
    RISK_VERDICT_REQUIRED = "RISK_VERDICT_REQUIRED"


@dataclass
class Recommendation:
    """Trading recommendation from signal generator."""

    id: str = field(default_factory=lambda: str(uuid4()))
    ticker: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    conviction: int = 50  # 1-100 scale
    thesis: str = ""
    target_price: Optional[float] = None
    sector: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    # 5-tier rating from multi-agent analysis
    rating: SignalRating = SignalRating.HOLD
    # Dynamic position sizing based on conviction
    position_size_pct: float = 0.0


@dataclass
class RiskVerdictEvent:
    """Risk evaluation result."""

    id: str = field(default_factory=lambda: str(uuid4()))
    recommendation_id: str = ""
    verdict: RiskVerdict = RiskVerdict.REVIEW
    reject_code: Optional[RejectCode] = None
    reason: str = ""
    metrics: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ApprovalRecord:
    """Human approval record."""

    id: str = field(default_factory=lambda: str(uuid4()))
    proposed_intent_id: str = ""
    approver_id: str = ""
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProposedIntent:
    """Proposed order intent awaiting approval."""

    id: str = field(default_factory=lambda: str(uuid4()))
    recommendation_id: str = ""
    risk_verdict_id: str = ""
    ticker: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    shares: int = 0
    estimated_value: float = 0.0
    status: OrderStatus = OrderStatus.PENDING_APPROVAL
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OrderSubmission:
    """Final submitted order."""

    id: str = field(default_factory=lambda: str(uuid4()))
    proposed_intent_id: str = ""
    approval_id: str = ""
    ticker: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    shares: int = 0
    broker_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.SUBMITTED
    timestamp: datetime = field(default_factory=datetime.now)

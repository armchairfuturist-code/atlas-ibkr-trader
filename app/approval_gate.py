"""Human approval gate service."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.schemas import ApprovalRecord, ProposedIntent, OrderStatus, RejectCode


@dataclass
class ApprovalRequest:
    """Request for human approval."""
    id: str = field(default_factory=lambda: str(uuid4()))
    proposed_intent_id: str = ""
    ticker: str = ""
    direction: str = ""
    shares: int = 0
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class ApprovalGate:
    """
    Human approval gate with replay protection.
    
    Flow:
    1. ProposedIntent created (awaiting approval)
    2. Human reviews and approves (or rejects)
    3. ApprovalRecord created with timestamp and approver
    4. Replay protection: cannot reuse same approval
    """
    
    def __init__(self):
        self._pending: dict[str, ProposedIntent] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        self._used_tokens: set[str] = set()  # For replay protection
    
    def create_approval_request(self, intent: ProposedIntent) -> ApprovalRequest:
        """Create an approval request from a proposed intent."""
        self._pending[intent.id] = intent
        
        return ApprovalRequest(
            proposed_intent_id=intent.id,
            ticker=intent.ticker,
            direction=intent.direction.value,
            shares=intent.shares,
            rationale=f"Approve {intent.shares} shares of {intent.ticker}"
        )
    
    def approve(
        self,
        request: ApprovalRequest,
        approver_id: str,
        rationale: str
    ) -> tuple[bool, Optional[str], Optional[ApprovalRecord]]:
        """
        Approve a request.
        Returns (success, error_message, approval_record)
        """
        # Check for replay
        if request.id in self._used_tokens:
            return False, "Approval token already used (replay protection)", None
        
        # Check intent exists
        if request.proposed_intent_id not in self._pending:
            return False, "Proposed intent not found", None
        
        # Create approval record
        approval = ApprovalRecord(
            proposed_intent_id=request.proposed_intent_id,
            approver_id=approver_id,
            rationale=rationale
        )
        
        # Mark token as used
        self._used_tokens.add(request.id)
        
        # Update intent status
        intent = self._pending[request.proposed_intent_id]
        intent.status = OrderStatus.APPROVED
        
        # Store approval
        self._approvals[approval.id] = approval
        
        return True, None, approval
    
    def reject(
        self,
        request: ApprovalRequest,
        approver_id: str,
        reason: str
    ) -> bool:
        """Reject a request."""
        if request.proposed_intent_id not in self._pending:
            return False
        
        # Mark token as used to prevent replay
        self._used_tokens.add(request.id)
        
        # Update intent status
        intent = self._pending[request.proposed_intent_id]
        intent.status = OrderStatus.REJECTED
        
        return True
    
    def get_approval(self, intent_id: str) -> Optional[ApprovalRecord]:
        """Get approval record for an intent."""
        for approval in self._approvals.values():
            if approval.proposed_intent_id == intent_id:
                return approval
        return None
    
    def is_approved(self, intent_id: str) -> bool:
        """Check if intent is approved."""
        return self.get_approval(intent_id) is not None

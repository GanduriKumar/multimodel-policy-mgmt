"""
Policy approval workflow service.

Manages the lifecycle for a policy version across states:
 - draft -> approved -> active -> retired

Includes signed activation metadata (HMAC) for governance. This service does
not perform signature key management; callers provide the secret key.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.policy_approval import PolicyApproval, VALID_STATES


class PolicyWorkflowService:
    """Encapsulates state transitions and activation signing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------
    # CRUD helpers
    # ---------------
    def get_or_create(self, *, tenant_id: int, policy_id: int, policy_version_id: int) -> PolicyApproval:
        pa = (
            self.session.query(PolicyApproval)
            .filter(PolicyApproval.policy_version_id == policy_version_id)
            .first()
        )
        if pa:
            return pa
        pa = PolicyApproval(
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            state="draft",
            requested_at=datetime.now(timezone.utc),
        )
        self.session.add(pa)
        self.session.commit()
        self.session.refresh(pa)
        return pa

    # ---------------
    # Transitions
    # ---------------
    def approve(self, pa: PolicyApproval, *, approved_by: str, notes: Optional[str] = None) -> PolicyApproval:
        self._ensure_state(pa, allowed_from=("draft",))
        pa.state = "approved"
        pa.approved_by = approved_by
        pa.approved_at = datetime.now(timezone.utc)
        pa.approval_notes = notes
        self.session.commit()
        self.session.refresh(pa)
        return pa

    def activate(
        self,
        pa: PolicyApproval,
        *,
        activated_by: str,
        activation_secret: str,
        notes: Optional[str] = None,
    ) -> PolicyApproval:
        self._ensure_state(pa, allowed_from=("approved",))
        pa.state = "active"
        pa.activated_by = activated_by
        pa.activated_at = datetime.now(timezone.utc)
        pa.activation_notes = notes
        pa.activation_signature = self._sign_activation(pa, activation_secret)
        self.session.commit()
        self.session.refresh(pa)
        return pa

    def retire(self, pa: PolicyApproval, *, retired_by: str, notes: Optional[str] = None) -> PolicyApproval:
        self._ensure_state(pa, allowed_from=("active", "approved", "draft"))
        pa.state = "retired"
        pa.activation_notes = notes
        self.session.commit()
        self.session.refresh(pa)
        return pa

    # ---------------
    # Utilities
    # ---------------
    def _sign_activation(self, pa: PolicyApproval, secret: str) -> str:
        msg = f"tenant={pa.tenant_id}|policy={pa.policy_id}|version={pa.policy_version_id}|activated_at={pa.activated_at.isoformat()}"
        mac = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()

    def _ensure_state(self, pa: PolicyApproval, *, allowed_from: tuple[str, ...]) -> None:
        if pa.state not in allowed_from:
            raise ValueError(f"Invalid state transition from {pa.state!r}; allowed: {allowed_from}")

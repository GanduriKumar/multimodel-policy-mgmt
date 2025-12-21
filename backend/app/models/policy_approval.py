"""
Policy approval and activation workflow model.

Tracks a policy version's lifecycle state (draft, approved, active, retired)
with optional signed activation metadata for governance/audit.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.mutable import MutableDict

from app.db.base import Base


VALID_STATES = ("draft", "approved", "active", "retired")


class PolicyApproval(Base):
    """Approval workflow record for a specific policy version."""

    __tablename__ = "policy_approval"
    __table_args__ = (
        UniqueConstraint("policy_version_id", name="uq_policy_approval_policy_version"),
        CheckConstraint(
            f"state in {VALID_STATES}", name="ck_policy_approval_state_valid"
        ),
        Index("ix_policy_approval_tenant_policy", "tenant_id", "policy_id"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Context
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policy.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("policy_version.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # State machine: draft -> approved -> active -> retired
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    # Request and approval metadata
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Activation metadata and signature
    activated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    activation_signature: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )  # e.g., HMAC-SHA256 hex

    # Arbitrary extra metadata
    metadata: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSON), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("policy_approvals", passive_deletes=True))
    policy: Mapped["Policy"] = relationship("Policy", backref=backref("policy_approvals", passive_deletes=True))
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", backref=backref("policy_approval", uselist=False, passive_deletes=True)
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PolicyApproval id={self.id!r} policy_id={self.policy_id!r} "
            f"version_id={self.policy_version_id!r} state={self.state!r}>"
        )

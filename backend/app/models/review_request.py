"""
ReviewRequest model for human oversight workflow.

Tracks decisions that require human review before being allowed.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.mutable import MutableList

from app.db.base import Base


class ReviewStatus(str, Enum):
    """Status of a review request."""
    PENDING = "pending"  # Awaiting human review
    IN_REVIEW = "in_review"  # Currently being reviewed
    APPROVED = "approved"  # Approved by reviewer
    REJECTED = "rejected"  # Rejected by reviewer
    EXPIRED = "expired"  # SLA exceeded, auto-rejected
    CANCELLED = "cancelled"  # Request cancelled


class ReviewPriority(str, Enum):
    """Priority level for review requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewRequest(Base):
    """
    Human oversight review request.
    
    When a decision requires human review (e.g., due to EU AI Act Article 14 
    requirements), a ReviewRequest is created and the original decision is blocked
    until a human reviewer approves or rejects it.
    """

    __tablename__ = "review_request"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to the decision that triggered this review
    decision_log_id: Mapped[int] = mapped_column(
        ForeignKey("decision_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One review request per decision
    )

    # Link to the request log for context
    request_log_id: Mapped[int] = mapped_column(
        ForeignKey("request_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Policy context
    policy_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy_version.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Review metadata
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=ReviewStatus.PENDING.value,
        server_default=text(f"'{ReviewStatus.PENDING.value}'"),
        index=True
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReviewPriority.MEDIUM.value,
        server_default=text(f"'{ReviewPriority.MEDIUM.value}'")
    )

    # Why this decision requires review
    review_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Explanation of why human review is required"
    )

    # Which regulatory frameworks require this review
    regulatory_triggers: Mapped[list[str] | None] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=True,
        default=list,
        comment="Regulatory frameworks that triggered review (e.g., ['eu_ai_act_high_risk'])"
    )

    # Specific articles/controls that require oversight
    regulatory_references: Mapped[list[str] | None] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=True,
        default=list,
        comment="Specific articles/controls (e.g., ['EU AI Act Article 14'])"
    )

    # SLA tracking (24-hour requirement)
    sla_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
        server_default=text("24"),
        comment="SLA in hours for review completion"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )

    # SLA deadline (auto-calculated)
    sla_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Deadline for review completion"
    )

    # Assignment
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="User ID of assigned reviewer"
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Completion
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # Backward-compatible alias used by tests: reviewed_at maps to completed_at
    @property
    def reviewed_at(self) -> datetime | None:
        """Return the time when review was completed (alias for completed_at)."""
        return self.completed_at

    # Context for reviewer
    decision_context: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Decision context: input, risk factors, triggered rules, etc."
    )

    # Additional metadata
    review_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata (e.g., escalation notes, tags)"
    )

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("review_requests", passive_deletes=True))
    decision_log: Mapped["DecisionLog"] = relationship(
        "DecisionLog", 
        backref=backref("review_request", uselist=False, passive_deletes=True)
    )
    request_log: Mapped["RequestLog"] = relationship("RequestLog", backref=backref("review_requests", passive_deletes=True))
    policy: Mapped["Policy"] = relationship("Policy", backref=backref("review_requests", passive_deletes=True))
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", 
        backref=backref("review_requests", passive_deletes=True)
    )

    def __init__(self, **kwargs):
        # Auto-calculate SLA deadline if not provided
        if "sla_deadline" not in kwargs and "created_at" in kwargs and "sla_hours" in kwargs:
            kwargs["sla_deadline"] = kwargs["created_at"] + timedelta(hours=kwargs["sla_hours"])
        elif "sla_deadline" not in kwargs:
            sla_hours = kwargs.get("sla_hours", 24)
            kwargs["sla_deadline"] = datetime.utcnow() + timedelta(hours=sla_hours)
        
        super().__init__(**kwargs)

    @property
    def is_overdue(self) -> bool:
        """Check if review is past SLA deadline."""
        return datetime.utcnow() > self.sla_deadline and self.status == ReviewStatus.PENDING.value

    @property
    def time_remaining(self) -> timedelta:
        """Time remaining until SLA deadline."""
        return self.sla_deadline - datetime.utcnow()

    @property
    def hours_remaining(self) -> float:
        """Hours remaining until SLA deadline."""
        return self.time_remaining.total_seconds() / 3600

    def __repr__(self) -> str:
        return (
            f"<ReviewRequest id={self.id!r} status={self.status!r} "
            f"priority={self.priority!r} sla_deadline={self.sla_deadline!r}>"
        )

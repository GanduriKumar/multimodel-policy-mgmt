"""
ReviewDecision model for storing human review outcomes.

Records the reviewer's decision (approve/reject) with justification.
"""

from __future__ import annotations

from datetime import datetime

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

from app.db.base import Base


class ReviewDecision(Base):
    """
    Human reviewer's decision on a ReviewRequest.
    
    Records whether the reviewer approved or rejected the flagged decision,
    along with their justification and any corrective actions.
    """

    __tablename__ = "review_decision"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Link to the review request
    review_request_id: Mapped[int] = mapped_column(
        ForeignKey("review_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One decision per review request
    )

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reviewer information
    reviewer_user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="User ID of the reviewer who made this decision"
    )

    reviewer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of reviewer for audit trail"
    )

    reviewer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email of reviewer for audit trail"
    )

    # Decision outcome
    approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="True if approved, False if rejected"
    )

    # Justification
    justification: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Reviewer's explanation for their decision"
    )

    # Confidence level in decision (0-100)
    confidence_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Reviewer's confidence in their decision (0-100)"
    )

    # Corrective actions (if rejected)
    corrective_actions: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of corrective actions to take if rejected"
    )

    # Escalation flag
    requires_escalation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Whether this decision requires further escalation"
    )

    escalation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for escalation if required"
    )

    # Compliance notes
    compliance_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about compliance considerations"
    )

    # Risk assessment by reviewer
    reviewer_risk_assessment: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Reviewer's assessment of risks: {risk_level, risk_factors, mitigation}"
    )

    # Additional metadata
    decision_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata (tags, custom fields, etc.)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When the review decision was made"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    review_request: Mapped["ReviewRequest"] = relationship(
        "ReviewRequest",
        backref=backref("review_decision", uselist=False, passive_deletes=True)
    )
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("review_decisions", passive_deletes=True))

    def __repr__(self) -> str:
        outcome = "APPROVED" if self.approved else "REJECTED"
        return (
            f"<ReviewDecision id={self.id!r} review_request_id={self.review_request_id!r} "
            f"outcome={outcome} reviewer_user_id={self.reviewer_user_id!r}>"
        )

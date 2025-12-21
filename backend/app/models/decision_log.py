"""
DecisionLog model (MVP).

Records the outcome of evaluating a request against a policy.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.mutable import MutableList

from app.db.base import Base


class DecisionLog(Base):
    """
    Minimal viable DecisionLog entity.
    """

    __tablename__ = "decision_log"
    __table_args__ = (
        # Typically one decision per request within a tenant
        UniqueConstraint("tenant_id", "request_log_id", name="uq_decision_per_request"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to the originating request
    request_log_id: Mapped[int] = mapped_column(
        ForeignKey("request_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Policy context used for this decision (optional if decision made without policy)
    policy_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy_version.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Decision outcome
    allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    # Explainability: reasons that led to the decision (e.g., ["blocked_term:x", "missing_evidence:url"])
    reasons: Mapped[list[str] | None] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)

    # Optional numeric risk score associated with this decision (0-100 typical)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("decision_logs", passive_deletes=True))
    request_log: Mapped["RequestLog"] = relationship(
        "RequestLog", backref=backref("decision_logs", passive_deletes=True)
    )
    policy: Mapped["Policy"] = relationship("Policy", backref=backref("decision_logs", passive_deletes=True))
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", backref=backref("decision_logs", passive_deletes=True)
    )

    def __repr__(self) -> str:
        return (
            f"<DecisionLog id={self.id!r} tenant_id={self.tenant_id!r} "
            f"request_log_id={self.request_log_id!r} allowed={self.allowed!r} "
            f"risk_score={self.risk_score!r}>"
        )
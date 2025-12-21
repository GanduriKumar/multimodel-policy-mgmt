"""
RiskScore model (MVP).

Stores the computed risk score and reasons for a given request/policy context.
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
    CheckConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.mutable import MutableList

from app.db.base import Base


class RiskScore(Base):
    """
    Minimal viable RiskScore entity.
    """

    __tablename__ = "risk_score"
    __table_args__ = (
        # Typically one risk score entry per request within a tenant
        UniqueConstraint("tenant_id", "request_log_id", name="uq_risk_per_request"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_risk_score_bounds"),
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

    # Policy context used (optional)
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

    # Computed risk score (0-100 typical)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Explainability: reasons produced by the risk engine (e.g., ["prompt_injection:ignore_previous_instructions"])
    reasons: Mapped[list[str] | None] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)

    # Whether supporting evidence was present at scoring time
    evidence_present: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("risk_scores", passive_deletes=True))
    request_log: Mapped["RequestLog"] = relationship(
        "RequestLog", backref=backref("risk_scores", passive_deletes=True)
    )
    policy: Mapped["Policy"] = relationship("Policy", backref=backref("risk_scores", passive_deletes=True))
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", backref=backref("risk_scores", passive_deletes=True)
    )

    def __repr__(self) -> str:
        return (
            f"<RiskScore id={self.id!r} tenant_id={self.tenant_id!r} "
            f"request_log_id={self.request_log_id!r} score={self.score!r} "
            f"evidence_present={self.evidence_present!r}>"
        )
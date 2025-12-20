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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RiskScore(Base):
    """
    Minimal viable RiskScore entity.
    """

    __tablename__ = "risk_score"
    __table_args__ = (
        # Typically one risk score entry per request within a tenant
        UniqueConstraint("tenant_id", "request_log_id", name="uq_risk_per_request"),
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
    reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)

    # Whether supporting evidence was present at scoring time
    evidence_present: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", backref="risk_scores")
    request_log = relationship("RequestLog", backref="risk_scores")
    policy = relationship("Policy", backref="risk_scores")
    policy_version = relationship("PolicyVersion", backref="risk_scores")

    def __repr__(self) -> str:
        return (
            f"<RiskScore id={self.id!r} tenant_id={self.tenant_id!r} "
            f"request_log_id={self.request_log_id!r} score={self.score!r} "
            f"evidence_present={self.evidence_present!r}>"
        )
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

    # ===============================
    # ENHANCED COMPLIANCE AUDIT FIELDS
    # ===============================

    # Complete decision reasoning chain: which rules triggered, evaluation order, scores
    # Structure: {
    #   "rules_evaluated": [{"rule_id": "...", "triggered": bool, "score": float}],
    #   "policy_checks": [{"check": "blocked_terms", "result": bool, "matched": [...]}],
    #   "intent_classifications": [{"intent": "...", "score": float, "threshold": float}],
    #   "risk_factors": [{"factor": "...", "contribution": float}]
    # }
    reasoning_chain: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Regulatory frameworks that were active for this decision
    compliance_frameworks: Mapped[list[str] | None] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
    )

    # Mappings to specific regulatory articles/controls that governed this decision
    # Structure: {
    #   "eu_ai_act_high_risk": ["Article 9", "Article 14"],
    #   "nist_ai_rmf": ["GOVERN-1.2", "MEASURE-2.1"]
    # }
    regulatory_mappings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Detailed engine scores from various evaluators
    # Structure: {
    #   "risk_engine_score": 75.5,
    #   "pii_detection_score": 20.3,
    #   "intent_classifier_scores": {"weapon_instruction": 0.85},
    #   "evidence_quality_score": 90.0
    # }
    engine_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Snapshot of the complete policy version at decision time (for auditability)
    # Includes: policy_doc, compliance configs, validation status
    # This ensures we can recreate exact decision context even if policy changes
    policy_version_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

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
        frameworks = f" frameworks={len(self.compliance_frameworks or [])}" if self.compliance_frameworks else ""
        return (
            f"<DecisionLog id={self.id!r} tenant_id={self.tenant_id!r} "
            f"request_log_id={self.request_log_id!r} allowed={self.allowed!r} "
            f"risk_score={self.risk_score!r}{frameworks}>"
        )
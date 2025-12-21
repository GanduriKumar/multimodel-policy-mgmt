"""
EvidenceItem model (MVP).

Represents an evidence artifact (e.g., URL, document reference, metadata) that can
support a policy, a particular policy version, or be associated with a tenant broadly.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref, declared_attr
from sqlalchemy.ext.mutable import MutableDict

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.tenant import Tenant
    from app.models.policy import Policy
    from app.models.policy_version import PolicyVersion


class EvidenceItem(Base):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "evidence_item"
    __table_args__ = (
        # Prevent duplicate artifacts within a tenant (best-effort; content_hash may be null)
        UniqueConstraint("tenant_id", "content_hash", name="uq_evidence_tenant_hash"),
    )

    # Identity
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Evidence fields
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deterministic content hash (sha256 of content/source/description as computed by repo)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Arbitrary metadata (tracked for in-place JSON mutations)
    metadata: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )

    # Optional policy linkage
    policy_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy.id", ondelete="SET NULL"), nullable=True, index=True
    )
    policy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("policy_version.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), index=True
    )

    # Relationships (lazy select-in for batch efficiency)
    tenant: "Mapped[Tenant]" = relationship(
        "Tenant", backref=backref("evidence_items", lazy="selectin")
    )
    policy: "Mapped[Policy] | None" = relationship(
        "Policy", backref=backref("evidence_items", lazy="selectin")
    )
    policy_version: "Mapped[PolicyVersion] | None" = relationship(
        "PolicyVersion", backref=backref("evidence_items", lazy="selectin")
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EvidenceItem id={self.id!r} tenant_id={self.tenant_id!r} "
            f"type={self.evidence_type!r} src={self.source!r}>"
        )


__all__ = ["EvidenceItem"]
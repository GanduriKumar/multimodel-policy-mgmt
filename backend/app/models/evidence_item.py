"""
EvidenceItem model (MVP).

Represents an evidence artifact (e.g., URL, document reference, metadata) that can
support a policy, a particular policy version, or be associated with a tenant broadly.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvidenceItem(Base):
    """
    Minimal viable EvidenceItem entity.
    """

    __tablename__ = "evidence_item"
    __table_args__ = (
        # Optional de-duplication by tenant + content_hash if provided
        UniqueConstraint(
            "tenant_id", "content_hash", name="uq_evidence_tenant_hash"
        ),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional linkage to a policy or a specific policy version
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

    # Evidence descriptor
    evidence_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., "url", "document", "dataset"
    source: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # e.g., URL or identifier
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional content hash (e.g., SHA-256 hex) for deduplication/integrity
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Arbitrary metadata payload (structured)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", backref="evidence_items")
    policy = relationship("Policy", backref="evidence_items")
    policy_version = relationship("PolicyVersion", backref="evidence_items")

    def __repr__(self) -> str:
        return (
            f"<EvidenceItem id={self.id!r} tenant_id={self.tenant_id!r} "
            f"type={self.evidence_type!r} source={self.source!r}>"
        )
"""
EvidenceBundle model.

Captures a group of retrieval chunks associated with a source URI, along with
document-level and chunk-level hashes, timestamps, and optional claim references.

Typical usage:
- Persist the chunks returned by RAG retrieval for later audit/explanation.
- Deduplicate by (tenant_id, document_hash, chunk_hash, source_uri) when applicable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.mutable import MutableList

from app.db.base import Base


class EvidenceBundle(Base):
    """A tenant-scoped bundle of retrieval chunks and provenance metadata."""

    __tablename__ = "evidence_bundle"
    __table_args__ = (
        # Optional deduping key when hashes/URI are available
        UniqueConstraint(
            "tenant_id",
            "document_hash",
            "chunk_hash",
            "source_uri",
            name="uq_bundle_tenant_doc_chunk_src",
        ),
        Index("ix_bundle_tenant_created", "tenant_id", "created_at"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provenance
    source_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    document_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chunk_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Retrieval chunks (ordered), e.g., list of text snippets
    chunks: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=False, default=list
    )

    # Optional claim references providing linkage to claims/assertions
    # Recommended shape per item (not enforced): {"id": str, "span": [start, end], "confidence": float}
    claim_references: Mapped[list[dict] | None] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", backref=backref("evidence_bundles", passive_deletes=True)
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<EvidenceBundle id={self.id!r} tenant_id={self.tenant_id!r} "
            f"source_uri={self.source_uri!r} doc_hash={self.document_hash!r} chunk_hash={self.chunk_hash!r}>"
        )

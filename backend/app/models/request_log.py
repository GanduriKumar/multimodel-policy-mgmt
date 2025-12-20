"""
RequestLog model (MVP).

Captures an inbound request to evaluate content/policy, along with basic context.
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


class RequestLog(Base):
    """
    Minimal viable RequestLog entity.
    """

    __tablename__ = "request_log"
    __table_args__ = (
        # Optional de-duplication within tenant by input_hash if provided
        UniqueConstraint("tenant_id", "input_hash", name="uq_request_tenant_input_hash"),
        # Optional uniqueness for a client-provided request identifier within a tenant
        UniqueConstraint("tenant_id", "request_id", name="uq_request_tenant_request_id"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional linkage to a policy or a specific policy version used in the request
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

    # Client-supplied correlation/request identifier (optional)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Original input text being evaluated (store for auditing)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional SHA-256 hex (or similar) of input_text for deduplication
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Contextual info
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Arbitrary request metadata (e.g., headers, tags)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", backref="request_logs")
    policy = relationship("Policy", backref="request_logs")
    policy_version = relationship("PolicyVersion", backref="request_logs")

    def __repr__(self) -> str:
        return (
            f"<RequestLog id={self.id!r} tenant_id={self.tenant_id!r} "
            f"policy_id={self.policy_id!r} policy_version_id={self.policy_version_id!r}>"
        )
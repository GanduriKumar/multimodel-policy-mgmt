"""
Policy model (MVP).

Represents a policy owned by a tenant. Policies can have multiple versions.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from app.db.base import Base


class Policy(Base):
    """
    Minimal viable Policy entity.
    """

    __tablename__ = "policy"
    __table_args__ = (
        # Ensure per-tenant uniqueness for human identifiers
        UniqueConstraint("tenant_id", "name", name="uq_policy_tenant_name"),
        UniqueConstraint("tenant_id", "slug", name="uq_policy_tenant_slug"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Ownership
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identifiers
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Active flag
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", backref=backref("policies", passive_deletes=True))
    versions: Mapped[list["PolicyVersion"]] = relationship(
        "PolicyVersion",
        back_populates="policy",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Policy id={self.id!r} tenant_id={self.tenant_id!r} slug={self.slug!r} active={self.is_active!r}>"
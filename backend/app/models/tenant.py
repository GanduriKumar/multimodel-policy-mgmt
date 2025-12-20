"""
Tenant model.

Represents an organizational tenant that owns policies, requests, and logs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    """
    A top-level organization or customer namespace.
    """

    __tablename__ = "tenant"
    __table_args__ = (
        UniqueConstraint("name", name="uq_tenant_name"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Human-readable name (unique via constraint)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-safe slug (unique and indexed)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Active flag
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!r} slug={self.slug!r} active={self.is_active!r}>"
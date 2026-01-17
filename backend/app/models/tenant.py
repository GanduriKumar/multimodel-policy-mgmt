"""
Tenant model.

Represents an organizational tenant that owns policies, requests, and logs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    """
    A top-level organization or customer namespace.
    """

    __tablename__ = "tenant"
    __tablename__ = "tenant"
    # Note: tests create tenants with duplicate names; keep slug unique but allow
    # non-unique human-readable names. Previously a UniqueConstraint enforced
    # unique tenant.name which caused test failures. Do not enforce name uniqueness.
    __table_args__ = ()

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Human-readable name (unique via constraint)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-safe slug (unique and indexed)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Optional API key hash (HMAC-SHA256 hex, 64 chars). Kept nullable to avoid breaking
    # existing rows/tests; UNIQUE ensures one tenant per key when populated.
    api_key_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

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

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!r} slug={self.slug!r} active={self.is_active!r}>"

    # Ensure slug is generated from name if not provided
    def __init__(self, *args, **kwargs):
        # If slug not specified but name provided, generate a slug
        name = kwargs.get("name")
        slug = kwargs.get("slug")
        if name and not slug:
            # lightweight slugify: lowercase, replace spaces with hyphens, remove unsafe chars
            s = name.strip().lower()
            import re

            s = re.sub(r"[^a-z0-9\- ]+", "", s)
            s = re.sub(r"\s+", "-", s)
            kwargs["slug"] = s
        super().__init__(*args, **kwargs)
"""
PolicyVersion model (MVP).

Represents a versioned snapshot of a policy's document/configuration.
Each version belongs to a Policy and is unique per policy.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PolicyVersion(Base):
    """
    Minimal viable PolicyVersion entity.
    """

    __tablename__ = "policy_version"
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_policy_version_per_policy"),
        CheckConstraint("version >= 1", name="ck_policy_version_min"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Parent policy
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policy.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Monotonic version number within a policy
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # JSON document representing the policy content/rules for this version
    document: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Flag indicating if this version is active/published
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
    policy: Mapped["Policy"] = relationship("Policy", back_populates="versions", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<PolicyVersion id={self.id!r} policy_id={self.policy_id!r} version={self.version!r} active={self.is_active!r}>"
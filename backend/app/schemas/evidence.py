"""
Pydantic models for Evidence creation and reading.

Compatible with SQLAlchemy model:
- app.models.evidence_item.EvidenceItem
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

# Support both Pydantic v2 (ConfigDict, from_attributes) and v1 (orm_mode)
try:
    from pydantic import BaseModel, Field, ConfigDict  # type: ignore

    class ORMBase(BaseModel):
        model_config = ConfigDict(from_attributes=True)
except Exception:  # pragma: no cover - fallback for Pydantic v1
    from pydantic import BaseModel, Field  # type: ignore

    class ORMBase(BaseModel):
        class Config:
            orm_mode = True


__all__ = ["EvidenceCreate", "EvidenceOut", "EvidenceListResponse"]


class EvidenceCreate(BaseModel):
    # Evidence type/category (e.g., "url", "document", "dataset")
    evidence_type: str = Field(..., min_length=1, max_length=100, description="Evidence type/category")

    # Optional associations
    policy_id: Optional[int] = Field(default=None, ge=1)
    policy_version_id: Optional[int] = Field(default=None, ge=1)

    # Source reference and human description
    source: Optional[str] = Field(default=None, description="Source reference (e.g., URL or identifier)")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    # Raw content to be hashed for deduplication/integrity (optional)
    # Named 'content' to align with API expectations; repositories may use this to compute content_hash
    content: Optional[str] = Field(default=None, description="Raw content used to compute content hash (optional)")

    # Arbitrary metadata payload
    metadata: Optional[dict] = Field(default=None, description="Structured metadata (optional)")


class EvidenceOut(ORMBase):
    id: int
    tenant_id: int

    # Optional associations
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None

    # Evidence fields
    evidence_type: str
    source: Optional[str] = None
    description: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Optional[dict] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class EvidenceListResponse(BaseModel):
    items: list[EvidenceOut] = Field(default_factory=list)
    total: int = Field(..., ge=0)
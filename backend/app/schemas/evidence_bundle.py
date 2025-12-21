"""
Pydantic schemas for EvidenceBundle.

Defines request/response models for API integration and internal usage.
Compatible with Pydantic v1 and v2 (uses model_dump when available).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore


class ClaimRef(BaseModel):
    """Lightweight reference to a claim/assertion tied to retrieved chunks."""

    id: Optional[str] = Field(default=None, description="Identifier of the claim/reference")
    span: Optional[List[int]] = Field(
        default=None, description="Optional [start, end] offsets into a related text"
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EvidenceBundleBase(BaseModel):
    tenant_id: int = Field(..., description="Owning tenant id")
    source_uri: Optional[str] = Field(default=None, max_length=1024)
    document_hash: Optional[str] = Field(default=None, max_length=64)
    chunk_hash: Optional[str] = Field(default=None, max_length=64)
    chunks: List[str] = Field(default_factory=list, description="Ordered retrieval chunks")
    claim_references: Optional[List[ClaimRef]] = Field(default=None)


class EvidenceBundleCreate(EvidenceBundleBase):
    """Payload to create a new EvidenceBundle."""

    pass


class EvidenceBundleOut(EvidenceBundleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

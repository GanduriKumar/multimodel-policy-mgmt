"""
Pydantic models for creating and listing Policies and Policy Versions.

Designed to be compatible with the SQLAlchemy models:
- app.models.policy.Policy
- app.models.policy_version.PolicyVersion
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


# -------------------------------
# Policy Schemas
# -------------------------------

class PolicyCreate(BaseModel):
    tenant_id: int = Field(..., ge=1, description="Owner tenant id")
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, description="URL-safe identifier")
    description: Optional[str] = Field(default=None, description="Optional policy description")
    is_active: bool = Field(default=True)


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class PolicyOut(ORMBase):
    id: int
    tenant_id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyListResponse(BaseModel):
    items: list[PolicyOut] = Field(default_factory=list)
    total: int = Field(..., ge=0)


# -------------------------------
# Policy Version Schemas
# -------------------------------

class PolicyVersionCreate(BaseModel):
    policy_id: int = Field(..., ge=1, description="Parent policy id")
    document: dict = Field(..., description="Policy document payload for this version")
    is_active: bool = Field(default=True, description="Whether to activate this version")


class PolicyVersionOut(ORMBase):
    id: int
    policy_id: int
    version: int
    document: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyVersionListResponse(BaseModel):
    items: list[PolicyVersionOut] = Field(default_factory=list)
    total: int = Field(..., ge=0)
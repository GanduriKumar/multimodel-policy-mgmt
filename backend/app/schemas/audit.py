"""
Pydantic models for Audit listings and Decision details.

- AuditListRow: Minimal fields for listing recent requests/decisions.
- DecisionDetail: Rich detail for a specific decision, including policy/risk reasons and evidence references.
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


__all__ = [
    "AuditListRow",
    "AuditListResponse",
    "DecisionDetail",
]


class AuditListRow(ORMBase):
    """
    Row model for audit listings.
    """
    request_log_id: int = Field(..., ge=1, description="Request log identifier")
    tenant_id: int = Field(..., ge=1, description="Tenant identifier")
    decision_id: Optional[int] = Field(default=None, ge=1, description="Associated decision identifier (if any)")
    decision: Optional[bool] = Field(default=None, description="Decision outcome if available")
    risk_score: Optional[int] = Field(default=None, ge=0, le=100, description="Risk score if available")
    created_at: datetime = Field(..., description="Request creation timestamp")


class AuditListResponse(BaseModel):
    """
    Paginated response for audit listings.
    """
    items: list[AuditListRow] = Field(default_factory=list)
    total: int = Field(..., ge=0)


class DecisionDetail(ORMBase):
    """
    Detailed view of a decision, including explainability and references.
    """
    # Core identifiers
    decision_id: int = Field(..., ge=1, description="Decision log identifier")
    request_log_id: int = Field(..., ge=1, description="Originating request identifier")
    tenant_id: int = Field(..., ge=1, description="Tenant identifier")

    # Outcome
    allowed: bool = Field(..., description="Final decision outcome")
    risk_score: Optional[int] = Field(default=None, ge=0, le=100, description="Computed risk score")

    # Policy context (optional)
    policy_id: Optional[int] = Field(default=None, ge=1)
    policy_version_id: Optional[int] = Field(default=None, ge=1)

    # Explainability
    policy_reasons: list[str] = Field(default_factory=list, description="Reasons from policy evaluation")
    risk_reasons: list[str] = Field(default_factory=list, description="Reasons from risk scoring")

    # Evidence references associated with the request/decision
    evidence_ids: list[int] = Field(default_factory=list, description="Referenced evidence item IDs")

    # Timestamps
    created_at: datetime = Field(..., description="Decision creation timestamp")
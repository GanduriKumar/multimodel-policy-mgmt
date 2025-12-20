"""
Pydantic models for the Protect API schema.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


__all__ = ["ProtectRequest", "ProtectResponse"]


class ProtectRequest(BaseModel):
    # Optional tenant identifier (when multi-tenant). Must be positive if provided.
    tenant_id: Optional[int] = Field(default=None, ge=1, description="Tenant identifier (optional)")

    # Optional caller identifiers
    user_id: Optional[str] = Field(default=None, description="End-user identifier (optional)")
    app_id: Optional[str] = Field(default=None, description="Client application identifier (optional)")

    # Text to evaluate
    input_text: str = Field(..., min_length=1, description="Input text to evaluate")

    # Optional evidence references associated with this request
    evidence_ids: list[int] = Field(default_factory=list, description="List of evidence item IDs")


class ProtectResponse(BaseModel):
    # Final decision (True = allow, False = deny)
    decision: bool = Field(..., description="Final decision outcome")

    # Computed risk score (0-100 typical)
    risk_score: int = Field(..., ge=0, le=100, description="Computed risk score")

    # Explainability: reasons from policy evaluation and risk engine
    policy_reasons: list[str] = Field(default_factory=list, description="Reasons from policy evaluation")
    risk_reasons: list[str] = Field(default_factory=list, description="Reasons from risk scoring")

    # Identifier of the persisted decision/audit record
    decision_id: int = Field(..., ge=1, description="Decision log identifier")
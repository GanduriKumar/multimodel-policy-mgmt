"""
Pydantic models for the Protect API schema.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

# Support Pydantic v2 and v1 (import BaseModel, Field only)
try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore

__all__ = ["ProtectRequest", "ProtectResponse"]


class ProtectRequest(BaseModel):
    tenant_id: int = Field(..., ge=1, description="Tenant identifier")
    policy_slug: str = Field(..., min_length=1, description="Policy slug within the tenant")
    input_text: str = Field(..., min_length=1, description="Input text to evaluate")
    # Using Optional[Set[str]] to align with DecisionService and policy engine callsites
    evidence_types: Optional[Set[str]] = Field(
        default=None, description="Set of evidence type strings (e.g., {'url','document'})"
    )
    request_id: Optional[str] = Field(default=None, description="Client-provided correlation ID")
    user_agent: Optional[str] = Field(default=None, description="Caller user agent")
    client_ip: Optional[str] = Field(default=None, description="Caller IP address")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata")


class ProtectResponse(BaseModel):
    # Mirrors app.services.decision_service.ProtectResult
    allowed: bool
    reasons: list[str]
    risk_score: int
    request_log_id: Optional[int] = None
    decision_log_id: Optional[int] = None



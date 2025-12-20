"""
Protect endpoint.

POST /api/protect
- Parses request with Pydantic schema.
- Delegates to DecisionService.protect.
- Returns a typed response model.

No business logic is implemented here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import DecisionService, get_decision_service

__all__ = ["router"]

router = APIRouter()


class ProtectRequest(BaseModel):
    tenant_id: int = Field(..., ge=1, description="Tenant identifier")
    policy_slug: str = Field(..., min_length=1, description="Policy slug within the tenant")
    input_text: str = Field(..., min_length=1, description="Input text to evaluate")
    evidence_types: Optional[Set[str]] = Field(
        default=None, description="Set of evidence type strings (e.g., {'url','document'})"
    )
    request_id: Optional[str] = Field(default=None, description="Client-provided correlation ID")
    user_agent: Optional[str] = Field(default=None, description="Caller user agent")
    client_ip: Optional[str] = Field(default=None, description="Caller IP address")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata")


class ProtectResponse(BaseModel):
    allowed: bool
    reasons: list[str]
    risk_score: int
    request_log_id: Optional[int] = None
    decision_log_id: Optional[int] = None


@router.post("/protect", response_model=ProtectResponse)
def protect_endpoint(
    payload: ProtectRequest,
    service: DecisionService = Depends(get_decision_service),
) -> ProtectResponse:
    """
    Evaluate the input against the active policy and compute risk.
    """
    try:
        result = service.protect(
            tenant_id=payload.tenant_id,
            input_text=payload.input_text,
            policy_slug=payload.policy_slug,
            evidence_types=payload.evidence_types,
            request_id=payload.request_id,
            user_agent=payload.user_agent,
            client_ip=payload.client_ip,
            metadata=payload.metadata,
        )
        return ProtectResponse(**result)
    except ValueError as e:
        # Bad input from client
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        # Unexpected server error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error") from e
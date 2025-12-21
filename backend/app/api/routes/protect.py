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

from app.core.deps import DecisionService, get_decision_service
from app.schemas.protect import ProtectRequest, ProtectResponse  # use shared schema models

router = APIRouter(prefix="/api", tags=["protect"])


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error") from e
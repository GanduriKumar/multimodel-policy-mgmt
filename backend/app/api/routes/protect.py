"""
Protect endpoint.

POST /api/protect
- Parses request with Pydantic schema.
- Delegates to DecisionService.protect.
- Returns a typed response model.

No business logic is implemented here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import DecisionService, get_decision_service
from app.schemas.protect import ProtectRequest, ProtectResponse  # use shared schema models
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.repos.tenant_repo import SqlAlchemyTenantRepo
from app.repos.policy_repo import SqlAlchemyPolicyRepo

router = APIRouter(prefix="/api", tags=["protect"])


@router.post("/protect", response_model=ProtectResponse)
def protect_endpoint(
    payload: ProtectRequest,
    service: DecisionService = Depends(get_decision_service),
    db: Session = Depends(get_db),
) -> ProtectResponse:
    """
    Evaluate the input against the active policy and compute risk.
    """
    try:
        # Validate tenant exists
        t_repo = SqlAlchemyTenantRepo(db)
        if t_repo.get_by_id(payload.tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant not found")

        # Validate policy exists
        p_repo = SqlAlchemyPolicyRepo(db)
        pol = getattr(p_repo, "get_policy_by_id")(int(payload.policy_id))
        if pol is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy not found")

        # Normalize evidence_types to a clean set[str], accepting string CSV or list
        ev = None
        if payload.evidence_types is not None:
            if isinstance(payload.evidence_types, str):
                ev = {s.strip() for s in payload.evidence_types.split(',') if s.strip()}
            else:
                try:
                    ev = {str(x).strip() for x in set(payload.evidence_types) if str(x).strip()}
                except Exception:
                    ev = None

        result = service.protect(
            tenant_id=payload.tenant_id,
            input_text=payload.input_text,
            policy_id=payload.policy_id,
            evidence_types=ev,
            request_id=payload.request_id,
            user_agent=payload.user_agent,
            client_ip=payload.client_ip,
            metadata=payload.metadata,
        )
        return ProtectResponse(**result)
    except ValueError as e:
        # Pass through clean messages (e.g., validation) to the client
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        # Fallback: avoid noisy "Internal error" prefix when we already provided clear messages
        msg = str(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg) from e
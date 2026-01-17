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
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo

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

        # Resolve policy ID from slug if needed (if repository supports it). Otherwise, allow slug-only
        p_repo = SqlAlchemyPolicyRepo(db)
        policy_id = payload.policy_id
        if policy_id is None and payload.policy_slug:
            try:
                if hasattr(p_repo, "get_policy_by_slug"):
                    pol = getattr(p_repo, "get_policy_by_slug")(payload.tenant_id, payload.policy_slug)  # type: ignore[attr-defined]
                    if pol is None:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Policy not found with slug: {payload.policy_slug}")
                    policy_id = pol.id
                else:
                    # Repository does not support slug lookup; defer resolution to DecisionService
                    policy_id = None
            except Exception:
                # Defer resolution to DecisionService which can handle slug via PolicyRepo protocol where available
                policy_id = None
        elif policy_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either policy_id or policy_slug must be provided")
        
        # Validate policy exists
        if policy_id is not None:
            pol = getattr(p_repo, "get_policy_by_id")(int(policy_id))
            if pol is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy not found")
        # Resolve active policy version (for linking evidence context when auto-capturing)
        pv = None
        pv_id = None
        if policy_id is not None:
            try:
                if hasattr(p_repo, "get_active_version"):
                    pv = getattr(p_repo, "get_active_version")(int(policy_id))  # type: ignore[attr-defined]
                    pv_id = getattr(pv, "id", None)
            except Exception:
                pv = None
                pv_id = None

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

        # Optional: derive evidence types from provided evidence IDs in metadata
        try:
            e_repo = SqlAlchemyEvidenceRepo(db)
            ids: list[int] = []
            valid_ids: list[int] = []
            if payload.metadata and isinstance(payload.metadata, dict):
                raw_ids = payload.metadata.get("evidence_ids")  # can be list or CSV string
                if isinstance(raw_ids, str):
                    ids = [int(i) for i in raw_ids.split(',') if i.strip().isdigit()]
                elif isinstance(raw_ids, (list, tuple, set)):
                    for i in raw_ids:
                        try:
                            ids.append(int(i))
                        except Exception:
                            continue
            if ids:
                ev = set(ev or set())
                for eid in ids:
                    item = None
                    if hasattr(e_repo, "get_evidence"):
                        item = getattr(e_repo, "get_evidence")(int(eid))  # type: ignore[attr-defined]
                    if item is None and hasattr(e_repo, "get_by_id"):
                        item = getattr(e_repo, "get_by_id")(int(eid))  # type: ignore[attr-defined]
                    if item is not None:
                        et = getattr(item, "evidence_type", None)
                        if isinstance(et, str) and et.strip():
                            ev.add(et.strip())
                        valid_ids.append(int(eid))
            # If no valid IDs were provided, auto-capture the input as an evidence item for audit
            if not valid_ids and policy_id is not None:
                try:
                    created = e_repo.create_evidence(
                        tenant_id=payload.tenant_id,
                        evidence_type="document",
                        content_text=payload.input_text,
                        description="Captured request content",
                        policy_id=int(policy_id),
                        policy_version_id=(int(pv_id) if pv_id else None),
                    )
                    valid_ids = [int(getattr(created, "id"))]
                    ev = set(ev or set())
                    ev.add("document")
                except Exception:
                    # Do not fail main flow if auto-capture fails
                    pass

            # Sanitize metadata to include only valid evidence ids for audit
            try:
                meta = dict(payload.metadata or {})
                meta["evidence_ids"] = valid_ids
                payload.metadata = meta  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            # Do not fail request if evidence lookup fails
            pass

        result = service.protect(
            tenant_id=payload.tenant_id,
            input_text=payload.input_text,
            policy_id=policy_id,
            policy_slug=payload.policy_slug,
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
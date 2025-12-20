"""
Audit API routes.

Endpoints:
- GET /api/audit/requests                -> list recent requests with decision snapshot
- GET /api/audit/decisions/{id}          -> retrieve decision detail by id (or by request id as fallback)

Routes are thin and delegate to AuditRepo and Pydantic schemas.
"""

from __future__ import annotations

from typing import Any, List, Optional, Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.core.deps import get_audit_repo
from app.core.contracts import AuditRepo
from app.schemas.audit import AuditListRow, AuditListResponse, DecisionDetail


router = APIRouter(prefix="/api/audit", tags=["audit"])

T = TypeVar("T")


def _to_row(item: Any, decision: Optional[Any]) -> AuditListRow:
    """
    Convert RequestLog (and optional DecisionLog) to AuditListRow.
    Supports both Pydantic v1/v2 by creating the model from plain fields.
    """
    return AuditListRow(
        request_log_id=getattr(item, "id"),
        tenant_id=getattr(item, "tenant_id"),
        decision_id=(getattr(decision, "id", None) if decision is not None else None),
        decision=(getattr(decision, "allowed", None) if decision is not None else None),
        risk_score=(getattr(decision, "risk_score", None) if decision is not None else None),
        created_at=getattr(item, "created_at"),
    )


def _split_reasons(reasons: List[str]) -> tuple[List[str], List[str]]:
    """
    Split combined reasons into (policy_reasons, risk_reasons) heuristically.
    """
    policy: List[str] = []
    risk: List[str] = []
    for r in reasons or []:
        if r.startswith("prompt_injection:") or r.startswith("pii_like:") or r.startswith("secret_like:") or r.startswith("risk_above_threshold"):
            risk.append(r)
        else:
            policy.append(r)
    return policy, risk


@router.get("/requests", response_model=AuditListResponse)
def list_requests(
    tenant_id: int = Query(..., ge=1, description="Tenant identifier"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    repo: AuditRepo = Depends(get_audit_repo),
) -> AuditListResponse:
    """
    List recent requests with a snapshot of associated decisions (if any).
    """
    items = repo.list_requests(tenant_id=tenant_id, offset=offset, limit=limit)
    rows: List[AuditListRow] = []
    for req in items:
        # Try both possible repo methods for fetching a decision for a request
        dec = None
        if hasattr(repo, "get_decision_detail"):
            dec = getattr(repo, "get_decision_detail")(getattr(req, "id"))  # type: ignore[attr-defined]
        elif hasattr(repo, "get_decision_for_request"):
            dec = getattr(repo, "get_decision_for_request")(getattr(req, "id"))  # type: ignore[attr-defined]
        rows.append(_to_row(req, dec))

    return AuditListResponse(items=rows, total=len(rows))


@router.get("/decisions/{decision_id}", response_model=DecisionDetail)
def get_decision_detail(
    decision_id: int = Path(..., ge=1, description="Decision identifier (or request id fallback)"),
    repo: AuditRepo = Depends(get_audit_repo),
) -> DecisionDetail:
    """
    Retrieve decision detail by id. If the repository doesn't expose a direct
    lookup by decision id, falls back to using request id via get_decision_detail
    or get_decision_for_request.
    """
    decision = None

    # Try common patterns in order of specificity
    if hasattr(repo, "get_decision_by_id"):
        decision = getattr(repo, "get_decision_by_id")(decision_id)  # type: ignore[attr-defined]
    if decision is None and hasattr(repo, "get_decision_detail"):
        decision = getattr(repo, "get_decision_detail")(decision_id)  # type: ignore[attr-defined]
    if decision is None and hasattr(repo, "get_decision_for_request"):
        decision = getattr(repo, "get_decision_for_request")(decision_id)  # type: ignore[attr-defined]

    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    # Build response model
    reasons = list(getattr(decision, "reasons", []) or [])
    policy_reasons, risk_reasons = _split_reasons(reasons)

    return DecisionDetail(
        decision_id=getattr(decision, "id"),
        request_log_id=getattr(decision, "request_log_id"),
        tenant_id=getattr(decision, "tenant_id"),
        allowed=bool(getattr(decision, "allowed")),
        risk_score=getattr(decision, "risk_score", None),
        policy_id=getattr(decision, "policy_id", None),
        policy_version_id=getattr(decision, "policy_version_id", None),
        policy_reasons=policy_reasons,
        risk_reasons=risk_reasons,
        evidence_ids=[],  # Not linked in the MVP
        created_at=getattr(decision, "created_at"),
    )

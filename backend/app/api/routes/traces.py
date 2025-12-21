"""
End-to-end trace visualization API.

Endpoints:
- GET /api/traces/{trace_id}?tenant_id=... -> Correlated request, decision, and ledger entries

Notes:
- trace_id can be the request_log.id (int) or the client-provided request_id (str).
- EvidenceBundles are not directly linked to requests in the current schema; this endpoint focuses on
  request -> decision -> model_output (from the GovernanceLedger) correlation using request_log_id.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog

try:  # Governance ledger is optional but recommended for richer traces
    from app.services.governance_ledger import GovernanceLedger
except Exception:  # pragma: no cover
    GovernanceLedger = None  # type: ignore[assignment]


router = APIRouter(prefix="/api/traces", tags=["traces"])


def _parse_trace_id(value: str) -> tuple[Optional[int], Optional[str]]:
    """Return (request_log_id, client_request_id)."""
    try:
        return int(value), None
    except ValueError:
        return None, value


def _fetch_request(db: Session, tenant_id: int, *, request_log_id: Optional[int], client_request_id: Optional[str]) -> Optional[RequestLog]:
    if request_log_id is not None:
        stmt = select(RequestLog).where(RequestLog.id == request_log_id, RequestLog.tenant_id == tenant_id)
        return db.execute(stmt).scalars().first()
    if client_request_id is not None:
        stmt = select(RequestLog).where(RequestLog.request_id == client_request_id, RequestLog.tenant_id == tenant_id)
        return db.execute(stmt).scalars().first()
    return None


def _fetch_decision(db: Session, *, request_log_id: int) -> Optional[DecisionLog]:
    stmt = select(DecisionLog).where(DecisionLog.request_log_id == request_log_id)
    return db.execute(stmt).scalars().first()


def _load_ledger_entries_for_request(ledger: GovernanceLedger, *, request_log_id: int) -> List[Dict[str, Any]]:  # type: ignore[name-defined]
    """
    Read the governance ledger JSONL file and return entries matching request_log_id.
    Includes kinds: request, decision, model_output.
    """
    import json
    import os

    entries: List[Dict[str, Any]] = []
    path = getattr(ledger, "path", None)
    if not path or not os.path.exists(path):
        return entries

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get("kind") not in {"request", "decision", "model_output"}:
                continue
            body = entry.get("body", {}) or {}
            if body.get("request_log_id") == request_log_id:
                entries.append(entry)
    return entries


@router.get("/{trace_id}")
def get_trace(
    trace_id: str = Path(..., description="request_log.id (int) or client request_id (str)"),
    tenant_id: int = Query(..., ge=1, description="Tenant identifier"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return a correlated view of request -> decision plus any matching governance ledger entries.
    """
    req_id, client_req_id = _parse_trace_id(trace_id)
    req = _fetch_request(db, tenant_id, request_log_id=req_id, client_request_id=client_req_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found (request)")

    dec = _fetch_decision(db, request_log_id=req.id)

    # Attempt to enrich from governance ledger when available
    ledger_entries: List[Dict[str, Any]] = []
    if GovernanceLedger is not None:
        try:
            ledger = GovernanceLedger()
            ledger_entries = _load_ledger_entries_for_request(ledger, request_log_id=req.id)
        except Exception:
            ledger_entries = []

    # Build response shape
    request_view = {
        "id": req.id,
        "tenant_id": req.tenant_id,
        "policy_id": req.policy_id,
        "policy_version_id": req.policy_version_id,
        "request_id": req.request_id,
        "input_hash": req.input_hash,
        "user_agent": req.user_agent,
        "client_ip": req.client_ip,
        "metadata": req.metadata,
        "created_at": req.created_at,
    }

    decision_view: Optional[Dict[str, Any]] = None
    if dec is not None:
        decision_view = {
            "id": dec.id,
            "request_log_id": dec.request_log_id,
            "allowed": bool(dec.allowed),
            "reasons": list(dec.reasons or []),
            "risk_score": dec.risk_score,
            "policy_id": dec.policy_id,
            "policy_version_id": dec.policy_version_id,
            "created_at": dec.created_at,
        }

    return {
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "request": request_view,
        "decision": decision_view,
        "ledger": ledger_entries,
        # EvidenceBundles are not directly correlated to requests in current schema.
        # This can be enhanced in a future iteration once linkage is available.
        "evidence": [],
    }

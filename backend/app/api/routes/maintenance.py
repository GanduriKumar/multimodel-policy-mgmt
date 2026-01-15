"""
Admin/Maintenance routes.

Endpoints:
- POST /api/admin/reset-all  -> danger reset: clears evidence, audit logs, policies/versions

Use with caution. Intended for local/dev resets.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evidence_item import EvidenceItem
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog
from app.models.risk_score import RiskScore
from app.models.policy_version import PolicyVersion
from app.models.policy import Policy

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-all")
def reset_all(db: Session = Depends(get_db)) -> dict:
    """
    Danger reset: delete all rows from evidence, audit logs, policies and versions.
    Preserves tenants.
    """
    try:
        cleared: list[str] = []
        # Order matters due to FKs
        db.execute(delete(DecisionLog))
        cleared.append("decision_log")
        db.execute(delete(RiskScore))
        cleared.append("risk_score")
        db.execute(delete(RequestLog))
        cleared.append("request_log")
        db.execute(delete(EvidenceItem))
        cleared.append("evidence_item")
        db.execute(delete(PolicyVersion))
        cleared.append("policy_version")
        db.execute(delete(Policy))
        cleared.append("policy")
        db.commit()
        return {"ok": True, "cleared": cleared}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

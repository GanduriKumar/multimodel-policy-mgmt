"""
SQLAlchemy-based Audit repository.

Implements:
- log_request: persist a RequestLog (computes input_hash if missing)
- log_decision: persist a DecisionLog for a given request
- list_requests: list recent RequestLog rows for a tenant with pagination
- get_decision_detail: fetch the DecisionLog for a given request (if any)
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashing import sha256_text
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog


class SqlAlchemyAuditRepo:
    """
    Concrete Audit repository using SQLAlchemy ORM.
    """

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("session must be an instance of sqlalchemy.orm.Session")
        self.session = session

    # -------------------------------
    # Request Logs
    # -------------------------------

    def log_request(
        self,
        *,
        tenant_id: int,
        input_text: str,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        input_hash: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> RequestLog:
        """
        Persist and return a RequestLog entry. Computes input_hash if not provided.
        """
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(input_text, str):
            raise TypeError("input_text must be a str")

        # Compute deterministic hash if missing
        ihash = input_hash or sha256_text(input_text)

        req = RequestLog(
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            request_id=request_id,
            input_text=input_text,
            input_hash=ihash,
            user_agent=user_agent,
            client_ip=client_ip,
            metadata=metadata,
        )
        self.session.add(req)
        self.session.commit()
        self.session.refresh(req)
        return req

    def list_requests(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[RequestLog]:
        """
        List recent RequestLog rows for a tenant, newest first.
        """
        stmt = (
            select(RequestLog)
            .where(RequestLog.tenant_id == tenant_id)
            .order_by(RequestLog.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, limit))
        )
        return list(self.session.execute(stmt).scalars().all())

    # -------------------------------
    # Decision Logs
    # -------------------------------

    def log_decision(
        self,
        *,
        tenant_id: int,
        request_log_id: int,
        allowed: bool,
        reasons: Optional[list[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        risk_score: Optional[int] = None,
    ) -> DecisionLog:
        """
        Persist and return a DecisionLog entry linked to a RequestLog.
        """
        if not isinstance(tenant_id, int):
            raise TypeError("tenant_id must be an int")
        if not isinstance(request_log_id, int):
            raise TypeError("request_log_id must be an int")

        dec = DecisionLog(
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            allowed=bool(allowed),
            reasons=list(reasons) if reasons is not None else [],
            risk_score=risk_score,
        )
        self.session.add(dec)
        self.session.commit()
        self.session.refresh(dec)
        return dec

    def get_decision_detail(self, request_log_id: int) -> Optional[DecisionLog]:
        """
        Return the DecisionLog for the given request_log_id, if any.
        """
        stmt = select(DecisionLog).where(DecisionLog.request_log_id == request_log_id)
        return self.session.execute(stmt).scalars().first()
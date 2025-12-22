"""
SQLAlchemy-based Audit repository.

Implements:
- log_request: persist a RequestLog (computes input_hash if missing)
- list_requests: list recent RequestLog rows for a tenant with pagination
- get_request: fetch a RequestLog by id
- log_decision: persist a DecisionLog for a given request
- get_decision_detail/get_decision_for_request: fetch DecisionLog by request id
- get_decision_by_id: fetch DecisionLog by decision id
- log_risk_score: persist a RiskScore for a request (optional protocol)
- get_risk_for_request: fetch RiskScore by request id
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashing import sha256_text
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog
from app.models.risk_score import RiskScore


__all__ = ["SqlAlchemyAuditRepo"]


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
            metadata_json=metadata,
        )
        self.session.add(req)
        self.session.commit()
        self.session.refresh(req)
        return req

    def get_request(self, request_log_id: int) -> Optional[RequestLog]:
        stmt = select(RequestLog).where(RequestLog.id == int(request_log_id))
        return self.session.execute(stmt).scalars().first()

    def list_requests(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[RequestLog]:
        """
        List recent RequestLog rows for a tenant, newest first.
        """
        stmt = (
            select(RequestLog)
            .where(RequestLog.tenant_id == tenant_id)
            .order_by(RequestLog.created_at.desc())
            .offset(max(0, int(offset)))
            .limit(max(1, int(limit)))
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
        dec = DecisionLog(
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            allowed=bool(allowed),
            reasons=list(reasons or []),
            policy_id=policy_id,
            policy_version_id=policy_version_id,
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
        stmt = select(DecisionLog).where(DecisionLog.request_log_id == int(request_log_id))
        return self.session.execute(stmt).scalars().first()

    # Alias used by some callers
    def get_decision_for_request(self, request_log_id: int) -> Optional[DecisionLog]:
        return self.get_decision_detail(request_log_id)

    def get_decision_by_id(self, decision_id: int) -> Optional[DecisionLog]:
        stmt = select(DecisionLog).where(DecisionLog.id == int(decision_id))
        return self.session.execute(stmt).scalars().first()

    # -------------------------------
    # Risk Scores (optional)
    # -------------------------------

    def log_risk_score(
        self,
        *,
        tenant_id: int,
        request_log_id: int,
        score: int,
        reasons: Optional[list[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        evidence_present: bool = False,
    ) -> RiskScore:
        """
        Persist and return a RiskScore entry linked to a RequestLog.
        """
        rs = RiskScore(
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            score=int(score),
            reasons=list(reasons or []),
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            evidence_present=bool(evidence_present),
        )
        self.session.add(rs)
        self.session.commit()
        self.session.refresh(rs)
        return rs

    def get_risk_for_request(self, request_log_id: int) -> Optional[RiskScore]:
        stmt = select(RiskScore).where(RiskScore.request_log_id == int(request_log_id))
        return self.session.execute(stmt).scalars().first()
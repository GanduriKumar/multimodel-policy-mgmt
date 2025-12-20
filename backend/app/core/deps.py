"""
Dependency wiring for repositories and decision service.

- Returns interface (Protocol) types for easy overriding in tests.
- Concrete implementations use SQLAlchemy-based repos.
- Provides a thin DecisionService wrapper around the protect(...) function.

In FastAPI, you can override these dependencies in tests:
    app.dependency_overrides[get_policy_repo] = lambda: FakePolicyRepo()
    app.dependency_overrides[get_decision_service] = lambda: MyCustomDecisionService(...)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.contracts import PolicyRepo, EvidenceRepo, AuditRepo
from app.db.session import get_db
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from app.services.decision_service import protect, ProtectResult


__all__ = [
    "get_policy_repo",
    "get_evidence_repo",
    "get_audit_repo",
    "DecisionService",
    "get_decision_service",
]


# -------------------------------
# Repository Providers
# -------------------------------

def get_policy_repo(db: Session = Depends(get_db)) -> PolicyRepo:
    """
    Provide a PolicyRepo bound to the current DB session.
    """
    return SqlAlchemyPolicyRepo(db)


def get_evidence_repo(db: Session = Depends(get_db)) -> EvidenceRepo:
    """
    Provide an EvidenceRepo bound to the current DB session.
    """
    return SqlAlchemyEvidenceRepo(db)


def get_audit_repo(db: Session = Depends(get_db)) -> AuditRepo:
    """
    Provide an AuditRepo bound to the current DB session.
    """
    return SqlAlchemyAuditRepo(db)


# -------------------------------
# Decision Service
# -------------------------------

class DecisionService:
    """
    Thin wrapper that binds repos to the protect(...) orchestration function.

    Depends only on Protocol interfaces; easy to swap with fakes in tests.
    """

    def __init__(self, policy_repo: PolicyRepo, evidence_repo: EvidenceRepo, audit_repo: AuditRepo) -> None:
        self.policy_repo = policy_repo
        self.evidence_repo = evidence_repo
        self.audit_repo = audit_repo

    def protect(
        self,
        *,
        tenant_id: int,
        input_text: str,
        policy_slug: str,
        evidence_types: Optional[Set[str]] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProtectResult:
        """
        Delegate to the module-level protect function with bound repositories.
        """
        return protect(
            tenant_id=tenant_id,
            input_text=input_text,
            policy_slug=policy_slug,
            evidence_types=evidence_types,
            policy_repo=self.policy_repo,
            evidence_repo=self.evidence_repo,
            audit_repo=self.audit_repo,
            request_id=request_id,
            user_agent=user_agent,
            client_ip=client_ip,
            metadata=metadata,
        )


def get_decision_service(
    policy_repo: PolicyRepo = Depends(get_policy_repo),
    evidence_repo: EvidenceRepo = Depends(get_evidence_repo),
    audit_repo: AuditRepo = Depends(get_audit_repo),
) -> DecisionService:
    """
    Provide a DecisionService constructed from the repo dependencies.
    """
    return DecisionService(policy_repo=policy_repo, evidence_repo=evidence_repo, audit_repo=audit_repo)
"""
Dependency wiring for repositories, decision service, and governed generation.

This module exposes factory functions that construct concrete implementations
behind Protocol-like interfaces. It must not contain business logic.

Provided factories:
- get_policy_repo / get_evidence_repo / get_audit_repo
- DecisionService and get_decision_service
- get_llm_client (Ollama by default)
- get_rag_proxy
- get_governance_ledger
- get_groundedness_engine
- get_governed_generation_service (composes the above)
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.contracts import AuditRepo, EvidenceRepo, PolicyRepo
from app.db.session import get_db
from app.services.decision_service import ProtectResult, protect

# Optional imports are guarded to avoid hard failures when optional deps aren't present
try:  # Optional at import time; concrete implementations may not be used in all contexts
    from app.services.llm_gateway import LLMClient, OllamaLLMClient  # type: ignore
except Exception:  # pragma: no cover
    LLMClient = Any  # type: ignore
    OllamaLLMClient = None  # type: ignore

try:
    from app.services.rag_proxy import RAGProxy  # type: ignore
except Exception:  # pragma: no cover
    RAGProxy = Any  # type: ignore

try:
    from app.services.governance_ledger import GovernanceLedger  # type: ignore
except Exception:  # pragma: no cover
    GovernanceLedger = Any  # type: ignore

try:
    from app.services.groundedness_engine import GroundednessEngine  # type: ignore
except Exception:  # pragma: no cover
    GroundednessEngine = Any  # type: ignore

__all__ = [
    # repos
    "get_policy_repo",
    "get_evidence_repo",
    "get_audit_repo",
    # decision
    "DecisionService",
    "get_decision_service",
    # llm/rag/ledger/groundedness
    "get_llm_client",
    "get_rag_proxy",
    "get_governance_ledger",
    "get_groundedness_engine",
    # governed generation
    "get_governed_generation_service",
]

# -------------------------------
# Repository Providers
# -------------------------------

def get_policy_repo(db: Session = Depends(get_db)) -> PolicyRepo:
    """Provide a PolicyRepo bound to the current DB session."""
    from app.repos.policy_repo import SqlAlchemyPolicyRepo
    return SqlAlchemyPolicyRepo(db)  # type: ignore[return-value]

def get_evidence_repo(db: Session = Depends(get_db)) -> EvidenceRepo:
    """Provide an EvidenceRepo bound to the current DB session."""
    from app.repos.evidence_repo import SqlAlchemyEvidenceRepo
    return SqlAlchemyEvidenceRepo(db)  # type: ignore[return-value]

def get_audit_repo(db: Session = Depends(get_db)) -> AuditRepo:
    """Provide an AuditRepo bound to the current DB session."""
    from app.repos.audit_repo import SqlAlchemyAuditRepo
    return SqlAlchemyAuditRepo(db)  # type: ignore[return-value]

# -------------------------------
# Decision Service
# -------------------------------

class DecisionService:
    """Thin wrapper that binds repos to the protect(...) orchestration function."""

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
        """Delegate to the module-level protect function with bound repositories."""
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
    """Provide a DecisionService with bound repositories."""
    return DecisionService(policy_repo=policy_repo, evidence_repo=evidence_repo, audit_repo=audit_repo)

# -------------------------------
# Optional service providers (LLM/RAG/Ledger/Groundedness)
# -------------------------------

def get_llm_client() -> LLMClient:  # type: ignore[valid-type]
    """
    Return an LLM client instance. Selection can be extended to read from settings.
    Default is a no-op or Ollama client if available.
    """
    if OllamaLLMClient is not None:
        return OllamaLLMClient()  # type: ignore[call-arg]
    # Fallback placeholder; callers should handle capabilities accordingly.
    return LLMClient  # type: ignore[return-value]

def get_rag_proxy() -> RAGProxy:  # type: ignore[valid-type]
    return RAGProxy()  # type: ignore[call-arg]

def get_governance_ledger() -> GovernanceLedger:  # type: ignore[valid-type]
    return GovernanceLedger()  # type: ignore[call-arg]

def get_groundedness_engine() -> GroundednessEngine:  # type: ignore[valid-type]
    return GroundednessEngine()  # type: ignore[call-arg]

# -------------------------------
# Governed generation service
# -------------------------------

def get_governed_generation_service(
    decision_service: DecisionService = Depends(get_decision_service),
):
    """
    Provide a GovernedGenerationService instance wired with optional dependencies.
    Kept loosely typed here to avoid import-time hard deps.
    """
    from app.services.governed_generation_service import GovernedGenerationService
    return GovernedGenerationService(
        llm_client=get_llm_client(),
        rag_proxy=get_rag_proxy(),
        ledger=get_governance_ledger(),
        groundedness_engine=get_groundedness_engine(),
        decision_service=decision_service,
    )
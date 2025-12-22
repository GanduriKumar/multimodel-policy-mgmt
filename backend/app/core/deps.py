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

from app.core.contracts import PolicyRepo, EvidenceRepo, AuditRepo
from app.db.session import get_db
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from app.services.decision_service import protect, ProtectResult

# Type imports for return annotations (constructed in factories)
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
    return SqlAlchemyPolicyRepo(db)


def get_evidence_repo(db: Session = Depends(get_db)) -> EvidenceRepo:
    """Provide an EvidenceRepo bound to the current DB session."""
    return SqlAlchemyEvidenceRepo(db)


def get_audit_repo(db: Session = Depends(get_db)) -> AuditRepo:
    """Provide an AuditRepo bound to the current DB session."""
    return SqlAlchemyAuditRepo(db)


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
    """Provide a DecisionService constructed from the repo dependencies."""
    return DecisionService(policy_repo=policy_repo, evidence_repo=evidence_repo, audit_repo=audit_repo)


# -------------------------------
# LLM / RAG / Ledger / Groundedness Providers
# -------------------------------

def get_llm_client() -> LLMClient:  # type: ignore[valid-type]
    """Provide a default LLM client (Ollama-based) suitable for local development."""
    if OllamaLLMClient is None:  # pragma: no cover
        raise RuntimeError("OllamaLLMClient unavailable; ensure dependencies are installed")
    return OllamaLLMClient()


def get_rag_proxy() -> RAGProxy:  # type: ignore[valid-type]
    """Provide a RAGProxy instance (in-memory)."""
    return RAGProxy()


def get_governance_ledger() -> GovernanceLedger:  # type: ignore[valid-type]
    """Provide a GovernanceLedger instance with settings-based configuration."""
    return GovernanceLedger()


def get_groundedness_engine() -> GroundednessEngine:  # type: ignore[valid-type]
    """Provide a GroundednessEngine with default threshold."""
    return GroundednessEngine()


# -------------------------------
# Governed Generation Orchestrator
# -------------------------------

def get_governed_generation_service(
    decision_service: DecisionService = Depends(get_decision_service),
    llm_client: LLMClient = Depends(get_llm_client),  # type: ignore[valid-type]
    groundedness_engine: GroundednessEngine = Depends(get_groundedness_engine),  # type: ignore[valid-type]
    rag_proxy: RAGProxy = Depends(get_rag_proxy),  # type: ignore[valid-type]
    ledger: GovernanceLedger = Depends(get_governance_ledger),  # type: ignore[valid-type]
):
    """Compose GovernedGenerationService from its parts using local imports to avoid cycles."""
    # Local import to avoid circular import at module load time
    from app.services.governed_generation_service import GovernedGenerationService

    return GovernedGenerationService(
        decision_service=decision_service,
        llm_client=llm_client,
        groundedness_engine=groundedness_engine,
        rag_proxy=rag_proxy,
        ledger=ledger,
    )

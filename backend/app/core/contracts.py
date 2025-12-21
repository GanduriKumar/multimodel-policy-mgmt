"""
Repository contracts (Protocols) for data access layers.

These Protocols define the minimal operations required by the services layer.
Concrete implementations can use SQLAlchemy, HTTP services, or in-memory stores,
as long as they satisfy these interfaces.

Protocols:
- TenantRepo
- PolicyRepo
- EvidenceRepo
- AuditRepo
"""

from __future__ import annotations

from typing import Optional, Protocol, Sequence, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    # Imported only for type checking to avoid runtime import cycles
    from app.models.tenant import Tenant
    from app.models.policy import Policy
    from app.models.policy_version import PolicyVersion
    from app.models.evidence_item import EvidenceItem
    from app.models.request_log import RequestLog
    from app.models.decision_log import DecisionLog
    from app.models.risk_score import RiskScore

__all__ = ["TenantRepo", "PolicyRepo", "EvidenceRepo", "AuditRepo"]


# -------------------------------
# Tenant Repository
# -------------------------------

@runtime_checkable
class TenantRepo(Protocol):
    """
    Contract for tenant data access.
    """

    def get_by_id(self, tenant_id: int) -> Optional["Tenant"]:
        """Fetch a tenant by id."""
        raise NotImplementedError()

    def create(self, *, name: str) -> "Tenant":
        """Create and return a tenant."""
        raise NotImplementedError()


# -------------------------------
# Policy Repository
# -------------------------------

@runtime_checkable
class PolicyRepo(Protocol):
    """
    Contract for policy and policy-version data access.
    """

    # Policies
    def get_by_slug(self, tenant_id: int, slug: str) -> Optional["Policy"]:
        """Fetch policy by tenant+slug."""
        raise NotImplementedError()

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence["Policy"]:
        """List policies for a tenant."""
        raise NotImplementedError()

    def create_policy(
        self, *, tenant_id: int, name: str, slug: str, description: Optional[str] = None, is_active: bool = True
    ) -> "Policy":
        """Create a policy."""
        raise NotImplementedError()

    def update_policy(
        self, policy_id: int, *, name: Optional[str] = None, slug: Optional[str] = None,
        description: Optional[str] = None, is_active: Optional[bool] = None
    ) -> "Policy":
        """Update a policy."""
        raise NotImplementedError()

    # Versions
    def create_version(self, *, policy_id: int, document: dict, is_active: bool = True) -> "PolicyVersion":
        """Create a policy version."""
        raise NotImplementedError()

    def list_versions(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence["PolicyVersion"]:
        """List versions for a policy."""
        raise NotImplementedError()

    def set_active_version(self, policy_id: int, version: int) -> "PolicyVersion":
        """Mark the given version as active and return it."""
        raise NotImplementedError()

    # Optional alias used by some implementations/tests
    def activate_version(self, policy_id: int, version: int) -> "PolicyVersion":
        """Alias for set_active_version; mark the given version as active and return it."""
        raise NotImplementedError()

    # Convenience lookups
    def get_active_version_for_slug(self, tenant_id: int, slug: str) -> Optional["PolicyVersion"]:
        """Get active version for the policy identified by slug."""
        raise NotImplementedError()


# -------------------------------
# Evidence Repository
# -------------------------------

@runtime_checkable
class EvidenceRepo(Protocol):
    """
    Contract for evidence item data access.

    Note: We keep legacy add_evidence while adding create_evidence/get_evidence to match the SQLAlchemy adapter
    (app.repos.evidence_repo.SqlAlchemyEvidenceRepo) and API routes.
    """

    # Legacy/Protocol-first method (hash provided by caller)
    def add_evidence(
        self,
        tenant_id: int,
        evidence_type: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
        content_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> "EvidenceItem":
        """Create a new evidence item."""
        raise NotImplementedError()

    # Adapter-preferred method (hash computed by adapter)
    def create_evidence(
        self,
        *,
        tenant_id: int,
        evidence_type: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
        content_text: Optional[str] = None,
        metadata: Optional[dict] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> "EvidenceItem":
        """Create a new evidence item; content_hash is computed internally if possible."""
        raise NotImplementedError()

    # Lookups
    def get_by_id(self, evidence_id: int) -> Optional["EvidenceItem"]:
        """Return evidence by id (Protocol naming)."""
        raise NotImplementedError()

    def get_by_hash(self, tenant_id: int, content_hash: str) -> Optional["EvidenceItem"]:
        """Return evidence by content hash within a tenant."""
        raise NotImplementedError()

    # Adapter convenience (match SqlAlchemyEvidenceRepo and API usage)
    def get_evidence(self, evidence_id: int) -> Optional["EvidenceItem"]:
        """Alias/convenience for fetching by id (adapter naming)."""
        raise NotImplementedError()

    def list_evidence_by_ids(self, ids: Sequence[int]) -> Sequence["EvidenceItem"]:
        """Batch fetch by ids."""
        raise NotImplementedError()


# -------------------------------
# Audit/Logging Repository
# -------------------------------

@runtime_checkable
class AuditRepo(Protocol):
    """
    Contract for logging requests, decisions, and risk scores.
    """

    # Request logs
    def log_request(
        self,
        tenant_id: int,
        input_text: str,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        input_hash: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> "RequestLog":
        """Persist and return a request log entry."""
        raise NotImplementedError()

    def get_request(self, request_log_id: int) -> Optional["RequestLog"]:
        """Fetch a request log by id."""
        raise NotImplementedError()

    def list_requests(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence["RequestLog"]:
        """List recent requests for a tenant."""
        raise NotImplementedError()

    # Decision logs
    def log_decision(
        self,
        tenant_id: int,
        request_log_id: int,
        allowed: bool,
        reasons: Optional[list[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        risk_score: Optional[int] = None,
    ) -> "DecisionLog":
        """Persist and return a decision log entry."""
        raise NotImplementedError()

    def get_decision_for_request(self, request_log_id: int) -> Optional["DecisionLog"]:
        """Return the decision log for a given request, if any."""
        raise NotImplementedError()

    # Optional conveniences used by routes/tests
    def get_decision_detail(self, request_log_id: int) -> Optional["DecisionLog"]:
        """Alias for latest decision for the request (if any)."""
        raise NotImplementedError()

    def get_decision_by_id(self, decision_id: int) -> Optional["DecisionLog"]:
        """Return a decision log by id (if present)."""
        raise NotImplementedError()

    # Risk scores
    def log_risk_score(
        self,
        tenant_id: int,
        request_log_id: int,
        score: int,
        reasons: Optional[list[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        evidence_present: bool = False,
    ) -> "RiskScore":
        """Persist and return a risk score entry."""
        raise NotImplementedError()

    def get_risk_for_request(self, request_log_id: int) -> Optional["RiskScore"]:
        """Return the risk score for a given request, if any."""
        raise NotImplementedError()
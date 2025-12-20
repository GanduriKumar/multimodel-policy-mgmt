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

from typing import Any, Iterable, Optional, Protocol, Sequence, runtime_checkable, TYPE_CHECKING

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

    # Reads
    def get_by_id(self, tenant_id: int) -> Optional["Tenant"]:
        """Return a tenant by primary key or None if not found."""
        raise NotImplementedError()

    def get_by_slug(self, slug: str) -> Optional["Tenant"]:
        """Return a tenant by slug or None if not found."""
        raise NotImplementedError()

    def list(self, offset: int = 0, limit: int = 50) -> Sequence["Tenant"]:
        """Return a paginated list of tenants."""
        raise NotImplementedError()

    # Writes
    def create(self, name: str, slug: str, description: Optional[str] = None, is_active: bool = True) -> "Tenant":
        """Create and return a new tenant."""
        raise NotImplementedError()

    def update(self, tenant: "Tenant", **fields: Any) -> "Tenant":
        """Update fields on the tenant and return the updated entity."""
        raise NotImplementedError()

    def delete(self, tenant: "Tenant") -> None:
        """Delete the tenant."""
        raise NotImplementedError()


# -------------------------------
# Policy Repository
# -------------------------------

@runtime_checkable
class PolicyRepo(Protocol):
    """
    Contract for policy and policy-version data access.
    """

    # Policy reads
    def get_policy_by_id(self, policy_id: int) -> Optional["Policy"]:
        """Return a policy by id."""
        raise NotImplementedError()

    def get_policy_by_slug(self, tenant_id: int, slug: str) -> Optional["Policy"]:
        """Return a policy within a tenant by slug."""
        raise NotImplementedError()

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence["Policy"]:
        """List policies for a tenant."""
        raise NotImplementedError()

    # Policy writes
    def create_policy(
        self,
        tenant_id: int,
        name: str,
        slug: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> "Policy":
        """Create and return a new policy."""
        raise NotImplementedError()

    def update_policy(self, policy: "Policy", **fields: Any) -> "Policy":
        """Update fields on a policy."""
        raise NotImplementedError()

    def delete_policy(self, policy: "Policy") -> None:
        """Delete a policy."""
        raise NotImplementedError()

    # PolicyVersion operations
    def add_version(self, policy_id: int, document: dict, is_active: bool = True) -> "PolicyVersion":
        """Create and attach a new version to a policy, optionally marking active."""
        raise NotImplementedError()

    def get_active_version(self, policy_id: int) -> Optional["PolicyVersion"]:
        """Return the currently active version for a policy, if any."""
        raise NotImplementedError()

    def get_version(self, policy_id: int, version: int) -> Optional["PolicyVersion"]:
        """Return a specific policy version."""
        raise NotImplementedError()

    def list_versions(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence["PolicyVersion"]:
        """List versions for a policy."""
        raise NotImplementedError()

    def set_active_version(self, policy_id: int, version: int) -> "PolicyVersion":
        """Mark the given version as active and return it."""
        raise NotImplementedError()


# -------------------------------
# Evidence Repository
# -------------------------------

@runtime_checkable
class EvidenceRepo(Protocol):
    """
    Contract for evidence item data access.
    """

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

    def get_by_id(self, evidence_id: int) -> Optional["EvidenceItem"]:
        """Return evidence by id."""
        raise NotImplementedError()

    def get_by_hash(self, tenant_id: int, content_hash: str) -> Optional["EvidenceItem"]:
        """Return evidence by content hash within a tenant."""
        raise NotImplementedError()

    def list_for_policy(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence["EvidenceItem"]:
        """List evidence items associated with a policy."""
        raise NotImplementedError()

    def delete(self, evidence: "EvidenceItem") -> None:
        """Delete an evidence item."""
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
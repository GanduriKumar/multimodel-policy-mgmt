"""
In-memory fake repositories for testing services without a real database.

Implements Protocol-compatible classes:
- FakePolicyRepo
- FakeEvidenceRepo
- FakeAuditRepo

These are lightweight and deterministic, using simple in-memory structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

from app.core.hashing import sha256_text


# ----------------------------------------
# Internal lightweight entity classes
# ----------------------------------------

@dataclass
class _Tenant:
    id: int
    name: str
    slug: str
    is_active: bool = True


@dataclass
class _Policy:
    id: int
    tenant_id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True


@dataclass
class _PolicyVersion:
    id: int
    policy_id: int
    version: int
    document: Dict[str, Any]
    is_active: bool = True


@dataclass
class _EvidenceItem:
    id: int
    tenant_id: int
    evidence_type: str
    source: Optional[str] = None
    description: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None


@dataclass
class _RequestLog:
    id: int
    tenant_id: int
    input_text: str
    input_hash: str
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    request_id: Optional[str] = None
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class _DecisionLog:
    id: int
    tenant_id: int
    request_log_id: int
    allowed: bool
    reasons: List[str] = field(default_factory=list)
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    risk_score: Optional[int] = None

    # Relationship-like backref to request (filled by repo when fetched)
    request_log: Optional[_RequestLog] = None


@dataclass
class _RiskScore:
    id: int
    tenant_id: int
    request_log_id: int
    score: int
    reasons: List[str] = field(default_factory=list)
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    evidence_present: bool = False


# ----------------------------------------
# Fake Policy Repo
# ----------------------------------------

class FakePolicyRepo:
    """
    In-memory PolicyRepo.

    - Supports creating policies, adding/listing versions, activating a version.
    - Provides get_active_policy_doc helper used by services.
    """

    def __init__(self) -> None:
        self._policy_id_seq = 1
        self._policy_version_id_seq = 1
        self._policies: Dict[int, _Policy] = {}
        self._policies_by_tenant_slug: Dict[tuple[int, str], int] = {}
        self._versions_by_policy: Dict[int, List[_PolicyVersion]] = {}

    # Policy operations

    def create_policy(
        self,
        tenant_id: int,
        name: str,
        slug: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> _Policy:
        pid = self._policy_id_seq
        self._policy_id_seq += 1
        p = _Policy(
            id=pid,
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
        )
        self._policies[pid] = p
        self._policies_by_tenant_slug[(tenant_id, slug)] = pid
        self._versions_by_policy.setdefault(pid, [])
        return p

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[_Policy]:
        items = [p for p in self._policies.values() if p.tenant_id == tenant_id]
        items.sort(key=lambda x: x.id, reverse=True)
        start = max(0, int(offset))
        end = start + max(1, int(limit))
        return items[start:end]

    def get_policy_by_id(self, policy_id: int) -> Optional[_Policy]:
        return self._policies.get(policy_id)

    def get_policy_by_slug(self, tenant_id: int, slug: str) -> Optional[_Policy]:
        pid = self._policies_by_tenant_slug.get((tenant_id, slug))
        return self._policies.get(pid) if pid is not None else None

    def update_policy(self, policy: _Policy, **fields: Any) -> _Policy:
        for k, v in fields.items():
            if hasattr(policy, k):
                setattr(policy, k, v)
        return policy

    def delete_policy(self, policy: _Policy) -> None:
        self._policies.pop(policy.id, None)
        self._policies_by_tenant_slug.pop((policy.tenant_id, policy.slug), None)
        self._versions_by_policy.pop(policy.id, None)

    # Version operations

    def _next_version_number(self, policy_id: int) -> int:
        versions = self._versions_by_policy.get(policy_id, [])
        if not versions:
            return 1
        return max(v.version for v in versions) + 1

    def add_version(self, policy_id: int, document: dict, is_active: bool = True) -> _PolicyVersion:
        if policy_id not in self._policies:
            raise ValueError(f"Policy id={policy_id} not found")
        vid = self._policy_version_id_seq
        self._policy_version_id_seq += 1

        version_number = self._next_version_number(policy_id)

        if is_active:
            # Deactivate other versions
            for v in self._versions_by_policy.get(policy_id, []):
                v.is_active = False

        pv = _PolicyVersion(
            id=vid,
            policy_id=policy_id,
            version=version_number,
            document=dict(document),
            is_active=is_active,
        )
        self._versions_by_policy.setdefault(policy_id, []).append(pv)
        return pv

    def set_active_version(self, policy_id: int, version: int) -> _PolicyVersion:
        versions = self._versions_by_policy.get(policy_id, [])
        target = None
        for v in versions:
            if v.version == version:
                target = v
            else:
                v.is_active = False
        if target is None:
            raise ValueError(f"Version {version} for policy {policy_id} not found")
        target.is_active = True
        return target

    # Helpers often used by services/tests

    def get_active_version(self, policy_id: int) -> Optional[_PolicyVersion]:
        versions = self._versions_by_policy.get(policy_id, [])
        for v in versions:
            if v.is_active:
                return v
        return None

    def get_version(self, policy_id: int, version: int) -> Optional[_PolicyVersion]:
        versions = self._versions_by_policy.get(policy_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def list_versions(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence[_PolicyVersion]:
        versions = list(self._versions_by_policy.get(policy_id, []))
        versions.sort(key=lambda x: x.version, reverse=True)
        start = max(0, int(offset))
        end = start + max(1, int(limit))
        return versions[start:end]

    # Convenience helper (not required by Protocol)
    def get_active_policy_doc(self, tenant_id: int, policy_slug: str) -> Optional[dict]:
        pol = self.get_policy_by_slug(tenant_id, policy_slug)
        if not pol:
            return None
        pv = self.get_active_version(pol.id)
        return dict(pv.document) if pv else None


# ----------------------------------------
# Fake Evidence Repo
# ----------------------------------------

class FakeEvidenceRepo:
    """
    In-memory EvidenceRepo.
    """

    def __init__(self) -> None:
        self._id_seq = 1
        self._items: Dict[int, _EvidenceItem] = {}
        self._by_tenant_hash: Dict[tuple[int, str], int] = {}

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
    ) -> _EvidenceItem:
        # Compute hash if missing with a simple prioritization
        if not content_hash:
            if source:
                content_hash = sha256_text(source)
            elif description:
                content_hash = sha256_text(description)

        if content_hash:
            key = (tenant_id, content_hash)
            existing_id = self._by_tenant_hash.get(key)
            if existing_id:
                return self._items[existing_id]

        eid = self._id_seq
        self._id_seq += 1
        item = _EvidenceItem(
            id=eid,
            tenant_id=tenant_id,
            evidence_type=evidence_type,
            source=source,
            description=description,
            content_hash=content_hash,
            metadata=metadata,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
        )
        self._items[eid] = item
        if content_hash:
            self._by_tenant_hash[(tenant_id, content_hash)] = eid
        return item

    def get_by_id(self, evidence_id: int) -> Optional[_EvidenceItem]:
        return self._items.get(evidence_id)

    def get_by_hash(self, tenant_id: int, content_hash: str) -> Optional[_EvidenceItem]:
        eid = self._by_tenant_hash.get((tenant_id, content_hash))
        return self._items.get(eid) if eid else None

    def list_for_policy(self, policy_id: int, offset: int = 0, limit: int = 50) -> Sequence[_EvidenceItem]:
        results = [e for e in self._items.values() if e.policy_id == policy_id]
        results.sort(key=lambda x: x.id, reverse=True)
        start = max(0, int(offset))
        end = start + max(1, int(limit))
        return results[start:end]

    def delete(self, evidence: _EvidenceItem) -> None:
        self._items.pop(evidence.id, None)
        if evidence.content_hash:
            self._by_tenant_hash.pop((evidence.tenant_id, evidence.content_hash), None)


# ----------------------------------------
# Fake Audit Repo
# ----------------------------------------

class FakeAuditRepo:
    """
    In-memory AuditRepo for requests, decisions, and risk scores.
    """

    def __init__(self) -> None:
        self._req_id_seq = 1
        self._dec_id_seq = 1
        self._risk_id_seq = 1

        self._requests: Dict[int, _RequestLog] = {}
        self._decisions: Dict[int, _DecisionLog] = {}
        self._decision_by_request: Dict[int, int] = {}
        self._risks: Dict[int, _RiskScore] = {}
        self._risk_by_request: Dict[int, int] = {}

    # Request logs

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
    ) -> _RequestLog:
        rid = self._req_id_seq
        self._req_id_seq += 1
        ihash = input_hash or sha256_text(input_text)
        req = _RequestLog(
            id=rid,
            tenant_id=tenant_id,
            input_text=input_text,
            input_hash=ihash,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            request_id=request_id,
            user_agent=user_agent,
            client_ip=client_ip,
            metadata=metadata,
        )
        self._requests[rid] = req
        return req

    def list_requests(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[_RequestLog]:
        items = [r for r in self._requests.values() if r.tenant_id == tenant_id]
        items.sort(key=lambda x: x.id, reverse=True)
        start = max(0, int(offset))
        end = start + max(1, int(limit))
        return items[start:end]

    def get_request(self, request_log_id: int) -> Optional[_RequestLog]:
        return self._requests.get(request_log_id)

    # Decision logs

    def log_decision(
        self,
        *,
        tenant_id: int,
        request_log_id: int,
        allowed: bool,
        reasons: Optional[List[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        risk_score: Optional[int] = None,
    ) -> _DecisionLog:
        did = self._dec_id_seq
        self._dec_id_seq += 1
        dec = _DecisionLog(
            id=did,
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            allowed=bool(allowed),
            reasons=list(reasons or []),
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            risk_score=risk_score,
        )
        # Attach relationship-like backref for convenience
        dec.request_log = self._requests.get(request_log_id)
        self._decisions[did] = dec
        self._decision_by_request[request_log_id] = did
        return dec

    def get_decision_for_request(self, request_log_id: int) -> Optional[_DecisionLog]:
        did = self._decision_by_request.get(request_log_id)
        dec = self._decisions.get(did) if did else None
        if dec:
            dec.request_log = self._requests.get(request_log_id)
        return dec

    # Risk scores

    def log_risk_score(
        self,
        tenant_id: int,
        request_log_id: int,
        score: int,
        reasons: Optional[List[str]] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        evidence_present: bool = False,
    ) -> _RiskScore:
        rid = self._risk_id_seq
        self._risk_id_seq += 1
        rs = _RiskScore(
            id=rid,
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            score=int(score),
            reasons=list(reasons or []),
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            evidence_present=bool(evidence_present),
        )
        self._risks[rid] = rs
        self._risk_by_request[request_log_id] = rid
        return rs

    def get_risk_for_request(self, request_log_id: int) -> Optional[_RiskScore]:
        rid = self._risk_by_request.get(request_log_id)
        return self._risks.get(rid) if rid else None
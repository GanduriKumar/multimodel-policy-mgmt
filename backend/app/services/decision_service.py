"""
Decision service orchestrating request logging, policy evaluation, and risk scoring.

Depends only on:
- Protocol interfaces: PolicyRepo, EvidenceRepo, AuditRepo
- Engines: policy_engine.evaluate_policy, risk_engine.compute_risk
- Schema: PolicyDoc

Primary entrypoint:
    protect(...)

Behavior:
1) Logs the incoming request (AuditRepo.log_request).
2) Loads the active policy document for the tenant+slug via PolicyRepo.
3) Evaluates policy (policy_engine.evaluate_policy).
4) Computes risk (risk_engine.compute_risk) using evidence presence.
5) Determines final allow/deny (policy result AND risk below threshold).
6) Logs the decision (AuditRepo.log_decision). Best-effort logs risk score via AuditRepo.log_risk_score if available.
7) Returns a result dict with allow, reasons, risk_score, and log IDs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, TypedDict

from app.core.contracts import PolicyRepo, EvidenceRepo, AuditRepo
from app.schemas.policy_format import PolicyDoc
from app.services.policy_engine import evaluate_policy
from app.services.risk_engine import compute_risk


class ProtectResult(TypedDict):
    allowed: bool
    reasons: list[str]
    risk_score: int
    request_log_id: Optional[int]
    decision_log_id: Optional[int]


def _load_active_policy_doc(
    policy_repo: PolicyRepo,
    tenant_id: int,
    policy_slug: str,
) -> tuple[Optional[dict], Optional[int], Optional[int]]:
    """
    Try to obtain the active policy document (dict) for a tenant's policy slug.

    Returns:
        (document_dict or None, policy_id or None, policy_version_id or None)
    """
    # Path 1: Some implementations expose a direct helper
    try:
        if hasattr(policy_repo, "get_active_policy_doc"):
            # Not part of the strict Protocol, but used if available.
            doc = getattr(policy_repo, "get_active_policy_doc")(tenant_id, policy_slug)  # type: ignore[attr-defined]
            if isinstance(doc, dict):
                # Attempt to also extract ids if the repo exposes lookups
                pol = None
                if hasattr(policy_repo, "get_policy_by_slug"):
                    pol = policy_repo.get_policy_by_slug(tenant_id, policy_slug)  # type: ignore[call-arg]
                pv_id = None
                if pol is not None and hasattr(policy_repo, "get_active_version"):
                    pv = policy_repo.get_active_version(pol.id)  # type: ignore[attr-defined]
                    pv_id = getattr(pv, "id", None) if pv is not None else None
                return doc, (getattr(pol, "id", None) if pol is not None else None), pv_id
    except Exception:
        # Fall back to Protocol-only path
        pass

    # Path 2: Strict Protocol sequence
    pol = None
    if hasattr(policy_repo, "get_policy_by_slug"):
        pol = policy_repo.get_policy_by_slug(tenant_id, policy_slug)  # type: ignore[call-arg]
    if pol is None:
        return None, None, None

    pv = None
    if hasattr(policy_repo, "get_active_version"):
        pv = policy_repo.get_active_version(pol.id)  # type: ignore[attr-defined]
    if pv is None:
        return None, getattr(pol, "id", None), None

    doc = getattr(pv, "document", None)
    return (doc if isinstance(doc, dict) else None), getattr(pol, "id", None), getattr(pv, "id", None)


def protect(
    *,
    tenant_id: int,
    input_text: str,
    policy_slug: str,
    evidence_types: Optional[Set[str]],
    policy_repo: PolicyRepo,
    evidence_repo: EvidenceRepo,  # kept for future use; Protocol-only dependency
    audit_repo: AuditRepo,
    request_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    client_ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ProtectResult:
    """
    Orchestrate protection workflow: log request, evaluate policy, compute risk, log decision.

    Args:
        tenant_id: Tenant identifier.
        input_text: The content to analyze.
        policy_slug: Policy slug within the tenant.
        evidence_types: Set of provided evidence type strings (e.g., {"url", "document"}).
        policy_repo: Policy repository (Protocol).
        evidence_repo: Evidence repository (Protocol) - not used directly in MVP.
        audit_repo: Audit repository (Protocol).
        request_id: Optional client-provided request correlation ID.
        user_agent: Optional user agent string.
        client_ip: Optional client IP string.
        metadata: Optional metadata for request log.

    Returns:
        ProtectResult dict with allow/deny, reasons, risk_score, and log IDs.
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a str")
    if not isinstance(policy_slug, str) or not policy_slug.strip():
        raise ValueError("policy_slug must be a non-empty string")

    ev_types: Set[str] = set(evidence_types or set())

    # 1) Log the incoming request
    request_log = audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=input_text,
        policy_id=None,
        policy_version_id=None,
        input_hash=None,
        request_id=request_id,
        user_agent=user_agent,
        client_ip=client_ip,
        metadata=metadata,
    )

    # 2) Load active policy document
    policy_doc_dict, policy_id, policy_version_id = _load_active_policy_doc(
        policy_repo=policy_repo, tenant_id=tenant_id, policy_slug=policy_slug
    )

    # Default policy if none exists: permissive with high threshold
    if not isinstance(policy_doc_dict, dict):
        policy_doc = PolicyDoc(
            blocked_terms=[],
            allowed_sources=[],
            required_evidence_types=[],
            pii_rules={},
            risk_threshold=100,
        )
    else:
        policy_doc = PolicyDoc(**policy_doc_dict)

    # 3) Evaluate policy rules
    policy_allowed, policy_reasons = evaluate_policy(policy_doc, input_text, ev_types)

    # 4) Compute risk score (evidence presence is a simple boolean)
    evidence_present = bool(ev_types)
    risk_score, risk_reasons = compute_risk(input_text, evidence_present=evidence_present)

    # 5) Final decision: must satisfy policy and be below threshold
    reasons: list[str] = []
    allowed = policy_allowed
    reasons.extend(policy_reasons)
    reasons.extend(risk_reasons)

    if risk_score >= int(policy_doc.risk_threshold):
        allowed = False
        reasons.append(f"risk_above_threshold:{risk_score}>={policy_doc.risk_threshold}")

    # 6) Update request log with resolved policy ids (re-log not ideal; just include in decision)
    decision = audit_repo.log_decision(
        tenant_id=tenant_id,
        request_log_id= getattr(request_log, "id", None),
        allowed=allowed,
        reasons=reasons,
        policy_id=policy_id,
        policy_version_id=policy_version_id,
        risk_score=risk_score,
    )

    # Best-effort: log risk score entry if repository supports it (Protocol optional)
    try:
        if hasattr(audit_repo, "log_risk_score"):
            getattr(audit_repo, "log_risk_score")(  # type: ignore[attr-defined]
                tenant_id=tenant_id,
                request_log_id=getattr(request_log, "id", None),
                score=risk_score,
                reasons=risk_reasons,
                policy_id=policy_id,
                policy_version_id=policy_version_id,
                evidence_present=evidence_present,
            )
    except Exception:
        # Do not fail the main flow if auxiliary logging fails
        pass

    return ProtectResult(
        allowed=allowed,
        reasons=sorted(set(reasons)),
        risk_score=risk_score,
        request_log_id=getattr(request_log, "id", None),
        decision_log_id=getattr(decision, "id", None),
    )
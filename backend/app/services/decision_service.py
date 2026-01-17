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
from app.core.patterns import detect_pii_like


class ProtectResult(TypedDict):
    allowed: bool
    reasons: list[str]
    risk_score: int
    request_log_id: Optional[int]
    decision_log_id: Optional[int]


def _load_active_policy_doc(
    policy_repo: PolicyRepo,
    tenant_id: int,
    *,
    policy_id: Optional[int] = None,
    policy_slug: Optional[str] = None,
) -> tuple[Optional[dict], Optional[int], Optional[int]]:
    """
    Try to obtain the active policy document (dict) for a tenant's policy slug.

    Returns:
        (document_dict or None, policy_id or None, policy_version_id or None)
    """
    # Path 1: Some implementations expose a direct helper
    try:
        if hasattr(policy_repo, "get_active_policy_doc") and policy_slug:
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
    if policy_id is not None and hasattr(policy_repo, "get_policy_by_id"):
        pol = policy_repo.get_policy_by_id(int(policy_id))  # type: ignore[attr-defined]
    elif policy_slug and hasattr(policy_repo, "get_policy_by_slug"):
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
    policy_id: Optional[int] = None,
    policy_slug: Optional[str] = None,
    evidence_types: Optional[Set[str]],
    policy_repo: PolicyRepo,
    evidence_repo: EvidenceRepo,  # kept for future use; Protocol-only dependency
    audit_repo: AuditRepo,
    request_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    client_ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    stage: Optional[str] = None,
) -> ProtectResult:
    """
    Orchestrate protection workflow: log request, evaluate policy, compute risk, log decision.

    Args:
        tenant_id: Tenant identifier.
        input_text: The content to analyze.
        policy_id: Policy ID within the tenant (required if policy_slug not provided).
        policy_slug: Policy slug within the tenant (alternative to policy_id).
        evidence_types: Set of provided evidence type strings (e.g., {"url", "document"}).
        policy_repo: Policy repository (Protocol).
        evidence_repo: Evidence repository (Protocol) - not used directly in MVP.
        audit_repo: Audit repository (Protocol).
        request_id: Optional client-provided request correlation ID.
        user_agent: Optional user agent string.
        client_ip: Optional client IP string.
        metadata: Optional metadata for request log.
        stage: Optional stage identifier ("pre" or "post"). Evidence checks only run on "post".

    Returns:
        ProtectResult dict with allow/deny, reasons, risk_score, and log IDs.
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a str")
    
    # Resolve policy by slug or ID
    if policy_slug:
        if policy_id:
            raise ValueError("Provide either policy_id or policy_slug, not both")
        # We need to look up the policy by slug to get its ID
        # For now, we'll use the policy_repo to get the active policy by slug
        pol = policy_repo.get_policy_by_slug(tenant_id, policy_slug)
        if not pol:
            raise ValueError(f"Policy not found with slug: {policy_slug}")
        actual_policy_id = pol.id
    elif policy_id:
        actual_policy_id = policy_id
    else:
        raise ValueError("Either policy_id or policy_slug must be provided")
    
    if not isinstance(actual_policy_id, int) or actual_policy_id < 1:
        raise ValueError("policy_id must be a positive integer")

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
    policy_doc_dict, resolved_policy_id, policy_version_id = _load_active_policy_doc(
        policy_repo=policy_repo, tenant_id=tenant_id, policy_id=actual_policy_id
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
    
    # 3b) Enforce PII rules if configured
    pii_blocked = False
    pii_reasons = []
    if policy_doc.pii_rules:
        pii_markers = detect_pii_like(input_text)
        if pii_markers:
            # Check each PII marker against pii_rules configuration
            for marker in pii_markers:
                # Extract PII type from marker (e.g., "email_like" -> "email")
                pii_type = marker.replace("_like", "").replace("_", "")
                
                # Check if this PII type has a rule configured
                for rule_key, rule_config in policy_doc.pii_rules.items():
                    if rule_key.lower() in pii_type.lower() or pii_type.lower() in rule_key.lower():
                        if isinstance(rule_config, dict):
                            action = rule_config.get('action', 'detect')
                            enabled = rule_config.get('enabled', True)
                        else:
                            action = 'detect'
                            enabled = True
                        
                        if enabled:
                            if action == 'block':
                                pii_blocked = True
                                pii_reasons.append(f"pii_blocked:{pii_type}")
                            elif action in ['mask', 'redact']:
                                pii_reasons.append(f"pii_{action}:{pii_type}")
                            else:
                                pii_reasons.append(f"pii_detected:{pii_type}")
    
    # If PII is blocked, override policy decision
    if pii_blocked:
        policy_allowed = False
        policy_reasons.extend(pii_reasons)

    # 4) Compute risk score (evidence presence is a simple boolean)
    # Only check evidence during post-check stage (after content generation)
    evidence_present = bool(ev_types)
    check_evidence = (stage == "post")  # Only enforce evidence in post-check
    risk_score, risk_reasons = compute_risk(
        input_text, 
        evidence_present=evidence_present,
        check_evidence=check_evidence
    )
    # 4b) Conservative risk floor: elevate score up to threshold only for substantive indicators
    # Do NOT treat mere "evidence_missing" as a risk that triggers flooring.
    try:
        if getattr(policy_doc, "conservative_mode", False) and risk_reasons:
            substantive_indicator = any(
                r.startswith(("prompt_injection:", "pii_like:", "secret_like:")) for r in risk_reasons
            )
            if substantive_indicator and risk_score < int(policy_doc.risk_threshold):
                risk_score = int(policy_doc.risk_threshold)
                if "conservative_risk_floor" not in risk_reasons:
                    risk_reasons.append("conservative_risk_floor")
    except Exception:
        pass

    # 5) Final decision: must satisfy policy and be below threshold
    reasons: list[str] = []
    allowed = policy_allowed
    reasons.extend(policy_reasons)
    reasons.extend(risk_reasons)

    if risk_score >= int(policy_doc.risk_threshold):
        allowed = False
        reasons.append(f"risk_above_threshold:{risk_score}>={policy_doc.risk_threshold}")

    # Optional conservative mode: only substantive indicators trigger denial
    try:
        if getattr(policy_doc, "conservative_mode", False):
            if any(r.startswith(("prompt_injection:", "pii_like:", "secret_like:")) for r in risk_reasons):
                allowed = False
                reasons.append("conservative_denial:any_risk_indicator")
    except Exception:
        pass

    # 6) Update request log with resolved policy ids (re-log not ideal; just include in decision)
    decision = audit_repo.log_decision(
        tenant_id=tenant_id,
        request_log_id= getattr(request_log, "id", None),
        allowed=allowed,
        reasons=reasons,
        policy_id=resolved_policy_id,
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
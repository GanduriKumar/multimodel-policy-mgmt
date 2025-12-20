"""
Policy evaluation engine.

evaluate_policy(policy: PolicyDoc, input_text: str, evidence_types: set[str]) -> tuple[bool, list[str]]

Decision rules:
- Blocked terms: If any blocked term appears in the text (case-insensitive substring), deny.
- Required evidence: If any required evidence type is missing from provided evidence_types, deny.
- PII rules: Based on policy.pii_rules, detected PII in text may cause denial.
  Supported pii_rules keys (booleans):
    - deny_when_any_pii
    - deny_on_email
    - deny_on_phone
    - deny_on_ssn
    - deny_on_ipv4
    - deny_on_credit_card

Returns:
- allowed: bool (True if allowed, False if denied)
- reasons: list[str] explaining each reason that caused denial (empty if allowed)
"""

from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from app.schemas.policy_format import PolicyDoc
from app.core.patterns import detect_pii_like


def _find_blocked_terms(text: str, blocked_terms: Iterable[str]) -> list[str]:
    """
    Find blocked terms present in text (case-insensitive substring search).
    Returns list of reason strings.
    """
    reasons: list[str] = []
    t = text.lower()
    for term in blocked_terms:
        term_norm = (term or "").strip()
        if not term_norm:
            continue
        if term_norm.lower() in t:
            reasons.append(f"blocked_term:{term_norm}")
    return reasons


def _find_missing_evidence(
    provided: Set[str], required: Iterable[str]
) -> list[str]:
    """
    Compare provided vs required evidence types.
    Returns list of reason strings for any missing types.
    """
    reasons: list[str] = []
    prov_norm = {e.strip().lower() for e in provided if isinstance(e, str)}
    for req in required:
        req_norm = (req or "").strip().lower()
        if not req_norm:
            continue
        if req_norm not in prov_norm:
            reasons.append(f"missing_evidence:{req_norm}")
    return reasons


def _apply_pii_rules(text: str, pii_rules: dict) -> list[str]:
    """
    Apply PII rules to input text using detect_pii_like markers.
    Returns list of reason strings when a rule triggers denial.
    """
    if not isinstance(pii_rules, dict):
        return []

    markers = set(detect_pii_like(text))
    if not markers:
        return []

    # If any PII should cause denial
    reasons: list[str] = []
    if pii_rules.get("deny_when_any_pii", False):
        reasons.append("pii_denied:any")
        # No need to check individual types when blanket denial is set
        return reasons

    # Map policy flags to marker(s)
    flag_to_markers: list[tuple[str, Set[str]]] = [
        ("deny_on_email", {"email_address"}),
        ("deny_on_phone", {"us_phone_number", "intl_phone_number"}),
        ("deny_on_ssn", {"us_ssn"}),
        ("deny_on_ipv4", {"ipv4_address"}),
        ("deny_on_credit_card", {"credit_card_number"}),
    ]

    for flag, needed in flag_to_markers:
        if pii_rules.get(flag, False) and markers.intersection(needed):
            # Choose a stable reason name from the set (sorted for determinism)
            matched = sorted(markers.intersection(needed))[0]
            reasons.append(f"pii_denied:{matched}")

    return reasons


def evaluate_policy(
    policy: PolicyDoc, input_text: str, evidence_types: Set[str]
) -> tuple[bool, list[str]]:
    """
    Evaluate input against a policy.

    Args:
        policy: The PolicyDoc configuration.
        input_text: The content to evaluate.
        evidence_types: Set of evidence types provided for this content.

    Returns:
        (allowed, reasons)
        - allowed is True when no denial conditions are met.
        - reasons lists all denial explanations (empty if allowed).
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a str")
    if not isinstance(evidence_types, set):
        # Gracefully accept other iterables by converting to set
        try:
            evidence_types = set(evidence_types)  # type: ignore[arg-type]
        except Exception as exc:
            raise TypeError("evidence_types must be a set[str] or iterable of str") from exc

    denial_reasons: list[str] = []

    # 1) Blocked terms
    denial_reasons.extend(_find_blocked_terms(input_text, policy.blocked_terms))

    # 2) Required evidence
    denial_reasons.extend(_find_missing_evidence(evidence_types, policy.required_evidence_types))

    # 3) PII rules
    denial_reasons.extend(_apply_pii_rules(input_text, policy.pii_rules))

    allowed = len(denial_reasons) == 0
    return allowed, sorted(denial_reasons)
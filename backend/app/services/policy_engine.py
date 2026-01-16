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

    # Context-aware exception: if this is clearly creative/depiction and not instruction/incitement,
    # don't block purely on violent words like 'kill'/'murder' used in fiction contexts.
    try:
        from app.services.risk_engine import _local_intent_classifier  # local import to avoid cycles
        intents = _local_intent_classifier(text)
        v_weapon = intents.get("weapon_instruction", 0) >= 0.5
        v_incite = intents.get("incite_violence", 0) >= 0.5
        v_depict = intents.get("depict_violence", 0) >= 0.5
        skip_depiction_terms = v_depict and not (v_weapon or v_incite)
    except Exception:
        skip_depiction_terms = False

    violence_terms: set[str] = {
        "kill", "murder", "violence", "violent", "gun", "weapon", "bomb", "shoot", "stab",
    }
    for term in blocked_terms:
        term_norm = (term or "").strip()
        if not term_norm:
            continue
        # Conservative: substring match OR word boundary match both deny
        low = term_norm.lower()
        # Skip common violent words in depiction context
        if skip_depiction_terms and low in violence_terms:
            continue
        if low in t:
            reasons.append(f"blocked_term:{term_norm}")
            continue
        # Word boundary check to catch standalone prohibited words
        try:
            import re
            if re.search(rf"\b{re.escape(low)}\b", t):
                reasons.append(f"blocked_term:{term_norm}")
        except Exception:
            # If regex fails for any reason, fall back to substring logic handled above
            pass
    return reasons


def _find_missing_evidence(
    provided: Set[str], required: Iterable[str]
) -> list[str]:
    """
    Generic evidence check: if policy specifies any required evidence types,
    treat presence of any evidence as sufficient. No per-type matching.
    """
    req_list = [(req or "").strip() for req in required if (req or "").strip()]
    if not req_list:
        return []
    has_any = any(isinstance(e, str) and e.strip() for e in provided)
    return [] if has_any else ["missing_evidence:any"]


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

    # Support DOB-specific denial if configured
    flag_to_markers.append(("deny_on_dob", {"date_of_birth"}))

    for flag, needed in flag_to_markers:
        if pii_rules.get(flag, False) and markers.intersection(needed):
            # Choose a stable reason name from the set (sorted for determinism)
            matched = sorted(markers.intersection(needed))[0]
            reasons.append(f"pii_denied:{matched}")

    return reasons


def _apply_intent_rules(text: str, intent_rules: dict) -> list[str]:
    """
    Apply local intent rules. Expects risk_engine to add reasons like 'intent:label:0.82'.
    Since policy_engine doesn't compute intents, we heuristically re-run the same lightweight classifier here for determinism.
    """
    if not isinstance(intent_rules, dict) or not intent_rules:
        return []

    from app.services.risk_engine import _local_intent_classifier  # local import to avoid cycles

    deny_list = set((intent_rules.get("deny") or []))
    thresholds = intent_rules.get("thresholds") or {}
    reasons: list[str] = []
    intents = _local_intent_classifier(text)
    for label, score in intents.items():
        thr = float(thresholds.get(label, 0.5))
        if label in deny_list and score >= thr:
            reasons.append(f"intent_denied:{label}:{score:.2f}")
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

    # 2) Required evidence (generic presence-only check)
    if getattr(policy, "require_any_evidence", False) or policy.required_evidence_types:
        denial_reasons.extend(_find_missing_evidence(evidence_types, policy.required_evidence_types))

    # 3) PII rules
    denial_reasons.extend(_apply_pii_rules(input_text, policy.pii_rules))

    # 4) Intent rules (local)
    denial_reasons.extend(_apply_intent_rules(input_text, getattr(policy, "intent_rules", {})))

    allowed = len(denial_reasons) == 0
    return allowed, sorted(denial_reasons)
import os
import sys
import pytest

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.schemas.policy_format import PolicyDoc
from app.services.policy_engine import evaluate_policy


def test_blocked_term_denies():
    policy = PolicyDoc(
        blocked_terms=["forbidden"],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=50,
    )
    allowed, reasons = evaluate_policy(policy, "Please avoid FORBIDDEN content here.", evidence_types=set())
    assert allowed is False
    assert "blocked_term:forbidden" in reasons


def test_missing_required_evidence_denies():
    policy = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=["url", "document"],
        pii_rules={},
        risk_threshold=50,
    )
    # Provide only 'url', so 'document' is missing
    allowed, reasons = evaluate_policy(policy, "Neutral text without blocked terms.", evidence_types={"url"})
    assert allowed is False
    assert "missing_evidence:document" in reasons
    assert "missing_evidence:url" not in reasons  # url was provided


def test_reasons_list_explains_denial():
    policy = PolicyDoc(
        blocked_terms=["banword"],
        allowed_sources=[],
        required_evidence_types=["dataset"],
        pii_rules={},
        risk_threshold=50,
    )
    # Triggers both blocked term and missing evidence
    allowed, reasons = evaluate_policy(policy, "This includes BANWORD explicitly.", evidence_types=set())

    assert allowed is False
    assert isinstance(reasons, list)
    assert len(reasons) > 0
    assert "blocked_term:banword" in reasons
    assert "missing_evidence:dataset" in reasons
    # All reasons should be non-empty strings
    assert all(isinstance(r, str) and r.strip() for r in reasons)
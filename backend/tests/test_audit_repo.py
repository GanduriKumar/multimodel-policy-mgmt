import os
import sys

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.hashing import sha256_text
from app.models.tenant import Tenant
from app.repos.audit_repo import SqlAlchemyAuditRepo


def test_request_decision_linkage_integrity(db_session):
    # Create a tenant
    tenant = Tenant(name="Audit Tenant", slug="audit-tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Initialize repository
    repo = SqlAlchemyAuditRepo(db_session)

    # Log a request (input_hash should be computed automatically)
    input_text = "Evaluate this harmless statement."
    req = repo.log_request(
        tenant_id=tenant.id,
        input_text=input_text,
        request_id="req-123",
        user_agent="pytest-agent",
        client_ip="127.0.0.1",
        metadata={"env": "test"},
    )

    assert req.id is not None
    assert req.tenant_id == tenant.id
    assert req.input_hash == sha256_text(input_text)

    # Ensure the request appears in listing
    requests = repo.list_requests(tenant_id=tenant.id, limit=10)
    assert any(r.id == req.id for r in requests)

    # Log a decision linked to the request
    reasons = ["blocked_term:forbidden", "missing_evidence:url"]
    decision = repo.log_decision(
        tenant_id=tenant.id,
        request_log_id=req.id,
        allowed=False,
        reasons=reasons,
        risk_score=72,
    )

    assert decision.id is not None
    assert decision.request_log_id == req.id
    assert decision.allowed is False
    assert decision.risk_score == 72
    assert decision.reasons == reasons

    # Fetch decision detail and verify linkage integrity
    fetched = repo.get_decision_detail(request_log_id=req.id)
    assert fetched is not None
    assert fetched.id == decision.id
    assert fetched.request_log_id == req.id
    assert fetched.allowed is False
    assert fetched.reasons == reasons
    assert fetched.risk_score == 72

    # Relationship backref integrity: decision -> request
    # Accessing relationship should resolve to the same request id
    assert fetched.request_log is not None
    assert fetched.request_log.id == req.id
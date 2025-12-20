import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.api.routes.protect import router as protect_router  # noqa: E402
from app.core.deps import get_decision_service  # noqa: E402


class _FakeDecisionService:
    def protect(
        self,
        *,
        tenant_id: int,
        input_text: str,
        policy_slug: str,
        evidence_types=None,
        request_id=None,
        user_agent=None,
        client_ip=None,
        metadata=None,
    ):
        # Deterministic fake result
        return {
            "allowed": True,
            "reasons": ["test-double"],
            "risk_score": 7,
            "request_log_id": 123,
            "decision_log_id": 456,
        }


def test_api_protect_with_dependency_override():
    # Build a minimal app and include the protect router under /api
    app = FastAPI()
    app.include_router(protect_router, prefix="/api")

    # Override the dependency used by the route to inject our fake service
    app.dependency_overrides[get_decision_service] = lambda: _FakeDecisionService()

    client = TestClient(app)

    payload = {
        "tenant_id": 1,
        "policy_slug": "content-policy",
        "input_text": "Hello world",
        "evidence_types": ["url"],
        "request_id": "req-1",
        "user_agent": "pytest-agent",
        "client_ip": "127.0.0.1",
        "metadata": {"k": "v"},
    }

    resp = client.post("/api/protect", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # Validate response shape
    assert isinstance(data, dict)
    assert set(["allowed", "reasons", "risk_score", "request_log_id", "decision_log_id"]).issubset(data.keys())
    assert data["allowed"] is True
    assert isinstance(data["reasons"], list) and data["reasons"]
    assert isinstance(data["risk_score"], int)
    assert data["request_log_id"] == 123
    assert data["decision_log_id"] == 456
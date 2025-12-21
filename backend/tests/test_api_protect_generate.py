from __future__ import annotations

from typing import Any, Dict, List

from fastapi.testclient import TestClient

from app.main import get_application  # FastAPI app factory
from app.schemas.generation import ProtectGenerateRequest, ProtectGenerateResponse, GroundedClaim
from app.services.governed_generation_service import GovernedGenerationService


class FakeGovernedGenerationService(GovernedGenerationService):
    """A fake service that records calls and returns deterministic responses."""

    def __init__(self) -> None:
        # Do not call super(); we don't need real dependencies in this fake
        self.calls: List[Dict[str, Any]] = []
        self.raise_error: bool = False

    def protect_and_generate(self, request: ProtectGenerateRequest) -> ProtectGenerateResponse:
        if self.raise_error:
            raise RuntimeError("simulated failure")
        # Record the call for assertions
        self.calls.append({
            "input_text": request.input_text,
            "retrieval_query": request.retrieval_query,
            "tenant_id": request.tenant_id,
            "policy_slug": request.policy_slug,
        })
        # Return a deterministic response
        return ProtectGenerateResponse(
            allowed=True,
            risk_score=5,
            policy_reasons=["ok"],
            risk_reasons=[],
            grounded_claims=[GroundedClaim(text="claim", score=1.0, supported=True, matched_evidence_ids=[])],
            raw_model_output="hello",
            trace_id="trace-123",
        )


def _override_service(app):
    # Override the dependency function used by the route, which comes from core.deps
    from app.core.deps import get_governed_generation_service

    fake = FakeGovernedGenerationService()

    # Use FastAPI dependency override system
    app.dependency_overrides[get_governed_generation_service] = lambda: fake
    return fake


def test_protect_generate_success_pass_through_and_response_fields():
    app = get_application()
    fake = _override_service(app)
    client = TestClient(app)

    payload = {
        "tenant_id": 1,
        "policy_slug": "default",
        "input_text": "hello world",
        "evidence_types": [],
        "retrieval_query": "q1",
    }

    resp = client.post("/api/protect-generate", json=payload)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # Ensure fake recorded the call and payload passed through
    assert fake.calls and fake.calls[-1]["input_text"] == payload["input_text"]
    assert fake.calls[-1]["retrieval_query"] == payload["retrieval_query"]

    # Validate expected fields
    assert body["allowed"] is True
    assert body["risk_score"] == 5
    assert isinstance(body.get("grounded_claims"), list)
    assert body.get("raw_model_output") == "hello"
    assert body.get("trace_id") == "trace-123"


def test_protect_generate_error_handling_returns_500():
    app = get_application()
    fake = _override_service(app)
    fake.raise_error = True
    client = TestClient(app)

    payload = {
        "tenant_id": 1,
        "policy_slug": "default",
        "input_text": "boom",
        "evidence_types": [],
    }

    resp = client.post("/api/protect-generate", json=payload)
    assert resp.status_code == 500
    body = resp.json()
    assert body.get("detail") == "Internal error"

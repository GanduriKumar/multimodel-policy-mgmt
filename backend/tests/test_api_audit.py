import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.api.routes.audit import router as audit_router  # noqa: E402
from app.core.deps import get_audit_repo  # noqa: E402


@dataclass
class _RequestLogObj:
    id: int
    tenant_id: int
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class _DecisionLogObj:
    id: int
    tenant_id: int
    request_log_id: int
    allowed: bool
    reasons: List[str] = field(default_factory=list)
    risk_score: Optional[int] = None
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


class _FakeAuditRepo:
    def __init__(self) -> None:
        self._req_id = 1
        self._dec_id = 1
        self._requests: Dict[int, _RequestLogObj] = {}
        self._decisions: Dict[int, _DecisionLogObj] = {}
        self._decision_by_request: Dict[int, int] = {}

    # Helpers for seeding
    def seed_request(self, tenant_id: int) -> _RequestLogObj:
        r = _RequestLogObj(id=self._req_id, tenant_id=tenant_id)
        self._requests[self._req_id] = r
        self._req_id += 1
        return r

    def seed_decision(
        self,
        *,
        tenant_id: int,
        request_log_id: int,
        allowed: bool,
        reasons: Optional[List[str]] = None,
        risk_score: Optional[int] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> _DecisionLogObj:
        d = _DecisionLogObj(
            id=self._dec_id,
            tenant_id=tenant_id,
            request_log_id=request_log_id,
            allowed=allowed,
            reasons=list(reasons or []),
            risk_score=risk_score,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
        )
        self._decisions[self._dec_id] = d
        self._decision_by_request[request_log_id] = d.id
        self._dec_id += 1
        return d

    # Methods used by routes
    def list_requests(self, tenant_id: int, offset: int = 0, limit: int = 50):
        items = [r for r in self._requests.values() if r.tenant_id == tenant_id]
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items[offset : offset + limit]

    def get_decision_detail(self, request_log_id: int):
        # Route may call this with a request id; return decision for that request
        did = self._decision_by_request.get(int(request_log_id))
        return self._decisions.get(did) if did else None

    def get_decision_by_id(self, decision_id: int):
        # Route tries this first for /decisions/{id}
        return self._decisions.get(int(decision_id))

    def get_decision_for_request(self, request_log_id: int):
        # Alternative fallback name
        return self.get_decision_detail(request_log_id)


def _make_app(fake_repo: _FakeAuditRepo) -> TestClient:
    app = FastAPI()
    app.include_router(audit_router)

    # Override dependency to inject our in-test fake
    app.dependency_overrides[get_audit_repo] = lambda: fake_repo
    return TestClient(app)


def test_list_requests_returns_rows_and_snapshots():
    repo = _FakeAuditRepo()
    client = _make_app(repo)

    # Seed tenant 1 with two requests; one has a decision
    r1 = repo.seed_request(tenant_id=1)
    r2 = repo.seed_request(tenant_id=1)
    repo.seed_decision(
        tenant_id=1,
        request_log_id=r1.id,
        allowed=False,
        reasons=["blocked_term:ban", "prompt_injection:ignore_previous_instructions"],
        risk_score=70,
    )

    # Seed another tenant to ensure filtering works
    repo.seed_request(tenant_id=2)

    resp = client.get("/api/audit/requests", params={"tenant_id": 1, "offset": 0, "limit": 10})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "items" in data and isinstance(data["items"], list)
    assert "total" in data and isinstance(data["total"], int)
    assert data["total"] == len(data["items"]) == 2

    # Validate row fields
    for row in data["items"]:
        assert {"request_log_id", "tenant_id", "decision_id", "decision", "risk_score", "created_at"} <= set(row.keys())
        assert row["tenant_id"] == 1

    # Find the row with a decision snapshot
    with_dec = next((x for x in data["items"] if x["request_log_id"] == r1.id), None)
    assert with_dec is not None
    assert with_dec["decision_id"] is not None
    assert isinstance(with_dec["decision"], bool)
    assert isinstance(with_dec["risk_score"], int)

    # The other row should have no decision yet
    without_dec = next((x for x in data["items"] if x["request_log_id"] == r2.id), None)
    assert without_dec is not None
    assert without_dec["decision_id"] is None
    assert without_dec["decision"] is None
    assert without_dec["risk_score"] is None


def test_get_decision_detail_schema_and_reason_split():
    repo = _FakeAuditRepo()
    client = _make_app(repo)

    r = repo.seed_request(tenant_id=5)
    d = repo.seed_decision(
        tenant_id=5,
        request_log_id=r.id,
        allowed=False,
        reasons=["blocked_term:ban", "risk_above_threshold:70>=50", "prompt_injection:ignore_previous_instructions"],
        risk_score=70,
        policy_id=10,
        policy_version_id=3,
    )

    resp = client.get(f"/api/audit/decisions/{d.id}")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    # Validate shape
    expected_keys = {
        "decision_id",
        "request_log_id",
        "tenant_id",
        "allowed",
        "risk_score",
        "policy_id",
        "policy_version_id",
        "policy_reasons",
        "risk_reasons",
        "evidence_ids",
        "created_at",
    }
    assert expected_keys <= set(data.keys())

    # Values
    assert data["decision_id"] == d.id
    assert data["request_log_id"] == r.id
    assert data["tenant_id"] == 5
    assert data["allowed"] is False
    assert data["risk_score"] == 70
    assert data["policy_id"] == 10
    assert data["policy_version_id"] == 3
    assert isinstance(data["policy_reasons"], list)
    assert isinstance(data["risk_reasons"], list)
    assert isinstance(data["evidence_ids"], list)

    # Reason split heuristic: blocked_term -> policy, prompt_injection and risk_above_threshold -> risk
    assert any(r.startswith("blocked_term:") for r in data["policy_reasons"])
    assert any(r.startswith("prompt_injection:") for r in data["risk_reasons"])
    assert any(r.startswith("risk_above_threshold") for r in data["risk_reasons"])
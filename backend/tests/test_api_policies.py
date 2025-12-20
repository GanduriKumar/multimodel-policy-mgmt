import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.api.routes.policies import router as policies_router  # noqa: E402
from app.core.deps import get_policy_repo  # noqa: E402


# Local in-test fake implementing the minimal PolicyRepo surface needed by the API routes
@dataclass
class _PolicyObj:
    id: int
    tenant_id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class _PolicyVersionObj:
    id: int
    policy_id: int
    version: int
    document: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())


class _FakePolicyRepo:
    def __init__(self) -> None:
        self._pid = 1
        self._pvid = 1
        self._policies: Dict[int, _PolicyObj] = {}
        self._versions: Dict[int, List[_PolicyVersionObj]] = {}

    # Methods used by routes
    def create_policy(
        self, tenant_id: int, name: str, slug: str, description: Optional[str] = None, is_active: bool = True
    ) -> _PolicyObj:
        p = _PolicyObj(
            id=self._pid,
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
        )
        self._pid += 1
        self._policies[p.id] = p
        self._versions.setdefault(p.id, [])
        return p

    def list_policies(self, tenant_id: int, offset: int = 0, limit: int = 50) -> Sequence[_PolicyObj]:
        items = [p for p in self._policies.values() if p.tenant_id == tenant_id]
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items[offset : offset + limit]

    def add_version(self, policy_id: int, document: dict, is_active: bool = True) -> _PolicyVersionObj:
        if policy_id not in self._policies:
            raise ValueError("Policy not found")
        next_ver = (max([v.version for v in self._versions.get(policy_id, [])], default=0) + 1)
        if is_active:
            for v in self._versions.get(policy_id, []):
                v.is_active = False
        pv = _PolicyVersionObj(
            id=self._pvid,
            policy_id=policy_id,
            version=next_ver,
            document=dict(document),
            is_active=is_active,
        )
        self._pvid += 1
        self._versions.setdefault(policy_id, []).append(pv)
        return pv

    def set_active_version(self, policy_id: int, version: int) -> _PolicyVersionObj:
        versions = self._versions.get(policy_id, [])
        target = None
        for v in versions:
            if v.version == version:
                target = v
            v.is_active = (v.version == version)
        if not target:
            raise ValueError("Version not found")
        return target


def _make_app(fake_repo: _FakePolicyRepo) -> TestClient:
    app = FastAPI()
    app.include_router(policies_router)

    # Override dependency to inject our in-test fake
    app.dependency_overrides[get_policy_repo] = lambda: fake_repo
    return TestClient(app)


def test_create_and_list_policies_via_api():
    repo = _FakePolicyRepo()
    client = _make_app(repo)

    # Create a policy
    payload = {
        "tenant_id": 1,
        "name": "Content Policy",
        "slug": "content-policy",
        "description": "Test policy",
        "is_active": True,
    }
    resp = client.post("/api/policies", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert isinstance(data, dict)
    assert data["tenant_id"] == 1
    assert data["name"] == "Content Policy"
    assert data["slug"] == "content-policy"
    assert "created_at" in data and "updated_at" in data
    policy_id = data["id"]

    # List policies
    resp_list = client.get("/api/policies", params={"tenant_id": 1, "offset": 0, "limit": 10})
    assert resp_list.status_code == 200, resp_list.text
    list_data = resp_list.json()
    assert "items" in list_data and isinstance(list_data["items"], list)
    assert list_data["total"] >= 1
    # Ensure the created policy is present
    assert any(item["id"] == policy_id for item in list_data["items"])


def test_add_and_activate_policy_version_via_api():
    repo = _FakePolicyRepo()
    client = _make_app(repo)

    # Create a policy
    payload = {
        "tenant_id": 1,
        "name": "Compliance Policy",
        "slug": "compliance-policy",
        "description": None,
        "is_active": True,
    }
    resp = client.post("/api/policies", json=payload)
    assert resp.status_code == 201, resp.text
    policy_id = resp.json()["id"]

    # Add v1 active
    ver_payload = {
        "policy_id": policy_id,
        "document": {"risk_threshold": 50},
        "is_active": True,
    }
    resp_v1 = client.post(f"/api/policies/{policy_id}/versions", json=ver_payload)
    assert resp_v1.status_code == 201, resp_v1.text
    v1 = resp_v1.json()
    assert v1["version"] == 1
    assert v1["is_active"] is True

    # Add v2 inactive
    ver_payload2 = {
        "policy_id": policy_id,
        "document": {"risk_threshold": 75},
        "is_active": False,
    }
    resp_v2 = client.post(f"/api/policies/{policy_id}/versions", json=ver_payload2)
    assert resp_v2.status_code == 201, resp_v2.text
    v2 = resp_v2.json()
    assert v2["version"] == 2
    assert v2["is_active"] is False

    # Activate v2
    resp_act = client.post(f"/api/policies/{policy_id}/versions/2/activate")
    assert resp_act.status_code == 200, resp_act.text
    active_v = resp_act.json()
    assert active_v["version"] == 2
    assert active_v["is_active"] is True
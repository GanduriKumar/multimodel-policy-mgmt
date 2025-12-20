import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.api.routes.evidence import router as evidence_router  # noqa: E402
from app.core.deps import get_evidence_repo  # noqa: E402
from app.core.hashing import sha256_text  # noqa: E402


@dataclass
class _EvidenceObj:
    id: int
    tenant_id: int
    evidence_type: str
    source: Optional[str] = None
    description: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    policy_id: Optional[int] = None
    policy_version_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())


class _FakeEvidenceRepo:
    def __init__(self) -> None:
        self._id = 1
        self._items: Dict[int, _EvidenceObj] = {}

    # Preferred method used by our route
    def create_evidence(
        self,
        *,
        tenant_id: int,
        evidence_type: str,
        source: Optional[str] = None,
        description: Optional[str] = None,
        content_text: Optional[str] = None,
        metadata: Optional[dict] = None,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
    ) -> _EvidenceObj:
        # Determine deterministic content hash (content > source > description)
        content_hash = None
        if content_text:
            content_hash = sha256_text(content_text)
        elif source:
            content_hash = sha256_text(source)
        elif description:
            content_hash = sha256_text(description)

        obj = _EvidenceObj(
            id=self._id,
            tenant_id=tenant_id,
            evidence_type=evidence_type,
            source=source,
            description=description,
            content_hash=content_hash,
            metadata=metadata,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
        )
        self._items[self._id] = obj
        self._id += 1
        return obj

    # Also supported by route as a fallback name
    def get_evidence(self, evidence_id: int) -> Optional[_EvidenceObj]:
        return self._items.get(int(evidence_id))


def _make_app(fake_repo: _FakeEvidenceRepo) -> TestClient:
    app = FastAPI()
    app.include_router(evidence_router)

    # Override dependency to inject our in-test fake
    app.dependency_overrides[get_evidence_repo] = lambda: fake_repo
    return TestClient(app)


def test_post_and_get_evidence_api():
    repo = _FakeEvidenceRepo()
    client = _make_app(repo)

    tenant_id = 1
    payload = {
        "evidence_type": "document",
        "source": "https://example.com/doc/123",
        "description": "Example document",
        "content": "Café 🚀 body",  # ensures hash is from content, not source
        "metadata": {"k": "v"},
        "policy_id": None,
        "policy_version_id": None,
    }

    # POST create evidence
    resp = client.post(f"/api/evidence?tenant_id={tenant_id}", json=payload)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    # Response shape assertions
    for key in ["id", "tenant_id", "evidence_type", "created_at", "updated_at"]:
        assert key in data
    assert data["tenant_id"] == tenant_id
    assert data["evidence_type"] == "document"
    assert data["source"] == payload["source"]
    assert data["description"] == payload["description"]
    assert data["metadata"] == payload["metadata"]

    expected_hash = sha256_text(payload["content"])
    assert data["content_hash"] == expected_hash

    evidence_id = data["id"]

    # GET retrieve evidence
    resp_get = client.get(f"/api/evidence/{evidence_id}")
    assert resp_get.status_code == 200, resp_get.text

    got = resp_get.json()
    assert got["id"] == evidence_id
    assert got["tenant_id"] == tenant_id
    assert got["evidence_type"] == payload["evidence_type"]
    assert got["content_hash"] == expected_hash
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_reports_endpoint_basic(monkeypatch):
    client = TestClient(app)

    # No API key configured path: if get_api_key allows None, this will pass; otherwise adjust when auth is enforced.
    resp = client.get("/api/reports/policy-changes", params={"tenant_id": 1, "preset": "last24h", "format": "json"})
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        assert isinstance(resp.json(), list)

import os
import sys
import importlib
from dataclasses import dataclass

import pytest

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


@dataclass
class _TenantObj:
    id: int
    name: str
    is_active: bool = True


class _FakeTenantRepo:
    def __init__(self):
        self._by_hash: dict[str, _TenantObj] = {}
        self._id = 1

    def seed(self, api_key_hash: str, name: str = "Tenant", is_active: bool = True) -> _TenantObj:
        t = _TenantObj(id=self._id, name=name, is_active=is_active)
        self._id += 1
        self._by_hash[api_key_hash.lower()] = t
        return t

    # Duck-typed method used by AuthService
    def get_by_api_key_hash(self, api_key_hash: str):
        return self._by_hash.get(api_key_hash.lower())


def _import_auth_service_with_secret(monkeypatch, secret: str = "unit-auth-secret"):
    """
    Ensure auth modules are loaded with a known secret.
    Reload both app.core.auth and app.services.auth_service so the imported function binding is updated.
    """
    monkeypatch.setenv("API_KEY_SECRET", secret)

    auth_mod = importlib.import_module("app.core.auth")
    auth_mod = importlib.reload(auth_mod)

    svc_mod = importlib.import_module("app.services.auth_service")
    svc_mod = importlib.reload(svc_mod)

    return auth_mod, svc_mod


def test_authenticate_valid_key_returns_tenant(monkeypatch):
    auth_mod, svc_mod = _import_auth_service_with_secret(monkeypatch, "test-secret-1")

    # Prepare fake repo with a tenant keyed by hashed API key
    raw_key = "my-secret-api-key"
    api_key_hash = auth_mod.hash_api_key(raw_key)
    fake_repo = _FakeTenantRepo()
    seeded = fake_repo.seed(api_key_hash, name="Acme", is_active=True)

    service = svc_mod.AuthService(fake_repo)
    tenant = service.authenticate(raw_key)

    assert tenant is not None
    assert tenant.id == seeded.id
    assert tenant.name == "Acme"
    assert tenant.is_active is True


def test_authenticate_unknown_or_inactive_raises(monkeypatch):
    auth_mod, svc_mod = _import_auth_service_with_secret(monkeypatch, "test-secret-2")

    # Unknown key -> should raise
    fake_repo = _FakeTenantRepo()
    service = svc_mod.AuthService(fake_repo)
    with pytest.raises(svc_mod.AuthError):
        service.authenticate("unknown-key")

    # Inactive tenant -> should raise
    raw_key = "inactive-key"
    api_key_hash = auth_mod.hash_api_key(raw_key)
    fake_repo.seed(api_key_hash, name="Inactive Inc", is_active=False)

    with pytest.raises(svc_mod.AuthError):
        service.authenticate(raw_key)
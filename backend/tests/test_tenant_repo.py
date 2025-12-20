import os
import sys

# Ensure the 'backend' directory is on sys.path so imports work from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.repos.tenant_repo import SqlAlchemyTenantRepo
from app.models.tenant import Tenant


def test_create_and_get_by_api_key_hash(db_session):
    repo = SqlAlchemyTenantRepo(db_session)

    name = "Acme Inc"
    api_key_hash = "deadbeef" * 8  # 64 hex chars

    tenant = repo.create_tenant(name=name, api_key_hash=api_key_hash, is_active=True)

    # Persisted with ID and normalized fields
    assert isinstance(tenant.id, int)
    assert tenant.name == name
    assert tenant.slug == "acme-inc"
    assert tenant.api_key_hash == api_key_hash.lower()
    assert tenant.is_active is True

    # Retrieve by api_key_hash (case-insensitive input)
    fetched = repo.get_by_api_key_hash(api_key_hash.upper())
    assert fetched is not None
    assert fetched.id == tenant.id
    assert fetched.slug == tenant.slug
    assert fetched.api_key_hash == tenant.api_key_hash


def test_slug_uniqueness_increment(db_session):
    repo = SqlAlchemyTenantRepo(db_session)

    # Same name, different API key hashes -> slugs should be unique and incremented
    t1 = repo.create_tenant(name="Acme Inc", api_key_hash="a" * 64)
    t2 = repo.create_tenant(name="Acme Inc", api_key_hash="b" * 64)

    assert t1.slug == "acme-inc"
    assert t2.slug == "acme-inc-2"

    # Ensure both are retrievable via their hashes
    f1 = repo.get_by_api_key_hash("a" * 64)
    f2 = repo.get_by_api_key_hash("b" * 64)
    assert f1 is not None and f1.id == t1.id
    assert f2 is not None and f2.id == t2.id
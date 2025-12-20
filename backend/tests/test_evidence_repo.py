import os
import sys

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.hashing import sha256_text
from app.models.tenant import Tenant
from app.models.evidence_item import EvidenceItem
from app.repos.evidence_repo import SqlAlchemyEvidenceRepo


def test_create_evidence_stores_content_hash(db_session):
    # Create a tenant
    tenant = Tenant(name="Hash Test Tenant", slug="hash-tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Create repo and add evidence with content text (preferred for hashing)
    repo = SqlAlchemyEvidenceRepo(db_session)
    content = "Café 🚀 content body"
    item = repo.create_evidence(
        tenant_id=tenant.id,
        evidence_type="document",
        content_text=content,
        description="Sample doc",
    )

    # Hash should be stored and match the expected sha256 of the content
    expected_hash = sha256_text(content)
    assert item.content_hash == expected_hash

    # Verify persisted value directly from DB
    persisted = db_session.get(EvidenceItem, item.id)
    assert persisted is not None
    assert persisted.content_hash == expected_hash


def test_get_evidence_returns_same(db_session):
    # Create a tenant
    tenant = Tenant(name="Lookup Tenant", slug="lookup-tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Insert evidence (using source for hashing here)
    repo = SqlAlchemyEvidenceRepo(db_session)
    source_url = "https://example.com/resource?id=123"
    item = repo.create_evidence(
        tenant_id=tenant.id,
        evidence_type="url",
        source=source_url,
        description="Example URL",
    )

    # Retrieve via repository
    fetched = repo.get_evidence(item.id)
    assert fetched is not None
    assert fetched.id == item.id
    assert fetched.content_hash == sha256_text(source_url)
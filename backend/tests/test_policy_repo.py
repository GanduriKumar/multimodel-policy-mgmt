import os
import sys

import pytest
from sqlalchemy import select

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.models.tenant import Tenant
from app.models.policy_version import PolicyVersion
from app.repos.policy_repo import SqlAlchemyPolicyRepo


def test_activate_version_deactivates_previous(db_session):
    # Create a tenant
    tenant = Tenant(name="Acme Corp", slug="acme")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Create a policy for this tenant
    repo = SqlAlchemyPolicyRepo(db_session)
    policy = repo.create_policy(
        tenant_id=tenant.id,
        name="Content Policy",
        slug="content-policy",
        description="Test policy",
        is_active=True,
    )

    # Add v1 as active
    doc_v1 = {"risk_threshold": 50}
    pv1 = repo.add_version(policy_id=policy.id, document=doc_v1, is_active=True)
    assert pv1.version == 1
    # Only v1 should be active
    active_versions = db_session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id, PolicyVersion.is_active.is_(True)
        )
    ).scalars().all()
    assert len(active_versions) == 1
    assert active_versions[0].version == 1

    # Add v2 as inactive initially
    doc_v2 = {"risk_threshold": 75}
    pv2 = repo.add_version(policy_id=policy.id, document=doc_v2, is_active=False)
    assert pv2.version == 2

    # Still only v1 should be active
    active_versions = db_session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id, PolicyVersion.is_active.is_(True)
        )
    ).scalars().all()
    assert len(active_versions) == 1
    assert active_versions[0].version == 1

    # Activate v2; this should deactivate v1
    repo.activate_version(policy_id=policy.id, version=2)

    # Now only v2 should be active
    active_versions = db_session.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id, PolicyVersion.is_active.is_(True)
        )
    ).scalars().all()
    assert len(active_versions) == 1
    assert active_versions[0].version == 2

    # Ensure the repository returns the active document for the policy slug
    active_doc = repo.get_active_policy_doc(tenant_id=tenant.id, policy_slug=policy.slug)
    assert active_doc == doc_v2
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion
from app.services.reports.policy_changes import list_policy_change_events


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def test_empty_range_returns_no_events(db_session: Session):
    start = _utc_now() - timedelta(days=1)
    end = _utc_now()
    events = list_policy_change_events(db_session, tenant_id=1, from_utc=start, to_utc=end)
    assert events == []


def test_policy_created_event(db_session: Session):
    now = _utc_now()
    p = Policy(tenant_id=1, name="P1", slug="p1")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    # created_at is set by DB default; ensure updated_at too
    events = list_policy_change_events(db_session, tenant_id=1, from_utc=now - timedelta(days=1), to_utc=now + timedelta(days=1))
    # Expect at least policy_created
    kinds = [e.change_type for e in events]
    assert "policy_created" in kinds
    # Validate core fields
    evt = next(e for e in events if e.change_type == "policy_created")
    assert evt.policy_id == p.id and evt.policy_name == p.name and evt.tenant_id == 1
    assert evt.changed_at_utc.endswith("Z")
    assert evt.local_timezone == "Asia/Kolkata"


def test_version_created_and_activation_inference(db_session: Session):
    now = _utc_now()
    # Create policy
    p = Policy(tenant_id=1, name="P2", slug="p2")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    # Create two versions; mark v1 active first, then v2 active later
    v1 = PolicyVersion(policy_id=p.id, version=1, document={"risk_threshold": 50}, is_active=True)
    db_session.add(v1)
    db_session.commit()
    db_session.refresh(v1)

    # Activate v2 later
    v2 = PolicyVersion(policy_id=p.id, version=2, document={"risk_threshold": 60}, is_active=True)
    db_session.add(v2)
    db_session.commit()
    db_session.refresh(v2)

    # Simulate activation timestamp by bumping updated_at on v2
    # (SQLite server_default sets on insert; updated_at set on update by ORM)
    v2.is_active = True
    db_session.flush(); db_session.commit(); db_session.refresh(v2)

    events = list_policy_change_events(db_session, tenant_id=1, from_utc=now - timedelta(days=1), to_utc=now + timedelta(days=1))
    kinds = [e.change_type for e in events]
    # Version created should be present for v1 and v2
    assert kinds.count("version_created") >= 2
    # Activation should be present for v2, and deactivation inferred for v1
    assert "version_activated" in kinds
    assert "version_deactivated" in kinds

from __future__ import annotations

from app.services.reports.html_renderer import render_policy_changes_html
from app.services.reports.policy_changes import PolicyChangeEvent


def test_basic_html_structure():
    html = render_policy_changes_html(
        tenant_id=1,
        tz="Asia/Kolkata",
        range_meta={"preset": "last24h", "from_utc": "2026-01-15T12:00:00Z", "to_utc": "2026-01-16T12:00:00Z"},
        events=[
            PolicyChangeEvent(
                tenant_id=1,
                policy_id=10,
                policy_name="P",
                version_id=1,
                version=1,
                is_active=True,
                change_type="version_created",
                changed_by="Unknown",
                changed_at_utc="2026-01-16T12:00:00Z",
                changed_at_local="2026-01-16T17:30:00+05:30",
                local_timezone="Asia/Kolkata",
                event_id="evt-1",
                document_sha256="abc",
                diff_summary="risk_threshold: 50→60",
            )
        ],
        no_change_policies_recent=[{"policy_id": 11, "policy_name": "Q"}],
        older_no_change_count=2,
    )
    assert "<!doctype html>" in html.lower()
    assert "chartChanges" in html
    assert "chartPolicies" in html
    assert "Events" in html
    assert "Policies with no change" in html

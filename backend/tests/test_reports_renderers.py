from __future__ import annotations

from app.services.reports.policy_changes import PolicyChangeEvent
from app.services.reports.renderers import to_csv, to_ndjson, to_json_array


def _evt(idx: int) -> PolicyChangeEvent:
    return PolicyChangeEvent(
        tenant_id=1,
        policy_id=10,
        policy_name="P",
        version_id=None,
        version=None,
        is_active=None,
        change_type="policy_updated",
        changed_by="Unknown",
        changed_at_utc=f"2026-01-16T12:00:0{idx}Z",
        changed_at_local=f"2026-01-16T17:30:0{idx}+05:30",
        local_timezone="Asia/Kolkata",
        event_id=f"evt-{idx}",
        document_sha256="",
        diff_summary="",
    )


def test_csv_and_bom():
    data = to_csv([_evt(1), _evt(2)])
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("tenant_id,policy_id,policy_name")
    # Newest first by changed_at_utc
    assert "12:00:02Z" in text.splitlines()[1]


def test_ndjson_and_json_array():
    nd = to_ndjson([_evt(1), _evt(2)])
    lines = nd.decode("utf-8").strip().splitlines()
    assert len(lines) == 2
    arr = to_json_array([_evt(1)])
    assert arr.decode("utf-8").startswith("[")

from __future__ import annotations

from datetime import datetime, timezone

from app.services.reports.timeutils import compute_range, fmt_rfc3339_utc, fmt_rfc3339_local


def test_last24h_range():
    now = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    f, t = compute_range("last24h", now_utc=now)
    assert (t - f).total_seconds() == 24 * 3600


def test_this_month_and_last_month_boundaries():
    now = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    f1, t1 = compute_range("this_month", now_utc=now, tz="Asia/Kolkata")
    assert f1.tzinfo is not None and t1.tzinfo is not None
    f2, t2 = compute_range("last_month", now_utc=now, tz="Asia/Kolkata")
    assert f2 <= t2


def test_custom_and_formatters():
    f, t = compute_range(
        "custom",
        from_iso="2026-01-16T00:00:00Z",
        to_iso="2026-01-16T23:59:59Z",
    )
    assert fmt_rfc3339_utc(f).endswith("Z")
    s = fmt_rfc3339_local(f, tz="Asia/Kolkata")
    assert "+05:30" in s

# Prompt 4: Time Presets and Timezone Helpers

- What it implements: Utilities to compute inclusive [from,to] UTC ranges for presets and to format timestamps in RFC3339 for UTC and Asia/Kolkata.
- Dependency: Prompts 1–3 (used by event query and renderers).

## Prompt
```
Write complete and executable code providing time utilities:

Functions:
- compute_range(preset: str, now_utc: datetime | None = None, *, from_iso: str | None = None, to_iso: str | None = None, tz: str = "Asia/Kolkata") -> tuple[datetime, datetime]
  - Supported presets: last24h (default), last7d, last30d, this_month, last_month, custom
  - Inclusive time window [from,to]
  - For custom, parse from_iso/to_iso as RFC3339 strings; validate from <= to
  - Return timezone-aware UTC datetimes
- fmt_rfc3339_utc(dt: datetime) -> str (e.g., 2026-01-16T10:15:30.123456Z)
- fmt_rfc3339_local(dt: datetime, tz: str = "Asia/Kolkata") -> str (e.g., 2026-01-16T15:45:30.123456+05:30)

Implementation details:
- Use zoneinfo for timezone handling (standard library)
- Ensure deterministic formatting with microseconds when present
- Strict parsing for custom ISO inputs; raise ValueError on invalid inputs
- Treat inclusive endpoints: events with timestamp == from or == to are included

Files:
- Module: backend/app/services/reports/timeutils.py
- Tests: backend/tests/test_reports_timeutils.py

Tests (pytest):
- Each preset returns correct boundaries relative to now()
- Month boundary cases (this_month/last_month)
- Custom range parsing (valid/invalid) and inclusivity
- RFC3339 formatting correctness (UTC Z suffix; local offset +05:30)
```

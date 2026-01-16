# Prompt 6: HTML Report Renderer (Responsive + Charts)

- What it implements: Server-side HTML renderer for Policy Changes report using Bootstrap 5 and Chart.js. Includes responsive layout, charts, tables, and collapsible snapshots, with special handling for "No change" policies.
- Dependency: Prompts 1–5.

## Prompt
```
Write complete and executable code to render a self-contained HTML document as a string given:
- tenant_id: int
- tz: str (Asia/Kolkata)
- range_meta: { preset: str, from_utc: str, to_utc: str }
- events: list[PolicyChangeEvent]
- no_change_policies: list[{ policy_id: int, policy_name: str }]
- cap_no_change_html_to_last_days: int = 7 (policies with no change older than this are summarized as a single line)

HTML requirements:
- Use Bootstrap 5 (CDN) and Chart.js (CDN)
- Header: title, tenant_id, range (local + UTC), timezone
- Charts:
  - Changes per day by change_type (stacked bar)
  - Changes by policy (top N bar)
  - Distribution of risk_threshold across versions (histogram or bar)
- Table of events with columns: policy_id, policy_name, version_id, version, is_active, change_type, changed_at_local, changed_by, diff_summary
- Collapsible sections per event: full JSON snapshot (pretty-printed) and metadata (event_id, document_sha256)
- "No change" section:
  - Show rows for policies with no change within last cap_no_change_html_to_last_days days
  - Summarize additional policies as: "N policies had no changes earlier than X days"
- Responsive design: cards/rows collapse neatly on mobile

Files:
- Module: backend/app/services/reports/html_renderer.py
- Tests: backend/tests/test_reports_html_renderer.py

Tests (pytest):
- Render with sample data and assert presence of key sections/IDs
- Charts containers present with expected dataset labels
- Table contains expected columns and sample rows
- No-change handling with cap
- HTML validity basics (doctype, head, body)
```

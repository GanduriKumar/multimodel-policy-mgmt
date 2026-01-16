# Prompt 7: FastAPI Endpoint /api/reports/policy-changes

- What it implements: Admin-only server endpoint to generate Policy Changes reports in HTML, CSV, NDJSON, or JSON, with time presets/custom and Asia/Kolkata timezone handling.
- Dependency: Prompts 1–6.

## Prompt
```
Write complete and executable FastAPI code that adds a router under /api/reports with endpoint:
GET /api/reports/policy-changes

Query params:
- tenant_id: int (required)
- preset: str (last24h default | last7d | last30d | this_month | last_month | custom)
- from: str (RFC3339, required when preset=custom)
- to: str (RFC3339, required when preset=custom)
- tz: str (default Asia/Kolkata)
- format: str (html default | csv | ndjson | json)

Behavior:
- Require same API key auth as other admin endpoints
- Compute [from_utc,to_utc] via timeutils
- Build events via policy_changes service; compute diffs and hashes as needed
- Derive no_change_policies for HTML (and only HTML)
- Render via chosen renderer
- Set Content-Type accordingly and Content-Disposition: attachment; filename=policy-changes_t{tenant}_from{from}_to{to}_{format}.{ext}
- Empty results: return valid empty representation; HTML must still include headers and a "No changes in range" message

Files:
- Router: backend/app/api/routes/reports.py
- Wire router in backend/app/api/router.py
- Tests: backend/tests/test_api_reports_policy_changes.py

Tests (pytest):
- Each format returns 200 with expected headers and body shape
- Presets and custom ranges
- Auth required
- No events -> empty outputs with proper structure
```

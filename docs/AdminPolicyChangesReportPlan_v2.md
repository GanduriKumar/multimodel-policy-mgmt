# Admin Policy Changes Report – Implementation Plan (HTML + CSV + NDJSON + JSON)

Audience: Admin. Server-side report generation with download. Time-range selection supports presets (default Last 24h) and Custom. Tenant-local timezone Asia/Kolkata. Scope: all policies (policy_id only). If no changes in range, render "No changes". Changed-by is "Unknown". Deleted events not reconstructed.

Event taxonomy and heuristics
- policy_created: Policy.created_at in range
- policy_updated: any Policy.updated_at in range (heuristic)
- policy_activated / policy_deactivated: Policy.updated_at in range when is_active toggled
- version_created: PolicyVersion.created_at in range
- version_activated / version_deactivated: PolicyVersion.updated_at in range when is_active toggled (approximate timestamps acceptable)

Event schema (CSV/NDJSON/JSON)
- tenant_id, policy_id, policy_name, version_id (nullable), version (nullable), is_active (nullable), change_type, changed_by ("Unknown"), changed_at_utc (RFC3339), changed_at_local (RFC3339), local_timezone (Asia/Kolkata), event_id (UUIDv7), document_sha256 (SHA-256 of canonical JSON), diff_summary
- CSV: UTF-8 with BOM, comma-separated, LF newlines
- NDJSON: one event per line (minified JSON objects)
- JSON: array of events

---

## Prompt 1: Event Query by Time Range (policy_id only)
- What it implements: Service/repo function to enumerate Policy + PolicyVersion change events for tenant_id in [from,to] UTC, returning core fields to build the schema.
- Dependency: None.
- Prompt:
```
Write complete and executable code to list policy change events for a tenant_id over [from_utc, to_utc]. Use SQLAlchemy models Policy and PolicyVersion. Detect changes per taxonomy:
- policy_created from Policy.created_at
- policy_updated from Policy.updated_at (heuristic)
- policy_activated/deactivated from Policy.updated_at when is_active toggled
- version_created from PolicyVersion.created_at
- version_activated/deactivated from PolicyVersion.updated_at when is_active toggled
Return a list of objects containing: tenant_id, policy_id, policy_name, version_id, version, is_active, change_type, changed_at (UTC naive dt or aware), and the raw document for versions. Include unit tests covering empty ranges, boundaries, and toggles. Execute tests and show results.
```

## Prompt 2: Canonical JSON + SHA-256
- What it implements: Canonicalize a policy document (sorted keys, UTF-8, no extra whitespace) and compute SHA-256 hex digest.
- Dependency: Prompt 1.
- Prompt:
```
Write code that takes a Python dict policy document and returns (canonical_json_str, sha256_hex). Ensure deterministic ordering and stable formatting. Add tests with nested dicts/lists. Execute tests and show results.
```

## Prompt 3: Diff Summaries for Policy Documents
- What it implements: Human-readable and structured diffs across fields: risk_threshold, conservative_mode, blocked_terms, required_evidence_types, pii_rules, intent_rules.
- Dependency: Prompt 1.
- Prompt:
```
Write code to compute a field-level diff between two policy document dicts and return a concise summary string plus a structured diff object. Treat lists as order-insensitive where appropriate. Add tests for add/remove/modify scenarios. Execute tests and show results.
```

## Prompt 4: Time Presets and Timezone Helpers
- What it implements: Utilities to compute [from,to] UTC for presets (last24h default, last7d, last30d, this_month, last_month) and to format UTC -> Asia/Kolkata RFC3339.
- Dependency: None.
- Prompt:
```
Implement helpers to compute time ranges for presets given now() and to format timestamps as RFC3339 strings in UTC and Asia/Kolkata. Add tests for boundaries and formatting. Execute tests and show results.
```

## Prompt 5: Renderers for CSV, NDJSON, JSON
- What it implements: Convert event objects to CSV (UTF-8 BOM), NDJSON (one JSON per line), or a JSON array, applying the final schema (including event_id, changed_by, local timestamps, sha256, diff_summary).
- Dependency: Prompts 1–4.
- Prompt:
```
Write renderers that take the event list and produce bytes/strings for CSV (with BOM), NDJSON, and JSON array. Ensure ordering (newest first), correct RFC3339 formatting, and schema fields. Add tests that validate shape, ordering, and encoding. Execute tests and show results.
```

## Prompt 6: HTML Report Renderer (Responsive + Charts)
- What it implements: Server-side HTML with Bootstrap 5 and Chart.js visualizations: changes over time, changes by policy, distribution of risk_threshold across versions; tables with collapsible full snapshots.
- Dependency: Prompts 1–4 (events + diffs + SHA) and schema.
- Prompt:
```
Write a server-side HTML renderer that produces a self-contained document (CDN assets allowed) with:
- Header showing tenant_id, range (preset/custom), timezone
- Charts: changes per day by change_type; changes by policy; risk_threshold distribution
- Table: policy_id, policy_name, version_id, version, is_active, change_type, changed_at_local, changed_by, diff_summary
- Collapsible sections for full JSON snapshots and metadata (document_sha256, event_id)
Ensure responsive Bootstrap layout. Add tests that assert required sections/IDs are present. Execute tests and show results.
```

## Prompt 7: FastAPI Endpoint /api/reports/policy-changes
- What it implements: GET endpoint generating events and returning in the requested format with Content-Disposition for download.
- Dependency: Prompts 1–6.
- Prompt:
```
Implement GET /api/reports/policy-changes with query params: tenant_id (int, required), preset (last24h default|last7d|last30d|this_month|last_month|custom), from (ISO8601 when custom), to (ISO8601 when custom), tz=Asia/Kolkata default, format=html|csv|ndjson|json (default=html). Build events from the taxonomy, compute diffs and SHA where applicable, and render via the chosen renderer. Set appropriate content-type and Content-Disposition filename including tenant_id and date range. If no events, return an HTML/CSV/NDJSON/JSON stating No changes in range. Add endpoint tests for each format and presets/custom.
```

## Prompt 8: Admin UI – Reports Section (Policy Changes)
- What it implements: Adds a Reports section to the Admin page with time presets, custom From/To, and Generate/Download for Policy Changes.
- Dependency: Prompt 7.
- Prompt:
```
Update the Admin page to include a Reports area with a Policy Changes tab. Controls: preset selector (default Last 24h), optional From/To when Custom, and buttons for Generate (preview optional) and Download (invokes /api/reports/policy-changes with format=html by default, plus options for CSV/NDJSON/JSON). Ensure responsive layout and accessibility. Add component tests for control wiring and successful download trigger.
```

## Prompt 9: Documentation – Reports for Admin & SIEM
- What it implements: Docs for API usage, formats, schema, and UI workflow; compliance notes (timestamps, hashes, provenance).
- Dependency: Prompts 1–8.
- Prompt:
```
Write documentation covering:
- Purpose and audience (Admin)
- Event taxonomy and heuristics
- Endpoint parameters and formats (HTML, CSV, NDJSON, JSON)
- Event schema fields with examples
- Timezone handling (Asia/Kolkata) and RFC3339 formatting
- Admin UI steps to generate/download
- Notes on changed_by=Unknown and lack of delete events
- Extensibility to additional datasets and future IAM/RBAC
Include sample curl commands and screenshots/wireframes.
```

# Decisions Reports — Interview-First Implementation Plan

This plan defines server-side report generation for Decisions, aligned with the already implemented Policy Changes reports. It is interview-first: a set of atomic prompts to implement and test each unit.

---

## Summary of Agreed Requirements

- Purpose: Audit/compliance, event-level records with reasons, evidence links, integrity hashes.
- Time: Same presets (last24h, last7d, last30d, this_month, last_month, custom); default timezone Asia/Kolkata. RFC3339 timestamps (UTC and local).
- Schema fields per Decision event (redacted):
  - ids: tenant_id, policy_id, policy_version_id, request_log_id, decision_log_id, evidence_ids[]
  - decision: allowed (bool), reasons[], risk_score (int), evidence_present (bool)
  - timestamps: decided_at_utc/local, local_timezone
  - integrity: event_id (UUIDv7 if available, else v4), canonical_json_sha256, input_hash (SHA-256), evidence_hashes[]
  - context: request_id, client_ip, user_agent, policy_name (snapshot)
  - redaction: no raw input_text or evidence content; only hashes/types
- Outputs: HTML, CSV, NDJSON, JSON. Stream to client and also save under `<root>/reports` with sanitized filenames. Endpoint: `GET /api/reports/decisions` (same API key auth as policies).
- HTML visuals: keep all — stacked bar (decisions/day by outcome), stacked by policy (top 10), histogram of risk, top reasons bar. Responsive Bootstrap + Chart.js.
- Scope: No filters (all decisions across policies). Include all decision versions (no dedup by request).
- Evidence: Decision links to evidence; include IDs, hashes, types, and sources only.

---

## Implementation Plan (Atomic Prompts)

### Prompt 1: Decision Event Enumeration

- What it implements: Build `DecisionEvent` schema (Pydantic) and `list_decision_events(session, tenant_id, from_utc, to_utc, tz)` that returns fully normalized, redacted decision events within an inclusive UTC window.
- Dependency: Existing SQLAlchemy models (`DecisionLog`, `RequestLog`, `Policy`, `PolicyVersion`, `EvidenceItem`). Reuse timezone helpers.
- Prompt:
```
Write complete and executable code to:
1) Define a Pydantic model DecisionEvent containing: tenant_id, policy_id, policy_version_id, request_log_id, decision_log_id, allowed, reasons[], risk_score, evidence_present, decided_at_utc, decided_at_local, local_timezone, event_id (UUIDv7 or v4 fallback), canonical_json_sha256, input_hash, evidence_ids[], evidence_hashes[], evidence_types[], evidence_sources[], request_id, client_ip, user_agent, policy_name.
2) Implement list_decision_events(session, *, tenant_id:int, from_utc:datetime, to_utc:datetime, tz:str='Asia/Kolkata') that:
   - Queries DecisionLog joined to RequestLog and Policy/PolicyVersion for tenant_id.
   - Selects decisions where DecisionLog.created_at is within [from_utc, to_utc] (handle naive vs aware datetimes by normalizing to UTC-aware).
   - Collects evidence linked to the decision/request (IDs, content hashes, types, sources). Do not include content.
   - Sets decided_at_utc/local using RFC3339, local_timezone.
   - Generates event_id (UUIDv7 if available else UUIDv4).
   - Produces a canonical_json_sha256 for the event payload using a canonical JSON function (sorted keys, strict separators) and SHA-256.
   - Ensures strings, arrays, and numbers adhere to the schema (no nulls for hash strings, use empty string when missing).
   - Returns a list sorted newest-first by decided_at_utc.
3) Add unit tests covering: window filtering, timezone handling without tzdata (fallback for Asia/Kolkata), evidence mapping, hashing integrity, and sorting.
Execute the tests and show results.
```

### Prompt 2: Canonicalization and Hash Utilities (Reuse)

- What it implements: Reuse existing canonicalization helpers to produce canonical JSON and SHA-256 for Decision events.
- Dependency: Builds on existing `app/services/reports/canonicalization.py` or inline utility aliased for decisions.
- Prompt:
```
Refactor or reuse a canonicalize_and_hash utility that:
- Converts a Python dict to canonical JSON (UTF-8, sorted keys, separators=(',', ':'), reject NaN/Inf) and computes SHA-256 hex.
- Expose to Decision report enumeration for canonical_json_sha256.
Add unit tests specific to Decision payloads (including non-ASCII and stable ordering) and run them.
```

### Prompt 3: Renderers (CSV, NDJSON, JSON) for Decisions

- What it implements: Output Decision events as CSV (UTF-8 BOM), NDJSON, JSON array with a fixed SCHEMA_FIELDS order.
- Dependency: Prompt 1 DecisionEvent list and canonicalization.
- Prompt:
```
Implement renderers for Decision events:
- to_csv(events: list[DecisionEvent]) -> bytes (with UTF-8 BOM for Excel)
- to_ndjson(events: list[DecisionEvent]) -> bytes (LF-terminated)
- to_json_array(events: list[DecisionEvent]) -> bytes
Define SCHEMA_FIELDS in the required order and ensure all values are serializable and non-null where strings are expected (hashes as '').
Add renderer unit tests for empty/non-empty cases and schema ordering; run tests.
```

### Prompt 4: HTML Renderer for Decisions (Charts + Table)

- What it implements: Server-side HTML report using Bootstrap 5 and Chart.js with:
  - Stacked bar: decisions per day by outcome (allow/deny).
  - Stacked horizontal bar: decisions by policy (top 10) with outcomes stacked.
  - Histogram: risk score distribution (bucket size 10).
  - Top reasons bar: most frequent reasons (top 10).
  - Events table with all fields (redacted), no raw content.
- Dependency: Prompt 1 outputs; existing HTML patterns from Policy Changes.
- Prompt:
```
Create render_decisions_html(tenant_id, tz, range_meta, events) that produces a complete responsive HTML page:
- Uses Bootstrap 5 and Chart.js (CDN).
- Implements the four charts above (stacked bars, histogram, top reasons), and an events table.
- Handles empty datasets gracefully.
Add focused tests to validate emitted HTML contains expected sections and chart payload structures.
```

### Prompt 5: Time Presets and Timezone (Reuse)

- What it implements: Use existing presets compute_range and RFC3339 formatters; ensure Windows tzdata fallback.
- Dependency: Existing `timeutils` helpers.
- Prompt:
```
Integrate compute_range(preset, from, to, tz='Asia/Kolkata') and RFC3339 helpers for Decisions. Ensure ZoneInfo fallback for Windows (Asia/Kolkata -> UTC+05:30; else UTC). Add tests verifying preset windows and RFC3339 formatting.
```

### Prompt 6: API Endpoint `/api/reports/decisions` with Server-Side Save

- What it implements: FastAPI route similar to Policy Changes, with API key auth and saving files to `<root>/reports`.
- Dependency: Prompts 1, 3, 4, 5; existing auth dependency.
- Prompt:
```
Add GET /api/reports/decisions with query: tenant_id, preset, from, to, tz, format (html|csv|ndjson|json).
- Authenticate via existing API key dependency.
- Compute time window; call list_decision_events; render per requested format.
- Stream response with Content-Disposition and also write the same content to <root>/reports using sanitized filenames (avoid ':' etc.).
Add API tests for all formats (200 OK, file saved) and error cases (bad preset/from>to -> 400); run tests.
```

### Prompt 7: Admin UI — Decisions Report Section

- What it implements: Add a new “Decisions” section under Reports in the Admin page with the same time preset/custom controls and format selector; downloads the file via the new endpoint.
- Dependency: Prompt 6.
- Prompt:
```
Update the frontend Admin page to add a Decisions report section:
- Controls: preset selector, custom from/to (ISO), tz fixed to Asia/Kolkata, format selector (html/csv/ndjson/json), Generate & Download button.
- Build URL to /api/reports/decisions, respecting whether VITE_API_BASE_URL ends with /api to avoid double '/api'.
Add simple UI tests (if present) or manual verification steps.
```

### Prompt 8: Compliance-Oriented Tests and Validation

- What it implements: Cross-cutting tests ensuring redaction, hashes present, timestamps RFC3339, and outcomes.
- Dependency: Prompts 1–7.
- Prompt:
```
Add tests that verify:
- No raw input_text or evidence content appears in any renderer.
- evidence_present matches whether evidence_ids is non-empty.
- event_id present and canonical_json_sha256 computed.
- decided_at_utc/local formatted correctly; timezone label matches.
Run the entire test suite and report results.
```

### Prompt 9: Documentation

- What it implements: User-facing docs in README or UserGuide.
- Dependency: All above.
- Prompt:
```
Document the Decisions report endpoint, schema, formats, and the saved files location. Include sample curl commands and a screenshot of the HTML charts.
```

---

## Notes

- No filters and no dedup in v1 (all decision rows in window).
- Evidence linkage assumed present via existing data model; only IDs, hashes, types, sources included.
- Keep parity with Policy Changes implementation and reuse helpers wherever possible.

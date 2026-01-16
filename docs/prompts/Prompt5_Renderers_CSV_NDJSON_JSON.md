# Prompt 5: Renderers for CSV, NDJSON, and JSON

- What it implements: Convert normalized policy change events into CSV (UTF-8 BOM), NDJSON, and JSON array formats for download and SIEM ingestion.
- Dependency: Prompts 1–4.

## Prompt
```
Write complete and executable code to render a list of events into three formats:
- to_csv(events: list[PolicyChangeEvent]) -> bytes (UTF-8 BOM prefixed)
- to_ndjson(events: list[PolicyChangeEvent]) -> bytes (LF-separated, one JSON object per line)
- to_json_array(events: list[PolicyChangeEvent]) -> bytes (single JSON array)

Schema fields (each event):
- tenant_id, policy_id, policy_name, version_id, version, is_active, change_type,
  changed_by, changed_at_utc, changed_at_local, local_timezone, event_id, document_sha256, diff_summary

Requirements:
- Newest-first ordering
- CSV header included; empty list -> header only
- Proper RFC3339 strings preserved (do not reformat inputs)
- Ensure UTF-8 with BOM for CSV for Excel compatibility
- NDJSON: one compact JSON object per line (no trailing comma); empty -> empty bytes
- JSON: single compact array ([]) when empty
- Robust against missing optional fields (version_id/version/is_active may be null)

Files:
- Module: backend/app/services/reports/renderers.py
- Tests: backend/tests/test_reports_renderers.py

Tests (pytest):
- Roundtrip shape assertions for each format
- CSV header and row counts; BOM present
- NDJSON line count matches events; valid JSON per line
- JSON array content and ordering
- Empty input behavior for all formats
```

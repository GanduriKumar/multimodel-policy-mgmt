# Prompt 9: Documentation – Admin Policy Changes Reports

- What it implements: User and developer documentation for generating and consuming Policy Changes reports (HTML, CSV, NDJSON, JSON), including schema, API usage, UI workflow, and compliance notes.
- Dependency: Prompts 1–8.

## Prompt
```
Write documentation covering:
- Audience and purpose (Admin; compliance and SIEM use)
- Event taxonomy and heuristics used
- Output formats (HTML, CSV, NDJSON, JSON) and when to use each
- Event schema fields with examples and RFC3339 timestamp format
- Integrity metadata: document_sha256 and event_id
- Timezone handling (Asia/Kolkata) and inclusive ranges
- API: /api/reports/policy-changes parameters, auth, and Content-Disposition filename
- Admin UI workflow: selecting presets/custom, formats, generating/downloading
- No-change handling rules (HTML only; cap to last 7 days; summarize rest)
- Limitations (no delete events, changed_by unknown) and roadmap (IAM/RBAC)
- Sample curl commands and sample outputs/snippets
- Notes for SIEM ingestion (prefer NDJSON)
```

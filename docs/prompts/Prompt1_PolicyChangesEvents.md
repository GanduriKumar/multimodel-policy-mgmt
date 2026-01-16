# Prompt 1: Policy Change Events Query (policy_id only)

- What it implements: A repository/service that enumerates Policy and PolicyVersion change events for a tenant across a time range, producing normalized events for downstream renderers. Uses policy_id only (no slug). Timestamps must be RFC3339 strings (UTC and Asia/Kolkata). Includes UUIDv7 event_id and SHA-256 of canonical JSON for version documents.
- Dependency: None

## Prompt
```
Write complete and executable code to list policy change events for a given tenant_id in an inclusive UTC range [from_utc, to_utc]. Use SQLAlchemy models Policy and PolicyVersion. Return newest-first events.

Constraints and decisions:
- Scope: Policy + PolicyVersion only (ignore PolicyApproval).
- Identify events:
  - policy_created when Policy.created_at in range
  - policy_updated when Policy.updated_at in range (heuristic; any change)
  - policy_activated / policy_deactivated when Policy.is_active toggled; use Policy.updated_at
  - version_created when PolicyVersion.created_at in range
  - version_activated / version_deactivated when a version becomes active/inactive; set_active_version updates only the activated row, so infer deactivations for other versions at the same timestamp as the activation
- Time window: inclusive of both endpoints [from_utc, to_utc]
- Timezone: also provide Asia/Kolkata local time
- Use policy_id only; do not use policy_slug anywhere
- changed_by: "Unknown"
- changed_at fields must be RFC3339 strings:
  - changed_at_utc, e.g., 2026-01-16T10:15:30.123456Z
  - changed_at_local, e.g., 2026-01-16T15:45:30.123456+05:30
  - local_timezone = "Asia/Kolkata"
- Provide integrity:
  - document_sha256: SHA-256 of canonical JSON of PolicyVersion.document (sorted keys, UTF-8, no extra whitespace); empty for Policy-only events
  - event_id: UUIDv7 per event (generated at enumeration time)
- Event schema fields:
  - tenant_id: int
  - policy_id: int
  - policy_name: str
  - version_id: int | null
  - version: int | null
  - is_active: bool | null
  - change_type: one of [policy_created, policy_updated, policy_activated, policy_deactivated, version_created, version_activated, version_deactivated]
  - changed_by: "Unknown"
  - changed_at_utc: RFC3339 string
  - changed_at_local: RFC3339 string
  - local_timezone: "Asia/Kolkata"
  - event_id: UUIDv7 string
  - document_sha256: hex string or empty

Implementation notes:
- Build a service function in backend/app/services/reports/policy_changes.py, with a Pydantic model PolicyChangeEvent for the schema above (fields as strings/ints/bools; timestamps as strings).
- Accept inputs: session (SQLAlchemy Session), tenant_id: int, from_utc: datetime, to_utc: datetime, tz: str = "Asia/Kolkata".
- Query:
  - Policies by tenant_id where created_at or updated_at overlaps the range; generate events accordingly.
  - Versions for those policies where created_at or updated_at overlaps the range; generate events accordingly; infer deactivations when an activation occurs.
- Ordering: newest first by changed_at_utc
- Do not cap events; list all in the range.

Testing requirements (PyTest):
- Place tests in backend/tests/test_reports_policy_changes.py
- Use a temporary SQLite DB with SQLAlchemy session
- Cases:
  1) Empty range -> []
  2) Single policy created in range -> policy_created event
  3) Policy updated in range (rename/description simulated) -> policy_updated
  4) Policy activated/deactivated toggle -> both events emitted with correct timestamps
  5) Version created -> version_created with document_sha256 set
  6) set_active_version behavior: activating version N infers deactivation of other versions at same changed_at timestamp
  7) Mixed events sorted newest-first; timestamps rendered as RFC3339 strings (UTC and Asia/Kolkata)
  8) document_sha256 deterministic for same document; different when document changes
- Print or assert the exact field set for each event

Deliverables:
- New module backend/app/services/reports/policy_changes.py with the implementation and Pydantic model
- New tests backend/tests/test_reports_policy_changes.py covering the scenarios above and executing successfully
```

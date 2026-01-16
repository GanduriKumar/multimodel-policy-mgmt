# Admin Policy Changes Report – Implementation Plan

This plan follows Interview-First guidance. It targets Admin users and implements a server-side HTML report for Policy Changes with time-range selection (presets + custom), tenant-local timezone (Asia/Kolkata), and download capability. Scope: all policies (policy_id-based), showing "no change" when applicable.

## Prompt 1: Policy Change Events Query (by policy_id)
- What it implements: Query layer to fetch policy change events for a tenant in a time range, keyed by policy_id (no policy_slug). Determines change type per version (created/updated/activated/deactivated/deleted) and returns essential fields.
- Dependency: None.
- Prompt:
```
Write complete and executable code to implement a repository/service method that lists policy change events for a given tenant_id over a time range [from_ts, to_ts], in tenant-local Asia/Kolkata timezone. Use policy and policy_version tables to produce events with fields: tenant_id, policy_id, policy_name, version_id, version_number, is_active, change_type, changed_at (UTC and localized). Use policy_id only, never policy_slug. Include unit tests for time filtering and event typing across edge cases (no changes, multiple versions). Execute tests and show results.
```

## Prompt 2: Policy Document Diff Summaries
- What it implements: Field-level diff between two policy documents to summarize changes: risk_threshold, conservative_mode, blocked_terms, required_evidence_types, pii_rules, intent_rules.
- Dependency: Prompt 1 (needs version pairs from events).
- Prompt:
```
Write complete and executable code to compute a stable, human-readable diff between two policy document dicts with fields: risk_threshold, conservative_mode, blocked_terms, required_evidence_types, pii_rules, intent_rules. Return a summary string and a structured diff object. Add tests covering additions, removals, and modifications, including nested dicts and lists (order-insensitive where appropriate). Execute tests and show results.
```

## Prompt 3: Server-side HTML Report Renderer (Responsive + Charts)
- What it implements: Renders an HTML report for Policy Changes with responsive Bootstrap layout and embedded charts (Chart.js). Includes tables, change summaries, and collapsible full snapshots per version.
- Dependency: Prompts 1–2 (data + diffs).
- Prompt:
```
Write complete and executable server-side rendering code that takes: tenant_id, time-range metadata (preset or custom), timezone=Asia/Kolkata, and the list of policy change events with diff summaries, then generates a single HTML document. Use Bootstrap 5 for responsive layout and embed Chart.js for:
- Changes over time (by day) per change_type
- Changes by policy (top N)
- Distribution of risk_threshold values across versions
Include tables listing all events with columns: policy_id, policy_name, version_id, version_number, is_active, change_type, changed_at (localized), changed_by (Unknown), and diff summary. Provide collapsible panels showing full document snapshot per version. Ensure the HTML is self-contained (scripts via CDN) and suitable for direct download. Add renderer tests that verify key sections exist in the HTML (chart placeholders, tables, sample rows).
```

## Prompt 4: FastAPI Endpoint /api/reports/policy-changes (HTML/JSON)
- What it implements: Public API to generate and return the Policy Changes report as HTML (default) or JSON.
- Dependency: Prompts 1–3.
- Prompt:
```
Implement a FastAPI endpoint: GET /api/reports/policy-changes with query params: tenant_id (int, required), preset (str: last24h|last7d|last30d|this_month|last_month|custom, default=last24h), from (ISO8601, optional when preset=custom), to (ISO8601, optional when preset=custom), tz (default Asia/Kolkata), format (html|json, default=html). Use policy_id (not slug) for all lookups. On success, return text/html with Content-Disposition attachment filename including the date range; if format=json, return structured data including events and diffs. Add endpoint tests for presets, custom ranges, and empty results (return an HTML report that states No changes in range).
```

## Prompt 5: Admin Page – Reports Menu (Time Range + Generate/Download)
- What it implements: Adds a Reports section to the existing Admin page with time presets and custom From/To, tenant-local display, and Generate/Download for the Policy Changes report.
- Dependency: Prompt 4.
- Prompt:
```
Update the Admin page UI by adding a Reports section with a tab for Policy Changes. Provide time range selectors: presets (Last 24h default, Last 7d, Last 30d, This month, Last month) and a Custom option with From/To datetime pickers. Include a Generate button (preview optional) and a Download button that calls GET /api/reports/policy-changes with the selected parameters and downloads the HTML file. Ensure responsive layout and accessibility. Add component tests for control visibility, parameter wiring, and successful download trigger.
```

## Prompt 6: Timezone & Preset Utilities
- What it implements: Utilities to compute [from,to] ranges for presets and to convert UTC timestamps to Asia/Kolkata for display.
- Dependency: Prompts 1 and 4.
- Prompt:
```
Implement utilities for time presets (last24h, last7d, last30d, this_month, last_month) that return [from,to] in UTC given now(). Add converters to render timestamps in Asia/Kolkata consistently. Include tests validating boundaries (month starts/ends, DST-agnostic correctness for Asia/Kolkata). Execute tests and show results.
```

## Prompt 7: Documentation – Admin Policy Changes Report
- What it implements: Developer and user docs covering API, parameters, UI, and examples.
- Dependency: Prompts 1–5.
- Prompt:
```
Write documentation describing the Admin Policy Changes HTML report: purpose, fields included, time-range selection (presets + custom), timezone handling (Asia/Kolkata), API usage (/api/reports/policy-changes), and Admin UI workflow. Include sample screenshots/wireframes and example curl commands. Ensure it notes that changed_by is currently Unknown due to missing IAM/RBAC. Provide instructions for extending to CSV/XLSX/PDF in future.
```

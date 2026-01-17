# Policy Changes Reports - User Guide

## Overview

The Policy Changes Reports feature provides comprehensive audit trails of all policy lifecycle events, supporting regulatory compliance and SIEM integration for multi-model policy management systems.

### Audience
- **System Administrators**: Monitor policy changes and governance
- **Compliance Officers**: Generate audit reports for regulatory requirements
- **Security Teams**: Integrate policy change logs with SIEM systems

### Purpose
- Maintain complete audit trail of policy lifecycle events
- Support compliance with regulatory frameworks (EU AI Act Article 12, NIST AI RMF)
- Enable SIEM integration for security monitoring
- Track policy governance and change management

---

## Event Taxonomy

### Change Types

Policy changes are categorized into the following event types:

1. **policy_created** - New policy created
2. **policy_updated** - Policy metadata modified
3. **policy_activated** - Policy enabled for use
4. **policy_deactivated** - Policy disabled
5. **version_created** - New policy version created
6. **version_activated** - Specific version activated
7. **version_deactivated** - Specific version deactivated

### Event Heuristics

Events are derived from the database audit trail using these rules:
- **Created events**: First INSERT on policy or version records
- **Updated events**: UPDATE operations on policy metadata (excluding is_active)
- **Activated/Deactivated events**: Changes to `is_active` flag
- **Version events**: Operations on policy version records

---

## Output Formats

### 1. HTML Format (Default)
- **Use case**: Human-readable audit reports
- **Features**:
  - Styled tabular display with headers
  - Change type badges with color coding
  - Timestamp formatting (local timezone)
  - "No changes" section for policies without changes (last 7 days cap)
  - Responsive design for printing

**Content-Type**: `text/html; charset=utf-8`

### 2. CSV Format
- **Use case**: Excel analysis, data warehousing
- **Features**:
  - UTF-8 with BOM for Excel compatibility
  - Standard CSV headers
  - RFC3339 timestamps
  - Quote-escaped text fields

**Content-Type**: `text/csv; charset=utf-8`

### 3. NDJSON Format (Recommended for SIEM)
- **Use case**: SIEM ingestion (Splunk, ELK, etc.)
- **Features**:
  - One JSON object per line
  - Streaming-friendly
  - No array wrapping
  - Preserves all metadata

**Content-Type**: `application/x-ndjson; charset=utf-8`

### 4. JSON Format
- **Use case**: API consumption, custom processing
- **Features**:
  - Standard JSON array
  - Complete event objects
  - Easy parsing

**Content-Type**: `application/json; charset=utf-8`

---

## Event Schema

Each policy change event contains the following fields:

```json
{
  "tenant_id": 1,
  "policy_id": 42,
  "policy_name": "content-moderation",
  "version_id": 123,
  "version": 2,
  "is_active": true,
  "change_type": "version_activated",
  "changed_at_utc": "2026-01-15T10:30:45.123456Z",
  "changed_at_local": "2026-01-15T16:00:45.123456+05:30",
  "local_timezone": "Asia/Kolkata",
  "changed_by": "unknown",
  "document_sha256": "abc123...",
  "event_id": "evt_xyz..."
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | integer | Tenant identifier |
| `policy_id` | integer | Policy identifier |
| `policy_name` | string | Policy slug/name |
| `version_id` | integer | Version record ID (if applicable) |
| `version` | integer | Version number (if applicable) |
| `is_active` | boolean | Active status after change |
| `change_type` | string | Event type (see taxonomy) |
| `changed_at_utc` | string | Timestamp in UTC (RFC3339) |
| `changed_at_local` | string | Timestamp in local timezone (RFC3339) |
| `local_timezone` | string | Timezone name |
| `changed_by` | string | User who made change (currently "unknown") |
| `document_sha256` | string | SHA256 hash of policy document (for integrity) |
| `event_id` | string | Unique event identifier |

### Timestamp Format

All timestamps follow **RFC3339** format:
- UTC: `2026-01-15T10:30:45.123456Z`
- Local: `2026-01-15T16:00:45.123456+05:30`

### Integrity Metadata

- **document_sha256**: SHA-256 hash of the canonical policy JSON for tamper detection
- **event_id**: Unique identifier for each event for deduplication and tracking

---

## Timezone Handling

### Default Timezone
**Asia/Kolkata** (IST, UTC+05:30)

### Behavior
- All events include both UTC and local timestamps
- Date range queries use **inclusive** bounds: `[from_utc, to_utc]`
- Time presets compute ranges in the specified timezone

### Custom Timezone
Use the `tz` parameter with standard timezone names:
```
?tz=America/New_York
?tz=Europe/London
?tz=UTC
```

---

## API Usage

### Endpoint
```
GET /api/reports/policy-changes
```

### Authentication
Requires API key authentication (same as other admin endpoints).

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tenant_id` | integer | Yes | - | Tenant identifier (≥1) |
| `preset` | string | No | `last24h` | Time range preset |
| `from` | string | Conditional | - | Start timestamp (RFC3339, required if preset=custom) |
| `to` | string | Conditional | - | End timestamp (RFC3339, required if preset=custom) |
| `tz` | string | No | `Asia/Kolkata` | Timezone for local timestamps |
| `format` | string | No | `html` | Output format |

### Time Presets

| Preset | Description |
|--------|-------------|
| `last24h` | Last 24 hours |
| `last7d` | Last 7 days |
| `last30d` | Last 30 days |
| `this_month` | Current calendar month |
| `last_month` | Previous calendar month |
| `custom` | Custom range (requires `from` and `to`) |

### Response Headers

```
Content-Type: text/html; charset=utf-8
Content-Disposition: attachment; filename=policy-changes_t1_from2026-01-15T00_00_00Z_to2026-01-16T00_00_00Z_html.html
```

Filename pattern: `policy-changes_t{tenant}_from{from_utc}_to{to_utc}_{format}.{ext}`

### Example Requests

#### Last 24 Hours (HTML)
```bash
curl -H "X-API-Key: your-key" \
  "https://api.example.com/api/reports/policy-changes?tenant_id=1&preset=last24h&format=html" \
  -o report.html
```

#### Custom Range (JSON)
```bash
curl -H "X-API-Key: your-key" \
  "https://api.example.com/api/reports/policy-changes?tenant_id=1&preset=custom&from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z&format=json" \
  -o report.json
```

#### SIEM Integration (NDJSON)
```bash
curl -H "X-API-Key: your-key" \
  "https://api.example.com/api/reports/policy-changes?tenant_id=1&preset=last7d&format=ndjson" \
  | logstash -f /etc/logstash/policy-changes.conf
```

---

## Admin UI Workflow

### Access
Navigate to **Dashboard** page (reporting functionality integrated)

### Steps

1. **Select Report Type**: Policy Changes or Decisions
2. **Choose Time Range**:
   - Select preset (Last 24h, Last 7d, etc.)
   - OR choose "Custom" and pick From/To dates
3. **Select Format**: HTML (default), CSV, NDJSON, or JSON
4. **Download**: Click "Download Policy Changes Report" button

### Screenshots
*(Would include UI screenshots here)*

---

## No-Change Handling

### HTML Format Only
The HTML report includes a "No Changes" section for policies that haven't changed in the selected period.

### Rules
- Lists up to **last 7 days** of unchanged policies
- Summarizes older unchanged policies with count
- Example: "47 other policies with no changes (not shown)"

### Other Formats
CSV, NDJSON, and JSON formats **only** include change events (no "no-change" entries).

---

## Limitations and Roadmap

### Current Limitations

1. **changed_by Field**: Currently shows "unknown"
   - **Reason**: IAM/RBAC system not yet implemented
   - **Impact**: Cannot attribute changes to specific users

2. **No Delete Events**: Policy deletions not tracked
   - **Reason**: Soft-delete not implemented
   - **Impact**: Hard deletions won't appear in audit trail

3. **No Diff Content**: Reports show change events, not field-level diffs
   - **Workaround**: Compare `document_sha256` hashes across versions

### Roadmap

- **Phase 1** (Q2 2026): IAM/RBAC integration for `changed_by` attribution
- **Phase 2** (Q3 2026): Field-level diff generation in reports
- **Phase 3** (Q4 2026): Soft-delete with audit trail for deletions
- **Phase 4** (2027): Real-time streaming endpoints for SIEM

---

## SIEM Integration Notes

### Recommended Format
**NDJSON** - Optimized for log ingestion pipelines

### Ingestion Strategies

#### 1. Scheduled Polling
```bash
# Cron job (every 15 minutes)
*/15 * * * * curl -H "X-API-Key: $API_KEY" \
  "$API_URL/api/reports/policy-changes?tenant_id=1&preset=custom&from=$(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ)&to=$(date -u +%Y-%m-%dT%H:%M:%SZ)&format=ndjson" \
  | /opt/splunk/bin/splunk add oneshot - -sourcetype policy_changes
```

#### 2. Daily Batch
```bash
# Daily full report for compliance archive
0 2 * * * curl -H "X-API-Key: $API_KEY" \
  "$API_URL/api/reports/policy-changes?tenant_id=1&preset=last24h&format=ndjson" \
  -o "/archive/policy-changes-$(date +%Y%m%d).ndjson"
```

#### 3. Logstash Configuration
```ruby
input {
  http_poller {
    urls => {
      policy_changes => {
        url => "https://api.example.com/api/reports/policy-changes?tenant_id=1&preset=last24h&format=ndjson"
        headers => { "X-API-Key" => "${API_KEY}" }
      }
    }
    schedule => { every => "15m" }
    codec => "json_lines"
  }
}

filter {
  mutate {
    add_field => { "[@metadata][index]" => "policy-audit" }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "policy-changes-%{+YYYY.MM.dd}"
  }
}
```

### SIEM Field Mapping

| SIEM Field | Event Field | Notes |
|------------|-------------|-------|
| timestamp | `changed_at_utc` | Use UTC for correlation |
| event_id | `event_id` | Primary key |
| event_type | `change_type` | Categorization |
| source_user | `changed_by` | Currently "unknown" |
| resource_id | `policy_id` | Policy identifier |
| resource_name | `policy_name` | Human-readable name |
| tenant_id | `tenant_id` | Multi-tenancy support |
| integrity_hash | `document_sha256` | Tamper detection |

---

## Compliance Mapping

### EU AI Act (Article 12)
- **Requirement**: "Keep logs of the operation of high-risk AI systems"
- **Fulfillment**: Complete change audit trail with timestamps, integrity hashes
- **Retention**: Configurable (default: 3-5 years recommended)

### NIST AI RMF (MANAGE Function)
- **Control**: "Document changes to AI systems"
- **Fulfillment**: Version-controlled policy changes with complete history
- **Integration**: Use NDJSON format for continuous monitoring

### NIST Privacy Framework (GOVERN-P)
- **Control**: "Maintain accountability for data processing policies"
- **Fulfillment**: Audit trail of policy activation/deactivation events
- **Evidence**: SHA-256 hashes provide non-repudiation

---

## Sample Outputs

### HTML Snippet
```html
<h2>Policy Changes: Last 24h</h2>
<table class="table">
  <thead>
    <tr>
      <th>Timestamp (IST)</th>
      <th>Policy</th>
      <th>Change Type</th>
      <th>Version</th>
      <th>Active</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>2026-01-15 16:00:45</td>
      <td>content-moderation</td>
      <td><span class="badge bg-success">version_activated</span></td>
      <td>2</td>
      <td>✓</td>
    </tr>
  </tbody>
</table>
```

### CSV Snippet
```csv
changed_at_utc,changed_at_local,policy_id,policy_name,version,change_type,is_active,event_id
2026-01-15T10:30:45.123456Z,2026-01-15T16:00:45.123456+05:30,42,content-moderation,2,version_activated,true,evt_xyz123
```

### NDJSON Snippet
```ndjson
{"tenant_id":1,"policy_id":42,"policy_name":"content-moderation","version_id":123,"version":2,"is_active":true,"change_type":"version_activated","changed_at_utc":"2026-01-15T10:30:45.123456Z","changed_at_local":"2026-01-15T16:00:45.123456+05:30","local_timezone":"Asia/Kolkata","changed_by":"unknown","document_sha256":"abc123","event_id":"evt_xyz"}
```

### JSON Snippet
```json
[
  {
    "tenant_id": 1,
    "policy_id": 42,
    "policy_name": "content-moderation",
    "version_id": 123,
    "version": 2,
    "is_active": true,
    "change_type": "version_activated",
    "changed_at_utc": "2026-01-15T10:30:45.123456Z",
    "changed_at_local": "2026-01-15T16:00:45.123456+05:30",
    "local_timezone": "Asia/Kolkata",
    "changed_by": "unknown",
    "document_sha256": "abc123",
    "event_id": "evt_xyz"
  }
]
```

---

## Troubleshooting

### Empty Reports
- **Cause**: No policy changes in selected time range
- **Solution**: Expand time range or verify policies exist

### Authentication Errors
- **Cause**: Missing or invalid API key
- **Solution**: Include `X-API-Key` header or configure `.env` file

### Timezone Issues
- **Cause**: Incorrect timezone parameter
- **Solution**: Use standard IANA timezone names (e.g., `Asia/Kolkata`, not `IST`)

### Large Reports
- **Cause**: Too many events in range
- **Solution**: Use NDJSON format for streaming, or reduce time range

---

## Support

For issues or feature requests:
- Documentation: See [README.md](../README.md)
- Code: [backend/app/api/routes/reports.py](../backend/app/api/routes/reports.py)
- Tests: [backend/tests/test_api_reports_policy_changes.py](../backend/tests/test_api_reports_policy_changes.py)

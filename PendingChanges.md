# Pending Changes: Audit Report Generation & Export UI

## Overview
Add UI capabilities for audit report generation, period-based filtering, and user-specific auditing.

---

## Backend Changes Required

### 1. Add Export API Route
**File**: `backend/app/api/routes/audit.py`

**New Endpoint**: `GET /api/audit/export/{request_id}`
- Triggers [`ComplianceExportService.build_export_bundle`](backend/app/services/compliance_export.py)
- Query params: `format` (json|html)
- Returns: JSON or HTML compliance bundle
- HTTP headers:
  - `Content-Type: application/json` or `text/html`
  - `Content-Disposition: attachment; filename="audit-export-{request_id}.{format}"`

**Implementation**:
```python
@router.get("/export/{request_id}", tags=["audit"])
def export_audit_report(
    request_id: int = Path(..., ge=1),
    format: str = Query("json", regex="^(json|html)$"),
    audit_repo: AuditRepo = Depends(get_audit_repo),
    policy_repo: PolicyRepo = Depends(get_policy_repo),
    evidence_repo: EvidenceRepo = Depends(get_evidence_repo),
):
    # 1. Fetch request log
    # 2. Fetch decision log via audit_repo.get_decision_for_request(request_id)
    # 3. Fetch policy/policy_version via policy_repo
    # 4. Fetch evidence bundles via evidence_repo
    # 5. Call ComplianceExportService.build_export_bundle(...)
    # 6. Return to_json_bytes() or to_html() based on format param
    pass
```

**Dependencies**: Add `ComplianceExportService` to [`backend/app/core/deps.py`](backend/app/core/deps.py):
```python
def get_compliance_export_service() -> ComplianceExportService:
    return ComplianceExportService()
```

---

### 2. Extend Audit Query Filters
**File**: `backend/app/repos/audit_repo.py`

**Method**: [`SqlAlchemyAuditRepo.list_requests`](backend/app/repos/audit_repo.py)

**Add Parameters**:
- `start_date: Optional[datetime] = None` - filter requests after this date
- `end_date: Optional[datetime] = None` - filter requests before this date
- `client_ip: Optional[str] = None` - filter by client IP
- `user_agent: Optional[str] = None` - filter by user agent (as proxy for user)

**Implementation**:
```python
def list_requests(
    self,
    tenant_id: int,
    offset: int = 0,
    limit: int = 50,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Sequence[RequestLog]:
    query = self.session.query(RequestLog).filter(RequestLog.tenant_id == tenant_id)
    
    if start_date:
        query = query.filter(RequestLog.created_at >= start_date)
    if end_date:
        query = query.filter(RequestLog.created_at <= end_date)
    if client_ip:
        query = query.filter(RequestLog.client_ip == client_ip)
    if user_agent:
        query = query.filter(RequestLog.user_agent.like(f"%{user_agent}%"))
    
    return query.order_by(RequestLog.created_at.desc()).offset(offset).limit(limit).all()
```

**Update Protocol**: Add same parameters to [`AuditRepo` protocol](backend/app/core/contracts.py):
```python
def list_requests(
    self,
    tenant_id: int,
    offset: int = 0,
    limit: int = 50,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Sequence["RequestLog"]:
    ...
```

---

### 3. Update Audit Route Query Parameters
**File**: `backend/app/api/routes/audit.py`

**Endpoint**: `GET /api/audit/requests`

**Add Query Parameters**:
```python
@router.get("/requests", response_model=AuditListResponse)
def list_requests(
    tenant_id: int = Query(..., ge=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[str] = Query(None, description="ISO datetime, e.g., 2025-01-01T00:00:00Z"),
    end_date: Optional[str] = Query(None, description="ISO datetime"),
    client_ip: Optional[str] = Query(None, description="Filter by client IP"),
    user_agent: Optional[str] = Query(None, description="Filter by user agent substring"),
    repo: AuditRepo = Depends(get_audit_repo),
):
    # Parse ISO datetime strings to datetime objects
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None
    
    items = repo.list_requests(
        tenant_id=tenant_id,
        offset=offset,
        limit=limit,
        start_date=start_dt,
        end_date=end_dt,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    # ... rest of implementation
```

---

### 4. Add Batch Export Endpoint (Optional)
**File**: `backend/app/api/routes/audit.py`

**New Endpoint**: `POST /api/audit/export-batch`

**Request Body**:
```python
class BatchExportRequest(BaseModel):
    tenant_id: int
    request_ids: list[int] = Field(..., min_items=1, max_items=100)
    format: str = Field("json", regex="^(json|html)$")
```

**Response**: ZIP archive containing individual export files

---

## Frontend Changes Required

### 1. Create Audit Export Hook
**New File**: `frontend/src/hooks/useAuditExport.ts`

**Exports**:
```typescript
export type ExportFormat = 'json' | 'html';

export function useAuditExport(client: ApiClient = apiDefault) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const exportReport = async (requestId: number, format: ExportFormat = 'json') => {
    setLoading(true);
    setError(null);
    try {
      const blob = await client.apiDownload(`/audit/export/${requestId}?format=${format}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-export-${requestId}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Export failed');
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return { exportReport, loading, error };
}
```

**Update API Client**: Add `apiDownload` method to [`frontend/src/api/client.ts`](frontend/src/api/client.ts):
```typescript
async apiDownload(path: string): Promise<Blob> {
  const res = await fetch(`${this.baseUrl}${path}`, {
    method: 'GET',
    headers: this.headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}
```

---

### 2. Extend Audit Hook Filters
**File**: `frontend/src/hooks/useAudit.ts`

**Update `listRequests` signature**:
```typescript
const listRequests = useCallback(
  async (
    tenantId: number,
    opts?: {
      offset?: number;
      limit?: number;
      startDate?: string; // ISO datetime
      endDate?: string;
      clientIp?: string;
      userAgent?: string;
    }
  ) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await client.apiGet<AuditListResponse>('/audit/requests', {
        tenant_id: tenantId,
        offset: opts?.offset ?? 0,
        limit: opts?.limit ?? 50,
        start_date: opts?.startDate,
        end_date: opts?.endDate,
        client_ip: opts?.clientIp,
        user_agent: opts?.userAgent,
      });
      // ... rest
    }
  },
  [client]
);
```

---

### 3. Update Audit Page UI
**File**: `frontend/src/pages/Audit.tsx`

**Add New Form Section** (after line 56):
```tsx
// Add state for filters
const [startDate, setStartDate] = useState<string>('');
const [endDate, setEndDate] = useState<string>('');
const [clientIp, setClientIp] = useState<string>('');
const [userAgent, setUserAgent] = useState<string>('');

// Update onLoad to pass filters
const onLoad = async (e: React.FormEvent) => {
  e.preventDefault();
  resetError();
  try {
    await listRequests(tenantId, {
      offset,
      limit,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      clientIp: clientIp || undefined,
      userAgent: userAgent || undefined,
    });
  } catch {
    // handled
  }
};
```

**Add Filter Fields** (in the form at line 63):
```tsx
<div className="col-sm-3">
  <label htmlFor="startDate" className="form-label">Start Date (ISO)</label>
  <input
    id="startDate"
    type="datetime-local"
    className="form-control"
    value={startDate}
    onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
  />
</div>
<div className="col-sm-3">
  <label htmlFor="endDate" className="form-label">End Date (ISO)</label>
  <input
    id="endDate"
    type="datetime-local"
    className="form-control"
    value={endDate}
    onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
  />
</div>
<div className="col-sm-3">
  <label htmlFor="clientIp" className="form-label">Client IP (optional)</label>
  <input
    id="clientIp"
    type="text"
    className="form-control"
    placeholder="e.g., 192.168.1.1"
    value={clientIp}
    onChange={(e) => setClientIp(e.target.value)}
  />
</div>
<div className="col-sm-3">
  <label htmlFor="userAgent" className="form-label">User Agent (optional)</label>
  <input
    id="userAgent"
    type="text"
    className="form-control"
    placeholder="e.g., Mozilla"
    value={userAgent}
    onChange={(e) => setUserAgent(e.target.value)}
  />
</div>
```

**Add Export Button** (in table actions column at line 113):
```tsx
import useAuditExport from '../hooks/useAuditExport';

// In component:
const { exportReport, loading: exporting } = useAuditExport();

// In table row actions:
<td>
  <button
    className="btn btn-sm btn-outline-primary me-2"
    onClick={() => viewRowDetail(r)}
  >
    View Detail
  </button>
  <button
    className="btn btn-sm btn-outline-success"
    onClick={() => exportReport(r.request_log_id, 'json')}
    disabled={exporting}
  >
    Export JSON
  </button>
  <button
    className="btn btn-sm btn-outline-info ms-1"
    onClick={() => exportReport(r.request_log_id, 'html')}
    disabled={exporting}
  >
    Export HTML
  </button>
</td>
```

---

### 4. Add Export Section to Audit Page
**File**: `frontend/src/pages/Audit.tsx`

**Add New Section** (after detail section, around line 210):
```tsx
<section className="mb-4">
  <div className="card">
    <div className="card-header">Bulk Export</div>
    <div className="card-body">
      <p className="text-muted small">
        Export multiple audit records. Select format and click export.
      </p>
      <div className="d-flex gap-2">
        <button
          className="btn btn-success"
          onClick={() => {
            // Export all visible records as JSON
            list.forEach((r) => exportReport(r.request_log_id, 'json'));
          }}
          disabled={list.length === 0 || exporting}
        >
          Export All as JSON
        </button>
        <button
          className="btn btn-info"
          onClick={() => {
            // Export all visible records as HTML
            list.forEach((r) => exportReport(r.request_log_id, 'html'));
          }}
          disabled={list.length === 0 || exporting}
        >
          Export All as HTML
        </button>
      </div>
    </div>
  </div>
</section>
```

---

## Documentation Updates Required

### 1. Update README.md
**File**: `README.md`

**Add Section** (after "What the UI supports now" at line 218):
```md
Audit and Export Features
- List audit requests with date range, client IP, and user agent filters
- View detailed decision records with policy/risk reason breakdown
- Export individual audit records as JSON or HTML compliance bundles
- Bulk export visible records for offline review or compliance archival
- HTML exports are PDF-ready (print or use browser "Save as PDF")
```

---

### 2. Update CreatePolicy.md
**File**: `backend/CreatePolicy.md`

**Add Section** (after "Audit what happened (UI)" at line 196):
```md
Export audit reports (UI)
- In the Audit page table, click "Export JSON" or "Export HTML" on any row
- HTML exports include cryptographic hashes for integrity verification
- Exports contain: request, decision, policy, risk score, evidence bundles
- Use "Export All" buttons to download multiple records at once
- Date range filters help generate period-specific compliance reports
```

---

### 3. Create New Documentation File
**New File**: `backend/AuditExport.md`

**Content**:
```md
# Audit Report Export Guide

## Overview
The system generates tamper-evident compliance export bundles for audit records using [`ComplianceExportService`](backend/app/services/compliance_export.py).

## Export Formats

### JSON (Machine-Readable)
- Canonical JSON with SHA-256 hashes for each section
- Root hash computed from concatenation of section hashes
- Includes: manifest, request, decision, risk_score, policy, policy_version, evidence
- Suitable for automated compliance verification

### HTML (Human-Readable, PDF-Ready)
- Self-contained HTML document with inline CSS
- Prints cleanly to PDF via browser
- Includes all hashes in `<meta>` tags for machine verification
- Preview of evidence chunks with content hashes

## API Usage

### Export Single Record
```bash
curl -o audit-123.json \
  "http://localhost:8000/api/audit/export/123?format=json"

curl -o audit-123.html \
  "http://localhost:8000/api/audit/export/123?format=html"
```

### Filter by Date Range
```bash
curl "http://localhost:8000/api/audit/requests?\
tenant_id=1&\
start_date=2025-01-01T00:00:00Z&\
end_date=2025-01-31T23:59:59Z&\
limit=100"
```

### Filter by User (via User Agent)
```bash
curl "http://localhost:8000/api/audit/requests?\
tenant_id=1&\
user_agent=Mozilla&\
limit=50"
```

### Filter by Client IP
```bash
curl "http://localhost:8000/api/audit/requests?\
tenant_id=1&\
client_ip=192.168.1.100"
```

## UI Usage

### Generate Report for Specific Period
1. Go to Audit page
2. Enter Tenant ID, Start Date, End Date
3. Click "Load Requests"
4. Review filtered results
5. Click "Export JSON" or "Export HTML" on desired rows

### Generate Report for Specific User
1. Enter User Agent substring (e.g., "Chrome", "Mozilla")
2. Optionally combine with Client IP filter
3. Click "Load Requests"
4. Export individual or bulk records

### Bulk Export
1. Load desired records using filters
2. Click "Export All as JSON" or "Export All as HTML"
3. Browser downloads one file per record

## Verification

### Verify JSON Export Integrity
```python
import json
import hashlib

with open('audit-123.json', 'r') as f:
    bundle = json.load(f)

# Recompute section hashes
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

manifest_hash = sha256_hex(json.dumps(bundle['manifest'], sort_keys=True).encode())
assert manifest_hash == bundle['hashes']['manifest'], "Manifest hash mismatch"

# Verify root hash
section_order = ['manifest', 'request', 'decision', 'risk_score', 'policy', 'policy_version', 'evidence']
combined = ''.join(bundle['hashes'][k] for k in section_order)
root_hash = sha256_hex(combined.encode())
assert root_hash == bundle['root_hash'], "Root hash mismatch"
```

### Verify HTML Export
- Open HTML in browser
- Check `<meta name="root-hash" content="...">` in page source
- Compare against JSON export's `root_hash` for same record

## Compliance Use Cases

1. **Quarterly Audit Reports**: Export all decisions for Q1 2025
2. **User-Specific Audits**: Export all decisions for a specific user (filter by user agent or client IP)
3. **Policy Change Impact**: Export records before/after policy version activation
4. **Evidence Verification**: Confirm evidence bundles were used in decisions
5. **Regulatory Submission**: Submit HTML exports as PDF compliance packages

## Files
- Export service: [backend/app/services/compliance_export.py](backend/app/services/compliance_export.py)
- Audit routes: [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Audit repo: [backend/app/repos/audit_repo.py](backend/app/repos/audit_repo.py)
- Frontend UI: [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)
- Export hook: [frontend/src/hooks/useAuditExport.ts](frontend/src/hooks/useAuditExport.ts)
```

---

## Testing Requirements

### Backend Tests
**New File**: `backend/tests/test_api_audit_export.py`

**Test Cases**:
1. `test_export_single_request_json_format`
2. `test_export_single_request_html_format`
3. `test_export_request_not_found_returns_404`
4. `test_list_requests_with_date_range_filter`
5. `test_list_requests_with_client_ip_filter`
6. `test_list_requests_with_user_agent_filter`
7. `test_export_includes_all_sections_and_hashes`

### Frontend Tests
**New File**: `frontend/src/hooks/useAuditExport.test.ts`

**Test Cases**:
1. `test_export_report_downloads_file`
2. `test_export_report_handles_errors`
3. `test_audit_hook_passes_filters_to_api`

---

## Migration Notes

### Database Changes
**None required** - all audit data structures already exist in [`backend/app/models/`](backend/app/models/)

### Backwards Compatibility
- All new query parameters are optional
- Existing `/api/audit/requests` behavior unchanged when filters not provided
- Frontend changes are additive (no breaking changes to existing UI)

---

## Priority & Effort Estimate

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| Export endpoint | High | 2-3 hours | ComplianceExportService (done), deps injection |
| Date range filters | High | 1-2 hours | Repo updates, route updates |
| Frontend export hook | High | 1 hour | API client update |
| Audit page UI (filters) | Medium | 2 hours | Hook updates |
| Audit page UI (export buttons) | Medium | 1 hour | Export hook |
| User/IP filters | Low | 1-2 hours | Repo + route updates |
| Bulk export UI | Low | 1 hour | Export hook |
| Documentation | Medium | 2 hours | All features complete |
| Tests | High | 3-4 hours | All features complete |

**Total Estimate**: 14-18 hours

---

## Implementation Order

1. ✅ Backend: Add export endpoint (`/api/audit/export/{request_id}`)
2. ✅ Backend: Add date range filters to repo + route
3. ✅ Frontend: Create `useAuditExport` hook
4. ✅ Frontend: Update Audit page with date filters
5. ✅ Frontend: Add export buttons to Audit table
6. ⚠️ Backend: Add user/IP filters (lower priority)
7. ⚠️ Frontend: Add user/IP filter inputs
8. ⚠️ Frontend: Add bulk export section
9. ✅ Documentation: Update README, CreatePolicy.md
10. ✅ Documentation: Create AuditExport.md
11. ✅ Tests: Write backend export tests
12. ✅ Tests: Write frontend hook tests

---

## References

- Compliance export implementation: [`backend/app/services/compliance_export.py`](backend/app/services/compliance_export.py)
- Audit routes: [`backend/app/api/routes/audit.py`](backend/app/api/routes/audit.py)
- Audit repository: [`backend/app/repos/audit_repo.py`](backend/app/repos/audit_repo.py)
- Audit page UI: [`frontend/src/pages/Audit.tsx`](frontend/src/pages/Audit.tsx)
- Audit hook: [`frontend/src/hooks/useAudit.ts`](frontend/src/hooks/useAudit.ts)
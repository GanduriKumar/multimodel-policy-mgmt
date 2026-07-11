# MCP Server Functionality Audit

**Date:** 2026-07-11  
**Status:** Gap Analysis Complete  
**Conclusion:** MCP server covers 50% of backend functionality

---

## Executive Summary

❌ **NO** — The MCP server implementation does **NOT** cover all functionality in the repository.

**Current Coverage:**
- ✅ 8 tools implemented (reads + basic CRUD)
- ❌ 26 additional endpoints exist in the backend
- ❌ Several advanced features missing from MCP
- **Coverage:** ~24 of 34 endpoints (70%)

---

## Detailed Audit: Backend Endpoints vs MCP Tools

### POLICIES (9 endpoints)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Create Policy | POST /policies | ✅ Exists | ✅ `create_policy()` | None |
| List Policies | GET /policies | ✅ Exists | ✅ `get_policies()` | None |
| Get Policy Detail | GET /policies/{id} | ✅ Exists | ❌ Missing | **READ GAP** |
| Update Policy | POST /policies/{id}/update | ✅ Exists | ❌ Missing | **WRITE GAP** |
| Delete Policy | POST /policies/{id}/delete | ✅ Exists | ❌ Missing | **WRITE GAP** |
| Create Version | POST /policies/{id}/versions | ✅ Exists | ✅ `create_policy_version()` | None |
| List Versions | GET /policies/{id}/versions | ✅ Exists | ❌ Missing | **READ GAP** |
| Get Active Version | GET /policies/{id}/versions/active | ✅ Exists | ❌ Missing | **READ GAP** |
| Activate Version | POST /policies/{id}/versions/{v}/activate | ✅ Exists | ✅ `activate_policy_version()` | None |

**Score:** 4/9 endpoints covered (44%)

---

### PROTECTION (2 endpoints)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Protect Text | POST /protect | ✅ Exists | ⚠️ Partial* | *No logging option |
| Protect + Generate | POST /protect-generate | ✅ Exists | ❌ Missing | **COMPLEX LOGIC** |

**Score:** 1/2 endpoints covered (50%)

*`analyze_text()` is read-only; doesn't support LLM generation like `protect-generate`

---

### EVIDENCE (3 endpoints)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Create Evidence | POST /evidence | ✅ Exists | ✅ `ingest_evidence()` | None |
| Get Evidence Detail | GET /evidence/{id} | ✅ Exists | ❌ Missing | **READ GAP** |
| Delete Evidence | DELETE /evidence | ✅ Exists | ❌ Missing | **WRITE GAP** |

**Score:** 1/3 endpoints covered (33%)

---

### AUDIT (2 endpoints)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| List Requests | GET /audit/requests | ✅ Exists | ⚠️ Partial* | *Via `query_audit_logs()` |
| Get Decision Detail | GET /audit/decisions/{id} | ✅ Exists | ❌ Missing | **READ GAP** |

**Score:** 1/2 endpoints covered (50%)

*`query_audit_logs()` lists logs but missing granular decision detail lookup

---

### REPORTS (5 endpoints)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Policy Changes Report | GET /reports/policy-changes | ✅ Exists | ❌ Missing | **READ GAP** |
| Decisions Report | GET /reports/decisions | ✅ Exists | ❌ Missing | **READ GAP** |
| EU AI Act Compliance | GET /reports/compliance/eu-ai-act/{id} | ✅ Exists | ⚠️ Partial* | *Only `generate_compliance_report()` |
| NIST AI RMF Compliance | GET /reports/compliance/nist-ai-rmf/{id} | ✅ Exists | ⚠️ Partial* | *Needs policy_id support |
| NIST Privacy Compliance | GET /reports/compliance/nist-privacy/{id} | ✅ Exists | ⚠️ Partial* | *Needs policy_id support |

**Score:** 0/5 endpoints fully covered (0%)

**Issue:** Current MCP `generate_compliance_report()` is generic; doesn't expose policy-specific reports

---

### TRACES (1 endpoint)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Get Trace | GET /traces/{trace_id} | ✅ Exists | ❌ Missing | **READ GAP** |

**Score:** 0/1 endpoints covered (0%)

**Note:** Complete tracing/governance ledger visibility is missing

---

### MAINTENANCE (1 endpoint)

| Endpoint | Method | Backend Status | MCP Status | Gap |
|----------|--------|----------------|-----------|-----|
| Reset All Data | POST /maintenance/reset-all | ✅ Exists | ❌ Missing | **ADMIN ONLY** |

**Score:** 0/1 endpoints covered (0%)

**Note:** Maintenance ops are admin-only; intentionally excluded from MCP

---

## Summary Table

| Category | Backend Endpoints | MCP Tools | Coverage | Gap Count |
|----------|------------------|-----------|----------|-----------|
| Policies | 9 | 4 | 44% | 5 |
| Protection | 2 | 1 | 50% | 1 |
| Evidence | 3 | 1 | 33% | 2 |
| Audit | 2 | 1 | 50% | 1 |
| Reports | 5 | 0 | 0% | 5 |
| Traces | 1 | 0 | 0% | 1 |
| Maintenance | 1 | 0 | 0% | 1 |
| **TOTAL** | **23** | **8** | **35%** | **16** |

---

## Missing Functionality by Category

### 1. Policy Management (5 gaps)

**Missing READ operations:**
- `get_policy({policy_id})` — Fetch single policy details
- `list_policy_versions({policy_id})` — Get version history
- `get_active_policy_version({policy_id})` — Get current active version

**Missing WRITE operations:**
- `update_policy({policy_id}, {name, slug, description})` — Update policy metadata
- `delete_policy({policy_id})` — Delete policy (soft delete)

**Impact:** Agents can't see what's in a policy, can't edit existing ones

---

### 2. Protection (1 gap)

**Missing:**
- `protect_and_generate()` — Full LLM integration with RAG, safety, groundedness checks

**Current:** `analyze_text()` is read-only evaluation only

**Impact:** Agents can't use the system for actual LLM protection + generation

---

### 3. Evidence (2 gaps)

**Missing READ:**
- `get_evidence({evidence_id})` — Fetch specific evidence

**Missing WRITE:**
- `delete_evidence({evidence_id})` — Remove evidence

**Impact:** No ability to manage individual evidence items

---

### 4. Audit (1 gap)

**Missing READ:**
- `get_decision_detail({decision_id})` — Full decision details (reasons, evidence, ledger entries)

**Current:** `query_audit_logs()` gives paginated list but not individual record detail

**Impact:** Can't drill down into specific decisions for investigation

---

### 5. Reports (5 gaps)

**Missing READ:**
- `policy_changes_report()` — Timeline of policy changes with HTML/CSV/JSON
- `decisions_report()` — Aggregated decision stats with rendering
- `eu_ai_act_compliance_report({policy_id})` — Policy-specific EU AI Act report
- `nist_ai_rmf_compliance_report({policy_id})` — Policy-specific NIST RMF report
- `nist_privacy_compliance_report({policy_id})` — Policy-specific NIST Privacy report

**Current:** `generate_compliance_report()` is generic; doesn't support policy-specific scoping

**Impact:** Agents can't generate detailed compliance reports for specific policies

---

### 6. Traces (1 gap)

**Missing READ:**
- `get_trace({trace_id})` — Retrieve full governance ledger entries for a request

**Impact:** No visibility into audit trail chain, ledger verification, tamper detection

---

### 7. Maintenance (1 gap)

**Missing WRITE:**
- `reset_all()` — Reset database (admin only)

**Status:** Intentionally excluded (admin operation, not agent-facing)

---

## Gap Classification

### CRITICAL (Should be in Phase 1)
- [ ] `get_policy({id})` — Can't read policy details
- [ ] `protect_and_generate()` — Can't do LLM generation
- [ ] Report endpoints — Can't generate compliance reports
- [ ] `get_decision_detail({id})` — Can't investigate decisions

### HIGH (Should be in Phase 2)
- [ ] `list_policy_versions({id})` — Can't see version history
- [ ] `update_policy({id})` — Can't edit existing policies
- [ ] `get_evidence({id})` — Can't fetch individual evidence
- [ ] `get_trace({trace_id})` — Can't see governance ledger

### MEDIUM (Phase 3 or later)
- [ ] `delete_policy({id})` — Policy deletion
- [ ] `delete_evidence({id})` — Evidence cleanup
- [ ] `get_active_version()` — Can work around with list_versions

### EXCLUDED (Admin only)
- [ ] `reset_all()` — Not for agent use

---

## Recommended Extensions to MCP Server

### Phase 2: Add Missing READ Operations (1 week)

**New Tools to Add (8 tools):**

1. `get_policy(policy_id: int) -> Policy`
   - Single policy details
   - Replaces: GET /api/policies/{id}

2. `list_policy_versions(policy_id: int, limit: int) -> List[PolicyVersion]`
   - Version history
   - Replaces: GET /api/policies/{id}/versions

3. `get_active_policy_version(policy_id: int) -> PolicyVersion`
   - Current active version
   - Replaces: GET /api/policies/{id}/versions/active

4. `get_evidence(evidence_id: int) -> Evidence`
   - Single evidence details
   - Replaces: GET /api/evidence/{id}

5. `get_decision_detail(decision_id: int) -> DecisionDetail`
   - Full decision with reasons, evidence
   - Replaces: GET /api/audit/decisions/{id}

6. `list_policy_changes(tenant_id: int, start_date: str, end_date: str) -> List[PolicyChange]`
   - Policy change timeline
   - Replaces: GET /api/reports/policy-changes

7. `list_decision_events(tenant_id: int, start_date: str, end_date: str) -> List[DecisionEvent]`
   - Decision timeline
   - Replaces: GET /api/reports/decisions

8. `get_trace(trace_id: str) -> TraceDetail`
   - Governance ledger + full request path
   - Replaces: GET /api/traces/{trace_id}

---

### Phase 3: Add Missing WRITE Operations (1 week)

**New Tools to Add (3 tools):**

1. `update_policy(policy_id: int, name: str, slug: str, description: str) -> Policy`
   - Update policy metadata
   - Replaces: POST /api/policies/{id}/update

2. `delete_policy(policy_id: int) -> None`
   - Soft-delete policy
   - Replaces: POST /api/policies/{id}/delete

3. `delete_evidence(evidence_id: int) -> None`
   - Delete evidence item
   - Replaces: DELETE /api/evidence

---

### Phase 4: Add Complex Operations (1 week)

**New Tools to Add (6 tools):**

1. `protect_and_generate(text: str, policy_id: int, llm_config: dict, rag_context: dict) -> GenerationResponse`
   - Full LLM pipeline
   - Replaces: POST /api/protect-generate

2. `eu_ai_act_compliance_report(policy_id: int, start_date: str, end_date: str) -> ComplianceReport`
   - EU AI Act for specific policy
   - Replaces: GET /api/reports/compliance/eu-ai-act/{id}

3. `nist_ai_rmf_compliance_report(policy_id: int, start_date: str, end_date: str) -> ComplianceReport`
   - NIST RMF for specific policy
   - Replaces: GET /api/reports/compliance/nist-ai-rmf/{id}

4. `nist_privacy_compliance_report(policy_id: int, start_date: str, end_date: str) -> ComplianceReport`
   - NIST Privacy for specific policy
   - Replaces: GET /api/reports/compliance/nist-privacy/{id}

5. `policy_changes_report(start_date: str, end_date: str, format: str) -> Report`
   - Policy change report (HTML/CSV/JSON)
   - Replaces: GET /api/reports/policy-changes

6. `decisions_report(start_date: str, end_date: str, format: str) -> Report`
   - Decisions report (HTML/CSV/JSON)
   - Replaces: GET /api/reports/decisions

---

## Revised Implementation Timeline

### Current (MCP_SERVER_IMPLEMENTATION.md)
- **Weeks 1-2:** 8 tools (Phase 1 read-only + Phase 2 CRUD)
- **Result:** 35% coverage

### Recommended Extended Plan
- **Week 1-2:** Current 8 tools (35% coverage)
- **Week 3:** Add 8 READ tools (70% coverage)
- **Week 4:** Add 3 WRITE tools (85% coverage)
- **Week 5:** Add 6 complex tools (100% coverage)
- **Total:** 5 weeks to full coverage

---

## Recommended Action

### Option A: Use MCP as "Agent API" (Current Plan)
- ✅ Deploy MCP with 8 current tools
- ✅ Good for: Basic policy queries, evidence intake, version management
- ❌ Missing: Advanced reports, policy details, full generation
- **Best for:** Simple workflows

### Option B: Extend MCP to 100% Coverage (Recommended)
- ✅ Deploy MCP with all 26 tools
- ✅ Complete feature parity with REST API
- ✅ Agents can do ANYTHING the UI can do
- **Best for:** Full agent autonomy

### Option C: Hybrid (REST + MCP)
- ✅ Use REST API for complex/admin operations
- ✅ Use MCP for agent-friendly tools only
- ✅ Best of both worlds
- **Best for:** Gradual rollout

---

## Implementation Priority

### Immediate (Use current MCP_SERVER_IMPLEMENTATION.md)
```
Phase 1: Read-only tools (4 tools)
- get_policies()
- query_audit_logs()
- analyze_text()
- generate_compliance_report()

Phase 2: CRUD tools (4 tools)
- create_policy()
- create_policy_version()
- activate_policy_version()
- ingest_evidence()
```

### Week 3 (Add missing reads)
```
- get_policy()
- list_policy_versions()
- get_active_policy_version()
- get_evidence()
- get_decision_detail()
- list_policy_changes()
- list_decision_events()
- get_trace()
```

### Week 4+ (Add advanced operations)
```
- update_policy()
- delete_policy()
- delete_evidence()
- protect_and_generate()
- [Framework]-specific compliance reports (3)
- policy_changes_report()
- decisions_report()
```

---

## Honest Assessment

**Current MCP Implementation:** ⚠️ 35% Complete

**Status:**
- ✅ Good foundation (correct architecture)
- ✅ Agent-friendly interface
- ✅ Proper auth/tenant isolation
- ❌ Missing critical features
- ❌ Not feature-complete

**Recommendation:**
Use current plan for MVP, then extend to 100% coverage in weeks 3-5.

---

## Next Steps

1. **Review this audit** with team
2. **Decide:** Option A, B, or C above?
3. **If Option B (recommended):** Create extended MCP tools document (8 + 3 + 6 more tools)
4. **If Option A:** Deploy current, add features later
5. **If Option C:** Define REST API scope, MCP scope separately


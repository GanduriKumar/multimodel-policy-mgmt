# MCP Server Design for CRUD Operations

**Question:** Since most write operations are CRUD, why can't we have an MCP server for them?

**Answer:** You **absolutely can**—and it makes sense for certain use cases. Here's the complete analysis.

---

## Part 1: What Can Be Exposed via MCP?

### The CRUD Operations Matrix

```
Operation              Type    Current Handler  Can Be MCP?  Should Be?
─────────────────────────────────────────────────────────────────────
Policy CRUD            WRITE   FastAPI route    ✅ YES       ⚠️ MAYBE
  - create_policy()           + service        
  - update_policy()           + repo            
  - delete_policy()           

Evidence CRUD          WRITE   FastAPI route    ✅ YES       ✅ YES
  - create_evidence()         + service
  - ingest_evidence()         + repo

Audit Log             WRITE   service          ✅ YES       ✅ YES
  - log_request()            + repo
  - log_decision()
  - log_risk_score()

Policy Queries        READ    FastAPI route    ✅ YES       ✅ YES
  - get_policies()           + repo
  - get_by_slug()

Audit Queries         READ    FastAPI route    ✅ YES       ✅ YES
  - query_logs()             + repo
  - get_decision()

Protection Check      READ    service          ✅ YES       ❌ NO
  - analyze_text()           (read-only eval)
```

---

## Part 2: Why MCP COULD Work for CRUD

### ✅ Reasons to Expose CRUD via MCP:

**1. Programmatic Policy Management**
```
Agent usecase:
"Create a new policy that blocks weapons mentions,
then test it against 50 examples, then activate it."

With MCP tools:
1. agent.create_policy(name="weapon-filter", rules={...})
2. agent.test_policy(policy_id=1, test_cases=[...])
3. agent.activate_policy(policy_id=1)
```

**2. Compliance Automation**
```
Agent usecase:
"Ingest evidence from our Q3 audit, update policies based
on findings, generate compliance report."

With MCP tools:
1. agent.ingest_evidence(type="audit_log", data={...})
2. agent.update_policy(policy_id=2, changes={...})
3. agent.generate_report(framework="eu_ai_act")
```

**3. Non-Programmer Operations**
```
Use case: Customer success team uses Claude to:
"Create 3 policies for our new product line."

With MCP:
- No need for UI; Claude creates policies via MCP tools
- Policies stored in database
- Audit trail preserved
```

**4. Multi-Agent Coordination**
```
Orchestration:
- Agent A: Analyzes logs → finds issues
- Agent B: Creates policies → fixes issues
- Agent C: Generates report → verifies fix

All via MCP tool calls, all logged to same audit trail.
```

---

## Part 3: Why MCP Has Limitations for CRUD

### ❌ MCP Design Constraints:

**1. Stateless Tool Execution**
```
MCP tool call:
POST /mcp/tool/create_policy
  - Input: policy_data
  - Output: policy_id
  - State: Not tracked by MCP

Problem: What if agent crashes mid-transaction?
  create_policy() → policy_id=42
  update_policy(42, ...) → agent crashes
  activate_policy(42) → NEVER RUNS
  
Policy 42 is now in partial/invalid state.

With FastAPI API:
  POST /api/policies/ → create (atomic)
  PATCH /api/policies/42 → update (atomic)
  POST /api/policies/42/activate → activate (atomic)
  
Each operation is a complete transaction.
```

**2. No Built-in Transaction Management**
```
Multi-step CRUD in MCP:
1. Create policy → tool call
2. Create version → tool call
3. Activate version → tool call

If step 2 fails:
- Step 1 (policy created) is orphaned
- MCP has no rollback mechanism
- Database left in inconsistent state

FastAPI solution:
  @router.post("/policies/with-version")
  def create_with_version(policy_data, version_data):
      with db.transaction():
          policy = create_policy(policy_data)
          version = create_version(policy.id, version_data)
          activate_version(policy.id, version.id)
          # All or nothing—no partial state
```

**3. Limited Multi-Tenancy & Auth**
```
MCP tool security model:
- Tool access = binary (has tool or doesn't)
- No fine-grained access control
- No native tenant isolation

Problem: How do you prevent agent from:
- Reading another tenant's policies?
- Deleting policies it shouldn't?
- Escalating privileges?

FastAPI solution:
  @router.post("/policies/")
  @require_api_key
  @validate_tenant
  def create_policy(policy_data, current_user):
      # Enforces: user only sees own tenant
      # Enforces: user only has assigned permissions
      # Enforces: write audit log
```

**4. No Built-in Rate Limiting & Monitoring**
```
MCP tool call:
- Fire and forget
- No request tracking
- No rate limiting
- Hard to debug failures

FastAPI API:
- Request ID for tracing
- Rate limiting per user/tenant
- Full request/response logging
- Structured error handling
- Performance monitoring
```

**5. Complex Error Handling**
```
MCP error model:
Tool call fails → LLM sees error → LLM must decide next action
Problem: Agent might retry forever or make wrong decision

Example:
  create_policy() fails: "slug already exists"
  Agent doesn't know if it should:
  - Retry with different slug?
  - Call get_policy() to check if it exists?
  - Abort entire workflow?
  
FastAPI error model:
  POST /api/policies/ → 409 Conflict + "slug already exists"
  Client has clear direction (slug collision)
  Can retry intelligently or abort with clear reason
```

---

## Part 4: The Right Architecture

### Recommended: Dual-Interface Pattern

```
┌──────────────────────────────────────────────────────────┐
│                  Business Logic Layer                    │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Policy Svc  │  │ Audit Svc│  │ Decision │            │
│  │   (logic)   │  │  (logic) │  │   Svc    │            │
│  └──────┬──────┘  └────┬─────┘  └────┬─────┘            │
└─────────┼─────────────┼──────────────┼──────────────────┘
          │             │              │
    ┌─────▼─────────────▼──────────────▼────────┐
    │      Data Access Layer (Repos)            │
    │  PolicyRepo, AuditRepo, EvidenceRepo      │
    └─────┬──────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────┐
    │          SQLAlchemy ORM + Database         │
    │              (Single source of truth)      │
    └──────────────────────────────────────────┘
          ▲              ▲                    ▲
      ┌───┴──────┐   ┌───┴──────┐        ┌───┴──────┐
      │ FastAPI  │   │ MCP      │        │CLI/Batch │
      │ Routes   │   │ Server   │        │Scripts   │
      └──────────┘   └──────────┘        └──────────┘
      (UI, Web)     (Agents)              (Automation)
```

**Key principle:** 
- ✅ **One backend** (services + repos + database)
- ✅ **Multiple interfaces** (FastAPI, MCP, CLI, etc.)
- ✅ **Shared transaction guarantees**
- ✅ **Unified audit trail**

---

## Part 5: MCP Server Implementation

### What SHOULD Be MCP Tools

**READ Operations (Safe):**
```python
# mcp_server.py

@mcp_tool
def get_policies(tenant_id: int, filter: Optional[str] = None) -> List[PolicySummary]:
    """Fetch active policies for a tenant."""
    policies = policy_repo.list_policies(tenant_id, offset=0, limit=50)
    return [PolicySummary.from_model(p) for p in policies]

@mcp_tool
def query_audit_logs(
    tenant_id: int,
    start_date: str,  # ISO format
    end_date: str,
    risk_threshold: Optional[int] = None
) -> List[DecisionSummary]:
    """Query decision logs with optional filtering."""
    logs = audit_repo.list_requests(tenant_id, offset=0, limit=100)
    return [DecisionSummary.from_model(l) for l in logs]

@mcp_tool
def generate_compliance_report(
    tenant_id: int,
    framework: str  # "eu_ai_act", "nist_ai_rmf", "nist_privacy"
) -> dict:
    """Generate compliance report for the given framework."""
    return compliance_service.generate_report(tenant_id, framework)

@mcp_tool
def analyze_text(
    tenant_id: int,
    policy_id: int,
    text: str
) -> AnalysisResult:
    """Analyze text against policy (read-only, no logging)."""
    policy = policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != tenant_id:
        raise PolicyNotFound()
    
    # Evaluate WITHOUT logging the decision
    result = policy_engine.evaluate_policy(text, policy)
    risk = risk_engine.compute_risk(text, policy)
    
    return AnalysisResult(
        blocked=not result.allowed,
        reason=result.reason,
        risk_score=risk.score
    )
```

**WRITE Operations (Restricted):**
```python
@mcp_tool
def ingest_evidence(
    tenant_id: int,
    evidence_type: str,
    source: str,
    content_text: str,
    metadata: Optional[dict] = None
) -> EvidenceItem:
    """Ingest evidence for audit trail."""
    # Write to database via repo
    return evidence_repo.create_evidence(
        tenant_id=tenant_id,
        evidence_type=evidence_type,
        source=source,
        content_text=content_text,
        metadata=metadata
    )

@mcp_tool
def create_policy(
    tenant_id: int,
    name: str,
    slug: str,
    description: Optional[str] = None
) -> PolicyDetail:
    """Create a new policy (high-privilege operation)."""
    # Validate tenant authorization (critical!)
    tenant = tenant_repo.get_by_id(tenant_id)
    if not tenant or not tenant.is_active:
        raise TenantNotFound()
    
    # Create policy
    policy = policy_repo.create_policy(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        description=description
    )
    
    # Log to audit trail
    audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=f"policy_created:{name}",
        metadata={"action": "create_policy", "policy_id": policy.id}
    )
    
    return PolicyDetail.from_model(policy)

@mcp_tool
def create_policy_version(
    tenant_id: int,
    policy_id: int,
    document: dict,  # Policy rules
) -> PolicyVersionDetail:
    """Create a new policy version."""
    # Validate ownership
    policy = policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != tenant_id:
        raise PolicyNotFound()
    
    # Validate document structure
    if not self._validate_policy_doc(document):
        raise ValueError("Invalid policy document")
    
    # Create version (immutable snapshot)
    version = policy_repo.create_version(
        policy_id=policy_id,
        document=document,
        is_active=False  # Must explicitly activate
    )
    
    # Log
    audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=f"version_created:{policy.slug}",
        metadata={"policy_id": policy_id, "version": version.version}
    )
    
    return PolicyVersionDetail.from_model(version)

@mcp_tool
def activate_policy_version(
    tenant_id: int,
    policy_id: int,
    version: int
) -> PolicyVersionDetail:
    """Activate a specific policy version."""
    policy = policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != tenant_id:
        raise PolicyNotFound()
    
    # Atomic activate (deactivates others)
    active = policy_repo.set_active_version(policy_id, version)
    
    # Log
    audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=f"version_activated:{policy.slug}:v{version}",
        metadata={"policy_id": policy_id, "version": version}
    )
    
    return PolicyVersionDetail.from_model(active)
```

---

## Part 6: Security Considerations for MCP CRUD

### Critical: Multi-Tenant Isolation

```python
# WRONG: MCP tool doesn't validate tenant
@mcp_tool
def create_policy(name: str, slug: str):
    # BUG: Agent could pass any tenant_id
    policy = policy_repo.create_policy(..., tenant_id=ATTACKER_TENANT)
    return policy

# RIGHT: Extract tenant from MCP context
@mcp_tool
def create_policy(name: str, slug: str, context: MCPContext):
    # Enforce: tenant_id comes from authenticated context, not input
    tenant_id = context.authenticated_tenant_id
    policy = policy_repo.create_policy(
        tenant_id=tenant_id,  # ← Enforced from context
        name=name,
        slug=slug
    )
    return policy
```

### Critical: Input Validation

```python
@mcp_tool
def create_policy_version(policy_id: int, document: dict, context: MCPContext):
    # Validate document structure BEFORE database write
    if not isinstance(document, dict):
        raise ValueError("document must be dict")
    
    if not all(k in document for k in ["blocked_terms", "risk_threshold"]):
        raise ValueError("document missing required fields")
    
    if not isinstance(document["blocked_terms"], list):
        raise ValueError("blocked_terms must be list")
    
    # Now safe to create
    version = policy_repo.create_version(...)
    return version
```

### Critical: Audit Logging

```python
@mcp_tool
def create_policy(..., context: MCPContext):
    policy = policy_repo.create_policy(...)
    
    # Always log who did what and when
    audit_repo.log_request(
        tenant_id=context.tenant_id,
        input_text=f"mcp_action:create_policy",
        metadata={
            "source": "mcp_server",
            "agent_id": context.agent_id,
            "policy_id": policy.id,
            "policy_name": policy.name,
            "timestamp_unix": int(time.time())
        }
    )
    
    return policy
```

---

## Part 7: MCP vs FastAPI: Decision Matrix

| Requirement | FastAPI | MCP | Best Choice |
|-------------|---------|-----|-------------|
| **Interactive UI** | ✅ Easy | ❌ No | FastAPI |
| **Agent automation** | ✅ Can do | ✅✅ Native | MCP |
| **Transaction safety** | ✅✅ Built-in | ⚠️ Manual | FastAPI |
| **Multi-tenancy** | ✅✅ Easy | ⚠️ Manual | FastAPI |
| **Rate limiting** | ✅✅ Middleware | ❌ No | FastAPI |
| **Audit trail** | ✅✅ Easy | ✅ Possible | FastAPI |
| **Error handling** | ✅✅ Structured | ⚠️ Basic | FastAPI |
| **Monitoring** | ✅✅ Introspection | ⚠️ Logging | FastAPI |
| **Claude agent calls** | ✅ Can do | ✅✅ Native | MCP |
| **External API calls** | ✅✅ Easy | ✅ Possible | FastAPI |

---

## Part 8: Recommended Hybrid Approach

### Architecture: Two Interfaces, One Backend

**Keep:**
- ✅ FastAPI backend (REST API for web, external apps, complex transactions)
- ✅ Existing database, services, repos

**Add:**
- ✅ MCP server for agent automation (thin wrapper around services)

### Layering:

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Server Interface                  │
│   (Agent-friendly tools, read-mostly with safe CRUD)    │
├─────────────────────────────────────────────────────────┤
│                FastAPI REST API Interface               │
│   (Traditional HTTP, UI, external integrations)         │
├─────────────────────────────────────────────────────────┤
│         Shared Services + Repos + Database              │
│   (Single source of truth, shared validation/logging)   │
└─────────────────────────────────────────────────────────┘
```

### What Goes Where:

| Tool/API | READS | WRITES | Purpose |
|----------|-------|--------|---------|
| **MCP Server** | ✅ get_policies, query_logs, analyze_text | ✅ ingest_evidence, create_policy, activate_version | Agents automating policy management |
| **FastAPI API** | ✅ All reads | ✅ All writes + complex ops | UI, external apps, advanced flows |
| **Both** | ✅ Same backend | ✅ Same backend | Consistent audit trail |

---

## Part 9: Implementation Plan for MCP Server

### Phase 1: Read-Only MCP (Low Risk)
```
Duration: 1-2 weeks
Risk: Low (no database mutations)

Tools to expose:
- get_policies()
- query_audit_logs()
- generate_compliance_report()
- analyze_text()  (read-only evaluation)

Benefits:
- Agents can query policies without UI
- Agents can analyze text against policies
- Agents can generate reports
- Zero risk to data integrity
```

### Phase 2: Safe CRUD Operations (Medium Risk)
```
Duration: 2-3 weeks
Risk: Medium (writes, but simple)

Tools to expose:
- ingest_evidence()        (append-only)
- create_policy()          (with validation)
- create_policy_version()  (with validation)
- activate_policy_version() (atomic)

Prerequisites:
- Strict input validation
- Tenant isolation enforcement
- Audit logging for all operations
- Unit tests for each tool
- Integration tests for multi-step workflows
```

### Phase 3: Complex CRUD (Future)
```
Duration: Later
Risk: Higher (transactions, rollbacks)

Tools to expose (conditionally):
- update_policy()
- delete_policy()
- policy_approval_workflows()

Prerequisites:
- Transaction management in MCP layer
- Approval/authorization workflows
- Comprehensive audit logging
- Error recovery mechanisms
```

---

## Part 10: Code Example: MCP Server Implementation

```python
# backend/mcp_server.py

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from app.services.policy_service import PolicyService
from app.services.audit_service import AuditService
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo

# MCP server instance
mcp = FastMCP("multimodel-policy-mgmt")

# Inject services (same as FastAPI)
policy_service = PolicyService(
    repo=SqlAlchemyPolicyRepo(db_session)
)
audit_service = AuditService(
    repo=SqlAlchemyAuditRepo(db_session)
)

# ================== READ OPERATIONS ==================

@mcp.tool()
def get_policies(tenant_id: int) -> list:
    """Fetch all active policies for a tenant."""
    policies = policy_service.list_policies(tenant_id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat()
        }
        for p in policies
    ]

@mcp.tool()
def query_audit_logs(
    tenant_id: int,
    start_date: str,
    end_date: str,
    risk_threshold: Optional[int] = None
) -> list:
    """Query decision logs for a tenant."""
    logs = audit_service.query_logs(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        risk_threshold=risk_threshold
    )
    return [
        {
            "id": log.id,
            "request_text": log.request_text,
            "decision": "blocked" if not log.allowed else "allowed",
            "risk_score": log.risk_score,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]

@mcp.tool()
def analyze_text(
    tenant_id: int,
    policy_id: int,
    text: str
) -> dict:
    """Analyze text against policy (read-only)."""
    policy = policy_service.get_policy(policy_id)
    if not policy or policy.tenant_id != tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Evaluate without logging
    result = policy_service.evaluate(text, policy)
    
    return {
        "allowed": result.allowed,
        "reason": result.reason,
        "risk_score": result.risk_score
    }

# ================== WRITE OPERATIONS ==================

@mcp.tool()
def ingest_evidence(
    tenant_id: int,
    evidence_type: str,
    source: str,
    content_text: str
) -> dict:
    """Ingest evidence for audit trail."""
    evidence = audit_service.ingest_evidence(
        tenant_id=tenant_id,
        evidence_type=evidence_type,
        source=source,
        content_text=content_text
    )
    return {
        "id": evidence.id,
        "type": evidence.type,
        "created_at": evidence.created_at.isoformat()
    }

@mcp.tool()
def create_policy(
    tenant_id: int,
    name: str,
    slug: str,
    description: Optional[str] = None
) -> dict:
    """Create a new policy."""
    # Validate tenant exists and is active
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant or not tenant.is_active:
        raise ValueError(f"Tenant {tenant_id} not found or inactive")
    
    # Create policy
    policy = policy_service.create_policy(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        description=description
    )
    
    # Audit log
    audit_service.log_action(
        tenant_id=tenant_id,
        action="create_policy",
        metadata={"policy_id": policy.id, "policy_name": name}
    )
    
    return {
        "id": policy.id,
        "name": policy.name,
        "slug": policy.slug,
        "created_at": policy.created_at.isoformat()
    }

@mcp.tool()
def create_policy_version(
    tenant_id: int,
    policy_id: int,
    document: dict
) -> dict:
    """Create a new policy version."""
    # Validate policy ownership
    policy = policy_service.get_policy(policy_id)
    if not policy or policy.tenant_id != tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Validate document
    if not policy_service.validate_document(document):
        raise ValueError("Invalid policy document")
    
    # Create version (immutable)
    version = policy_service.create_version(
        policy_id=policy_id,
        document=document,
        is_active=False
    )
    
    # Audit
    audit_service.log_action(
        tenant_id=tenant_id,
        action="create_policy_version",
        metadata={"policy_id": policy_id, "version": version.version}
    )
    
    return {
        "version": version.version,
        "policy_id": policy_id,
        "created_at": version.created_at.isoformat()
    }

# Run MCP server
if __name__ == "__main__":
    mcp.run(host="0.0.0.0", port=3001)
```

---

## Part 11: Summary & Recommendation

### Bottom Line:

**Yes, you should have an MCP server for CRUD—BUT:**

✅ **DO expose via MCP:**
- ✅ All READ operations (safe, no state changes)
- ✅ Simple CRUD writes (create_policy, ingest_evidence)
- ✅ Append-only operations (audit logs, evidence)
- ✅ Policy versioning (immutable snapshots)

❌ **DON'T expose via MCP:**
- ❌ Complex multi-step transactions
- ❌ Bulk operations requiring rollbacks
- ❌ Administrative operations (user management, tenant deletion)
- ❌ Operations requiring real-time consistency checks

⚠️ **Handle carefully:**
- ⚠️ Enforce multi-tenant isolation in MCP layer (not input validation)
- ⚠️ Log all MCP operations to audit trail
- ⚠️ Use same backend services for both FastAPI + MCP
- ⚠️ Add authentication/authorization at MCP level

### Architecture:

```
┌──────────────────────────────────────────┐
│   MCP Server (Agent Interface)           │
│   - Read operations: get_policies()      │
│   - Simple CRUD: create_policy()         │
│   - Evidence: ingest_evidence()          │
└────────────┬─────────────────────────────┘
             │ (same backend)
┌────────────▼─────────────────────────────┐
│   FastAPI (Web/UI/External API)          │
│   - All operations + complex flows       │
└────────────┬─────────────────────────────┘
             │ (delegates to)
┌────────────▼─────────────────────────────┐
│   Services (PolicyService, etc)          │
│   - Business logic, validation           │
└────────────┬─────────────────────────────┘
             │ (uses)
┌────────────▼─────────────────────────────┐
│   Repos (PolicyRepo, AuditRepo)          │
│   - Data access, transactions            │
└────────────┬─────────────────────────────┘
             │
┌────────────▼─────────────────────────────┐
│   Database                               │
│   - Single source of truth               │
└──────────────────────────────────────────┘
```

---

## Part 12: Next Steps

1. **Implement Phase 1: Read-Only MCP** (1-2 weeks)
   - Expose: `get_policies()`, `query_audit_logs()`, `analyze_text()`
   - No database mutations
   - Zero risk; high value for agents

2. **Add Basic CRUD to MCP** (2-3 weeks)
   - Expose: `create_policy()`, `create_version()`, `activate_version()`
   - Strict validation at MCP layer
   - Full audit logging

3. **Keep FastAPI as Primary** (ongoing)
   - REST API remains for UI, complex flows, external apps
   - Both MCP + FastAPI use same backend
   - Unified audit trail

4. **MCP Client Library** (for convenience)
   - `mcp_client = PolicyMgmtMCPClient(url="http://localhost:3001")`
   - Simplifies agent code: `client.get_policies(tenant_id=1)`


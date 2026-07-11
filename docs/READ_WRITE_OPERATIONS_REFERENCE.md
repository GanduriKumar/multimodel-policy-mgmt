# Read & Write Operations Reference

## Overview

The codebase uses a **Repository Pattern** with **Protocol-based contracts** to abstract all data access. This enables:
- ✅ Pluggable storage backends (SQLAlchemy → HTTP API → in-memory)
- ✅ Easy testing with fakes/mocks
- ✅ Clear separation between business logic (services) and data access (repos)
- ✅ Audit trail consistency for compliance

---

## Architecture: 4 Repository Types

```
┌─────────────────────────────────────────────────┐
│  API Routes (handlers)                          │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  Services (decision_service, governed_gen, etc) │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴────────────┬────────────┬─────────────┐
        │                      │            │             │
    ┌───▼────┐           ┌────▼───┐  ┌────▼───┐    ┌────▼────┐
    │ Policy │           │Evidence│  │ Tenant │    │  Audit  │
    │  Repo  │ (READ+    │  Repo  │  │  Repo  │    │  Repo   │
    │(CRUD)  │  WRITE)   │(WRITE) │  │(READ)  │    │(WRITE)  │
    └───┬────┘           └────┬───┘  └────┬───┘    └────┬────┘
        │                     │           │             │
    ┌───▼────────────────────────────────────────────────▼────┐
    │       SQLAlchemy ORM Layer (SQL ← → Python Objects)     │
    └───────────────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────────────────┐
    │       SQLite Database (or PostgreSQL in production)        │
    │  ┌──────┐ ┌────────┐ ┌─────────┐ ┌──────────┐             │
    │  │Policy│ │Evidence│ │RequestLog│ │DecisionLog│  ...      │
    │  └──────┘ └────────┘ └─────────┘ └──────────┘             │
    └────────────────────────────────────────────────────────────┘
```

---

## 1. POLICY REPOSITORY (`backend/app/repos/policy_repo.py`)

### Purpose
Manage policy definitions and policy versions (immutable snapshots).

### READ Operations

```python
# READ: Get policy by slug (most common)
policy = policy_repo.get_by_slug(tenant_id=1, slug="content-safety-v1")
# → Returns: Policy object or None

# READ: Get policy by ID
policy = policy_repo.get_policy_by_id(policy_id=42)
# → Returns: Policy object or None

# READ: List all policies for a tenant (paginated)
policies = policy_repo.list_policies(tenant_id=1, offset=0, limit=50)
# → Returns: List[Policy]

# READ: Get active version of a policy
active_version = policy_repo.get_active_version_for_slug(tenant_id=1, slug="content-safety-v1")
# → Returns: PolicyVersion object or None

# READ: List all versions of a policy
versions = policy_repo.list_versions(policy_id=42, offset=0, limit=20)
# → Returns: List[PolicyVersion]
```

### WRITE Operations

```python
# WRITE: Create new policy
policy = policy_repo.create_policy(
    tenant_id=1,
    name="Content Safety Policy",
    slug="content-safety-v1",
    description="Rules for content moderation",
    is_active=True
)
# → Returns: Policy object (stored in DB)

# WRITE: Update policy metadata
policy = policy_repo.update_policy(
    policy_id=42,
    name="Content Safety Policy v2",
    is_active=False,
    description="Updated rules"
)
# → Returns: Updated Policy object

# WRITE: Create a new policy version
version = policy_repo.create_version(
    policy_id=42,
    document={
        "blocked_terms": ["gun", "bomb"],
        "pii_rules": {"email": {"action": "detect"}},
        "risk_threshold": 75
    },
    is_active=True
)
# → Returns: PolicyVersion object (immutable snapshot)

# WRITE: Activate a specific version (deactivates others)
active = policy_repo.set_active_version(policy_id=42, version=3)
# → Returns: PolicyVersion object (now active)
```

---

## 2. AUDIT REPOSITORY (`backend/app/repos/audit_repo.py`)

### Purpose
Append-only audit trail: log every request and decision for compliance/debugging.

### READ Operations

```python
# READ: Get request log by ID
request_log = audit_repo.get_request(request_log_id=1001)
# → Returns: RequestLog { input_text, policy_id, tenant_id, created_at, ... }

# READ: List requests for a tenant (paginated, newest first)
requests = audit_repo.list_requests(tenant_id=1, offset=0, limit=50)
# → Returns: List[RequestLog]

# READ: Get decision for a request
decision = audit_repo.get_decision_for_request(request_log_id=1001)
# → Returns: DecisionLog { allowed: bool, reasons: list, risk_score, ... }

# READ: Get decision by ID
decision = audit_repo.get_decision_by_id(decision_id=5)
# → Returns: DecisionLog object

# READ: Get risk score for a request
risk = audit_repo.get_risk_for_request(request_log_id=1001)
# → Returns: RiskScore { score: 0-100, reasons: list, ... }
```

### WRITE Operations

```python
# WRITE: Log an incoming request
request_log = audit_repo.log_request(
    tenant_id=1,
    input_text="Is it safe to deploy this model?",
    policy_id=42,
    policy_version_id=3,
    input_hash="abc123...",  # SHA256 of text
    request_id="req-12345",  # Client-provided idempotency key
    user_agent="curl/7.68",
    client_ip="192.168.1.1",
    metadata={"source": "api", "session_id": "..."}
)
# → Returns: RequestLog object (stored in DB, auto-assigned ID)

# WRITE: Log a protection decision (after policy evaluation)
decision = audit_repo.log_decision(
    tenant_id=1,
    request_log_id=1001,
    allowed=False,
    reasons=["risk_above_threshold", "pii_detected"],
    policy_id=42,
    policy_version_id=3,
    risk_score=78
)
# → Returns: DecisionLog object (stored in DB)

# WRITE: Log a risk score calculation
risk = audit_repo.log_risk_score(
    tenant_id=1,
    request_log_id=1001,
    score=78,
    reasons=["weapon_mention", "hallucination_detected"],
    policy_id=42,
    evidence_present=True
)
# → Returns: RiskScore object (stored in DB)
```

---

## 3. EVIDENCE REPOSITORY (`backend/app/repos/evidence_repo.py`)

### Purpose
Store supporting evidence for policy decisions (logs, screenshots, test results, etc.).

### READ Operations

```python
# READ: Get evidence by ID
evidence = evidence_repo.get_by_id(evidence_id=501)
# → Returns: EvidenceItem { type, source, description, content_hash, ... }

# READ: Get evidence by content hash (deduplication)
evidence = evidence_repo.get_by_hash(tenant_id=1, content_hash="def456...")
# → Returns: EvidenceItem or None (avoid duplicate evidence)

# READ: Batch fetch evidence by IDs
evidence_list = evidence_repo.list_evidence_by_ids([501, 502, 503])
# → Returns: List[EvidenceItem]
```

### WRITE Operations

```python
# WRITE: Create/ingest evidence (hash computed internally)
evidence = evidence_repo.create_evidence(
    tenant_id=1,
    evidence_type="decision_log",  # e.g., "decision_log", "test_result", "audit_trail"
    source="automated_test_suite",
    description="CI/CD test run #1234",
    content_text="Test passed: model accuracy > 95%",  # Text to hash
    metadata={"test_id": "1234", "framework": "pytest"},
    policy_id=42,
    policy_version_id=3
)
# → Returns: EvidenceItem { content_hash computed, ... }

# WRITE: Create evidence with pre-computed hash (legacy)
evidence = evidence_repo.add_evidence(
    tenant_id=1,
    evidence_type="audit_log",
    source="manual_review",
    description="Human review approval",
    content_hash="ghi789...",  # You provide the hash
    metadata={"reviewer_id": "user-42"}
)
# → Returns: EvidenceItem object
```

---

## 4. TENANT REPOSITORY (`backend/app/repos/tenant_repo.py`)

### Purpose
Simple tenant (workspace/organization) management for multi-tenant isolation.

### READ Operations

```python
# READ: Get tenant by ID
tenant = tenant_repo.get_by_id(tenant_id=1)
# → Returns: Tenant { id, name, is_active, created_at, ... } or None
```

### WRITE Operations

```python
# WRITE: Create a tenant (workspace)
tenant = tenant_repo.create(name="ACME Corporation")
# → Returns: Tenant object { id, name, is_active: True, created_at, ... }
```

---

## Protocol Contracts (`backend/app/core/contracts.py`)

All repositories implement **Protocol interfaces** (structural typing). This means:
- ✅ Any implementation that satisfies the interface "quacks like" the repo
- ✅ Enables testing with `FakePolicy Repo`, `FakeAuditRepo` (no database)
- ✅ Allows swapping SQLAlchemy ↔ HTTP API ↔ in-memory store

### PolicyRepo Protocol
```python
@runtime_checkable
class PolicyRepo(Protocol):
    def get_by_slug(tenant_id, slug) -> Policy
    def list_policies(tenant_id) -> List[Policy]
    def create_policy(...) -> Policy
    def update_policy(...) -> Policy
    def create_version(...) -> PolicyVersion
    def set_active_version(policy_id, version) -> PolicyVersion
    # ... more methods
```

### AuditRepo Protocol
```python
@runtime_checkable
class AuditRepo(Protocol):
    def log_request(...) -> RequestLog
    def get_request(id) -> RequestLog
    def log_decision(...) -> DecisionLog
    def log_risk_score(...) -> RiskScore
    # ... more methods
```

---

## Data Flow Example: Protecting Text

```
1. API Route: POST /api/protect
   ↓
   request_text = "Can I use weapons in my game?"
   policy_slug = "content-safety-v1"
   
2. Service: decision_service.protect()
   ├─ READ: policy_repo.get_by_slug(tenant_id, policy_slug)
   │  → Policy document loaded
   │
   ├─ WRITE: audit_repo.log_request(request_text, policy_id, ...)
   │  → RequestLog created (ID: 1001)
   │
   ├─ EVALUATE: policy_engine.evaluate_policy(request_text, policy)
   │  → Violation found: "weapons" in blocked_terms
   │
   ├─ COMPUTE: risk_engine.compute_risk(request_text, policy)
   │  → Risk score: 72
   │
   ├─ DECIDE: is_blocked = (risk > threshold) OR (violations exist)
   │  → Decision: BLOCK
   │
   ├─ WRITE: audit_repo.log_decision(
   │     request_log_id=1001,
   │     allowed=False,
   │     risk_score=72,
   │     reasons=["weapon_mention", "risk_above_threshold"]
   │  )
   │  → DecisionLog created (ID: 5)
   │
   └─ RETURN: {"allowed": false, "decision_id": 5, "risk": 72}

3. Frontend/Client sees decision, requests full audit trail:
   ├─ READ: audit_repo.get_request(1001)
   │  → RequestLog { input_text, timestamp, policy_id, ... }
   │
   ├─ READ: audit_repo.get_decision_for_request(1001)
   │  → DecisionLog { allowed, reasons, risk_score, ... }
   │
   └─ READ: evidence_repo.list_evidence_by_ids([...])
      → Evidence items supporting the decision
```

---

## Transaction Safety

All WRITE operations use **SQLAlchemy transactions**:

```python
# Example from audit_repo.log_request()

try:
    self.session.add(req)
    self.session.commit()  # ← Atomic: all or nothing
    self.session.refresh(req)
    return req
except IntegrityError as e:
    self.session.rollback()  # ← Rollback on any error
    # Handle the error (e.g., duplicate request_id)
    raise
```

**Guarantees:**
- ✅ Atomicity: All fields committed together or rolled back
- ✅ Consistency: Referential integrity (policy_id must exist)
- ✅ Isolation: No dirty reads between concurrent requests
- ✅ Durability: Once committed, persisted to disk

---

## Input Validation Pattern

All repos validate inputs **before** database operations:

```python
# Example from policy_repo.create_policy()

def create_policy(self, tenant_id, name, slug, ...):
    # Validate types
    if not isinstance(tenant_id, int):
        raise TypeError("tenant_id must be an int")
    
    # Validate values
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    
    # Check uniqueness proactively
    name_exists = self.session.execute(...).scalar() is not None
    if name_exists:
        raise ValueError("name already exists for this tenant")
    
    # Now safe to create
    policy = Policy(...)
    self.session.add(policy)
    self.session.commit()
```

---

## Summary Table

| Repo | READ | WRITE | Purpose |
|------|------|-------|---------|
| **PolicyRepo** | get_by_slug, list_policies, get_active_version | create_policy, update_policy, create_version, set_active_version | Policy definitions & versions |
| **AuditRepo** | get_request, list_requests, get_decision, get_risk | log_request, log_decision, log_risk_score | Audit trail (compliance) |
| **EvidenceRepo** | get_by_id, get_by_hash, list_by_ids | create_evidence, add_evidence | Supporting evidence for decisions |
| **TenantRepo** | get_by_id | create | Workspace isolation |

---

## Key Characteristics

1. **Append-only audit** (AuditRepo) — Never delete/update logs
2. **Immutable versions** (PolicyRepo) — Versions are snapshots; create new ones instead
3. **Hash-based dedup** (EvidenceRepo) — Avoid duplicate evidence by content hash
4. **Transaction safety** — All writes atomic; rollback on error
5. **Type + value validation** — Check before database operations
6. **Protocol-based** — Enables testing with fakes, swappable implementations


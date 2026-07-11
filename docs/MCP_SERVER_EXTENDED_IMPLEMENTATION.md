# Extended MCP Server Implementation (26 Tools, 100% Coverage)

**Status:** Ready to Execute  
**Duration:** 5 weeks (200 hours)  
**Target:** Complete feature parity with REST API  
**Timeline:** Week 1-2 (Phase 1), Week 3 (Phase 2), Week 4 (Phase 3), Week 5 (Phase 4)

---

## Overview

This document extends the MCP server from **8 tools (35% coverage)** to **26 tools (100% coverage)**, providing agents with complete feature parity with the REST API.

### Tool Count by Phase

| Phase | Name | Tools | Focus | Timeline |
|-------|------|-------|-------|----------|
| 1 | Foundation | 4 tools | Read-only basics | Week 1-2 |
| 2 | CRUD Ops | 4 tools | Create/update/activate/ingest | Week 1-2 |
| 3 | Advanced Reads | 8 tools | Policy details, versions, evidence, decisions, traces | Week 3 |
| 4 | Complex Ops | 3 tools | Update, delete policies; delete evidence | Week 4 |
| 5 | Enterprise Reports | 6 tools | Compliance reports, timelines, decision reports | Week 5 |
| **TOTAL** | **26 Tools** | **100% Coverage** | **All endpoints** | **5 weeks** |

---

## Phase 1 & 2: Foundation + CRUD (Weeks 1-2)

**Status:** Already designed in MCP_SERVER_IMPLEMENTATION.md

8 tools:
- `get_policies()` — List active policies
- `query_audit_logs()` — List audit events
- `analyze_text()` — Evaluate text against policy
- `generate_compliance_report()` — Generic compliance report
- `create_policy()` — Create new policy
- `create_policy_version()` — Add policy version
- `activate_policy_version()` — Activate specific version
- `ingest_evidence()` — Add evidence

**No changes needed.** Proceed with existing implementation.

---

## Phase 3: Advanced Reads (Week 3)

### Tool 9: `get_policy(policy_id: int) -> dict`

**Replaces:** `GET /api/policies/{id}`

```python
def get_policy(self, tenant_id: int, policy_id: int, context: MCPContext) -> dict:
    """
    Fetch single policy details.
    
    Args:
        tenant_id: Tenant ID
        policy_id: Policy ID
        context: MCPContext (enforces tenant isolation)
    
    Returns:
        {
            id: int,
            tenant_id: int,
            name: str,
            slug: str,
            description: str,
            is_active: bool,
            created_at: str,
            updated_at: str,
            versions_count: int
        }
    
    Raises:
        ValueError: Policy not found or tenant mismatch
    """
    # Enforce tenant isolation from context, not input
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Repository call
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Log read (optional, for governance)
    self.audit_repo.log_request(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        action="read_policy",
        resource_id=policy_id,
        status="success"
    )
    
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "slug": policy.slug,
        "description": policy.description,
        "is_active": policy.is_active,
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat(),
        "versions_count": len(policy.versions)
    }
```

---

### Tool 10: `list_policy_versions(policy_id: int, limit: int = 50) -> List[dict]`

**Replaces:** `GET /api/policies/{id}/versions`

```python
def list_policy_versions(
    self,
    tenant_id: int,
    policy_id: int,
    limit: int = 50,
    context: MCPContext = None
) -> List[dict]:
    """
    Fetch version history for a policy.
    
    Args:
        tenant_id: Tenant ID
        policy_id: Policy ID
        limit: Max versions (1-100)
        context: MCPContext
    
    Returns:
        [
            {
                version: int,
                policy_id: int,
                is_active: bool,
                document: dict,
                created_at: str,
                activated_at: Optional[str],
                created_by: str
            },
            ...
        ]
    """
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be 1-100")
    
    # Tenant isolation
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Verify policy exists and belongs to tenant
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Get versions (assumed OrderedDict or list, newest first)
    versions = policy.versions[:limit]
    
    return [
        {
            "version": v.version,
            "policy_id": v.policy_id,
            "is_active": v.is_active,
            "document": v.document,  # JSON dict
            "created_at": v.created_at.isoformat(),
            "activated_at": v.activated_at.isoformat() if v.activated_at else None,
            "created_by": v.created_by
        }
        for v in versions
    ]
```

---

### Tool 11: `get_active_policy_version(policy_id: int) -> dict`

**Replaces:** `GET /api/policies/{id}/versions/active`

```python
def get_active_policy_version(
    self,
    tenant_id: int,
    policy_id: int,
    context: MCPContext = None
) -> dict:
    """
    Fetch currently active version of a policy.
    
    Returns:
        {
            version: int,
            policy_id: int,
            is_active: bool,
            document: dict,
            created_at: str,
            activated_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Find active version
    active = next((v for v in policy.versions if v.is_active), None)
    if not active:
        raise ValueError(f"No active version for policy {policy_id}")
    
    return {
        "version": active.version,
        "policy_id": active.policy_id,
        "is_active": active.is_active,
        "document": active.document,
        "created_at": active.created_at.isoformat(),
        "activated_at": active.activated_at.isoformat()
    }
```

---

### Tool 12: `get_evidence(evidence_id: int) -> dict`

**Replaces:** `GET /api/evidence/{id}`

```python
def get_evidence(
    self,
    tenant_id: int,
    evidence_id: int,
    context: MCPContext = None
) -> dict:
    """
    Fetch single evidence item details.
    
    Returns:
        {
            id: int,
            tenant_id: int,
            type: str,  # "pii_sample", "decision_log", "generated_text", etc.
            source: str,
            content_text: str,
            content_hash: str,
            metadata: dict,
            created_at: str,
            used_in_decisions: int
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    evidence = self.evidence_repo.get_by_id(evidence_id)
    if not evidence or evidence.tenant_id != context.tenant_id:
        raise ValueError(f"Evidence {evidence_id} not found")
    
    # Log read
    self.audit_repo.log_request(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        action="read_evidence",
        resource_id=evidence_id,
        status="success"
    )
    
    return {
        "id": evidence.id,
        "tenant_id": evidence.tenant_id,
        "type": evidence.type,
        "source": evidence.source,
        "content_text": evidence.content_text,
        "content_hash": evidence.content_hash,
        "metadata": evidence.metadata or {},
        "created_at": evidence.created_at.isoformat(),
        "used_in_decisions": len(evidence.decisions) if hasattr(evidence, 'decisions') else 0
    }
```

---

### Tool 13: `get_decision_detail(decision_id: int) -> dict`

**Replaces:** `GET /api/audit/decisions/{id}`

```python
def get_decision_detail(
    self,
    tenant_id: int,
    decision_id: int,
    context: MCPContext = None
) -> dict:
    """
    Fetch full decision with reasons, evidence used, and ledger trace.
    
    Returns:
        {
            id: int,
            request_id: str,
            allowed: bool,
            risk_score: int,
            risk_level: str,  # "low", "medium", "high", "critical"
            pii_violations: [...],
            matching_rules: [...],
            evidence_used: [...],
            decision_reasons: [str],
            trace_id: str,
            created_at: str,
            agent_id: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    decision = self.audit_repo.get_decision_by_id(decision_id)
    if not decision or decision.tenant_id != context.tenant_id:
        raise ValueError(f"Decision {decision_id} not found")
    
    return {
        "id": decision.id,
        "request_id": decision.request_id,
        "allowed": decision.allowed,
        "risk_score": decision.risk_score,
        "risk_level": decision.risk_level,
        "pii_violations": decision.pii_violations or [],
        "matching_rules": decision.matching_rules or [],
        "evidence_used": [
            {
                "evidence_id": e.id,
                "type": e.type,
                "source": e.source
            }
            for e in decision.evidence
        ] if hasattr(decision, 'evidence') else [],
        "decision_reasons": decision.reasons or [],
        "trace_id": decision.trace_id,
        "created_at": decision.created_at.isoformat(),
        "agent_id": decision.agent_id
    }
```

---

### Tool 14: `list_policy_changes(start_date: str, end_date: str) -> List[dict]`

**Replaces:** `GET /api/reports/policy-changes`

```python
def list_policy_changes(
    self,
    tenant_id: int,
    start_date: str,  # ISO 8601: "2025-01-01T00:00:00Z"
    end_date: str,
    context: MCPContext = None
) -> List[dict]:
    """
    Fetch timeline of all policy changes (create, update, version activation).
    
    Returns:
        [
            {
                id: int,
                policy_id: int,
                policy_name: str,
                change_type: str,  # "created", "updated", "version_activated", "deleted"
                change_details: dict,
                changed_by: str,
                created_at: str
            },
            ...
        ]
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Parse dates
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format. Use ISO 8601: 2025-01-01T00:00:00Z")
    
    # Get change log from audit (assuming audit_repo has this)
    changes = self.audit_repo.list_policy_changes(
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    return [
        {
            "id": c.id,
            "policy_id": c.policy_id,
            "policy_name": c.policy_name,
            "change_type": c.change_type,
            "change_details": c.change_details or {},
            "changed_by": c.changed_by,
            "created_at": c.created_at.isoformat()
        }
        for c in changes
    ]
```

---

### Tool 15: `list_decision_events(start_date: str, end_date: str, risk_threshold: int = 0) -> List[dict]`

**Replaces:** `GET /api/reports/decisions`

```python
def list_decision_events(
    self,
    tenant_id: int,
    start_date: str,
    end_date: str,
    risk_threshold: int = 0,
    context: MCPContext = None
) -> List[dict]:
    """
    Fetch timeline of decision events with optional risk filtering.
    
    Returns:
        [
            {
                id: int,
                request_id: str,
                policy_id: int,
                allowed: bool,
                risk_score: int,
                risk_level: str,
                agent_id: str,
                created_at: str
            },
            ...
        ]
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    if not (0 <= risk_threshold <= 100):
        raise ValueError("risk_threshold must be 0-100")
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    events = self.audit_repo.list_decision_events(
        tenant_id=tenant_id,
        start_date=start,
        end_date=end,
        min_risk_score=risk_threshold
    )
    
    return [
        {
            "id": e.id,
            "request_id": e.request_id,
            "policy_id": e.policy_id,
            "allowed": e.allowed,
            "risk_score": e.risk_score,
            "risk_level": e.risk_level,
            "agent_id": e.agent_id,
            "created_at": e.created_at.isoformat()
        }
        for e in events
    ]
```

---

### Tool 16: `get_trace(trace_id: str) -> dict`

**Replaces:** `GET /api/traces/{trace_id}`

```python
def get_trace(
    self,
    tenant_id: int,
    trace_id: str,
    context: MCPContext = None
) -> dict:
    """
    Fetch full governance ledger for a request trace.
    Includes all decision checkpoints, evidence used, and audit chain.
    
    Returns:
        {
            trace_id: str,
            request_id: str,
            policy_id: int,
            agent_id: str,
            status: str,  # "processing", "allowed", "blocked", "error"
            
            checkpoints: [
                {
                    step: int,
                    name: str,
                    status: str,
                    timestamp: str,
                    details: dict
                },
                ...
            ],
            
            decision: {
                allowed: bool,
                risk_score: int,
                reasons: [str]
            },
            
            ledger_entries: [
                {
                    sequence: int,
                    action: str,
                    timestamp: str,
                    hash: str,
                    previous_hash: str
                },
                ...
            ],
            
            total_duration_ms: int,
            created_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Assuming audit_repo has trace lookup
    trace = self.audit_repo.get_trace(trace_id)
    if not trace or trace.tenant_id != context.tenant_id:
        raise ValueError(f"Trace {trace_id} not found")
    
    return {
        "trace_id": trace.trace_id,
        "request_id": trace.request_id,
        "policy_id": trace.policy_id,
        "agent_id": trace.agent_id,
        "status": trace.status,
        
        "checkpoints": [
            {
                "step": cp.step,
                "name": cp.name,
                "status": cp.status,
                "timestamp": cp.timestamp.isoformat(),
                "details": cp.details or {}
            }
            for cp in trace.checkpoints
        ],
        
        "decision": {
            "allowed": trace.decision.allowed,
            "risk_score": trace.decision.risk_score,
            "reasons": trace.decision.reasons or []
        },
        
        "ledger_entries": [
            {
                "sequence": e.sequence,
                "action": e.action,
                "timestamp": e.timestamp.isoformat(),
                "hash": e.hash,
                "previous_hash": e.previous_hash
            }
            for e in trace.ledger_entries
        ],
        
        "total_duration_ms": trace.total_duration_ms,
        "created_at": trace.created_at.isoformat()
    }
```

---

## Phase 4: Complex Write Operations (Week 4)

### Tool 17: `update_policy(policy_id: int, name: str, slug: str, description: str) -> dict`

**Replaces:** `POST /api/policies/{id}/update`

```python
def update_policy(
    self,
    tenant_id: int,
    policy_id: int,
    name: str,
    slug: str,
    description: str,
    context: MCPContext = None
) -> dict:
    """
    Update policy metadata.
    
    Args:
        tenant_id: Tenant ID
        policy_id: Policy ID
        name: New name
        slug: New slug (must be unique per tenant)
        description: New description
        context: MCPContext
    
    Returns:
        {
            id: int,
            name: str,
            slug: str,
            description: str,
            updated_at: str
        }
    
    Raises:
        ValueError: Invalid input, policy not found, or slug conflict
    """
    # Validation
    if not name or not name.strip():
        raise ValueError("name required")
    if not slug or not slug.strip():
        raise ValueError("slug required")
    if len(name) > 255:
        raise ValueError("name max 255 chars")
    if len(slug) > 100:
        raise ValueError("slug max 100 chars")
    
    # Tenant isolation
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Verify policy exists
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Check slug uniqueness (excluding self)
    existing = self.policy_repo.get_by_slug(slug)
    if existing and existing.id != policy_id:
        raise ValueError(f"Slug '{slug}' already in use")
    
    # Update
    policy.name = name.strip()
    policy.slug = slug.strip()
    policy.description = description.strip() if description else ""
    self.policy_repo.commit()
    
    # Audit log
    self.audit_repo.log_request(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        action="update_policy",
        resource_id=policy_id,
        status="success",
        details={
            "name": name,
            "slug": slug
        }
    )
    
    return {
        "id": policy.id,
        "name": policy.name,
        "slug": policy.slug,
        "description": policy.description,
        "updated_at": policy.updated_at.isoformat()
    }
```

---

### Tool 18: `delete_policy(policy_id: int) -> dict`

**Replaces:** `POST /api/policies/{id}/delete`

```python
def delete_policy(
    self,
    tenant_id: int,
    policy_id: int,
    context: MCPContext = None
) -> dict:
    """
    Soft-delete a policy. Sets is_active=False and preserves history.
    
    Returns:
        {
            id: int,
            name: str,
            status: "deleted",
            deleted_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    if not policy.is_active:
        raise ValueError(f"Policy {policy_id} already deleted")
    
    # Soft delete
    policy.is_active = False
    policy.deleted_at = datetime.utcnow()
    self.policy_repo.commit()
    
    # Audit
    self.audit_repo.log_request(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        action="delete_policy",
        resource_id=policy_id,
        status="success"
    )
    
    return {
        "id": policy.id,
        "name": policy.name,
        "status": "deleted",
        "deleted_at": policy.deleted_at.isoformat()
    }
```

---

### Tool 19: `delete_evidence(evidence_id: int) -> dict`

**Replaces:** `DELETE /api/evidence`

```python
def delete_evidence(
    self,
    tenant_id: int,
    evidence_id: int,
    context: MCPContext = None
) -> dict:
    """
    Delete evidence item (hard delete).
    
    Returns:
        {
            id: int,
            status: "deleted",
            deleted_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    evidence = self.evidence_repo.get_by_id(evidence_id)
    if not evidence or evidence.tenant_id != context.tenant_id:
        raise ValueError(f"Evidence {evidence_id} not found")
    
    # Check if used in active decisions (optional safeguard)
    if hasattr(evidence, 'decisions') and evidence.decisions:
        raise ValueError(
            f"Cannot delete: evidence is referenced by {len(evidence.decisions)} decisions"
        )
    
    # Delete
    self.evidence_repo.delete(evidence_id)
    
    # Audit
    self.audit_repo.log_request(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        action="delete_evidence",
        resource_id=evidence_id,
        status="success"
    )
    
    return {
        "id": evidence_id,
        "status": "deleted",
        "deleted_at": datetime.utcnow().isoformat()
    }
```

---

## Phase 5: Enterprise Reports (Week 5)

### Tool 20: `protect_and_generate(text: str, policy_id: int, llm_config: dict, rag_context: dict) -> dict`

**Replaces:** `POST /api/protect-generate`

```python
def protect_and_generate(
    self,
    tenant_id: int,
    text: str,
    policy_id: int,
    llm_config: dict,
    rag_context: dict = None,
    context: MCPContext = None
) -> dict:
    """
    Full LLM generation pipeline with policy enforcement, RAG, and safety checks.
    
    Args:
        tenant_id: Tenant ID
        text: Input text / prompt
        policy_id: Policy ID to enforce
        llm_config: {
            model: str,  # "gpt-4", "claude-3", etc.
            temperature: float,
            max_tokens: int
        }
        rag_context: {
            query: str,
            documents: [str],
            system_instructions: str
        }
    
    Returns:
        {
            allowed: bool,
            generated_text: str,
            pre_check: {
                allowed: bool,
                risk_score: int,
                violations: [str]
            },
            safety_check: {
                is_safe: bool,
                flags: [str]
            },
            groundedness_check: {
                is_grounded: bool,
                score: float,
                citation_coverage: float
            },
            request_id: str,
            trace_id: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    if not text or not text.strip():
        raise ValueError("text required")
    if not isinstance(policy_id, int) or policy_id <= 0:
        raise ValueError("policy_id must be positive int")
    
    # Load policy
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Pre-generation check
    pre_check = self.decision_service.protect(
        text=text,
        policy=policy,
        agent_id=context.agent_id
    )
    
    if not pre_check['allowed']:
        return {
            "allowed": False,
            "generated_text": None,
            "pre_check": pre_check,
            "safety_check": None,
            "groundedness_check": None,
            "request_id": context.request_id,
            "trace_id": context.request_id  # Same for now
        }
    
    # Generate with LLM
    llm_response = self.generation_service.generate(
        prompt=text,
        policy_id=policy_id,
        llm_config=llm_config,
        rag_context=rag_context,
        agent_id=context.agent_id
    )
    
    # Safety evaluation
    safety = self.safety_service.evaluate(
        text=llm_response['generated_text'],
        policy=policy
    )
    
    # Groundedness evaluation
    groundedness = self.groundedness_service.evaluate(
        generated_text=llm_response['generated_text'],
        rag_documents=rag_context.get('documents', []) if rag_context else []
    )
    
    # Log decision
    self.audit_repo.log_generation(
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        policy_id=policy_id,
        input_text=text[:500],
        output_text=llm_response['generated_text'][:500],
        safety_passed=safety['is_safe'],
        groundedness_passed=groundedness['is_grounded'],
        request_id=context.request_id
    )
    
    return {
        "allowed": safety['is_safe'] and groundedness['is_grounded'],
        "generated_text": llm_response['generated_text'],
        "pre_check": pre_check,
        "safety_check": safety,
        "groundedness_check": groundedness,
        "request_id": context.request_id,
        "trace_id": context.request_id
    }
```

---

### Tool 21: `eu_ai_act_compliance_report(policy_id: int, start_date: str, end_date: str) -> dict`

**Replaces:** `GET /api/reports/compliance/eu-ai-act/{id}`

```python
def eu_ai_act_compliance_report(
    self,
    tenant_id: int,
    policy_id: int,
    start_date: str,
    end_date: str,
    context: MCPContext = None
) -> dict:
    """
    Generate EU AI Act compliance report for a specific policy.
    
    Returns:
        {
            policy_id: int,
            framework: "eu_ai_act",
            report_period: {start_date, end_date},
            
            summary: {
                total_decisions: int,
                allowed: int,
                blocked: int,
                avg_risk_score: float,
                compliance_score: float  # 0-100
            },
            
            controls_assessment: {
                transparency: {score, status, gaps},
                human_oversight: {score, status, gaps},
                data_governance: {score, status, gaps},
                risk_management: {score, status, gaps}
            },
            
            gaps: [{
                control: str,
                severity: str,
                recommendation: str
            }],
            
            evidence_summary: {
                pii_incidents: int,
                decisions_with_evidence: int,
                decision_traceability: float
            },
            
            generated_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    # Validate policy
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    # Parse dates
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    # Generate report (delegated to compliance_service)
    report = self.compliance_service.generate_eu_ai_act_report(
        policy_id=policy_id,
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    return report
```

---

### Tool 22: `nist_ai_rmf_compliance_report(policy_id: int, start_date: str, end_date: str) -> dict`

**Replaces:** `GET /api/reports/compliance/nist-ai-rmf/{id}`

```python
def nist_ai_rmf_compliance_report(
    self,
    tenant_id: int,
    policy_id: int,
    start_date: str,
    end_date: str,
    context: MCPContext = None
) -> dict:
    """
    Generate NIST AI RMF compliance report for a specific policy.
    
    Returns similar structure to EU AI Act but with NIST RMF controls:
    - Govern (policies, procedures)
    - Map (risk categorization)
    - Measure (metrics, monitoring)
    - Manage (mitigation, documentation)
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    report = self.compliance_service.generate_nist_ai_rmf_report(
        policy_id=policy_id,
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    return report
```

---

### Tool 23: `nist_privacy_compliance_report(policy_id: int, start_date: str, end_date: str) -> dict`

**Replaces:** `GET /api/reports/compliance/nist-privacy/{id}`

```python
def nist_privacy_compliance_report(
    self,
    tenant_id: int,
    policy_id: int,
    start_date: str,
    end_date: str,
    context: MCPContext = None
) -> dict:
    """
    Generate NIST Privacy Framework compliance report for a specific policy.
    
    Returns:
        {
            policy_id: int,
            framework: "nist_privacy",
            report_period: {start_date, end_date},
            
            summary: {
                data_processing_decisions: int,
                pii_handling_compliance: float,
                consent_recorded: int,
                breach_incidents: int
            },
            
            core_functions: {
                govern: {score, status},
                identify: {score, status},
                protect: {score, status},
                detect: {score, status},
                respond: {score, status}
            },
            
            recommendations: [str],
            generated_at: str
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    policy = self.policy_repo.get_by_id(policy_id)
    if not policy or policy.tenant_id != context.tenant_id:
        raise ValueError(f"Policy {policy_id} not found")
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    report = self.compliance_service.generate_nist_privacy_report(
        policy_id=policy_id,
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    return report
```

---

### Tool 24: `policy_changes_report(start_date: str, end_date: str, format: str = "json") -> dict | str`

**Replaces:** `GET /api/reports/policy-changes`

```python
def policy_changes_report(
    self,
    tenant_id: int,
    start_date: str,
    end_date: str,
    format: str = "json",
    context: MCPContext = None
) -> dict | str:
    """
    Generate policy change report in JSON, CSV, or HTML format.
    
    Args:
        format: "json" (dict), "csv" (string), "html" (string)
    
    Returns:
        JSON: {
            report_period: {start_date, end_date},
            total_changes: int,
            changes: [
                {
                    timestamp: str,
                    policy: str,
                    change_type: str,
                    changed_by: str,
                    details: dict
                }
            ]
        }
        
        CSV: CSV string with headers: timestamp,policy,change_type,changed_by,details
        HTML: Rendered HTML table with styling
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    if format not in ("json", "csv", "html"):
        raise ValueError("format must be 'json', 'csv', or 'html'")
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    # Get data
    changes = self.audit_repo.list_policy_changes(
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    # Format
    if format == "json":
        return {
            "report_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_changes": len(changes),
            "changes": [
                {
                    "timestamp": c.created_at.isoformat(),
                    "policy": c.policy_name,
                    "change_type": c.change_type,
                    "changed_by": c.changed_by,
                    "details": c.change_details or {}
                }
                for c in changes
            ]
        }
    
    elif format == "csv":
        return self.report_service.render_csv(
            rows=[
                {
                    "timestamp": c.created_at.isoformat(),
                    "policy": c.policy_name,
                    "change_type": c.change_type,
                    "changed_by": c.changed_by,
                    "details": json.dumps(c.change_details or {})
                }
                for c in changes
            ],
            headers=["timestamp", "policy", "change_type", "changed_by", "details"]
        )
    
    else:  # html
        return self.report_service.render_html(
            title="Policy Changes Report",
            rows=changes,
            columns=["timestamp", "policy", "change_type", "changed_by"]
        )
```

---

### Tool 25: `decisions_report(start_date: str, end_date: str, format: str = "json") -> dict | str`

**Replaces:** `GET /api/reports/decisions`

```python
def decisions_report(
    self,
    tenant_id: int,
    start_date: str,
    end_date: str,
    format: str = "json",
    context: MCPContext = None
) -> dict | str:
    """
    Generate decision report with aggregated statistics.
    
    Returns (JSON format):
        {
            report_period: {start_date, end_date},
            summary: {
                total_decisions: int,
                allowed_count: int,
                blocked_count: int,
                allowed_percentage: float,
                avg_risk_score: float
            },
            risk_distribution: {
                low: int,
                medium: int,
                high: int,
                critical: int
            },
            top_violation_types: [
                {type, count, percentage}
            ],
            decision_timeline: [
                {date, count, allowed_count}
            ]
        }
    """
    if tenant_id != context.tenant_id:
        raise ValueError("Tenant mismatch")
    
    if format not in ("json", "csv", "html"):
        raise ValueError("format must be 'json', 'csv', or 'html'")
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid date format")
    
    # Get decisions
    decisions = self.audit_repo.list_decision_events(
        tenant_id=tenant_id,
        start_date=start,
        end_date=end
    )
    
    if format == "json":
        allowed = sum(1 for d in decisions if d.allowed)
        blocked = len(decisions) - allowed
        
        return {
            "report_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_decisions": len(decisions),
                "allowed_count": allowed,
                "blocked_count": blocked,
                "allowed_percentage": (allowed / len(decisions) * 100) if decisions else 0,
                "avg_risk_score": sum(d.risk_score for d in decisions) / len(decisions) if decisions else 0
            },
            "risk_distribution": {
                "low": sum(1 for d in decisions if d.risk_level == "low"),
                "medium": sum(1 for d in decisions if d.risk_level == "medium"),
                "high": sum(1 for d in decisions if d.risk_level == "high"),
                "critical": sum(1 for d in decisions if d.risk_level == "critical")
            },
            "decision_timeline": self._aggregate_timeline(decisions)
        }
    
    elif format == "csv":
        return self.report_service.render_csv(
            rows=[
                {
                    "timestamp": d.created_at.isoformat(),
                    "allowed": "yes" if d.allowed else "no",
                    "risk_score": d.risk_score,
                    "risk_level": d.risk_level,
                    "policy_id": d.policy_id
                }
                for d in decisions
            ]
        )
    
    else:  # html
        return self.report_service.render_html(
            title="Decisions Report",
            rows=decisions
        )
```

---

### Tool 26: `maintenance_reset_all() -> dict` (ADMIN ONLY)

**Replaces:** `POST /api/maintenance/reset-all`

**Note:** This tool is intentionally designed for admin-only use and should NOT be exposed through standard agent calls. Include it for completeness but guard with strict permission checks.

```python
def maintenance_reset_all(
    self,
    tenant_id: int,
    confirm: str = "",
    context: MCPContext = None
) -> dict:
    """
    ADMIN ONLY: Reset all data for a tenant.
    
    Args:
        confirm: Must equal "RESET_CONFIRMED" to prevent accidents
    
    Returns:
        {status: "reset_complete", timestamp: str}
    """
    # Admin-only check
    if context.agent_id != "ADMIN_AGENT":
        raise PermissionError("Not authorized")
    
    if confirm != "RESET_CONFIRMED":
        raise ValueError("Confirmation code incorrect")
    
    # Reset all tables for tenant
    self.policy_repo.delete_all_for_tenant(tenant_id)
    self.audit_repo.delete_all_for_tenant(tenant_id)
    self.evidence_repo.delete_all_for_tenant(tenant_id)
    
    return {
        "status": "reset_complete",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Extended Server Module

**File:** `backend/mcp/server.py` (Updated)

```python
"""
Extended MCP Server with all 26 tools.
"""

from fastmcp import FastMCP
from mcp.tools import ReadOnlyTools, CRUDTools, AdvancedReadTools, WriteTools, ReportTools
from mcp.context import extract_context

# Initialize server
mcp = FastMCP(
    name="PolicyMgmt MCP Server",
    version="1.0.0"
)

# Service singletons
_services = None

def get_services():
    """Lazy-load services."""
    global _services
    if _services is None:
        from app.services import policy_service, audit_service, decision_service
        from app.services import compliance_service, generation_service, safety_service
        from app.repos import policy_repo, audit_repo, evidence_repo
        
        _services = {
            'policy_service': policy_service,
            'audit_service': audit_service,
            'decision_service': decision_service,
            'compliance_service': compliance_service,
            'generation_service': generation_service,
            'safety_service': safety_service,
            'policy_repo': policy_repo,
            'audit_repo': audit_repo,
            'evidence_repo': evidence_repo
        }
    return _services

# Phase 1 & 2: Basic tools
@mcp.tool()
def get_policies(tenant_id: int, limit: int = 50, offset: int = 0):
    """List active policies."""
    services = get_services()
    tools = ReadOnlyTools(**services)
    return tools.get_policies(tenant_id, limit, offset)

# ... (other 7 Phase 1/2 tools as in MCP_SERVER_IMPLEMENTATION.md)

# Phase 3: Advanced reads
@mcp.tool()
def get_policy(tenant_id: int, policy_id: int):
    """Fetch single policy details."""
    services = get_services()
    tools = AdvancedReadTools(**services)
    return tools.get_policy(tenant_id, policy_id)

# ... (other Phase 3 tools: list_policy_versions, get_active_policy_version, etc.)

# Phase 4: Complex writes
@mcp.tool()
def update_policy(tenant_id: int, policy_id: int, name: str, slug: str, description: str):
    """Update policy metadata."""
    services = get_services()
    tools = WriteTools(**services)
    return tools.update_policy(tenant_id, policy_id, name, slug, description)

# ... (other Phase 4 tools: delete_policy, delete_evidence)

# Phase 5: Reports
@mcp.tool()
def protect_and_generate(tenant_id: int, text: str, policy_id: int, llm_config: dict, rag_context: dict = None):
    """Full LLM generation with policy enforcement."""
    services = get_services()
    tools = ReportTools(**services)
    return tools.protect_and_generate(tenant_id, text, policy_id, llm_config, rag_context)

# ... (other Phase 5 tools: eu_ai_act_compliance_report, decisions_report, etc.)

if __name__ == "__main__":
    mcp.run(host="0.0.0.0", port=3001)
```

---

## Extended Client Library

**File:** `backend/client/client.py` (Updated)

```python
"""
MCP Client with all 26 tools.
"""

import httpx
from typing import Optional, List
from contextlib import contextmanager

class PolicyMgmtMCPClient:
    """Complete MCP client for agent developers."""
    
    def __init__(self, url: str, tenant_id: int, agent_id: str, api_key: str, timeout: int = 30):
        self.url = url
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "X-Tenant-ID": str(tenant_id),
            "X-Agent-ID": agent_id,
            "Authorization": f"Bearer {api_key}"
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    # ===== PHASE 1 & 2 (Existing) =====
    
    def get_policies(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """List active policies."""
        return self._call("get_policies", {"tenant_id": self.tenant_id, "limit": limit, "offset": offset})
    
    # ... (other existing 7 tools)
    
    # ===== PHASE 3 (New) =====
    
    def get_policy(self, policy_id: int) -> dict:
        """Fetch single policy."""
        return self._call("get_policy", {"tenant_id": self.tenant_id, "policy_id": policy_id})
    
    def list_policy_versions(self, policy_id: int, limit: int = 50) -> List[dict]:
        """List policy versions."""
        return self._call("list_policy_versions", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id,
            "limit": limit
        })
    
    def get_active_policy_version(self, policy_id: int) -> dict:
        """Get active version."""
        return self._call("get_active_policy_version", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id
        })
    
    def get_evidence(self, evidence_id: int) -> dict:
        """Fetch evidence."""
        return self._call("get_evidence", {
            "tenant_id": self.tenant_id,
            "evidence_id": evidence_id
        })
    
    def get_decision_detail(self, decision_id: int) -> dict:
        """Fetch decision with full details."""
        return self._call("get_decision_detail", {
            "tenant_id": self.tenant_id,
            "decision_id": decision_id
        })
    
    def list_policy_changes(self, start_date: str, end_date: str) -> List[dict]:
        """List policy changes."""
        return self._call("list_policy_changes", {
            "tenant_id": self.tenant_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def list_decision_events(self, start_date: str, end_date: str, risk_threshold: int = 0) -> List[dict]:
        """List decision events."""
        return self._call("list_decision_events", {
            "tenant_id": self.tenant_id,
            "start_date": start_date,
            "end_date": end_date,
            "risk_threshold": risk_threshold
        })
    
    def get_trace(self, trace_id: str) -> dict:
        """Fetch trace with full ledger."""
        return self._call("get_trace", {
            "tenant_id": self.tenant_id,
            "trace_id": trace_id
        })
    
    # ===== PHASE 4 (New) =====
    
    def update_policy(self, policy_id: int, name: str, slug: str, description: str) -> dict:
        """Update policy."""
        return self._call("update_policy", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id,
            "name": name,
            "slug": slug,
            "description": description
        })
    
    def delete_policy(self, policy_id: int) -> dict:
        """Delete policy."""
        return self._call("delete_policy", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id
        })
    
    def delete_evidence(self, evidence_id: int) -> dict:
        """Delete evidence."""
        return self._call("delete_evidence", {
            "tenant_id": self.tenant_id,
            "evidence_id": evidence_id
        })
    
    # ===== PHASE 5 (New) =====
    
    def protect_and_generate(self, text: str, policy_id: int, llm_config: dict, rag_context: dict = None) -> dict:
        """Full generation with protection."""
        return self._call("protect_and_generate", {
            "tenant_id": self.tenant_id,
            "text": text,
            "policy_id": policy_id,
            "llm_config": llm_config,
            "rag_context": rag_context
        })
    
    def eu_ai_act_compliance_report(self, policy_id: int, start_date: str, end_date: str) -> dict:
        """EU AI Act compliance."""
        return self._call("eu_ai_act_compliance_report", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def nist_ai_rmf_compliance_report(self, policy_id: int, start_date: str, end_date: str) -> dict:
        """NIST RMF compliance."""
        return self._call("nist_ai_rmf_compliance_report", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def nist_privacy_compliance_report(self, policy_id: int, start_date: str, end_date: str) -> dict:
        """NIST Privacy compliance."""
        return self._call("nist_privacy_compliance_report", {
            "tenant_id": self.tenant_id,
            "policy_id": policy_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def policy_changes_report(self, start_date: str, end_date: str, format: str = "json") -> dict | str:
        """Policy changes report."""
        return self._call("policy_changes_report", {
            "tenant_id": self.tenant_id,
            "start_date": start_date,
            "end_date": end_date,
            "format": format
        })
    
    def decisions_report(self, start_date: str, end_date: str, format: str = "json") -> dict | str:
        """Decisions report."""
        return self._call("decisions_report", {
            "tenant_id": self.tenant_id,
            "start_date": start_date,
            "end_date": end_date,
            "format": format
        })
    
    # ===== Helper =====
    
    def _call(self, tool_name: str, params: dict) -> dict | str | List:
        """Call a tool on the MCP server."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.url}/call",
                json={"tool": tool_name, "params": params},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
```

---

## 5-Week Implementation Timeline

### Week 1-2: Foundation + CRUD (8 tools)
- Implement Phase 1 & 2 as per MCP_SERVER_IMPLEMENTATION.md
- Deliverable: 8 working tools + client

### Week 3: Advanced Reads (8 tools)
- Implement `get_policy()`, `list_policy_versions()`, `get_active_policy_version()`
- Implement `get_evidence()`, `get_decision_detail()`
- Implement `list_policy_changes()`, `list_decision_events()`, `get_trace()`
- Add repository methods if missing
- Deliverable: 16 tools total, 100% read coverage

### Week 4: Complex Writes (3 tools)
- Implement `update_policy()`, `delete_policy()`, `delete_evidence()`
- Add transaction safety
- Deliverable: 19 tools, all CRUD operations

### Week 5: Enterprise Reports (6 tools)
- Implement `protect_and_generate()` with full LLM pipeline
- Implement 3 framework-specific compliance reports
- Implement `policy_changes_report()`, `decisions_report()`
- Deliverable: 25 tools (26 minus maintenance)

### After Week 5:
- Comprehensive testing (integration, load, security)
- Documentation for agent developers
- Deployment to staging/production

---

## Testing Strategy

### Unit Tests (Per Phase)
- Input validation for all tools
- Tenant isolation enforcement
- Audit logging verification
- Error handling

### Integration Tests
- End-to-end workflows (create → query → update → delete)
- Cross-tool consistency (e.g., create_policy + get_policy return same data)
- LLM pipeline integration

### Security Tests
- Tenant isolation bypass attempts
- Invalid input handling
- Admin-only operation checks
- Rate limiting

### Load Tests
- Concurrent read operations
- Large result sets (pagination)
- Report generation performance

---

## Deployment Checklist

- [ ] All 26 tools implemented and tested
- [ ] Client library complete with all methods
- [ ] Documentation for agent developers
- [ ] Rate limiting configured
- [ ] Auth/tenant isolation verified
- [ ] Audit logging working
- [ ] Error messages user-friendly
- [ ] Performance benchmarks met
- [ ] Staging deployment successful
- [ ] Production deployment with rollback plan

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Tool Coverage | 26/26 (100%) |
| Endpoint Coverage | 23/23 (100%) |
| Response Time (p95) | <500ms |
| Availability | 99.9% |
| Test Coverage | 85%+ |
| Documentation | Complete |
| Agent Developer Onboarding | <30 min |

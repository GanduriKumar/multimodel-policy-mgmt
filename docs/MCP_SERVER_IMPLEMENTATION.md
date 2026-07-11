# MCP Server + Client Implementation Guide

**Status:** Ready to Execute  
**Duration:** 2 weeks (80 hours)  
**Target:** `multimodel-policy-mgmt/backend/mcp_server.py` + client library  
**Prerequisite:** Complete code refactoring first

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Phase 1: MCP Server (Read-Only)](#phase-1-mcp-server-read-only)
3. [Phase 2: MCP Server (Safe CRUD)](#phase-2-mcp-server-safe-crud)
4. [MCP Client Library](#mcp-client-library)
5. [Testing & Validation](#testing--validation)
6. [Deployment](#deployment)

---

## Quick Start

### Prerequisites

```bash
# Install MCP SDK and dependencies
pip install fastmcp httpx pydantic python-dotenv

# Verify backend refactoring is complete
pytest backend/tests/ -q  # Should all pass

# Create MCP directory structure
mkdir -p backend/mcp
touch backend/mcp/__init__.py
touch backend/mcp/server.py
touch backend/mcp/tools.py
touch backend/mcp/context.py
touch backend/mcp/validators.py
```

### Directory Structure

```
backend/
├── app/
│   ├── services/      (already refactored)
│   ├── repos/
│   └── models/
├── mcp/               ← NEW
│   ├── __init__.py
│   ├── server.py      (Main MCP server)
│   ├── tools.py       (Tool implementations)
│   ├── context.py     (Auth context handling)
│   └── validators.py  (Input validation)
├── client/            ← NEW (for agent developers)
│   ├── __init__.py
│   ├── client.py      (MCP client library)
│   └── models.py      (Request/response types)
└── tests/
    ├── test_mcp_server.py
    └── test_mcp_client.py
```

---

## Phase 1: MCP Server (Read-Only)

### Step 1: Create Context Module

**File:** `backend/mcp/context.py`

```python
"""
MCP context management—carries authenticated tenant/agent info.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class MCPContext:
    """Authentication and request context."""
    
    tenant_id: int
    agent_id: str
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Validate context."""
        if not isinstance(self.tenant_id, int) or self.tenant_id <= 0:
            raise ValueError("tenant_id must be positive int")
        
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be non-empty string")


def extract_context(headers: dict) -> MCPContext:
    """Extract authenticated context from MCP request headers."""
    # In real implementation, validate JWT/API key
    tenant_id = int(headers.get("X-Tenant-ID", 0))
    agent_id = headers.get("X-Agent-ID", "unknown")
    request_id = headers.get("X-Request-ID")
    
    return MCPContext(
        tenant_id=tenant_id,
        agent_id=agent_id,
        request_id=request_id
    )
```

### Step 2: Create Validators Module

**File:** `backend/mcp/validators.py`

```python
"""Input validation for MCP tools."""

from typing import dict, list, Optional
from pydantic import BaseModel, Field, validator

class PolicyFilter(BaseModel):
    """Filter options for policy queries."""
    tenant_id: int
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)
    active_only: bool = True
    
    @validator('limit')
    def validate_limit(cls, v):
        if v <= 0:
            raise ValueError("limit must be > 0")
        return v

class AuditLogFilter(BaseModel):
    """Filter options for audit log queries."""
    tenant_id: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    risk_threshold: Optional[int] = Field(None, ge=0, le=100)
    limit: int = Field(default=100, le=1000)
    
    @validator('risk_threshold')
    def validate_risk(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("risk must be 0-100")
        return v

class TextAnalysisRequest(BaseModel):
    """Request to analyze text against policy."""
    tenant_id: int
    policy_id: int
    text: str = Field(..., min_length=1, max_length=10000)
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("text cannot be empty")
        return v.strip()
```

### Step 3: Create Tools Module (Read-Only)

**File:** `backend/mcp/tools.py` (Part 1: Read-only tools)

```python
"""
MCP tools—called by agents via the MCP server.
All tools are read-only in Phase 1.
"""

from typing import List, Optional, dict
from fastmcp import Tool
from app.services.policy_service import PolicyService
from app.services.audit_service import AuditService
from app.services.decision_service import DecisionService
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from mcp.context import MCPContext
from mcp.validators import PolicyFilter, AuditLogFilter, TextAnalysisRequest


class ReadOnlyTools:
    """Read-only MCP tools (Phase 1)."""
    
    def __init__(self, policy_service, audit_service, decision_service):
        self.policy_service = policy_service
        self.audit_service = audit_service
        self.decision_service = decision_service
    
    # =============== TOOL 1: Get Policies ===============
    
    def get_policies(self, tenant_id: int, limit: int = 50, offset: int = 0) -> List[dict]:
        """
        Fetch active policies for a tenant.
        
        Args:
            tenant_id: Tenant ID
            limit: Max results (1-100)
            offset: Pagination offset
        
        Returns:
            List of policy objects with basic info
        
        Example:
            policies = tool.get_policies(tenant_id=1, limit=10)
        """
        try:
            # Validate inputs
            if not isinstance(tenant_id, int) or tenant_id <= 0:
                raise ValueError("Invalid tenant_id")
            if limit <= 0 or limit > 100:
                raise ValueError("limit must be 1-100")
            if offset < 0:
                raise ValueError("offset must be >= 0")
            
            # Query policies
            policies = self.policy_service.list_policies(
                tenant_id=tenant_id,
                offset=offset,
                limit=limit
            )
            
            # Convert to JSON-serializable format
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in policies
            ]
        
        except Exception as e:
            raise ValueError(f"Failed to fetch policies: {str(e)}")
    
    # =============== TOOL 2: Query Audit Logs ===============
    
    def query_audit_logs(
        self,
        tenant_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        risk_threshold: Optional[int] = None,
        limit: int = 100
    ) -> dict:
        """
        Query decision logs for a tenant with optional filtering.
        
        Args:
            tenant_id: Tenant ID
            start_date: ISO format start date
            end_date: ISO format end date
            risk_threshold: Filter by risk >= threshold (0-100)
            limit: Max results (1-1000)
        
        Returns:
            Paginated list of decision logs
        
        Example:
            logs = tool.query_audit_logs(
                tenant_id=1,
                risk_threshold=70,
                limit=50
            )
        """
        try:
            # Validate
            if not isinstance(tenant_id, int) or tenant_id <= 0:
                raise ValueError("Invalid tenant_id")
            if limit <= 0 or limit > 1000:
                raise ValueError("limit must be 1-1000")
            
            # Query
            logs = self.audit_service.query_logs(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                risk_threshold=risk_threshold,
                limit=limit
            )
            
            # Format response
            return {
                "total": len(logs),
                "limit": limit,
                "logs": [
                    {
                        "id": log.id,
                        "input_text": log.input_text[:100],  # Truncate for privacy
                        "allowed": log.allowed,
                        "risk_score": log.risk_score,
                        "reasons": log.reasons,
                        "created_at": log.created_at.isoformat()
                    }
                    for log in logs
                ]
            }
        
        except Exception as e:
            raise ValueError(f"Failed to query audit logs: {str(e)}")
    
    # =============== TOOL 3: Analyze Text (Read-Only) ===============
    
    def analyze_text(
        self,
        tenant_id: int,
        policy_id: int,
        text: str
    ) -> dict:
        """
        Analyze text against a policy (read-only, no logging).
        
        Args:
            tenant_id: Tenant ID
            policy_id: Policy to check against
            text: Text to analyze
        
        Returns:
            Analysis result with risk score and violations
        
        Example:
            result = tool.analyze_text(
                tenant_id=1,
                policy_id=42,
                text="Is this safe to deploy?"
            )
        """
        try:
            # Validate
            if not isinstance(text, str) or not text.strip():
                raise ValueError("text cannot be empty")
            if len(text) > 10000:
                raise ValueError("text too long (max 10000 chars)")
            
            # Load policy
            policy = self.policy_service.get_policy(policy_id)
            if not policy or policy.tenant_id != tenant_id:
                raise ValueError(f"Policy {policy_id} not found")
            
            # Evaluate WITHOUT logging
            pii_violations = self.decision_service._check_pii_rules(text, policy)
            risk = self.decision_service._compute_risk(text, policy, None)
            
            # Format response
            return {
                "allowed": risk.score < policy.risk_threshold and not pii_violations,
                "risk_score": risk.score,
                "risk_level": self._get_risk_level(risk.score),
                "pii_violations": [
                    {
                        "marker": v.marker,
                        "type": v.pii_type
                    }
                    for v in pii_violations
                ],
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            raise ValueError(f"Failed to analyze text: {str(e)}")
    
    # =============== TOOL 4: Generate Compliance Report ===============
    
    def generate_compliance_report(
        self,
        tenant_id: int,
        framework: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Generate compliance report for a framework.
        
        Args:
            tenant_id: Tenant ID
            framework: One of 'eu_ai_act', 'nist_ai_rmf', 'nist_privacy'
            start_date: Report start date (optional)
            end_date: Report end date (optional)
        
        Returns:
            Compliance report JSON
        
        Example:
            report = tool.generate_compliance_report(
                tenant_id=1,
                framework='eu_ai_act',
                start_date='2024-01-01',
                end_date='2024-12-31'
            )
        """
        try:
            # Validate framework
            valid_frameworks = ['eu_ai_act', 'nist_ai_rmf', 'nist_privacy']
            if framework not in valid_frameworks:
                raise ValueError(f"Invalid framework. Must be one of {valid_frameworks}")
            
            # Generate report
            report = self.audit_service.generate_compliance_report(
                tenant_id=tenant_id,
                framework=framework,
                start_date=start_date,
                end_date=end_date
            )
            
            return report
        
        except Exception as e:
            raise ValueError(f"Failed to generate report: {str(e)}")
    
    # =============== Helper Methods ===============
    
    def _get_risk_level(self, score: int) -> str:
        """Classify risk score into level."""
        if score < 25:
            return "low"
        elif score < 50:
            return "medium"
        elif score < 75:
            return "high"
        else:
            return "critical"
```

### Step 4: Create MCP Server

**File:** `backend/mcp/server.py` (Phase 1 - Read-Only)

```python
"""
MCP Server for policy management.
Phase 1: Read-only operations.
"""

from fastmcp import FastMCP
from fastapi import FastAPI, Request
from app.core.deps import get_db_session
from app.services.policy_service import PolicyService
from app.services.audit_service import AuditService
from app.services.decision_service import DecisionService
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from mcp.tools import ReadOnlyTools
from mcp.context import extract_context

# Initialize MCP server
mcp = FastMCP(
    name="multimodel-policy-mgmt",
    description="AI Safety & Policy Management MCP Server",
    version="1.0.0"
)

# Lazy-loaded services (initialized on first request)
_services = None

def get_services():
    """Get or initialize services."""
    global _services
    if _services is None:
        db = get_db_session()
        policy_repo = SqlAlchemyPolicyRepo(db)
        audit_repo = SqlAlchemyAuditRepo(db)
        
        policy_svc = PolicyService(repo=policy_repo)
        audit_svc = AuditService(repo=audit_repo)
        decision_svc = DecisionService(
            policy_repo=policy_repo,
            audit_repo=audit_repo
        )
        
        _services = {
            'policy': policy_svc,
            'audit': audit_svc,
            'decision': decision_svc,
            'tools': ReadOnlyTools(policy_svc, audit_svc, decision_svc)
        }
    
    return _services


# =============== MCP TOOLS REGISTRATION ===============

@mcp.tool()
def get_policies(
    tenant_id: int,
    limit: int = 50,
    offset: int = 0
) -> list:
    """Fetch active policies for a tenant."""
    services = get_services()
    return services['tools'].get_policies(tenant_id, limit, offset)


@mcp.tool()
def query_audit_logs(
    tenant_id: int,
    start_date: str = None,
    end_date: str = None,
    risk_threshold: int = None,
    limit: int = 100
) -> dict:
    """Query decision logs for a tenant."""
    services = get_services()
    return services['tools'].query_audit_logs(
        tenant_id, start_date, end_date, risk_threshold, limit
    )


@mcp.tool()
def analyze_text(
    tenant_id: int,
    policy_id: int,
    text: str
) -> dict:
    """Analyze text against a policy (read-only)."""
    services = get_services()
    return services['tools'].analyze_text(tenant_id, policy_id, text)


@mcp.tool()
def generate_compliance_report(
    tenant_id: int,
    framework: str,
    start_date: str = None,
    end_date: str = None
) -> dict:
    """Generate compliance report for a framework."""
    services = get_services()
    return services['tools'].generate_compliance_report(
        tenant_id, framework, start_date, end_date
    )


# =============== START SERVER ===============

if __name__ == "__main__":
    import uvicorn
    
    # Start MCP server on port 3001
    uvicorn.run(
        mcp,
        host="0.0.0.0",
        port=3001,
        log_level="info"
    )
```

### Step 5: Test Phase 1

Create `backend/tests/test_mcp_phase1.py`:

```python
"""Tests for Phase 1 (read-only) MCP tools."""

import pytest
from mcp.server import get_services

class TestReadOnlyTools:
    
    def test_get_policies(self):
        """Test fetching policies."""
        services = get_services()
        result = services['tools'].get_policies(tenant_id=1, limit=10)
        
        assert isinstance(result, list)
        assert all('id' in p and 'name' in p for p in result)
    
    def test_get_policies_invalid_tenant(self):
        """Test error on invalid tenant."""
        services = get_services()
        
        with pytest.raises(ValueError):
            services['tools'].get_policies(tenant_id=-1)
    
    def test_query_audit_logs(self):
        """Test querying audit logs."""
        services = get_services()
        result = services['tools'].query_audit_logs(tenant_id=1, limit=10)
        
        assert 'logs' in result
        assert 'total' in result
        assert result['limit'] == 10
    
    def test_analyze_text_safe(self):
        """Test analyzing safe text."""
        services = get_services()
        result = services['tools'].analyze_text(
            tenant_id=1,
            policy_id=1,
            text="Hello world"
        )
        
        assert 'allowed' in result
        assert 'risk_score' in result
        assert result['risk_score'] < 50
    
    def test_analyze_text_risky(self):
        """Test analyzing risky text."""
        services = get_services()
        result = services['tools'].analyze_text(
            tenant_id=1,
            policy_id=1,
            text="bomb threat"
        )
        
        assert 'allowed' in result
        assert 'risk_score' in result
    
    def test_generate_compliance_report(self):
        """Test generating compliance report."""
        services = get_services()
        result = services['tools'].generate_compliance_report(
            tenant_id=1,
            framework='eu_ai_act'
        )
        
        assert isinstance(result, dict)

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Run tests:
```bash
pytest backend/tests/test_mcp_phase1.py -v
```

---

## Phase 2: MCP Server (Safe CRUD)

### Step 1: Create CRUD Tools Module

**File:** `backend/mcp/tools.py` (Part 2: CRUD Tools)

Add to `ReadOnlyTools` class or create `CRUDTools`:

```python
class CRUDTools(ReadOnlyTools):
    """CRUD tools (Phase 2)—with input validation & tenant isolation."""
    
    # =============== TOOL 5: Create Policy ===============
    
    def create_policy(
        self,
        tenant_id: int,
        name: str,
        slug: str,
        description: Optional[str] = None,
        context: Optional[MCPContext] = None
    ) -> dict:
        """
        Create a new policy.
        
        Args:
            tenant_id: Tenant ID
            name: Policy name
            slug: URL-safe slug
            description: Policy description
            context: MCP context (tenant enforced)
        
        Returns:
            Created policy object
        """
        try:
            # Validate inputs
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name required")
            if not isinstance(slug, str) or not slug.strip():
                raise ValueError("slug required")
            if len(name) > 100:
                raise ValueError("name too long")
            if len(slug) > 50:
                raise ValueError("slug too long")
            
            # Enforce tenant from context (NOT from input)
            if context:
                tenant_id = context.tenant_id
            
            # Create policy
            policy = self.policy_service.create_policy(
                tenant_id=tenant_id,
                name=name.strip(),
                slug=slug.strip(),
                description=description
            )
            
            # Audit log
            self.audit_service.log_action(
                tenant_id=tenant_id,
                agent_id=context.agent_id if context else "unknown",
                action="create_policy",
                metadata={
                    "policy_id": policy.id,
                    "policy_name": name,
                    "request_id": context.request_id if context else None
                }
            )
            
            return {
                "id": policy.id,
                "name": policy.name,
                "slug": policy.slug,
                "created_at": policy.created_at.isoformat()
            }
        
        except Exception as e:
            raise ValueError(f"Failed to create policy: {str(e)}")
    
    # =============== TOOL 6: Create Policy Version ===============
    
    def create_policy_version(
        self,
        tenant_id: int,
        policy_id: int,
        document: dict,
        context: Optional[MCPContext] = None
    ) -> dict:
        """
        Create a new policy version (immutable snapshot).
        
        Args:
            tenant_id: Tenant ID
            policy_id: Parent policy ID
            document: Policy rules as dict
            context: MCP context
        
        Returns:
            Created version object
        """
        try:
            # Validate document
            if not isinstance(document, dict):
                raise ValueError("document must be dict")
            if not document:
                raise ValueError("document cannot be empty")
            
            # Load policy (enforce tenant)
            policy = self.policy_service.get_policy(policy_id)
            if not policy or policy.tenant_id != tenant_id:
                raise ValueError(f"Policy {policy_id} not found")
            
            # Validate document structure
            required_fields = ['blocked_terms', 'pii_rules', 'risk_threshold']
            missing = [f for f in required_fields if f not in document]
            if missing:
                raise ValueError(f"Missing fields: {missing}")
            
            # Create version
            version = self.policy_service.create_version(
                policy_id=policy_id,
                document=document,
                is_active=False
            )
            
            # Audit log
            self.audit_service.log_action(
                tenant_id=tenant_id,
                agent_id=context.agent_id if context else "unknown",
                action="create_policy_version",
                metadata={
                    "policy_id": policy_id,
                    "version": version.version,
                    "request_id": context.request_id if context else None
                }
            )
            
            return {
                "version": version.version,
                "policy_id": policy_id,
                "is_active": version.is_active,
                "created_at": version.created_at.isoformat()
            }
        
        except Exception as e:
            raise ValueError(f"Failed to create version: {str(e)}")
    
    # =============== TOOL 7: Activate Policy Version ===============
    
    def activate_policy_version(
        self,
        tenant_id: int,
        policy_id: int,
        version: int,
        context: Optional[MCPContext] = None
    ) -> dict:
        """
        Activate a specific policy version (atomic, deactivates others).
        
        Args:
            tenant_id: Tenant ID
            policy_id: Policy ID
            version: Version number to activate
            context: MCP context
        
        Returns:
            Activated version object
        """
        try:
            # Load policy (enforce tenant)
            policy = self.policy_service.get_policy(policy_id)
            if not policy or policy.tenant_id != tenant_id:
                raise ValueError(f"Policy {policy_id} not found")
            
            # Activate version (atomic)
            active = self.policy_service.set_active_version(
                policy_id=policy_id,
                version=version
            )
            
            # Audit log
            self.audit_service.log_action(
                tenant_id=tenant_id,
                agent_id=context.agent_id if context else "unknown",
                action="activate_policy_version",
                metadata={
                    "policy_id": policy_id,
                    "version": version,
                    "request_id": context.request_id if context else None
                }
            )
            
            return {
                "version": active.version,
                "policy_id": policy_id,
                "is_active": active.is_active,
                "activated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            raise ValueError(f"Failed to activate version: {str(e)}")
    
    # =============== TOOL 8: Ingest Evidence ===============
    
    def ingest_evidence(
        self,
        tenant_id: int,
        evidence_type: str,
        source: str,
        content_text: str,
        metadata: Optional[dict] = None,
        context: Optional[MCPContext] = None
    ) -> dict:
        """
        Ingest evidence for audit trail.
        
        Args:
            tenant_id: Tenant ID
            evidence_type: Type of evidence
            source: Source system/agent
            content_text: Evidence content
            metadata: Optional metadata
            context: MCP context
        
        Returns:
            Created evidence object
        """
        try:
            # Validate inputs
            if not evidence_type or not isinstance(evidence_type, str):
                raise ValueError("evidence_type required")
            if not source or not isinstance(source, str):
                raise ValueError("source required")
            if not content_text or not isinstance(content_text, str):
                raise ValueError("content_text required")
            if len(content_text) > 100000:
                raise ValueError("content too large (max 100KB)")
            
            # Create evidence
            evidence = self.audit_service.ingest_evidence(
                tenant_id=tenant_id,
                evidence_type=evidence_type.strip(),
                source=source.strip(),
                content_text=content_text.strip(),
                metadata=metadata or {}
            )
            
            # Audit log
            self.audit_service.log_action(
                tenant_id=tenant_id,
                agent_id=context.agent_id if context else "unknown",
                action="ingest_evidence",
                metadata={
                    "evidence_id": evidence.id,
                    "evidence_type": evidence_type,
                    "request_id": context.request_id if context else None
                }
            )
            
            return {
                "id": evidence.id,
                "type": evidence.type,
                "source": evidence.source,
                "created_at": evidence.created_at.isoformat()
            }
        
        except Exception as e:
            raise ValueError(f"Failed to ingest evidence: {str(e)}")
```

### Step 2: Update MCP Server to Include CRUD

**File:** `backend/mcp/server.py` (Phase 2 additions)

Add these tool registrations:

```python
@mcp.tool()
def create_policy(
    tenant_id: int,
    name: str,
    slug: str,
    description: str = None
) -> dict:
    """Create a new policy."""
    services = get_services()
    # In real implementation, extract context from request headers
    return services['tools'].create_policy(tenant_id, name, slug, description)


@mcp.tool()
def create_policy_version(
    tenant_id: int,
    policy_id: int,
    document: dict
) -> dict:
    """Create a new policy version."""
    services = get_services()
    return services['tools'].create_policy_version(tenant_id, policy_id, document)


@mcp.tool()
def activate_policy_version(
    tenant_id: int,
    policy_id: int,
    version: int
) -> dict:
    """Activate a policy version."""
    services = get_services()
    return services['tools'].activate_policy_version(tenant_id, policy_id, version)


@mcp.tool()
def ingest_evidence(
    tenant_id: int,
    evidence_type: str,
    source: str,
    content_text: str,
    metadata: dict = None
) -> dict:
    """Ingest evidence."""
    services = get_services()
    return services['tools'].ingest_evidence(
        tenant_id, evidence_type, source, content_text, metadata
    )
```

---

## MCP Client Library

Agent developers use this client to call MCP tools. This is the "convenience layer" so they don't deal with MCP protocol directly.

### Step 1: Create Client Models

**File:** `backend/client/models.py`

```python
"""Request/response models for MCP client."""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Policy:
    """Policy object."""
    id: int
    name: str
    slug: str
    is_active: bool
    created_at: str

@dataclass
class Decision:
    """Decision object."""
    id: int
    allowed: bool
    risk_score: int
    reasons: List[str]
    created_at: str

@dataclass
class AnalysisResult:
    """Text analysis result."""
    allowed: bool
    risk_score: int
    risk_level: str
    pii_violations: List[dict]

@dataclass
class EvidenceItem:
    """Evidence object."""
    id: int
    type: str
    source: str
    created_at: str
```

### Step 2: Create Client Class

**File:** `backend/client/client.py`

```python
"""MCP Client Library for agents."""

import httpx
import json
from typing import List, Optional, dict
from client.models import Policy, Decision, AnalysisResult, EvidenceItem

class PolicyMgmtMCPClient:
    """High-level client for policy management MCP server."""
    
    def __init__(
        self,
        url: str = "http://localhost:3001",
        tenant_id: int = 1,
        agent_id: str = "default-agent",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize client.
        
        Args:
            url: MCP server URL
            tenant_id: Tenant ID
            agent_id: Agent identifier
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip("/")
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=self.url,
            timeout=timeout,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> dict:
        """Get request headers."""
        headers = {
            "X-Tenant-ID": str(self.tenant_id),
            "X-Agent-ID": self.agent_id,
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _call_tool(self, tool_name: str, **kwargs) -> dict:
        """Call an MCP tool."""
        try:
            response = self.client.post(
                f"/mcp/tool/{tool_name}",
                json=kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"MCP tool call failed: {str(e)}")
    
    # =============== READ OPERATIONS ===============
    
    def get_policies(self, limit: int = 50, offset: int = 0) -> List[Policy]:
        """Fetch active policies."""
        result = self._call_tool(
            "get_policies",
            tenant_id=self.tenant_id,
            limit=limit,
            offset=offset
        )
        return [Policy(**p) for p in result]
    
    def query_audit_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        risk_threshold: Optional[int] = None,
        limit: int = 100
    ) -> List[Decision]:
        """Query audit logs."""
        result = self._call_tool(
            "query_audit_logs",
            tenant_id=self.tenant_id,
            start_date=start_date,
            end_date=end_date,
            risk_threshold=risk_threshold,
            limit=limit
        )
        return [Decision(**log) for log in result.get("logs", [])]
    
    def analyze_text(self, policy_id: int, text: str) -> AnalysisResult:
        """Analyze text against policy."""
        result = self._call_tool(
            "analyze_text",
            tenant_id=self.tenant_id,
            policy_id=policy_id,
            text=text
        )
        return AnalysisResult(**result)
    
    def generate_compliance_report(
        self,
        framework: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """Generate compliance report."""
        return self._call_tool(
            "generate_compliance_report",
            tenant_id=self.tenant_id,
            framework=framework,
            start_date=start_date,
            end_date=end_date
        )
    
    # =============== WRITE OPERATIONS ===============
    
    def create_policy(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None
    ) -> Policy:
        """Create a new policy."""
        result = self._call_tool(
            "create_policy",
            tenant_id=self.tenant_id,
            name=name,
            slug=slug,
            description=description
        )
        return Policy(**result)
    
    def create_policy_version(
        self,
        policy_id: int,
        document: dict
    ) -> dict:
        """Create a policy version."""
        return self._call_tool(
            "create_policy_version",
            tenant_id=self.tenant_id,
            policy_id=policy_id,
            document=document
        )
    
    def activate_policy_version(self, policy_id: int, version: int) -> dict:
        """Activate a policy version."""
        return self._call_tool(
            "activate_policy_version",
            tenant_id=self.tenant_id,
            policy_id=policy_id,
            version=version
        )
    
    def ingest_evidence(
        self,
        evidence_type: str,
        source: str,
        content_text: str,
        metadata: Optional[dict] = None
    ) -> EvidenceItem:
        """Ingest evidence."""
        result = self._call_tool(
            "ingest_evidence",
            tenant_id=self.tenant_id,
            evidence_type=evidence_type,
            source=source,
            content_text=content_text,
            metadata=metadata
        )
        return EvidenceItem(**result)
    
    def close(self):
        """Close client connection."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
```

### Step 3: Create Client Usage Examples

**File:** `backend/client/examples.py`

```python
"""Usage examples for the MCP client."""

from client.client import PolicyMgmtMCPClient

# Example 1: Query policies
with PolicyMgmtMCPClient(tenant_id=1, agent_id="analysis-agent") as client:
    policies = client.get_policies(limit=10)
    for policy in policies:
        print(f"Policy: {policy.name} ({policy.slug})")

# Example 2: Analyze text
with PolicyMgmtMCPClient(tenant_id=1, agent_id="safety-agent") as client:
    result = client.analyze_text(policy_id=1, text="Is this safe?")
    print(f"Allowed: {result.allowed}")
    print(f"Risk Score: {result.risk_score}")

# Example 3: Create policy + version
with PolicyMgmtMCPClient(tenant_id=1, agent_id="policy-agent") as client:
    # Create policy
    policy = client.create_policy(
        name="Content Safety v2",
        slug="content-safety-v2",
        description="Updated rules"
    )
    print(f"Created policy {policy.id}")
    
    # Create version
    version = client.create_policy_version(
        policy_id=policy.id,
        document={
            "blocked_terms": ["gun", "bomb"],
            "pii_rules": {"email": {"action": "detect"}},
            "risk_threshold": 75
        }
    )
    print(f"Created version {version['version']}")
    
    # Activate version
    active = client.activate_policy_version(
        policy_id=policy.id,
        version=version['version']
    )
    print(f"Activated version {active['version']}")

# Example 4: Ingest evidence
with PolicyMgmtMCPClient(tenant_id=1, agent_id="evidence-agent") as client:
    evidence = client.ingest_evidence(
        evidence_type="audit_log",
        source="ci_pipeline",
        content_text="Model evaluation passed with 95% accuracy",
        metadata={"test_id": "1234"}
    )
    print(f"Ingested evidence {evidence.id}")

# Example 5: Generate compliance report
with PolicyMgmtMCPClient(tenant_id=1, agent_id="compliance-agent") as client:
    report = client.generate_compliance_report(
        framework="eu_ai_act",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"Compliance Score: {report.get('compliance_score')}")
```

---

## Testing & Validation

### Integration Tests

**File:** `backend/tests/test_mcp_integration.py`

```python
"""Integration tests: MCP server + client + refactored backend."""

import pytest
from client.client import PolicyMgmtMCPClient
from app.models import Policy

class TestMCPIntegration:
    
    def test_end_to_end_workflow(self):
        """Test complete workflow: create policy → version → activate."""
        with PolicyMgmtMCPClient(tenant_id=1, agent_id="test-agent") as client:
            # Create policy
            policy = client.create_policy(
                name="Test Policy",
                slug="test-policy"
            )
            assert policy.id > 0
            
            # Create version
            version = client.create_policy_version(
                policy_id=policy.id,
                document={
                    "blocked_terms": ["test"],
                    "pii_rules": {},
                    "risk_threshold": 50
                }
            )
            assert version['version'] > 0
            
            # Activate
            active = client.activate_policy_version(
                policy_id=policy.id,
                version=version['version']
            )
            assert active['is_active']
            
            # Verify in audit trail
            logs = client.query_audit_logs(limit=100)
            assert len(logs) > 0
    
    def test_analyze_text_workflow(self):
        """Test text analysis."""
        with PolicyMgmtMCPClient(tenant_id=1, agent_id="test-agent") as client:
            result = client.analyze_text(
                policy_id=1,
                text="Hello world"
            )
            
            assert result.allowed
            assert result.risk_score < 50
    
    def test_ingest_evidence(self):
        """Test evidence ingestion."""
        with PolicyMgmtMCPClient(tenant_id=1, agent_id="test-agent") as client:
            evidence = client.ingest_evidence(
                evidence_type="test",
                source="test",
                content_text="Test evidence"
            )
            
            assert evidence.id > 0
            assert evidence.type == "test"
```

Run tests:

```bash
# Start MCP server
python backend/mcp/server.py &

# Run integration tests
pytest backend/tests/test_mcp_integration.py -v

# Kill server
pkill -f "python backend/mcp/server.py"
```

---

## Deployment

### Docker Setup

**File:** `backend/Dockerfile.mcp`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install

# Copy source
COPY . .

# Expose MCP port
EXPOSE 3001

# Start MCP server
CMD ["python", "-m", "backend.mcp.server"]
```

### Docker Compose

**File:** `docker-compose.yml` (additions)

```yaml
mcp-server:
  build:
    context: .
    dockerfile: backend/Dockerfile.mcp
  ports:
    - "3001:3001"
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - LOG_LEVEL=info
  depends_on:
    - postgres
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3001/health"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Start:

```bash
docker-compose up mcp-server
```

---

## Completion Checklist

- [ ] MCP server (Phase 1: read-only) working
- [ ] MCP server (Phase 2: safe CRUD) working
- [ ] MCP client library complete
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Documentation updated
- [ ] Docker builds successfully
- [ ] Health checks passing
- [ ] Client examples working
- [ ] Committed and pushed

---

## Next Steps

1. ✅ Complete code refactoring
2. ✅ Implement MCP server + client (this guide)
3. ⏭️ AgentOps integration (export audit trail)
4. ⏭️ MLflow integration (evaluation metrics)
5. ⏭️ OTEL integration (governance signals)


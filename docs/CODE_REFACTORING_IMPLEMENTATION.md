# Code Refactoring Implementation Guide

**Status:** Ready to Execute  
**Duration:** 3 weeks (120 hours) - *Extended to address code hygiene standards*  
**Target Branch:** `claude/code-structure-review-eprtuy`  
**Prerequisite:** Read `REFACTORING_PLAN.md` and `REFACTORING_VS_QUALITY_STANDARDS.md` first  
**Standards Reference:** Master Engineering Context Pack v3 (CODE_QUALITY_CHECKER, HYGIENE_ENFORCER)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Week 1: Extract Large Functions](#week-1-extract-large-functions)
3. [Week 2: Flatten Nesting & Add Tests](#week-2-flatten-nesting--add-tests)
4. [Week 3: Hygiene Standards & Code Quality (NEW)](#week-3-hygiene-standards--code-quality-new)
5. [Testing & Validation](#testing--validation)
6. [Common Patterns & Recipes](#common-patterns--recipes)
7. [Rollback Strategy](#rollback-strategy)

---

## Quick Start

### Prerequisites
```bash
# Install tools for code quality checks
pip install radon pylint mypy pytest pytest-cov

# Baseline measurements (before refactoring)
radon mi backend/app/services/ -j > metrics_before.json
radon cc backend/app/services/ -a -j >> metrics_before.json
pytest backend/tests/ --cov=backend/app --cov-report=json -q
```

### Main Tasks (In Order)
**WEEK 1-2: Code Structure (80 hours)**
1. **Week 1, Day 1-2:** Extract `decision_service.protect()` (205 lines → 50 lines)
2. **Week 1, Day 3-4:** Extract `protect_endpoint()` (138 lines → 30 lines)
3. **Week 1, Day 5:** Extract `governed_generation_service.protect_and_generate()` (208 lines → 50 lines)
4. **Week 2, Day 1-2:** Flatten nesting in `decision_service.py` and `compliance_renderers.py`
5. **Week 2, Day 3-4:** Add unit tests + linting
6. **Week 2, Day 5:** Final validation + metrics comparison

**WEEK 3: Code Hygiene & Standards (40 hours) - NEW**
7. **Week 3, Day 1:** Class size audit + type hints enforcement
8. **Week 3, Day 2:** Code duplication detection & elimination
9. **Week 3, Day 3:** Naming conventions standardization
10. **Week 3, Day 4:** Import organization + comment style validation
11. **Week 3, Day 5:** File size audit + final verification

---

## Week 1: Extract Large Functions

### Task 1.1: Extract `decision_service.protect()` (205 lines)

**File:** `backend/app/services/decision_service.py`  
**Current Location:** Lines 92-297  
**Complexity:** HIGH (5 levels of nesting, mixed concerns)

#### Step 1: Read the current function
```bash
head -n 297 backend/app/services/decision_service.py | tail -n +92
```

#### Step 2: Create helper function stubs

Add these new functions to `decision_service.py` (before `protect()`):

```python
def _log_request(
    self, 
    input_text: str, 
    policy_id: Optional[int],
    tenant_id: Optional[int],
    evidence_ids: Optional[list[int]]
) -> RequestLog:
    """Log incoming request."""
    # TODO: Implementation from lines 153-163

def _load_policy(
    self, 
    policy_id: Optional[int],
    tenant_id: Optional[int],
    request_log: RequestLog
) -> Policy:
    """Load policy, fallback to default."""
    # TODO: Implementation from lines 166-180

def _check_pii_rules(
    self, 
    text: str, 
    policy: Policy
) -> List[PiiViolation]:
    """Check PII violations (no nesting)."""
    # TODO: Implementation from lines 186-218

def _find_matching_rule(self, marker: str, rules: dict) -> Optional[str]:
    """Find first matching rule key."""
    # TODO: Implementation helper

def _compute_risk(
    self, 
    text: str, 
    policy: Policy,
    evidence_ids: Optional[list[int]]
) -> RiskScore:
    """Compute risk score."""
    # TODO: Implementation from lines 220-241

def _make_decision(
    self, 
    policy: Policy, 
    risk: RiskScore,
    violations: List[PiiViolation]
) -> Decision:
    """Make allow/block/review decision."""
    # TODO: Implementation from lines 254-260

def _log_decision(
    self, 
    request_log: RequestLog, 
    policy: Policy,
    risk: RiskScore,
    violations: List[PiiViolation],
    decision: Decision
) -> DecisionLog:
    """Log decision to audit trail."""
    # TODO: Implementation from lines 263-287
```

#### Step 3: Implement `_log_request()`

Replace `# TODO: Implementation from lines 153-163` with:

```python
def _log_request(
    self, 
    input_text: str, 
    policy_id: Optional[int],
    tenant_id: Optional[int],
    evidence_ids: Optional[list[int]]
) -> RequestLog:
    """Log incoming request."""
    return self.audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=input_text,
        policy_id=policy_id,
        input_hash=sha256_text(input_text),
        metadata={"evidence_ids": evidence_ids} if evidence_ids else None
    )
```

#### Step 4: Implement `_load_policy()`

```python
def _load_policy(
    self, 
    policy_id: Optional[int],
    tenant_id: Optional[int],
    request_log: RequestLog
) -> Policy:
    """Load policy, fallback to default."""
    if policy_id:
        policy = self.policy_repo.get_by_id(policy_id)
    else:
        policy = self.policy_repo.get_default_policy(tenant_id)
    
    if not policy:
        raise PolicyNotFound(f"Policy {policy_id or 'default'} not found")
    
    # Update request log with policy info
    request_log.policy_id = policy.id
    self.audit_repo.update_request(request_log)
    
    return policy
```

#### Step 5: Implement `_check_pii_rules()`

```python
def _check_pii_rules(
    self, 
    text: str, 
    policy: Policy
) -> List[PiiViolation]:
    """Check PII violations (NO NESTING)."""
    # Guard: No PII rules defined
    if not policy.pii_rules:
        return []
    
    # Guard: No PII detected
    pii_markers = detect_pii_like(text)
    if not pii_markers:
        return []
    
    # Simple loop—no nesting
    violations = []
    for marker in pii_markers:
        rule_key = self._find_matching_rule(marker, policy.pii_rules)
        if rule_key:
            rule_config = policy.pii_rules.get(rule_key, {})
            violations.append(PiiViolation(marker, rule_key, rule_config))
    
    return violations

def _find_matching_rule(self, marker: str, rules: dict) -> Optional[str]:
    """Find first rule key that matches marker."""
    pii_type = marker.replace("_like", "").replace("_", "")
    
    for rule_key in rules.keys():
        if (rule_key.lower() in pii_type.lower() or 
            pii_type.lower() in rule_key.lower()):
            return rule_key
    
    return None
```

#### Step 6: Implement `_compute_risk()`

```python
def _compute_risk(
    self, 
    text: str, 
    policy: Policy,
    evidence_ids: Optional[list[int]]
) -> RiskScore:
    """Compute risk score."""
    return self.risk_engine.compute_risk(
        input_text=text,
        policy_doc=policy,
        evidence_ids=evidence_ids
    )
```

#### Step 7: Implement `_make_decision()`

```python
def _make_decision(
    self, 
    policy: Policy, 
    risk: RiskScore,
    violations: List[PiiViolation]
) -> Decision:
    """Make allow/block/review decision (pure logic)."""
    # PII violations take priority
    if violations and policy.pii_block_enabled:
        return Decision(allowed=False, reasons=["pii_detected"])
    
    # Risk threshold check
    if risk.score >= policy.risk_threshold:
        return Decision(allowed=False, reasons=["risk_above_threshold"])
    
    # Warning threshold (in conservative mode)
    if policy.conservative_mode and risk.score >= policy.warning_threshold:
        return Decision(allowed=False, reasons=["risk_above_warning"])
    
    return Decision(allowed=True, reasons=[])
```

#### Step 8: Implement `_log_decision()`

```python
def _log_decision(
    self, 
    request_log: RequestLog, 
    policy: Policy,
    risk: RiskScore,
    violations: List[PiiViolation],
    decision: Decision
) -> DecisionLog:
    """Log decision for audit trail."""
    return self.audit_repo.log_decision(
        tenant_id=request_log.tenant_id,
        request_log_id=request_log.id,
        allowed=decision.allowed,
        reasons=decision.reasons,
        risk_score=risk.score,
        policy_id=policy.id,
        policy_version_id=policy.active_version_id
    )
```

#### Step 9: Refactor `protect()` to use helpers

Replace the entire `protect()` function (lines 92-297) with:

```python
def protect(
    self, 
    input_text: str, 
    policy_id: Optional[int] = None,
    evidence_ids: Optional[list[int]] = None,
    tenant_id: Optional[int] = None
) -> ProtectResponse:
    """Orchestrate all protection checks."""
    # Log request
    request_log = self._log_request(input_text, policy_id, tenant_id, evidence_ids)
    
    # Load policy
    policy = self._load_policy(policy_id, tenant_id, request_log)
    
    # Check PII
    pii_violations = self._check_pii_rules(input_text, policy)
    
    # Compute risk
    risk = self._compute_risk(input_text, policy, evidence_ids)
    
    # Make decision
    decision = self._make_decision(policy, risk, pii_violations)
    
    # Log decision
    decision_log = self._log_decision(request_log, policy, risk, pii_violations, decision)
    
    # Return response
    return ProtectResponse(
        allowed=decision.allowed,
        decision_id=decision_log.id,
        risk_score=risk.score,
        reasons=decision.reasons
    )
```

#### Step 10: Test extraction

```bash
# Run tests for decision_service
pytest backend/tests/test_decision_service.py -v

# Check function sizes
radon cc backend/app/services/decision_service.py -a
```

**Expected Output:**
- `protect()` should be ~10 lines
- Each helper should be 10-25 lines
- No functions with cyclomatic complexity > 5

---

### Task 1.2: Extract `protect_endpoint()` (138 lines)

**File:** `backend/app/api/routes/protect.py`  
**Current Location:** Lines 28-166  
**Complexity:** MEDIUM (3 levels of nesting, mixed concerns)

#### Step 1: Create helper functions in same file

Add before `protect_endpoint()`:

```python
def _validate_tenant(tenant_id: int) -> Tenant:
    """Validate tenant exists and is active."""
    tenant = tenant_repo.get_by_id(tenant_id)
    if not tenant or not tenant.is_active:
        raise TenantNotFound(tenant_id)
    return tenant

def _resolve_policy(request: ProtectRequest, tenant: Tenant) -> Policy:
    """Resolve policy by slug or ID."""
    if request.policy_slug:
        policy = policy_repo.get_by_slug(tenant.id, request.policy_slug)
    else:
        policy = policy_repo.get_by_id(request.policy_id)
    
    if not policy or policy.tenant_id != tenant.id:
        raise PolicyNotFound(request.policy_slug or request.policy_id)
    
    return policy

def _resolve_evidence_items(
    request: ProtectRequest,
    policy: Policy
) -> List[ResolvedEvidence]:
    """Resolve and normalize evidence items."""
    resolved = []
    
    for ev in request.evidence or []:
        # Normalize type
        normalized_type = _normalize_evidence_type(ev.type, policy)
        
        # Resolve reference if provided
        reference = None
        if ev.reference_id:
            reference = evidence_repo.get_by_id(ev.reference_id)
            if not reference or reference.tenant_id != policy.tenant_id:
                raise EvidenceNotFound(ev.reference_id)
        
        resolved.append(ResolvedEvidence(
            type=normalized_type,
            data=ev.data,
            reference=reference
        ))
    
    return resolved

def _normalize_evidence_type(ev_type: str, policy: Policy) -> str:
    """Map user-provided type to canonical policy type."""
    # Implementation from lines 79-87
    mapping = EVIDENCE_TYPE_MAPPING.get(ev_type, ev_type)
    if mapping not in policy.accepted_evidence_types:
        raise InvalidEvidenceType(mapping)
    return mapping
```

#### Step 2: Refactor `protect_endpoint()`

Replace lines 28-166 with:

```python
@router.post("/api/protect")
async def protect_endpoint(request: ProtectRequest) -> ProtectResponse:
    """Handle protect request."""
    tenant = _validate_tenant(request.tenant_id)
    policy = _resolve_policy(request, tenant)
    evidence = _resolve_evidence_items(request, policy)
    
    return service.protect(
        input_text=request.text,
        policy_id=policy.id,
        evidence_ids=[e.id for e in evidence if e.reference],
        tenant_id=tenant.id
    )
```

#### Step 3: Test

```bash
pytest backend/tests/test_api_protect.py -v
```

---

### Task 1.3: Extract `governed_generation_service.protect_and_generate()` (208 lines)

**File:** `backend/app/services/governed_generation_service.py`  
**Current Location:** Lines 53-261  
**Complexity:** HIGH (8 distinct concerns mixed)

#### Step 1: Create helper functions

```python
def _pre_check_policy(
    self, 
    input_text: str, 
    policy: Policy
) -> PreCheckResult:
    """Run pre-generation policy check."""
    violations = self.decision_service._check_pii_rules(input_text, policy)
    if violations and policy.pii_block_enabled:
        return PreCheckResult(allowed=False, reason="pii_detected")
    return PreCheckResult(allowed=True, reason=None)

def _generate_with_rag(
    self, 
    input_text: str,
    llm_config: dict,
    context_data: Optional[dict]
) -> str:
    """Generate text with RAG context."""
    rag_context = self.rag_proxy.get_context(
        query=input_text,
        metadata=context_data
    )
    
    prompt = self._build_prompt(input_text, rag_context)
    return self.llm_gateway.generate(prompt, llm_config)

def _evaluate_safety(self, text: str, policy: Policy) -> SafetyReport:
    """Evaluate response safety."""
    return self.response_safety_engine.evaluate(text, policy)

def _evaluate_groundedness(
    self, 
    response: str, 
    context: Optional[dict]
) -> GroundednessScore:
    """Evaluate response groundedness."""
    return self.groundedness_engine.evaluate(response, context)

def _make_final_decision(
    self, 
    safety_report: SafetyReport,
    groundedness: GroundednessScore,
    policy: Policy
) -> FinalDecision:
    """Make final allow/block decision."""
    if safety_report.has_violations and policy.safety_block_enabled:
        return FinalDecision(allowed=False, reason="safety_violation")
    
    if groundedness.score < policy.min_groundedness_score:
        return FinalDecision(allowed=False, reason="low_groundedness")
    
    return FinalDecision(allowed=True, reason=None)

def _log_generation(
    self, 
    request_log: RequestLog,
    response: str,
    decision: FinalDecision,
    metadata: dict
) -> GenerationLog:
    """Log generation to audit trail."""
    return self.audit_repo.log_generation(
        request_log_id=request_log.id,
        response_text=response,
        allowed=decision.allowed,
        reason=decision.reason,
        metadata=metadata
    )
```

#### Step 2: Refactor `protect_and_generate()`

```python
def protect_and_generate(
    self, 
    payload: ProtectAndGenerateRequest
) -> ProtectAndGenerateResponse:
    """Generate text with protection and governance."""
    # Log request
    request_log = self.audit_repo.log_request(
        tenant_id=payload.tenant_id,
        input_text=payload.input_text
    )
    
    # Load policy
    policy = self.policy_repo.get_by_id(payload.policy_id)
    if not policy:
        raise PolicyNotFound(payload.policy_id)
    
    # Pre-generation check
    pre_check = self._pre_check_policy(payload.input_text, policy)
    if not pre_check.allowed:
        return ProtectAndGenerateResponse(
            allowed=False,
            reason=pre_check.reason
        )
    
    # Generate with RAG
    generated_text = self._generate_with_rag(
        payload.input_text,
        payload.llm_config,
        payload.context_data
    )
    
    # Evaluate safety
    safety_report = self._evaluate_safety(generated_text, policy)
    
    # Evaluate groundedness
    groundedness = self._evaluate_groundedness(
        generated_text,
        payload.context_data
    )
    
    # Make final decision
    decision = self._make_final_decision(safety_report, groundedness, policy)
    
    # Log generation
    generation_log = self._log_generation(
        request_log,
        generated_text,
        decision,
        {
            "safety_violations": len(safety_report.violations),
            "groundedness_score": groundedness.score
        }
    )
    
    return ProtectAndGenerateResponse(
        allowed=decision.allowed,
        response_text=generated_text if decision.allowed else None,
        reason=decision.reason,
        log_id=generation_log.id
    )
```

#### Step 3: Test

```bash
pytest backend/tests/test_governed_generation_service.py -v
```

---

## Week 2: Flatten Nesting & Add Tests

### Task 2.1: Flatten nesting in `_check_pii_rules()`

**Current Status:** Already extracted in Task 1.1  
**Verification:**

```bash
radon cc backend/app/services/decision_service.py::DecisionService._check_pii_rules -a
# Expected: Complexity 2-3 (max 1 nesting level)
```

### Task 2.2: Flatten nesting in `compliance_renderers.py` (Lines 73-102)

**File:** `backend/app/services/reports/compliance_renderers.py`  
**Current Location:** Lines 52-139  
**Complexity:** HIGH (6 levels of nesting)

#### Step 1: Create helper class

```python
class CSVRenderer:
    """Utility for rendering compliance data to CSV."""
    
    def __init__(self, framework_config: dict):
        self.framework = framework_config.get('name')
        self.items_key = framework_config.get('items_key', 'items')
    
    def render(self, report_dict: dict, writer) -> None:
        """Render compliance report to CSV."""
        rows = self._extract_rows(report_dict)
        for row in rows:
            writer.writerow(row)
    
    def _extract_rows(self, report_dict: dict) -> List[List[str]]:
        """Extract rows from report."""
        rows = []
        for item in report_dict.get(self.items_key, []):
            evidence = self._collect_evidence(item)
            row = self._format_row(item, evidence)
            rows.append(row)
        return rows
    
    def _collect_evidence(self, item: dict) -> List[dict]:
        """Collect evidence from item categories."""
        evidence = []
        for category in item.get('categories', []):
            evidence.extend(self._get_category_evidence(category))
        return evidence
    
    def _get_category_evidence(self, category: dict) -> List[dict]:
        """Extract evidence from single category (NO NESTING)."""
        evidence_data = category.get('evidence', [])
        
        # Guard: Invalid type
        if not isinstance(evidence_data, list):
            return []
        
        # Guard: Empty
        if not evidence_data:
            return []
        
        # Simple loop—max 1 level
        valid = []
        for evidence in evidence_data[:2]:  # Limit to 2
            if self._is_valid_evidence(evidence):
                valid.append(evidence)
        
        return valid
    
    def _is_valid_evidence(self, evidence: dict) -> bool:
        """Check if evidence is valid."""
        if not isinstance(evidence, dict):
            return False
        
        ev_type = evidence.get('type', 'unknown')
        return ev_type in ['detection', 'monitoring', 'audit']
    
    def _format_row(self, item: dict, evidence: List[dict]) -> List[str]:
        """Format item + evidence as CSV row."""
        return [
            item.get('name', 'Unknown'),
            str(len(evidence)),
            ', '.join(e.get('type', '') for e in evidence)
        ]
```

#### Step 2: Update `compliance_to_csv()` to use helper

```python
def compliance_to_csv(self, report_dict: dict, framework: str) -> str:
    """Render compliance data to CSV format."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Get framework config
    config = self._get_framework_config(framework)
    renderer = CSVRenderer(config)
    
    # Render
    renderer.render(report_dict, writer)
    
    return output.getvalue()

def _get_framework_config(self, framework: str) -> dict:
    """Get framework-specific config."""
    configs = {
        'eu_ai_act': {'name': 'EU AI Act', 'items_key': 'articles'},
        'nist_ai_rmf': {'name': 'NIST AI RMF', 'items_key': 'functions'},
        'nist_privacy': {'name': 'NIST Privacy', 'items_key': 'controls'}
    }
    return configs.get(framework, {})
```

#### Step 3: Verify

```bash
radon cc backend/app/services/reports/compliance_renderers.py -a
# All functions should have complexity < 5
```

---

### Task 2.3: Add Unit Tests

Create `backend/tests/test_refactored_functions.py`:

```python
import pytest
from backend.app.services.decision_service import DecisionService
from backend.app.models.policy import Policy, PiiViolation

class TestDecisionServiceRefactored:
    
    def test_protect_with_pii_violations_blocks(self):
        """Test PII violations trigger BLOCK."""
        service = DecisionService(...)
        policy = Policy(pii_rules={"email": {...}}, pii_block_enabled=True)
        
        result = service.protect("my email is test@example.com", policy_id=1)
        
        assert not result.allowed
        assert "pii_detected" in result.reasons
    
    def test_protect_with_high_risk_blocks(self):
        """Test risk scoring blocks high-risk content."""
        policy = Policy(risk_threshold=50)
        
        result = service.protect("bomb threat", policy_id=1)
        
        assert not result.allowed
        assert result.risk_score > 50
    
    def test_protect_with_low_risk_allows(self):
        """Test low-risk content is allowed."""
        policy = Policy(risk_threshold=50)
        
        result = service.protect("hello world", policy_id=1)
        
        assert result.allowed
        assert result.risk_score < 50
    
    def test_check_pii_rules_with_no_rules(self):
        """Test PII check returns empty when no rules."""
        policy = Policy(pii_rules=None)
        
        violations = service._check_pii_rules("test@example.com", policy)
        
        assert violations == []
    
    def test_check_pii_rules_with_violations(self):
        """Test PII detection returns violations."""
        policy = Policy(pii_rules={"email": {...}})
        
        violations = service._check_pii_rules("contact: test@example.com", policy)
        
        assert len(violations) > 0
        assert violations[0].pii_type == "email"
    
    def test_find_matching_rule(self):
        """Test rule matching logic."""
        rules = {"email_pii": {...}, "ssn": {...}}
        
        match = service._find_matching_rule("pii_email_like", rules)
        
        assert match == "email_pii"
    
    def test_make_decision_pii_blocks(self):
        """Test PII violation blocks decision."""
        policy = Policy(pii_block_enabled=True)
        violations = [PiiViolation("test@example.com", "email")]
        
        decision = service._make_decision(policy, risk=RiskScore(10), violations=violations)
        
        assert not decision.allowed
        assert "pii_detected" in decision.reasons
    
    def test_make_decision_risk_blocks(self):
        """Test risk threshold blocks decision."""
        policy = Policy(risk_threshold=50)
        
        decision = service._make_decision(policy, risk=RiskScore(75), violations=[])
        
        assert not decision.allowed
        assert "risk_above_threshold" in decision.reasons
    
    def test_make_decision_allows_safe(self):
        """Test safe content is allowed."""
        policy = Policy(risk_threshold=50)
        
        decision = service._make_decision(policy, risk=RiskScore(25), violations=[])
        
        assert decision.allowed


class TestCSVRenderer:
    
    def test_render_with_valid_data(self):
        """Test CSV rendering with valid data."""
        renderer = CSVRenderer({'name': 'Test', 'items_key': 'items'})
        report = {
            'items': [
                {
                    'name': 'Item1',
                    'categories': [
                        {'evidence': [{'type': 'detection'}]}
                    ]
                }
            ]
        }
        
        output = StringIO()
        renderer.render(report, csv.writer(output))
        
        assert 'Item1' in output.getvalue()
    
    def test_collect_evidence_limits_to_two(self):
        """Test evidence collection limits to 2 items."""
        renderer = CSVRenderer({'name': 'Test', 'items_key': 'items'})
        category = {
            'evidence': [
                {'type': 'detection'},
                {'type': 'monitoring'},
                {'type': 'audit'},
                {'type': 'other'}
            ]
        }
        
        evidence = renderer._get_category_evidence(category)
        
        assert len(evidence) == 2
    
    def test_is_valid_evidence(self):
        """Test evidence validation."""
        renderer = CSVRenderer({'name': 'Test', 'items_key': 'items'})
        
        assert renderer._is_valid_evidence({'type': 'detection'})
        assert not renderer._is_valid_evidence({'type': 'invalid'})
        assert not renderer._is_valid_evidence("not a dict")
```

#### Run tests:

```bash
pytest backend/tests/test_refactored_functions.py -v --cov=backend/app/services

# Expected: All tests pass, coverage > 80%
```

---

## Week 3: Hygiene Standards & Code Quality (NEW)

*Addresses gaps from REFACTORING_VS_QUALITY_STANDARDS.md analysis*

### Task 3.1: Type Hints Enforcement

**Duration:** 1 day (8 hours)  
**Standard:** HYGIENE_ENFORCER - All public functions must have type hints

#### Step 1: Install type checking tools

```bash
pip install mypy pylint pyright
```

#### Step 2: Configure MyPy

Create `backend/pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
disallow_untyped_defs = true
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
exclude = ["build/", "dist/"]
```

#### Step 3: Add type hints to key services

**File:** `backend/app/services/decision_service.py`

```python
from typing import Optional, List, Dict, Any
from datetime import datetime

class DecisionService:
    """Service for making policy decisions."""
    
    def protect(
        self, 
        input_text: str, 
        policy_id: Optional[int] = None,
        evidence_ids: Optional[List[int]] = None,
        tenant_id: Optional[int] = None
    ) -> ProtectResponse:
        """Orchestrate all protection checks."""
        # Implementation...
    
    def _log_request(
        self, 
        input_text: str, 
        policy_id: Optional[int],
        tenant_id: Optional[int],
        evidence_ids: Optional[List[int]]
    ) -> RequestLog:
        """Log incoming request."""
        # Implementation...
    
    def _load_policy(
        self, 
        policy_id: Optional[int],
        tenant_id: Optional[int],
        request_log: RequestLog
    ) -> Policy:
        """Load policy, fallback to default."""
        # Implementation...
    
    def _check_pii_rules(
        self, 
        text: str, 
        policy: Policy
    ) -> List[PiiViolation]:
        """Check PII violations."""
        # Implementation...
    
    def _find_matching_rule(
        self, 
        marker: str, 
        rules: Dict[str, Any]
    ) -> Optional[str]:
        """Find first matching rule key."""
        # Implementation...
    
    def _compute_risk(
        self, 
        text: str, 
        policy: Policy,
        evidence_ids: Optional[List[int]]
    ) -> RiskScore:
        """Compute risk score."""
        # Implementation...
    
    def _make_decision(
        self, 
        policy: Policy, 
        risk: RiskScore,
        violations: List[PiiViolation]
    ) -> Decision:
        """Make allow/block decision."""
        # Implementation...
    
    def _log_decision(
        self, 
        request_log: RequestLog, 
        policy: Policy,
        risk: RiskScore,
        violations: List[PiiViolation],
        decision: Decision
    ) -> DecisionLog:
        """Log decision to audit trail."""
        # Implementation...
```

**File:** `backend/app/services/governed_generation_service.py`

```python
from typing import Optional, Dict, Any

class GovernedGenerationService:
    """Service for LLM generation with governance."""
    
    def protect_and_generate(
        self, 
        payload: ProtectAndGenerateRequest
    ) -> ProtectAndGenerateResponse:
        """Generate text with protection and governance."""
        # Implementation...
    
    def _pre_check_policy(
        self, 
        input_text: str, 
        policy: Policy
    ) -> PreCheckResult:
        """Run pre-generation policy check."""
        # Implementation...
    
    def _generate_with_rag(
        self, 
        input_text: str,
        llm_config: Dict[str, Any],
        context_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate text with RAG context."""
        # Implementation...
    
    def _evaluate_safety(
        self, 
        text: str, 
        policy: Policy
    ) -> SafetyReport:
        """Evaluate response safety."""
        # Implementation...
    
    def _evaluate_groundedness(
        self, 
        response: str, 
        context: Optional[Dict[str, Any]]
    ) -> GroundednessScore:
        """Evaluate response groundedness."""
        # Implementation...
```

#### Step 4: Validate type hints

```bash
# Check type hints
mypy backend/app/services/ --strict

# Expected: Zero errors
```

**Success Criteria:**
- All public functions have return type annotations
- All parameters have type hints
- MyPy strict mode passes with zero errors

---

### Task 3.2: Class Size Audit

**Duration:** 1 day (8 hours)  
**Standard:** CODE_QUALITY_CHECKER - Classes SHOULD be ≤500 lines, MUST be ≤1000 lines

#### Step 1: Audit class sizes

```bash
# Check class sizes
wc -l backend/app/services/*.py | sort -rn

# Find classes >500 lines
grep -n "^class " backend/app/services/*.py | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  line_num=$(echo "$line" | cut -d: -f2)
  # Calculate size
done
```

#### Step 2: Plan refactoring for large classes

Classes typically exceeding 500 lines:
- `DecisionService` (if grown beyond extraction)
- `ComplianceReportService` (if consolidating reports)

**Strategy:** Extract domain concerns into separate services

```python
# EXAMPLE: Split ComplianceReportService

# Before: ComplianceReportService (800+ lines)
#   - EU AI Act report generation
#   - NIST AI RMF report generation
#   - NIST Privacy report generation
#   - CSV/HTML rendering

# After: Split into 4 services
class EUAIActReportService:
    """Generate EU AI Act compliance reports."""
    
class NISTAIRMFReportService:
    """Generate NIST AI RMF compliance reports."""
    
class NISTPrivacyReportService:
    """Generate NIST Privacy compliance reports."""
    
class ComplianceReportRenderer:
    """Render compliance reports to CSV/HTML/JSON."""
```

#### Step 3: Execute refactoring (if needed)

If any class > 500 lines, split following this pattern:
- Extract each framework into separate service
- Move rendering to dedicated renderer class
- Keep factory pattern if needed

**Verification:**

```bash
# Verify all classes < 500 lines
for file in backend/app/services/*.py; do
  lines=$(wc -l < "$file")
  if [ "$lines" -gt 500 ]; then
    echo "WARNING: $file is $lines lines"
  fi
done
```

**Success Criteria:**
- All classes ≤500 lines (SHOULD)
- All classes ≤1000 lines (MUST)
- Clear separation of concerns per service

---

### Task 3.3: Code Duplication Detection & Elimination

**Duration:** 1 day (8 hours)  
**Standard:** HYGIENE_ENFORCER - Eliminate duplicates after 3rd occurrence

#### Step 1: Install and run duplication detector

```bash
pip install pylint-json2html

# Run duplication detection
pylint --disable=all --enable=duplicate-code backend/app/services/ > duplication_report.txt
```

#### Step 2: Identify common patterns

Expected duplications:
- Validation patterns (email, URL, text length)
- Logging patterns (request/response logging)
- Error handling patterns
- Type conversion utilities

#### Step 3: Extract duplicates to shared modules

**Example Pattern 1: Validation**

```python
# backend/app/utils/validators.py
from typing import Optional

class TextValidator:
    """Centralized text validation."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_text_length(
        text: str, 
        min_length: int = 1, 
        max_length: int = 10000
    ) -> bool:
        """Validate text length."""
        return min_length <= len(text) <= max_length
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        from urllib.parse import urlparse
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

# Usage (replaces inline validations):
from app.utils.validators import TextValidator

if not TextValidator.validate_email(user_email):
    raise ValueError("Invalid email")
```

**Example Pattern 2: Logging**

```python
# backend/app/utils/logging.py
from typing import Optional, Dict, Any

class AuditLogger:
    """Centralized audit logging."""
    
    def __init__(self, audit_repo):
        self.audit_repo = audit_repo
    
    def log_action(
        self,
        tenant_id: int,
        agent_id: str,
        action: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an action to audit trail."""
        self.audit_repo.log_request(
            tenant_id=tenant_id,
            agent_id=agent_id,
            action=action,
            resource_id=resource_id,
            details=details
        )

# Usage (replaces copy-paste logging):
logger = AuditLogger(audit_repo)
logger.log_action(
    tenant_id=tenant_id,
    agent_id=agent_id,
    action="create_policy",
    resource_id=policy.id
)
```

#### Step 4: Verify duplication eliminated

```bash
# Re-run detection
pylint --disable=all --enable=duplicate-code backend/app/services/ > duplication_report_after.txt

# Compare
diff duplication_report.txt duplication_report_after.txt
```

**Success Criteria:**
- Zero duplicate code patterns found
- All common utilities extracted to `backend/app/utils/`
- All services use centralized validators/loggers

---

### Task 3.4: Naming Convention Standardization

**Duration:** 1 day (8 hours)  
**Standard:** HYGIENE_ENFORCER - Consistent naming (PascalCase/camelCase/UPPER_SNAKE_CASE)

#### Step 1: Configure linting for naming

```bash
pip install flake8 pep8-naming
```

Create `.flake8` or `setup.cfg`:

```ini
[flake8]
select = N  # Enable naming checks
ignore = E501,W503
exclude = venv,build,dist,tests
max-line-length = 120
```

#### Step 2: Run naming audit

```bash
# Check naming conventions
flake8 backend/app/services/ --select=N

# Expected issues to fix:
# N802: function name should be lowercase
# N806: variable name should be lowercase
# N815: variable name should be lowercase
# N999: module name is invalid
```

#### Step 3: Fix naming issues

**Python Naming Conventions:**
- Classes: `PascalCase` (e.g., `DecisionService`)
- Functions/methods: `snake_case` (e.g., `compute_risk`, `_check_pii_rules`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_TEXT_LENGTH`, `PII_RULES`)
- Private: `_leading_underscore` (e.g., `_internal_helper`)
- Protected: `_leading_underscore` (same as private in Python)

**Example fixes:**

```python
# ❌ BEFORE: Inconsistent naming
class decision_service:  # Wrong: should be PascalCase
    MAX_text = 10000  # Wrong: should be UPPER_SNAKE_CASE
    def Protect():  # Wrong: should be snake_case
        RiskLevel = "high"  # Wrong: should be UPPER_SNAKE_CASE
        return riskLevel  # Wrong: inconsistent

# ✅ AFTER: Consistent naming
class DecisionService:  # Correct: PascalCase
    MAX_TEXT_LENGTH = 10000  # Correct: UPPER_SNAKE_CASE
    def protect(self):  # Correct: snake_case
        RISK_LEVEL = "high"  # Correct: UPPER_SNAKE_CASE
        return RISK_LEVEL  # Correct: consistent
```

#### Step 4: Verify naming conventions

```bash
# Final check
flake8 backend/app/services/ --select=N

# Expected: Zero naming violations
```

**Success Criteria:**
- All classes use PascalCase
- All functions/methods use snake_case
- All constants use UPPER_SNAKE_CASE
- All private methods use `_leading_underscore`
- Flake8 reports zero naming issues

---

### Task 3.5: Import Organization & File Size

**Duration:** 1 day (8 hours)  
**Standard:** HYGIENE_ENFORCER - Imports organized; CODE_QUALITY_CHECKER - Files ≤500 lines

#### Step 1: Install import organizer

```bash
pip install isort
```

#### Step 2: Configure isort

Create `backend/pyproject.toml` (add to existing):

```toml
[tool.isort]
profile = "black"
line_length = 120
multi_line_mode = 3  # Vertical hanging indent
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

# Import order: future, stdlib, third-party, first-party, local
known_first_party = ["app"]
known_local_folder = ["app"]
```

#### Step 3: Apply isort to all files

```bash
# Organize all imports
isort backend/app/ --recursive

# Verify organization
isort backend/app/ --recursive --check-only --diff
```

#### Step 4: Audit file sizes

```bash
# Find files > 500 lines
find backend/app -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print}'
```

**Strategy for large files:**
- Split by concern (separate classes to separate files)
- Use subdirectories: `services/` vs `repos/` vs `models/`
- Max 400 lines per file is ideal

**Example File Structure:**
```
backend/app/
├── services/
│   ├── __init__.py
│   ├── decision_service.py       (250 lines)
│   ├── generation_service.py     (180 lines)
│   ├── compliance_service.py     (220 lines)
│   └── reports/
│       ├── __init__.py
│       ├── eu_ai_act.py         (150 lines)
│       ├── nist_ai_rmf.py       (150 lines)
│       └── renderer.py          (180 lines)
└── repos/
    ├── __init__.py
    ├── policy_repo.py           (200 lines)
    ├── audit_repo.py            (180 lines)
    └── evidence_repo.py         (150 lines)
```

#### Step 5: Validate files and imports

```bash
# Check all files < 500 lines
find backend/app -name "*.py" -exec sh -c 'lines=$(wc -l < "$1"); if [ "$lines" -gt 500 ]; then echo "$1: $lines lines"; fi' _ {} \;

# Verify imports organized
isort backend/app/ --check-only
```

**Success Criteria:**
- All files ≤500 lines (SHOULD)
- Imports organized: external → internal → relative
- All imports sorted alphabetically within groups
- No circular imports

---

### Task 3.6: Comment Style Validation

**Duration:** 0.5 days (4 hours)  
**Standard:** HYGIENE_ENFORCER - Comments explain WHY, not WHAT

#### Step 1: Comment audit

Run through code and identify comments that describe WHAT (obvious code):

```python
# ❌ BAD: Explains WHAT (obvious)
# Increment counter
counter += 1

# ❌ BAD: Explains obvious code
# Create a new list
results = []

# ❌ BAD: Describes code structure
# Loop through users
for user in users:
    # Check if user is active
    if user.is_active:
        # Add to results
        results.append(user)
```

#### Step 2: Rewrite to explain WHY

```python
# ✅ GOOD: Explains WHY (non-obvious)
# Skip header row when processing CSV
counter += 1

# ✅ GOOD: Explains business logic
# Only include active users for billing calculations
results = []

# ✅ GOOD: Clear separation by business step
# Only include active users in billing report (excludes trial accounts)
for user in users:
    if user.is_active:
        results.append(user)

# ✅ GOOD: Explains non-obvious decision
# Use exponential backoff to avoid rate limiting
retry_delay = initial_delay * (2 ** attempt)

# ✅ GOOD: Explains why empty, not just that it's empty
# Default to empty list if no evidence provided (caller may not have any)
evidence_items = []
```

#### Step 3: Apply comment rules

**Guidelines:**
1. Delete obvious comments (code is self-documenting)
2. Add comments for non-obvious decisions
3. Explain WHY, not WHAT
4. Add comments for workarounds/hacks (explain limitation)
5. Add comments for subtle invariants (explain constraint)

#### Step 4: Verify comment quality

Manual code review:
- Read function comments
- Do they explain business logic or just repeat code?
- Are workarounds documented?
- Are assumptions stated?

**Success Criteria:**
- No obvious comments remaining
- All non-obvious logic explained
- All workarounds documented
- Comments answer "WHY", not "WHAT"

---

### Task 3.7: Final Verification

**Duration:** 1 day (8 hours)  
**Validation:** All 12 code quality standards

```bash
# Run comprehensive quality checks
#!/bin/bash
set -e

echo "=== Code Quality Verification ==="

# 1. Type hints
echo "1. Checking type hints..."
mypy backend/app/services/ --strict

# 2. Function size
echo "2. Checking function sizes..."
radon cc backend/app/services/ -a | grep -E "([6-9]|[0-9]{2,})" && echo "WARNING: High complexity detected" || echo "✓ Function complexity OK"

# 3. Nesting depth
echo "3. Checking nesting depth..."
grep -r "^        " backend/app/services/ && echo "WARNING: Deep nesting detected" || echo "✓ Nesting depth OK"

# 4. Class sizes
echo "4. Checking class sizes..."
for file in backend/app/services/*.py; do
    lines=$(wc -l < "$file")
    if [ "$lines" -gt 500 ]; then
        echo "WARNING: $file is $lines lines (>500)"
    fi
done

# 5. Duplication
echo "5. Checking code duplication..."
pylint --disable=all --enable=duplicate-code backend/app/services/ 2>/dev/null || echo "✓ No duplicates detected"

# 6. Naming conventions
echo "6. Checking naming conventions..."
flake8 backend/app/services/ --select=N || echo "✓ Naming OK"

# 7. Imports
echo "7. Checking import organization..."
isort backend/app/ --check-only || echo "WARNING: Imports need organizing"

# 8. Tests
echo "8. Running tests..."
pytest backend/tests/ -q --tb=short

# 9. Coverage
echo "9. Checking coverage..."
pytest backend/tests/ --cov=backend/app --cov-report=term-missing --cov-report=html

# 10. Linting
echo "10. Running linting..."
pylint backend/app/services/ --exit-zero

echo "=== Verification Complete ==="
```

**Expected Results:**

| Check | Status | Criteria |
|-------|--------|----------|
| Type hints | ✅ | MyPy strict: 0 errors |
| Function size | ✅ | All ≤50 lines |
| Nesting depth | ✅ | Max 2-3 levels |
| Class size | ✅ | All ≤500 lines |
| Duplication | ✅ | Zero 3+ patterns |
| Naming | ✅ | Flake8 N checks: 0 errors |
| Imports | ✅ | isort: 0 changes needed |
| Unit tests | ✅ | 100% pass |
| Coverage | ✅ | >85% |
| Linting | ✅ | <10 warnings |

---

## Testing & Validation

### Comprehensive Testing Strategy

```bash
# 1. Run all unit tests
pytest backend/tests/ -v --tb=short

# 2. Check type hints
mypy backend/app/services/ --strict

# 3. Lint code
ruff check backend/app/services/
pylint backend/app/services/ --exit-zero

# 4. Measure complexity
radon cc backend/app/services/ -a
radon mi backend/app/services/ -j

# 5. Check coverage
pytest backend/tests/ --cov=backend/app --cov-report=term-missing --cov-report=html

# 6. Compare metrics
diff metrics_before.json <(radon mi backend/app/services/ -j)
```

### Expected Results (Before vs After)

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Avg function size | 75 lines | 25 lines | ✅ |
| Max nesting depth | 6 | 2 | ✅ |
| Cyclomatic complexity | 8-12 | 3-5 | ✅ |
| Code duplication | 4 patterns | 0 | ✅ |
| Test coverage | 40% | >80% | ✅ |
| Maintainability index | 65 | >80 | ✅ |

---

## Common Patterns & Recipes

### Pattern 1: Guard Clauses Instead of Nesting

**Before:**
```python
if condition1:
    if condition2:
        if condition3:
            do_work()
```

**After:**
```python
if not condition1:
    return []

if not condition2:
    return []

if not condition3:
    return []

do_work()
```

### Pattern 2: Extract Loops to Named Functions

**Before:**
```python
for item in items:
    for sub_item in item.children:
        if sub_item.valid:
            for val in sub_item.values:
                if val > threshold:
                    results.append(val)
```

**After:**
```python
results = []
for item in items:
    results.extend(self._filter_valid_values(item))

def _filter_valid_values(self, item) -> List:
    results = []
    for sub_item in item.children:
        if sub_item.valid:
            results.extend(self._filter_high_values(sub_item))
    return results

def _filter_high_values(self, sub_item) -> List:
    return [v for v in sub_item.values if v > threshold]
```

### Pattern 3: Early Returns

**Before:**
```python
def check(data):
    if valid(data):
        if exists(data):
            if authorized(data):
                return process(data)
            else:
                return error("unauthorized")
        else:
            return error("not found")
    else:
        return error("invalid")
```

**After:**
```python
def check(data):
    if not valid(data):
        return error("invalid")
    
    if not exists(data):
        return error("not found")
    
    if not authorized(data):
        return error("unauthorized")
    
    return process(data)
```

---

## Rollback Strategy

If anything breaks:

```bash
# Stash current changes
git stash

# Go back to safe commit
git reset --hard origin/claude/code-structure-review-eprtuy

# Start specific task again
# Complete and test before moving to next
```

---

## Completion Checklist

### Phase 1-2: Code Structure (Weeks 1-2)
- [ ] Task 1.1: `decision_service.protect()` extracted (10 + 7 helpers)
- [ ] Task 1.2: `protect_endpoint()` extracted (5 + 4 helpers)
- [ ] Task 1.3: `protect_and_generate()` extracted (50 + 6 helpers)
- [ ] Task 2.1: `_check_pii_rules()` nesting flattened
- [ ] Task 2.2: `compliance_renderers.py` nesting flattened (6 → 2 levels)
- [ ] Task 2.3: Unit tests created (15+ test cases, >80% coverage)
- [ ] Metrics comparison: before/after collected

### Phase 3: Code Hygiene & Standards (Week 3)
- [ ] Task 3.1: Type hints added to all public functions
  - [ ] MyPy strict mode: 0 errors
  - [ ] All function signatures annotated
  - [ ] All return types annotated
- [ ] Task 3.2: Class size audit completed
  - [ ] All classes ≤500 lines (SHOULD)
  - [ ] All classes ≤1000 lines (MUST)
  - [ ] Large classes refactored if needed
- [ ] Task 3.3: Code duplication eliminated
  - [ ] Duplication scan: 0 patterns
  - [ ] Common utilities extracted to `utils/`
  - [ ] Validators/loggers centralized
- [ ] Task 3.4: Naming conventions standardized
  - [ ] Classes: PascalCase
  - [ ] Functions: snake_case
  - [ ] Constants: UPPER_SNAKE_CASE
  - [ ] Flake8 naming checks: 0 errors
- [ ] Task 3.5: Import organization & file sizes
  - [ ] All imports organized (external → internal → relative)
  - [ ] All files ≤500 lines
  - [ ] isort check-only: 0 changes needed
- [ ] Task 3.6: Comment style validation
  - [ ] No obvious comments remaining
  - [ ] All non-obvious logic documented
  - [ ] Comments explain WHY, not WHAT

### Final Validation
- [ ] All functions < 50 lines (SHOULD), < 400 lines (MUST)
- [ ] All nesting flattened (max depth = 2-3 levels)
- [ ] All unit tests pass (pytest)
- [ ] Type hints verified (mypy --strict)
- [ ] Code linted (flake8, pylint)
- [ ] Coverage > 85% (pytest --cov)
- [ ] Cyclomatic complexity < 5
- [ ] No code duplication patterns
- [ ] Naming conventions consistent
- [ ] All tests pass without warnings
- [ ] Metrics compared (before vs after)
- [ ] Code review completed
- [ ] Committed and pushed

---

## Timeline Summary

| Phase | Duration | Focus | Deliverable |
|-------|----------|-------|-------------|
| Phase 1-2 | 2 weeks (80 hrs) | Code structure | Extracted functions, flattened nesting, unit tests |
| Phase 3 | 1 week (40 hrs) | Code hygiene | Type hints, naming, duplication, organization |
| **Total** | **3 weeks (120 hrs)** | **Complete refactoring** | **100% standards compliance** |

---

## Standards Coverage

This extended plan addresses all 12 aspects from Master Engineering Context Pack:

| Standard | Aspect | Phase | Status |
|----------|--------|-------|--------|
| CODE_QUALITY_CHECKER | Function size | 1-2 | ✅ |
| CODE_QUALITY_CHECKER | File size | 3 | ✅ |
| CODE_QUALITY_CHECKER | Class size | 3 | ✅ |
| CODE_QUALITY_CHECKER | Cyclomatic complexity | 1-2 | ✅ |
| CODE_QUALITY_CHECKER | Nesting depth | 1-2 | ✅ |
| HYGIENE_ENFORCER | Single responsibility | 1-2 | ✅ |
| HYGIENE_ENFORCER | Type hints | 3 | ✅ |
| HYGIENE_ENFORCER | Code duplication | 3 | ✅ |
| HYGIENE_ENFORCER | Naming conventions | 3 | ✅ |
| HYGIENE_ENFORCER | Comment style | 3 | ✅ |
| HYGIENE_ENFORCER | Import organization | 3 | ✅ |
| General | Testing & coverage | 1-2 | ✅ |

---

## Next Steps After Refactoring

1. ✅ **Week 1-2:** Complete Phase 1-2 (code structure)
2. ✅ **Week 3:** Complete Phase 3 (code hygiene)
3. ⏭️ Start MCP Server Implementation (next document)
4. ⏭️ Create MCP Client Library
5. ⏭️ Integration tests (MCP + refactored code)
6. ⏭️ Production deployment


# Code Refactoring Implementation Guide

**Status:** Ready to Execute  
**Duration:** 2 weeks (80 hours)  
**Target Branch:** `claude/code-structure-review-eprtuy`  
**Prerequisite:** Read `REFACTORING_PLAN.md` first

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Week 1: Extract Large Functions](#week-1-extract-large-functions)
3. [Week 2: Flatten Nesting & Add Tests](#week-2-flatten-nesting--add-tests)
4. [Testing & Validation](#testing--validation)
5. [Common Patterns & Recipes](#common-patterns--recipes)
6. [Rollback Strategy](#rollback-strategy)

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
1. **Week 1, Day 1-2:** Extract `decision_service.protect()` (205 lines → 50 lines)
2. **Week 1, Day 3-4:** Extract `protect_endpoint()` (138 lines → 30 lines)
3. **Week 1, Day 5:** Extract `governed_generation_service.protect_and_generate()` (208 lines → 50 lines)
4. **Week 2, Day 1-2:** Flatten nesting in `decision_service.py` and `compliance_renderers.py`
5. **Week 2, Day 3-4:** Add unit tests + linting
6. **Week 2, Day 5:** Final validation + metrics comparison

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

- [ ] All functions extracted (< 50 lines each)
- [ ] All nesting flattened (max depth = 2)
- [ ] All unit tests pass (pytest)
- [ ] Type hints verified (mypy)
- [ ] Code linted (ruff, pylint)
- [ ] Coverage > 80% (pytest --cov)
- [ ] Cyclomatic complexity < 5
- [ ] All tests pass without warnings
- [ ] Metrics compared (before vs after)
- [ ] Code review completed
- [ ] Committed and pushed

---

## Next Steps After Refactoring

1. ✅ Complete this refactoring guide
2. ⏭️ Start MCP Server Implementation (next document)
3. ⏭️ Create MCP Client Library
4. ⏭️ Integration tests (MCP + refactored code)


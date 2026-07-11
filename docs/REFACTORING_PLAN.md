# Code Refactoring Plan: Hygiene & Separation of Concerns

**Document Version**: 1.0  
**Target**: `multimodel-policy-mgmt` Backend (Python)  
**Goal**: Improve maintainability, testability, and code readability

---

## Executive Summary

The codebase has **significant hygiene issues**:
- **12 functions exceed 100 lines** (hard to test, hard to reason about)
- **8+ functions have 4-5 levels of nesting** (logic buried, untestable blocks)
- **5 services mix multiple responsibilities** (violates Single Responsibility Principle)
- **4 duplicate patterns** (maintenance nightmare—bugs replicate across 3 reporters)

This plan provides a **prioritized, phased approach** to refactor the codebase systematically.

---

## Part 1: Why Nesting Depth Should Be Maximum 2

### The Problem: Deep Nesting (4-6 levels)

**High nesting creates cognitive load:**

```python
# BAD: 6 levels of nesting (actual code from compliance_renderers.py)
elif 'NIST AI RMF' in framework:
    writer.writerow([...])
    for func in report_dict.get('functions', []):        # Level 1: for loop
        categories = func.get('categories', [])
        cat_evidence = []
        for cat in categories:                            # Level 2: for loop
            cat_name = cat.get('name', cat.get('category', 'Unknown'))
            evidence_data = cat.get('evidence', [])
            if isinstance(evidence_data, list) and evidence_data:  # Level 3: if
                for ev in evidence_data[:2]:             # Level 4: for loop
                    if isinstance(ev, dict):             # Level 5: if
                        ev_type = ev.get('type', 'unknown')
                        if ev_type in ['detection', 'monitoring']:  # Level 6: if
                            cat_evidence.append({...})
```

**Why is this bad?**

1. **Hard to test**: Which branch path are you testing? 6 nested conditions = 2^6 = 64 possible paths
2. **Hard to reason about**: Reader must hold 6 levels of context in memory simultaneously
3. **Easy to break**: Changing one condition affects all nested logic below
4. **Cannot reuse**: The deeply-nested logic is trapped inside 6 indentation levels

---

### The Solution: Maximum 2 Levels of Nesting

**Why 2 is the magic number:**

| Nesting Depth | Paths | Testability | Readability | Brain Load |
|---------------|-------|-------------|-------------|-----------|
| 1 (linear)    | 1     | ✅ Perfect  | ✅ Perfect  | 1 concept |
| 2 (one check) | 4     | ✅ Good     | ✅ Good     | 2 concepts |
| 3             | 8     | ⚠️ Okay     | ⚠️ Okay     | 3 concepts |
| 4+            | 16+   | ❌ Bad      | ❌ Bad      | Too much  |

**Maximum 2 levels means:**
- ✅ Easy to understand at a glance
- ✅ Each function tests one thing
- ✅ Early returns and guards prevent nesting
- ✅ Logic is extracted into named helper functions

---

### Pattern 1: Extract Early Returns (Depth 3→1)

**Before (3 levels):**
```python
def protect(input_text: str, policy_id: str) -> Decision:
    request_log = self._log_request(input_text, policy_id)
    policy = self.repo.get_policy(policy_id)
    if policy:
        pii_violations = self._check_pii_rules(input_text, policy)
        if not pii_violations:
            risk = self._compute_risk(input_text, policy)
            if risk < policy.threshold:
                decision = Decision.ALLOW
            else:
                decision = Decision.BLOCK
        else:
            decision = Decision.BLOCK
    else:
        raise PolicyNotFound(policy_id)
    return decision
```

**After (2 levels with early returns):**
```python
def protect(input_text: str, policy_id: str) -> Decision:
    request_log = self._log_request(input_text, policy_id)
    policy = self.repo.get_policy(policy_id)
    
    # Early return on invalid state
    if not policy:
        raise PolicyNotFound(policy_id)
    
    # Check violations
    pii_violations = self._check_pii_rules(input_text, policy)
    if pii_violations:
        return Decision.BLOCK
    
    # Compute risk
    risk = self._compute_risk(input_text, policy)
    if risk >= policy.threshold:
        return Decision.BLOCK
    
    return Decision.ALLOW
```

**Benefits:**
- ✅ Flat structure—no nesting pyramid
- ✅ Each condition is at depth 1 (easy to test)
- ✅ Early exits mean no trailing `else` blocks
- ✅ Can unit test each decision path in ~2 lines

---

### Pattern 2: Extract to Helper Functions (Depth 6→2)

**Before (6 levels in CSV rendering):**
```python
# Inside compliance_renderers.py (137 lines, deeply nested)
elif 'NIST AI RMF' in framework:
    writer.writerow([...])
    for func in report_dict.get('functions', []):
        categories = func.get('categories', [])
        cat_evidence = []
        for cat in categories:
            cat_name = cat.get('name', cat.get('category', 'Unknown'))
            evidence_data = cat.get('evidence', [])
            if isinstance(evidence_data, list) and evidence_data:
                for ev in evidence_data[:2]:
                    if isinstance(ev, dict):
                        ev_type = ev.get('type', 'unknown')
                        if ev_type in ['detection', 'monitoring']:
                            cat_evidence.append({...})
```

**After (2 levels with extraction):**
```python
def _render_framework_csv(self, framework: str, report_dict: dict, writer):
    """Top-level orchestrator—no business logic, just delegation."""
    rows = self._extract_rows(report_dict, framework)
    for row in rows:
        writer.writerow(row)

def _extract_rows(self, report_dict: dict, framework: str) -> List[List[str]]:
    """Collect all rows from report—one level of iteration."""
    rows = []
    for item in report_dict.get('items', []):
        evidence = self._collect_evidence(item)
        rows.append(self._format_row(item, evidence))
    return rows

def _collect_evidence(self, item: dict) -> List[dict]:
    """Collect evidence from categories—no nesting."""
    evidence = []
    for category in item.get('categories', []):
        evidence.extend(self._get_category_evidence(category))
    return evidence

def _get_category_evidence(self, category: dict) -> List[dict]:
    """Extract evidence from ONE category—simple, testable."""
    evidence_data = category.get('evidence', [])
    
    if not isinstance(evidence_data, list):
        return []
    
    valid_evidence = []
    for evidence in evidence_data[:2]:
        if self._is_valid_evidence(evidence):
            valid_evidence.append(evidence)
    
    return valid_evidence

def _is_valid_evidence(self, evidence: dict) -> bool:
    """Check single evidence validity—pure function."""
    if not isinstance(evidence, dict):
        return False
    
    ev_type = evidence.get('type', 'unknown')
    return ev_type in ['detection', 'monitoring']
```

**Benefits:**
- ✅ Main function is 2 lines—easy to understand
- ✅ Each helper is 5-10 lines—easy to test
- ✅ Each function has ONE job (Single Responsibility)
- ✅ Can unit test `_is_valid_evidence()` with 5 test cases in ~20 lines
- ✅ Reusable—`_collect_evidence()` works for any report type

---

### Pattern 3: Use Guards to Exit Early (Depth 3→1)

**Before (3 levels of if-else chains):**
```python
def detect_pii_violations(self, text: str, policy: Policy) -> List[Violation]:
    violations = []
    if policy.pii_rules:
        pii_markers = detect_pii_like(text)
        if pii_markers:
            for marker in pii_markers:
                rule_matched = False
                for rule_key, rule_config in policy.pii_rules.items():
                    if matches_rule(marker, rule_key):
                        rule_matched = True
                        break
                if rule_matched:
                    violations.append(Violation(marker, rule_key))
    return violations
```

**After (1-2 levels with guards):**
```python
def detect_pii_violations(self, text: str, policy: Policy) -> List[Violation]:
    # Guard: No PII rules defined
    if not policy.pii_rules:
        return []
    
    pii_markers = detect_pii_like(text)
    
    # Guard: No PII detected
    if not pii_markers:
        return []
    
    # Simple loop—no nesting
    violations = []
    for marker in pii_markers:
        rule_key = self._find_matching_rule(marker, policy.pii_rules)
        if rule_key:
            violations.append(Violation(marker, rule_key))
    
    return violations

def _find_matching_rule(self, marker: str, rules: dict) -> Optional[str]:
    """Find first rule key that matches marker—pure, testable."""
    for rule_key in rules.keys():
        if matches_rule(marker, rule_key):
            return rule_key
    return None
```

**Benefits:**
- ✅ Flat structure—guards exit early
- ✅ Main loop has NO nesting
- ✅ `_find_matching_rule()` is testable in isolation
- ✅ Obvious intent: "guard against empty rules, then process"

---

## Part 2: Separation of Concerns Principles

### Single Responsibility Principle (SRP)

**One function = One reason to change.**

| Function | Should Handle | Should NOT |
|----------|---------------|-----------|
| `decision_service.protect()` | Orchestration | PII checking, risk computation |
| `_check_pii_violations()` | Only PII logic | Risk scoring, logging |
| `_compute_risk_score()` | Only risk logic | PII checking, decision making |
| `audit_repo.log_decision()` | Only database write | Computing the decision |

**Bad (mixed concerns):**
```python
def protect(text, policy):
    # Concern 1: Logging
    req = RequestLog(...)
    self.session.add(req)
    
    # Concern 2: PII detection
    if "email" in text:
        violations.append(...)
    
    # Concern 3: Risk computation
    risk = self.risk_engine.compute(text)
    
    # Concern 4: Decision making
    if risk > threshold:
        return Decision.BLOCK
    
    # Concern 5: Logging decision
    self.session.add(DecisionLog(...))
    return Decision.ALLOW
```

**Good (separated concerns):**
```python
def protect(text, policy):
    req_log = self._log_request(text, policy)
    violations = self._check_pii(text, policy)
    risk = self._compute_risk(text, policy)
    decision = self._make_decision(policy, risk, violations)
    self._log_decision(req_log, decision)
    return decision
```

Each helper function has ONE concern:
- `_log_request()` → Request persistence
- `_check_pii()` → PII detection only
- `_compute_risk()` → Risk calculation only
- `_make_decision()` → Decision logic only
- `_log_decision()` → Decision persistence

---

## Part 3: Refactoring Roadmap (4 Phases)

### PHASE 1: Extract Giant Functions (Week 1)

**Target**: Functions > 100 lines

| File | Function | Lines | Action |
|------|----------|-------|--------|
| `decision_service.py` | `protect()` | 205 | Extract to 5 helpers |
| `governed_generation_service.py` | `protect_and_generate()` | 208 | Extract to 6 helpers |
| `compliance_renderers.py` | `compliance_to_html()` | 506 | Break into template builders |
| `compliance_renderers.py` | `compliance_to_csv()` | 137 | Extract CSV logic |
| `protect.py` | `protect_endpoint()` | 138 | Extract 3 helper functions |

**Effort**: ~20 hours  
**Outcome**: All functions < 50 lines; each testable in isolation

---

### PHASE 2: Flatten Nesting (Week 1-2)

**Target**: All functions with 3+ nesting levels

**Strategy:**
1. Add guard clauses (early return)
2. Extract nested loops to helpers
3. Invert conditionals (guard against failure, then process)

**Files to refactor:**
- `decision_service.py` (lines 186-218): PII rule checking
- `compliance_renderers.py` (lines 73-102): CSV data aggregation
- `governed_generation_service.py` (lines 155-208): Safety evaluation
- `risk_engine.py` (lines 167-194): Scoring logic

**Effort**: ~12 hours  
**Outcome**: Max nesting depth = 2 across entire codebase

---

### PHASE 3: Eliminate Duplication (Week 2)

**Target**: 4 duplicate patterns

#### 3a. Create Base Reporter Class
```python
# backend/app/services/reports/base_reporter.py

class BaseComplianceReporter(ABC):
    def assess_section(self, policy, config, field_checks, from_date, to_date):
        """Generic assessment—used by all reporters."""
        evidence = []
        gaps = []
        
        for check in field_checks:
            if config.get(check.key):
                evidence.append(self._find_evidence(check))
            else:
                gaps.append(check.gap_message)
        
        return SectionEvidence(evidence, gaps)
```

**Refactor:**
- `eu_ai_act_reporter.py` → Inherit from `BaseComplianceReporter`
- `nist_ai_rmf_reporter.py` → Inherit from `BaseComplianceReporter`
- `nist_privacy_reporter.py` → Inherit from `BaseComplianceReporter`

**Effort**: ~6 hours  
**Outcome**: Single source of truth for assessment logic

#### 3b. Extract CSV Rendering
```python
# backend/app/services/reports/csv_renderer.py

class CSVRenderer:
    def render(self, framework: str, report_dict: dict, writer):
        rows = self._extract_rows(report_dict, framework)
        for row in rows:
            writer.writerow(row)
    
    def _extract_rows(self, report_dict, framework):
        # Reusable for ALL frameworks
        ...
```

**Refactor:**
- EU AI Act CSV → Use `CSVRenderer`
- NIST AI RMF CSV → Use `CSVRenderer`
- NIST Privacy CSV → Use `CSVRenderer`

**Effort**: ~6 hours  
**Outcome**: Zero code duplication; fixes apply to all frameworks

---

### PHASE 4: Establish Standards & Testing (Week 3-4)

#### 4a. Create `CONTRIBUTING.md` with Standards
```markdown
# Code Hygiene Standards

## Function Size
- Max 30 lines for business logic
- Max 50 lines for orchestration

## Nesting
- Max 2 levels (3 is emergency only)

## Naming
- No single-letter vars except i,j,k in loops
- No abbreviations: `meta` → `request_metadata`
- Consistent within function

## Constants
- All magic numbers → constants.py
- All decision strings → DecisionReasons enum
```

#### 4b. Add Linting Rules
```python
# pyproject.toml

[tool.ruff]
max-line-length = 100
select = ["E", "F", "W"]

[tool.pylint]
max-attributes = 7
max-locals = 15
max-returns = 6
max-statements = 50

[tool.radon]
exclude = "tests"
complexity_threshold = 5  # Fail if any function > complexity 5
mi_threshold = 75         # Fail if maintainability index < 75
```

#### 4c. Add Unit Tests
```python
# backend/tests/test_decision_service.py

def test_protect_with_pii_violations_blocks():
    """Test PII violations trigger BLOCK decision."""
    policy = Policy(pii_rules={"email": {...}})
    result = service.protect("my email is test@example.com", policy)
    assert result == Decision.BLOCK

def test_protect_with_high_risk_blocks():
    """Test risk scoring triggers BLOCK."""
    policy = Policy(risk_threshold=50)
    result = service.protect("bomb threat", policy)
    assert result.risk > 50
    assert result == Decision.BLOCK

def test_protect_with_low_risk_allows():
    """Test low-risk content is allowed."""
    policy = Policy(risk_threshold=50)
    result = service.protect("hello world", policy)
    assert result.risk < 50
    assert result == Decision.ALLOW
```

**Effort**: ~15 hours  
**Outcome**: Test coverage > 80%; automated linting prevents regressions

---

## Part 4: Implementation Checklist

### Week 1: Extract & Flatten

- [ ] Extract `decision_service.protect()` into 5 functions
  - [ ] `_log_request()`
  - [ ] `_load_policy()`
  - [ ] `_check_pii_rules()`
  - [ ] `_compute_risk()`
  - [ ] `_make_decision()`
- [ ] Flatten PII checking logic (decision_service.py:186-218)
- [ ] Extract `protect_endpoint()` into 3 functions
  - [ ] `validate_tenant()`
  - [ ] `resolve_policy()`
  - [ ] `resolve_evidence()`
- [ ] Flatten compliance CSV rendering (compliance_renderers.py)

**Testing after each change:**
```bash
pytest backend/tests/ -v
pytest backend/tests/ --cov=backend/app
```

### Week 2: Eliminate Duplication

- [ ] Create `backend/app/services/reports/base_reporter.py`
- [ ] Refactor `eu_ai_act_reporter.py` to inherit from base
- [ ] Refactor `nist_ai_rmf_reporter.py` to inherit from base
- [ ] Refactor `nist_privacy_reporter.py` to inherit from base
- [ ] Create `backend/app/services/reports/csv_renderer.py`
- [ ] Update all CSV rendering to use `CSVRenderer`

**Verification:**
```bash
radon mi backend/app/services/reports/  # Maintainability index
radon cc backend/app/services/reports/  # Cyclomatic complexity
```

### Week 3: Standards & Testing

- [ ] Create `CONTRIBUTING.md` with code standards
- [ ] Add `backend/app/core/constants.py` with all magic numbers
  - [ ] `RiskScoringWeights` (weapon=40, incitement=50, etc.)
  - [ ] `ComplianceThresholds` (required_fields=3, etc.)
  - [ ] `DecisionReasons` (enums for decision strings)
- [ ] Update `pyproject.toml` with linting rules
- [ ] Add pre-commit hooks for `ruff`, `pylint`, `radon`
- [ ] Write unit tests for extracted functions (~50 tests total)

**Verify code quality:**
```bash
ruff check backend/app/
pylint backend/app/ --exit-zero  # For reporting only
radon cc backend/app/ -a         # Average complexity
radon mi backend/app/            # Maintainability index (target > 75)
pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

### Week 4: Cleanup & Documentation

- [ ] Update `ARCHITECTURE.md` with new patterns
- [ ] Add docstrings to all public functions
- [ ] Update API docs (`/backend/app/main.py`)
- [ ] Run full test suite
- [ ] Test in browser: Start frontend, hit all endpoints
- [ ] Final linting pass

---

## Part 5: Before/After Example: `decision_service.protect()`

### BEFORE (205 lines, mixed concerns, hard to test)

```python
def protect(
    self, 
    input_text: str, 
    policy_id: Optional[int] = None,
    evidence_ids: Optional[list[int]] = None,
    tenant_id: Optional[int] = None
) -> ProtectResponse:
    """Main orchestrator with embedded business logic."""
    
    # Lines 153-163: Request logging
    request_log = RequestLog(
        timestamp=datetime.utcnow(),
        input_text=input_text,
        input_hash=sha256_text(input_text),
        policy_id=policy_id,
        tenant_id=tenant_id
    )
    self.audit_repo.log_request(request_log)
    
    # Lines 166-180: Policy loading + fallback
    if policy_id:
        policy_doc = self.policy_repo.get_policy(policy_id)
    else:
        policy_doc = self.policy_repo.get_default_policy(tenant_id)
    
    if not policy_doc:
        raise PolicyNotFound(f"Policy {policy_id} not found")
    
    # Lines 186-218: PII enforcement (5 levels of nesting!)
    if policy_doc.pii_rules:
        pii_markers = detect_pii_like(input_text)
        if pii_markers:
            for marker in pii_markers:
                pii_type = marker.replace("_like", "").replace("_", "")
                for rule_key, rule_config in policy_doc.pii_rules.items():
                    if rule_key.lower() in pii_type.lower() or pii_type.lower() in rule_key.lower():
                        if isinstance(rule_config, dict):
                            action = rule_config.get('action', 'detect')
                            enabled = rule_config.get('enabled', True)
                            if enabled:
                                if action == 'block':
                                    return ProtectResponse(allowed=False, reason="pii_detected")
    
    # Lines 220-241: Risk computation
    risk_score = self.risk_engine.compute_risk(
        input_text=input_text,
        policy_doc=policy_doc,
        evidence_ids=evidence_ids
    )
    
    # Lines 254-260: Conservative mode
    if policy_doc.conservative_mode and risk_score > policy_doc.warning_threshold:
        return ProtectResponse(allowed=False, reason="risk_above_threshold")
    
    # Lines 263-287: Decision logging (mixed with decision logic)
    decision = risk_score <= policy_doc.risk_threshold
    
    decision_log = DecisionLog(
        request_log_id=request_log.id,
        allowed=decision,
        risk_score=risk_score,
        policy_id=policy_id,
        reasons=["pii_detected"] if pii_markers else ["risk_score"]
    )
    self.audit_repo.log_decision(decision_log)
    
    return ProtectResponse(
        allowed=decision,
        risk_score=risk_score,
        decision_id=decision_log.id
    )
```

**Problems:**
- ❌ 205 lines: Can't test individual parts
- ❌ 5 levels of nesting in PII logic: Impossible to understand
- ❌ Mixed concerns: Logging, PII, risk, decision all together
- ❌ Hard to extend: Adding new decision logic requires touching entire function
- ❌ No reusability: Logic is buried

---

### AFTER (50 lines + 8 small helpers = cleaner, testable, maintainable)

```python
def protect(
    self, 
    input_text: str, 
    policy_id: Optional[int] = None,
    evidence_ids: Optional[list[int]] = None,
    tenant_id: Optional[int] = None
) -> ProtectResponse:
    """Orchestrate all protection checks."""
    request_log = self._log_request(input_text, policy_id, tenant_id)
    policy = self._load_policy(policy_id, tenant_id)
    pii_violations = self._check_pii_rules(input_text, policy)
    risk = self._compute_risk(input_text, policy, evidence_ids)
    decision = self._make_decision(policy, risk, pii_violations)
    decision_log = self._log_decision(request_log, policy, risk, pii_violations, decision)
    
    return ProtectResponse(
        allowed=decision.allowed,
        risk_score=risk.score,
        decision_id=decision_log.id,
        reasons=decision.reasons
    )

# Each helper: 5-20 lines, ONE job, TESTABLE

def _log_request(self, text: str, policy_id, tenant_id) -> RequestLog:
    """Log incoming request."""
    return self.audit_repo.log_request(
        tenant_id=tenant_id,
        input_text=text,
        policy_id=policy_id,
        input_hash=sha256_text(text)
    )

def _load_policy(self, policy_id: Optional[int], tenant_id: Optional[int]) -> Policy:
    """Load policy, fallback to default."""
    if policy_id:
        policy = self.policy_repo.get_policy(policy_id)
    else:
        policy = self.policy_repo.get_default_policy(tenant_id)
    
    if not policy:
        raise PolicyNotFound(policy_id or tenant_id)
    
    return policy

def _check_pii_rules(self, text: str, policy: Policy) -> List[PiiViolation]:
    """Check PII violations (NO NESTING)."""
    # Guard: No PII rules
    if not policy.pii_rules:
        return []
    
    # Guard: No PII detected
    pii_markers = detect_pii_like(text)
    if not pii_markers:
        return []
    
    # Simple loop—ONE level
    violations = []
    for marker in pii_markers:
        rule_key = self._find_matching_rule(marker, policy.pii_rules)
        if rule_key:
            violations.append(PiiViolation(marker, rule_key))
    
    return violations

def _find_matching_rule(self, marker: str, rules: dict) -> Optional[str]:
    """Find first matching rule (PURE FUNCTION)."""
    for rule_key in rules.keys():
        if self._rule_matches_marker(marker, rule_key):
            return rule_key
    return None

def _rule_matches_marker(self, marker: str, rule_key: str) -> bool:
    """Check if marker matches rule key."""
    pii_type = marker.replace("_like", "").replace("_", "")
    return (rule_key.lower() in pii_type.lower() or 
            pii_type.lower() in rule_key.lower())

def _compute_risk(self, text: str, policy: Policy, evidence_ids) -> RiskScore:
    """Compute risk score."""
    return self.risk_engine.compute_risk(
        input_text=text,
        policy_doc=policy,
        evidence_ids=evidence_ids
    )

def _make_decision(self, policy: Policy, risk: RiskScore, 
                   violations: List[PiiViolation]) -> Decision:
    """Make allow/block/review decision (PURE)."""
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

def _log_decision(self, req_log: RequestLog, policy: Policy, risk: RiskScore,
                  violations: List[PiiViolation], decision: Decision) -> DecisionLog:
    """Log decision for audit trail."""
    return self.audit_repo.log_decision(
        tenant_id=req_log.tenant_id,
        request_log_id=req_log.id,
        allowed=decision.allowed,
        reasons=decision.reasons,
        risk_score=risk.score,
        policy_id=policy.id
    )
```

**Benefits:**
- ✅ Main function: 10 lines—instantly clear
- ✅ Each helper: 5-20 lines—easy to test
- ✅ No nesting: Max depth = 2 (in `_check_pii_rules`)
- ✅ One responsibility per function
- ✅ Reusable: `_find_matching_rule()` can be used elsewhere
- ✅ Testable: Can test `_make_decision()` with 5 unit tests (~25 lines total)

**Unit tests (compare to original—impossible to test):**
```python
def test_pii_violations_block():
    policy = Policy(pii_rules={"email": {...}}, pii_block_enabled=True)
    decision = service._make_decision(policy, risk=RiskScore(10), 
                                      violations=[PiiViolation(...)])
    assert not decision.allowed
    assert "pii_detected" in decision.reasons

def test_high_risk_blocks():
    policy = Policy(risk_threshold=50)
    decision = service._make_decision(policy, risk=RiskScore(75), violations=[])
    assert not decision.allowed

def test_low_risk_allows():
    policy = Policy(risk_threshold=50)
    decision = service._make_decision(policy, risk=RiskScore(25), violations=[])
    assert decision.allowed
```

---

## Part 6: Success Metrics

Track these metrics **before and after** refactoring:

| Metric | Before | After | Tool |
|--------|--------|-------|------|
| **Avg function size** | 75 lines | 25 lines | `radon mi` |
| **Max nesting depth** | 6 | 2 | `radon cc` |
| **Cyclomatic complexity** | 8-12 | 3-5 | `radon cc` |
| **Unit test coverage** | ~40% | >80% | `pytest --cov` |
| **Duplicate code** | 4 patterns | 0 | `pylint --duplicate-code-check` |
| **Maintainability Index** | ~65 | >80 | `radon mi` |

**Run measurements:**
```bash
# Before refactoring
radon mi backend/app/services/ -j > metrics_before.json
radon cc backend/app/services/ -a -j >> metrics_before.json
pytest backend/tests/ --cov=backend/app --cov-report=json

# After refactoring
radon mi backend/app/services/ -j > metrics_after.json
radon cc backend/app/services/ -a -j >> metrics_after.json
pytest backend/tests/ --cov=backend/app --cov-report=json

# Compare
diff metrics_before.json metrics_after.json
```

---

## Part 7: FAQ

### Q: Why extract functions instead of leaving them inline?

**A:** Extracting functions enables:
- **Testability**: Test `_make_decision()` without database calls
- **Reusability**: `_find_matching_rule()` used in multiple places
- **Clarity**: Function names document intent (`_check_pii_rules` is clearer than 30 lines of nested logic)
- **Changeability**: Update decision logic in ONE place, not three

### Q: Won't extracting functions slow down the code?

**A:** No. Function calls are negligible overhead. Benefits far outweigh cost:
- Clearer code → fewer bugs
- Easier testing → higher confidence
- Better separation → easier to optimize specific functions if needed

### Q: Should I extract functions even if they're only called once?

**A:** Yes, if they:
- Exceed 20 lines
- Have multiple responsibilities
- Contain complex logic

Example: `_check_pii_rules()` is only called from `protect()`, but extracting it:
- Reduces main function to 10 lines
- Makes PII logic testable
- Enables future reuse (e.g., audit reports)

### Q: How do I know if a function is too nested?

**A:** Count indentation levels:
```python
def func():                    # Level 0
    if condition:              # Level 1 ✅
        if nested:             # Level 2 ✅
            if more_nested:    # Level 3 ⚠️ (emergency only)
                if deep:       # Level 4 ❌ EXTRACT!
```

Use guards and early returns to stay at level 2.

---

## Summary

**This plan transforms the codebase from:**
- ❌ 205-line functions with 6-level nesting
- ❌ Mixed concerns (logging, PII, risk, decision all together)
- ❌ Duplicate reporter patterns
- ❌ Hard to test, hard to change

**To:**
- ✅ 20-50 line functions with max 2-level nesting
- ✅ Clear separation: each function does ONE thing
- ✅ Single source of truth (base classes, helpers)
- ✅ Easily testable, easy to change
- ✅ Test coverage > 80%

**Investment:**
- 4 weeks of focused refactoring
- ~60 hours of work
- Long-term payoff: 50% faster feature development, fewer bugs

**Next step:** Begin PHASE 1 (Week 1) by extracting `decision_service.protect()` into 5 functions.


# Engineering Constitution

This document defines non-negotiable engineering standards for this repository. It applies to all code, tests, and tooling.

## 1) Architecture layers
- Presentation (API/UI)
  - Purpose: transport, authentication, authorization, request/response mapping.
  - May depend on: Application.
  - Must not depend on: Infrastructure directly, data stores, third-party SDKs.
- Application (Use Cases / Services)
  - Purpose: orchestrate use cases, transactions, cross-aggregate workflows.
  - May depend on: Domain, Ports (interfaces) defined in Domain, and abstractions of Infrastructure via ports.
  - Must not contain: persistence details, HTTP objects, framework-specific types.
- Domain (Core Model)
  - Purpose: entities, value objects, domain services, domain errors, invariants.
  - May depend on: standard library only.
  - Must have no knowledge of frameworks or I/O.
- Infrastructure (Adapters)
  - Purpose: implement ports (repositories, external services, messaging, cache, file system), migrations.
  - May depend on: Domain and third-party libraries.
  - Must be replaceable via DI without touching Domain or Application.
- Cross-cutting
  - Logging, configuration, validation, error mapping, observability, DI wiring.

Allowed dependency direction:
Presentation → Application → Domain
Infrastructure → Domain (implements ports) and is invoked by Application through ports.

## 2) Folder boundaries
Top-level layout (Python-oriented; adapt names if using another language):
- src/
  - presentation/            # API routers/controllers, serializers, request/response models
  - application/             # use_case services, transactions, coordinators
  - domain/                  # entities, value_objects, domain_services, ports (interfaces), domain_errors
  - infrastructure/          # adapters: repositories, clients, gateways, orm, queues, cache
  - crosscutting/            # logging, config, validation, error mapping, DI container
- tests/
  - unit/
  - integration/
  - api/

Import rules:
- presentation can import application-only.
- application can import domain and domain.ports; it consumes infrastructure only via DI on ports.
- domain imports nothing from other layers.
- infrastructure may import domain to implement ports but must not be imported by presentation.

Enforcement:
- Use static checks (import-linter/layer-contracts) and CI to reject forbidden imports.

## 3) Dependency Injection (DI) rules
- Injection style: constructor/function injection preferred. No global service locators.
- Lifetimes:
  - Request-scoped: use case services, repositories, clients.
  - App-scoped singletons: configuration, logger factory, DI container.
- Wiring:
  - Infrastructure implements domain ports (protocols/abstract base classes).
  - Application depends on ports; concrete adapters are bound in DI at composition root.
- Prohibitions:
  - No inline construction of concrete adapters inside business logic.
  - No optional backdoor imports that bypass ports.

Minimal Python example (complete and runnable excerpt):

```python
# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class PolicyRepo(ABC):
    @abstractmethod
    def get(self, policy_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("PolicyRepo.get must be implemented by an adapter")

# src/domain/errors.py
class PolicyNotFound(Exception):
    def __init__(self, policy_id: str):
        super().__init__(f"POLICY_NOT_FOUND:{policy_id}")
        self.policy_id = policy_id

# src/application/use_cases.py
from typing import Dict, Any

class GetPolicy:
    def __init__(self, repo: PolicyRepo):
        self._repo = repo
    def execute(self, policy_id: str) -> Dict[str, Any]:
        policy = self._repo.get(policy_id)
        if not policy:
            raise PolicyNotFound(policy_id)
        return policy

# src/infrastructure/repositories.py
from typing import Optional, Dict, Any

class InMemoryPolicyRepo(PolicyRepo):
    def __init__(self, store: Optional[Dict[str, Dict[str, Any]]] = None):
        self._store = store or {}
    def get(self, policy_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(policy_id)

# src/crosscutting/container.py
class Container:
    def __init__(self):
        self.repo = InMemoryPolicyRepo({"P1": {"id": "P1", "name": "Default"}})
    def get_policy_use_case(self) -> GetPolicy:
        return GetPolicy(self.repo)
```

## 4) Strict rule for routes
- API routes must not contain business logic. They may:
  - Parse/validate input, authorize, call a single use case, map errors to transport responses.
  - They must not perform domain calculations, persistence, or multi-step orchestration.

Example route delegating only (FastAPI-style):

```python
# src/presentation/routes.py
from fastapi import APIRouter, HTTPException
from crosscutting.container import Container
from domain.errors import PolicyNotFound

router = APIRouter()
container = Container()

@router.get("/policies/{policy_id}")
def get_policy(policy_id: str):
    try:
        use_case = container.get_policy_use_case()
        return use_case.execute(policy_id)
    except PolicyNotFound:
        raise HTTPException(status_code=404, detail="Policy not found")
```

## 5) Testing pyramid
- Goals:
  - Optimize for many fast unit tests, fewer integration tests, and few API tests.
- Targets (guidelines):
  - Unit: 70–80% of total tests, cover domain and application logic with pure functions/objects, no I/O.
  - Integration: 15–25%, cover adapters with real infrastructure or containers (DB, cache, queues).
  - API/E2E: ≤10%, exercise happy paths and critical error mappings through HTTP.
- Rules:
  - Unit tests must not hit network, file system, or sleep.
  - Integration tests must isolate state (unique schemas, containers, or fixtures) and be parallel-safe.
  - API tests focus on contract and mapping; avoid reproducing unit/integration coverage.
- Structure:
  - tests/unit/... mirrors src/domain and src/application
  - tests/integration/... mirrors src/infrastructure
  - tests/api/... targets presentation endpoints

## 6) Naming conventions
- Files and modules: snake_case (e.g., policy_service.py, policy_repo.py).
- Packages/directories: snake_case.
- Classes: PascalCase (Policy, PolicyService, InMemoryPolicyRepo).
- Functions/methods/variables: snake_case.
- Constants: UPPER_SNAKE_CASE.
- Interfaces/ports: descriptive ABC names (PolicyRepo, PaymentGateway).
- Test files: test_<module>.py; test names describe behavior: test_returns_404_when_policy_missing.
- Branches: feature/<slug>, fix/<slug>, chore/<slug>.

## 7) Error handling
- Domain errors: typed exceptions defined in domain; never return raw infrastructure exceptions outside infrastructure.
- Mapping:
  - Application raises domain errors; Presentation translates to HTTP status codes and problem details.
  - 400: validation errors; 401/403: auth; 404: missing resources; 409: conflicts; 422: domain rule violations; 500: unexpected.
- Retries:
  - Only in infrastructure for idempotent operations with exponential backoff and jitter.
- Idempotency:
  - Use idempotency keys for externally observable state changes when applicable.
- Never swallow exceptions silently; log with context then propagate or map.

Minimal error mapping example:

```python
# src/presentation/error_mapping.py
from fastapi import HTTPException
from domain.errors import PolicyNotFound

def map_error(err: Exception):
    if isinstance(err, PolicyNotFound):
        raise HTTPException(404, "Policy not found")
    raise err
```

## 8) Logging
- Style: structured logging (key-value), JSON preferred in production.
- Levels: DEBUG (dev only), INFO (lifecycle, major actions), WARNING (recoverable anomalies), ERROR (failed operations), CRITICAL (service unusable).
- Content:
  - Include correlation/request IDs, user/tenant IDs, operation names, latency, and key parameters.
  - Never log secrets, credentials, tokens, or sensitive PII.
- Context propagation:
  - Pass context explicitly or via framework facilities; avoid mutable globals.
- Sampling:
  - Enable debug sampling in high-volume paths; full logs for errors.

Minimal Python logger setup (stdlib):

```python
# src/crosscutting/logging_setup.py
import json
import logging
import sys

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        # include extra fields if present (e.g., correlation_id)
        for key, value in record.__dict__.items():
            if key not in {
                "name","msg","args","levelname","levelno","pathname","filename","module",
                "exc_info","exc_text","stack_info","lineno","funcName","created","msecs",
                "relativeCreated","thread","threadName","processName","process"
            }:
                payload[key] = value
        return json.dumps(payload)

logger = logging.getLogger("app")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

# usage example:
# logger.info("policy.fetched", extra={"policy_id": "P1", "latency_ms": 12})
```

## 9) Additional rules
- Configuration: Twelve-Factor compatible; environment-driven configuration with safe dev defaults.
- Validation: Validate at the boundary (presentation) and enforce invariants in domain.
- Performance: Measure first; add caches behind ports in infrastructure; keep domain pure.

## 10) Review checklist (PRs)
- [ ] Route handlers contain no business logic; call a single use case.
- [ ] Layer import direction respected; no forbidden imports.
- [ ] DI binds ports to adapters at composition root; no inline construction in business logic.
- [ ] Domain free of framework/I/O; pure, unit-testable logic.
- [ ] Tests follow pyramid; coverage adequate where it matters.
- [ ] Errors mapped correctly; no leaking infra exceptions.
- [ ] Logging is structured and free of secrets.
- [ ] Names follow conventions; files placed in correct folders.

Violation of this constitution requires remediation before merge unless a documented exception is approved by maintainers.

# Multimodel Policy Management (Monorepo)

Monorepo containing a Python FastAPI backend and a React (Vite + TypeScript) frontend for multimodel policy management. Architecture, layering, DI, testing, error handling, and logging follow the principles in [constitution.md](constitution.md).

## Repository structure

- backend/ — FastAPI application, domain/services, repositories, and tests
- frontend/ — Vite + React TypeScript UI
- constitution.md — architectural rules and guidelines

Key backend modules:
- app/core: hashing, patterns, auth, config, logging, errors, DI deps, contracts
- app/services: risk_engine, policy_engine, decision_service, auth_service
- app/db: SQLAlchemy engine/session and Declarative Base
- app/models: tenant, policy, policy_version, evidence_item, request_log, decision_log, risk_score
- app/repos: policy_repo, evidence_repo, audit_repo, tenant_repo
- app/api: router and route modules (protect, policies, evidence, audit)
- app/tools: CLI entry points (run_risk.py, run_policy.py)
- app/main.py: FastAPI app entry

---

## Backend changes since last update

Models
- Portable boolean defaults using server defaults:
  - [`app.models.tenant.Tenant`](backend/app/models/tenant.py)
  - [`app.models.policy.Policy`](backend/app/models/policy.py)
  - [`app.models.policy_version.PolicyVersion`](backend/app/models/policy_version.py)
  - [`app.models.decision_log.DecisionLog`](backend/app/models/decision_log.py)
  - [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py)
- Track in-place JSON mutations via Mutable mappings:
  - [`app.models.evidence_item.EvidenceItem`](backend/app/models/evidence_item.py) metadata uses MutableDict
  - [`app.models.request_log.RequestLog`](backend/app/models/request_log.py) metadata uses MutableDict
  - [`app.models.decision_log.DecisionLog`](backend/app/models/decision_log.py) reasons uses MutableList
  - [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py) reasons uses MutableList
- Integrity constraints and indexes:
  - Version min bound and uniqueness in [`app.models.policy_version.PolicyVersion`](backend/app/models/policy_version.py)
  - Risk score bounds in [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py)
  - Composite index (tenant_id, created_at) in [`app.models.request_log.RequestLog`](backend/app/models/request_log.py)

Repositories
- Regenerated SQLAlchemy adapters with consistent pagination, ordering, and validation:
  - [`app.repos.policy_repo.SqlAlchemyPolicyRepo`](backend/app/repos/policy_repo.py): version auto-increment, activate version
  - [`app.repos.evidence_repo.SqlAlchemyEvidenceRepo`](backend/app/repos/evidence_repo.py): deterministic content_hash and tenant-scoped dedupe
  - [`app.repos.audit_repo.SqlAlchemyAuditRepo`](backend/app/repos/audit_repo.py): request/decision/risk logging and lookups
  - [`app.repos.tenant_repo.SqlAlchemyTenantRepo`](backend/app/repos/tenant_repo.py): slug generation and lookups

Schemas
- Pydantic v1/v2 compatibility and stricter validation:
  - [`app.schemas.policies`](backend/app/schemas/policies.py)
  - [`app.schemas.evidence`](backend/app/schemas/evidence.py)
  - [`app.schemas.protect`](backend/app/schemas/protect.py)
  - [`app.schemas.policy_format.PolicyDoc`](backend/app/schemas/policy_format.py)

Core
- Unified error handling with ValidationError mapping and optional auth error binding:
  - [`app.core.errors`](backend/app/core/errors.py)
- DI helpers for services and repos:
  - [`app.core.deps`](backend/app/core/deps.py)

App entry and tools
- App wiring, CORS, health/version routes:
  - [`app.main`](backend/app/main.py)
- CLI tools:
  - [`app.tools.run_risk`](backend/app/tools/run_risk.py)
  - [`app.tools.run_policy`](backend/app/tools/run_policy.py)

Dev ergonomics
- Make targets for run/test/lint/format: [backend/Makefile](backend/Makefile)
- Backend docs for Make usage: [backend/Makefile.md](backend/Makefile.md)
- Plain-English policy walkthrough: [backend/CreatePolicy.md](backend/CreatePolicy.md)

---

## Bring up the backend independently

Prerequisites
- Python 3.11+
- From repo root or backend/, create and activate a venv:
  - macOS/Linux: `python -m venv backend/.venv && source backend/.venv/bin/activate`
  - Windows (PowerShell): `python -m venv backend\.venv; .\backend\.venv\Scripts\Activate.ps1`
- Install deps:
  - `cd backend && pip install -e .`
  - or `pip install -r requirements.txt`

Environment (optional)
- DATABASE_URL=sqlite:///./app.db
- SQLALCHEMY_ECHO=0
- ALLOW_ORIGINS=*
- APP_VERSION=0.1.0
- API key HMAC secret (choose one): API_KEY_SECRET, AUTH_HMAC_SECRET, SECRET_KEY

Create database tables (no migrations)
- One-time bootstrap:
  - cd backend
  - python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

Run the API
- Using Makefile (recommended):
  - cd backend && make run
- Direct Uvicorn:
  - cd backend && python -m uvicorn app.main:app --reload --port 8000

Verify
- Health: http://localhost:8000/api/health
- Version: http://localhost:8000/api/version
- OpenAPI: http://localhost:8000/docs

Key files:
- Entry: [`app.main`](backend/app/main.py)
- DB session: [`app.db.session`](backend/app/db/session.py)
- Base/models: [`app.db.base`](backend/app/db/base.py)

---

## Creating policies (quick guide)

Use the full walkthrough at [backend/CreatePolicy.md](backend/CreatePolicy.md). Summary below.

1) Create a policy
- POST /api/policies
- Body example:
  {
    "tenant_id": 1,
    "name": "Content Safety",
    "slug": "content-safety",
    "description": "Blocks unsafe words",
    "is_active": true
  }

2) Add a policy version (rules)
- POST /api/policies/{policy_id}/versions
- Body example:
  {
    "policy_id": 123,
    "document": {
      "blocked_terms": ["forbidden", "secret sauce"],
      "allowed_sources": [],
      "required_evidence_types": [],
      "pii_rules": {},
      "risk_threshold": 80
    },
    "is_active": true
  }

3) Activate a version (if not already active)
- POST /api/policies/{policy_id}/versions/{version}/activate

4) Evaluate text with a policy
- POST /api/protect
- Body example:
  {
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "this contains a forbidden word",
    "evidence_types": ["url"]
  }

Related routes:
- Policies API: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
- Protect API: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)

---

## CLI helpers

Evaluate a policy JSON against stdin
- cd backend
- echo "some text" | python -m app.tools.run_policy --policy path/to/policy.json
- Tool: [`app.tools.run_policy`](backend/app/tools/run_policy.py)

Compute risk score for stdin
- cd backend
- echo "text" | python -m app.tools.run_risk --evidence-present
- Tool: [`app.tools.run_risk`](backend/app/tools/run_risk.py)

---

## Running tests (backend)

From repo root or backend/
- All tests: `pytest -q`
- With Makefile: `cd backend && make test`
- With coverage: `pytest -q --cov=app --cov-report=term-missing`

---

## Frontend: setup and run

1) Configure environment
- cd frontend
- Copy .env.example to .env and update:
  - VITE_API_BASE_URL=http://localhost:8000
  - VITE_API_KEY=your-dev-api-key

2) Install and start
- npm install
- npm run dev
- Open http://localhost:5173

---

## Docker Compose (optional)

See the example in this README (earlier section) to run backend and frontend with docker compose.

---

## Troubleshooting

- If the API fails to start, verify env vars and dependencies in backend/.
- If the frontend cannot reach the API, ensure CORS (ALLOW_ORIGINS) and VITE_API_BASE_URL are correct.
- On Windows PowerShell, execution policy may block venv activation; use an elevated shell and set-ExecutionPolicy RemoteSigned if needed.
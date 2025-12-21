# Multimodel Policy Management (Monorepo)

Monorepo with a Python FastAPI backend and a React (Vite + TypeScript) frontend for multimodel policy management. The code follows principles in [constitution.md](constitution.md).

## Repository structure

- backend/ — FastAPI app, domain/services, repos, models, tools, tests
  - App entry: [backend/app/main.py](backend/app/main.py)
  - API router: [backend/app/api/router.py](backend/app/api/router.py)
  - Routes: [backend/app/api/routes](backend/app/api)
  - Core (config, DI, errors, auth): [backend/app/core](backend/app/core)
  - DB base/session: [backend/app/db](backend/app/db)
  - Models: [backend/app/models](backend/app/models)
  - Repos: [backend/app/repos](backend/app/repos)
  - Schemas: [backend/app/schemas](backend/app/schemas)
  - Services: [backend/app/services](backend/app/services)
  - Tools/CLIs: [backend/app/tools](backend/app/tools)
  - Makefile: [backend/Makefile](backend/Makefile)
  - How-to docs:
    - Backend run guide: [backend/Makefile.md](backend/Makefile.md)
    - Policy creation: [backend/CreatePolicy.md](backend/CreatePolicy.md)
    - Deploy & integrate: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)
    - Sample integration app: [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py), [backend/SampleAPPIntegration.md](backend/SampleAPPIntegration.md)
- frontend/ — Vite + React TypeScript UI
- constitution.md — architectural rules and guidelines

---

## Backend changes since last update

Architecture and core
- Unified error responses with ValidationError mapping and optional AuthError handling:
  - [`app.core.errors`](backend/app/core/errors.py)
- DI providers for repos/services:
  - [`app.core.deps.get_decision_service`](backend/app/core/deps.py)

Models
- Versioned policies and decision/audit entities:
  - [`app.models.policy.Policy`](backend/app/models/policy.py)
  - [`app.models.policy_version.PolicyVersion`](backend/app/models/policy_version.py)
  - [`app.models.request_log.RequestLog`](backend/app/models/request_log.py)
  - [`app.models.decision_log.DecisionLog`](backend/app/models/decision_log.py)
  - [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py)
- Policy approval workflow (draft -> approved -> active -> retired):
  - [`app.models.policy_approval.PolicyApproval`](backend/app/models/policy_approval.py)
  - Workflow service: [`app.services.policy_workflow.PolicyWorkflowService`](backend/app/services/policy_workflow.py)

Repositories
- SQLAlchemy adapters with pagination and activation logic:
  - [`app.repos.policy_repo.SqlAlchemyPolicyRepo`](backend/app/repos/policy_repo.py)
  - [`app.repos.evidence_repo.SqlAlchemyEvidenceRepo`](backend/app/repos/evidence_repo.py)
  - [`app.repos.audit_repo.SqlAlchemyAuditRepo`](backend/app/repos/audit_repo.py)
  - [`app.repos.tenant_repo.SqlAlchemyTenantRepo`](backend/app/repos/tenant_repo.py)

Services and engines
- Decision orchestration and engines:
  - [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
  - [`app.services.policy_engine.evaluate_policy`](backend/app/services/policy_engine.py)
  - [`app.services.risk_engine.compute_risk`](backend/app/services/risk_engine.py)
- New components:
  - Tamper-evident ledger: [`app.services.governance_ledger.GovernanceLedger`](backend/app/services/governance_ledger.py)
  - Groundedness scoring: [`app.services.groundedness_engine.GroundednessEngine`](backend/app/services/groundedness_engine.py)

API routes
- Policy, evidence, audit, and protect endpoints:
  - [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
  - [backend/app/api/routes/evidence.py](backend/app/api/routes/evidence.py)
  - [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
  - [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)

Tooling and examples
- CLI tools:
  - [backend/app/tools/run_policy.py](backend/app/tools/run_policy.py)
  - [backend/app/tools/run_risk.py](backend/app/tools/run_risk.py)
- Sample GenAI integration (pre/post policy checks around LLM calls):
  - [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)
  - [backend/SampleAPPIntegration.md](backend/SampleAPPIntegration.md)

---

## 1) Bring up the backend independently and create policies

Setup
- Create venv and install:
  - macOS/Linux:
    - `cd backend && python -m venv .venv && source .venv/bin/activate`
  - Windows (PowerShell):
    - `cd backend && python -m venv .venv; .\.venv\Scripts\Activate.ps1`
  - Install:
    - `pip install -r requirements.txt` or `pip install -e .`

Initialize database (no migrations)
- `cd backend`
- `python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"`  
  Files: [backend/app/db/base.py](backend/app/db/base.py), [backend/app/db/session.py](backend/app/db/session.py)

Run the API
- With Makefile:
  - `cd backend && make run`
- Or direct Uvicorn:
  - `cd backend && python -m uvicorn app.main:app --reload --port 8000`
  - Entry: [backend/app/main.py](backend/app/main.py)

Verify
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs

Quick policy creation
- Create a policy (POST /api/policies):
  {
    "tenant_id": 1,
    "name": "Content Safety",
    "slug": "content-safety",
    "description": "Blocks unsafe words",
    "is_active": true
  }
- Add a policy version (POST /api/policies/{policy_id}/versions):
  {
    "policy_id": 1,
    "document": {
      "blocked_terms": ["forbidden", "secret sauce"],
      "allowed_sources": [],
      "required_evidence_types": [],
      "pii_rules": {},
      "risk_threshold": 80
    },
    "is_active": true
  }
- Activate a version (POST /api/policies/{policy_id}/versions/{version}/activate)
- Evaluate text via protect (POST /api/protect):
  {
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "this contains a forbidden word",
    "evidence_types": []
  }

More details: [backend/CreatePolicy.md](backend/CreatePolicy.md). Processing: [`app.services.decision_service.protect`](backend/app/services/decision_service.py), policy evaluation: [`app.services.policy_engine.evaluate_policy`](backend/app/services/policy_engine.py).

---

## 2) Integrate and deploy for runtime bidirectional policy management and governance

Goal
- Place the backend as a gate before and after LLM calls to enforce policies and log/audit decisions.

Patterns
- Pre-check: Validate user input via backend before LLM call.
- Sandwich: Check both user input and model output.
- Observe-only: Log/risk without blocking (pilot mode).

JavaScript/TypeScript example
```ts
// Pre + post check around your LLM call
async function protectAndCallLLM(userText: string) {
  const pre = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_id: 1,
      policy_slug: "content-safety",
      input_text: userText,
      evidence_types: []
    }),
  }).then(r => r.json());
  if (!pre.allowed) return { error: "Blocked by policy", reasons: pre.reasons };

  // Call LLM (example: OpenAI)
  const llmRes = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: userText }],
    }),
  });
  const data = await llmRes.json();
  const draft = data.choices?.[0]?.message?.content ?? "";

  const post = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_id: 1,
      policy_slug: "content-safety",
      input_text: draft,
      evidence_types: []
    }),
  }).then(r => r.json());
  if (!post.allowed) return { error: "Output blocked by policy", reasons: post.reasons };

  return { content: draft };
}
```

Python example
```python
import os, json, urllib.request

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

def protect(text: str, tenant_id: int = 1, policy_slug: str = "content-safety") -> dict:
    payload = {"tenant_id": tenant_id, "policy_slug": policy_slug, "input_text": text, "evidence_types": []}
    req = urllib.request.Request(
        f"{BACKEND.rstrip('/')}/api/protect",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

Deploy options
- Single VM
  - `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Docker
  - Minimal image running `uvicorn app.main:app`
- PaaS (Render/Fly/Heroku/Azure)
  - Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Configuration checklist
- DATABASE_URL (Postgres recommended for production)
- ALLOW_ORIGINS (frontend origin or *)
- APP_VERSION
- Governance ledger (optional):
  - GOVERNANCE_LEDGER_PATH, GOVERNANCE_LEDGER_HMAC_SECRET
  - Service: [`app.services.governance_ledger.GovernanceLedger`](backend/app/services/governance_ledger.py)
- Groundedness checks (optional scoring of output vs evidence):
  - Service: [`app.services.groundedness_engine.GroundednessEngine`](backend/app/services/groundedness_engine.py)

Observability and governance
- Health: GET /api/health; Version: GET /api/version
- Decisions/requests: audit endpoints in [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Errors: standardized JSON from [backend/app/core/errors.py](backend/app/core/errors.py)
- Policy evaluation: [`app.services.policy_engine`](backend/app/services/policy_engine.py)
- Risk scoring: [`app.services.risk_engine`](backend/app/services/risk_engine.py)
- Ledger verification: [`app.services.governance_ledger.GovernanceLedger.verify_chain`](backend/app/services/governance_ledger.py)

---

## CLI helpers (backend)

- Evaluate a policy file: `echo "text" | python -m app.tools.run_policy --policy path/to/policy.json` ([run_policy.py](backend/app/tools/run_policy.py))
- Compute risk score: `echo "text" | python -m app.tools.run_risk --evidence-present` ([run_risk.py](backend/app/tools/run_risk.py))

## Running tests (backend)

- From repo root or backend: `pytest -q`
- With Makefile: `cd backend && make test`

## Frontend: setup and run

- Configure env: copy frontend/.env.example to .env and set VITE_API_BASE_URL=http://localhost:8000
- Start: `npm install && npm run dev` then open http://localhost:5173
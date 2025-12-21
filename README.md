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
- frontend/ — Vite + React TypeScript UI
- constitution.md — architectural rules and guidelines

---

## Backend changes since last update

Models
- Portable boolean defaults via server defaults:
  - [`app.models.tenant.Tenant`](backend/app/models/tenant.py)
  - [`app.models.policy.Policy`](backend/app/models/policy.py)
  - [`app.models.policy_version.PolicyVersion`](backend/app/models/policy_version.py)
  - [`app.models.decision_log.DecisionLog`](backend/app/models/decision_log.py)
  - [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py)
- Track in-place JSON mutations:
  - [`app.models.evidence_item.EvidenceItem`](backend/app/models/evidence_item.py) metadata uses MutableDict
  - [`app.models.request_log.RequestLog`](backend/app/models/request_log.py) metadata uses MutableDict
  - [`app.models.decision_log.DecisionLog`](backend/app/models/decision_log.py) reasons uses MutableList
  - [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py) reasons uses MutableList
- Integrity and indexing:
  - Version min bound in [`app.models.policy_version.PolicyVersion`](backend/app/models/policy_version.py)
  - Risk score bounds in [`app.models.risk_score.RiskScore`](backend/app/models/risk_score.py)
  - Composite/indexed timestamps in [`app.models.request_log.RequestLog`](backend/app/models/request_log.py)

Repositories
- Regenerated SQLAlchemy adapters with consistent pagination and validation:
  - [`app.repos.policy_repo.SqlAlchemyPolicyRepo`](backend/app/repos/policy_repo.py)
  - [`app.repos.evidence_repo.SqlAlchemyEvidenceRepo`](backend/app/repos/evidence_repo.py)
  - [`app.repos.audit_repo.SqlAlchemyAuditRepo`](backend/app/repos/audit_repo.py)
  - [`app.repos.tenant_repo.SqlAlchemyTenantRepo`](backend/app/repos/tenant_repo.py)

Schemas
- Pydantic v1/v2 compatibility across:
  - [backend/app/schemas/policies.py](backend/app/schemas/policies.py)
  - [backend/app/schemas/evidence.py](backend/app/schemas/evidence.py)
  - [backend/app/schemas/protect.py](backend/app/schemas/protect.py)
  - [backend/app/schemas/policy_format.py](backend/app/schemas/policy_format.py)

Core
- Unified error responses and optional auth error binding:
  - [backend/app/core/errors.py](backend/app/core/errors.py)
- DI providers for repos/services:
  - [backend/app/core/deps.py](backend/app/core/deps.py)

App entry and tools
- App wiring, CORS, health/version:
  - [backend/app/main.py](backend/app/main.py)
- CLIs:
  - [backend/app/tools/run_risk.py](backend/app/tools/run_risk.py)
  - [backend/app/tools/run_policy.py](backend/app/tools/run_policy.py)

Docs and ergonomics
- Make targets for run/test/lint/format: [backend/Makefile](backend/Makefile)
- Makefile how-to: [backend/Makefile.md](backend/Makefile.md)
- Plain-English policy walkthrough: [backend/CreatePolicy.md](backend/CreatePolicy.md)
- Deployment and integration narrative: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)

---

## 1) Bring up the backend independently and create policies

Prerequisites
- Python 3.11+
- In a terminal:
  - macOS/Linux: `python -m venv backend/.venv && source backend/.venv/bin/activate`
  - Windows (PowerShell): `python -m venv backend\.venv; .\backend\.venv\Scripts\Activate.ps1`
- Install dependencies:
  - `cd backend && pip install -e .` or `pip install -r requirements.txt`

Environment (optional)
- DATABASE_URL=sqlite:///./app.db
- ALLOW_ORIGINS=*
- APP_VERSION=0.1.0

Create database tables (no migrations)
- From backend:
  - `python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"`

Run the API
- With Make: `cd backend && make run`
- Directly: `cd backend && python -m uvicorn app.main:app --reload --port 8000`

Verify
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs

Quick policy creation
- Create a policy:
  - POST /api/policies
  - Body:
    {
      "tenant_id": 1,
      "name": "Content Safety",
      "slug": "content-safety",
      "description": "Blocks unsafe words",
      "is_active": true
    }
- Add a version (rules):
  - POST /api/policies/{policy_id}/versions
  - Body:
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
- Activate a version (if needed):
  - POST /api/policies/{policy_id}/versions/{version}/activate
- Evaluate text via protect:
  - POST /api/protect
  - Body:
    {
      "tenant_id": 1,
      "policy_slug": "content-safety",
      "input_text": "this contains a forbidden word",
      "evidence_types": []
    }

More details: [backend/CreatePolicy.md](backend/CreatePolicy.md). Processing pipeline: [`app.services.decision_service.protect`](backend/app/services/decision_service.py), policy evaluation: [`app.services.policy_engine.evaluate_policy`](backend/app/services/policy_engine.py).

---

## 2) Integrate and deploy for runtime bidirectional policy management and governance

Purpose
- Place the backend as a gate before and after LLM calls to enforce policies and log/audit decisions.

Patterns
- Pre-check (recommended): Check user input before calling the LLM.
- Sandwich: Check both user input and model output before showing it to users.
- Observe-only: Log decisions and risk without blocking during pilot phases.

JavaScript/TypeScript example (pre + post check)
- Pre-check user input; if allowed, call LLM; optionally post-check the draft:

```ts
async function protectAndCallLLM(userText: string) {
  // 1) Ask backend to check the text
  const pre = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: userText,
      evidence_types: [],
    }),
  }).then(r => r.json());

  if (!pre.allowed) return { error: "Blocked by policy", reasons: pre.reasons };

  // 2) Call LLM provider (example: OpenAI; swap for your provider)
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

  // 3) Optional post-check
  const post = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: draft,
      evidence_types: [],
    }),
  }).then(r => r.json());

  if (!post.allowed) return { error: "Output blocked by policy", reasons: post.reasons };
  return { content: draft };
}
```

Python example (server-to-server)
```python
import os, requests

BACKEND = os.getenv("BACKEND_URL", "https://your-backend.app")

def protect(text: str) -> dict:
  r = requests.post(f"{BACKEND}/api/protect", json={
    "policy_slug": "content-safety",
    "input_text": text,
    "evidence_types": []
  }, timeout=15)
  r.raise_for_status()
  return r.json()

def call_llm(text: str) -> str:
  from openai import OpenAI
  client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
  resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": text}],
  )
  return resp.choices[0].message.content

def guarded_generation(user_text: str) -> dict:
  pre = protect(user_text)
  if not pre.get("allowed"):
    return {"error": "Blocked by policy", "reasons": pre.get("reasons", [])}
  draft = call_llm(user_text)
  post = protect(draft)
  if not post.get("allowed"):
    return {"error": "Output blocked by policy", "reasons": post.get("reasons", [])}
  return {"content": draft}
```

Deploy options
- Single VM (simple)
  - Create venv, install deps, run Uvicorn:
    - `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Docker
  - Minimal Dockerfile:
    - FROM python:3.11-slim
    - WORKDIR /app
    - COPY backend /app
    - RUN pip install --no-cache-dir -r requirements.txt
    - EXPOSE 8000
    - CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
- PaaS (Render/Fly/Heroku/Azure App Service)
  - Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Configuration checklist
- DATABASE_URL (Postgres recommended for production)
- ALLOW_ORIGINS (frontend origin or *)
- APP_VERSION
- API key secret (if enforcing key-based access): one of AUTH_HMAC_SECRET, API_KEY_SECRET, SECRET_KEY
- Optional SQL echo flag via settings in [backend/app/core/config.py](backend/app/core/config.py)

Observability and governance
- Health: GET /api/health; Version: GET /api/version
- Decisions/requests: audit endpoints in [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Errors: standardized JSON from [backend/app/core/errors.py](backend/app/core/errors.py)
- Policy evaluation: [`app.services.policy_engine`](backend/app/services/policy_engine.py)
- Risk scoring: [`app.services.risk_engine`](backend/app/services/risk_engine.py)

More deployment details and integration narrative: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)

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
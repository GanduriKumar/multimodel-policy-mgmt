# Multimodel Policy Management (Monorepo)

This project helps you set simple “policies” for AI apps. A policy is just a set of rules (like “block these words” or “require a URL as evidence”) that you can create, version, activate, and use to allow or block content.

If you’re new to this, don’t worry—this guide uses everyday language and shows exactly what to click or type.

What’s in here
- Backend (FastAPI): the policy and decision engine
  - App entry: [backend/app/main.py](backend/app/main.py)
  - API router: [backend/app/api/router.py](backend/app/api/router.py)
  - Routes:
    - Policies: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
      - Key handlers: [`app.api.routes.policies.create_policy`](backend/app/api/routes/policies.py), [`app.api.routes.policies.list_policies`](backend/app/api/routes/policies.py), [`app.api.routes.policies.add_policy_version`](backend/app/api/routes/policies.py)
    - Protect (check text): [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
    - Protect & Generate (one call): [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
    - Evidence: [backend/app/api/routes/evidence.py](backend/app/api/routes/evidence.py)
    - Audit: [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
  - Services (how decisions are made):
    - Policy engine: [backend/app/services/policy_engine.py](backend/app/services/policy_engine.py)
    - Decision orchestration: [backend/app/services/decision_service.py](backend/app/services/decision_service.py)
    - Risk engine: [backend/app/services/risk_engine.py](backend/app/services/risk_engine.py)
    - One-call orchestration: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)
  - Repos (data access):
    - Policies: [backend/app/repos/policy_repo.py](backend/app/repos/policy_repo.py) (see [`app.repos.policy_repo.SqlAlchemyPolicyRepo.update_policy`](backend/app/repos/policy_repo.py))
- Frontend (React + Vite): a simple UI to manage and test
  - Pages: Policies [frontend/src/pages/Policies.tsx](frontend/src/pages/Policies.tsx), Protect [frontend/src/pages/Protect.tsx](frontend/src/pages/Protect.tsx), Evidence [frontend/src/pages/Evidence.tsx](frontend/src/pages/Evidence.tsx), Audit [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)
  - Policies hook: [frontend/src/hooks/usePolicies.ts](frontend/src/hooks/usePolicies.ts)

Helpful how-to docs
- Makefile run guide: [backend/Makefile.md](backend/Makefile.md)
- Create policies (step-by-step): [backend/CreatePolicy.md](backend/CreatePolicy.md)
- Deploy & integrate: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)
- Sample app integration: [backend/SampleAPPIntegration.md](backend/SampleAPPIntegration.md), script [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)

Policies in plain English
- Tenant: the “workspace” that owns policies.
- Policy: a named container (has many versions).
- Version: a snapshot of rules. You don’t edit a version in place—create a new one and activate it.
- Only one version is active at a time.

Quick start

Backend
- Create venv and install
  - macOS/Linux:
    - cd backend && python -m venv .venv && source .venv/bin/activate
  - Windows (PowerShell):
    - cd backend && python -m venv .venv; .\.venv\Scripts\Activate.ps1
  - Install deps:
    - pip install -r requirements.txt (or pip install -e .)
- Initialize the DB (no migrations for now)
  - cd backend
  - python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"
- Run the API
  - make run (see [backend/Makefile](backend/Makefile) and [backend/Makefile.md](backend/Makefile.md))
  - or: python -m uvicorn app.main:app --reload --port 8000
- Verify
  - Health: http://localhost:8000/api/health
  - Docs: http://localhost:8000/docs

Frontend
- cd frontend && npm install && npm run dev
- Open http://localhost:5173
- Ensure VITE_API_BASE_URL points to your backend (see frontend/.env.example)

Policies from the command line (CLI)

You can manage policies using curl. Replace values with your own.

1) Create a policy
- Endpoint: POST /api/policies
- Handler: [`app.api.routes.policies.create_policy`](backend/app/api/routes/policies.py)

```bash
curl -X POST http://localhost:8000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Content Safety",
    "slug": "content-safety",
    "description": "Blocks unsafe words",
    "is_active": true
  }'
```

2) Modify (rules) by adding a new version
- Endpoint: POST /api/policies/{policy_id}/versions
- Handler: [`app.api.routes.policies.add_policy_version`](backend/app/api/routes/policies.py)
- Important: Include policy_id in the body and it must match the URL; otherwise the API returns 400.

```bash
POLICY_ID=1
curl -X POST http://localhost:8000/api/policies/$POLICY_ID/versions \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": '"$POLICY_ID"',
    "document": {
      "blocked_terms": ["forbidden", "secret sauce"],
      "allowed_sources": [],
      "required_evidence_types": ["url"],
      "pii_rules": { "mask_emails": true },
      "risk_threshold": 50
    },
    "is_active": true
  }'
```

3) Activate a specific version
- Endpoint: POST /api/policies/{policy_id}/versions/{version}/activate
- Handler: [`app.api.routes.policies.set_active_version`](backend/app/api/routes/policies.py)

```bash
curl -X POST http://localhost:8000/api/policies/1/versions/2/activate
```

4) Update policy metadata (name, slug, description, is_active)
- Current public HTTP routes do not expose “update policy” yet.
- Internals support it via [`app.repos.policy_repo.SqlAlchemyPolicyRepo.update_policy`](backend/app/repos/policy_repo.py), but there is no HTTP endpoint.
- Practical approach today:
  - For rule changes: create a new version (step 2) and activate it (step 3).
  - To “retire” usage: mark clients to use a different policy, or create a version that blocks all content.
- If you need true metadata updates right now, add an API route wired to `update_policy` in [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py), or run an admin task against the repo. The UI does not expose metadata editing yet.

5) Delete a policy
- There is no public HTTP “delete policy” endpoint at the moment.
- Internals have delete helpers (see repo layer in [backend/app/repos/policy_repo.py](backend/app/repos/policy_repo.py)), but they’re not routed.
- Practical workaround:
  - “Retire” the policy by moving clients to another policy and/or deactivating its practical use (e.g., keep it but stop referencing its slug).
  - If you must hard-delete, add an admin-only route that calls the repo delete method, or use a maintenance script (not provided here).

6) List policies
- Endpoint: GET /api/policies?tenant_id=...&offset=...&limit=...
- Handler: [`app.api.routes.policies.list_policies`](backend/app/api/routes/policies.py)

```bash
curl "http://localhost:8000/api/policies?tenant_id=1&offset=0&limit=50"
```

7) Check text against the active policy
- Endpoint: POST /api/protect
- Service: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)

```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "this contains a forbidden word",
    "evidence_types": []
  }'
```

Optional: one-call Protect & Generate
- Endpoint: POST /api/protect-generate
- Service: [`app.services.governed_generation_service.GovernedGenerationService`](backend/app/services/governed_generation_service.py)

```bash
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "Summarize our policy.",
    "llm": { "provider": "openai", "model": "gpt-4o-mini" }
  }'
```

Policies from the frontend UI

Open the app
- Start the frontend: cd frontend && npm install && npm run dev
- Open http://localhost:5173
- Make sure VITE_API_BASE_URL points at your backend.

1) Create a policy (UI)
- Go to “Policies” (top navigation) [frontend/src/pages/Policies.tsx](frontend/src/pages/Policies.tsx)
- In the “Create Policy” card:
  - Fill Name, Slug, Description (optional), Active
  - Click “Create Policy”
- The new policy appears in the table (hook: [`frontend/src/hooks/usePolicies.ts`](frontend/src/hooks/usePolicies.ts))

2) Modify rules by adding a version (UI)
- In the policy row’s “Versioning” area:
  - Paste Version JSON (example below)
  - Check “Active” to activate immediately (or uncheck to keep inactive)
  - Click “Add Version”
- Example JSON to paste:
```json
{
  "blocked_terms": ["forbidden", "secret sauce"],
  "allowed_sources": [],
  "required_evidence_types": ["url"],
  "pii_rules": { "mask_emails": true },
  "risk_threshold": 50
}
```

3) Activate a specific version (UI)
- Enter the version number in “Version # to activate”
- Click “Activate”
- The backend will mark that version active and deactivate others

4) Update policy metadata (UI)
- Not supported in the UI yet (no form to rename slug/name or change description after creation).
- Workaround: treat policy metadata as stable; change rules by creating a new version and activating it.

5) Delete a policy (UI)
- Not supported in the UI.
- Workaround: stop using that policy’s slug in clients, and/or create a version that blocks everything (effectively “retired”).

6) Test your policy quickly (UI)
- Go to “Protect” [frontend/src/pages/Protect.tsx](frontend/src/pages/Protect.tsx)
  - Enter Tenant ID, Policy Slug, and Input Text
  - Submit to see allowed (true/false) and reasons

What the UI supports now
- Create policy, list policies, add versions, activate a version, try Protect
- Evidence and Audit pages are also available:
  - Evidence: [frontend/src/pages/Evidence.tsx](frontend/src/pages/Evidence.tsx)
  - Audit: [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)

Policy document shape

Policies are validated by [`app.schemas.policy_format.PolicyDoc`](backend/app/schemas/policy_format.py). Common fields:
- blocked_terms: list[string]
- allowed_sources: list[string]
- required_evidence_types: list[string]
- pii_rules: dict
- risk_threshold: number 0–100

Under the hood

- Routes (thin): see [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
- Decision flow: [`app.services.decision_service.protect`](backend/app/services/decision_service.py) calls the policy and risk engines:
  - Policy engine: [backend/app/services/policy_engine.py](backend/app/services/policy_engine.py)
  - Risk engine: [backend/app/services/risk_engine.py](backend/app/services/risk_engine.py)
- One-call orchestration: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)

CLI helpers (backend)
- Evaluate a policy file against input text:
  - echo "text" | python -m app.tools.run_policy --policy path/to/policy.json ([backend/app/tools/run_policy.py](backend/app/tools/run_policy.py))
- Compute a risk score:
  - echo "text" | python -m app.tools.run_risk --evidence-present ([backend/app/tools/run_risk.py](backend/app/tools/run_risk.py))

Running tests (backend)
- From repo root or backend: pytest -q
- With Makefile: cd backend && make test (see [backend/Makefile](backend/Makefile))

Deploy basics
See the step-by-step guide in [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md). Quick pointers:
- Run with Uvicorn:
  - python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
- Docker (example):
  - docker build -t policy-backend -f Dockerfile .
  - docker run -d -p 8000:8000 -e DATABASE_URL=sqlite:///./app.db -e ALLOW_ORIGINS=* policy-backend
- Health: GET /api/health; Version: GET /api/version

Notes and tips
- You don’t edit an existing version. Create a new version and activate it so there’s a clear history and easy rollback.
- When adding a version via the API, policy_id in the JSON body must match the URL path, by design in [`app.api.routes.policies.add_policy_version`](backend/app/api/routes/policies.py).
- Only one version is active per policy.
- For metadata update/delete, public HTTP endpoints are intentionally minimal right now; plan workflows around versioning until those routes are added.
# 1. Introduction

Multimodel Policy Management helps you define, version, activate, and enforce simple “policies” for AI apps. Policies can block terms, require evidence, and incorporate a risk engine. The system logs requests/decisions for audit and supports an optional governance ledger.

Key components (monorepo):
- Backend (FastAPI): decision flow, policy/risk engines, evidence, audit
  - App entry: [backend/app/main.py](backend/app/main.py)
  - Router aggregator: [backend/app/api/router.py](backend/app/api/router.py)
  - Decision orchestration: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
  - Policy engine: [backend/app/services/policy_engine.py](backend/app/services/policy_engine.py)
  - Risk engine: [backend/app/services/risk_engine.py](backend/app/services/risk_engine.py)
  - One-call orchestrator: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)
- Frontend (React + Vite): simple UI to manage policies, evaluate text, inspect audit
  - Protect page: [frontend/src/pages/Protect.tsx](frontend/src/pages/Protect.tsx)
  - Evidence page: [frontend/src/pages/Evidence.tsx](frontend/src/pages/Evidence.tsx)
  - Audit page: [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)
  - Policies hook: [frontend/src/hooks/usePolicies.ts](frontend/src/hooks/usePolicies.ts)

Helpful docs:
- Deploy & integrate: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)
- Create policies (step-by-step): [backend/CreatePolicy.md](backend/CreatePolicy.md)
- Makefile run guide: [backend/Makefile.md](backend/Makefile.md)

---

# 2. Getting started

Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

Clone and install
- Backend
  - cd backend
  - python -m venv .venv && source .venv/bin/activate  (Windows: .\.venv\Scripts\Activate.ps1)
  - pip install -r requirements.txt  (or: pip install -e .)
  - Initialize DB (SQLite default):
    - python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"
- Frontend
  - cd frontend && npm install

Environment
- Backend config: [backend/app/core/config.py](backend/app/core/config.py)
  - DATABASE_URL or DB_URL (default sqlite:///./app.db)
  - API_KEY_HEADER (default x-api-key)
  - DEFAULT_RISK_THRESHOLD
- Frontend config: [frontend/.env.example](frontend/.env.example)
  - VITE_API_BASE_URL=http://localhost:8000

---

# 3. How to start the backend service

Option A — Makefile (recommended)
- cd backend && make run
  - Starts: uvicorn app.main:app --reload --port 8000

Option B — Raw uvicorn
- cd backend && python -m uvicorn app.main:app --reload --port 8000

Verify
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs
- Version: http://localhost:8000/api/version

Notes
- CORS is configured in [`app.main.get_application`](backend/app/main.py).
- API key header name comes from settings; see [backend/app/core/config.py](backend/app/core/config.py) and auth helpers in [backend/app/core/auth.py](backend/app/core/auth.py).
- Make targets: [backend/Makefile](backend/Makefile), guide: [backend/Makefile.md](backend/Makefile.md).

---

# 4. How to use the frontend service

- cd frontend && npm install && npm run dev
- Open http://localhost:5173
- Ensure VITE_API_BASE_URL points to the backend (see [frontend/.env.example](frontend/.env.example)).

Pages
- Protect: try POST /api/protect flows ([frontend/src/pages/Protect.tsx](frontend/src/pages/Protect.tsx))
- Policies: create/list/add versions/activate (see hooks in [frontend/src/hooks/usePolicies.ts](frontend/src/hooks/usePolicies.ts))
- Evidence: ingest and fetch ([frontend/src/pages/Evidence.tsx](frontend/src/pages/Evidence.tsx))
- Audit: list requests and view decision details ([frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx))

---

# 5. Sample test application and integration with backend with REST API integration

Python sample app
- Runner script: [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)
- Flow:
  1) Pre-check user input via POST /api/protect
  2) Call LLM (OpenAI REST)
  3) Post-check the model output via POST /api/protect
- Core call: [`app.services.decision_service.protect`](backend/app/services/decision_service.py) is the backend’s orchestrator.

Usage
- Prompt via arg:
  - python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --prompt "Hello!"
- Prompt via STDIN:
  - echo "Summarize..." | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety

Minimal curl examples
- Create policy:
  - See examples in [backend/CreatePolicy.md](backend/CreatePolicy.md)
- Check text:
  - curl -X POST http://localhost:8000/api/protect -H "Content-Type: application/json" -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"some text","evidence_types":[]}'

JS/TS snippet (from docs)
- End-to-end sandwich pattern is shown in [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)

---

# 6. Details of Backend API

Router entry
- Aggregator: [backend/app/api/router.py](backend/app/api/router.py)
- App factory: [backend/app/main.py](backend/app/main.py)

Policies
- File: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
- Endpoints (high level):
  - POST /api/policies  (create)
  - GET /api/policies?tenant_id=...&offset=...&limit=...  (list)
  - POST /api/policies/{policy_id}/versions  (add version; body must include matching policy_id)
  - POST /api/policies/{policy_id}/versions/{version}/activate  (activate one version)
- Policy doc shape: [backend/app/schemas/policy_format.py](backend/app/schemas/policy_format.py)

Protect (evaluate text)
- File: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
- Service: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
- Endpoint:
  - POST /api/protect
  - Request: tenant_id, policy_slug, input_text, evidence_types (optional)
  - Response: allowed, reasons, risk_score, and log IDs

Protect & Generate (one call)
- File: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Schema: [backend/app/schemas/generation.py](backend/app/schemas/generation.py)
- Service: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)
- Endpoint: POST /api/protect-generate

Evidence
- File: [backend/app/api/routes/evidence.py](backend/app/api/routes/evidence.py)
- Typical endpoints:
  - POST /api/evidence?tenant_id=... (ingest)
  - GET /api/evidence/{id}?tenant_id=... (fetch)
- Tests: [backend/tests/test_api_evidence.py](backend/tests/test_api_evidence.py)

Audit
- File: [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Typical endpoints:
  - GET /api/audit/requests?tenant_id=...&offset=...&limit=... (list)
  - GET /api/audit/decisions/{request_id}?tenant_id=... (detail)
- Traces (correlation helper): [backend/app/api/routes/traces.py](backend/app/api/routes/traces.py)

Governance and compliance (optional)
- Governance ledger: [backend/app/services/governance_ledger.py](backend/app/services/governance_ledger.py)
- Compliance export service: [backend/app/services/compliance_export.py](backend/app/services/compliance_export.py)

Security and config
- API key header name and secrets: [backend/app/core/config.py](backend/app/core/config.py), [backend/app/core/auth.py](backend/app/core/auth.py)

---

# 7. Licensing and credits

License
- MIT, see [LICENSE](LICENSE)

Credits
- Author: KumarGN (2025)
- Built with:
  - FastAPI, Pydantic, SQLAlchemy (backend)
  - React, Vite, TypeScript (frontend)
- Engineering guidelines: [constitution.md](constitution.md)
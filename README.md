# Multimodel Policy Management

A lightweight, testable policy enforcement and audit system for AI apps. It helps you define versioned policies, evaluate user input and model output (pre/post), compute risk, record decisions for audit, and optionally append evidence to a tamper‑evident governance ledger. It ships with a minimal React frontend for non‑engineers and a clean FastAPI backend for integration.

- Backend entry: [backend/app/main.py](backend/app/main.py)
- API router: [backend/app/api/router.py](backend/app/api/router.py)
- Decision orchestration: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
- One‑call orchestration: [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py)
- Frontend entry: [frontend/src/main.tsx](frontend/src/main.tsx)

---

## 1) Introduction

What this is
- A policy‑first safety layer you can put between your app and any LLM.
- Define simple JSON policies, version them, activate one version at a time.
- Check text against policies, compute a heuristic risk score, and log every decision for audit.
- Optional tamper‑evident governance ledger and RAG trace capture.

What’s different from typical tools
- Versioned policies that are easy to reason about (no black‑box config).
- Simple, deterministic engines (policy, risk, groundedness, safety) you can read and test.
- Clean separation of concerns: route → service → repo/engine; easy to swap adapters.
- Beginner‑friendly UI (create/list/activate policies, evaluate text, ingest evidence, browse audit).
- Compliance‑ready exports (JSON/HTML bundles with hashes) via [`ComplianceExportService`](backend/app/services/compliance_export.py).

What this is not
- Not a vendor‑locked gateway. It’s framework code you can extend or replace.
- Not a complex rule engine—intentionally minimal to keep it transparent and testable.

---

## 2) Getting started

Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

Clone the repo
```bash
git clone https://github.com/your-org/multimodel-policy-mgmt.git
cd multimodel-policy-mgmt
```

Backend setup (FastAPI)
```bash
# macOS/Linux
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Initialize SQLite schema
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

# Run (option A)
python -m uvicorn app.main:app --reload --port 8000
# or (option B, with Makefile)
make run
```

Windows (PowerShell)
```powershell
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"
python -m uvicorn app.main:app --reload --port 8000
```

Frontend setup (React + Vite)
```bash
cd frontend
npm install
# Configure API base URL if needed
cp .env.example .env   # edit VITE_API_BASE_URL if backend is not on localhost:8000
npm run dev            # opens http://localhost:5173
```

Useful URLs
- Backend health: http://localhost:8000/api/health
- OpenAPI docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

Configuration (env)
- Backend settings: [backend/app/core/config.py](backend/app/core/config.py)
  - DATABASE_URL or DB_URL (default sqlite:///./app.db)
  - API_KEY_HEADER (default x-api-key)
  - DEFAULT_RISK_THRESHOLD (default 80)
  - Governance ledger (optional): GOVERNANCE_LEDGER_PATH, GOVERNANCE_LEDGER_HMAC_SECRET
- Frontend settings: [frontend/.env.example](frontend/.env.example)
  - VITE_API_BASE_URL=http://localhost:8000
  - VITE_API_KEY (optional if backend enforces API keys)

Tests and lint (backend)
```bash
cd backend
make test        # all tests
make test-api    # API tests only
make lint        # Ruff checks
make format      # Apply Ruff formatting
```

---

## 3) How to use the backend services

Integration patterns
- Pre‑check (recommended): Call the backend before sending user text to an LLM.
- Sandwich: Pre‑check user text and post‑check the model output before showing it.
- One‑call: Let the backend do pre‑check, call the LLM, run safety/groundedness, post‑check.

Python example (simple pre‑check) using urllib (no extra deps)
```python
import json, urllib.request

payload = {
  "tenant_id": 1,
  "policy_slug": "content-safety",
  "input_text": "Hello world",
  "evidence_types": []
}
req = urllib.request.Request(
  "http://localhost:8000/api/protect",
  data=json.dumps(payload).encode("utf-8"),
  method="POST",
  headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
  result = json.loads(resp.read().decode("utf-8"))
  print(result)  # {"allowed": true/false, "reasons": [...], "risk_score": ...}
```

cURL (pre‑check and post‑check)
```bash
# Pre-check user input
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"some text","evidence_types":[]}'

# Post-check model output
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"model draft here","evidence_types":[]}'
```

One‑call orchestration (backend calls the LLM)
- Route: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Service: [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py)
```bash
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "Draft a brief policy summary.",
    "evidence_types": [],
    "retrieval_query": "policy overview"
  }'
```
Response includes:
- allowed, risk_score
- policy_reasons, risk_reasons
- grounded_claims (scored claims)
- raw_model_output
- trace_id (for RAG/ledger correlation)
Schemas: [backend/app/schemas/generation.py](backend/app/schemas/generation.py)

Key backend pieces you may call or extend
- Protect orchestration: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
- LLM gateway (Ollama/OpenAI): [backend/app/services/llm_gateway.py](backend/app/services/llm_gateway.py)
- RAG proxy: [backend/app/services/rag_proxy.py](backend/app/services/rag_proxy.py)
- Governance ledger: [backend/app/services/governance_ledger.py](backend/app/services/governance_ledger.py)

---

## 4) How to use the frontend service

Start the UI
- cd frontend && npm run dev → http://localhost:5173
- Ensure VITE_API_BASE_URL points to your backend.

Pages (top navigation)
- Protect
  - Try POST /api/protect flows live: enter Tenant ID, Policy Slug, the text, and optional Evidence Types.
  - See allowed, reasons, and risk score.
- Policies
  - Create policy (name, slug, description, active).
  - List policies by tenant; add new versions and activate a specific version.
  - Versions let you change rules safely (history is preserved).
- Evidence
  - Ingest evidence (url/text) your policies require and fetch by ID.
  - Helps policies that need supporting artifacts to pass.
- Audit
  - Browse requests and decision details (policy/risk reasons).
  - Export a request’s audit bundle as JSON or HTML (PDF‑ready) via the export actions.

These are the core workflows:
1) Create a policy → add a version (JSON rules) → activate it.
2) Use Protect to evaluate text (or use your app against the backend).
3) Optionally ingest evidence if the policy requires it.
4) Review what happened in Audit; export a compliance bundle if needed.

Frontend API client: [frontend/src/api/client.ts](frontend/src/api/client.ts)

---

## 5) Sample Python GenAI application and backend integration

The sample shows a full “sandwich” pattern: pre‑check → call OpenAI → post‑check.
- Script: [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)

Run examples
```bash
# Prompt via argument
python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --prompt "Hello"

# Prompt via STDIN
echo "Summarize this..." | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety

# JSON output (pre/post + content)
echo "Hello" | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --json
```

What it does
1) Pre‑checks your prompt via POST /api/protect.
2) Calls OpenAI (needs OPENAI_API_KEY).
3) Post‑checks the draft via POST /api/protect.
Core call in backend: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)

---

## 6) Details of Backend APIs

Router entry
- Aggregator: [backend/app/api/router.py](backend/app/api/router.py)
- App factory: [backend/app/main.py](backend/app/main.py)

Policies
- Route file: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
- Endpoints (high level):
  - POST /api/policies
    - Body: { tenant_id, name, slug, description?, is_active? }
  - GET /api/policies?tenant_id=...&offset=...&limit=...
  - POST /api/policies/{policy_id}/versions
    - Body includes matching policy_id and a JSON “document” with rules
    - Example policy doc schema: [backend/app/schemas/policy_format.py](backend/app/schemas/policy_format.py)
  - POST /api/policies/{policy_id}/versions/{version}/activate
- Use cases: create/list/add version/activate a policy version.

Protect (evaluate text)
- Route file: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
- Service: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
- Endpoint: POST /api/protect
- Request
  - { tenant_id: number, policy_slug: string, input_text: string, evidence_types?: string[] }
- Response
  - { allowed: boolean, reasons: string[], risk_score: number, request_log_id?: number, decision_log_id?: number }

Protect & Generate (one‑call orchestration)
- Route: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Service: [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py)
- Endpoint: POST /api/protect-generate
- Request (subset)
  - { tenant_id, policy_slug, input_text, evidence_types?, retrieval_query?, evidence_payloads? }
- Response
  - { allowed, risk_score, policy_reasons, risk_reasons, grounded_claims, raw_model_output, trace_id }

Evidence
- Route: [backend/app/api/routes/evidence.py](backend/app/api/routes/evidence.py)
- Typical endpoints
  - POST /api/evidence?tenant_id=... (ingest)
  - GET /api/evidence/{id}?tenant_id=... (fetch)

Audit (list, detail, export)
- Route: [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Typical endpoints
  - GET /api/audit/requests?tenant_id=...&offset=...&limit=...
  - GET /api/audit/decisions/{request_id}?tenant_id=...
  - GET /api/audit/export/{request_id}?format=json|html
    - Returns a compliance bundle (JSON or HTML) with section hashes
    - Export service: [backend/app/services/compliance_export.py](backend/app/services/compliance_export.py)

Traces (correlation helper)
- Route: [backend/app/api/routes/traces.py](backend/app/api/routes/traces.py)

Optional governance and LLM wiring
- LLM gateway (Ollama/OpenAI): [backend/app/services/llm_gateway.py](backend/app/services/llm_gateway.py)
- RAG proxy and sessions: [backend/app/services/rag_proxy.py](backend/app/services/rag_proxy.py)
- Governance ledger: [backend/app/services/governance_ledger.py](backend/app/services/governance_ledger.py)
- Dependency wiring: [backend/app/core/deps.py](backend/app/core/deps.py)

Security and config
- Settings: [backend/app/core/config.py](backend/app/core/config.py)
- Auth helpers: [backend/app/core/auth.py](backend/app/core/auth.py)
- Engineering guidelines: [constitution.md](constitution.md)

---

## 7) Licensing and credits

License
- MIT, see [LICENSE](LICENSE)

Credits
- Author: KumarGN (2025)
- Built with:
  - FastAPI, Pydantic, SQLAlchemy (backend)
  - React, Vite, TypeScript (frontend)
- Engineering guidelines: [constitution.md](constitution.md)

---
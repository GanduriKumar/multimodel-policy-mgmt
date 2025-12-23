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
- Optional tamper‑evident governance ledger and retrieval traces for compliance.
- Beginner‑friendly UI (create/list/activate policies, evaluate text, ingest evidence, browse/export audit).

What’s different from typical tools today
- Policy once, apply everywhere:
  - You can encode enterprise, domain, and regulatory policies once and enforce them across multiple applications and multiple LLM providers.
  - Providers are pluggable via the gateway abstraction in [backend/app/services/llm_gateway.py](backend/app/services/llm_gateway.py) (Ollama, OpenAI today).
- Deterministic, inspectable engines:
  - Policy engine, risk engine, groundedness and safety checks are clear and testable. See:
    - Policy engine: [backend/app/services/policy_engine.py](backend/app/services/policy_engine.py)
    - Risk engine: [backend/app/services/risk_engine.py](backend/app/services/risk_engine.py)
    - Groundedness: [backend/app/services/groundedness_engine.py](backend/app/services/groundedness_engine.py)
    - Response safety: [backend/app/services/response_safety_engine.py](backend/app/services/response_safety_engine.py)
- Audit‑ready by design:
  - Every request and decision is captured via the audit repository contracts in [`app.core.contracts.AuditRepo`](backend/app/core/contracts.py).
  - Optional tamper‑evident ledger for immutable evidence trails: [`app.services.governance_ledger.GovernanceLedger`](backend/app/services/governance_ledger.py).
  - One‑click compliance exports (JSON or HTML) via [`app.services.compliance_export.ComplianceExportService`](backend/app/services/compliance_export.py).
- Clean layering (route → service → repo/engine):
  - Routes contain no business logic (see [backend/app/api/README.md](backend/app/api/README.md)).
  - Swappable adapters behind Protocol ports (see [backend/app/core/contracts.py](backend/app/core/contracts.py)).

How it helps in an enterprise
- Centralized policy: encode regulations and business rules once; apply across teams and apps.
- Multi‑provider: enforce the same guardrails across different LLMs without per‑app rewrites.
- Compliance reporting:
  - Exportable, machine‑verifiable JSON and PDF‑ready HTML bundles with section hashes: [`ComplianceExportService`](backend/app/services/compliance_export.py).
  - Append‑only, hash‑chained ledger for immutable evidence: [`GovernanceLedger`](backend/app/services/governance_ledger.py).
- Traceability:
  - Inspect requests, decisions, risk, and supporting evidence through the Audit UI and APIs.

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
cp .env.example .env   # edit VITE_API_BASE_URL if backend isn't on http://localhost:8000
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
  - OPENAI_API_KEY and OPENAI_MODEL (for OpenAI gateway)
  - OLLAMA_BASE_URL and OLLAMA_MODEL (for Ollama gateway)
  - GOVERNANCE_LEDGER_PATH, GOVERNANCE_LEDGER_HMAC_SECRET (optional governance ledger)
- Frontend settings: [frontend/.env.example](frontend/.env.example)
  - VITE_API_BASE_URL=http://localhost:8000
  - VITE_API_KEY (optional if backend enforces API keys)

Makefile helpers (backend)
```bash
cd backend
make run         # start API with reload
make test        # run all backend tests
make test-api    # API tests only
make lint        # Ruff lint checks
make format      # Apply Ruff formatting
```

---

## 3) How to use the backend services

Core concepts
- Policies are versioned JSON documents validated by [`app.schemas.policy_format.PolicyDoc`](backend/app/schemas/policy_format.py).
- The protect flow orchestrates policy evaluation and risk scoring via [`app.services.decision_service.protect`](backend/app/services/decision_service.py).
- The one‑call orchestrator also handles LLM calls, groundedness, and safety via [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py).

Schemas
- Protect request/response: [backend/app/schemas/protect.py](backend/app/schemas/protect.py)
- Protect‑Generate request/response: [backend/app/schemas/generation.py](backend/app/schemas/generation.py)
- Policy document shape: [backend/app/schemas/policy_format.py](backend/app/schemas/policy_format.py)

Calling the Protect API (pre/post checks)
- Route: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
- Endpoint: POST /api/protect
- Request fields (ProtectRequest)
  - tenant_id: number — Your tenant/workspace id.
  - policy_slug: string — The policy to enforce.
  - input_text: string — The content to evaluate.
  - evidence_types?: string[] — Tags such as "url" or "document".
- Response (ProtectResponse)
  - allowed: boolean — Final decision.
  - reasons: string[] — Human‑readable reasons (policy or risk).
  - risk_score: number — 0–100 heuristic risk score.
  - request_log_id?: number — Audit reference.
  - decision_log_id?: number — Audit reference.

cURL examples
```bash
# Pre-check user input
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"some text","evidence_types":[]}'
```

# Post-check model output
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"draft from LLM","evidence_types":[]}'

```

Python (urllib, no extra deps)
```python
# filepath: examples/protect_example.py
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
print(result)
```

One‑call orchestration: Protect‑Generate
- Route: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Service: [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py)
- Endpoint: POST /api/protect-generate
- Request (subset from [`app.schemas.generation`](backend/app/schemas/generation.py))
  - tenant_id: number (required)
  - policy_slug: string (required)
  - input_text: string (required)
  - evidence_types?: string[]
  - retrieval_query?: string
  - evidence_payloads?: array of { text: string, source_uri?: string, metadata?: object, document_hash?: string, chunk_hash?: string }
  - llm?: { provider?: "ollama" | "openai", model?: string }
- Response adds:
  - policy_reasons, risk_reasons (split reasons)
  - grounded_claims: [{ claim: { text }, score, supported, matched_evidence_ids }]
  - raw_model_output: string
  - trace_id: string

Example
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

Policy documents
- Shape: [`app.schemas.policy_format.PolicyDoc`](backend/app/schemas/policy_format.py)
  - blocked_terms: string[] (required)
  - allowed_sources: string[] (required)
  - required_evidence_types: string[] (required)
  - pii_rules: object (required)
  - risk_threshold: number 0–100 (required)
- CLI helper to evaluate a policy file:
  - [`app.tools.run_policy`](backend/app/tools/run_policy.py)
- CLI helper to compute risk from stdin:
  - [`app.tools.run_risk`](backend/app/tools/run_risk.py)

Audit exports and ledger (optional, but recommended)
- Export service: [`ComplianceExportService`](backend/app/services/compliance_export.py)
  - Produces JSON (machine‑verifiable with SHA‑256 hashes) and HTML (PDF‑ready) bundles.
- Append‑only ledger: [`GovernanceLedger`](backend/app/services/governance_ledger.py)
  - Tamper‑evident record with hash chaining; verify with [`app.tools.verify_ledger`](backend/app/tools/verify_ledger.py).

---

## 4) How to use the frontend service

Start the UI
- cd frontend && npm run dev → http://localhost:5173
- Ensure VITE_API_BASE_URL points to your backend.

Pages (top navigation) and why they matter
- Home
  - Quick entry point and health overview.
- Policies
  - Create policy containers (name/slug/description/active).
  - Add JSON policy versions and activate one version.
  - Why: versioned rules let you evolve guardrails safely and keep history.
  - Uses hook: [frontend/src/hooks/usePolicies.ts](frontend/src/hooks/usePolicies.ts)
- Protect
  - Try POST /api/protect flows live: enter Tenant ID, Policy Slug, the text, and optional Evidence Types.
  - See allowed, reasons, and risk score to validate your policy logic.
- Evidence
  - Ingest evidence (url/text) your policies may require and fetch by ID.
  - Why: some policies depend on supporting artifacts (e.g., citations).
  - Uses hook: [frontend/src/hooks/useEvidence.ts](frontend/src/hooks/useEvidence.ts)
- Audit
  - Browse requests and decision details (policy/risk reasons).
  - Export compliance bundles (JSON or HTML, PDF‑ready).
  - Why: compliance and governance—prove what happened and why.
  - UI: [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)

---

## 5) Sample Python GenAI application and backend integration

End‑to‑end “sandwich” pattern (pre‑check → call LLM → post‑check)
- Script: [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)

What it does
1) Pre‑checks your prompt via POST /api/protect.
2) Calls OpenAI (needs OPENAI_API_KEY).
3) Post‑checks the draft via POST /api/protect.
4) Optionally use the one‑call endpoint /api/protect-generate.

Run examples
```bash
# Prompt via argument
python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --prompt "Hello"

# Prompt via STDIN
echo "Summarize this..." | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety

# JSON output (pre/post + content)
echo "Hello" | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --json
```

Core call in backend: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)

Helper calls in the sample
- Protect call: [`protect(...)`](backend/SampleAppIntegration.py)
- OpenAI call: [`call_openai_chat(...)`](backend/SampleAppIntegration.py)

Why bi‑directional checks matter
- Pre‑check blocks unsafe or non‑compliant prompts before they leave your app.
- Post‑check ensures model output also respects policy, reducing compliance risk.
- Same policies apply across apps and providers without rewriting logic.

---

## 6) Details of Backend APIs

Router entry
- Aggregator: [backend/app/api/router.py](backend/app/api/router.py)
- App factory: [backend/app/main.py](backend/app/main.py)

Policies
- Route module: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
- Endpoints
  - POST /api/policies
    - Body: { tenant_id: number, name: string, slug: string, description?: string, is_active?: boolean }
    - Creates a policy container for versions.
  - GET /api/policies?tenant_id=...&offset=...&limit=...
    - Lists policies for a tenant; includes basic metadata.
  - POST /api/policies/{policy_id}/versions
    - Body: { policy_id: number, document: object, is_active?: boolean }
    - Adds a new version (JSON policy doc). See schema: [backend/app/schemas/policy_format.py](backend/app/schemas/policy_format.py)
  - POST /api/policies/{policy_id}/versions/{version}/activate
    - Activates that version and deactivates others.
- Typical workflow: create → add version (document JSON) → activate.

Protect (evaluate text)
- Route: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
- Service: [`app.services.decision_service.protect`](backend/app/services/decision_service.py)
- Endpoint: POST /api/protect
- Request
  - { tenant_id: number, policy_slug: string, input_text: string, evidence_types?: string[] }
- Response
  - { allowed: boolean, reasons: string[], risk_score: number, request_log_id?: number, decision_log_id?: number }
- Notes
  - Reasons include both policy matching and risk rationales.
  - Risk threshold defaults from settings; can be encoded in policy docs as well.

Protect & Generate (one‑call orchestration)
- Route: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Service: [`app.services.governed_generation_service`](backend/app/services/governed_generation_service.py)
- Endpoint: POST /api/protect-generate
- Request (subset)
  - { tenant_id, policy_slug, input_text, evidence_types?, retrieval_query?, evidence_payloads?, llm? }
- Response
  - { allowed, risk_score, policy_reasons, risk_reasons, grounded_claims, raw_model_output, trace_id }

Evidence
- Route: [backend/app/api/routes/evidence.py](backend/app/api/routes/evidence.py)
- Typical endpoints
  - POST /api/evidence?tenant_id=... (ingest)
    - Body: { type: "url"|"text"|string, source?: string, description?: string, content?: string, policy_id?: number, policy_version_id?: number, metadata?: object }
  - GET /api/evidence/{id}?tenant_id=... (fetch)
- Frontend hook: [frontend/src/hooks/useEvidence.ts](frontend/src/hooks/useEvidence.ts)

Audit (list, detail, export)
- Route: [backend/app/api/routes/audit.py](backend/app/api/routes/audit.py)
- Endpoints
  - GET /api/audit/requests?tenant_id=...&offset=...&limit=...&date_from=...&date_to=...&client_ip=...&user_agent=...
    - Lists recent requests with optional filters.
  - GET /api/audit/decisions/{request_id}?tenant_id=...
    - Returns decision detail for a specific request.
  - GET /api/audit/export/{request_id}?format=json|html
    - Returns a compliance bundle (JSON or HTML) with section hashes.
    - Export implementation: [`ComplianceExportService`](backend/app/services/compliance_export.py)
- Docs and quick‑start guides
  - Manage policies: [backend/CreatePolicy.md](backend/CreatePolicy.md)
  - Deploy & integrate: [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)
  - Sample integration: [backend/SampleAPPIntegration.md](backend/SampleAPPIntegration.md)

Traces (correlation helper)
- Route: [backend/app/api/routes/traces.py](backend/app/api/routes/traces.py)
- Correlates RAG sessions and ledger trace ids for investigations.

Optional governance and LLM wiring
- LLM gateway (Ollama/OpenAI): [backend/app/services/llm_gateway.py](backend/app/services/llm_gateway.py)
- RAG proxy and sessions: [backend/app/services/rag_proxy.py](backend/app/services/rag_proxy.py)
- Governance ledger: [backend/app/services/governance_ledger.py](backend/app/services/governance_ledger.py)
- Dependency wiring (providers): [backend/app/core/deps.py](backend/app/core/deps.py)

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
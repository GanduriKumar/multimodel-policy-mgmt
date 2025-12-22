# Creating and managing policies (beginner-friendly)

This guide shows, step by step, how to create and use “policies.” It is written for beginners and avoids jargon.

Key ideas (simple)
- Tenant: the owner of policies (think “workspace”).
- Policy: a named container that can hold many versions.
- Policy version: a snapshot of rules. Only one version is active at a time.
- You don’t edit an existing version; you create a new version and (optionally) make it active.

Where things live (for reference)
- API routes (backend):
  - Policies: [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)
  - Protect (evaluate text): [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
  - Protect & Generate (one-call): [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Frontend (UI pages):
  - Policies page: [frontend/src/pages/Policies.tsx](frontend/src/pages/Policies.tsx) uses [frontend/src/hooks/usePolicies.ts](frontend/src/hooks/usePolicies.ts)
  - Protect page: [frontend/src/pages/Protect.tsx](frontend/src/pages/Protect.tsx)
  - Evidence page: [frontend/src/pages/Evidence.tsx](frontend/src/pages/Evidence.tsx)
  - Audit page: [frontend/src/pages/Audit.tsx](frontend/src/pages/Audit.tsx)

Before you start
- Start the backend:
  - macOS/Linux: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -m uvicorn app.main:app --reload --port 8000
  - Windows (PowerShell): cd backend && python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; python -m uvicorn app.main:app --reload --port 8000
- Open API docs: http://localhost:8000/docs
- Base URL used below: http://localhost:8000
- If your backend enforces an API key, add the header (example): -H "x-api-key: YOUR_KEY"

## A) Manage policies from the command line (CLI)

You can do everything below with curl. Replace numbers and slugs with your own.

Step 1 — Create a policy (empty container)
- Endpoint: POST /api/policies
- Fields: tenant_id (number), name, slug, description (optional), is_active (bool)

Example
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

Step 2 — Add a policy version (the rules)
- Endpoint: POST /api/policies/{policy_id}/versions
- Important: The JSON body must include "policy_id" matching the path, or the API returns 400.
- Document example (fields supported by the policy engine):
  - blocked_terms: list of words to block
  - allowed_sources: whitelisted sources
  - required_evidence_types: evidence tags you require (e.g., "url")
  - pii_rules: config for handling PII
  - risk_threshold: 0-100 number for risk sensitivity

Example
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

Step 3 — Activate a specific version (optional if you set is_active: true above)
- Endpoint: POST /api/policies/{policy_id}/versions/{version}/activate

Example
```bash
curl -X POST http://localhost:8000/api/policies/1/versions/2/activate
```

Step 4 — List policies (to verify)
- Endpoint: GET /api/policies?tenant_id=...&offset=...&limit=...

Example
```bash
curl "http://localhost:8000/api/policies?tenant_id=1&offset=0&limit=50"
```

Step 5 — Check some text against the active policy
- Endpoint: POST /api/protect
- Fields: tenant_id, policy_slug, input_text, evidence_types (optional list)

Example
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

One-call (optional): Protect & Generate (backend calls the LLM and does pre/post checks)
- Endpoint: POST /api/protect-generate

Example (short)
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

How to “modify” a policy (rules) from the CLI
- You don’t edit a version in place. Instead:
  1) Create a new version with updated "document" (Step 2).
  2) Activate that version (Step 3).
- This keeps history and makes rollbacks easy.

Updating policy metadata (name, slug, description, is_active)
- Current API routes expose create/list/add-version/activate only (see [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)).
- Direct “update policy” and “delete policy” endpoints are not exposed via HTTP in this version.
- Practical workaround today:
  - To change rules: create a new version and activate it (recommended).
  - To “retire” a policy: create a new version with rules that effectively block usage, or move clients to another policy.
- Note: The repository layer supports updates internally, but routes are intentionally minimal for now.

## B) Manage policies from the frontend UI (no coding)

The UI gives you simple screens to create policies and manage versions.

Open the app
- Start the frontend (from repo root):
  - cd frontend && npm install && npm run dev
  - Open http://localhost:5173
- Ensure VITE_API_BASE_URL points to your backend (see frontend/.env.example).

Create a policy (UI)
1) Go to “Policies” (top navigation).
2) At “Create Policy”:
   - Fill Name, Slug, Description (optional), and Active (checkbox).
   - Click “Create Policy.”
3) The policy appears in the table.

Load policies for a tenant (UI)
1) At the top of the Policies page, set Tenant ID (e.g., 1).
2) Click “Load Policies.” You will see:
   - ID, Name/Slug, Status (active/inactive), Created time.
   - A “Versioning” section for each row.

Add a version (UI)
1) In the policy row’s “Versioning” area:
   - Paste Version JSON (example below).
   - Leave “Active” checked to activate immediately (or uncheck to keep it inactive).
2) Click “Add Version.”
3) The UI shows the last added version number and whether it is active.

Example JSON to paste
```json
{
  "blocked_terms": ["forbidden", "secret sauce"],
  "allowed_sources": [],
  "required_evidence_types": ["url"],
  "pii_rules": { "mask_emails": true },
  "risk_threshold": 50
}
```

Activate a specific version (UI)
1) In the same policy row:
   - Enter a version number in “Version # to activate.”
   - Click “Activate.”
2) The backend marks that version active and deactivates others.

Test your policy quickly (UI)
- Go to “Protect” and:
  - Enter Tenant ID, Policy Slug, and the text to check.
  - Optionally include Evidence Types (CSV).
  - Submit and review “allowed” and “reasons.”

Add evidence (optional UI)
- Go to “Evidence” to attach items like URLs or text snippets that policies may require.
- You can ingest evidence and then reference it in your flows.

Audit what happened (UI)
- Go to “Audit” to inspect requests and decisions recorded by the backend.

What the UI supports today (and what it doesn’t)
- Supported now:
  - Create policy
  - List policies (by tenant)
  - Add policy versions
  - Activate a version
  - Evaluate text via “Protect”
  - Evidence ingestion and Audit browsing
- Not exposed in UI:
  - Update policy metadata (name/slug/description/is_active)
  - Delete a policy
- Work with versions to “modify rules”: add a new version and activate it (keeps history and is safest).

## Quick reference (copy/paste)

Create a policy (CLI)
```bash
curl -X POST http://localhost:8000/api/policies \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"name":"Content Safety","slug":"content-safety","description":"Blocks unsafe words","is_active":true}'
```

Add a version (CLI)
```bash
curl -X POST http://localhost:8000/api/policies/1/versions \
  -H "Content-Type: application/json" \
  -d '{"policy_id":1,"document":{"blocked_terms":["forbidden"],"allowed_sources":[],"required_evidence_types":["url"],"pii_rules":{},"risk_threshold":50},"is_active":true}'
```

Activate a version (CLI)
```bash
curl -X POST http://localhost:8000/api/policies/1/versions/2/activate
```

List policies (CLI)
```bash
curl "http://localhost:8000/api/policies?tenant_id=1&offset=0&limit=50"
```

Protect (evaluate text) (CLI)
```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"policy_slug":"content-safety","input_text":"this contains a forbidden word","evidence_types":[]}'
```

Frontend steps (short)
- Policies page: create policy → add version (paste JSON) → activate version if needed.
- Protect page: enter tenant, policy slug, text → submit → read reasons.
- Evidence page: ingest evidence if your policy requires it.
- Audit page: review requests and decisions.

Notes
- Only one version is active per policy.
- To change rules, add a new version and activate it (don’t edit older versions).
- If policy_id in the add-version request body doesn’t match the URL, the API returns 400 (by design in [backend/app/api/routes/policies.py](backend/app/api/routes/policies.py)).
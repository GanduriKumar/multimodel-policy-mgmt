# Deploy and integrate the backend (plain-English guide)

This guide explains, in simple terms, how to deploy the backend and place it between your app and your LLM provider.

What the backend does
- Checks user input and model output against policies (allow/block with reasons).
- Logs requests, decisions, and optional risk scores for auditing.
- Optionally appends to a tamper-evident ledger for governance.
- Offers a one-call orchestration endpoint: POST /api/protect-generate.

How it fits in
1) Your app gets user text.
2) Your app asks the backend: “Is this safe under policy X?”
3) If allowed, your app calls the LLM provider (or lets the backend do it via /api/protect-generate).
4) Optionally, check the LLM’s draft with the backend before showing it to the user.

Integration patterns
- Pre-check (recommended): Check user input before sending to LLM.
- Sandwich: Check both user input and the LLM’s output (before showing it).
- One-call orchestration: POST /api/protect-generate to let the backend handle both checks and the LLM call.
- Observe-only: Don’t block, just log and get risk signals (useful for early pilot).

Typical request to backend
- Endpoint: POST /api/protect
- Body: tenant_id, policy_slug, input_text, optional evidence_types
- Response: allowed (true/false), reasons

One-call orchestration
- Endpoint: POST /api/protect-generate
- Schema: [app/schemas/generation.py](app/schemas/generation.py)
- Route: [app/api/routes/protect_generate.py](app/api/routes/protect_generate.py)
- Service: [app/services/governed_generation_service.py](app/services/governed_generation_service.py)
- Minimal example:
```json
{
  "tenant_id": 1,
  "policy_slug": "content-safety",
  "user_input": "Draft a short policy overview.",
  "llm": { "provider": "openai", "model": "gpt-4o-mini" }
}
```

Deploy the backend

Option A — One machine (simple)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e . || pip install -r requirements.txt
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Option B — Docker (portable)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t policy-backend -f Dockerfile .
docker run -d --name policy-backend -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./app.db \
  -e ALLOW_ORIGINS=* \
  policy-backend
```

Option C — PaaS (Render, Fly.io, Heroku, Azure App Service)
- Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Set environment variables in the platform dashboard.

Config checklist (prod-friendly)
- DATABASE_URL: use Postgres in production.
- ALLOW_ORIGINS: frontend origin (e.g., https://your-frontend.app).
- APP_VERSION: app version shown in /api/version.
- LLM provider settings:
  - OPENAI_API_KEY for OpenAI (used by LLM gateway) [app/services/llm_gateway.py](app/services/llm_gateway.py)
- Governance ledger (optional):
  - GOVERNANCE_LEDGER_PATH, GOVERNANCE_LEDGER_HMAC_SECRET
  - Implementation: [app/services/governance_ledger.py](app/services/governance_ledger.py)
- Groundedness (optional output-evidence scoring):
  - [app/services/groundedness_engine.py](app/services/groundedness_engine.py)

Wire your app to the backend (pre + post check)

JavaScript/TypeScript
```typescript
async function guardLLM(userText: string) {
  const pre = await fetch("/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: 1, policy_slug: "content-safety", input_text: userText, evidence_types: [] }),
  }).then(r => r.json());
  if (!pre.allowed) return { error: "Blocked by policy", reasons: pre.reasons };

  // call provider...
  const draft = "...";

  const post = await fetch("/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: 1, policy_slug: "content-safety", input_text: draft, evidence_types: [] }),
  }).then(r => r.json());
  if (!post.allowed) return { error: "Output blocked by policy", reasons: post.reasons };

  return { content: draft };
}
```

One-call client example
```bash
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "user_input": "Summarize our policy.",
    "llm": { "provider": "openai", "model": "gpt-4o-mini" }
  }'
```

Observability
- Health: GET /api/health
- Version: GET /api/version
- Audit queries: [app/api/routes/audit.py](app/api/routes/audit.py)
- Errors: standardized JSON in [app/core/errors.py](app/core/errors.py)

Troubleshooting
- CORS: set ALLOW_ORIGINS to your frontend.
- Imports: run from backend dir; ensure venv and deps installed.
- DB: confirm DATABASE_URL and that tables exist (create_all snippet above).
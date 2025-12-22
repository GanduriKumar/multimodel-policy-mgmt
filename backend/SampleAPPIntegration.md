# Bidirectional backend integration example (Python)

This example shows how to place the backend between your app and an LLM:
- Pre-check the user prompt with the backend (/api/protect).
- If allowed, call the LLM (OpenAI REST).
- Post-check the LLM draft with the backend before returning it.
- Alternative: call the one-step orchestration endpoint (/api/protect-generate).

Files
- Runner script: [backend/SampleAppIntegration.py](backend/SampleAppIntegration.py)
- Protect route: [backend/app/api/routes/protect.py](backend/app/api/routes/protect.py)
- One-call orchestration route: [backend/app/api/routes/protect_generate.py](backend/app/api/routes/protect_generate.py)
- Orchestrator service: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)
- Decision orchestration: [backend/app/services/decision_service.py](backend/app/services/decision_service.py)

Prerequisites
- Backend running locally:
  - make run (see [backend/Makefile](backend/Makefile) and [backend/Makefile.md](backend/Makefile.md))
  - or: python -m uvicorn app.main:app --reload --port 8000
- Policy exists and has an active version (see [backend/CreatePolicy.md](backend/CreatePolicy.md))
- Environment:
  - OPENAI_API_KEY: your OpenAI key (if using OpenAI via LLM gateway)
  - Optional:
    - BACKEND_URL (default http://localhost:8000)
    - BACKEND_API_KEY (if backend enforces API keys)
    - BACKEND_API_KEY_HEADER (default x-api-key)
    - OPENAI_MODEL (default gpt-4o-mini)

How it works
1) Your app asks the backend if text is allowed under a policy:
   - POST /api/protect with tenant_id, policy_slug, input_text
2) If allowed, your app calls the LLM provider.
3) Optionally, send the model output back to /api/protect for a post-check.

Run

- Prompt via CLI argument:
  - python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --prompt "Hello!"

- Prompt via STDIN:
  - echo "Summarize: ..." | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety

- JSON output (includes pre/post decisions and content):
  - echo "Hello" | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --json

Options (CLI)
- --tenant-id: Tenant identifier used by backend policies
- --policy-slug: Policy slug to enforce (e.g., content-safety)
- --prompt: Prompt text; omit to read from STDIN
- --evidence-types: Comma-separated tags like url,document
- --backend-url: Backend base URL (default http://localhost:8000)
- --backend-api-key / --backend-api-key-header: API key configuration if enforced
- --openai-api-key / --openai-model: LLM provider credentials and model
- --json: Emit a machine-readable JSON result

Alternative: one-call orchestration
- Let the backend pre-check, call the LLM, run safety checks, and post-check in one request.
- Endpoint: POST /api/protect-generate
- Schema: [backend/app/schemas/generation.py](backend/app/schemas/generation.py)
- Service: [backend/app/services/governed_generation_service.py](backend/app/services/governed_generation_service.py)

Example
```bash
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "Draft a brief policy summary.",
    "evidence_types": [],
    "retrieval_query": "policy overview",
    "llm": { "provider": "openai", "model": "gpt-4o-mini" }
  }'
```

Response (shape)
- allowed: boolean
- risk_score: number
- policy_reasons: string[]
- risk_reasons: string[]
- grounded_claims: array of claims with scores
- raw_model_output: string
- trace_id: string

Troubleshooting
- 400/500 from /api/protect: ensure tenant_id, policy_slug, and input_text are set and backend is running.
- 400/500 from /api/protect-generate: ensure payload uses input_text (not user_input), and optional fields match the schema.
- Empty output: ensure OPENAI_API_KEY is configured and your model name is valid.
- CORS or auth errors (for web apps): use the correct API key header name; see settings in backend.
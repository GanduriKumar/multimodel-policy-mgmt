# Deploy and integrate the backend (plain-English guide)

This guide explains, in simple terms, how to deploy the backend and place it between your app and your LLM provider (OpenAI, Azure OpenAI, Anthropic, etc.).

What the backend does
- Checks user input and model output against policies (allow/block with reasons).
- Logs requests, decisions, and optional risk scores for auditing.
- Gives your app a simple yes/no answer before calling the LLM.

How it fits in
1) Your app gets user text.
2) Your app asks the backend: “Is this safe under policy X?”
3) If allowed, your app calls the LLM provider.
4) Optionally, check the LLM’s draft with the backend before showing it to the user.

Think of it as a gate in front of the LLM (and optionally after).

Integration patterns
- Pre-check (recommended): Check user input before sending to LLM.
- Sandwich: Check both user input and the LLM’s output (before showing it).
- Observe-only: Don’t block, just log and get risk signals (useful for early pilot).

Typical request to backend
- Endpoint: POST /api/protect
- Body:
  - policy_slug (which rules to use)
  - input_text (text to check)
  - evidence_types (optional tags like "url" if you have supporting evidence)

Example response
- allowed: true/false
- reasons: list of strings explaining the decision

Deploy the backend

Option A — One machine (simple)
- Requirements: Python 3.11+, a server (Linux VM), and a way to keep a process running (systemd or screen/tmux).
- Steps:
  1) Copy the repository to the server.
  2) Create a virtual environment and install dependencies.
  3) Set environment variables (see “Config checklist” below).
  4) Run Uvicorn (or use the Makefile).

```bash
# On the server
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e . || pip install -r requirements.txt

# Create DB tables (if you don’t use migrations)
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

# Run the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Option B — Docker (portable)
- Build once, run anywhere with Docker.

```dockerfile
# Dockerfile (simple production-ish)
FROM python:3.11-slim

WORKDIR /app
COPY backend /app
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (container)
EXPOSE 8000

# Start the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t policy-backend -f Dockerfile .
docker run -d --name policy-backend -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./app.db \
  -e ALLOW_ORIGINS=* \
  policy-backend
```

Option C — PaaS (Render, Fly.io, Heroku, Azure App Service)
- Point the service to run: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Set environment variables in the platform dashboard.
- Attach a managed database if you want a durable Postgres instead of SQLite.

Config checklist (prod-friendly)
- DATABASE_URL: use Postgres in production (e.g., postgresql://user:pass@host/dbname).
- ALLOW_ORIGINS: CORS for your frontend domain (e.g., https://your-frontend.app).
- APP_VERSION: app version displayed in /api/version.
- API key secret (if you enforce it): configure your auth header and key secret.
- HTTPS: terminate TLS at your reverse proxy or platform.
- Reverse proxy (optional): Nginx or cloud LB in front of Uvicorn.

Health and readiness
- Health: GET /api/health -> {"status": "ok"}
- Version: GET /api/version -> {"version": "x.y.z"}

Wire your app to the backend (before LLM call)

JavaScript/TypeScript (frontend/server)
```typescript
// Pre-check user input, then call LLM if allowed
async function protectAndCallLLM(userText: string) {
  // 1) Ask backend to check the text
  const protectRes = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // "x-api-key": "YOUR_API_KEY", // if your backend requires it
    },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: userText,
      evidence_types: [], // optional
    }),
  });

  const decision = await protectRes.json();
  if (!decision.allowed) {
    return { error: "Blocked by policy", reasons: decision.reasons };
  }

  // 2) Safe to call the LLM provider
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

  // 3) Optional post-check (sandwich pattern)
  const postCheck = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: draft,
      evidence_types: [],
    }),
  }).then(r => r.json());

  if (!postCheck.allowed) {
    return { error: "Model output blocked by policy", reasons: postCheck.reasons };
  }

  return { content: draft };
}
```

Python (server)
```python
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "https://your-backend.app")
API_KEY = os.getenv("BACKEND_API_KEY")  # if enforced

def protect(text: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(
        f"{BACKEND_URL}/api/protect",
        json={"policy_slug": "content-safety", "input_text": text, "evidence_types": []},
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def call_llm(text: str) -> str:
    # Example: OpenAI; replace with your provider
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

Set up policies
- Use the simple guide in CreatePolicies.md (in this folder) to create a policy and add a version with rules.
- For quick tests, use the CLI tool:
  - echo "some text" | python -m app.tools.run_policy --policy path/to/policy.json

Observability
- Logs: captured by Uvicorn/your platform logs.
- Auditing: list requests/decisions via the audit endpoints.
- Errors: standardized JSON error shape; see /docs and core/errors.

Troubleshooting
- CORS issues: set ALLOW_ORIGINS to your frontend URL or “*” for testing.
- “Module not found”: ensure you’re running from the backend directory and dependencies are installed in the active environment.
- Database issues: confirm DATABASE_URL, network access (for managed DB), and that tables exist (run the create_all snippet if not using migrations).
```// filepath: backend/Deploy&Integrate.md
# Deploy and integrate the backend (plain-English guide)

This guide explains, in simple terms, how to deploy the backend and place it between your app and your LLM provider (OpenAI, Azure OpenAI, Anthropic, etc.).

What the backend does
- Checks user input and model output against policies (allow/block with reasons).
- Logs requests, decisions, and optional risk scores for auditing.
- Gives your app a simple yes/no answer before calling the LLM.

How it fits in
1) Your app gets user text.
2) Your app asks the backend: “Is this safe under policy X?”
3) If allowed, your app calls the LLM provider.
4) Optionally, check the LLM’s draft with the backend before showing it to the user.

Think of it as a gate in front of the LLM (and optionally after).

Integration patterns
- Pre-check (recommended): Check user input before sending to LLM.
- Sandwich: Check both user input and the LLM’s output (before showing it).
- Observe-only: Don’t block, just log and get risk signals (useful for early pilot).

Typical request to backend
- Endpoint: POST /api/protect
- Body:
  - policy_slug (which rules to use)
  - input_text (text to check)
  - evidence_types (optional tags like "url" if you have supporting evidence)

Example response
- allowed: true/false
- reasons: list of strings explaining the decision

Deploy the backend

Option A — One machine (simple)
- Requirements: Python 3.11+, a server (Linux VM), and a way to keep a process running (systemd or screen/tmux).
- Steps:
  1) Copy the repository to the server.
  2) Create a virtual environment and install dependencies.
  3) Set environment variables (see “Config checklist” below).
  4) Run Uvicorn (or use the Makefile).

```bash
# On the server
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e . || pip install -r requirements.txt

# Create DB tables (if you don’t use migrations)
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

# Run the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Option B — Docker (portable)
- Build once, run anywhere with Docker.

```dockerfile
# Dockerfile (simple production-ish)
FROM python:3.11-slim

WORKDIR /app
COPY backend /app
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (container)
EXPOSE 8000

# Start the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t policy-backend -f Dockerfile .
docker run -d --name policy-backend -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./app.db \
  -e ALLOW_ORIGINS=* \
  policy-backend
```

Option C — PaaS (Render, Fly.io, Heroku, Azure App Service)
- Point the service to run: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Set environment variables in the platform dashboard.
- Attach a managed database if you want a durable Postgres instead of SQLite.

Config checklist (prod-friendly)
- DATABASE_URL: use Postgres in production (e.g., postgresql://user:pass@host/dbname).
- ALLOW_ORIGINS: CORS for your frontend domain (e.g., https://your-frontend.app).
- APP_VERSION: app version displayed in /api/version.
- API key secret (if you enforce it): configure your auth header and key secret.
- HTTPS: terminate TLS at your reverse proxy or platform.
- Reverse proxy (optional): Nginx or cloud LB in front of Uvicorn.

Health and readiness
- Health: GET /api/health -> {"status": "ok"}
- Version: GET /api/version -> {"version": "x.y.z"}

Wire your app to the backend (before LLM call)

JavaScript/TypeScript (frontend/server)
```typescript
// Pre-check user input, then call LLM if allowed
async function protectAndCallLLM(userText: string) {
  // 1) Ask backend to check the text
  const protectRes = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // "x-api-key": "YOUR_API_KEY", // if your backend requires it
    },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: userText,
      evidence_types: [], // optional
    }),
  });

  const decision = await protectRes.json();
  if (!decision.allowed) {
    return { error: "Blocked by policy", reasons: decision.reasons };
  }

  // 2) Safe to call the LLM provider
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

  // 3) Optional post-check (sandwich pattern)
  const postCheck = await fetch("https://your-backend.app/api/protect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_slug: "content-safety",
      input_text: draft,
      evidence_types: [],
    }),
  }).then(r => r.json());

  if (!postCheck.allowed) {
    return { error: "Model output blocked by policy", reasons: postCheck.reasons };
  }

  return { content: draft };
}
```

Python (server)
```python
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "https://your-backend.app")
API_KEY = os.getenv("BACKEND_API_KEY")  # if enforced

def protect(text: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(
        f"{BACKEND_URL}/api/protect",
        json={"policy_slug": "content-safety", "input_text": text, "evidence_types": []},
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def call_llm(text: str) -> str:
    # Example: OpenAI; replace with your provider
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

Set up policies
- Use the simple guide in CreatePolicies.md (in this folder) to create a policy and add a version with rules.
- For quick tests, use the CLI tool:
  - echo "some text" | python -m app.tools.run_policy --policy path/to/policy.json

Observability
- Logs: captured by Uvicorn/your platform logs.
- Auditing: list requests/decisions via the audit endpoints.
- Errors: standardized JSON error shape; see /docs and core/errors.

Troubleshooting
- CORS issues: set ALLOW_ORIGINS to your frontend URL or “*” for testing.
- “Module not found”: ensure you’re running from the backend directory and dependencies are installed in the active environment.
- Database issues: confirm DATABASE_URL, network access (for managed DB), and that tables exist (run the create_all snippet if not using migrations).
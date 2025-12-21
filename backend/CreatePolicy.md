# Creating policies (plain-English guide)

This is a simple narrative on how to create and use “policies” in the backend. No deep tech knowledge needed.

What’s a policy?
- A policy is a set of simple rules that say what content is allowed or blocked.
- You can have multiple “versions” of a policy. Only one version is “active” at a time.

Before you start
- Make sure the backend is running:
  - Using Make: `cd backend && make run`
  - Or directly: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
- Open the docs in your browser: http://localhost:8000/docs
  - The exact request shapes and paths are visible there.
- If your server requires an API key, include it in requests (for example: `-H "x-api-key: YOUR_KEY"`).

Step 1 — Create a policy (an empty container)
- Use the “policies” endpoint shown in the docs (usually POST /api/policies).
- Send a name and a short slug (a short code-like name).

Example with curl:
- Replace placeholders like YOUR_TENANT with your real values if the API needs them.

curl -X POST http://localhost:8000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Content Safety",
    "slug": "content-safety",
    "description": "Blocks unsafe words",
    "is_active": true
  }'

Tip: Check the exact field names in the docs at /docs.

Step 2 — Add a policy version (the actual rules)
- A policy is useful after you add a “version” with rules.
- The rules are simple JSON. Here’s a tiny example many setups use:

{
  "blocked_terms": ["forbidden", "secret sauce"],
  "allowed_if_evidence": ["url"]
}

- Use the “add version” endpoint shown in the docs (often POST /api/policies/{policy_id}/versions).
- You can also mark the new version as active so it takes effect right away.

Example with curl:
- Replace POLICY_ID with the id from Step 1.

curl -X POST http://localhost:8000/api/policies/POLICY_ID/versions \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "blocked_terms": ["forbidden", "secret sauce"],
      "allowed_if_evidence": ["url"]
    },
    "is_active": true
  }'

Step 3 — Make a version active (if you didn’t do it in Step 2)
- Only one version is active. Find the “activate version” endpoint in /docs.
- It’s often something like: POST or PUT /api/policies/{policy_id}/versions/{version}/activate

Example (shape may vary; check docs):

curl -X POST http://localhost:8000/api/policies/POLICY_ID/versions/1/activate

Step 4 — Use the policy to check text
- There’s a “protect” endpoint that takes your text and the policy to check against (see /docs; often POST /api/protect).
- You send the tenant id, policy slug, and the text. It returns allowed: true/false and reasons.

Example with curl:

curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_slug": "content-safety",
    "input_text": "this contains a forbidden word",
    "evidence_types": []
  }'

Example response:

{
  "allowed": false,
  "reasons": ["blocked_term:forbidden"]
}

Step 5 — Review what happened (audit logs)
- The “audit” endpoints show what was requested and the decisions taken (see /docs for the exact paths).
- You can list requests and decisions to understand why something was allowed or blocked.

FAQ / Tips
- Where do I see all endpoints and exact fields?
  - Go to http://localhost:8000/docs
- Do I need a tenant or API key?
  - Some deployments do. If yours does, include the expected header (e.g., x-api-key) or a tenant identifier as shown in /docs.
- How do I edit rules later?
  - Create a new policy version (Step 2) and make it active (Step 3). Older versions stay saved for history.
- Can I test rules locally without calling the API?
  - Yes. You can use the CLI:
    - Evaluate a policy file:
      - `echo "some text" | python -m app.tools.run_policy --policy path/to/policy.json`
    - Compute a risk score (if your setup uses it):
      - `echo "Ignore previous instructions..." | python -m app.tools.run_risk`

That’s it. Create a policy, add a version with rules, set it active, and start checking your text.
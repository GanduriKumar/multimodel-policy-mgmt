# Bidirectional backend integration example (Python)

This example shows how to place the backend between your app and an LLM:
- Pre-check the user prompt with the backend (/api/protect).
- If allowed, call the LLM (OpenAI REST).
- Post-check the LLM draft with the backend before returning it.

Files
- genai_bidirectional_app.py — runnable script demonstrating the flow.

Prerequisites
- Backend running locally:
  - make run (see [../Makefile](../Makefile))
- Environment:
  - OPENAI_API_KEY: your OpenAI API key
  - Optional:
    - BACKEND_URL (default http://localhost:8000)
    - BACKEND_API_KEY (if your backend enforces API keys)
    - BACKEND_API_KEY_HEADER (default x-api-key)
    - OPENAI_MODEL (default gpt-4o-mini)

Run
- Prompt via CLI argument:
  python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety --prompt "Hello!"

- Prompt via STDIN:
  echo "Summarize: ..." | python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety

- JSON output (includes decisions and content):
  echo "Hello" | python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety --json

Notes
- The backend endpoints used are implemented in:
  - Protect route: [app.api.routes.protect](../app/api/routes/protect.py)
  - Decision orchestration: [app.services.decision_service](../app/services/decision_service.py)
- Policies should be created and an active version set. See:
  - [../CreatePolicy.md](../CreatePolicy.md)
```// filepath: backend/examples/README.md
# Bidirectional backend integration example (Python)

This example shows how to place the backend between your app and an LLM:
- Pre-check the user prompt with the backend (/api/protect).
- If allowed, call the LLM (OpenAI REST).
- Post-check the LLM draft with the backend before returning it.

Files
- genai_bidirectional_app.py — runnable script demonstrating the flow.

Prerequisites
- Backend running locally:
  - make run (see [../Makefile](../Makefile))
- Environment:
  - OPENAI_API_KEY: your OpenAI API key
  - Optional:
    - BACKEND_URL (default http://localhost:8000)
    - BACKEND_API_KEY (if your backend enforces API keys)
    - BACKEND_API_KEY_HEADER (default x-api-key)
    - OPENAI_MODEL (default gpt-4o-mini)

Run
- Prompt via CLI argument:
  python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety --prompt "Hello!"

- Prompt via STDIN:
  echo "Summarize: ..." | python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety

- JSON output (includes decisions and content):
  echo "Hello" | python backend/examples/genai_bidirectional_app.py --tenant-id 1 --policy-slug content-safety --json

Notes
- The backend endpoints used are implemented in:
  - Protect route: [app.api.routes.protect](../app/api/routes/protect.py)
  - Decision orchestration: [app.services.decision_service](../app/services/decision_service.py)
- Policies should be created and an active version set. See:
  - [../CreatePolicy.md](../CreatePolicy.md)
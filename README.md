# Multimodel Policy Management (Monorepo)

Monorepo containing a Python FastAPI backend and a React (Vite + TypeScript) frontend for multimodel policy management. Architecture, layering, DI, testing, error handling, and logging follow the principles in the authoritative document: [constitution.md](./constitution.md).

## Repository structure

- backend/ — FastAPI application, domain/services, repositories, and tests
- frontend/ — Vite + React TypeScript UI
- constitution.md — architectural rules and guidelines

Key backend modules (non-exhaustive):
- app/core: hashing, patterns (detectors), auth, config, logging, errors, DI deps, contracts
- app/services: risk_engine, policy_engine, decision_service, auth_service
- app/db: SQLAlchemy engine/session and Declarative Base
- app/models: tenant, policy, policy_version, evidence_item, request_log, decision_log, risk_score
- app/repos: policy_repo, evidence_repo, audit_repo, tenant_repo
- app/api: router and route modules (protect, policies, evidence, audit)
- app/tools: CLI entry points (run_risk.py, run_policy.py)
- app/main.py: FastAPI app entry

## Prerequisites

- Python 3.11+
- Node.js 18+ (or 20+)
- npm (or pnpm/yarn)

---

## Backend: setup and run

1) Create and activate a virtual environment

- Windows PowerShell
	- cd backend
	- py -3.11 -m venv .venv
	- .\.venv\Scripts\Activate.ps1

2) Install dependencies

- Using pip
	- python -m pip install --upgrade pip
	- pip install -e .

- Using uv (optional)
	- uv pip install -e .

3) Configure environment (optional defaults shown)

- DATABASE_URL=sqlite:///./app.db
- SQLALCHEMY_ECHO=0
- ALLOW_ORIGINS=*
- API key HMAC secret (choose one): API_KEY_SECRET, AUTH_SECRET, SECRET_KEY, APP_AUTH_SECRET

4) Run the API server

- cd backend
- uvicorn app.main:app --reload --port 8000

Health and version:
- GET http://localhost:8000/api/health
- GET http://localhost:8000/api/version

Primary endpoint:
- POST http://localhost:8000/api/protect

CLI helpers (optional):
- python -m app.tools.run_risk < input.txt
- python -m app.tools.run_policy --policy policy.json < input.txt

---

## Running tests (backend)

From repo root or backend/:

- All tests (unit + integration + API)
	- pytest -q

- Run a specific test module
	- pytest -q backend/tests/test_hashing.py
	- pytest -q backend/tests/test_policy_engine.py
	- pytest -q backend/tests/test_api_protect.py

- Filter tests by keyword
	- pytest -q -k risk_engine

- With coverage
	- pytest -q --cov=app --cov-report=term-missing

Notes
- Tests use a temp SQLite database and do not require external services.
- API tests use FastAPI TestClient with dependency overrides where needed.

---

## Frontend: setup and run

1) Configure environment

- cd frontend
- Copy .env.example to .env and update values as needed:
	- VITE_API_BASE_URL=http://localhost:8000
	- VITE_API_KEY=your-dev-api-key

2) Install and start

- npm install
- npm run dev

App will be available at:
- http://localhost:5173

Build for production:
- npm run build
- npm run preview

---

## Docker Compose (optional)

If you prefer containers, save the example below as docker-compose.yml in the repo root, then run the commands in the Usage section.

Example docker-compose.yml:

```yaml
version: '3.9'
services:
	backend:
		build:
			context: ./backend
		working_dir: /app
		environment:
			DATABASE_URL: sqlite:////data/app.db
			ALLOW_ORIGINS: "*"
			API_KEY_SECRET: "dev-secret"
		volumes:
			- backend_data:/data
		ports:
			- "8000:8000"
		command: uvicorn app.main:app --host 0.0.0.0 --port 8000

	frontend:
		build:
			context: ./frontend
		environment:
			VITE_API_BASE_URL: http://localhost:8000
			VITE_API_KEY: dev-frontend-key
		ports:
			- "5173:5173"
		command: npm run dev -- --host 0.0.0.0 --port 5173
		depends_on:
			- backend

volumes:
	backend_data:
```

Usage:
- docker compose up --build
- Open http://localhost:8000 (API) and http://localhost:5173 (UI)
- docker compose down

Notes
- This setup uses SQLite for persistence inside a named volume (backend_data).
- For production, consider a managed database and production builds (e.g., serve frontend as static files).

---

## Troubleshooting

- If the API fails to start, check environment variables and Python dependencies in backend/.
- If the frontend cannot reach the API, ensure VITE_API_BASE_URL is set to the API origin and CORS is configured (ALLOW_ORIGINS).
- On Windows PowerShell, execution policy might block venv activation; run PowerShell as Administrator and set-ExecutionPolicy RemoteSigned if needed.

## Contributing

- Follow the testing pyramid and the architectural rules in constitution.md.
- Keep business logic in services/engines; routes are thin delegators.
- Add/maintain tests for all changes before submitting PRs.
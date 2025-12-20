# Multimodel Policy Management (Monorepo)

This repository is a monorepo that hosts both backend and frontend for Multimodel Policy Management.

- Architecture, layering, DI, testing strategy, naming, error handling, and logging are governed by the authoritative document: [constitution.md](./constitution.md).

## Repository structure

Top-level packages:
- `backend/` — server-side services and APIs (implementation follows the constitution; no business logic in route handlers).
- `frontend/` — client/UI application.

Key backend additions (MVP):
- `backend/app/core/`
	- `hashing.py` — deterministic SHA-256 helpers for text and JSON.
	- `patterns.py` — simple detectors for prompt injection, secrets, PII.
	- `auth.py` — HMAC-SHA256 API key hashing/verification via env secret.
	- `contracts.py` — repository Protocols (TenantRepo, PolicyRepo, EvidenceRepo, AuditRepo).
	- `deps.py` — DI wiring for repos and the decision service.
- `backend/app/schemas/`
	- `policy_format.py` — Pydantic `PolicyDoc` schema.
- `backend/app/services/`
	- `risk_engine.py` — risk scoring from detectors.
	- `policy_engine.py` — evaluate policy rules and evidence.
	- `decision_service.py` — orchestrates request logging, policy evaluation, and risk.
- `backend/app/db/`
	- `session.py` — SQLAlchemy engine/session and `get_db()` dependency.
	- `base.py` — Declarative Base and model auto-import hook.
- `backend/app/models/`
	- `tenant.py` — adds `api_key_hash` (nullable, unique) and timestamps.
	- `policy.py`, `policy_version.py` — policies and version snapshots (JSON document).
	- `evidence_item.py`, `request_log.py`, `decision_log.py`, `risk_score.py` — audit and evidence entities.
- `backend/app/repos/`
	- `policy_repo.py` — create/list policies, add/activate versions, fetch active doc.
	- `evidence_repo.py` — create/get/list evidence with deterministic content hashing.
	- `audit_repo.py` — request/decision logging helpers.
	- `tenant_repo.py` — create tenant with API key hash and lookups.
- `backend/app/api/`
	- `router.py` — shared APIRouter aggregator (best-effort includes sub-routers).
	- `routes/protect.py` — `POST /api/protect` endpoint using DecisionService.
- `backend/app/tools/`
	- `run_risk.py` — CLI: score text from stdin.
	- `run_policy.py` — CLI: evaluate policy JSON against stdin text.
- `backend/app/main.py` — FastAPI app with CORS and health/version endpoints.
- `backend/tests/`
	- `conftest.py` — isolated temp-file SQLite for tests.
	- Fakes for unit tests: `tests/fakes.py`.
	- Unit/integration tests for core, services, repos, and API.

## Getting started
1) Read the [constitution.md](./constitution.md) before making changes.
2) Work inside the corresponding package folder (`backend/` or `frontend/`).
3) Keep business logic in the Application/Domain layers; adapters in Infrastructure; routes/controllers only delegate.

Backend quickstart:
- Python 3.11+ recommended.
- From `backend/`, install dependencies per `pyproject.toml` (e.g., `pip install -e .` or your preferred tool).
- Environment variables (optional):
	- `DATABASE_URL` (default: `sqlite:///./app.db`)
	- `SQLALCHEMY_ECHO` ("1" to enable SQL echo)
	- `ALLOW_ORIGINS` (CORS, comma-separated or "*")
	- API key HMAC secret (one of): `API_KEY_SECRET`, `AUTH_SECRET`, `SECRET_KEY`, `APP_AUTH_SECRET`
- Run API locally:
	- `cd backend` then `uvicorn app.main:app --reload`
	- Health: `GET /api/health`, Version: `GET /api/version`
	- Protect endpoint is defined in `app.api.routes.protect`. Include its router in your app if not already aggregated.

Testing:
- From repo root or `backend/`, run `pytest -q`.
	- Tests cover hashing, detectors, risk/policy engines, repositories, decision service, and API route with dependency override.

## Contributing
- Follow the testing pyramid (unit > integration > API) and enforce import/layer boundaries.
- Submit PRs that pass CI checks and respect the review checklist in the constitution.
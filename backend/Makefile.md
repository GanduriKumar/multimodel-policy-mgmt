# Makefile usage guide

This Makefile streamlines common dev tasks so you can run and test the backend independently and consistently.

## Prerequisites
- Python 3.10+ available on PATH
- Bash shell (macOS/Linux natively; on Windows use Git Bash, WSL, or run the raw commands shown below)
- Project dependencies installed:
  - If using requirements: `pip install -r requirements.txt`
  - If using pyproject: `pip install -e .`

Recommended virtual environment:
- macOS/Linux:
  - `python -m venv .venv && source .venv/bin/activate`
- Windows (PowerShell):
  - `python -m venv .venv; .\.venv\Scripts\Activate.ps1`

## Core targets

- Run the API (with auto-reload for local dev)
  - `make run`
  - Starts: `uvicorn app.main:app --reload --port 8000`
  - Browse: http://127.0.0.1:8000 and OpenAPI at http://127.0.0.1:8000/docs

- Run all tests
  - `make test`

- Run grouped tests
  - Unit: `make test-unit`
  - Integration: `make test-integration`
  - API: `make test-api`

- Lint and format
  - Lint check: `make lint` (Ruff lint + format check)
  - Apply formatting: `make format` (Ruff format)

## Environment variables

- APP_VERSION to surface version in `/api/version`
  - `APP_VERSION=0.1.0 make run`
- ALLOW_ORIGINS to configure CORS (comma-separated or `*`)
  - `ALLOW_ORIGINS=http://localhost:5173 make run`

These are read by the FastAPI app at startup.

## Overriding tools

The Makefile exposes variables you can override per-invocation:
- `PYTHON` (default: `python`)
- `PYTEST` (default: `pytest`)
- `UVICORN` (default: `uvicorn`)
- `RUFF` (default: `ruff`)

Examples:
- Use a specific Python: `PYTHON=.venv/bin/python make test`
- Use a specific uvicorn: `UVICORN=.venv/bin/uvicorn make run`

## Running without Make

If you can’t use Bash (e.g., plain Windows cmd), run the underlying commands:
- Run API: `python -m uvicorn app.main:app --reload --port 8000`
- All tests: `python -m pytest -q`
- Lint: `python -m ruff check app tests`
- Format: `python -m ruff format app tests`

## How this helps independent backend runs

- Single-command startup: `make run` hides uvicorn flags and env nuances.
- Repeatable workflows: consistent test, lint, and format commands across machines.
- CI-friendly: same targets can be invoked in pipelines.
- Dev ergonomics: less command memorization; faster iteration.

## Troubleshooting

- “bash not found” on Windows: use Git Bash or WSL, or run the raw commands above.
- “module not found”: ensure you’re in the `backend` directory and the venv is activated.
- Uvicorn import errors: install deps in the active environment (`pip install -r requirements.txt` or `pip install -e .`).
# Multimodel Policy Management (Monorepo)

This repository is a monorepo that hosts both backend and frontend for Multimodel Policy Management.

- Architecture, layering, DI, testing strategy, naming, error handling, and logging are governed by the authoritative document: [constitution.md](./constitution.md).

## Repository structure

Top-level packages:
- `backend/` — server-side services and APIs (implementation follows the constitution; no business logic in route handlers).
- `frontend/` — client/UI application.

## Getting started
1) Read the [constitution.md](./constitution.md) before making changes.
2) Work inside the corresponding package folder (`backend/` or `frontend/`).
3) Keep business logic in the Application/Domain layers; adapters in Infrastructure; routes/controllers only delegate.

## Contributing
- Follow the testing pyramid (unit > integration > API) and enforce import/layer boundaries.
- Submit PRs that pass CI checks and respect the review checklist in the constitution.
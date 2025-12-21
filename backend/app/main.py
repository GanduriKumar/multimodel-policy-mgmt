"""
FastAPI application entrypoint.

- Configures CORS.
- Registers standardized error handlers.
- Initializes structured logging.
- Includes infra routes (health/version) and aggregates API sub-routers.

Run locally:
  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import register_exception_handlers
from app.core.logging import init_logging
from app.api.router import router as api_router


def _create_cors_origins() -> List[str]:
    """
    Build the list of allowed CORS origins.

    Reads from ALLOW_ORIGINS (comma-separated). Defaults to "*" if unset.
    """
    raw = os.getenv("ALLOW_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def _create_infra_router() -> APIRouter:
    """
    Create a minimal API router with non-business endpoints (health, version).
    """
    router = APIRouter(prefix="/api", tags=["infra"])

    @router.get("/health")
    def health() -> dict:
        # Simple health probe
        return {"status": "ok"}

    @router.get("/version")
    def version() -> dict:
        # Basic version info via environment variable or default
        return {"version": os.getenv("APP_VERSION", "0.1.0")}

    return router


def get_application() -> FastAPI:
    """
    Construct the FastAPI app with CORS, logging, routers, and error handlers.
    """
    # Initialize structured logging early (idempotent)
    try:
        init_logging()
    except Exception:
        # Logging initialization failures should not prevent app startup
        pass

    app = FastAPI(title="Policy Management API", version=os.getenv("APP_VERSION", "0.1.0"))

    # Configure CORS (defaults; can be tightened via env)
    origins = _create_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include infra and aggregated API routers
    app.include_router(_create_infra_router())
    app.include_router(api_router)

    # Register standardized error handlers
    register_exception_handlers(app)

    # Optional root route (informational only)
    @app.get("/")
    def root() -> dict:
        return {"message": "Policy Management API", "health": "/api/health"}

    return app


# ASGI application
app = get_application()
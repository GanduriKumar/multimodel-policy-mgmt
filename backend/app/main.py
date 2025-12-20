"""
FastAPI application entrypoint.

- Configures CORS.
- Registers a basic API router.
- Avoids business logic (infrastructure only).
"""

from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware


def _create_cors_origins() -> List[str]:
    """
    Build the list of allowed CORS origins.

    Reads from ALLOW_ORIGINS (comma-separated). Defaults to "*" if unset.
    """
    raw = os.getenv("ALLOW_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def _create_router() -> APIRouter:
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
    Construct the FastAPI app with CORS and router.
    """
    app = FastAPI(title="Policy Management API", version=os.getenv("APP_VERSION", "0.1.0"))

    # Configure CORS (beginner-friendly defaults; can be tightened via env)
    origins = _create_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include router (no business logic)
    app.include_router(_create_router())

    # Optional root route (informational only)
    @app.get("/")
    def root() -> dict:
        return {"message": "Policy Management API", "health": "/api/health"}

    return app


# ASGI application
app = get_application()
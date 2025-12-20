"""
Shared API router.

- Defines a top-level APIRouter that can aggregate sub-routers.
- Safely attempts to include optional sub-routers if they exist.
- Keeps concerns minimal (no business logic here).
"""

from __future__ import annotations

import importlib
from typing import List, Optional

from fastapi import APIRouter


__all__ = ["router"]

# Create the top-level router for the backend API.
# You can mount this in FastAPI with: app.include_router(router)
router = APIRouter(prefix="/api")


def _try_include_subrouter(parent: APIRouter, module_path: str) -> Optional[APIRouter]:
    """
    Attempt to import a module and include its 'router' (if present and is an APIRouter).
    Returns the included router or None.
    """
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        return None
    except Exception:
        # Ignore any unexpected import error to avoid breaking the API wiring.
        return None

    sub = getattr(module, "router", None)
    if isinstance(sub, APIRouter):
        parent.include_router(sub)
        return sub
    return None


def _include_known_subrouters(parent: APIRouter) -> List[str]:
    """
    Try to include common API sub-routers by conventional module names.
    Returns a list of module paths that were successfully included.
    """
    candidates = [
        "app.api.health",
        "app.api.policies",
        "app.api.policy",
        "app.api.evidence",
        "app.api.decisions",
        "app.api.risk",
        "app.api.admin",
    ]
    included: List[str] = []
    for mod in candidates:
        if _try_include_subrouter(parent, mod):
            included.append(mod)
    return included


# Best-effort: include any known sub-routers if present.
_INCLUDED = _include_known_subrouters(router)
"""
Shared API router.

- Aggregates sub-routers from app.api.routes.* modules.
- Uses no top-level prefix to avoid double-/api when sub-routers already define their own prefixes.
- Safely attempts to include optional sub-routers if they exist.

Sub-routers included (if present):
- app.api.routes.protect   -> /api/protect
- app.api.routes.evidence  -> /api/evidence
- app.api.routes.audit     -> /api/audit
- app.api.routes.policies  -> /api/policies
"""

from __future__ import annotations

import importlib
from typing import List, Optional

from fastapi import APIRouter

__all__ = ["router", "INCLUDED_MODULES"]

# Create the top-level router without a prefix.
# Each sub-router controls its own path under /api/...
router = APIRouter()


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
    Try to include known API sub-routers by conventional module names.
    Returns a list of module paths that were successfully included.
    """
    candidates = [
        "app.api.routes.protect",
        "app.api.routes.evidence",
        "app.api.routes.audit",
        "app.api.routes.policies",
    ]
    included: List[str] = []
    for mod in candidates:
        if _try_include_subrouter(parent, mod) is not None:
            included.append(mod)
    return included


# Best-effort: include any known sub-routers if present.
INCLUDED_MODULES = _include_known_subrouters(router)
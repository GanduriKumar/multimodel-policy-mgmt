"""
Shared API router.

- Aggregates sub-routers from app.api.routes.* modules.
- Uses no top-level prefix to avoid double-/api when sub-routers already define their own prefixes.
- Directly imports known routers so import errors are immediately visible.

Sub-routers included:
- app.api.routes.protect   -> /api/protect
- app.api.routes.evidence  -> /api/evidence
- app.api.routes.audit     -> /api/audit
- app.api.routes.policies  -> /api/policies
- app.api.routes.maintenance -> /api/admin
 - app.api.routes.reports -> /api/reports
"""

from __future__ import annotations

from fastapi import APIRouter

# Direct imports - any error will be visible at startup
from app.api.routes.protect import router as protect_router
from app.api.routes.protect_generate import router as protect_generate_router
from app.api.routes.policies import router as policies_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.audit import router as audit_router
from app.api.routes.maintenance import router as maintenance_router
from app.api.routes.reports import router as reports_router

__all__ = ["router"]

# Create the top-level router without a prefix.
# Each sub-router controls its own path under /api/...
router = APIRouter()

# Include all known routers
router.include_router(protect_router)
router.include_router(protect_generate_router)
router.include_router(policies_router)
router.include_router(evidence_router)
router.include_router(audit_router)
router.include_router(maintenance_router)
router.include_router(reports_router)
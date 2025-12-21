"""
Protect-and-generate API.

This route composes pre-check policy enforcement, LLM generation, and post-check
governance using the governed generation orchestrator.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.generation import ProtectGenerateRequest, ProtectGenerateResponse
from app.services.governed_generation_service import GovernedGenerationService
from app.core.deps import get_governed_generation_service

router = APIRouter(prefix="/api", tags=["protect-generate"])


@router.post("/protect-generate", response_model=ProtectGenerateResponse)
def protect_and_generate(
    payload: ProtectGenerateRequest,
    service: GovernedGenerationService = Depends(get_governed_generation_service),
) -> ProtectGenerateResponse:
    try:
        return service.protect_and_generate(payload)
    except Exception as e:
        # Keep error surface minimal and consistent
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"protect-generate failed: {e}",
        ) from e
"""
Protect-and-generate API.

This route composes pre-check policy enforcement, LLM generation, and post-check
governance using the governed generation orchestrator.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.generation import ProtectGenerateRequest, ProtectGenerateResponse
from app.core.deps import get_decision_service, DecisionService

router = APIRouter(prefix="/api", tags=["protect-generate"])


@router.post("/protect-generate", response_model=ProtectGenerateResponse)
def protect_and_generate(
    payload: ProtectGenerateRequest,
    decision_service: DecisionService = Depends(get_decision_service),
) -> ProtectGenerateResponse:
    """
    Combined protect-and-generate endpoint with optional LLM provider selection.
    
    The provider can be specified in the request payload via 'llm_provider' field.
    """
    # Import services here to avoid circular dependencies
    from app.core.deps import (
        get_llm_client,
        get_rag_proxy,
        get_governance_ledger,
        get_groundedness_engine,
    )
    from app.services.governed_generation_service import GovernedGenerationService
    
    # Create service with specified LLM provider from the request
    service = GovernedGenerationService(
        decision_service=decision_service,
        llm_client=get_llm_client(payload.llm_provider),
        rag_proxy=get_rag_proxy(),
        ledger=get_governance_ledger(),
        groundedness_engine=get_groundedness_engine(),
    )
    
    try:
        return service.protect_and_generate(payload)
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"ERROR in protect_and_generate: {e}")
        print(traceback.format_exc())
        # Keep error surface minimal and consistent
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}",
        ) from e
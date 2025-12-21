"""
Protect-and-Generate endpoint.

POST /api/protect-generate
- Accepts ProtectGenerateRequest
- Resolves GovernedGenerationService via DI
- Returns ProtectGenerateResponse
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.generation import ProtectGenerateRequest, ProtectGenerateResponse
from app.services.governed_generation_service import GovernedGenerationService


router = APIRouter(prefix="/api", tags=["protect-generate"])


def get_governed_generation_service() -> GovernedGenerationService:
    # Minimal inline DI to avoid changing core deps. Construct service with defaults.
    # Repos and engines are wired through DecisionService dependency providers already.
    from app.core.deps import (
        get_decision_service,
    )
    from app.services.llm_gateway import OllamaLLMClient
    from app.services.groundedness_engine import GroundednessEngine
    from app.services.rag_proxy import RAGProxy
    from app.services.governance_ledger import GovernanceLedger

    decision_service = get_decision_service()  # type: ignore[call-arg]
    llm = OllamaLLMClient()
    grounded = GroundednessEngine()
    rag = RAGProxy()
    ledger = GovernanceLedger()
    return GovernedGenerationService(
        decision_service=decision_service,
        llm_client=llm,
        groundedness_engine=grounded,
        rag_proxy=rag,
        ledger=ledger,
    )


@router.post("/protect-generate", response_model=ProtectGenerateResponse)
def protect_and_generate(
    payload: ProtectGenerateRequest,
    service: GovernedGenerationService = Depends(get_governed_generation_service),
) -> ProtectGenerateResponse:
    try:
        return service.protect_and_generate(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

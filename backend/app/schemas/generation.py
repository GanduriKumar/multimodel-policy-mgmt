"""
Schemas for a combined protect-and-generate flow.

Defines request/response contracts that extend the existing Protect API
with optional retrieval artifacts and groundedness results.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

try:  # Pydantic v2 preferred
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - v1 fallback
    from pydantic import BaseModel, Field  # type: ignore

from .protect import ProtectRequest

__all__ = [
    "ProtectGenerateRequest",
    "GroundedClaim",
    "ProtectGenerateResponse",
]


class ProtectGenerateRequest(ProtectRequest):
    """Extend ProtectRequest with retrieval context for RAG flows.

    - retrieval_query: the exact query used to retrieve evidence (optional)
    - evidence_payloads: raw evidence chunk payloads if the client wants
      to send them explicitly (each item is a dict with keys like text, source_uri, metadata)
    """

    retrieval_query: Optional[str] = Field(default=None, description="RAG retrieval query text")
    evidence_payloads: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of evidence chunk payloads"
    )


class GroundedClaim(BaseModel):
    """Groundedness result for a single claim extracted from model output."""

    text: str
    score: float = Field(ge=0.0, le=1.0)
    supported: bool
    matched_evidence_ids: List[int] = Field(default_factory=list)


class ProtectGenerateResponse(BaseModel):
    """Response combining decision, risk, grounded claims, and raw output."""

    allowed: bool
    risk_score: int
    policy_reasons: List[str] = Field(default_factory=list)
    risk_reasons: List[str] = Field(default_factory=list)
    grounded_claims: List[GroundedClaim] = Field(default_factory=list)
    raw_model_output: str
    trace_id: str

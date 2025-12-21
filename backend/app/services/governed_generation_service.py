"""
GovernedGenerationService: Orchestrates protect + generate + groundedness with governance.

Flow:
1) Record inbound request to GovernanceLedger and start a RAG session -> trace_id
2) Call DecisionService.protect; if denied, return immediately (allow=False)
3) If allowed, record retrieval context via RAGProxy (using retrieval_query/evidence_payloads)
4) Call LLMClient to generate raw_model_output
5) Score groundedness using GroundednessEngine
6) Optionally enforce minimum groundedness threshold from settings
7) Record decision and model_output to GovernanceLedger and return response
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import get_settings
from app.core.deps import DecisionService
from app.schemas.generation import (
    GroundedClaim,
    ProtectGenerateRequest,
    ProtectGenerateResponse,
)
from app.services.groundedness_engine import GroundednessEngine
from app.services.llm_gateway import LLMClient
from app.services.rag_proxy import RAGProxy
from app.services.governance_ledger import GovernanceLedger


class GovernedGenerationService:
    def __init__(
        self,
        *,
        decision_service: DecisionService,
        llm_client: LLMClient,
        groundedness_engine: GroundednessEngine,
        rag_proxy: RAGProxy,
        ledger: GovernanceLedger,
    ) -> None:
        self.decision_service = decision_service
        self.llm = llm_client
        self.grounded = groundedness_engine
        self.rag = rag_proxy
        self.ledger = ledger

    def protect_and_generate(self, request: ProtectGenerateRequest) -> ProtectGenerateResponse:
        settings = get_settings()

        # 1) Governance: record incoming request and start a trace
        trace_id = self.rag.start_session({
            "tenant_id": request.tenant_id,
            "policy_slug": request.policy_slug,
        })
        self.ledger.append_entry(
            "request",
            {
                "tenant_id": request.tenant_id,
                "policy_slug": request.policy_slug,
                "input_preview": request.input_text[:256],
            },
            trace_id,
        )

        # 2) Policy protect pre-check
        result = self.decision_service.protect(
            tenant_id=request.tenant_id,
            input_text=request.input_text,
            policy_slug=request.policy_slug,
            evidence_types=request.evidence_types,
            request_id=request.request_id,
            user_agent=None,
            client_ip=None,
            metadata=request.metadata,
        )

        # Split reasons heuristically for response fields
        policy_reasons: List[str] = []
        risk_reasons: List[str] = []
        for r in result["reasons"]:
            if r.startswith(("prompt_injection:", "pii_like:", "secret_like:", "risk_above_threshold")) or r == "evidence_missing":
                risk_reasons.append(r)
            else:
                policy_reasons.append(r)

        if not result["allowed"]:
            # Denied at pre-check, return without LLM call
            self.ledger.append_entry(
                "decision",
                {
                    "allowed": False,
                    "reasons": result["reasons"],
                    "risk_score": result["risk_score"],
                },
                trace_id,
            )
            return ProtectGenerateResponse(
                allowed=False,
                risk_score=result["risk_score"],
                policy_reasons=policy_reasons,
                risk_reasons=risk_reasons,
                grounded_claims=[],
                raw_model_output="",
                trace_id=trace_id,
            )

        # 3) Record retrieval context
        if request.retrieval_query or request.evidence_payloads:
            chunks = []
            for ch in (request.evidence_payloads or []):
                # Expect keys: text, source_uri, metadata, document_hash/chunk_hash optional
                if not isinstance(ch, dict):
                    continue
                chunks.append({
                    "text": str(ch.get("text", "")),
                    "source_uri": ch.get("source_uri") or ch.get("source"),
                    "metadata": ch.get("metadata") or {},
                    "document_hash": ch.get("document_hash"),
                    "chunk_hash": ch.get("chunk_hash"),
                })
            if chunks:
                self.rag.record_retrieval(trace_id, request.retrieval_query or "", chunks)

        # 4) Generate with downstream LLM
        raw_model_output = self.llm.generate(request.input_text, context={
            "options": {"temperature": 0},  # deterministic-ish
        })

        # 5) Groundedness scoring
        evidence_texts = [str(ch.get("text", "")) for ch in (request.evidence_payloads or [])]
        g_results = self.grounded.score_output(raw_model_output, evidence_texts)
        grounded_claims = [
            GroundedClaim(
                text=gr.claim.text,
                score=gr.score,
                supported=gr.supported,
                matched_evidence_ids=gr.matched_evidence_ids,
            )
            for gr in g_results
        ]
        overall = (sum(gc.score for gc in grounded_claims) / max(1, len(grounded_claims))) if grounded_claims else 0.0

        # 6) Enforce minimum groundedness threshold (optional)
        min_g = 0.0
        try:
            # Read from settings if present; default to 0.0 (no enforcement)
            min_g = float(getattr(settings, "MIN_GROUNDEDNESS_SCORE", 0.0) or 0.0)
        except Exception:
            min_g = 0.0

        allowed = bool(result["allowed"])
        if overall < min_g:
            allowed = False
            policy_reasons.append(f"groundedness_below_threshold:{overall:.2f}<{min_g:.2f}")

        # 7) Governance: record decision and model output
        self.ledger.append_entry(
            "model_output",
            {
                "provider": "llm_gateway",
                "model": getattr(self.llm, "model", None),
                "preview": raw_model_output[:256],
            },
            trace_id,
        )
        self.ledger.append_entry(
            "decision",
            {
                "allowed": allowed,
                "reasons": policy_reasons + risk_reasons,
                "risk_score": result["risk_score"],
                "groundedness_overall": overall,
                "min_groundedness": min_g,
            },
            trace_id,
        )

        return ProtectGenerateResponse(
            allowed=allowed,
            risk_score=result["risk_score"],
            policy_reasons=policy_reasons,
            risk_reasons=risk_reasons,
            grounded_claims=grounded_claims,
            raw_model_output=raw_model_output,
            trace_id=trace_id,
        )

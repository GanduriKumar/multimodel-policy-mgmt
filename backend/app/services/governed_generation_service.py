"""
GovernedGenerationService: Orchestrates protect + generate + safety + groundedness with governance.

Flow:
1) Record inbound request to GovernanceLedger and start a RAG session -> trace_id
2) Call DecisionService.protect; if denied, return immediately (allow=False)
3) If allowed, record retrieval context via RAGProxy (using retrieval_query/evidence_payloads)
4) Call LLMClient to generate raw_model_output
5) Run ResponseSafetyEngine on raw_model_output
6) Score groundedness using GroundednessEngine
7) Optionally enforce minimum groundedness threshold from settings
8) Optionally enforce minimum safety level from settings
9) Record safety report, decision and model_output to GovernanceLedger and return response
"""

from __future__ import annotations

from typing import Any, List, Optional, Dict

from app.core.config import get_settings
from app.core.deps import DecisionService
from app.schemas.generation import (
    GroundedClaim,
    ProtectGenerateRequest,
    ProtectGenerateResponse,
)
from app.services.groundedness_engine import GroundednessEngine
from app.services.response_safety_engine import ResponseSafetyEngine
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
        safety_engine: Optional[ResponseSafetyEngine] = None,
        rag_proxy: RAGProxy,
        ledger: GovernanceLedger,
    ) -> None:
        self.decision_service = decision_service
        self.llm = llm_client
        self.grounded = groundedness_engine
        # Backward compatible: allow None and create a default engine
        self.safety = safety_engine or ResponseSafetyEngine()
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

        # 5) Safety evaluation (deterministic, no external calls)
        safety_report = self.safety.evaluate(raw_model_output)
        # Summarize issues for inclusion in reasons and ledger; keep messages concise
        safety_issues_slim: List[Dict[str, str]] = [
            {
                "kind": iss.kind,
                "severity": iss.severity,
                "message": (iss.message[:120] if isinstance(iss.message, str) else ""),
            }
            for iss in safety_report.issues
        ]
        # Highest severity present (none -> -1)
        severity_order = {"low": 0, "medium": 1, "high": 2}
        max_sev_level = -1
        max_sev_name = None
        for iss in safety_report.issues:
            lvl = severity_order.get(str(iss.severity).lower(), 1)
            if lvl > max_sev_level:
                max_sev_level = lvl
                max_sev_name = str(iss.severity).lower()

        # 6) Groundedness scoring
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

        # 7) Enforce minimum groundedness threshold (optional)
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

        # 8) Enforce minimum safety level (optional)
        min_safety_level_name = str(getattr(settings, "MIN_SAFETY_LEVEL", "")).strip().lower() or None
        if min_safety_level_name and min_safety_level_name in severity_order:
            threshold = severity_order[min_safety_level_name]
            if max_sev_level >= threshold and max_sev_level >= 0:
                allowed = False
                # Include compact summary of issues in reasons
                policy_reasons.append(
                    f"safety_below_threshold:{max_sev_name}>={min_safety_level_name}"
                )
        # Always add a summary reason for visibility
        policy_reasons.append(f"is_safe_output:{str(safety_report.is_safe).lower()}")
        # Also add individual safety issue summaries into risk_reasons
        for iss in safety_issues_slim[:10]:  # cap to avoid overly long responses
            risk_reasons.append(
                f"safety_issue:{iss['kind']}:{iss['severity']}:{iss['message']}"
            )

        # 9) Governance: record model output, safety, and decision
        self.ledger.append_entry(
            "model_output",
            {
                "provider": "llm_gateway",
                "model": getattr(self.llm, "model", None),
                "preview": raw_model_output[:256],
            },
            trace_id,
        )
        # Safety report entry
        self.ledger.append_entry(
            "safety_report",
            {
                "is_safe": safety_report.is_safe,
                "issues": safety_issues_slim,
                "max_issue_severity": max_sev_name,
                "min_safety_level": min_safety_level_name,
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
                "is_safe_output": safety_report.is_safe,
                "max_safety_issue_severity": max_sev_name,
                "min_safety_level": min_safety_level_name,
            },
            trace_id,
        )

        # Build response; include safety fields if the schema permits extras; also mirrored in reasons
        response_kwargs: Dict[str, Any] = {
            "allowed": allowed,
            "risk_score": result["risk_score"],
            "policy_reasons": policy_reasons,
            "risk_reasons": risk_reasons,
            "grounded_claims": grounded_claims,
            "raw_model_output": raw_model_output,
            "trace_id": trace_id,
        }
        # Extras (some Pydantic configs ignore extras; reasons already carry summaries regardless)
        response_kwargs["is_safe_output"] = safety_report.is_safe
        response_kwargs["safety_issues"] = safety_issues_slim

        return ProtectGenerateResponse(**response_kwargs)

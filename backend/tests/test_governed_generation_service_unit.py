import types
from typing import Any, Dict, List, Optional

import pytest

from app.schemas.generation import ProtectGenerateRequest
from app.services.governed_generation_service import GovernedGenerationService
from app.services.groundedness_engine import Claim as GClaim, GroundednessResult as GResult


class FakeDecisionService:
    def __init__(self, *, allow: bool, reasons: Optional[List[str]] = None, risk_score: int = 0) -> None:
        self.allow = allow
        self.reasons = list(reasons or [])
        self.risk_score = int(risk_score)
        self.calls: List[Dict[str, Any]] = []

    def protect(
        self,
        *,
        tenant_id: int,
        input_text: str,
        policy_slug: str,
        evidence_types: Optional[set[str]] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.calls.append({
            "tenant_id": tenant_id,
            "policy_slug": policy_slug,
            "input_text": input_text,
        })
        return {
            "allowed": bool(self.allow),
            "reasons": list(self.reasons),
            "risk_score": self.risk_score,
            "request_log_id": 1,
            "decision_log_id": 1,
        }


class FakeLLMClient:
    def __init__(self, text: str = "MOCK OUTPUT") -> None:
        self.text = text
        self.calls: List[Dict[str, Any]] = []

    def generate(self, prompt: str, context: Optional[dict] = None) -> str:
        self.calls.append({"prompt": prompt, "context": context})
        return self.text


class FakeRAGProxy:
    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.retrieval_calls: List[Dict[str, Any]] = []

    def start_session(self, context: Optional[Dict[str, Any]] = None) -> str:
        tid = "trace-xyz"
        self.sessions[tid] = {"context": dict(context or {})}
        return tid

    def record_retrieval(self, trace_id: str, query: str, chunks: List[Dict[str, Any]]) -> None:
        self.retrieval_calls.append({"trace_id": trace_id, "query": query, "chunks": chunks})


class FakeGroundednessEngine:
    def __init__(self, results: List[GResult]) -> None:
        self.results = results
        self.calls: List[Dict[str, Any]] = []

    def score_output(self, model_output: str, evidence_texts: List[str]) -> List[GResult]:
        self.calls.append({"model_output": model_output, "evidence_texts": list(evidence_texts)})
        return list(self.results)


class FakeLedger:
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def append_entry(self, kind: str, payload: dict, trace_id: str) -> str:
        self.entries.append({"kind": kind, "payload": payload, "trace_id": trace_id})
        return "h" * 64


def test_deny_path_no_llm_called(monkeypatch: pytest.MonkeyPatch) -> None:
    dec = FakeDecisionService(allow=False, reasons=["blocked_term:test"], risk_score=90)
    llm = FakeLLMClient(text="SHOULD_NOT_BE_USED")
    rag = FakeRAGProxy()
    grounded = FakeGroundednessEngine(results=[GResult(claim=GClaim(text="x"), score=0.0, supported=False, matched_evidence_ids=[])])
    ledger = FakeLedger()

    svc = GovernedGenerationService(
        decision_service=dec,
        llm_client=llm,
        groundedness_engine=grounded,
        rag_proxy=rag,
        ledger=ledger,
    )

    req = ProtectGenerateRequest(tenant_id=1, policy_slug="content-safety", input_text="deny me")
    res = svc.protect_and_generate(req)

    assert res.allowed is False
    assert res.raw_model_output == ""
    assert len(llm.calls) == 0, "LLM should not be called on deny path"
    kinds = [e["kind"] for e in ledger.entries]
    assert "request" in kinds and "decision" in kinds
    assert "model_output" not in kinds


def test_allow_and_well_grounded() -> None:
    dec = FakeDecisionService(allow=True, reasons=[], risk_score=5)
    llm = FakeLLMClient(text="Hello world.")
    rag = FakeRAGProxy()
    grounded = FakeGroundednessEngine(
        results=[GResult(claim=GClaim(text="Hello world"), score=0.9, supported=True, matched_evidence_ids=[0])]
    )
    ledger = FakeLedger()

    svc = GovernedGenerationService(
        decision_service=dec,
        llm_client=llm,
        groundedness_engine=grounded,
        rag_proxy=rag,
        ledger=ledger,
    )

    req = ProtectGenerateRequest(
        tenant_id=1,
        policy_slug="content-safety",
        input_text="Hello world",
        retrieval_query="hello",
        evidence_payloads=[{"text": "Hello world evidence", "source_uri": "s://u"}],
    )
    res = svc.protect_and_generate(req)

    assert res.allowed is True
    assert res.raw_model_output == "Hello world."
    assert res.grounded_claims and res.grounded_claims[0].supported is True
    kinds = [e["kind"] for e in ledger.entries]
    assert "model_output" in kinds and "decision" in kinds and "request" in kinds


def test_low_groundedness_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch settings to enforce a minimum groundedness score
    import app.services.governed_generation_service as ggs

    class _Cfg:
        MIN_GROUNDEDNESS_SCORE = 0.8

    monkeypatch.setattr(ggs, "get_settings", lambda: _Cfg())

    dec = FakeDecisionService(allow=True, reasons=[], risk_score=5)
    llm = FakeLLMClient(text="Some text.")
    rag = FakeRAGProxy()
    grounded = FakeGroundednessEngine(
        results=[GResult(claim=GClaim(text="Some text"), score=0.1, supported=False, matched_evidence_ids=[])]
    )
    ledger = FakeLedger()

    svc = GovernedGenerationService(
        decision_service=dec,
        llm_client=llm,
        groundedness_engine=grounded,
        rag_proxy=rag,
        ledger=ledger,
    )

    req = ProtectGenerateRequest(tenant_id=1, policy_slug="content-safety", input_text="Some text")
    res = svc.protect_and_generate(req)

    assert res.allowed is False, "Should be denied due to low groundedness enforcement"
    assert any(r.startswith("groundedness_below_threshold") for r in res.policy_reasons)
    kinds = [e["kind"] for e in ledger.entries]
    assert "decision" in kinds

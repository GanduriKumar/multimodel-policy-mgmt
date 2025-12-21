"""
RAG interception interface and service.

Goal
-----
Provide a lightweight, pluggable interceptor to capture:
 - Retrieval queries (what was asked of the retriever)
 - Retrieved chunks (what content came back, from where)
 - Tool calls (invocations used during RAG)
Each capture is tied to a correlation/session ID for end-to-end tracing.

Design
------
 - In-memory append-only session store; safe for single-process apps.
 - Optional integration with GovernanceLedger (if available) for tamper-evident
   append-only recording.
 - No external dependencies.

Usage
-----
    proxy = InMemoryRAGProxy()
    sid = proxy.start(correlation_id="req-123")
    proxy.log_retrieval_query(sid, query="What is RAG?", top_k=5)
    proxy.log_retrieved_chunks(sid, [
        {"text": "RAG stands for Retrieval-Augmented Generation.",
         "source_uri": "https://example.com/rag",
         "document_hash": None,
         "chunk_hash": None,
         "score": 0.92,
         "metadata": {"page": 1}},
    ])
    proxy.log_tool_call(sid, name="search", arguments={"q": "RAG"}, result={"hits": 42}, latency_ms=120)
    report = proxy.end(sid)

Notes
-----
 - To attach the optional on-disk ledger, do:
        from app.services.governance_ledger import GovernanceLedger
        proxy.attach_ledger(GovernanceLedger())
 - The proxy stores the first 512 characters of chunk text as a preview to
   avoid memory bloat, and includes a SHA-256 content hash for integrity.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, MutableMapping, Optional, Protocol


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RAGInterceptor(Protocol):
    """Protocol for RAG interception services."""

    def start(self, correlation_id: Optional[str] = None) -> str:
        ...

    def log_retrieval_query(
        self,
        session_id: str,
        *,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        retriever: Optional[str] = None,
    ) -> None:
        ...

    def log_retrieved_chunks(
        self,
        session_id: str,
        chunks: List[Dict[str, Any]],
        *,
        provider: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        ...

    def log_tool_call(
        self,
        session_id: str,
        *,
        name: str,
        arguments: Any = None,
        result: Any = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        ...

    def get(self, session_id: str) -> Dict[str, Any]:
        ...

    def end(self, session_id: str) -> Dict[str, Any]:
        ...


@dataclass
class _Session:
    id: str
    correlation_id: str
    started_at: str
    ended_at: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)


class InMemoryRAGProxy(RAGInterceptor):
    """In-memory RAG interception store with optional governance ledger output."""

    def __init__(self) -> None:
        self._sessions: Dict[str, _Session] = {}
        self._ledger: Optional[Any] = None  # GovernanceLedger (optional)

    # -----------------------------
    # Public API
    # -----------------------------

    def attach_ledger(self, ledger: Any) -> None:
        """Attach a GovernanceLedger-like object with .append(kind, body)."""
        self._ledger = ledger

    def start(self, correlation_id: Optional[str] = None) -> str:
        sid = str(uuid.uuid4())
        corr = correlation_id or sid
        self._sessions[sid] = _Session(id=sid, correlation_id=corr, started_at=_now_iso())
        self._emit_ledger("rag_session_start", {"session_id": sid, "correlation_id": corr})
        return sid

    def log_retrieval_query(
        self,
        session_id: str,
        *,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        retriever: Optional[str] = None,
    ) -> None:
        s = self._require_session(session_id)
        evt = {
            "type": "retrieval_query",
            "timestamp": _now_iso(),
            "query": query,
            "top_k": top_k,
            "filters": filters or {},
            "retriever": retriever,
        }
        s.events.append(evt)
        self._emit_ledger("rag_retrieval_query", {"session_id": session_id, **{k: v for k, v in evt.items() if k != "type"}})

    def log_retrieved_chunks(
        self,
        session_id: str,
        chunks: List[Dict[str, Any]],
        *,
        provider: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        s = self._require_session(session_id)
        norm: List[Dict[str, Any]] = []
        for ch in chunks:
            text = str(ch.get("text", ""))
            preview = text[:512]
            chash = ch.get("chunk_hash") or _sha256_hex(text)
            norm.append(
                {
                    "preview": preview,
                    "content_hash": chash,
                    "source_uri": ch.get("source_uri"),
                    "document_hash": ch.get("document_hash"),
                    "score": ch.get("score"),
                    "metadata": ch.get("metadata"),
                }
            )
        evt = {
            "type": "retrieved_chunks",
            "timestamp": _now_iso(),
            "provider": provider,
            "latency_ms": latency_ms,
            "count": len(norm),
            "chunks": norm,
        }
        s.events.append(evt)
        self._emit_ledger(
            "rag_retrieved_chunks",
            {
                "session_id": session_id,
                "provider": provider,
                "latency_ms": latency_ms,
                "count": len(norm),
                # do not emit the full previews to ledger to keep it compact
                "chunk_hashes": [c["content_hash"] for c in norm],
            },
        )

    def log_tool_call(
        self,
        session_id: str,
        *,
        name: str,
        arguments: Any = None,
        result: Any = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        s = self._require_session(session_id)
        evt = {
            "type": "tool_call",
            "timestamp": _now_iso(),
            "name": name,
            "arguments": arguments,
            "result_preview": _safe_preview(result),
            "latency_ms": latency_ms,
        }
        s.events.append(evt)
        self._emit_ledger(
            "rag_tool_call",
            {
                "session_id": session_id,
                "name": name,
                "latency_ms": latency_ms,
            },
        )

    def get(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        return {
            "session_id": s.id,
            "correlation_id": s.correlation_id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "events": list(s.events),
        }

    def end(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        if not s.ended_at:
            s.ended_at = _now_iso()
            self._emit_ledger("rag_session_end", {"session_id": session_id})
        return self.get(session_id)

    # -----------------------------
    # Internals
    # -----------------------------

    def _require_session(self, session_id: str) -> _Session:
        s = self._sessions.get(session_id)
        if not s:
            raise KeyError(f"Unknown RAG session: {session_id}")
        return s

    def _emit_ledger(self, kind: str, body: Dict[str, Any]) -> None:
        if self._ledger is None:
            return
        try:
            self._ledger.append(kind, body)  # type: ignore[attr-defined]
        except Exception:
            # Do not break RAG flow if ledger writing fails
            pass


def _safe_preview(obj: Any, limit: int = 256) -> Any:
    """Return a compact preview for arbitrary objects suitable for logging."""
    try:
        if obj is None:
            return None
        if isinstance(obj, (str, bytes)):
            s = obj.decode("utf-8", errors="ignore") if isinstance(obj, bytes) else obj
            return s[:limit]
        # Attempt to serialize to JSON; fall back to type name
        s = json.dumps(obj)
        return s[:limit]
    except Exception:
        return {"type": type(obj).__name__}

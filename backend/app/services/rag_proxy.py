"""
RAGProxy: capture retrievals for end-to-end tracing and optional governance.

Contract implemented:
- start_session(context: dict | None = None) -> str  -> returns generated trace_id
- record_retrieval(trace_id: str, query: str, chunks: list[dict]) -> None

Behavior:
- Maintains an in-memory session store keyed by trace_id.
- For each record_retrieval, normalizes chunks and stores a compact preview
  plus deterministic content hashes.
- Optionally emits an "evidence" entry into the GovernanceLedger for each chunk.

Configuration (via app.core.config.get_settings):
- rag_emit_ledger: bool (default True)
- rag_chunk_preview_length: int (default 256)

Back-compat:
- Exposes InMemoryRAGProxy as an alias to RAGProxy for existing imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.hashing import sha256_text

try:  # optional; tests may run without it
    from app.services.governance_ledger import GovernanceLedger
except Exception:  # pragma: no cover
    GovernanceLedger = None  # type: ignore[assignment]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, n: int) -> str:
    return text[: max(0, int(n))]


@dataclass
class _RetrievalEvent:
    timestamp: str
    query: str
    chunks: List[Dict[str, Any]]


@dataclass
class _Session:
    trace_id: str
    created_at: str
    context: Dict[str, Any] = field(default_factory=dict)
    retrievals: List[_RetrievalEvent] = field(default_factory=list)


class RAGProxy:
    """Small in-memory RAG tracing proxy with optional governance emission."""

    def __init__(self, *, emit_to_ledger: Optional[bool] = None, chunk_preview_len: Optional[int] = None) -> None:
        settings = get_settings()
        # Resolve configuration with safe defaults
        self._emit_to_ledger: bool = (
            bool(getattr(settings, "rag_emit_ledger", True)) if emit_to_ledger is None else bool(emit_to_ledger)
        )
        self._preview_len: int = (
            int(getattr(settings, "rag_chunk_preview_length", 256)) if chunk_preview_len is None else int(chunk_preview_len)
        )

        self._sessions: Dict[str, _Session] = {}
        self._ledger = None
        if self._emit_to_ledger and GovernanceLedger is not None:
            try:
                self._ledger = GovernanceLedger()
            except Exception:  # pragma: no cover
                self._ledger = None

    # ---------------------------------
    # Public API (required by contract)
    # ---------------------------------

    def start_session(self, context: Optional[Dict[str, Any]] = None) -> str:
        trace_id = str(uuid.uuid4())
        self._sessions[trace_id] = _Session(trace_id=trace_id, created_at=_now_iso(), context=dict(context or {}))
        return trace_id

    def record_retrieval(self, trace_id: str, query: str, chunks: List[Dict[str, Any]]) -> None:
        sess = self._sessions.get(trace_id)
        if not sess:
            raise KeyError(f"Unknown trace_id: {trace_id}")

        norm_chunks: List[Dict[str, Any]] = []
        for ch in chunks or []:
            text = str(ch.get("text", ""))
            source_uri = ch.get("source_uri") or ch.get("source")
            metadata = ch.get("metadata") or {}
            document_hash = ch.get("document_hash")
            chunk_hash = ch.get("chunk_hash")
            # Deterministic content hash based on text when explicit chunk_hash is missing
            content_hash = chunk_hash or sha256_text(text)
            preview = _preview(text, self._preview_len)

            item = {
                "preview": preview,
                "content_hash": content_hash,
                "document_hash": document_hash,
                "source_uri": source_uri,
                "metadata": metadata,
            }
            norm_chunks.append(item)

            # Optionally emit evidence entry per chunk to ledger
            if self._ledger is not None:
                payload = {
                    "query": query,
                    "source_uri": source_uri,
                    "document_hash": document_hash,
                    "chunk_hash": content_hash,
                    "preview": preview,
                    "metadata": metadata,
                }
                try:
                    self._ledger.append_entry("evidence", payload, trace_id)  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover - do not break flow on ledger errors
                    pass

        sess.retrievals.append(_RetrievalEvent(timestamp=_now_iso(), query=query, chunks=norm_chunks))

    # ---------------------------------
    # Convenience helpers
    # ---------------------------------

    def get_session(self, trace_id: str) -> Dict[str, Any]:
        sess = self._sessions.get(trace_id)
        if not sess:
            raise KeyError(f"Unknown trace_id: {trace_id}")
        return {
            "trace_id": sess.trace_id,
            "created_at": sess.created_at,
            "context": dict(sess.context),
            "retrievals": [
                {"timestamp": r.timestamp, "query": r.query, "chunks": list(r.chunks)} for r in sess.retrievals
            ],
        }


# Back-compat alias
InMemoryRAGProxy = RAGProxy

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


"""RAG proxy helpers for tracing retrievals and emitting compact ledger events.

This module provides two compatible implementations used by the codebase and tests:
- RAGProxy: simple, backwards-compatible in-memory tracer
- InMemoryRAGProxyV2: a protocol-based interceptor with richer events

Design goals:
- Keep the implementation dependency-free so test collection doesn't require
  optional external services.
- Emit compact hashes and previews for storage into optional governance ledgers.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from app.core.config import get_settings
from app.core.hashing import sha256_text


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
    """Backward-compatible RAG proxy used in some services/tests.

    API:
      start_session(context: dict | None = None) -> str
      record_retrieval(trace_id: str, query: str, chunks: list[dict]) -> None
      get_session(trace_id: str) -> dict
    """

    def __init__(self, *, emit_to_ledger: Optional[bool] = None, chunk_preview_len: Optional[int] = None) -> None:
        settings = get_settings()
        self._emit_to_ledger: bool = bool(getattr(settings, "rag_emit_ledger", True)) if emit_to_ledger is None else bool(emit_to_ledger)
        self._preview_len: int = int(getattr(settings, "rag_chunk_preview_length", 256)) if chunk_preview_len is None else int(chunk_preview_len)

        self._sessions: Dict[str, _Session] = {}
        self._ledger = None
        try:
            from app.services.governance_ledger import GovernanceLedger

            self._ledger = GovernanceLedger()
        except Exception:  # pragma: no cover - ledger optional
            self._ledger = None

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
                except Exception:
                    pass

        sess.retrievals.append(_RetrievalEvent(timestamp=_now_iso(), query=query, chunks=norm_chunks))

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


# Backwards compatible alias
InMemoryRAGProxy = RAGProxy


class RAGInterceptor(Protocol):
    def start(self, correlation_id: Optional[str] = None) -> str:
        ...

    def log_retrieval_query(self, session_id: str, *, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None, retriever: Optional[str] = None) -> None:
        ...

    def log_retrieved_chunks(self, session_id: str, chunks: List[Dict[str, Any]], *, provider: Optional[str] = None, latency_ms: Optional[int] = None) -> None:
        ...

    def log_tool_call(self, session_id: str, *, name: str, arguments: Any = None, result: Any = None, latency_ms: Optional[int] = None) -> None:
        ...

    def get(self, session_id: str) -> Dict[str, Any]:
        ...

    def end(self, session_id: str) -> Dict[str, Any]:
        ...


@dataclass
class _SessionV2:
    id: str
    correlation_id: str
    started_at: str
    ended_at: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)


class InMemoryRAGProxyV2(RAGInterceptor):
    def __init__(self) -> None:
        self._sessions: Dict[str, _SessionV2] = {}
        self._ledger: Optional[Any] = None

    def attach_ledger(self, ledger: Any) -> None:
        self._ledger = ledger

    def start(self, correlation_id: Optional[str] = None) -> str:
        sid = str(uuid.uuid4())
        corr = correlation_id or sid
        self._sessions[sid] = _SessionV2(id=sid, correlation_id=corr, started_at=_now_iso())
        self._emit_ledger("rag_session_start", {"session_id": sid, "correlation_id": corr})
        return sid

    def log_retrieval_query(self, session_id: str, *, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None, retriever: Optional[str] = None) -> None:
        s = self._require_session(session_id)
        evt = {"type": "retrieval_query", "timestamp": _now_iso(), "query": query, "top_k": top_k, "filters": filters or {}, "retriever": retriever}
        s.events.append(evt)
        self._emit_ledger("rag_retrieval_query", {"session_id": session_id, **{k: v for k, v in evt.items() if k != "type"}})

    def log_retrieved_chunks(self, session_id: str, chunks: List[Dict[str, Any]], *, provider: Optional[str] = None, latency_ms: Optional[int] = None) -> None:
        s = self._require_session(session_id)
        norm: List[Dict[str, Any]] = []
        for ch in chunks:
            text = str(ch.get("text", ""))
            preview = text[:512]
            chash = ch.get("chunk_hash") or hashlib.sha256(text.encode("utf-8")).hexdigest()
            norm.append({
                "preview": preview,
                "content_hash": chash,
                "source_uri": ch.get("source_uri"),
                "document_hash": ch.get("document_hash"),
                "score": ch.get("score"),
                "metadata": ch.get("metadata"),
            })
        evt = {"type": "retrieved_chunks", "timestamp": _now_iso(), "provider": provider, "latency_ms": latency_ms, "count": len(norm), "chunks": norm}
        s.events.append(evt)
        self._emit_ledger("rag_retrieved_chunks", {"session_id": session_id, "provider": provider, "latency_ms": latency_ms, "count": len(norm), "chunk_hashes": [c["content_hash"] for c in norm]})

    def log_tool_call(self, session_id: str, *, name: str, arguments: Any = None, result: Any = None, latency_ms: Optional[int] = None) -> None:
        s = self._require_session(session_id)
        evt = {"type": "tool_call", "timestamp": _now_iso(), "name": name, "arguments": arguments, "result_preview": _safe_preview(result), "latency_ms": latency_ms}
        s.events.append(evt)
        self._emit_ledger("rag_tool_call", {"session_id": session_id, "name": name, "latency_ms": latency_ms})

    def get(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        return {"session_id": s.id, "correlation_id": s.correlation_id, "started_at": s.started_at, "ended_at": s.ended_at, "events": list(s.events)}

    def end(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        if not s.ended_at:
            s.ended_at = _now_iso()
            self._emit_ledger("rag_session_end", {"session_id": session_id})
        return self.get(session_id)

    # internals
    def _require_session(self, session_id: str) -> _SessionV2:
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
            pass


def _safe_preview(obj: Any, limit: int = 256) -> Any:
    try:
        if obj is None:
            return None
        if isinstance(obj, (str, bytes)):
            s = obj.decode("utf-8", errors="ignore") if isinstance(obj, bytes) else obj
            return s[:limit]
        s = json.dumps(obj)
        return s[:limit]
    except Exception:
        return {"type": type(obj).__name__}


# Backwards compatible alias
InMemoryRAGProxy = RAGProxy


# Newer protocol-based interceptor used elsewhere
class RAGInterceptor(Protocol):
    def start(self, correlation_id: Optional[str] = None) -> str:
        ...

    def log_retrieval_query(self, session_id: str, *, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None, retriever: Optional[str] = None) -> None:
        ...

    def log_retrieved_chunks(self, session_id: str, chunks: List[Dict[str, Any]], *, provider: Optional[str] = None, latency_ms: Optional[int] = None) -> None:
        ...

    def log_tool_call(self, session_id: str, *, name: str, arguments: Any = None, result: Any = None, latency_ms: Optional[int] = None) -> None:
        ...

    def get(self, session_id: str) -> Dict[str, Any]:
        ...

    def end(self, session_id: str) -> Dict[str, Any]:
        ...


@dataclass
class _SessionV2:
    id: str
    correlation_id: str
    started_at: str
    ended_at: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)


class InMemoryRAGProxyV2(RAGInterceptor):
    def __init__(self) -> None:
        self._sessions: Dict[str, _SessionV2] = {}
        self._ledger: Optional[Any] = None

    def attach_ledger(self, ledger: Any) -> None:
        self._ledger = ledger

    def start(self, correlation_id: Optional[str] = None) -> str:
        sid = str(uuid.uuid4())
        corr = correlation_id or sid
        self._sessions[sid] = _SessionV2(id=sid, correlation_id=corr, started_at=_now_iso())
        self._emit_ledger("rag_session_start", {"session_id": sid, "correlation_id": corr})
        return sid

    def log_retrieval_query(self, session_id: str, *, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None, retriever: Optional[str] = None) -> None:
        s = self._require_session(session_id)
        evt = {"type": "retrieval_query", "timestamp": _now_iso(), "query": query, "top_k": top_k, "filters": filters or {}, "retriever": retriever}
        s.events.append(evt)
        self._emit_ledger("rag_retrieval_query", {"session_id": session_id, **{k: v for k, v in evt.items() if k != "type"}})

    def log_retrieved_chunks(self, session_id: str, chunks: List[Dict[str, Any]], *, provider: Optional[str] = None, latency_ms: Optional[int] = None) -> None:
        s = self._require_session(session_id)
        norm: List[Dict[str, Any]] = []
        for ch in chunks:
            text = str(ch.get("text", ""))
            preview = text[:512]
            chash = ch.get("chunk_hash") or hashlib.sha256(text.encode("utf-8")).hexdigest()
            norm.append({
                "preview": preview,
                "content_hash": chash,
                "source_uri": ch.get("source_uri"),
                "document_hash": ch.get("document_hash"),
                "score": ch.get("score"),
                "metadata": ch.get("metadata"),
            })
        evt = {"type": "retrieved_chunks", "timestamp": _now_iso(), "provider": provider, "latency_ms": latency_ms, "count": len(norm), "chunks": norm}
        s.events.append(evt)
        self._emit_ledger("rag_retrieved_chunks", {"session_id": session_id, "provider": provider, "latency_ms": latency_ms, "count": len(norm), "chunk_hashes": [c["content_hash"] for c in norm]})

    def log_tool_call(self, session_id: str, *, name: str, arguments: Any = None, result: Any = None, latency_ms: Optional[int] = None) -> None:
        s = self._require_session(session_id)
        evt = {"type": "tool_call", "timestamp": _now_iso(), "name": name, "arguments": arguments, "result_preview": _safe_preview(result), "latency_ms": latency_ms}
        s.events.append(evt)
        self._emit_ledger("rag_tool_call", {"session_id": session_id, "name": name, "latency_ms": latency_ms})

    def get(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        return {"session_id": s.id, "correlation_id": s.correlation_id, "started_at": s.started_at, "ended_at": s.ended_at, "events": list(s.events)}

    def end(self, session_id: str) -> Dict[str, Any]:
        s = self._require_session(session_id)
        if not s.ended_at:
            s.ended_at = _now_iso()
            self._emit_ledger("rag_session_end", {"session_id": session_id})
        return self.get(session_id)

    # internals
    def _require_session(self, session_id: str) -> _SessionV2:
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
            pass


def _safe_preview(obj: Any, limit: int = 256) -> Any:
    try:
        if obj is None:
            return None
        if isinstance(obj, (str, bytes)):
            s = obj.decode("utf-8", errors="ignore") if isinstance(obj, bytes) else obj
            return s[:limit]
        s = json.dumps(obj)
        return s[:limit]
    except Exception:
        return {"type": type(obj).__name__}
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

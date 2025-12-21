"""
GovernanceLedger service (append-only, hash-chained).

Purpose
-------
Record an immutable, append-only timeline of backend governance events with
hash chaining for tamper-evidence. Events include:
 - request:     Incoming user request (RequestLog)
 - evidence:    Retrieval EvidenceBundle captured for a request
 - decision:    Policy decision outcome (DecisionLog)
 - model_output:Provider/model result associated with a request

Design
------
 - Storage: newline-delimited JSON (JSONL) file on disk (no extra deps).
 - Chain: each entry contains prev_hash and hash = HMAC-SHA256(prev_hash || body).
 - Canonical JSON: sort_keys=True, compact separators to ensure stable hashing.
 - Verification: verify_chain() replays the file and checks the chain.

Environment variables
---------------------
 - GOVERNANCE_LEDGER_PATH: path to the JSONL file (default: ./governance_ledger.jsonl)
 - GOVERNANCE_LEDGER_HMAC_KEY: hex or utf-8 string key for HMAC. If missing, a
   weak default is used (not recommended for production).

Notes
-----
 - File appends are atomic on most platforms when using append mode, but this
   is not a full multi-process consensus log. Keep a single writer per service
   instance for strongest guarantees.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional, Tuple

# Optional imports of ORM models for typed helper methods
try:  # pragma: no cover - type-only usage in signatures
    from app.models.request_log import RequestLog  # noqa: F401
    from app.models.decision_log import DecisionLog  # noqa: F401
    from app.models.evidence_bundle import EvidenceBundle  # noqa: F401
except Exception:  # pragma: no cover
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_bytes(key: Optional[str]) -> bytes:
    if not key:
        return b"governance-ledger-weak-default-key"
    try:
        # Accept hex-encoded keys
        return bytes.fromhex(key)
    except Exception:
        return key.encode("utf-8")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class LedgerHead:
    index: int
    hash: str


class GovernanceLedger:
    """Append-only governance ledger with HMAC-SHA256 hash chaining."""

    def __init__(self, path: Optional[str] = None, hmac_key: Optional[str] = None) -> None:
        self.path = path or os.getenv("GOVERNANCE_LEDGER_PATH", os.path.join(os.getcwd(), "governance_ledger.jsonl"))
        self.key = _to_bytes(hmac_key or os.getenv("GOVERNANCE_LEDGER_HMAC_KEY"))
        self._ensure_dir()

    # -----------------------------
    # Core append/verify operations
    # -----------------------------

    def append(self, kind: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new ledger entry and return it."""
        head = self._load_head()
        idx = (head.index + 1) if head else 0
        prev_hash = head.hash if head else "0" * 64

        entry = {
            "index": idx,
            "timestamp": _now_iso(),
            "kind": kind,
            "body": body,
            "prev_hash": prev_hash,
        }
        mac = hmac.new(self.key, digestmod=hashlib.sha256)
        mac.update(prev_hash.encode("utf-8"))
        mac.update(_canonical(body).encode("utf-8"))
        mac.update(entry["timestamp"].encode("utf-8"))
        mac.update(kind.encode("utf-8"))
        entry_hash = mac.hexdigest()
        entry["hash"] = entry_hash

        line = _canonical(entry) + "\n"
        # Atomic-ish append
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()

        return entry

    def verify_chain(self) -> Tuple[bool, Optional[int]]:
        """
        Verify the chain from start to end.
        Returns (ok, bad_index). If ok is False, bad_index indicates the first
        failing entry index.
        """
        if not os.path.exists(self.path):
            return True, None

        prev_hash = "0" * 64
        expected_index = 0
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    return False, expected_index

                if entry.get("index") != expected_index:
                    return False, expected_index
                if entry.get("prev_hash") != prev_hash:
                    return False, expected_index

                mac = hmac.new(self.key, digestmod=hashlib.sha256)
                mac.update(prev_hash.encode("utf-8"))
                mac.update(_canonical(entry.get("body", {})).encode("utf-8"))
                mac.update(str(entry.get("timestamp", "")).encode("utf-8"))
                mac.update(str(entry.get("kind", "")).encode("utf-8"))
                calc_hash = mac.hexdigest()
                if calc_hash != entry.get("hash"):
                    return False, expected_index

                prev_hash = calc_hash
                expected_index += 1

        return True, None

    def head(self) -> Optional[LedgerHead]:
        """Return current head (index, hash) or None if empty."""
        return self._load_head()

    # -----------------------------
    # Convenience recorders
    # -----------------------------

    def record_request(self, req: "RequestLog") -> Dict[str, Any]:  # type: ignore[name-defined]
        body = {
            "tenant_id": req.tenant_id,
            "request_log_id": req.id,
            "policy_id": req.policy_id,
            "policy_version_id": req.policy_version_id,
            "input_hash": req.input_hash,
            "created_at": getattr(req, "created_at", None).isoformat() if getattr(req, "created_at", None) else None,
        }
        return self.append("request", body)

    def record_evidence(self, bundle: "EvidenceBundle") -> Dict[str, Any]:  # type: ignore[name-defined]
        body = {
            "tenant_id": bundle.tenant_id,
            "evidence_bundle_id": bundle.id,
            "source_uri": bundle.source_uri,
            "document_hash": bundle.document_hash,
            "chunk_hash": bundle.chunk_hash,
            "chunk_count": len(bundle.chunks or []),
            "created_at": getattr(bundle, "created_at", None).isoformat() if getattr(bundle, "created_at", None) else None,
        }
        return self.append("evidence", body)

    def record_decision(self, dec: "DecisionLog") -> Dict[str, Any]:  # type: ignore[name-defined]
        body = {
            "tenant_id": dec.tenant_id,
            "decision_id": dec.id,
            "request_log_id": dec.request_log_id,
            "policy_id": dec.policy_id,
            "policy_version_id": dec.policy_version_id,
            "allowed": bool(dec.allowed),
            "reasons": list(dec.reasons or []),
            "risk_score": dec.risk_score,
            "created_at": getattr(dec, "created_at", None).isoformat() if getattr(dec, "created_at", None) else None,
        }
        return self.append("decision", body)

    def record_model_output(
        self,
        *,
        request_log_id: int,
        provider: str,
        model: str,
        output_text: str,
        tenant_id: Optional[int] = None,
        truncate_preview: int = 256,
    ) -> Dict[str, Any]:
        content_hash = _sha256_hex(output_text.encode("utf-8"))
        preview = output_text[: max(0, int(truncate_preview))]
        body = {
            "tenant_id": tenant_id,
            "request_log_id": int(request_log_id),
            "provider": provider,
            "model": model,
            "content_hash": content_hash,
            "preview": preview,
        }
        return self.append("model_output", body)

    # -----------------------------
    # Internals
    # -----------------------------

    def _ensure_dir(self) -> None:
        d = os.path.dirname(self.path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load_head(self) -> Optional[LedgerHead]:
        if not os.path.exists(self.path):
            return None
        last: Optional[dict] = None
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    last = json.loads(line)
                except Exception:
                    continue
        if not last:
            return None
        idx = int(last.get("index", -1))
        h = str(last.get("hash", ""))
        if idx < 0 or len(h) != 64:
            return None
        return LedgerHead(index=idx, hash=h)

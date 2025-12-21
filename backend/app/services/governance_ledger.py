"""
GovernanceLedger: tamper-evident append-only ledger (JSONL).

- append_entry(kind, payload, trace_id) -> str (hash)
- verify_chain() -> bool
- Convenience helpers: record_request/record_decision/record_model_output/record_evidence

Configuration resolution (in order):
- Path: explicit arg -> settings.governance_ledger_path -> env GOVERNANCE_LEDGER_PATH -> ./governance_ledger.jsonl
- Secret: explicit arg -> settings.governance_ledger_hmac_secret -> settings.auth_hmac_secret
          -> env GOVERNANCE_LEDGER_HMAC_SECRET -> "dev-secret"

Hashing:
- We build a canonical JSON structure: {prev_hash, kind, timestamp, trace_id, body, secret_fingerprint}
- secret_fingerprint = sha256_text(secret)
- Entry hash = sha256_json(struct)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.hashing import sha256_json, sha256_text


def _now_iso(prev: Optional[str]) -> str:
    """
    Monotonic-ish ISO-8601 with UTC timezone. If prev exists and is >= now, nudge by 1 ms.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    if not prev:
        return now_iso
    # If previous timestamp sorts after current, append a tiny suffix
    return now_iso if now_iso > prev else f"{prev}Z"


@dataclass
class _Head:
    index: int
    hash: str
    timestamp: str


class GovernanceLedger:
    """Append-only, hash-chained governance ledger stored as JSONL."""

    def __init__(self, path: Optional[str] = None, secret: Optional[str] = None) -> None:
        settings = get_settings()

        # Resolve path
        env_path = os.getenv("GOVERNANCE_LEDGER_PATH")
        default_path = os.path.join(os.getcwd(), "governance_ledger.jsonl")
        self.path: str = (
            path
            or getattr(settings, "governance_ledger_path", None)
            or env_path
            or default_path
        )

        # Resolve secret
        env_secret = os.getenv("GOVERNANCE_LEDGER_HMAC_SECRET")
        resolved_secret = (
            secret
            or getattr(settings, "governance_ledger_hmac_secret", None)
            or getattr(settings, "auth_hmac_secret", None)
            or env_secret
            or "dev-secret"
        )
        self._secret_fingerprint = sha256_text(str(resolved_secret)) if resolved_secret else ""

        # Ensure directory exists
        d = os.path.dirname(self.path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

        self._last_timestamp: Optional[str] = None

    # -----------------------------
    # Public API
    # -----------------------------

    def append_entry(self, kind: str, payload: Dict[str, Any], trace_id: str) -> str:
        """
        Append an entry and return its hash.
        """
        prev = self._load_head()
        prev_hash = prev.hash if prev else ""
        ts = _now_iso(self._last_timestamp)
        body = {
            "index": (prev.index + 1) if prev else 0,
            "timestamp": ts,
            "kind": str(kind),
            "trace_id": str(trace_id),
            "prev_hash": prev_hash,
            "body": payload or {},
        }

        canonical_for_hash = {
            "prev_hash": prev_hash,
            "kind": body["kind"],
            "timestamp": ts,
            "trace_id": body["trace_id"],
            "body": body["body"],
            "secret_fingerprint": self._secret_fingerprint,
        }
        entry_hash = sha256_json(canonical_for_hash)
        body["hash"] = entry_hash

        # Append JSONL
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
            f.write("\n")

        # Update last timestamp
        self._last_timestamp = ts
        return entry_hash

    def verify_chain(self) -> bool:
        """
        Verify the entire chain; return True if valid, False otherwise.
        """
        prev_hash = ""
        last_ts = ""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    # Check index monotonicity
                    if obj.get("index") != idx:
                        return False
                    # Check prev_hash linkage
                    if obj.get("prev_hash", "") != prev_hash:
                        return False
                    # Recompute hash
                    canonical = {
                        "prev_hash": obj.get("prev_hash", ""),
                        "kind": obj.get("kind", ""),
                        "timestamp": obj.get("timestamp", ""),
                        "trace_id": obj.get("trace_id", ""),
                        "body": obj.get("body", {}),
                        "secret_fingerprint": self._secret_fingerprint,
                    }
                    expected = sha256_json(canonical)
                    if obj.get("hash") != expected:
                        return False
                    # Timestamps should be non-decreasing
                    ts = str(obj.get("timestamp", ""))
                    if ts and last_ts and ts < last_ts:
                        return False
                    last_ts = ts
                    prev_hash = expected
            return True
        except FileNotFoundError:
            # Empty chain is considered valid
            return True
        except Exception:
            return False

    # -----------------------------
    # Convenience helpers (back-compat)
    # -----------------------------

    def record_request(self, req: "RequestLog", trace_id: Optional[str] = None) -> str:  # type: ignore[name-defined]
        """
        Record an incoming request. Accepts a RequestLog-like object or dict.
        """
        tid = getattr(req, "tenant_id", None) if not isinstance(req, dict) else req.get("tenant_id")
        rid = getattr(req, "id", None) if not isinstance(req, dict) else req.get("id")
        payload = {
            "tenant_id": tid,
            "request_log_id": rid,
        }
        return self.append_entry("request", payload, trace_id or f"req:{rid}")

    def record_decision(self, dec: "DecisionLog", trace_id: Optional[str] = None) -> str:  # type: ignore[name-defined]
        """
        Record a policy decision. Accepts a DecisionLog-like object or dict.
        """
        if isinstance(dec, dict):
            payload = {
                "tenant_id": dec.get("tenant_id"),
                "request_log_id": dec.get("request_log_id"),
                "decision_log_id": dec.get("id"),
                "allowed": dec.get("allowed"),
                "reasons": dec.get("reasons"),
                "risk_score": dec.get("risk_score"),
            }
            trace = trace_id or f"dec:{payload.get('decision_log_id')}"
        else:
            payload = {
                "tenant_id": getattr(dec, "tenant_id", None),
                "request_log_id": getattr(dec, "request_log_id", None),
                "decision_log_id": getattr(dec, "id", None),
                "allowed": getattr(dec, "allowed", None),
                "reasons": getattr(dec, "reasons", None),
                "risk_score": getattr(dec, "risk_score", None),
            }
            trace = trace_id or f"dec:{payload.get('decision_log_id')}"
        return self.append_entry("decision", payload, trace)

    def record_model_output(
        self,
        *,
        request_log_id: int,
        provider: str,
        model: str,
        output_text: str,
        tenant_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        preview_len: int = 256,
    ) -> str:
        """
        Record a model output artifact with content hash and short preview.
        """
        preview = (output_text or "")[: max(0, int(preview_len))]
        content_hash = sha256_text(output_text or "")
        payload = {
            "tenant_id": tenant_id,
            "request_log_id": int(request_log_id),
            "provider": provider,
            "model": model,
            "content_hash": content_hash,
            "preview": preview,
        }
        return self.append_entry("model_output", payload, trace_id or f"req:{request_log_id}")

    def record_evidence(self, bundle: "EvidenceBundle", trace_id: Optional[str] = None) -> str:  # type: ignore[name-defined]
        """
        Record a retrieval evidence bundle (accepts dict-like or object with attributes).
        """
        if isinstance(bundle, dict):
            payload = {
                "bundle_id": bundle.get("id"),
                "tenant_id": bundle.get("tenant_id"),
                "request_log_id": bundle.get("request_log_id"),
                "chunks": bundle.get("chunks"),
                "meta": bundle.get("metadata"),
            }
            trace = trace_id or f"ev:{payload.get('bundle_id')}"
        else:
            payload = {
                "bundle_id": getattr(bundle, "id", None),
                "tenant_id": getattr(bundle, "tenant_id", None),
                "request_log_id": getattr(bundle, "request_log_id", None),
                "chunks": getattr(bundle, "chunks", None),
                "meta": getattr(bundle, "metadata", None),
            }
            trace = trace_id or f"ev:{payload.get('bundle_id')}"
        return self.append_entry("evidence", payload, trace)

    # -----------------------------
    # Internals
    # -----------------------------

    def _load_head(self) -> Optional[_Head]:
        try:
            size = os.path.getsize(self.path)
            if size <= 0:
                return None
        except Exception:
            return None

        last: Optional[dict] = None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        last = json.loads(line)
                    except Exception:
                        continue
        except FileNotFoundError:
            return None

        if not last:
            return None
        try:
            return _Head(index=int(last.get("index", 0)), hash=str(last.get("hash", "")), timestamp=str(last.get("timestamp", "")))
        except Exception:
            return None


__all__ = ["GovernanceLedger"]
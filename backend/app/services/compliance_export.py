"""
ComplianceExportService
-----------------------

Packages requests, decisions, policies, evidence bundles, and derived hashes
into export formats that are both human-readable (HTML) and machine-verifiable
(canonical JSON with content hashes).

No external dependencies. "PDF‑ready" means we emit a self-contained HTML
document suitable for printing or conversion to PDF by common tools.

Usage example:
    svc = ComplianceExportService()
    bundle = svc.build_export_bundle(
        request=req, decision=dec, policy=pol, policy_version=pv,
        evidence_bundles=bundles, risk_score=rs, ledger_head=ledger.head() if ledger else None,
    )
    json_bytes = svc.to_json_bytes(bundle)
    html_str = svc.to_html(bundle)

Machine verification:
 - Each section is hashed with SHA-256 over canonical JSON.
 - A top-level root_hash is computed from the concatenation of section hashes.
 - Optional ledger head (index, hash) can be embedded to anchor in the
   append-only GovernanceLedger.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# -------------
# Hash helpers
# -------------

def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_section(section_obj: Any) -> str:
    return _sha256_hex(_canonical(section_obj).encode("utf-8"))


def _normalize_dt(dt: Any) -> Optional[str]:
    try:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        # str() fallback for other types
        return str(dt)
    except Exception:
        return None


def _maybe_dict(obj: Any, fields: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Best-effort conversion of ORM/dataclass/dict-like to plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        data = dict(obj)
    elif is_dataclass(obj):
        data = asdict(obj)
    else:
        # ORM-like: collect given fields or public attrs
        data = {}
        if fields:
            for k in fields:
                data[k] = getattr(obj, k, None)
        else:
            for k in dir(obj):
                if k.startswith("_"):
                    continue
                try:
                    v = getattr(obj, k)
                except Exception:
                    continue
                if callable(v):
                    continue
                # Keep simple attrs only to avoid recursion
                if isinstance(v, (str, int, float, bool, type(None), list, dict)) or isinstance(v, datetime):
                    data[k] = v
    # Normalize datetimes to ISO8601 strings
    for k, v in list(data.items()):
        if isinstance(v, datetime):
            data[k] = v.isoformat()
    return data


class ComplianceExportService:
    """Compose compliant, verifiable export bundles (JSON + HTML)."""

    SECTION_ORDER: Tuple[str, ...] = (
        "manifest",
        "request",
        "decision",
        "risk_score",
        "policy",
        "policy_version",
        "evidence",
    )

    def build_export_bundle(
        self,
        *,
        request: Any,
        decision: Any,
        policy: Any,
        policy_version: Any,
        evidence_bundles: Sequence[Any],
        risk_score: Optional[Any] = None,
        ledger_head: Optional[Dict[str, Any]] = None,
        generator: str = "ComplianceExportService/1.0",
    ) -> Dict[str, Any]:
        """Return a dict bundle with sections, per-section hashes, and root hash."""

        manifest = {
            "format": "policy-compliance-export",
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": generator,
            "ledger_head": ledger_head or None,
        }

        req = _maybe_dict(
            request,
            fields=(
                "id",
                "tenant_id",
                "policy_id",
                "policy_version_id",
                "request_id",
                "input_hash",
                "user_agent",
                "client_ip",
                "metadata",
                "created_at",
            ),
        )

        dec = _maybe_dict(
            decision,
            fields=(
                "id",
                "tenant_id",
                "request_log_id",
                "policy_id",
                "policy_version_id",
                "allowed",
                "reasons",
                "risk_score",
                "created_at",
            ),
        )

        rs = _maybe_dict(
            risk_score,
            fields=(
                "id",
                "tenant_id",
                "request_log_id",
                "policy_id",
                "policy_version_id",
                "score",
                "reasons",
                "evidence_present",
                "created_at",
            ),
        ) if risk_score is not None else {}

        pol = _maybe_dict(policy, fields=("id", "tenant_id", "name", "slug", "description", "is_active", "created_at"))
        pv = _maybe_dict(
            policy_version,
            fields=("id", "policy_id", "version", "document", "is_active", "created_at"),
        )

        evidence_list: List[Dict[str, Any]] = []
        for b in evidence_bundles:
            item = _maybe_dict(
                b,
                fields=(
                    "id",
                    "tenant_id",
                    "source_uri",
                    "document_hash",
                    "chunk_hash",
                    "chunks",
                    "claim_references",
                    "created_at",
                ),
            )
            # For large chunks, hash each and keep previews
            chunks = item.get("chunks") or []
            norm_chunks: List[Dict[str, Any]] = []
            for ch in chunks:
                text = ch if isinstance(ch, str) else str(ch)
                norm_chunks.append(
                    {
                        "preview": text[:256],
                        "content_hash": _sha256_hex(text.encode("utf-8")),
                    }
                )
            item["chunks_index"] = norm_chunks
            # Top-level bundle hash (source/doc/chunk identifiers)
            item["bundle_hash"] = _hash_section(
                {
                    "source_uri": item.get("source_uri"),
                    "document_hash": item.get("document_hash"),
                    "chunk_hash": item.get("chunk_hash"),
                    "chunks": [c["content_hash"] for c in norm_chunks],
                }
            )
            evidence_list.append(item)

        sections = {
            "manifest": manifest,
            "request": req,
            "decision": dec,
            "risk_score": rs,
            "policy": pol,
            "policy_version": pv,
            "evidence": evidence_list,
        }

        hashes: Dict[str, str] = {name: _hash_section(sections[name]) for name in self.SECTION_ORDER}
        root_hash = _sha256_hex("".join(hashes[name] for name in self.SECTION_ORDER).encode("utf-8"))

        bundle = {
            **sections,
            "hashes": hashes,
            "root_hash": root_hash,
        }
        return bundle

    # -----------------
    # Renderers/outputs
    # -----------------

    def to_json_bytes(self, bundle: Dict[str, Any]) -> bytes:
        return _canonical(bundle).encode("utf-8")

    def to_html(self, bundle: Dict[str, Any]) -> str:
        """Return a self-contained HTML document representing the export bundle."""
        m = bundle.get("manifest", {})
        req = bundle.get("request", {})
        dec = bundle.get("decision", {})
        rs = bundle.get("risk_score", {})
        pol = bundle.get("policy", {})
        pv = bundle.get("policy_version", {})
        ev = bundle.get("evidence", [])
        hashes = bundle.get("hashes", {})
        root_hash = bundle.get("root_hash", "")

        def pre(obj: Any) -> str:
            return json.dumps(obj, indent=2, ensure_ascii=False)

        # Minimal CSS for print/PDF
        css = """
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
        h1, h2, h3 { margin: 0.6em 0 0.3em; }
        .meta { color: #555; font-size: 0.95em; }
        .box { border: 1px solid #ddd; padding: 12px; border-radius: 8px; background: #fafafa; }
        code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92em; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .small { font-size: 0.9em; }
        .hash { font-family: ui-monospace, monospace; word-break: break-all; }
        .section { margin-bottom: 24px; }
        """

        # Evidence list HTML
        ev_items = []
        for i, b in enumerate(ev, start=1):
            chunk_index = b.get("chunks_index", [])
            chunk_list_html = "".join(
                f"<li><div><div class='hash small'>hash: {c.get('content_hash')}</div>"
                f"<div class='small'>preview: {html_escape(c.get('preview',''))}</div></div></li>"
                for c in chunk_index
            )
            ev_items.append(
                f"""
                <div class="box section">
                  <h3>Evidence Bundle #{i}</h3>
                  <div class="grid">
                    <div>
                      <div class="small">source_uri</div>
                      <div>{html_escape(b.get('source_uri') or '')}</div>
                    </div>
                    <div>
                      <div class="small">document_hash</div>
                      <div class="hash">{html_escape(b.get('document_hash') or '')}</div>
                    </div>
                    <div>
                      <div class="small">chunk_hash</div>
                      <div class="hash">{html_escape(b.get('chunk_hash') or '')}</div>
                    </div>
                    <div>
                      <div class="small">bundle_hash</div>
                      <div class="hash">{html_escape(b.get('bundle_hash') or '')}</div>
                    </div>
                  </div>
                  <div class="small" style="margin-top:8px;">chunks</div>
                  <ul>{chunk_list_html}</ul>
                </div>
                """
            )
        ev_html = "\n".join(ev_items) if ev_items else "<div class='small'>No evidence bundles</div>"

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Policy Compliance Export</title>
  <style>{css}</style>
  <meta name="root-hash" content="{html_escape(root_hash)}" />
  <meta name="manifest-hash" content="{html_escape(hashes.get('manifest',''))}" />
  <meta name="request-hash" content="{html_escape(hashes.get('request',''))}" />
  <meta name="decision-hash" content="{html_escape(hashes.get('decision',''))}" />
  <meta name="risk-score-hash" content="{html_escape(hashes.get('risk_score',''))}" />
  <meta name="policy-hash" content="{html_escape(hashes.get('policy',''))}" />
  <meta name="policy-version-hash" content="{html_escape(hashes.get('policy_version',''))}" />
  <meta name="evidence-hash" content="{html_escape(hashes.get('evidence',''))}" />
  <meta name="generator" content="{html_escape(m.get('generator',''))}" />
  <meta name="generated_at" content="{html_escape(m.get('generated_at',''))}" />
  <meta name="format" content="{html_escape(m.get('format',''))}" />
  <meta name="format_version" content="{html_escape(m.get('version',''))}" />
  <meta name="ledger_index" content="{html_escape(str((m.get('ledger_head') or {}).get('index', '')))}" />
  <meta name="ledger_hash" content="{html_escape(str((m.get('ledger_head') or {}).get('hash', '')))}" />
  <style>@media print {{ a[href]::after {{ content: ""; }} }}</style>
</head>
<body>
  <h1>Policy Compliance Export</h1>
  <div class="meta">Generated {html_escape(m.get('generated_at',''))} by {html_escape(m.get('generator',''))}</div>

  <div class="section box">
    <h2>Integrity</h2>
    <div class="small">root_hash</div>
    <div class="hash">{html_escape(root_hash)}</div>
    <div class="grid" style="margin-top:8px;">
      <div><div class="small">manifest</div><div class="hash">{html_escape(hashes.get('manifest',''))}</div></div>
      <div><div class="small">request</div><div class="hash">{html_escape(hashes.get('request',''))}</div></div>
      <div><div class="small">decision</div><div class="hash">{html_escape(hashes.get('decision',''))}</div></div>
      <div><div class="small">risk_score</div><div class="hash">{html_escape(hashes.get('risk_score',''))}</div></div>
      <div><div class="small">policy</div><div class="hash">{html_escape(hashes.get('policy',''))}</div></div>
      <div><div class="small">policy_version</div><div class="hash">{html_escape(hashes.get('policy_version',''))}</div></div>
      <div><div class="small">evidence</div><div class="hash">{html_escape(hashes.get('evidence',''))}</div></div>
    </div>
  </div>

  <div class="section box"><h2>Request</h2><pre>{html_escape(pre(req))}</pre></div>
  <div class="section box"><h2>Decision</h2><pre>{html_escape(pre(dec))}</pre></div>
  <div class="section box"><h2>Risk Score</h2><pre>{html_escape(pre(rs))}</pre></div>
  <div class="section box"><h2>Policy</h2><pre>{html_escape(pre(pol))}</pre></div>
  <div class="section box"><h2>Policy Version</h2><pre>{html_escape(pre(pv))}</pre></div>
  <div class="section"><h2>Evidence</h2>{ev_html}</div>

  <div class="meta small" style="margin-top:24px;">This document can be printed or saved as PDF for audit.
  The JSON representation contains the same sections and hashes for machine verification.</div>
</body>
</html>
        """
        return html


def html_escape(s: Any) -> str:
    """Simple HTML escaping for embedding content safely."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


__all__ = ["ComplianceExportService"]

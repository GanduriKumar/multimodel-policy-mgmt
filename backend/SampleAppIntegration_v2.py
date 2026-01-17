"""
Enhanced Sample Python GenAI app with multi-provider support.

This version supports TWO modes:

MODE 1 (--mode sandwich, default): Traditional bidirectional pattern
    1) Pre-check with /api/protect
    2) Call LLM provider directly (OpenAI REST API)
    3) Post-check with /api/protect

MODE 2 (--mode unified): New unified pattern using backend LLM gateway
    1) Single call to /api/protect-generate
    2) Backend handles: pre-check → LLM call → post-check → groundedness
    3) Provider selection via --llm-provider flag

Env vars:
- BACKEND_URL (default: http://localhost:8000)
- BACKEND_API_KEY (optional; sent via x-api-key header)
- BACKEND_API_KEY_HEADER (default: x-api-key)
- OPENAI_API_KEY (required for MODE 1; optional for MODE 2 if using backend OpenAI)
- OPENAI_MODEL (default: gpt-4o-mini)

Usage examples:

    # MODE 1: Traditional sandwich pattern (calls OpenAI directly)
    python backend/SampleAppIntegration_v2.py --mode sandwich --tenant-id 1 --policy-id 1 --prompt "Hello"

    # MODE 2: Unified backend pattern with Ollama (default)
    python backend/SampleAppIntegration_v2.py --mode unified --tenant-id 1 --policy-id 1 --prompt "Hello"

    # MODE 2: Unified with OpenAI provider
    python backend/SampleAppIntegration_v2.py --mode unified --tenant-id 1 --policy-id 1 --prompt "Hello" --llm-provider openai

    # MODE 2: Unified with Vertex AI provider
    python backend/SampleAppIntegration_v2.py --mode unified --tenant-id 1 --policy-id 1 --prompt "Hello" --llm-provider vertex

    # JSON output
    python backend/SampleAppIntegration_v2.py --mode unified --tenant-id 1 --policy-id 1 --prompt "Write a murder mystery" --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Set, List


def _json_post(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            if v is not None:
                req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"HTTP {e.code} POST {url} failed: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"POST {url} failed: {e}") from e


def protect(
    *,
    backend_url: str,
    tenant_id: int,
    policy_id: int,
    text: str,
    evidence_types: Optional[Set[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "x-api-key",
) -> Dict[str, Any]:
    """Call the backend /api/protect endpoint."""
    url = backend_url.rstrip("/") + "/api/protect"
    headers: Dict[str, str] = {}
    if api_key:
        headers[api_key_header] = api_key
    payload: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "policy_id": policy_id,
        "input_text": text,
    }
    if evidence_types:
        payload["evidence_types"] = sorted(list(evidence_types))
    if metadata:
        payload["metadata"] = metadata
    return _json_post(url, payload, headers)


def protect_generate(
    *,
    backend_url: str,
    tenant_id: int,
    policy_id: int,
    text: str,
    llm_provider: Optional[str] = None,
    evidence_types: Optional[Set[str]] = None,
    retrieval_query: Optional[str] = None,
    evidence_payloads: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "x-api-key",
) -> Dict[str, Any]:
    """Call the backend /api/protect-generate endpoint with optional provider selection."""
    url = backend_url.rstrip("/") + "/api/protect-generate"
    headers: Dict[str, str] = {}
    if api_key:
        headers[api_key_header] = api_key
    payload: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "policy_id": policy_id,
        "input_text": text,
    }
    if llm_provider:
        payload["llm_provider"] = llm_provider
    if evidence_types:
        payload["evidence_types"] = sorted(list(evidence_types))
    if retrieval_query:
        payload["retrieval_query"] = retrieval_query
    if evidence_payloads:
        payload["evidence_payloads"] = evidence_payloads
    if metadata:
        payload["metadata"] = metadata
    return _json_post(url, payload, headers)


def call_openai_chat(*, api_key: str, model: str, prompt: str) -> str:
    """Minimal REST call to OpenAI Chat Completions API."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            obj = json.loads(body) if body else {}
            content = (
                obj.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not isinstance(content, str):
                raise RuntimeError("Unexpected response shape from OpenAI")
            return content
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"OpenAI error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI request failed: {e}") from e


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-provider policy-guarded GenAI app.")
    p.add_argument("--mode", type=str, choices=["sandwich", "unified"], default="sandwich",
                   help="sandwich=pre/post pattern (default), unified=single /api/protect-generate call")
    p.add_argument("--tenant-id", type=int, default=1, help="Tenant identifier (default 1).")
    p.add_argument("--policy-id", type=int, required=True, help="Policy ID to enforce.")
    p.add_argument("--prompt", type=str, default=None, help="Prompt text; if omitted, read from STDIN.")
    p.add_argument("--llm-provider", type=str, default=None,
                   help="LLM provider for unified mode: openai, ollama, vertex (default: ollama)")
    p.add_argument("--evidence-types", type=str, default="", help="Comma-separated evidence types.")
    p.add_argument("--evidence-ids", type=str, default="", help="Comma-separated evidence IDs.")
    p.add_argument("--evidence-source", type=str, action="append", help="Evidence source (can be repeated). Format: 'text|source_uri'")
    p.add_argument("--backend-url", type=str, default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    p.add_argument("--backend-api-key", type=str, default=os.getenv("BACKEND_API_KEY"))
    p.add_argument("--backend-api-key-header", type=str, default=os.getenv("BACKEND_API_KEY_HEADER", "x-api-key"))
    p.add_argument("--openai-api-key", type=str, default=os.getenv("OPENAI_API_KEY"))
    p.add_argument("--openai-model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    p.add_argument("--json", action="store_true", help="Print JSON output.")
    return p.parse_args()


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception as e:
        raise RuntimeError(f"Failed reading STDIN: {e}") from e


def run_sandwich_mode(args: argparse.Namespace, prompt: str, ev_types: Set[str], ev_ids: List[int], evidence_payloads: List[Dict[str, Any]]) -> int:
    """MODE 1: Traditional pre-check → LLM → post-check pattern."""
    import uuid
    import time
    correlation_id = f"sample-app-sandwich-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    meta: Dict[str, Any] = {
        "correlation_id": correlation_id,
        "stage": "pre",
    }
    if ev_ids:
        meta["evidence_ids"] = ev_ids

    # Pre-check
    try:
        pre = protect(
            backend_url=args.backend_url,
            tenant_id=args.tenant_id,
            policy_id=args.policy_id,
            text=prompt,
            evidence_types=ev_types,
            metadata=meta,
            api_key=args.backend_api_key,
            api_key_header=args.backend_api_key_header,
        )
    except Exception as e:
        print(f"Error calling backend (pre-check): {e}", file=sys.stderr)
        return 9

    if not pre.get("allowed", False):
        if args.json:
            print(json.dumps({"stage": "pre", "decision": pre}, ensure_ascii=False))
        else:
            print(f"Blocked by policy (pre-check). Reasons: {pre.get('reasons', [])}", file=sys.stderr)
        return 10

    # Call LLM directly
    if not args.openai_api_key:
        print("Error: OPENAI_API_KEY not set for sandwich mode.", file=sys.stderr)
        return 3
    try:
        draft = call_openai_chat(api_key=args.openai_api_key, model=args.openai_model, prompt=prompt)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return 11

    # Post-check
    meta_post = {
        "correlation_id": correlation_id,
        "stage": "post",
    }
    if ev_ids:
        meta_post["evidence_ids"] = ev_ids
        
    try:
        post = protect(
            backend_url=args.backend_url,
            tenant_id=args.tenant_id,
            policy_id=args.policy_id,
            text=draft,
            evidence_types=ev_types,
            metadata=meta_post,
            api_key=args.backend_api_key,
            api_key_header=args.backend_api_key_header,
        )
    except Exception as e:
        print(f"Error calling backend (post-check): {e}", file=sys.stderr)
        return 13

    if not post.get("allowed", False):
        if args.json:
            print(json.dumps({"stage": "post", "decision": post, "draft": draft}, ensure_ascii=False))
        else:
            print(f"Output blocked by policy (post-check). Reasons: {post.get('reasons', [])}", file=sys.stderr)
        return 12

    # Success
    if args.json:
        print(json.dumps({"mode": "sandwich", "pre": pre, "post": post, "content": draft}, ensure_ascii=False))
    else:
        print(draft)
    return 0


def run_unified_mode(args: argparse.Namespace, prompt: str, ev_types: Set[str], ev_ids: List[int], evidence_payloads: List[Dict[str, Any]]) -> int:
    """MODE 2: Unified /api/protect-generate with multi-provider support."""
    import uuid
    import time
    correlation_id = f"sample-app-unified-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    meta: Dict[str, Any] = {
        "correlation_id": correlation_id,
    }
    if ev_ids:
        meta["evidence_ids"] = ev_ids

    try:
        result = protect_generate(
            backend_url=args.backend_url,
            tenant_id=args.tenant_id,
            policy_id=args.policy_id,
            text=prompt,
            llm_provider=args.llm_provider,  # NEW: provider selection
            evidence_types=ev_types,
            evidence_payloads=evidence_payloads if evidence_payloads else None,
            metadata=meta,
            api_key=args.backend_api_key,
            api_key_header=args.backend_api_key_header,
        )
    except Exception as e:
        print(f"Error calling backend (protect-generate): {e}", file=sys.stderr)
        return 9

    if not result.get("allowed", False):
        if args.json:
            print(json.dumps({"mode": "unified", "result": result}, ensure_ascii=False))
        else:
            reasons = result.get('policy_reasons', []) + result.get('risk_reasons', [])
            print(f"Blocked by policy. Reasons: {reasons}", file=sys.stderr)
        return 10

    # Success
    if args.json:
        print(json.dumps({
            "mode": "unified",
            "provider": args.llm_provider or "ollama",
            "allowed": result["allowed"],
            "risk_score": result["risk_score"],
            "content": result["raw_model_output"],
            "trace_id": result["trace_id"],
            "grounded_claims": result.get("grounded_claims", []),
            "policy_reasons": result.get("policy_reasons", []),
            "risk_reasons": result.get("risk_reasons", []),
        }, ensure_ascii=False))
    else:
        print(result["raw_model_output"])
    return 0


def main() -> int:
    args = _parse_args()

    prompt = args.prompt if args.prompt is not None else _read_stdin()
    prompt = prompt.strip()
    if not prompt:
        print("Error: empty prompt (provide --prompt or pipe via STDIN).", file=sys.stderr)
        return 2

    ev_types = {s.strip() for s in (args.evidence_types or "").split(",") if s.strip()}
    ev_ids: List[int] = []
    for part in (args.evidence_ids or "").split(","):
        part = part.strip()
        if part.isdigit():
            ev_ids.append(int(part))
    
    # Parse evidence sources into payloads
    evidence_payloads: List[Dict[str, Any]] = []
    if args.evidence_source:
        for source_spec in args.evidence_source:
            # Format: "text|source_uri" or just "text"
            parts = source_spec.split("|", 1)
            if len(parts) == 2:
                text, uri = parts
            else:
                text = parts[0]
                uri = "inline-source"
            evidence_payloads.append({
                "text": text,
                "source_uri": uri,
                "metadata": {},
            })

    if args.mode == "sandwich":
        return run_sandwich_mode(args, prompt, ev_types, ev_ids, evidence_payloads)
    else:  # unified
        return run_unified_mode(args, prompt, ev_types, ev_ids, evidence_payloads)


if __name__ == "__main__":
    raise SystemExit(main())

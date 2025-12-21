"""
Sample Python GenAI app demonstrating bidirectional policy integration.

Flow:
1) Pre-check user prompt with backend /api/protect (deny fast if not allowed).
2) If allowed, call LLM provider (OpenAI REST API).
3) Post-check the LLM draft with backend /api/protect before returning to user.

Env vars:
- BACKEND_URL (default: http://localhost:8000)
- BACKEND_API_KEY (optional; sent via x-api-key header)
- BACKEND_API_KEY_HEADER (default: x-api-key)
- OPENAI_API_KEY (required to call OpenAI)
- OPENAI_MODEL (default: gpt-4o-mini)

Usage examples:
  # Prompt via argument
  python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety --prompt "Hello"

  # Or read prompt from STDIN
  echo "Summarize this text..." | python backend/SampleAppIntegration.py --tenant-id 1 --policy-slug content-safety

Notes:
- Protect endpoint: see backend route [app.api.routes.protect](backend/app/api/routes/protect.py)
- Orchestration: see service [app.services.decision_service](backend/app/services/decision_service.py)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Set


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
    policy_slug: str,
    text: str,
    evidence_types: Optional[Set[str]] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "x-api-key",
) -> Dict[str, Any]:
    """
    Call the backend /api/protect endpoint with the given payload.
    """
    url = backend_url.rstrip("/") + "/api/protect"
    headers: Dict[str, str] = {}
    if api_key:
        headers[api_key_header] = api_key
    payload = {
        "tenant_id": tenant_id,
        "policy_slug": policy_slug,
        "input_text": text,
        "evidence_types": sorted(list(evidence_types or set())),
    }
    return _json_post(url, payload, headers)


def call_openai_chat(*, api_key: str, model: str, prompt: str) -> str:
    """
    Minimal REST call to OpenAI Chat Completions API using urllib (no extra deps).
    """
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
    p = argparse.ArgumentParser(description="Bidirectional policy-guarded GenAI app (Python).")
    p.add_argument("--tenant-id", type=int, required=True, help="Tenant identifier used by backend policies.")
    p.add_argument("--policy-slug", type=str, required=True, help="Policy slug to enforce.")
    p.add_argument("--prompt", type=str, default=None, help="Prompt text; if omitted, read from STDIN.")
    p.add_argument("--evidence-types", type=str, default="", help="Comma-separated evidence types (e.g., url,document).")
    p.add_argument("--backend-url", type=str, default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    p.add_argument("--backend-api-key", type=str, default=os.getenv("BACKEND_API_KEY"))
    p.add_argument("--backend-api-key-header", type=str, default=os.getenv("BACKEND_API_KEY_HEADER", "x-api-key"))
    p.add_argument("--openai-api-key", type=str, default=os.getenv("OPENAI_API_KEY"))
    p.add_argument("--openai-model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    p.add_argument("--json", action="store_true", help="Print JSON output with pre/post decisions and content.")
    return p.parse_args()


def _read_stdin() -> str:
    try:
        data = sys.stdin.read()
    except Exception as e:
        raise RuntimeError(f"Failed reading STDIN: {e}") from e
    return data


def main() -> int:
    args = _parse_args()

    prompt = args.prompt if args.prompt is not None else _read_stdin()
    prompt = prompt.strip()
    if not prompt:
        print("Error: empty prompt (provide --prompt or pipe via STDIN).", file=sys.stderr)
        return 2

    ev_types = {s.strip() for s in (args.evidence_types or "").split(",") if s.strip()}

    # Pre-check
    try:
        pre = protect(
            backend_url=args.backend_url,
            tenant_id=args.tenant_id,
            policy_slug=args.policy_slug,
            text=prompt,
            evidence_types=ev_types,
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

    # Call LLM
    if not args.openai_api_key:
        print("Error: OPENAI_API_KEY not set or --openai-api-key missing.", file=sys.stderr)
        return 3
    try:
        draft = call_openai_chat(api_key=args.openai_api_key, model=args.openai_model, prompt=prompt)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return 11

    # Post-check
    try:
        post = protect(
            backend_url=args.backend_url,
            tenant_id=args.tenant_id,
            policy_slug=args.policy_slug,
            text=draft,
            evidence_types=ev_types,
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
        print(json.dumps({"pre": pre, "post": post, "content": draft}, ensure_ascii=False))
    else:
        print(draft)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
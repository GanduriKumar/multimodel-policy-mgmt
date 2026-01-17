"""
Backfill missing DecisionLog entries for RequestLog rows.
For each request without a decision, call the /api/protect endpoint with the original input_text
and policy context to create a decision snapshot.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any

from sqlalchemy import text
from app.db.session import engine

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("BACKEND_API_KEY")
API_KEY_HEADER = os.getenv("BACKEND_API_KEY_HEADER", "x-api-key")


def _json_post(url: str, payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            if v is not None:
                req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def main(limit: int = 50):
    headers: Dict[str, str] = {}
    if API_KEY:
        headers[API_KEY_HEADER] = API_KEY
    protect_url = BACKEND_URL + "/api/protect"

    with engine.connect() as conn:
        rows = conn.execute(text(
            """
            SELECT id, tenant_id, policy_id, input_text
            FROM request_log r
            WHERE NOT EXISTS (
              SELECT 1 FROM decision_log d WHERE d.request_log_id = r.id
            )
            ORDER BY r.created_at DESC
            LIMIT :limit
            """
        ), {"limit": limit}).fetchall()
        if not rows:
            print("No requests missing decisions.")
            return 0
        print(f"Found {len(rows)} request(s) with no decisions. Backfilling via /api/protect...")
        ok = 0
        failed = 0
        for rid, tenant_id, policy_id, input_text in rows:
            payload = {
                "tenant_id": int(tenant_id),
                "policy_id": int(policy_id) if policy_id is not None else None,
                "input_text": input_text,
                "metadata": {"stage": "backfill"},
            }
            try:
                resp = _json_post(protect_url, payload, headers)
                if isinstance(resp, dict) and "allowed" in resp:
                    ok += 1
                    print(f"  ✓ Backfilled decision for request {rid}: allowed={resp['allowed']}")
                else:
                    failed += 1
                    print(f"  ✗ Unexpected response for request {rid}: {resp}")
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                failed += 1
                print(f"  ✗ Backfill failed for request {rid}: {e}")
        print(f"Done. Success: {ok}, Failed: {failed}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

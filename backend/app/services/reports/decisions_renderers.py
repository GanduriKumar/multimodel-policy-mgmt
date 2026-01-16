from __future__ import annotations

from typing import Iterable, List

import csv
import io
import json

from app.services.reports.decisions import DecisionEvent


SCHEMA_FIELDS = [
    # ids
    "tenant_id",
    "policy_id",
    "policy_version_id",
    "request_log_id",
    "decision_log_id",
    # decision
    "allowed",
    "reasons",
    "risk_score",
    "evidence_present",
    # timestamps
    "decided_at_utc",
    "decided_at_local",
    "local_timezone",
    # integrity
    "event_id",
    "canonical_json_sha256",
    "input_hash",
    "evidence_ids",
    "evidence_hashes",
    "evidence_types",
    "evidence_sources",
    # context
    "request_id",
    "client_ip",
    "user_agent",
    "policy_name",
]


def _normalize_events(events: Iterable[DecisionEvent]) -> List[dict]:
    rows = [e.dict() for e in events]
    rows.sort(key=lambda r: r.get("decided_at_utc", ""), reverse=True)
    return rows


def to_csv(events: List[DecisionEvent]) -> bytes:
    rows = _normalize_events(events)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=SCHEMA_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k) for k in SCHEMA_FIELDS})
    data = buf.getvalue().encode("utf-8")
    return b"\xef\xbb\xbf" + data


def to_ndjson(events: List[DecisionEvent]) -> bytes:
    rows = _normalize_events(events)
    if not rows:
        return b""
    out_lines = []
    for r in rows:
        out_lines.append(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
    return ("\n".join(out_lines) + "\n").encode("utf-8")


def to_json_array(events: List[DecisionEvent]) -> bytes:
    rows = _normalize_events(events)
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

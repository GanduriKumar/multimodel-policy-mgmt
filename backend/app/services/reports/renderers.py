from __future__ import annotations

from typing import Iterable, List

import csv
import io
import json

from app.services.reports.policy_changes import PolicyChangeEvent


SCHEMA_FIELDS = [
    "tenant_id",
    "policy_id",
    "policy_name",
    "version_id",
    "version",
    "is_active",
    "change_type",
    "changed_by",
    "changed_at_utc",
    "changed_at_local",
    "local_timezone",
    "event_id",
    "document_sha256",
    "diff_summary",
]


def _normalize_events(events: Iterable[PolicyChangeEvent]) -> List[dict]:
    # Convert to dicts and ensure order newest-first by changed_at_utc
    rows = [e.dict() for e in events]
    rows.sort(key=lambda r: r.get("changed_at_utc", ""), reverse=True)
    return rows


def to_csv(events: List[PolicyChangeEvent]) -> bytes:
    rows = _normalize_events(events)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=SCHEMA_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k) for k in SCHEMA_FIELDS})
    data = buf.getvalue().encode("utf-8")
    # Prepend UTF-8 BOM for Excel compatibility
    return b"\xef\xbb\xbf" + data


def to_ndjson(events: List[PolicyChangeEvent]) -> bytes:
    rows = _normalize_events(events)
    if not rows:
        return b""
    out_lines = []
    for r in rows:
        out_lines.append(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
    return ("\n".join(out_lines) + "\n").encode("utf-8")


def to_json_array(events: List[PolicyChangeEvent]) -> bytes:
    rows = _normalize_events(events)
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

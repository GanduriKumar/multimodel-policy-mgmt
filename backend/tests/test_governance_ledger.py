import json
from pathlib import Path

import pytest

from app.services.governance_ledger import GovernanceLedger


def _make_ledger(tmp_path: Path) -> GovernanceLedger:
    ledger_path = tmp_path / "ledger.jsonl"
    return GovernanceLedger(path=str(ledger_path), secret="test-secret")


def test_verify_chain_true_when_log_missing(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)
    # No file created yet -> should verify as True (empty chain is valid)
    assert ledger.verify_chain() is True


def test_append_multiple_entries_same_trace_valid_chain(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)

    trace_id = "trace-123"
    # Append several kinds under same trace id
    h1 = ledger.append_entry("request", {"request_log_id": 1, "tenant_id": 7}, trace_id)
    assert isinstance(h1, str) and len(h1) == 64
    h2 = ledger.append_entry("decision", {"decision_id": 11, "request_log_id": 1, "allowed": True}, trace_id)
    assert isinstance(h2, str) and len(h2) == 64
    h3 = ledger.append_entry(
        "model_output",
        {"request_log_id": 1, "provider": "openai", "model": "gpt-test", "preview": "ok"},
        trace_id,
    )
    assert isinstance(h3, str) and len(h3) == 64

    # The intact file should verify
    assert ledger.verify_chain() is True

    # Optional: sanity check prev_hash linkage by reading and comparing
    path = Path(ledger.path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])
    e3 = json.loads(lines[2])
    assert e2["prev_hash"] == e1["hash"]
    assert e3["prev_hash"] == e2["hash"]


def test_verify_chain_detects_corruption(tmp_path: Path) -> None:
    ledger = _make_ledger(tmp_path)
    trace_id = "t-1"
    ledger.append_entry("request", {"request_log_id": 5}, trace_id)
    ledger.append_entry("decision", {"decision_id": 9, "request_log_id": 5, "allowed": False}, trace_id)
    assert ledger.verify_chain() is True

    # Corrupt the first line's hash while keeping valid JSON shape
    p = Path(ledger.path)
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    first = json.loads(lines[0])
    first["hash"] = "0" * 64  # invalid hash that won't match recomputation
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Now verification must fail
    assert ledger.verify_chain() is False

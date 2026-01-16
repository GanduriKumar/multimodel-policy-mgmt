# Prompt 2: Canonical JSON + SHA-256 for Policy Documents

- What it implements: Deterministic canonicalization of policy document JSON and computation of a SHA-256 hex digest. Ensures identical logical documents yield identical canonical strings and hashes, suitable for compliance, integrity, and deduplication. To be reused by the reports pipeline.
- Dependency: Prompt 1 (events will pass version documents here for hashing).

## Prompt
```
Write complete and executable code to canonicalize a Python dict representing a policy document and compute a SHA-256 hex digest.

Requirements:
- Input: any JSON-serializable Python object (dicts, lists, strings, numbers, booleans, null), typically a policy document dict.
- Output: (canonical_json: str, sha256_hex: str)
- Canonical JSON rules:
  - Sort all object keys lexicographically at every nesting level.
  - No insignificant whitespace (use compact separators, e.g., separators=(",", ":"))
  - Ensure stable representation of numbers (ints and floats)
  - Preserve order within arrays/lists (do not sort arrays)
  - Ensure Unicode is serialized in a normalized, deterministic form (NFC); escape only where JSON requires
  - Disallow NaN/Infinity (raise a ValueError if present)
- Encoding: canonical_json must be UTF-8 encodable; compute SHA-256 over canonical_json.encode("utf-8").

Implementation details:
- Provide a public function canonicalize_and_hash(obj: Any) -> tuple[str, str]
- Optionally expose helpers: ensure_canonical(obj) -> Any and to_canonical_json(obj) -> str
- Use only standard library if possible (json, hashlib, unicodedata); avoid extra deps
- Include type hints and docstrings
- Robust error handling with clear messages for non-serializable inputs

File locations:
- Module: backend/app/services/reports/canonicalization.py
- Tests: backend/tests/test_reports_canonicalization.py

Tests (pytest):
- Determinism: two equal dicts with different key orders produce identical canonical_json and sha256
- Nested structures: dicts of dicts, lists of dicts
- List order sensitivity: swapping array elements changes hash
- Unicode stability: strings with composed/decomposed forms (NFC vs NFD) produce identical canonical outputs and hashes after normalization
- Numbers: ints and floats serialize stably; reject NaN/Infinity with ValueError
- Large document: performance sanity (within reasonable time) and stable output
- Edge cases: empty dict, empty list, nulls, booleans
- Assert canonical_json is valid JSON that round-trips to the same Python structure
- Print or assert exact sha256_hex for known fixtures

Deliverables:
- backend/app/services/reports/canonicalization.py with implementation
- backend/tests/test_reports_canonicalization.py with passing tests
- Test run output demonstrating success
```

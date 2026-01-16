# Prompt 3: Policy Document Diff Summaries

- What it implements: A deterministic diff between two policy document dicts producing (a) a concise human-readable summary and (b) a structured diff object. Focus fields: risk_threshold, conservative_mode, blocked_terms, required_evidence_types, pii_rules, intent_rules.
- Dependency: Prompt 1 (event pairs), Prompt 2 (canonicalization optional for stable comparisons).

## Prompt
```
Write complete and executable code to compute a diff between two policy document dicts (old_doc, new_doc).

Requirements:
- Inputs: old_doc: dict | None, new_doc: dict | None
- Outputs:
  - summary: str (concise, single-line or short multi-line)
  - diff: dict with keys { added: {...}, removed: {...}, modified: {...} }
- Compare these fields:
  - risk_threshold (int)
  - conservative_mode (bool)
  - blocked_terms (list[str]) – compare as case-insensitive sets; report additions/removals; preserve original casing in output
  - required_evidence_types (list[str]) – set diff
  - pii_rules (dict) – deep-compare keys/values; report key-level adds/removes/modifies
  - intent_rules (dict) – consider two subfields:
      * deny: list[str] – set diff
      * thresholds: dict[str->float] – per-key add/remove/modify with numeric deltas
- Treat other fields as opaque; ignore unless included above.
- Order-insensitive where lists represent sets; preserve deterministic output order in diff (alphabetical keys).
- Handle None inputs: if old_doc is None -> all fields are added; if new_doc is None -> all fields are removed.
- Generate summary string such as:
  - "risk_threshold: 50→65; blocked_terms: +2 -1; intent_rules.deny: +weapon_instruction; pii_rules: modified keys=2"

Implementation details:
- Public function diff_policy_docs(old_doc: dict | None, new_doc: dict | None) -> tuple[str, dict]
- Provide helpers for set-like list diffs and deep dict diffs
- Include type hints and docstrings

Files:
- Module: backend/app/services/reports/diffing.py
- Tests: backend/tests/test_reports_diffing.py

Tests (pytest):
- Threshold change only
- Add/remove blocked_terms and ensure case-insensitive matching with original casing preserved
- intent_rules deny/thresholds add/remove/modify with float comparisons
- pii_rules nested diffs (add/remove keys and modify values)
- None vs dict (pure additions/removals)
- Summary formatting stable and informative
```

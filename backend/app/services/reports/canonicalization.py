"""
Canonical JSON + SHA-256 utilities for policy documents.

Produces a deterministic JSON string and a stable SHA-256 hash for any
JSON-serializable Python object. Ensures:
- Sorted object keys
- Compact JSON (no insignificant whitespace)
- Unicode strings normalized to NFC
- NaN/Infinity are rejected
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, MutableSequence

import hashlib
import json
import math
import unicodedata


def _normalize_string(s: str) -> str:
    """Normalize Unicode string to NFC form."""
    return unicodedata.normalize("NFC", s)


def _ensure_serializable(obj: Any) -> Any:
    """
    Recursively normalize an object for deterministic JSON serialization:
    - Dict keys and string values normalized to NFC
    - Reject NaN/Infinity by pre-checking floats
    - Convert non-str dict keys to str deterministically
    Returns a new structure (does not mutate input).
    """
    # Primitives
    if obj is None or isinstance(obj, (bool, int)):
        return obj
    if isinstance(obj, float):
        # Reject NaN/Infinity explicitly (json.dumps with allow_nan=False would also fail)
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("NaN or Infinity not allowed in canonical JSON")
        return obj
    if isinstance(obj, str):
        return _normalize_string(obj)

    # Lists/tuples
    if isinstance(obj, (list, tuple)):
        return [ _ensure_serializable(v) for v in obj ]

    # Dicts / mappings: normalize keys (to str + NFC) and values
    if isinstance(obj, Mapping):
        normalized: dict[str, Any] = {}
        for k, v in obj.items():
            # Convert keys to string deterministically
            k_str = str(k) if not isinstance(k, str) else k
            k_norm = _normalize_string(k_str)
            if k_norm in normalized:
                # Key collision after normalization
                raise ValueError(f"Duplicate key after normalization: {k_norm!r}")
            normalized[k_norm] = _ensure_serializable(v)
        return normalized

    # Other types are not JSON-serializable
    raise ValueError(f"Unsupported type for canonical JSON: {type(obj).__name__}")


def to_canonical_json(obj: Any) -> str:
    """
    Convert a JSON-serializable object to canonical JSON string:
    - NFC-normalized strings
    - Sorted keys, compact separators
    - ensure_ascii=False to preserve Unicode
    - allow_nan=False to enforce strict JSON
    """
    normalized = _ensure_serializable(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonicalize_and_hash(obj: Any) -> tuple[str, str]:
    """
    Produce (canonical_json, sha256_hex) for the given object.
    """
    canonical = to_canonical_json(obj)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return canonical, digest

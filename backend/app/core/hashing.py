"""
Deterministic SHA-256 hashing utilities.

- sha256_text: Hashes a UTF-8 encoded text string.
- sha256_json: Hashes a JSON-serializable dict with sorted keys and UTF-8 encoding.
"""

from __future__ import annotations

import hashlib
import json

__all__ = ["sha256_text", "sha256_json"]


def sha256_text(text: str) -> str:
    """
    Compute the SHA-256 hex digest of a text string using UTF-8 encoding.

    Args:
        text: The input text to hash.

    Returns:
        The hexadecimal SHA-256 digest as a lowercase string.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    # Encode text to UTF-8 bytes and hash
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: dict) -> str:
    """
    Compute the SHA-256 hex digest of a JSON-serializable dict.

    Determinism rules:
    - Keys are sorted to ensure stable ordering.
    - Compact separators avoid whitespace differences.
    - UTF-8 encoding is used for hashing.

    Args:
        obj: The dictionary to serialize and hash.

    Returns:
        The hexadecimal SHA-256 digest as a lowercase string.
    """
    if not isinstance(obj, dict):
        raise TypeError("obj must be a dict")

    # Canonical JSON: sorted keys, compact separators, do not ASCII-escape, then UTF-8 encode
    json_str = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
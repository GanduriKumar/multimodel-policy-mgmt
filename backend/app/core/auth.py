"""
API key hashing and verification using HMAC-SHA256.

- hash_api_key(raw): Derives a stable HMAC-SHA256 hex digest from the given raw API key.
- verify_api_key(raw, hashed): Constant-time verification of a raw key against a stored hash.

Secret source:
- Loaded from the first defined environment variable among:
  API_KEY_SECRET, AUTH_SECRET, SECRET_KEY, APP_AUTH_SECRET
- Falls back to a safe development default if none are set.

Notes:
- Hex digests are lowercase.
- Functions are pure/deterministic for a given environment secret.
"""

from __future__ import annotations

import hmac
import hashlib
import os
from typing import Optional

__all__ = ["hash_api_key", "verify_api_key"]


# -------------------------------
# Secret loading
# -------------------------------

def _load_secret() -> str:
    """
    Load the HMAC secret from environment variables.
    Uses a development-safe default if none are provided.
    """
    candidates = (
        os.getenv("API_KEY_SECRET"),
        os.getenv("AUTH_SECRET"),
        os.getenv("SECRET_KEY"),
        os.getenv("APP_AUTH_SECRET"),
    )
    for candidate in candidates:
        if candidate and candidate.strip():
            return candidate.strip()
    # Development/default fallback. Override in production!
    return "dev-secret"


_SECRET: str = _load_secret()


# -------------------------------
# Public API
# -------------------------------

def hash_api_key(raw: str) -> str:
    """
    Compute HMAC-SHA256 hex digest of the provided API key using the environment secret.

    Args:
        raw: The raw API key material.

    Returns:
        Lowercase hexadecimal HMAC-SHA256 digest string.
    """
    if not isinstance(raw, str):
        raise TypeError("raw must be a str")
    key_bytes = _SECRET.encode("utf-8")
    msg_bytes = raw.encode("utf-8")
    digest = hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()
    return digest


def verify_api_key(raw: str, hashed: str) -> bool:
    """
    Verify that the provided raw API key matches the stored HMAC-SHA256 hash.

    Args:
        raw: Raw API key to verify.
        hashed: Stored hexadecimal HMAC-SHA256 digest to compare against.

    Returns:
        True if the hash of `raw` matches `hashed` (constant-time), else False.
    """
    if not isinstance(raw, str):
        raise TypeError("raw must be a str")
    if not isinstance(hashed, str):
        raise TypeError("hashed must be a str")

    computed = hash_api_key(raw)
    # Normalize to lowercase for robust comparison against hex digests.
    return hmac.compare_digest(computed, hashed.lower())
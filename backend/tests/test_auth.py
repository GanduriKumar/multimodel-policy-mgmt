import os
import sys
import importlib

import pytest

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def _load_auth_module_with_secret(monkeypatch, secret: str = "test-secret"):
    """
    Helper to set the API key secret and reload the auth module so it picks up the new env.
    """
    monkeypatch.setenv("API_KEY_SECRET", secret)
    # Import (or reload) the module after setting env so the secret is captured
    auth_mod = importlib.import_module("app.core.auth")
    auth_mod = importlib.reload(auth_mod)
    return auth_mod


def test_hash_api_key_deterministic(monkeypatch):
    auth = _load_auth_module_with_secret(monkeypatch, "unit-test-secret")
    key = "api-key-123"

    h1 = auth.hash_api_key(key)
    h2 = auth.hash_api_key(key)

    assert isinstance(h1, str) and isinstance(h2, str)
    assert h1 == h2  # same input, same output
    assert len(h1) == 64  # sha256 hex digest length
    assert h1.islower()  # hex lowercase


def test_hash_api_key_differs_for_different_inputs(monkeypatch):
    auth = _load_auth_module_with_secret(monkeypatch, "unit-test-secret")
    k1 = "alpha"
    k2 = "beta"

    h1 = auth.hash_api_key(k1)
    h2 = auth.hash_api_key(k2)

    assert h1 != h2  # different inputs, different hashes


def test_verify_api_key_matches_and_mismatches(monkeypatch):
    auth = _load_auth_module_with_secret(monkeypatch, "unit-test-secret")
    raw = "s3cr3t-key"
    hashed = auth.hash_api_key(raw)

    # Correct match
    assert auth.verify_api_key(raw, hashed) is True

    # Uppercase hashed should still verify (robustness)
    assert auth.verify_api_key(raw, hashed.upper()) is True

    # Wrong raw should fail
    assert auth.verify_api_key("wrong-key", hashed) is False

    # Totally unrelated hash should fail
    other_hash = auth.hash_api_key("different")
    assert auth.verify_api_key(raw, other_hash) is False
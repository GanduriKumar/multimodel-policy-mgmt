import os
import sys
import hashlib
import json

# Ensure the 'backend' directory is on sys.path so we can import app modules when running tests from repo root
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.hashing import sha256_text, sha256_json


def test_sha256_text_deterministic_and_known_value():
    # Deterministic: same input yields same output
    text = "hello"
    h1 = sha256_text(text)
    h2 = sha256_text(text)
    assert h1 == h2

    # Known SHA-256 for "hello"
    assert h1 == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_sha256_text_unicode_utf8():
    # Unicode input should be hashed as UTF-8
    text = "Café 🚀 — 日本語 — عربى"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert sha256_text(text) == expected

    # Deterministic check
    assert sha256_text(text) == expected


def test_sha256_json_key_order_independent_and_unicode():
    # Two dicts with same data but different key orders (including nested) should hash the same
    obj1 = {"name": "café", "emoji": "🚀", "lang": "日本語", "nested": {"x": 1, "y": 2}}
    obj2 = {"nested": {"y": 2, "x": 1}, "lang": "日本語", "emoji": "🚀", "name": "café"}

    h1 = sha256_json(obj1)
    h2 = sha256_json(obj2)

    # Key order independence
    assert h1 == h2

    # Deterministic and canonical JSON confirmation
    canonical = json.dumps(obj1, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert h1 == expected
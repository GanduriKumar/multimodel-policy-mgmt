from __future__ import annotations

import json
import math

import pytest

from app.services.reports.canonicalization import canonicalize_and_hash, to_canonical_json


def test_determinism_key_order():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    ca, ha = canonicalize_and_hash(a)
    cb, hb = canonicalize_and_hash(b)
    assert ca == cb and ha == hb


def test_nested_and_list_order_sensitivity():
    obj1 = {"x": [1, 2, {"k": "v"}]}
    obj2 = {"x": [1, {"k": "v"}, 2]}
    c1, h1 = canonicalize_and_hash(obj1)
    c2, h2 = canonicalize_and_hash(obj2)
    assert c1 != c2 and h1 != h2


def test_unicode_normalization():
    # 'é' composed vs decomposed
    composed = "café"
    decomposed = "cafe\u0301"
    c1, h1 = canonicalize_and_hash({"t": composed})
    c2, h2 = canonicalize_and_hash({"t": decomposed})
    assert c1 == c2 and h1 == h2


def test_reject_nan_and_infinity():
    with pytest.raises(ValueError):
        canonicalize_and_hash({"v": float("nan")})
    with pytest.raises(ValueError):
        canonicalize_and_hash({"v": float("inf")})


def test_roundtrip_valid_json():
    obj = {"a": [1, 2, 3], "b": {"x": True, "y": None}}
    s, h = canonicalize_and_hash(obj)
    parsed = json.loads(s)
    assert parsed == obj

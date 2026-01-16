from __future__ import annotations

from app.services.reports.diffing import diff_policy_docs


def test_threshold_change_only():
    s, d = diff_policy_docs({"risk_threshold": 50}, {"risk_threshold": 65})
    assert "risk_threshold: 50→65" in s
    assert d["modified"]["risk_threshold"]["old"] == 50
    assert d["modified"]["risk_threshold"]["new"] == 65


def test_blocked_terms_case_insensitive():
    o = {"blocked_terms": ["Kill", "murder"]}
    n = {"blocked_terms": ["kill", "stab"]}
    s, d = diff_policy_docs(o, n)
    bt = d["modified"]["blocked_terms"]
    assert set(bt["added"]) == {"stab"}
    assert set(bt["removed"]) == {"Kill"}


def test_intent_rules_deny_and_thresholds():
    o = {"intent_rules": {"deny": ["weapon_instruction"], "thresholds": {"weapon_instruction": 0.6}}}
    n = {"intent_rules": {"deny": ["weapon_instruction", "incite_violence"], "thresholds": {"weapon_instruction": 0.7}}}
    s, d = diff_policy_docs(o, n)
    ir = d["modified"]["intent_rules"]
    assert ir["deny"]["added"] == ["incite_violence"]
    assert ir["thresholds"]["modified"]["weapon_instruction"]["old"] == 0.6
    assert ir["thresholds"]["modified"]["weapon_instruction"]["new"] == 0.7


def test_pii_rules_nested():
    o = {"pii_rules": {"deny_on_email": False, "deny_on_ssn": True}}
    n = {"pii_rules": {"deny_on_email": True, "deny_on_ssn": True, "deny_on_dob": True}}
    s, d = diff_policy_docs(o, n)
    pr = d["modified"]["pii_rules"]
    assert pr["added"].get("deny_on_dob") is True
    assert pr["modified"]["deny_on_email"]["old"] is False
    assert pr["modified"]["deny_on_email"]["new"] is True


def test_none_additions_and_removals():
    s1, d1 = diff_policy_docs(None, {"risk_threshold": 50, "blocked_terms": ["x"]})
    assert "added:" in s1 and "risk_threshold" in s1
    s2, d2 = diff_policy_docs({"risk_threshold": 50, "blocked_terms": ["x"]}, None)
    assert "removed:" in s2 and "risk_threshold" in s2

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import json


def _casefold_set(items: List[str]) -> dict[str, str]:
    """Return mapping of casefolded->original (first occurrence) for a list of strings."""
    out: dict[str, str] = {}
    for s in items or []:
        if not isinstance(s, str):
            continue
        k = s.casefold()
        out.setdefault(k, s)
    return out


def _json_equal(a: Any, b: Any) -> bool:
    try:
        return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))
    except Exception:
        return a == b


def diff_policy_docs(old_doc: Optional[dict], new_doc: Optional[dict]) -> Tuple[str, dict]:
    """
    Compute a deterministic diff focused on key policy fields.

    Returns (summary, diff) where diff has keys: added, removed, modified.
    """
    fields = [
        "risk_threshold",
        "conservative_mode",
        "blocked_terms",
        "required_evidence_types",
        "pii_rules",
        "intent_rules",
    ]

    added: dict = {}
    removed: dict = {}
    modified: dict = {}
    summary_parts: List[str] = []

    # Handle None cases
    if old_doc is None and new_doc is None:
        return "", {"added": {}, "removed": {}, "modified": {}}
    if old_doc is None:
        # Everything present is added (only the fields we care about)
        for f in fields:
            if f in (new_doc or {}):
                added[f] = (new_doc or {}).get(f)
        return "added: " + ", ".join(sorted(added.keys())), {"added": added, "removed": {}, "modified": {}}
    if new_doc is None:
        for f in fields:
            if f in (old_doc or {}):
                removed[f] = (old_doc or {}).get(f)
        return "removed: " + ", ".join(sorted(removed.keys())), {"added": {}, "removed": removed, "modified": {}}

    o = old_doc or {}
    n = new_doc or {}

    # risk_threshold
    if o.get("risk_threshold") != n.get("risk_threshold"):
        modified["risk_threshold"] = {"old": o.get("risk_threshold"), "new": n.get("risk_threshold")}
        summary_parts.append(f"risk_threshold: {o.get('risk_threshold')}→{n.get('risk_threshold')}")

    # conservative_mode
    if o.get("conservative_mode") != n.get("conservative_mode"):
        modified["conservative_mode"] = {"old": o.get("conservative_mode"), "new": n.get("conservative_mode")}
        summary_parts.append(f"conservative_mode: {o.get('conservative_mode')}→{n.get('conservative_mode')}")

    # blocked_terms (case-insensitive set diff, preserve casing per side)
    o_bt = o.get("blocked_terms") or []
    n_bt = n.get("blocked_terms") or []
    if isinstance(o_bt, list) and isinstance(n_bt, list):
        o_map = _casefold_set([x for x in o_bt if isinstance(x, str)])
        n_map = _casefold_set([x for x in n_bt if isinstance(x, str)])
        add_keys = sorted([k for k in n_map.keys() if k not in o_map])
        rem_keys = sorted([k for k in o_map.keys() if k not in n_map])
        if add_keys or rem_keys:
            modified["blocked_terms"] = {
                "added": [n_map[k] for k in add_keys],
                "removed": [o_map[k] for k in rem_keys],
            }
            summary_parts.append(f"blocked_terms: +{len(add_keys)} -{len(rem_keys)}")

    # required_evidence_types (set diff, case-sensitive)
    o_re = o.get("required_evidence_types") or []
    n_re = n.get("required_evidence_types") or []
    if isinstance(o_re, list) and isinstance(n_re, list):
        o_set = set([x for x in o_re if isinstance(x, str)])
        n_set = set([x for x in n_re if isinstance(x, str)])
        adds = sorted(n_set - o_set)
        rems = sorted(o_set - n_set)
        if adds or rems:
            modified["required_evidence_types"] = {"added": adds, "removed": rems}
            summary_parts.append(f"required_evidence_types: +{len(adds)} -{len(rems)}")

    # pii_rules (top-level key diff)
    o_pii = o.get("pii_rules") or {}
    n_pii = n.get("pii_rules") or {}
    if isinstance(o_pii, dict) and isinstance(n_pii, dict):
        o_keys = set(o_pii.keys())
        n_keys = set(n_pii.keys())
        added_keys = sorted(n_keys - o_keys)
        removed_keys = sorted(o_keys - n_keys)
        modified_keys = []
        mods: dict = {}
        for k in sorted(o_keys & n_keys):
            if not _json_equal(o_pii.get(k), n_pii.get(k)):
                modified_keys.append(k)
                mods[k] = {"old": o_pii.get(k), "new": n_pii.get(k)}
        if added_keys or removed_keys or modified_keys:
            modified["pii_rules"] = {
                "added": {k: n_pii[k] for k in added_keys},
                "removed": {k: o_pii[k] for k in removed_keys},
                "modified": mods,
            }
            summary_parts.append(
                f"pii_rules: +{len(added_keys)} -{len(removed_keys)} ~{len(modified_keys)}"
            )

    # intent_rules: deny (set diff), thresholds (per-key add/remove/modify with deltas)
    o_ir = o.get("intent_rules") or {}
    n_ir = n.get("intent_rules") or {}
    if isinstance(o_ir, dict) and isinstance(n_ir, dict):
        # deny list
        o_den = set([x for x in (o_ir.get("deny") or []) if isinstance(x, str)])
        n_den = set([x for x in (n_ir.get("deny") or []) if isinstance(x, str)])
        d_adds = sorted(n_den - o_den)
        d_rems = sorted(o_den - n_den)
        if d_adds or d_rems:
            modified.setdefault("intent_rules", {})["deny"] = {"added": d_adds, "removed": d_rems}
            summary_parts.append(f"intent_rules.deny: +{len(d_adds)} -{len(d_rems)}")

        # thresholds
        o_th = o_ir.get("thresholds") or {}
        n_th = n_ir.get("thresholds") or {}
        if isinstance(o_th, dict) and isinstance(n_th, dict):
            o_keys = set(o_th.keys())
            n_keys = set(n_th.keys())
            t_adds = sorted(n_keys - o_keys)
            t_rems = sorted(o_keys - n_keys)
            t_mods: dict = {}
            for k in sorted(o_keys & n_keys):
                try:
                    o_val = float(o_th.get(k))
                    n_val = float(n_th.get(k))
                except Exception:
                    if o_th.get(k) != n_th.get(k):
                        t_mods[k] = {"old": o_th.get(k), "new": n_th.get(k)}
                    continue
                if o_val != n_val:
                    t_mods[k] = {"old": o_val, "new": n_val, "delta": n_val - o_val}
            if t_adds or t_rems or t_mods:
                modified.setdefault("intent_rules", {})["thresholds"] = {
                    "added": {k: n_th[k] for k in t_adds},
                    "removed": {k: o_th[k] for k in t_rems},
                    "modified": t_mods,
                }
                summary_parts.append(
                    f"intent_rules.thresholds: +{len(t_adds)} -{len(t_rems)} ~{len(t_mods)}"
                )

    summary = "; ".join(summary_parts)
    return summary, {"added": added, "removed": removed, "modified": modified}

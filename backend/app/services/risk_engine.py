"""
Risk engine that scores input text for potential safety risks.

- Uses detectors from app.core.patterns:
  - detect_prompt_injection
  - detect_secret_like
  - detect_pii_like

Scoring (capped at 100):
- Prompt injection: 40 base + 5 per additional marker
- Secret-like:      50 base + 3 per additional marker
- PII-like:         30 base + 2 per additional marker
- Category synergy: +5 for each additional category present (beyond the first)
- Evidence missing: +10 if evidence_present is False

Returns:
    (risk_score:int [0-100], reasons:list[str])
"""

from __future__ import annotations

from typing import List, Tuple, Dict

from app.core.patterns import (
    detect_prompt_injection,
    detect_secret_like,
    detect_pii_like,
    detect_violence_like,
)


def _local_intent_classifier(text: str) -> Dict[str, float]:
    """
    Pattern-based intent classifier.
    Returns mapping label -> score in [0,1].
    Labels: weapon_instruction, incite_violence, depict_violence
    """
    text_l = text.lower()
    scores: Dict[str, float] = {}
    
    # Weapon instruction heuristics
    if any(k in text_l for k in ["how to build a bomb", "make a bomb", "build a weapon", "assemble a gun", "explosive recipe", "detonator"]):
        scores["weapon_instruction"] = 0.9
    elif any(k in text_l for k in ["how to make", "how to build"]) and any(k in text_l for k in ["bomb", "gun", "explosive", "detonator", "weapon"]):
        scores["weapon_instruction"] = max(scores.get("weapon_instruction", 0), 0.75)
    
    # Incite violence heuristics (expanded to include harm planning)
    incite_phrases = [
        "kill them",
        "kill all",
        "kill someone",
        "murder someone",
        "murder them",
        "attack them",
        "attack the city",
        "bomb the city",
        "drop a bomb",
        "drop a nuclear bomb",
        "wipe out",
        "wipe out the",
        "decimate the city",
        "destroy the city",
        "obliterate",
        "annihilate",
        "genocide",
        "harm them",
        "harm someone",
        "exterminate",
        "eliminate someone",
        "eliminate them",
        "assassinate",
        "get rid of someone",
        "get rid of them",
    ]
    
    # Harm planning phrases (how to/plan to cause harm)
    harm_planning = [
        "how to kill",
        "how to murder",
        "how to eliminate",
        "how to harm",
        "how to hurt",
        "plan to kill",
        "plan to murder",
        "plan to eliminate",
        "plan to harm",
        "plan to hurt",
        "plan how to kill",
        "plan how to murder",
        "plan how to eliminate",
        "plan how to harm",
    ]
    
    if any(k in text_l for k in incite_phrases):
        scores["incite_violence"] = max(scores.get("incite_violence", 0), 0.9)
    elif any(k in text_l for k in harm_planning):
        scores["incite_violence"] = max(scores.get("incite_violence", 0), 0.95)
    
    # Depiction (usually allowed)
    depiction_cues = [
        "murder mystery",
        "murder story",
        "violent scene",
        "crime thriller",
        # creative writing intents
        "write a ", "write an ", "draft a ", "compose a ",
        "screenplay", "script", "novel", "short story", "poem", "fiction",
        "plot", "outline", "synopsis",
    ]
    violence_terms = [
        "murder", "kill", "violent", "violence", "gun", "weapon", "bomb", "shoot", "stab",
    ]
    if any(cue in text_l for cue in depiction_cues) and any(v in text_l for v in violence_terms):
        scores["depict_violence"] = max(scores.get("depict_violence", 0), 0.7)
    elif any(k in text_l for k in ["murder mystery", "murder story", "violent scene", "crime thriller"]):
        scores["depict_violence"] = max(scores.get("depict_violence", 0), 0.6)
    
    return scores


def compute_risk(input_text: str, evidence_present: bool) -> tuple[int, list[str]]:
    """
    Compute a risk score and reasons based on detectors and evidence presence.

    Args:
        input_text: The text to analyze.
        evidence_present: Whether sufficient evidence is present to support claims.

    Returns:
        A tuple of (risk_score in [0, 100], reasons list).
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a str")
    if not isinstance(evidence_present, bool):
        raise TypeError("evidence_present must be a bool")

    # Run detectors
    inj_markers = detect_prompt_injection(input_text)
    sec_markers = detect_secret_like(input_text)
    pii_markers = detect_pii_like(input_text)
    vio_markers = detect_violence_like(input_text)
    intents = _local_intent_classifier(input_text)

    # Collect reasons (deduplicated)
    reasons: set[str] = set()
    reasons.update(f"prompt_injection:{m}" for m in inj_markers)
    reasons.update(f"secret_like:{m}" for m in sec_markers)
    reasons.update(f"pii_like:{m}" for m in pii_markers)
    reasons.update(f"violence_like:{m}" for m in vio_markers)
    for label, score in intents.items():
        reasons.add(f"intent:{label}:{score:.2f}")
    # Promote DOB to a stronger PII-like marker if present
    if "date_of_birth" in pii_markers:
        reasons.add("pii_like:date_of_birth")

    # Scoring based on matches
    score = 0

    # Prompt injection scoring
    if inj_markers:
        score += 40 + max(0, len(inj_markers) - 1) * 5

    # Secret-like scoring
    if sec_markers:
        score += 50 + max(0, len(sec_markers) - 1) * 3

    # PII-like scoring
    if pii_markers:
        score += 30 + max(0, len(pii_markers) - 1) * 2
    # Violence-like scoring influenced by intent
    v_weapon = intents.get("weapon_instruction", 0) >= 0.5
    v_incite = intents.get("incite_violence", 0) >= 0.5
    v_depict = intents.get("depict_violence", 0) >= 0.5
    if vio_markers:
        if v_weapon or v_incite:
            # Strong risk when instructing or inciting
            score += 70 + max(0, len(vio_markers) - 1) * 5
        elif v_depict:
            # Creative/depiction context: minimal risk bump
            score += 5
        else:
            # Ambiguous mentions: modest risk
            score += 20
    # Intent scoring (weapon/incite strongly)
    if v_weapon:
        score += 80
    if v_incite:
        score += 80
    if v_depict:
        # No extra beyond the small bump above to avoid double counting
        score += 0

    # Synergy bonus if multiple categories are present
    categories_present = sum(
        [
            1 if inj_markers else 0,
            1 if sec_markers else 0,
            1 if pii_markers else 0,
            1 if vio_markers else 0,
        ]
    )
    if categories_present > 1:
        score += (categories_present - 1) * 5

    # Evidence consideration
    if not evidence_present:
        score += 10
        reasons.add("evidence_missing")

    # Cap score to [0, 100]
    score = max(0, min(100, score))

    return score, sorted(reasons)

def _split_reasons(reasons: List[str]) -> tuple[List[str], List[str]]:
    """
    Split combined reasons into (policy_reasons, risk_reasons) heuristically.
    """
    policy: List[str] = []
    risk: List[str] = []
    for r in reasons or []:
        if (
            r.startswith("prompt_injection:")
            or r.startswith("pii_like:")
            or r.startswith("secret_like:")
            or r.startswith("risk_above_threshold")
            or r == "evidence_missing"  # risk engine marker
        ):
            risk.append(r)
        else:
            policy.append(r)
    return policy, risk
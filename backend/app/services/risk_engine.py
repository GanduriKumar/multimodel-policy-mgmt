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

from typing import List, Tuple

from app.core.patterns import (
    detect_prompt_injection,
    detect_secret_like,
    detect_pii_like,
)


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

    # Collect reasons (deduplicated)
    reasons: set[str] = set()
    reasons.update(f"prompt_injection:{m}" for m in inj_markers)
    reasons.update(f"secret_like:{m}" for m in sec_markers)
    reasons.update(f"pii_like:{m}" for m in pii_markers)

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

    # Synergy bonus if multiple categories are present
    categories_present = sum(
        [
            1 if inj_markers else 0,
            1 if sec_markers else 0,
            1 if pii_markers else 0,
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
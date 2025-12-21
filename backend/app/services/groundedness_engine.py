"""
Simple deterministic groundedness engine for model outputs.

Contract (aligned with tests):
- Pydantic model Claim(text: str, evidence_ids: list[int] | None = None)
- Pydantic model GroundednessResult(claim: Claim, score: float, supported: bool, matched_evidence_ids: list[int])
- GroundednessEngine.score_output(model_output: str, evidence_texts: list[str]) -> list[GroundednessResult]

Implementation notes:
- Heuristic, deterministic scoring based on token overlap (Jaccard) with a substring shortcut.
- Evidence IDs are derived from input order (0-based indices) as we receive plain strings.
"""

from __future__ import annotations

import re
import string
from typing import List

# Pydantic v2 first, v1 fallback
try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # pragma: no cover
    from pydantic import BaseModel  # type: ignore

    def Field(*_args, **_kwargs):  # type: ignore
        return None


# -----------------------------
# Utilities
# -----------------------------

_PUNCT_TABLE = str.maketrans({k: " " for k in string.punctuation})


def _normalize(text: str) -> str:
    return " ".join(text.lower().translate(_PUNCT_TABLE).split())


def _tokens(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) >= 2]


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return (inter / union) if union else 0.0


def _sentences(text: str) -> List[str]:
    parts = re.split(r"[\.!?\n]+", text)
    return [p.strip() for p in parts if p and len(p.strip()) >= 5]


# -----------------------------
# Pydantic models
# -----------------------------

class Claim(BaseModel):
    text: str = Field(..., description="Extracted claim text (sentence)")
    evidence_ids: List[int] | None = Field(default=None, description="IDs of matching evidence (0-based indices)")


class GroundednessResult(BaseModel):
    claim: Claim
    score: float = Field(..., ge=0.0, le=1.0)
    supported: bool
    matched_evidence_ids: List[int] = Field(default_factory=list)


# -----------------------------
# Engine
# -----------------------------

class GroundednessEngine:
    """
    Compute groundedness of claims against evidence texts.

    Strategy:
    - Split model output into simple sentences (“claims”).
    - For each claim, compute a best-match score across evidence texts:
        - If claim is a substring of an evidence text (normalized), score = 1.0
        - Else, score = Jaccard(token_set(claim), token_set(evidence_text))
    - supported = score >= threshold
    """

    def __init__(self, threshold: float = 0.30) -> None:
        if not (0.0 <= float(threshold) <= 1.0):
            raise ValueError("threshold must be in [0.0, 1.0]")
        self.threshold = float(threshold)

    def score_output(self, model_output: str, evidence_texts: List[str]) -> List[GroundednessResult]:
        if not isinstance(model_output, str):
            raise TypeError("model_output must be a str")
        if not isinstance(evidence_texts, list):
            raise TypeError("evidence_texts must be a list[str]")

        evid_norm: List[str] = [_normalize(str(e or "")) for e in evidence_texts]
        evid_tokens: List[List[str]] = [_tokens(str(e or "")) for e in evidence_texts]

        results: List[GroundednessResult] = []
        for sent in _sentences(model_output):
            ctoks = _tokens(sent)
            if len(ctoks) < 3:
                # Very small claims are unlikely to be meaningful; score 0
                claim = Claim(text=sent)
                results.append(GroundednessResult(claim=claim, score=0.0, supported=False, matched_evidence_ids=[]))
                continue

            cnorm = " ".join(ctoks)
            best = 0.0
            matched_ids: List[int] = []

            for idx, (enorm, etoks) in enumerate(zip(evid_norm, evid_tokens)):
                if not enorm and not etoks:
                    continue
                # Substring shortcut (normalized)
                if cnorm and cnorm in enorm:
                    score = 1.0
                else:
                    score = _jaccard(ctoks, etoks)

                if score > 0.0:
                    matched_ids.append(idx)
                if score > best:
                    best = score

            supported = best >= self.threshold
            claim = Claim(text=sent, evidence_ids=matched_ids or None)
            results.append(
                GroundednessResult(
                    claim=claim,
                    score=float(best),
                    supported=bool(supported),
                    matched_evidence_ids=list(matched_ids),
                )
            )
        return results


__all__ = ["Claim", "GroundednessResult", "GroundednessEngine"]
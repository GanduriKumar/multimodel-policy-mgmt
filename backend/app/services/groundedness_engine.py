"""
Claim Extraction and Groundedness Engine.

This module provides two lightweight services:
 - ClaimExtraction: splits model output into simple "claims" (sentences/clauses)
 - GroundednessEngine: scores each claim against provided EvidenceBundles and
   determines whether the claim is supported by retrieved evidence.

Design goals
 - Zero external dependencies; fast, heuristic-based scoring
 - Friendly types and straightforward integration points
 - Safe defaults; production systems can swap with an LLM-based verifier

Typical usage
    extractor = ClaimExtraction()
    claims = extractor.extract_claims(output_text)

    engine = GroundednessEngine()
    result = engine.evaluate_groundedness(output_text, evidence_bundles)

Where evidence_bundles is a list of ORM objects (EvidenceBundle) or dict-like
objects with fields: {id, chunks: [str, ...]}.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Optional import for type hints; the engine works with dict-like bundles too
try:  # pragma: no cover - import guarded for loose coupling
    from app.models.evidence_bundle import EvidenceBundle  # noqa: F401
except Exception:  # pragma: no cover
    EvidenceBundle = Any  # type: ignore


# -----------------------------
# Utility helpers
# -----------------------------

_PUNCT_TABLE = str.maketrans({k: " " for k in string.punctuation})


def _normalize(text: str) -> str:
    return " ".join(text.lower().translate(_PUNCT_TABLE).split())


def _tokens(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) >= 2]


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return (inter / union) if union else 0.0


def _sentences(text: str) -> List[str]:
    # Naive sentence split on . ! ? and newlines; keeps simple clauses
    parts = re.split(r"[\.!?\n]+", text)
    # Trim and filter tiny/empty parts
    return [p.strip() for p in parts if p and len(p.strip()) >= 5]


# -----------------------------
# Data structures
# -----------------------------

@dataclass
class Claim:
    id: int
    text: str
    tokens: List[str] = field(default_factory=list)


@dataclass
class Match:
    bundle_id: Optional[int]
    chunk_index: int
    score: float


@dataclass
class ClaimAssessment:
    claim_id: int
    text: str
    supported: bool
    score: float
    matches: List[Match] = field(default_factory=list)


@dataclass
class GroundednessReport:
    output_text: str
    overall_score: float
    threshold: float
    claims: List[ClaimAssessment]


# -----------------------------
# Claim extraction
# -----------------------------

class ClaimExtraction:
    """Heuristic claim extractor using sentence segmentation and tokenization."""

    def __init__(self, min_len: int = 12) -> None:
        self.min_len = min_len

    def extract_claims(self, output_text: str) -> List[Claim]:
        claims: List[Claim] = []
        sid = 1
        for sent in _sentences(output_text):
            if len(sent) < self.min_len:
                continue
            toks = _tokens(sent)
            if len(toks) < 3:
                continue
            claims.append(Claim(id=sid, text=sent, tokens=toks))
            sid += 1
        return claims


# -----------------------------
# Groundedness scoring
# -----------------------------

class GroundednessEngine:
    """Compute groundedness of claims w.r.t. EvidenceBundles.

    Strategy
    - For each claim, compute maximum similarity against all evidence chunks.
    - Similarity uses token Jaccard with a fast substring check
      (substring -> score=1.0).
    - A claim is supported if best_score >= threshold.
    """

    def __init__(self, threshold: float = 0.30) -> None:
        self.threshold = float(threshold)

    # Public API
    def evaluate_groundedness(
        self,
        output_text: str,
        bundles: Sequence[EvidenceBundle | Dict[str, Any]],
    ) -> GroundednessReport:
        extractor = ClaimExtraction()
        claims = extractor.extract_claims(output_text)
        assessments: List[ClaimAssessment] = []

        for claim in claims:
            best_score = 0.0
            matches: List[Match] = []
            for b_idx, (bid, chunks) in enumerate(self._iter_bundle_chunks(bundles)):
                for ci, ch_text in enumerate(chunks):
                    score = self._chunk_similarity(claim.tokens, ch_text)
                    if score > 0:
                        matches.append(Match(bundle_id=bid, chunk_index=ci, score=score))
                    if score > best_score:
                        best_score = score
            supported = best_score >= self.threshold
            # Keep top-k matches (e.g., 5) for brevity
            matches.sort(key=lambda m: m.score, reverse=True)
            assessments.append(
                ClaimAssessment(
                    claim_id=claim.id,
                    text=claim.text,
                    supported=supported,
                    score=best_score,
                    matches=matches[:5],
                )
            )

        overall = self._aggregate_overall(assessments)
        return GroundednessReport(
            output_text=output_text,
            overall_score=overall,
            threshold=self.threshold,
            claims=assessments,
        )

    # Internals
    def _iter_bundle_chunks(
        self, bundles: Sequence[EvidenceBundle | Dict[str, Any]]
    ) -> Iterable[Tuple[Optional[int], List[str]]]:
        for b in bundles:
            try:
                # ORM-like
                bid = getattr(b, "id", None)
                chunks = list(getattr(b, "chunks", []) or [])
            except Exception:
                bid = None
                chunks = []
            # Dict-like override
            if isinstance(b, dict):
                bid = b.get("id", bid)
                chunks = list(b.get("chunks", chunks) or [])
            # Ensure string chunks
            chunks = [str(c) for c in chunks if isinstance(c, (str, bytes))]
            yield bid, chunks

    def _chunk_similarity(self, claim_tokens: List[str], chunk_text: str) -> float:
        if not chunk_text:
            return 0.0
        norm_chunk = _normalize(chunk_text)
        # Quick substring: if claim string appears in chunk, mark as 1.0
        claim_str = " ".join(claim_tokens)
        if claim_str and claim_str in norm_chunk:
            return 1.0
        return _jaccard(claim_tokens, _tokens(norm_chunk))

    def _aggregate_overall(self, assessments: List[ClaimAssessment]) -> float:
        if not assessments:
            return 0.0
        # Simple average of individual scores
        return sum(a.score for a in assessments) / max(1, len(assessments))


__all__ = [
    "ClaimExtraction",
    "GroundednessEngine",
    "Claim",
    "ClaimAssessment",
    "GroundednessReport",
]

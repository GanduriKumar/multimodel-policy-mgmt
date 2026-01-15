"""
Pydantic schema for policy documents used by the risk/policy engine.

Fields:
- blocked_terms: Terms that are not allowed to appear in content.
- allowed_sources: Whitelisted sources (domains, IDs, etc.).
- required_evidence_types: Evidence categories required to substantiate claims.
- pii_rules: Arbitrary configuration for PII handling rules.
- risk_threshold: Numeric threshold (0-100) at which content is considered risky.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["PolicyDoc"]


class PolicyDoc(BaseModel):
    # List of terms that are blocked outright
    blocked_terms: list[str] = Field(
        ...,
        description="List of terms that should be blocked.",
    )

    # List of allowed/approved sources (e.g., domains or identifiers)
    allowed_sources: list[str] = Field(
        ...,
        description="Whitelisted sources (domains, identifiers, etc.).",
    )

    # Evidence configuration
    # required_evidence_types retained for backward compatibility but is presence-only in engine
    required_evidence_types: list[str] = Field(
        ...,
        description="Deprecated granular types; engine treats any source as satisfying evidence.",
    )
    require_any_evidence: bool = Field(
        default=False,
        description="If true, require at least one source/evidence to be provided.",
    )

    # Configuration dict for PII handling (e.g., {'mask_emails': True, 'allow_phone': False})
    pii_rules: dict = Field(
        ...,
        description="Configuration dictionary for PII handling rules.",
    )

    # Risk score threshold from 0 to 100
    risk_threshold: int = Field(
        ...,
        ge=0,
        le=100,
        description="Risk score threshold (0-100) beyond which content is blocked or escalated.",
    )

    # Conservative mode: if True, any risk indicators (prompt injection, PII-like, secret-like, etc.)
    # will cause denial even when the risk score is below threshold. This opts for "benefit of doubt" -> deny.
    conservative_mode: bool = Field(
        default=True,
        description="When enabled, any risk indicators trigger denial even if risk score is below threshold.",
    )
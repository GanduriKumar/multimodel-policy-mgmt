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

from typing import Optional
from pydantic import BaseModel, Field

__all__ = ["PolicyDoc"]


class PolicyDoc(BaseModel):
    # Metadata fields
    id: Optional[int] = Field(
        default=None,
        description="Policy ID (optional, for reporting/tracking)",
    )
    
    name: Optional[str] = Field(
        default=None,
        description="Policy name (optional, for reporting/tracking)",
    )
    
    version: Optional[int] = Field(
        default=None,
        description="Policy version (optional, for reporting/tracking)",
    )
    
    # List of terms that are blocked outright
    blocked_terms: list[str] = Field(
        default_factory=list,
        description="List of terms that should be blocked.",
    )

    # List of allowed/approved sources (e.g., domains or identifiers)
    allowed_sources: list[str] = Field(
        default_factory=list,
        description="Whitelisted sources (domains, identifiers, etc.).",
    )

    # Evidence configuration
    # required_evidence_types retained for backward compatibility but is presence-only in engine
    required_evidence_types: list[str] = Field(
        default_factory=list,
        description="Deprecated granular types; engine treats any source as satisfying evidence.",
    )
    require_any_evidence: bool = Field(
        default=False,
        description="If true, require at least one source/evidence to be provided.",
    )

    # Configuration dict for PII handling (e.g., {'mask_emails': True, 'allow_phone': False})
    pii_rules: dict = Field(
        default_factory=dict,
        description="Configuration dictionary for PII handling rules.",
    )

    # Intent rules for local intent-based enforcement.
    # Structure:
    #   intent_rules: {
    #       "deny": ["weapon_instruction", "incite_violence"],
    #       "thresholds": { "weapon_instruction": 0.7, "incite_violence": 0.6 }
    #   }
    # If a detected intent label appears in 'deny' and its score >= threshold (default 0.5), the request is denied.
    intent_rules: dict = Field(
        default_factory=dict,
        description="Intent-based policy: labels to deny and per-label thresholds. Keys: 'deny' (list[str]), 'thresholds' (dict[label->float]).",
    )

    # Risk score threshold from 0 to 100
    risk_threshold: int | float = Field(
        default=50,
        ge=0,
        le=100,
        description="Risk score threshold (0-100) beyond which content is blocked or escalated.",
    )
    
    # Rules list (for compliance frameworks)
    rules: list[str] = Field(
        default_factory=list,
        description="List of policy rules (for compliance reporting)",
    )
    
    # Outputs configuration (for compliance frameworks)
    outputs: dict = Field(
        default_factory=dict,
        description="Outputs configuration (for compliance reporting)",
    )

    # Conservative mode: if True, any risk indicators (prompt injection, PII-like, secret-like, etc.)
    # will cause denial even when the risk score is below threshold. This opts for "benefit of doubt" -> deny.
    conservative_mode: bool = Field(
        default=True,
        description="When enabled, any risk indicators trigger denial even if risk score is below threshold.",
    )

    # ===============================
    # REGULATORY COMPLIANCE FIELDS
    # ===============================

    # Regulatory frameworks this policy adheres to
    regulatory_frameworks: list[str] = Field(
        default_factory=list,
        description="Selected regulatory frameworks (e.g., ['eu_ai_act_high_risk', 'nist_ai_rmf', 'nist_privacy'])",
    )

    # EU AI Act configuration for high-risk AI systems
    eu_ai_act_config: dict = Field(
        default_factory=dict,
        description="EU AI Act Articles 9-15 compliance configuration",
    )

    # NIST AI Risk Management Framework configuration
    nist_ai_rmf_config: dict = Field(
        default_factory=dict,
        description="NIST AI RMF four core functions (Govern, Map, Measure, Manage) configuration",
    )

    # NIST Privacy Framework configuration
    nist_privacy_config: dict = Field(
        default_factory=dict,
        description="NIST Privacy Framework data lifecycle configuration",
    )

    # Compliance metadata and mappings
    compliance_metadata: dict = Field(
        default_factory=dict,
        description="Compliance metadata including article/control mappings, validation status, auto-generated rule mappings",
    )

    # Human oversight requirement flag (auto-set based on compliance configs)
    requires_human_review: bool = Field(
        default=False,
        description="Whether this policy requires human review for certain decisions (auto-set from compliance config)",
    )

    # Current compliance validation status
    compliance_status: str = Field(
        default="draft",
        description="Compliance validation status: 'draft', 'validated', 'non_compliant'",
    )

    # Human oversight configuration
    human_oversight_config: dict = Field(
        default_factory=dict,
        description="Configuration for human oversight triggers, SLA, and escalation procedures",
    )
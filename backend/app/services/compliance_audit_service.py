"""
Compliance-aware audit logging service.

This service helps construct enhanced audit trails with complete reasoning chains,
regulatory mappings, and policy snapshots for compliance reporting.
"""

from typing import Optional, Dict, List, Any
import logging
from datetime import datetime

from app.schemas.policy_format import PolicyDoc
from app.models.policy_version import PolicyVersion


class ComplianceAuditService:
    """
    Service for creating compliance-rich audit log entries.
    
    Helps construct:
    - Complete reasoning chains showing which rules triggered and why
    - Regulatory mappings to specific articles/controls
    - Policy version snapshots for auditability
    - Detailed engine scores for transparency
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def build_reasoning_chain(
        self,
        *,
        policy_doc: Optional[PolicyDoc] = None,
        rules_evaluated: Optional[List[Dict[str, Any]]] = None,
        policy_checks: Optional[List[Dict[str, Any]]] = None,
        intent_classifications: Optional[List[Dict[str, Any]]] = None,
        risk_factors: Optional[List[Dict[str, Any]]] = None,
        decision_path: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build a complete reasoning chain for a decision.
        
        Args:
            policy_doc: PolicyDoc that was evaluated
            rules_evaluated: List of rules evaluated with their results
            policy_checks: List of policy checks performed (blocked_terms, PII, etc.)
            intent_classifications: Intent classification results
            risk_factors: Risk factors that contributed to risk score
            decision_path: Ordered list of decision steps taken
            
        Returns:
            Complete reasoning chain dict
        """
        chain = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision_path": decision_path or [],
        }
        
        if rules_evaluated:
            chain["rules_evaluated"] = rules_evaluated
            # Add summary stats
            triggered = [r for r in rules_evaluated if r.get("triggered")]
            chain["rules_summary"] = {
                "total_rules": len(rules_evaluated),
                "triggered_rules": len(triggered),
                "triggered_rule_ids": [r.get("rule_id") for r in triggered]
            }
        
        if policy_checks:
            chain["policy_checks"] = policy_checks
            # Add summary
            failed_checks = [c for c in policy_checks if not c.get("result")]
            chain["policy_checks_summary"] = {
                "total_checks": len(policy_checks),
                "failed_checks": len(failed_checks),
                "failed_check_types": [c.get("check") for c in failed_checks]
            }
        
        if intent_classifications:
            chain["intent_classifications"] = intent_classifications
            # Add summary
            denied_intents = [i for i in intent_classifications 
                             if i.get("score", 0) >= i.get("threshold", 1.0)]
            chain["intent_summary"] = {
                "total_intents": len(intent_classifications),
                "denied_intents": len(denied_intents),
                "denied_intent_names": [i.get("intent") for i in denied_intents]
            }
        
        if risk_factors:
            chain["risk_factors"] = risk_factors
            total_risk = sum(f.get("contribution", 0) for f in risk_factors)
            chain["risk_summary"] = {
                "total_factors": len(risk_factors),
                "total_risk_contribution": total_risk,
                "top_risk_factors": sorted(
                    risk_factors,
                    key=lambda x: x.get("contribution", 0),
                    reverse=True
                )[:3]
            }
        
        # Add policy context if available
        if policy_doc:
            chain["policy_context"] = {
                "regulatory_frameworks": policy_doc.regulatory_frameworks,
                "compliance_status": policy_doc.compliance_status,
                "requires_human_review": policy_doc.requires_human_review,
                "risk_threshold": policy_doc.risk_threshold,
                "conservative_mode": policy_doc.conservative_mode
            }
        
        return chain
    
    def extract_regulatory_mappings(
        self,
        policy_doc: PolicyDoc,
        triggered_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, List[str]]:
        """
        Extract regulatory article/control mappings from policy and triggered rules.
        
        Args:
            policy_doc: PolicyDoc with regulatory configurations
            triggered_rules: List of rules that triggered (with enforcement_mapping info)
            
        Returns:
            Dict mapping framework IDs to lists of articles/controls
        """
        mappings: Dict[str, List[str]] = {}
        
        # Extract from compliance metadata if available
        if policy_doc.compliance_metadata:
            auto_mappings = policy_doc.compliance_metadata.get("regulatory_mappings", {})
            for framework_id, articles in auto_mappings.items():
                if framework_id not in mappings:
                    mappings[framework_id] = []
                if isinstance(articles, list):
                    mappings[framework_id].extend(articles)
        
        # Extract from regulatory framework configs
        for framework_id in policy_doc.regulatory_frameworks:
            if framework_id not in mappings:
                mappings[framework_id] = []
            
            # For EU AI Act, map based on active articles
            if framework_id == "eu_ai_act_high_risk" and policy_doc.eu_ai_act_config:
                for article_id in policy_doc.eu_ai_act_config.keys():
                    # Convert article_9 -> Article 9
                    article_num = article_id.replace("article_", "")
                    mappings[framework_id].append(f"Article {article_num}")
            
            # For NIST AI RMF, map based on functions
            elif framework_id == "nist_ai_rmf" and policy_doc.nist_ai_rmf_config:
                for function_id in policy_doc.nist_ai_rmf_config.keys():
                    function_name = function_id.upper()
                    mappings[framework_id].append(function_name)
            
            # For NIST Privacy, map based on functions
            elif framework_id == "nist_privacy" and policy_doc.nist_privacy_config:
                for function_id in policy_doc.nist_privacy_config.keys():
                    function_name = function_id.upper().replace("_", "-")
                    mappings[framework_id].append(function_name)
        
        # Add specific rule-level mappings if available
        if triggered_rules:
            for rule in triggered_rules:
                enforcement_mapping = rule.get("enforcement_mapping", {})
                regulatory_ref = enforcement_mapping.get("regulatory_reference")
                if regulatory_ref:
                    # Parse regulatory_reference to extract framework and article
                    # Example: "EU AI Act Article 9(2)(a)" or "NIST AI RMF GOVERN-1.2"
                    for framework_id in policy_doc.regulatory_frameworks:
                        if framework_id in regulatory_ref or framework_id.replace("_", " ").upper() in regulatory_ref.upper():
                            if framework_id not in mappings:
                                mappings[framework_id] = []
                            if regulatory_ref not in mappings[framework_id]:
                                mappings[framework_id].append(regulatory_ref)
        
        # Deduplicate
        for framework_id in mappings:
            mappings[framework_id] = list(set(mappings[framework_id]))
        
        return mappings
    
    def create_policy_version_snapshot(
        self,
        policy_version: Optional[PolicyVersion] = None,
        policy_doc: Optional[PolicyDoc] = None
    ) -> Dict[str, Any]:
        """
        Create a complete snapshot of policy version for auditability.
        
        This ensures we can recreate exact decision context even if policy changes.
        
        Args:
            policy_version: PolicyVersion database model
            policy_doc: PolicyDoc schema
            
        Returns:
            Complete policy snapshot dict
        """
        snapshot = {
            "snapshot_timestamp": datetime.utcnow().isoformat(),
        }
        
        if policy_version:
            snapshot["policy_version_id"] = policy_version.id
            snapshot["policy_id"] = policy_version.policy_id
            snapshot["version_number"] = policy_version.version
            snapshot["is_active"] = policy_version.is_active
            snapshot["created_at"] = policy_version.created_at.isoformat() if policy_version.created_at else None
        
        if policy_doc:
            snapshot["policy_doc"] = {
                "blocked_terms": policy_doc.blocked_terms,
                "allowed_sources": policy_doc.allowed_sources,
                "required_evidence_types": policy_doc.required_evidence_types,
                "require_any_evidence": policy_doc.require_any_evidence,
                "pii_rules": policy_doc.pii_rules,
                "intent_rules": policy_doc.intent_rules,
                "risk_threshold": policy_doc.risk_threshold,
                "conservative_mode": policy_doc.conservative_mode,
                # Compliance fields
                "regulatory_frameworks": policy_doc.regulatory_frameworks,
                "compliance_status": policy_doc.compliance_status,
                "requires_human_review": policy_doc.requires_human_review,
                # Store compliance configs
                "eu_ai_act_config": policy_doc.eu_ai_act_config,
                "nist_ai_rmf_config": policy_doc.nist_ai_rmf_config,
                "nist_privacy_config": policy_doc.nist_privacy_config,
                "compliance_metadata": policy_doc.compliance_metadata,
                "human_oversight_config": policy_doc.human_oversight_config,
            }
        
        return snapshot
    
    def aggregate_engine_scores(
        self,
        *,
        risk_engine_score: Optional[float] = None,
        pii_detection_score: Optional[float] = None,
        intent_classifier_scores: Optional[Dict[str, float]] = None,
        evidence_quality_score: Optional[float] = None,
        groundedness_score: Optional[float] = None,
        safety_score: Optional[float] = None,
        custom_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate scores from various engines into a structured dict.
        
        Args:
            risk_engine_score: Overall risk score (0-100)
            pii_detection_score: PII detection confidence
            intent_classifier_scores: Dict of intent -> confidence scores
            evidence_quality_score: Evidence quality/groundedness score
            groundedness_score: RAG groundedness score
            safety_score: Response safety score
            custom_scores: Any additional custom scores
            
        Returns:
            Aggregated engine scores dict
        """
        scores = {}
        
        if risk_engine_score is not None:
            scores["risk_engine_score"] = float(risk_engine_score)
        
        if pii_detection_score is not None:
            scores["pii_detection_score"] = float(pii_detection_score)
        
        if intent_classifier_scores:
            scores["intent_classifier_scores"] = {
                intent: float(score) for intent, score in intent_classifier_scores.items()
            }
        
        if evidence_quality_score is not None:
            scores["evidence_quality_score"] = float(evidence_quality_score)
        
        if groundedness_score is not None:
            scores["groundedness_score"] = float(groundedness_score)
        
        if safety_score is not None:
            scores["safety_score"] = float(safety_score)
        
        if custom_scores:
            scores["custom_scores"] = {
                key: float(value) for key, value in custom_scores.items()
            }
        
        # Calculate overall confidence if multiple scores available
        all_scores = []
        if risk_engine_score is not None:
            all_scores.append(risk_engine_score)
        if pii_detection_score is not None:
            all_scores.append(pii_detection_score)
        if evidence_quality_score is not None:
            all_scores.append(evidence_quality_score)
        if groundedness_score is not None:
            all_scores.append(groundedness_score)
        if safety_score is not None:
            all_scores.append(safety_score)
        
        if all_scores:
            scores["overall_confidence"] = sum(all_scores) / len(all_scores)
            scores["score_count"] = len(all_scores)
        
        return scores
    
    def create_compliance_audit_data(
        self,
        *,
        policy_version: Optional[PolicyVersion] = None,
        policy_doc: Optional[PolicyDoc] = None,
        rules_evaluated: Optional[List[Dict[str, Any]]] = None,
        policy_checks: Optional[List[Dict[str, Any]]] = None,
        intent_classifications: Optional[List[Dict[str, Any]]] = None,
        risk_factors: Optional[List[Dict[str, Any]]] = None,
        decision_path: Optional[List[str]] = None,
        engine_scores_kwargs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convenience method to create all compliance audit data at once.
        
        Returns dict with keys: reasoning_chain, compliance_frameworks,
        regulatory_mappings, engine_scores, policy_version_snapshot
        """
        # Build reasoning chain
        reasoning_chain = self.build_reasoning_chain(
            policy_doc=policy_doc,
            rules_evaluated=rules_evaluated,
            policy_checks=policy_checks,
            intent_classifications=intent_classifications,
            risk_factors=risk_factors,
            decision_path=decision_path
        )
        
        # Extract compliance frameworks
        compliance_frameworks = policy_doc.regulatory_frameworks if policy_doc else []
        
        # Extract regulatory mappings
        regulatory_mappings = {}
        if policy_doc:
            triggered_rules = [r for r in (rules_evaluated or []) if r.get("triggered")]
            regulatory_mappings = self.extract_regulatory_mappings(policy_doc, triggered_rules)
        
        # Aggregate engine scores
        engine_scores = self.aggregate_engine_scores(**(engine_scores_kwargs or {}))
        
        # Create policy snapshot
        policy_version_snapshot = self.create_policy_version_snapshot(
            policy_version=policy_version,
            policy_doc=policy_doc
        )
        
        return {
            "reasoning_chain": reasoning_chain,
            "compliance_frameworks": compliance_frameworks,
            "regulatory_mappings": regulatory_mappings,
            "engine_scores": engine_scores,
            "policy_version_snapshot": policy_version_snapshot
        }

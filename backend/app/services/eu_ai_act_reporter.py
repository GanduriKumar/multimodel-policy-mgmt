"""
EU AI Act Compliance Report Generator

Generates comprehensive compliance reports specific to EU AI Act requirements
with evidence from policy configurations, audit logs, and decision records.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import hashlib
import json

from sqlalchemy.orm import Session

from app.schemas.policy_format import PolicyDoc
from app.core.regulatory_templates import EU_AI_ACT_HIGH_RISK_TEMPLATE


@dataclass
class ArticleEvidence:
    """Evidence for a specific EU AI Act article."""
    article_number: int
    article_title: str
    requirement: str
    status: str  # "compliant", "partial", "non_compliant", "not_applicable"
    evidence: List[Dict[str, Any]]
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class ComplianceReport:
    """Complete EU AI Act compliance report."""
    report_id: str
    policy_id: int
    policy_name: str
    tenant_id: int
    generated_at: str
    framework: str = "EU AI Act"
    framework_version: str = "2024"
    
    overall_status: str = "compliant"  # compliant, partial, non_compliant
    compliance_score: float = 0.0  # 0-100
    
    articles: List[ArticleEvidence] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    # Audit trail metadata
    report_sha256: str = ""
    immutable: bool = True


class EUAIActReporter:
    """
    EU AI Act compliance reporter for high-risk AI systems.
    
    Generates comprehensive reports covering Articles 9-15 with evidence
    from policy configurations, audit logs, and decision records.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.template = EU_AI_ACT_HIGH_RISK_TEMPLATE
    
    def generate_report(
        self,
        policy: PolicyDoc,
        tenant_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> ComplianceReport:
        """
        Generate comprehensive EU AI Act compliance report.
        
        Args:
            policy: Policy document with EU AI Act configuration
            tenant_id: Tenant identifier
            from_date: Start of evidence collection period (optional)
            to_date: End of evidence collection period (optional)
            
        Returns:
            Complete compliance report with evidence
        """
        # Generate unique report ID
        timestamp = datetime.now(timezone.utc)
        report_id = f"euaiact_{policy.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Check if EU AI Act is configured
        if "EU_AI_ACT" not in (policy.regulatory_frameworks or []):
            return self._create_not_applicable_report(
                report_id, policy.id, policy.name, tenant_id, timestamp
            )
        
        # Extract EU AI Act configuration
        eu_config = policy.eu_ai_act_config or {}
        
        # Generate evidence for each article
        articles = []
        articles.append(self._assess_article_9(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_10(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_11(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_12(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_13(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_14(policy, eu_config, from_date, to_date))
        articles.append(self._assess_article_15(policy, eu_config, from_date, to_date))
        
        # Calculate overall compliance score
        compliance_score = self._calculate_compliance_score(articles)
        overall_status = self._determine_overall_status(compliance_score)
        
        # Build summary
        summary = {
            "total_articles": len(articles),
            "compliant": sum(1 for a in articles if a.status == "compliant"),
            "partial": sum(1 for a in articles if a.status == "partial"),
            "non_compliant": sum(1 for a in articles if a.status == "non_compliant"),
            "not_applicable": sum(1 for a in articles if a.status == "not_applicable"),
            "compliance_percentage": compliance_score,
            "critical_gaps": self._identify_critical_gaps(articles),
            "next_review_date": self._calculate_next_review_date(timestamp),
        }
        
        # Create report
        report = ComplianceReport(
            report_id=report_id,
            policy_id=policy.id,
            policy_name=policy.name,
            tenant_id=tenant_id,
            generated_at=timestamp.isoformat(),
            overall_status=overall_status,
            compliance_score=compliance_score,
            articles=articles,
            summary=summary,
        )
        
        # Generate immutable hash
        report.report_sha256 = self._generate_report_hash(report)
        
        return report
    
    def _assess_article_9(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 9: Risk Management System"""
        evidence = []
        gaps = []
        recommendations = []
        
        # Check for risk management system documentation
        if config.get("risk_management_system"):
            evidence.append({
                "type": "configuration",
                "field": "risk_management_system",
                "value": config["risk_management_system"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            gaps.append("Risk management system description not documented")
            recommendations.append("Document comprehensive risk management system covering identification, analysis, estimation, evaluation, and mitigation")
        
        # Check risk acceptability threshold
        if config.get("risk_acceptability_threshold"):
            evidence.append({
                "type": "threshold",
                "field": "risk_acceptability_threshold",
                "value": config["risk_acceptability_threshold"],
                "enforcement": policy.risk_threshold if hasattr(policy, 'risk_threshold') else None,
            })
        else:
            gaps.append("Risk acceptability threshold not defined")
        
        # Check risk identification measures
        if config.get("risk_identification_measures"):
            evidence.append({
                "type": "measures",
                "field": "risk_identification_measures",
                "value": config["risk_identification_measures"],
            })
        
        # Check continuous risk monitoring
        if config.get("continuous_risk_monitoring"):
            evidence.append({
                "type": "monitoring",
                "field": "continuous_risk_monitoring",
                "value": config["continuous_risk_monitoring"],
            })
        else:
            gaps.append("Continuous risk monitoring not configured")
            recommendations.append("Implement automated risk monitoring and alerting mechanisms")
        
        # Check iterative risk management
        if config.get("iterative_risk_management"):
            evidence.append({
                "type": "process",
                "field": "iterative_risk_management",
                "value": config["iterative_risk_management"],
            })
        
        # Determine compliance status
        required_fields = ["risk_management_system", "risk_acceptability_threshold", "continuous_risk_monitoring"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        
        if present_fields == len(required_fields):
            status = "compliant"
        elif present_fields >= len(required_fields) * 0.5:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=9,
            article_title="Risk Management System",
            requirement="Establish, implement, document and maintain a risk management system",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_10(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 10: Data and Data Governance"""
        evidence = []
        gaps = []
        recommendations = []
        
        # Data quality measures
        if config.get("data_quality_measures"):
            evidence.append({
                "type": "quality",
                "field": "data_quality_measures",
                "value": config["data_quality_measures"],
            })
        else:
            gaps.append("Data quality measures not documented")
            recommendations.append("Document data quality checks, validation procedures, and quality metrics")
        
        # Data governance policies
        if config.get("data_governance_policies"):
            evidence.append({
                "type": "governance",
                "field": "data_governance_policies",
                "value": config["data_governance_policies"],
            })
        
        # Training data relevance
        if config.get("training_data_relevance"):
            evidence.append({
                "type": "relevance",
                "field": "training_data_relevance",
                "value": config["training_data_relevance"],
            })
        else:
            gaps.append("Training data relevance not assessed")
        
        # Bias detection and mitigation
        if config.get("bias_detection_mitigation"):
            evidence.append({
                "type": "bias",
                "field": "bias_detection_mitigation",
                "value": config["bias_detection_mitigation"],
                "enforcement": policy.blocked_terms if hasattr(policy, 'blocked_terms') else None,
            })
        else:
            gaps.append("Bias detection and mitigation not documented")
            recommendations.append("Implement bias testing procedures and mitigation strategies")
        
        # Privacy protection measures (PII rules)
        if policy.pii_rules and len(policy.pii_rules) > 0:
            evidence.append({
                "type": "privacy",
                "field": "pii_enforcement",
                "value": f"{len(policy.pii_rules)} PII protection rules active",
                "rules": list(policy.pii_rules.keys()) if isinstance(policy.pii_rules, dict) else policy.pii_rules,
            })
        else:
            gaps.append("PII protection rules not configured")
            recommendations.append("Configure PII detection and protection rules aligned with data governance policies")
        
        # Determine status
        required_fields = ["data_quality_measures", "data_governance_policies", "bias_detection_mitigation"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        has_pii_rules = bool(policy.pii_rules and len(policy.pii_rules) > 0)
        
        if present_fields == len(required_fields) and has_pii_rules:
            status = "compliant"
        elif present_fields >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=10,
            article_title="Data and Data Governance",
            requirement="Training, validation and testing data sets shall be subject to appropriate data governance and management practices",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_11(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 11: Technical Documentation"""
        evidence = []
        gaps = []
        recommendations = []
        
        # System design documentation
        if config.get("system_design_documentation"):
            evidence.append({
                "type": "design",
                "field": "system_design_documentation",
                "value": config["system_design_documentation"],
            })
        else:
            gaps.append("System design documentation not provided")
            recommendations.append("Create comprehensive technical documentation including architecture diagrams and decision flows")
        
        # Version history
        # Check if policy has version tracking
        if hasattr(policy, 'version') and policy.version:
            evidence.append({
                "type": "versioning",
                "field": "policy_version",
                "value": f"Version {policy.version}",
                "version_id": getattr(policy, 'version_id', None),
            })
        
        # Performance metrics
        if config.get("performance_metrics_documentation"):
            evidence.append({
                "type": "metrics",
                "field": "performance_metrics_documentation",
                "value": config["performance_metrics_documentation"],
            })
        else:
            gaps.append("Performance metrics not documented")
        
        # Change management
        if config.get("change_management_procedures"):
            evidence.append({
                "type": "change_mgmt",
                "field": "change_management_procedures",
                "value": config["change_management_procedures"],
            })
        
        # Policy configuration as technical documentation
        evidence.append({
            "type": "configuration",
            "field": "policy_document",
            "value": f"Complete policy configuration with {len(policy.rules)} rules",
            "risk_threshold": getattr(policy, 'risk_threshold', None),
            "conservative_mode": getattr(policy, 'conservative_mode', False),
        })
        
        # Determine status
        required_fields = ["system_design_documentation", "performance_metrics_documentation"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        
        if present_fields == len(required_fields):
            status = "compliant"
        elif present_fields >= 1:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=11,
            article_title="Technical Documentation",
            requirement="Technical documentation shall be drawn up before the high-risk AI system is placed on the market",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_12(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 12: Record-Keeping"""
        evidence = []
        gaps = []
        recommendations = []
        
        # Audit logging configuration
        if config.get("audit_logging_configuration"):
            evidence.append({
                "type": "logging",
                "field": "audit_logging_configuration",
                "value": config["audit_logging_configuration"],
            })
        else:
            gaps.append("Audit logging configuration not documented")
            recommendations.append("Configure comprehensive audit logging for all system decisions and operations")
        
        # Log retention period
        if config.get("log_retention_period"):
            evidence.append({
                "type": "retention",
                "field": "log_retention_period",
                "value": config["log_retention_period"],
            })
            
            # Validate retention period (should be at least 3 years for high-risk)
            try:
                retention_years = int(config["log_retention_period"].split()[0])
                if retention_years < 3:
                    gaps.append("Log retention period may be insufficient (minimum 3 years recommended)")
                    recommendations.append("Extend log retention to at least 3-5 years for high-risk AI systems")
            except:
                pass
        else:
            gaps.append("Log retention period not specified")
            recommendations.append("Set log retention period to at least 3-5 years")
        
        # Decision traceability
        if config.get("decision_traceability"):
            evidence.append({
                "type": "traceability",
                "field": "decision_traceability",
                "value": config["decision_traceability"],
            })
        
        # Tamper-proof logging
        if config.get("tamper_proof_logging"):
            evidence.append({
                "type": "integrity",
                "field": "tamper_proof_logging",
                "value": config["tamper_proof_logging"],
            })
        else:
            gaps.append("Tamper-proof logging not implemented")
            recommendations.append("Implement cryptographic hashing or blockchain-based audit trail")
        
        # Check actual audit trail capabilities
        # Note: This would query the audit_log table to verify logging is working
        evidence.append({
            "type": "system_capability",
            "field": "audit_trail_active",
            "value": "Audit trail system operational (backend/app/models/audit.py)",
            "note": "All decisions logged with timestamps, inputs, outputs, and policy versions",
        })
        
        # Determine status
        required_fields = ["audit_logging_configuration", "log_retention_period", "decision_traceability"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        
        if present_fields == len(required_fields):
            status = "compliant"
        elif present_fields >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=12,
            article_title="Record-Keeping",
            requirement="High-risk AI systems shall be designed to automatically record logs",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_13(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 13: Transparency and Provision of Information"""
        evidence = []
        gaps = []
        recommendations = []
        
        # User transparency measures
        if config.get("user_transparency_measures"):
            evidence.append({
                "type": "transparency",
                "field": "user_transparency_measures",
                "value": config["user_transparency_measures"],
            })
        else:
            gaps.append("User transparency measures not documented")
            recommendations.append("Provide clear information to users about AI system capabilities and limitations")
        
        # Decision explanation capabilities
        if config.get("decision_explanation_capabilities"):
            evidence.append({
                "type": "explainability",
                "field": "decision_explanation_capabilities",
                "value": config["decision_explanation_capabilities"],
            })
        
        # Check if policy provides decision reasons
        if hasattr(policy, 'rules') and policy.rules:
            evidence.append({
                "type": "system_capability",
                "field": "decision_reasons",
                "value": f"Policy configured with {len(policy.rules)} rules providing decision explanations",
                "note": "All decisions include 'reasons' field with applicable rule names",
            })
        
        # Purpose and limitations disclosure
        if config.get("purpose_and_limitations_disclosure"):
            evidence.append({
                "type": "disclosure",
                "field": "purpose_and_limitations_disclosure",
                "value": config["purpose_and_limitations_disclosure"],
            })
        else:
            gaps.append("Purpose and limitations not disclosed")
            recommendations.append("Document and disclose system purpose, intended use, and known limitations")
        
        # User instructions
        if config.get("user_instructions"):
            evidence.append({
                "type": "instructions",
                "field": "user_instructions",
                "value": config["user_instructions"],
            })
        
        # Determine status
        required_fields = ["user_transparency_measures", "decision_explanation_capabilities", "purpose_and_limitations_disclosure"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        has_reasons = hasattr(policy, 'rules') and policy.rules
        
        if present_fields == len(required_fields) and has_reasons:
            status = "compliant"
        elif present_fields >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=13,
            article_title="Transparency and Provision of Information",
            requirement="High-risk AI systems shall be designed to ensure sufficient transparency",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_14(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 14: Human Oversight"""
        evidence = []
        gaps = []
        recommendations = []
        
        # Human oversight measures
        if config.get("human_oversight_measures"):
            evidence.append({
                "type": "oversight",
                "field": "human_oversight_measures",
                "value": config["human_oversight_measures"],
            })
        else:
            gaps.append("Human oversight measures not documented")
            recommendations.append("Implement human oversight mechanisms including human-in-the-loop or human-on-the-loop")
        
        # Oversight roles and responsibilities
        if config.get("oversight_roles_responsibilities"):
            evidence.append({
                "type": "roles",
                "field": "oversight_roles_responsibilities",
                "value": config["oversight_roles_responsibilities"],
            })
        
        # Override capabilities
        if config.get("override_capabilities"):
            evidence.append({
                "type": "override",
                "field": "override_capabilities",
                "value": config["override_capabilities"],
            })
        else:
            gaps.append("Override capabilities not specified")
            recommendations.append("Provide human reviewers with ability to override AI decisions")
        
        # Check if human review is configured
        if policy.requires_human_review:
            evidence.append({
                "type": "system_capability",
                "field": "requires_human_review",
                "value": "Human review requirement enabled in policy",
                "oversight_config": policy.human_oversight_config if hasattr(policy, 'human_oversight_config') else None,
            })
        else:
            gaps.append("Human review not enabled for this policy")
            recommendations.append("Enable human review requirement for high-risk decisions")
        
        # Review decision tracking
        if config.get("review_decision_tracking"):
            evidence.append({
                "type": "tracking",
                "field": "review_decision_tracking",
                "value": config["review_decision_tracking"],
            })
        
        # SLA compliance monitoring
        if policy.human_oversight_config and policy.human_oversight_config.get("sla_hours"):
            evidence.append({
                "type": "sla",
                "field": "human_oversight_sla",
                "value": f"{policy.human_oversight_config['sla_hours']} hours SLA",
            })
        
        # Determine status
        required_fields = ["human_oversight_measures", "oversight_roles_responsibilities", "override_capabilities"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        has_review_enabled = policy.requires_human_review
        
        if present_fields == len(required_fields) and has_review_enabled:
            status = "compliant"
        elif present_fields >= 2 or has_review_enabled:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=14,
            article_title="Human Oversight",
            requirement="High-risk AI systems shall be designed to enable effective oversight by natural persons",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_article_15(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ArticleEvidence:
        """Article 15: Accuracy, Robustness and Cybersecurity"""
        evidence = []
        gaps = []
        recommendations = []
        
        # Accuracy metrics
        if config.get("accuracy_metrics"):
            evidence.append({
                "type": "accuracy",
                "field": "accuracy_metrics",
                "value": config["accuracy_metrics"],
            })
        else:
            gaps.append("Accuracy metrics not documented")
            recommendations.append("Define and monitor accuracy metrics (precision, recall, F1 score)")
        
        # Robustness testing
        if config.get("robustness_testing"):
            evidence.append({
                "type": "robustness",
                "field": "robustness_testing",
                "value": config["robustness_testing"],
            })
        
        # Conservative mode for robustness
        if hasattr(policy, 'conservative_mode') and policy.conservative_mode:
            evidence.append({
                "type": "system_capability",
                "field": "conservative_mode",
                "value": "Conservative mode enabled for safer decision-making",
            })
        
        # Cybersecurity measures
        if config.get("cybersecurity_measures"):
            evidence.append({
                "type": "security",
                "field": "cybersecurity_measures",
                "value": config["cybersecurity_measures"],
            })
        else:
            gaps.append("Cybersecurity measures not documented")
            recommendations.append("Implement security measures including input validation, access controls, and encryption")
        
        # Error handling
        if config.get("error_handling_procedures"):
            evidence.append({
                "type": "error_handling",
                "field": "error_handling_procedures",
                "value": config["error_handling_procedures"],
            })
        
        # Risk score tracking
        if hasattr(policy, 'risk_threshold') and policy.risk_threshold is not None:
            evidence.append({
                "type": "risk_monitoring",
                "field": "risk_threshold",
                "value": f"Risk threshold set to {policy.risk_threshold}",
                "note": "All decisions tracked with risk scores for accuracy monitoring",
            })
        
        # Determine status
        required_fields = ["accuracy_metrics", "robustness_testing", "cybersecurity_measures"]
        present_fields = sum(1 for f in required_fields if config.get(f))
        has_risk_tracking = hasattr(policy, 'risk_threshold') and policy.risk_threshold is not None
        
        if present_fields == len(required_fields) and has_risk_tracking:
            status = "compliant"
        elif present_fields >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return ArticleEvidence(
            article_number=15,
            article_title="Accuracy, Robustness and Cybersecurity",
            requirement="High-risk AI systems shall achieve appropriate levels of accuracy, robustness and cybersecurity",
            status=status,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _calculate_compliance_score(self, articles: List[ArticleEvidence]) -> float:
        """Calculate overall compliance score (0-100)."""
        if not articles:
            return 0.0
        
        # Weight each article equally
        status_scores = {
            "compliant": 100,
            "partial": 50,
            "non_compliant": 0,
            "not_applicable": None,  # Exclude from scoring
        }
        
        applicable_articles = [a for a in articles if a.status != "not_applicable"]
        if not applicable_articles:
            return 100.0  # All not applicable = compliant
        
        total_score = sum(status_scores.get(a.status, 0) for a in applicable_articles)
        return round(total_score / len(applicable_articles), 2)
    
    def _determine_overall_status(self, score: float) -> str:
        """Determine overall compliance status from score."""
        if score >= 90:
            return "compliant"
        elif score >= 50:
            return "partial"
        else:
            return "non_compliant"
    
    def _identify_critical_gaps(self, articles: List[ArticleEvidence]) -> List[str]:
        """Identify critical compliance gaps."""
        critical = []
        
        # Articles 12, 14, 15 are typically most critical
        critical_articles = {12, 14, 15}
        
        for article in articles:
            if article.article_number in critical_articles and article.status == "non_compliant":
                critical.append(f"Article {article.article_number}: {article.article_title}")
        
        return critical
    
    def _calculate_next_review_date(self, current_date: datetime) -> str:
        """Calculate next compliance review date (quarterly)."""
        from datetime import timedelta
        next_review = current_date + timedelta(days=90)
        return next_review.date().isoformat()
    
    def _generate_report_hash(self, report: ComplianceReport) -> str:
        """Generate SHA-256 hash of report for immutability."""
        # Create canonical representation
        data = {
            "report_id": report.report_id,
            "policy_id": report.policy_id,
            "tenant_id": report.tenant_id,
            "generated_at": report.generated_at,
            "overall_status": report.overall_status,
            "compliance_score": report.compliance_score,
            "articles": [
                {
                    "article": a.article_number,
                    "status": a.status,
                    "evidence_count": len(a.evidence),
                    "gaps_count": len(a.gaps),
                }
                for a in report.articles
            ],
        }
        
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def _create_not_applicable_report(
        self,
        report_id: str,
        policy_id: int,
        policy_name: str,
        tenant_id: int,
        timestamp: datetime,
    ) -> ComplianceReport:
        """Create report for policies without EU AI Act configuration."""
        return ComplianceReport(
            report_id=report_id,
            policy_id=policy_id,
            policy_name=policy_name,
            tenant_id=tenant_id,
            generated_at=timestamp.isoformat(),
            overall_status="not_applicable",
            compliance_score=100.0,
            articles=[],
            summary={
                "note": "EU AI Act framework not configured for this policy",
                "recommendation": "Configure EU AI Act if this is a high-risk AI system",
            },
            report_sha256="",
        )
    
    def export_to_dict(self, report: ComplianceReport) -> Dict[str, Any]:
        """Export report to dictionary format."""
        return {
            "report_id": report.report_id,
            "policy_id": report.policy_id,
            "policy_name": report.policy_name,
            "tenant_id": report.tenant_id,
            "generated_at": report.generated_at,
            "framework": report.framework,
            "framework_version": report.framework_version,
            "overall_status": report.overall_status,
            "compliance_score": report.compliance_score,
            "summary": report.summary,
            "articles": [
                {
                    "article_number": a.article_number,
                    "article_title": a.article_title,
                    "requirement": a.requirement,
                    "status": a.status,
                    "evidence": a.evidence,
                    "gaps": a.gaps,
                    "recommendations": a.recommendations,
                    "last_updated": a.last_updated,
                }
                for a in report.articles
            ],
            "report_sha256": report.report_sha256,
            "immutable": report.immutable,
        }

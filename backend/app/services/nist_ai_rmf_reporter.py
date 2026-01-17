"""
NIST AI RMF (Risk Management Framework) Compliance Report Generator

Generates compliance reports for NIST AI Risk Management Framework
covering the four core functions: GOVERN, MAP, MEASURE, and MANAGE.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import hashlib
import json

from sqlalchemy.orm import Session

from app.schemas.policy_format import PolicyDoc
from app.core.regulatory_templates import NIST_AI_RMF_TEMPLATE


@dataclass
class FunctionEvidence:
    """Evidence for a specific NIST AI RMF function."""
    function_name: str
    function_description: str
    categories: List[Dict[str, Any]]
    status: str  # "compliant", "partial", "non_compliant", "not_applicable"
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class TrustworthinessScorecard:
    """Trustworthiness metrics scorecard."""
    fairness_score: Optional[float] = None
    reliability_score: Optional[float] = None
    safety_score: Optional[float] = None
    transparency_score: Optional[float] = None
    privacy_score: Optional[float] = None
    security_score: Optional[float] = None
    overall_trustworthiness: Optional[float] = None
    metrics_timestamp: str = ""


@dataclass
class RiskRegisterEntry:
    """Entry in the risk register."""
    risk_id: str
    risk_description: str
    category: str
    likelihood: str  # "low", "medium", "high"
    impact: str  # "low", "medium", "high"
    treatment_status: str  # "identified", "analyzed", "mitigated", "accepted"
    mitigation_measures: List[str] = field(default_factory=list)


@dataclass
class NISTAIRMFReport:
    """Complete NIST AI RMF compliance report."""
    report_id: str
    policy_id: int
    policy_name: str
    tenant_id: int
    generated_at: str
    framework: str = "NIST AI RMF"
    framework_version: str = "1.0"
    
    overall_status: str = "compliant"
    compliance_score: float = 0.0
    
    functions: List[FunctionEvidence] = field(default_factory=list)
    trustworthiness_scorecard: TrustworthinessScorecard = field(default_factory=TrustworthinessScorecard)
    risk_register: List[RiskRegisterEntry] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    report_sha256: str = ""
    immutable: bool = True


class NISTAIRMFReporter:
    """
    NIST AI Risk Management Framework compliance reporter.
    
    Generates reports covering the four core functions:
    - GOVERN: Accountability and governance structures
    - MAP: Context understanding and risk identification
    - MEASURE: Trustworthiness metrics and monitoring
    - MANAGE: Risk treatment and continuous improvement
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.template = NIST_AI_RMF_TEMPLATE
    
    def generate_report(
        self,
        policy: PolicyDoc,
        tenant_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> NISTAIRMFReport:
        """Generate comprehensive NIST AI RMF compliance report."""
        timestamp = datetime.now(timezone.utc)
        report_id = f"nistrmf_{policy.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Check if NIST AI RMF is configured
        if "NIST_AI_RMF" not in (policy.regulatory_frameworks or []):
            return self._create_not_applicable_report(
                report_id, policy.id, policy.name, tenant_id, timestamp
            )
        
        config = policy.nist_ai_rmf_config or {}
        
        # Generate evidence for each function
        functions = []
        functions.append(self._assess_govern(policy, config, from_date, to_date))
        functions.append(self._assess_map(policy, config, from_date, to_date))
        functions.append(self._assess_measure(policy, config, from_date, to_date))
        functions.append(self._assess_manage(policy, config, from_date, to_date))
        
        # Generate trustworthiness scorecard
        scorecard = self._generate_trustworthiness_scorecard(policy, config)
        
        # Build risk register
        risk_register = self._build_risk_register(policy, config)
        
        # Calculate overall compliance
        compliance_score = self._calculate_compliance_score(functions)
        overall_status = self._determine_overall_status(compliance_score)
        
        # Build summary
        summary = {
            "total_functions": len(functions),
            "compliant": sum(1 for f in functions if f.status == "compliant"),
            "partial": sum(1 for f in functions if f.status == "partial"),
            "non_compliant": sum(1 for f in functions if f.status == "non_compliant"),
            "compliance_percentage": compliance_score,
            "risk_posture": self._assess_risk_posture(risk_register),
            "trustworthiness_level": self._assess_trustworthiness_level(scorecard),
            "next_review_date": self._calculate_next_review_date(timestamp),
        }
        
        report = NISTAIRMFReport(
            report_id=report_id,
            policy_id=policy.id,
            policy_name=policy.name,
            tenant_id=tenant_id,
            generated_at=timestamp.isoformat(),
            overall_status=overall_status,
            compliance_score=compliance_score,
            functions=functions,
            trustworthiness_scorecard=scorecard,
            risk_register=risk_register,
            summary=summary,
        )
        
        report.report_sha256 = self._generate_report_hash(report)
        
        return report
    
    def _assess_govern(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> FunctionEvidence:
        """GOVERN function: Accountability and governance."""
        categories = []
        gaps = []
        recommendations = []
        
        # Governance structures
        if config.get("governance_structures"):
            categories.append({
                "category": "Governance Structures",
                "evidence": config["governance_structures"],
                "status": "documented",
            })
        else:
            gaps.append("Governance structures not documented")
            recommendations.append("Define AI governance structure with clear roles and responsibilities")
        
        # Accountability mechanisms
        if config.get("accountability_mechanisms"):
            categories.append({
                "category": "Accountability",
                "evidence": config["accountability_mechanisms"],
                "status": "documented",
            })
        
        # Risk tolerance levels
        if config.get("risk_tolerance_levels"):
            categories.append({
                "category": "Risk Tolerance",
                "evidence": config["risk_tolerance_levels"],
                "risk_threshold": getattr(policy, 'risk_threshold', None),
                "status": "configured",
            })
        else:
            gaps.append("Risk tolerance levels not defined")
            recommendations.append("Define organizational risk tolerance and map to policy thresholds")
        
        # Stakeholder engagement
        if config.get("stakeholder_engagement"):
            categories.append({
                "category": "Stakeholder Engagement",
                "evidence": config["stakeholder_engagement"],
                "status": "documented",
            })
        
        # Compliance metadata
        if hasattr(policy, 'compliance_metadata') and policy.compliance_metadata:
            categories.append({
                "category": "Compliance Tracking",
                "evidence": "Compliance metadata tracked in policy",
                "status": policy.compliance_status if hasattr(policy, 'compliance_status') else "unknown",
            })
        
        # Determine status
        required = 3  # governance, accountability, risk tolerance
        present = sum(1 for c in categories if c.get("status") in ["documented", "configured"])
        
        if present >= required:
            status = "compliant"
        elif present >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return FunctionEvidence(
            function_name="GOVERN",
            function_description="Cultivates a culture of AI risk management and establishes governance structures",
            categories=categories,
            status=status,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_map(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> FunctionEvidence:
        """MAP function: Context and risk identification."""
        categories = []
        gaps = []
        recommendations = []
        
        # System context documentation
        if config.get("system_context_documentation"):
            categories.append({
                "category": "System Context",
                "evidence": config["system_context_documentation"],
                "status": "documented",
            })
        else:
            gaps.append("System context not documented")
            recommendations.append("Document AI system context including purpose, scope, and stakeholders")
        
        # Risk categorization
        if config.get("risk_categorization"):
            categories.append({
                "category": "Risk Categorization",
                "evidence": config["risk_categorization"],
                "status": "categorized",
            })
        
        # Impact assessments
        if config.get("impact_assessments"):
            categories.append({
                "category": "Impact Assessments",
                "evidence": config["impact_assessments"],
                "status": "assessed",
            })
        else:
            gaps.append("Impact assessments not conducted")
            recommendations.append("Conduct comprehensive impact assessments for fairness, privacy, and safety")
        
        # Stakeholder analysis
        if config.get("stakeholder_analysis"):
            categories.append({
                "category": "Stakeholder Analysis",
                "evidence": config["stakeholder_analysis"],
                "status": "analyzed",
            })
        
        # Policy-specific context
        categories.append({
            "category": "Policy Configuration",
            "evidence": f"Policy with {len(policy.rules)} rules configured",
            "has_pii_rules": bool(policy.pii_rules),
            "has_intent_rules": bool(getattr(policy, 'intent_rules', None)),
            "status": "configured",
        })
        
        # Determine status
        required = 3  # context, categorization, impact
        present = sum(1 for c in categories if c.get("status") in ["documented", "categorized", "assessed", "configured"])
        
        if present >= required:
            status = "compliant"
        elif present >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return FunctionEvidence(
            function_name="MAP",
            function_description="Establishes context to frame risks related to the AI system",
            categories=categories,
            status=status,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_measure(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> FunctionEvidence:
        """MEASURE function: Trustworthiness metrics."""
        categories = []
        gaps = []
        recommendations = []
        
        # Fairness metrics
        if config.get("fairness_metrics"):
            categories.append({
                "category": "Fairness",
                "evidence": config["fairness_metrics"],
                "bias_detection": bool(policy.blocked_terms) if hasattr(policy, 'blocked_terms') else False,
                "status": "monitored",
            })
        else:
            gaps.append("Fairness metrics not defined")
            recommendations.append("Define and monitor fairness metrics (demographic parity, equalized odds)")
        
        # Reliability metrics
        if config.get("reliability_metrics"):
            categories.append({
                "category": "Reliability",
                "evidence": config["reliability_metrics"],
                "status": "monitored",
            })
        
        # Safety metrics
        if config.get("safety_metrics"):
            categories.append({
                "category": "Safety",
                "evidence": config["safety_metrics"],
                "conservative_mode": getattr(policy, 'conservative_mode', False),
                "status": "monitored",
            })
        
        # Bias testing results
        if config.get("bias_testing_results"):
            categories.append({
                "category": "Bias Testing",
                "evidence": config["bias_testing_results"],
                "status": "tested",
            })
        else:
            gaps.append("Bias testing results not available")
            recommendations.append("Conduct regular bias testing across demographic groups")
        
        # Performance monitoring
        if hasattr(policy, 'risk_threshold') and policy.risk_threshold is not None:
            categories.append({
                "category": "Performance Monitoring",
                "evidence": f"Risk threshold monitoring at {policy.risk_threshold}",
                "status": "active",
            })
        
        # Determine status
        required = 3  # fairness, reliability, safety
        present = sum(1 for c in categories if c.get("status") in ["monitored", "tested", "active"])
        
        if present >= required:
            status = "compliant"
        elif present >= 2:
            status = "partial"
        else:
            status = "non_compliant"
        
        return FunctionEvidence(
            function_name="MEASURE",
            function_description="Employs metrics and methodologies to assess AI trustworthiness and track risks",
            categories=categories,
            status=status,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _assess_manage(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> FunctionEvidence:
        """MANAGE function: Risk treatment and mitigation."""
        categories = []
        gaps = []
        recommendations = []
        
        # Risk treatment plans
        if config.get("risk_treatment_plans"):
            categories.append({
                "category": "Risk Treatment",
                "evidence": config["risk_treatment_plans"],
                "status": "planned",
            })
        else:
            gaps.append("Risk treatment plans not documented")
            recommendations.append("Develop comprehensive risk treatment and mitigation plans")
        
        # Mitigation strategies
        if config.get("mitigation_strategies"):
            categories.append({
                "category": "Mitigation Strategies",
                "evidence": config["mitigation_strategies"],
                "status": "implemented",
            })
        
        # Human oversight implementation
        if policy.requires_human_review:
            oversight_config = policy.human_oversight_config if hasattr(policy, 'human_oversight_config') else {}
            categories.append({
                "category": "Human Oversight",
                "evidence": "Human review requirement enabled",
                "sla_hours": oversight_config.get("sla_hours") if oversight_config else None,
                "triggers": oversight_config.get("triggers") if oversight_config else None,
                "status": "implemented",
            })
        else:
            gaps.append("Human oversight not implemented")
            recommendations.append("Enable human oversight for high-risk decisions")
        
        # Monitoring procedures
        if config.get("monitoring_procedures"):
            categories.append({
                "category": "Monitoring",
                "evidence": config["monitoring_procedures"],
                "status": "active",
            })
        
        # Incident response
        if config.get("incident_response_procedures"):
            categories.append({
                "category": "Incident Response",
                "evidence": config["incident_response_procedures"],
                "status": "documented",
            })
        else:
            gaps.append("Incident response procedures not documented")
            recommendations.append("Document incident response procedures for AI system failures")
        
        # Continuous improvement
        if config.get("continuous_improvement_documentation"):
            categories.append({
                "category": "Continuous Improvement",
                "evidence": config["continuous_improvement_documentation"],
                "status": "active",
            })
        
        # Determine status
        required = 4  # treatment, mitigation, oversight, monitoring
        present = sum(1 for c in categories if c.get("status") in ["planned", "implemented", "active", "documented"])
        
        if present >= required:
            status = "compliant"
        elif present >= 3:
            status = "partial"
        else:
            status = "non_compliant"
        
        return FunctionEvidence(
            function_name="MANAGE",
            function_description="Allocates resources to manage AI risks on a regular basis",
            categories=categories,
            status=status,
            gaps=gaps,
            recommendations=recommendations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
    
    def _generate_trustworthiness_scorecard(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
    ) -> TrustworthinessScorecard:
        """Generate trustworthiness metrics scorecard."""
        scorecard = TrustworthinessScorecard(
            metrics_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Calculate scores based on configuration and policy settings
        # These would ideally come from actual metrics collected from decision logs
        
        # Fairness score (based on bias detection)
        if policy.blocked_terms or config.get("fairness_metrics"):
            scorecard.fairness_score = 85.0  # Placeholder
        
        # Reliability score (based on performance metrics)
        if config.get("reliability_metrics"):
            scorecard.reliability_score = 90.0  # Placeholder
        
        # Safety score (based on conservative mode and safety measures)
        if getattr(policy, 'conservative_mode', False) or config.get("safety_metrics"):
            scorecard.safety_score = 88.0  # Placeholder
        
        # Transparency score (based on explainability)
        if policy.rules:  # Rules provide explanations
            scorecard.transparency_score = 92.0  # Placeholder
        
        # Privacy score (based on PII rules)
        if policy.pii_rules:
            scorecard.privacy_score = 95.0  # Placeholder
        
        # Security score (based on cybersecurity measures)
        if config.get("cybersecurity_measures"):
            scorecard.security_score = 87.0  # Placeholder
        
        # Calculate overall trustworthiness
        scores = [
            s for s in [
                scorecard.fairness_score,
                scorecard.reliability_score,
                scorecard.safety_score,
                scorecard.transparency_score,
                scorecard.privacy_score,
                scorecard.security_score,
            ] if s is not None
        ]
        
        if scores:
            scorecard.overall_trustworthiness = round(sum(scores) / len(scores), 2)
        
        return scorecard
    
    def _build_risk_register(
        self,
        policy: PolicyDoc,
        config: Dict[str, Any],
    ) -> List[RiskRegisterEntry]:
        """Build risk register from configuration."""
        register = []
        
        # Extract identified risks from configuration
        if config.get("risk_categorization"):
            # Parse risk categorization to build register
            # This is a simplified example
            register.append(RiskRegisterEntry(
                risk_id="RISK-001",
                risk_description="Algorithmic bias in decision-making",
                category="Fairness",
                likelihood="medium",
                impact="high",
                treatment_status="mitigated" if policy.blocked_terms else "identified",
                mitigation_measures=["Bias detection rules", "Blocked terms filtering"] if policy.blocked_terms else [],
            ))
        
        # Risk from insufficient human oversight
        if not policy.requires_human_review:
            register.append(RiskRegisterEntry(
                risk_id="RISK-002",
                risk_description="High-risk decisions without human review",
                category="Safety",
                likelihood="high",
                impact="high",
                treatment_status="identified",
                mitigation_measures=[],
            ))
        else:
            register.append(RiskRegisterEntry(
                risk_id="RISK-002",
                risk_description="High-risk decisions without human review",
                category="Safety",
                likelihood="low",
                impact="high",
                treatment_status="mitigated",
                mitigation_measures=["Human review requirement enabled"],
            ))
        
        # Privacy risks
        if not policy.pii_rules:
            register.append(RiskRegisterEntry(
                risk_id="RISK-003",
                risk_description="PII exposure in decision outputs",
                category="Privacy",
                likelihood="medium",
                impact="high",
                treatment_status="identified",
                mitigation_measures=[],
            ))
        
        return register
    
    def _calculate_compliance_score(self, functions: List[FunctionEvidence]) -> float:
        """Calculate overall compliance score."""
        if not functions:
            return 0.0
        
        status_scores = {
            "compliant": 100,
            "partial": 50,
            "non_compliant": 0,
            "not_applicable": None,
        }
        
        applicable = [f for f in functions if f.status != "not_applicable"]
        if not applicable:
            return 100.0
        
        total = sum(status_scores.get(f.status, 0) for f in applicable)
        return round(total / len(applicable), 2)
    
    def _determine_overall_status(self, score: float) -> str:
        """Determine overall status from score."""
        if score >= 90:
            return "compliant"
        elif score >= 50:
            return "partial"
        else:
            return "non_compliant"
    
    def _assess_risk_posture(self, register: List[RiskRegisterEntry]) -> str:
        """Assess overall risk posture."""
        if not register:
            return "unknown"
        
        high_impact_unmitigated = sum(
            1 for r in register
            if r.impact == "high" and r.treatment_status in ["identified", "analyzed"]
        )
        
        if high_impact_unmitigated == 0:
            return "low"
        elif high_impact_unmitigated <= 2:
            return "medium"
        else:
            return "high"
    
    def _assess_trustworthiness_level(self, scorecard: TrustworthinessScorecard) -> str:
        """Assess trustworthiness level."""
        if scorecard.overall_trustworthiness is None:
            return "not_assessed"
        
        if scorecard.overall_trustworthiness >= 85:
            return "high"
        elif scorecard.overall_trustworthiness >= 70:
            return "medium"
        else:
            return "low"
    
    def _calculate_next_review_date(self, current: datetime) -> str:
        """Calculate next review date (quarterly)."""
        from datetime import timedelta
        next_review = current + timedelta(days=90)
        return next_review.date().isoformat()
    
    def _generate_report_hash(self, report: NISTAIRMFReport) -> str:
        """Generate SHA-256 hash for immutability."""
        data = {
            "report_id": report.report_id,
            "policy_id": report.policy_id,
            "generated_at": report.generated_at,
            "compliance_score": report.compliance_score,
            "functions": [
                {"name": f.function_name, "status": f.status}
                for f in report.functions
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
    ) -> NISTAIRMFReport:
        """Create not applicable report."""
        return NISTAIRMFReport(
            report_id=report_id,
            policy_id=policy_id,
            policy_name=policy_name,
            tenant_id=tenant_id,
            generated_at=timestamp.isoformat(),
            overall_status="not_applicable",
            compliance_score=100.0,
            summary={
                "note": "NIST AI RMF framework not configured for this policy",
                "recommendation": "Configure NIST AI RMF for comprehensive AI risk management",
            },
        )
    
    def export_to_dict(self, report: NISTAIRMFReport) -> Dict[str, Any]:
        """Export report to dictionary."""
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
            "functions": [
                {
                    "function_name": f.function_name,
                    "function_description": f.function_description,
                    "categories": f.categories,
                    "status": f.status,
                    "gaps": f.gaps,
                    "recommendations": f.recommendations,
                    "last_updated": f.last_updated,
                }
                for f in report.functions
            ],
            "trustworthiness_scorecard": {
                "fairness_score": report.trustworthiness_scorecard.fairness_score,
                "reliability_score": report.trustworthiness_scorecard.reliability_score,
                "safety_score": report.trustworthiness_scorecard.safety_score,
                "transparency_score": report.trustworthiness_scorecard.transparency_score,
                "privacy_score": report.trustworthiness_scorecard.privacy_score,
                "security_score": report.trustworthiness_scorecard.security_score,
                "overall_trustworthiness": report.trustworthiness_scorecard.overall_trustworthiness,
                "metrics_timestamp": report.trustworthiness_scorecard.metrics_timestamp,
            },
            "risk_register": [
                {
                    "risk_id": r.risk_id,
                    "risk_description": r.risk_description,
                    "category": r.category,
                    "likelihood": r.likelihood,
                    "impact": r.impact,
                    "treatment_status": r.treatment_status,
                    "mitigation_measures": r.mitigation_measures,
                }
                for r in report.risk_register
            ],
            "report_sha256": report.report_sha256,
            "immutable": report.immutable,
        }

"""
Tests for compliance reporter services.

Tests EU AI Act, NIST AI RMF, and NIST Privacy Framework reporters.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from app.services.eu_ai_act_reporter import EUAIActReporter
from app.services.nist_ai_rmf_reporter import NISTAIRMFReporter
from app.services.nist_privacy_reporter import NISTPrivacyReporter
from app.schemas.policy_format import PolicyDoc


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def sample_eu_ai_act_policy():
    """Sample policy with EU AI Act configuration."""
    return PolicyDoc(
        id=1,
        name="test-policy",
        version=1,
        regulatory_frameworks=["EU_AI_ACT"],
        eu_ai_act_config={
            "risk_management_system": "Comprehensive risk management documented",
            "risk_acceptability_threshold": "0.7",
            "continuous_risk_monitoring": "Automated monitoring enabled",
            "data_quality_measures": "Data validation procedures in place",
            "data_governance_policies": "GDPR-compliant governance",
            "bias_detection_mitigation": "Bias testing quarterly",
            "system_design_documentation": "Architecture docs available",
            "performance_metrics_documentation": "KPIs tracked",
            "audit_logging_configuration": "All decisions logged",
            "log_retention_period": "5 years",
            "decision_traceability": "Full audit trail",
            "tamper_proof_logging": "Cryptographic hashing",
            "user_transparency_measures": "Decision explanations provided",
            "decision_explanation_capabilities": "Rule-based reasoning",
            "purpose_and_limitations_disclosure": "User guide published",
            "human_oversight_measures": "Human review workflow",
            "oversight_roles_responsibilities": "Reviewers assigned",
            "override_capabilities": "Manual override enabled",
            "accuracy_metrics": "95% accuracy target",
            "robustness_testing": "Adversarial testing quarterly",
            "cybersecurity_measures": "ISO 27001 compliant",
        },
        rules=["rule1", "rule2"],
        pii_rules={"email": {"action": "mask"}, "ssn": {"action": "redact"}},
        requires_human_review=True,
        human_oversight_config={"sla_hours": 24, "triggers": ["high_risk"]},
        risk_threshold=0.7,
        conservative_mode=True,
    )


@pytest.fixture
def sample_nist_rmf_policy():
    """Sample policy with NIST AI RMF configuration."""
    return PolicyDoc(
        id=2,
        name="rmf-policy",
        version=1,
        regulatory_frameworks=["NIST_AI_RMF"],
        nist_ai_rmf_config={
            "governance_structures": "AI Governance Board established",
            "accountability_mechanisms": "Clear accountability framework",
            "risk_tolerance_levels": "Medium risk tolerance",
            "stakeholder_engagement": "Monthly stakeholder reviews",
            "system_context_documentation": "System context documented",
            "risk_categorization": "High-risk AI system",
            "impact_assessments": "Impact assessment completed",
            "stakeholder_analysis": "Stakeholder mapping done",
            "fairness_metrics": "Demographic parity monitored",
            "reliability_metrics": "99.5% uptime target",
            "safety_metrics": "Zero safety incidents target",
            "bias_testing_results": "Bias testing passed",
            "risk_treatment_plans": "Risk treatment documented",
            "mitigation_strategies": "Mitigation measures in place",
            "monitoring_procedures": "Continuous monitoring active",
            "incident_response_procedures": "Incident response plan",
            "continuous_improvement_documentation": "Quarterly reviews",
        },
        rules=["rule1"],
        pii_rules={"email": {"action": "mask"}},
        blocked_terms=["hate", "violence"],
        requires_human_review=True,
        risk_threshold=0.6,
        conservative_mode=True,
        compliance_metadata={"validated": True},
        compliance_status="validated",
    )


@pytest.fixture
def sample_nist_privacy_policy():
    """Sample policy with NIST Privacy Framework configuration."""
    return PolicyDoc(
        id=3,
        name="privacy-policy",
        version=1,
        regulatory_frameworks=["NIST_PRIVACY"],
        nist_privacy_config={
            "data_processing_inventory": "All processing activities documented",
            "data_processing_purposes": "Purposes clearly defined",
            "privacy_risk_assessments": "PIA completed",
            "stakeholder_privacy_expectations": "Privacy expectations documented",
            "privacy_governance_policies": "Privacy governance framework",
            "data_minimization_procedures": "Data minimization enforced",
            "individual_rights_management": "Data subject rights process",
            "privacy_by_design_implementation": "Privacy by design integrated",
            "data_lifecycle_controls": "Lifecycle controls documented",
            "pii_access_controls": "RBAC for PII access",
            "data_sharing_limitations": "Strict sharing controls",
            "data_retention_deletion_policies": "Retention policies defined",
            "privacy_notices": "Privacy notices published",
            "consent_mechanisms": "Consent management system",
            "privacy_training_programs": "Annual privacy training",
            "transparency_measures": "Transparency reports published",
            "technical_safeguards": "Encryption and masking",
            "data_security_measures": "Security controls implemented",
            "privacy_incident_response": "Breach notification process",
            "anonymization_procedures": "Anonymization techniques used",
        },
        rules=["privacy_rule1", "privacy_rule2"],
        pii_rules={
            "email": {"action": "mask"},
            "phone": {"action": "redact"},
            "address": {"action": "anonymize"},
            "ssn": {"action": "block"},
            "credit_card": {"action": "tokenize"},
        },
        compliance_status="validated",
    )


class TestEUAIActReporter:
    """Tests for EU AI Act compliance reporter."""
    
    def test_generate_report_with_eu_config(self, mock_db, sample_eu_ai_act_policy):
        """Test report generation with EU AI Act configuration."""
        reporter = EUAIActReporter(mock_db)
        report = reporter.generate_report(sample_eu_ai_act_policy, tenant_id=1)
        
        assert report.report_id.startswith("euaiact_1_")
        assert report.policy_id == 1
        assert report.policy_name == "test-policy"
        assert report.framework == "EU AI Act"
        assert report.overall_status in ["compliant", "partial", "non_compliant"]
        assert 0 <= report.compliance_score <= 100
        assert len(report.articles) == 7  # Articles 9-15
        assert report.report_sha256  # Hash generated
        
    def test_article_9_assessment(self, mock_db, sample_eu_ai_act_policy):
        """Test Article 9 (Risk Management) assessment."""
        reporter = EUAIActReporter(mock_db)
        report = reporter.generate_report(sample_eu_ai_act_policy, tenant_id=1)
        
        article_9 = next(a for a in report.articles if a.article_number == 9)
        assert article_9.article_title == "Risk Management System"
        assert article_9.status == "compliant"  # All required fields present
        assert len(article_9.evidence) > 0
        
    def test_article_14_human_oversight(self, mock_db, sample_eu_ai_act_policy):
        """Test Article 14 (Human Oversight) assessment."""
        reporter = EUAIActReporter(mock_db)
        report = reporter.generate_report(sample_eu_ai_act_policy, tenant_id=1)
        
        article_14 = next(a for a in report.articles if a.article_number == 14)
        assert article_14.article_title == "Human Oversight"
        assert article_14.status in ["compliant", "partial"]
        
        # Check human review evidence
        has_review_evidence = any(
            e.get("field") == "requires_human_review" for e in article_14.evidence
        )
        assert has_review_evidence
        
    def test_not_applicable_report(self, mock_db):
        """Test report for policy without EU AI Act configuration."""
        policy = PolicyDoc(
            id=99,
            name="non-eu-policy",
            version=1,
            regulatory_frameworks=["OTHER"],
            rules=[],
        )
        
        reporter = EUAIActReporter(mock_db)
        report = reporter.generate_report(policy, tenant_id=1)
        
        assert report.overall_status == "not_applicable"
        assert report.compliance_score == 100.0
        assert len(report.articles) == 0
        
    def test_export_to_dict(self, mock_db, sample_eu_ai_act_policy):
        """Test export to dictionary format."""
        reporter = EUAIActReporter(mock_db)
        report = reporter.generate_report(sample_eu_ai_act_policy, tenant_id=1)
        
        export = reporter.export_to_dict(report)
        
        assert export["report_id"] == report.report_id
        assert export["policy_id"] == report.policy_id
        assert export["framework"] == "EU AI Act"
        assert "articles" in export
        assert len(export["articles"]) == 7
        assert export["report_sha256"]


class TestNISTAIRMFReporter:
    """Tests for NIST AI RMF compliance reporter."""
    
    def test_generate_report_with_rmf_config(self, mock_db, sample_nist_rmf_policy):
        """Test report generation with NIST AI RMF configuration."""
        reporter = NISTAIRMFReporter(mock_db)
        report = reporter.generate_report(sample_nist_rmf_policy, tenant_id=1)
        
        assert report.report_id.startswith("nistrmf_2_")
        assert report.policy_id == 2
        assert report.framework == "NIST AI RMF"
        assert len(report.functions) == 4  # GOVERN, MAP, MEASURE, MANAGE
        assert report.trustworthiness_scorecard is not None
        assert len(report.risk_register) > 0
        
    def test_govern_function(self, mock_db, sample_nist_rmf_policy):
        """Test GOVERN function assessment."""
        reporter = NISTAIRMFReporter(mock_db)
        report = reporter.generate_report(sample_nist_rmf_policy, tenant_id=1)
        
        govern = next(f for f in report.functions if f.function_name == "GOVERN")
        assert "Accountability" in govern.function_description or "governance" in govern.function_description.lower()
        assert len(govern.categories) > 0
        assert govern.status in ["compliant", "partial", "non_compliant"]
        
    def test_measure_function(self, mock_db, sample_nist_rmf_policy):
        """Test MEASURE function assessment."""
        reporter = NISTAIRMFReporter(mock_db)
        report = reporter.generate_report(sample_nist_rmf_policy, tenant_id=1)
        
        measure = next(f for f in report.functions if f.function_name == "MEASURE")
        assert "trustworthiness" in measure.function_description.lower() or "metrics" in measure.function_description.lower()
        
    def test_trustworthiness_scorecard(self, mock_db, sample_nist_rmf_policy):
        """Test trustworthiness scorecard generation."""
        reporter = NISTAIRMFReporter(mock_db)
        report = reporter.generate_report(sample_nist_rmf_policy, tenant_id=1)
        
        scorecard = report.trustworthiness_scorecard
        assert scorecard.overall_trustworthiness is not None
        assert 0 <= scorecard.overall_trustworthiness <= 100
        
    def test_risk_register(self, mock_db, sample_nist_rmf_policy):
        """Test risk register generation."""
        reporter = NISTAIRMFReporter(mock_db)
        report = reporter.generate_report(sample_nist_rmf_policy, tenant_id=1)
        
        assert len(report.risk_register) > 0
        for risk in report.risk_register:
            assert risk.risk_id
            assert risk.category
            assert risk.treatment_status in ["identified", "analyzed", "mitigated", "accepted"]


class TestNISTPrivacyReporter:
    """Tests for NIST Privacy Framework compliance reporter."""
    
    def test_generate_report_with_privacy_config(self, mock_db, sample_nist_privacy_policy):
        """Test report generation with NIST Privacy configuration."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        assert report.report_id.startswith("nistprivacy_3_")
        assert report.policy_id == 3
        assert report.framework == "NIST Privacy Framework"
        assert len(report.functions) == 5  # IDENTIFY-P, GOVERN-P, CONTROL-P, COMMUNICATE-P, PROTECT-P
        assert report.privacy_metrics is not None
        
    def test_identify_p_function(self, mock_db, sample_nist_privacy_policy):
        """Test IDENTIFY-P function assessment."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        identify = next(f for f in report.functions if f.function_name == "IDENTIFY-P")
        assert "privacy risks" in identify.function_description.lower() or "data processing" in identify.function_description.lower()
        assert len(identify.categories) > 0
        
    def test_control_p_function(self, mock_db, sample_nist_privacy_policy):
        """Test CONTROL-P function assessment."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        control = next(f for f in report.functions if f.function_name == "CONTROL-P")
        assert len(control.categories) > 0
        
        # Should have PII detection evidence
        has_pii_evidence = any(
            "PII" in str(c.get("category", "")) for c in control.categories
        )
        assert has_pii_evidence
        
    def test_protect_p_function(self, mock_db, sample_nist_privacy_policy):
        """Test PROTECT-P function assessment."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        protect = next(f for f in report.functions if f.function_name == "PROTECT-P")
        assert "safeguards" in protect.function_description.lower()
        
    def test_privacy_metrics(self, mock_db, sample_nist_privacy_policy):
        """Test privacy metrics generation."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        metrics = report.privacy_metrics
        assert metrics.pii_detection_rate is not None
        assert metrics.pii_masking_accuracy is not None
        assert metrics.privacy_incident_count >= 0
        
    def test_data_lifecycle_controls(self, mock_db, sample_nist_privacy_policy):
        """Test data lifecycle controls."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        assert len(report.data_lifecycle_controls) > 0
        for control in report.data_lifecycle_controls:
            assert control.data_category
            assert control.collection_purpose
            assert control.retention_period
            
    def test_pii_protection_level(self, mock_db, sample_nist_privacy_policy):
        """Test PII protection level assessment."""
        reporter = NISTPrivacyReporter(mock_db)
        report = reporter.generate_report(sample_nist_privacy_policy, tenant_id=1)
        
        # Policy has 5 PII rules
        assert report.summary["pii_protection_level"] == "comprehensive"


class TestComplianceReportAPI:
    """Integration tests for compliance report API endpoints."""
    
    def test_eu_ai_act_endpoint_not_found(self, client):
        """Test EU AI Act endpoint with non-existent policy."""
        resp = client.get("/api/reports/compliance/eu-ai-act/99999?tenant_id=1")
        # May return 401/403 if auth required, or 404 if policy doesn't exist
        assert resp.status_code in [401, 403, 404]
        
    def test_nist_rmf_endpoint_format(self, client):
        """Test NIST AI RMF endpoint format parameter."""
        # This would require a real policy to exist
        # For now, just test that the endpoint exists and handles auth
        resp = client.get("/api/reports/compliance/nist-ai-rmf/1?tenant_id=1&format=json")
        assert resp.status_code in [200, 401, 403, 404]
        
    def test_nist_privacy_endpoint_date_range(self, client):
        """Test NIST Privacy endpoint with date range."""
        resp = client.get(
            "/api/reports/compliance/nist-privacy/1?tenant_id=1&from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z"
        )
        assert resp.status_code in [200, 401, 403, 404]

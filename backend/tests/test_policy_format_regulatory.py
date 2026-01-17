"""
Unit tests for enhanced PolicyDoc schema with regulatory compliance features.
"""

import pytest
from pydantic import ValidationError
from app.schemas.policy_format import PolicyDoc


class TestPolicyDocRegulatory:
    """Test regulatory compliance features of PolicyDoc."""

    def test_policy_doc_backward_compatibility(self):
        """Test that existing policy documents remain valid."""
        # Original policy format without compliance fields
        original_policy = {
            "blocked_terms": ["violence", "weapon"],
            "allowed_sources": ["example.com", "trusted.org"],
            "required_evidence_types": ["scientific"],
            "pii_rules": {"deny_email": True},
            "risk_threshold": 75,
        }
        
        policy = PolicyDoc(**original_policy)
        assert policy.blocked_terms == ["violence", "weapon"]
        assert policy.regulatory_frameworks == []
        assert policy.compliance_status == "draft"
        assert policy.requires_human_review is False
        assert policy.eu_ai_act_config == {}
        assert policy.nist_ai_rmf_config == {}
        assert policy.nist_privacy_config == {}

    def test_regulatory_frameworks_field(self):
        """Test regulatory frameworks field validation."""
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 50,
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf", "nist_privacy"]
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.regulatory_frameworks == ["eu_ai_act_high_risk", "nist_ai_rmf", "nist_privacy"]

    def test_eu_ai_act_config_field(self):
        """Test EU AI Act configuration field."""
        eu_config = {
            "article_9": {
                "risk_management_system": "Implemented comprehensive risk assessment",
                "risk_mitigation_measures": "Automated content filtering and human oversight"
            },
            "article_10": {
                "data_governance": "Data quality monitoring in place",
                "training_data_quality": "Validated against bias and accuracy metrics"
            },
            "article_13": {
                "transparency_obligations": "Users informed of AI decision-making",
                "information_provided": "Risk level and decision factors disclosed"
            }
        }
        
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 70,
            "regulatory_frameworks": ["eu_ai_act_high_risk"],
            "eu_ai_act_config": eu_config
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.eu_ai_act_config == eu_config
        assert policy.eu_ai_act_config["article_9"]["risk_management_system"] == "Implemented comprehensive risk assessment"

    def test_nist_ai_rmf_config_field(self):
        """Test NIST AI RMF configuration field."""
        nist_config = {
            "govern": {
                "accountability_structures": "Chief AI Officer designated",
                "risk_tolerance": "Medium risk tolerance for content moderation"
            },
            "map": {
                "ai_system_context": "Content moderation and policy enforcement",
                "stakeholder_impacts": "Users, content creators, regulators"
            },
            "measure": {
                "trustworthiness_metrics": "Accuracy: 95%, Fairness: 90%, Safety: 98%",
                "performance_monitoring": "Continuous bias and accuracy monitoring"
            },
            "manage": {
                "risk_treatment": "Automated filtering with human escalation",
                "monitoring_procedures": "Real-time dashboard and weekly reviews"
            }
        }
        
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 60,
            "regulatory_frameworks": ["nist_ai_rmf"],
            "nist_ai_rmf_config": nist_config
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.nist_ai_rmf_config == nist_config

    def test_nist_privacy_config_field(self):
        """Test NIST Privacy Framework configuration field."""
        privacy_config = {
            "identify_p": {
                "data_processing_purposes": "Content analysis and policy enforcement",
                "privacy_risk_assessment": "High risk for PII exposure"
            },
            "govern_p": {
                "data_minimization": "Only necessary data processed",
                "individual_rights": "Right to erasure and correction supported"
            },
            "control_p": {
                "data_lifecycle": "30-day retention for audit purposes",
                "pii_handling": "Automatic masking and anonymization"
            }
        }
        
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 80,
            "regulatory_frameworks": ["nist_privacy"],
            "nist_privacy_config": privacy_config
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.nist_privacy_config == privacy_config

    def test_compliance_metadata_field(self):
        """Test compliance metadata field for mappings and validation status."""
        metadata = {
            "article_mappings": {
                "risk_threshold": ["eu_ai_act_article_15", "nist_ai_rmf_manage"],
                "pii_rules": ["nist_privacy_control_p", "eu_ai_act_article_10"]
            },
            "validation_results": {
                "eu_ai_act": {"status": "compliant", "score": 95},
                "nist_ai_rmf": {"status": "partial", "score": 78}
            },
            "auto_generated_rules": {
                "risk_threshold": "Generated from EU AI Act Article 15 accuracy requirements",
                "requires_human_review": "Set from Article 14 human oversight mandate"
            },
            "last_validated": "2026-01-17T10:30:00Z"
        }
        
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 85,
            "compliance_metadata": metadata
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.compliance_metadata == metadata

    def test_compliance_status_field(self):
        """Test compliance status field validation."""
        # Test valid statuses
        for status in ["draft", "validated", "non_compliant"]:
            policy_data = {
                "blocked_terms": [],
                "allowed_sources": [],
                "required_evidence_types": [],
                "pii_rules": {},
                "risk_threshold": 50,
                "compliance_status": status
            }
            policy = PolicyDoc(**policy_data)
            assert policy.compliance_status == status

    def test_requires_human_review_field(self):
        """Test human review requirement field."""
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 90,
            "requires_human_review": True
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.requires_human_review is True

    def test_human_oversight_config_field(self):
        """Test human oversight configuration field."""
        oversight_config = {
            "triggers": {
                "risk_score_threshold": 80,
                "specific_violations": ["blocked_terms", "pii_detected"],
                "policy_frameworks": ["eu_ai_act_high_risk"]
            },
            "sla": {
                "review_deadline_hours": 24,
                "escalation_hours": 48,
                "notification_methods": ["email", "dashboard"]
            },
            "reviewers": {
                "required_qualifications": ["compliance_officer", "domain_expert"],
                "assignment_method": "round_robin"
            }
        }
        
        policy_data = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 70,
            "human_oversight_config": oversight_config
        }
        
        policy = PolicyDoc(**policy_data)
        assert policy.human_oversight_config == oversight_config

    def test_multi_framework_policy(self):
        """Test policy with multiple regulatory frameworks."""
        policy_data = {
            "blocked_terms": ["violence", "discrimination"],
            "allowed_sources": ["verified.gov"],
            "required_evidence_types": ["official"],
            "pii_rules": {"deny_email": True, "mask_phone": True},
            "risk_threshold": 75,
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf", "nist_privacy"],
            "eu_ai_act_config": {
                "article_14": {"human_oversight": True},
                "article_15": {"accuracy_requirements": ">=95%"}
            },
            "nist_ai_rmf_config": {
                "govern": {"risk_tolerance": "low"},
                "manage": {"human_oversight": True}
            },
            "nist_privacy_config": {
                "control_p": {"data_minimization": True}
            },
            "compliance_status": "validated",
            "requires_human_review": True
        }
        
        policy = PolicyDoc(**policy_data)
        assert len(policy.regulatory_frameworks) == 3
        assert policy.compliance_status == "validated"
        assert policy.requires_human_review is True

    def test_policy_doc_serialization(self):
        """Test that enhanced PolicyDoc can be properly serialized and deserialized."""
        policy_data = {
            "blocked_terms": ["test"],
            "allowed_sources": ["example.com"],
            "required_evidence_types": ["scientific"],
            "pii_rules": {"deny_email": True},
            "risk_threshold": 80,
            "regulatory_frameworks": ["eu_ai_act_high_risk"],
            "eu_ai_act_config": {"article_9": {"implemented": True}},
            "compliance_status": "validated"
        }
        
        # Create policy from dict
        policy = PolicyDoc(**policy_data)
        
        # Serialize to dict
        serialized = policy.model_dump()
        
        # Deserialize back to policy
        policy_restored = PolicyDoc(**serialized)
        
        # Verify data integrity
        assert policy_restored.regulatory_frameworks == ["eu_ai_act_high_risk"]
        assert policy_restored.eu_ai_act_config == {"article_9": {"implemented": True}}
        assert policy_restored.compliance_status == "validated"

    def test_default_values(self):
        """Test that all new compliance fields have appropriate default values."""
        minimal_policy = {
            "blocked_terms": [],
            "allowed_sources": [],
            "required_evidence_types": [],
            "pii_rules": {},
            "risk_threshold": 50
        }
        
        policy = PolicyDoc(**minimal_policy)
        
        # Verify all compliance fields have proper defaults
        assert policy.regulatory_frameworks == []
        assert policy.eu_ai_act_config == {}
        assert policy.nist_ai_rmf_config == {}
        assert policy.nist_privacy_config == {}
        assert policy.compliance_metadata == {}
        assert policy.requires_human_review is False
        assert policy.compliance_status == "draft"
        assert policy.human_oversight_config == {}

    def test_field_descriptions(self):
        """Test that all fields have proper descriptions for API documentation."""
        policy = PolicyDoc(
            blocked_terms=[],
            allowed_sources=[],
            required_evidence_types=[],
            pii_rules={},
            risk_threshold=50
        )
        
        # Get field info from schema
        schema = PolicyDoc.model_json_schema()
        properties = schema["properties"]
        
        # Verify compliance fields have descriptions
        assert "description" in properties["regulatory_frameworks"]
        assert "description" in properties["eu_ai_act_config"]
        assert "description" in properties["nist_ai_rmf_config"]
        assert "description" in properties["nist_privacy_config"]
        assert "description" in properties["compliance_metadata"]
        assert "description" in properties["requires_human_review"]
        assert "description" in properties["compliance_status"]
        assert "description" in properties["human_oversight_config"]
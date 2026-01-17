"""
Unit tests for regulatory framework templates and field definitions.
"""

import pytest
from app.core.regulatory_templates import (
    REGULATORY_FRAMEWORKS,
    EU_AI_ACT_HIGH_RISK_TEMPLATE,
    NIST_AI_RMF_TEMPLATE,
    NIST_PRIVACY_TEMPLATE,
    get_framework_template,
    get_available_frameworks,
    validate_framework_config,
    FieldType,
    EnforcementRule,
    ComplianceField,
    ComplianceSection,
    RegulatoryFramework
)


class TestRegulatoryTemplates:
    """Test regulatory framework templates and definitions."""

    def test_framework_registry_completeness(self):
        """Test that all expected frameworks are in the registry."""
        expected_frameworks = ["eu_ai_act_high_risk", "nist_ai_rmf", "nist_privacy"]
        available_frameworks = get_available_frameworks()
        
        assert len(available_frameworks) == 3
        for framework_id in expected_frameworks:
            assert framework_id in available_frameworks
            assert framework_id in REGULATORY_FRAMEWORKS

    def test_get_framework_template(self):
        """Test getting framework templates by ID."""
        # Test valid framework IDs
        eu_framework = get_framework_template("eu_ai_act_high_risk")
        assert eu_framework.id == "eu_ai_act_high_risk"
        assert eu_framework.name == "EU AI Act - High-Risk AI Systems"
        
        nist_rmf = get_framework_template("nist_ai_rmf")
        assert nist_rmf.id == "nist_ai_rmf"
        assert nist_rmf.name == "NIST AI Risk Management Framework"
        
        # Test invalid framework ID
        with pytest.raises(ValueError, match="Unknown regulatory framework"):
            get_framework_template("invalid_framework")

    def test_eu_ai_act_template_structure(self):
        """Test EU AI Act template structure and content."""
        framework = EU_AI_ACT_HIGH_RISK_TEMPLATE
        
        # Basic framework properties
        assert framework.id == "eu_ai_act_high_risk"
        assert framework.version == "2024"
        assert len(framework.sections) == 7  # Articles 9-15
        
        # Check all expected sections are present
        section_ids = [section.id for section in framework.sections]
        expected_sections = ["article_9", "article_10", "article_11", "article_12", "article_13", "article_14", "article_15"]
        for expected_id in expected_sections:
            assert expected_id in section_ids
        
        # Check Article 9 (Risk Management System) in detail
        article_9 = next(section for section in framework.sections if section.id == "article_9")
        assert article_9.title == "Article 9 - Risk Management System"
        assert len(article_9.fields) >= 4  # Should have multiple required fields
        
        # Check that required fields exist in Article 9
        field_ids = [field.id for field in article_9.fields]
        assert "risk_management_system" in field_ids
        assert "risk_mitigation_measures" in field_ids
        
        # Verify enforcement mappings exist where expected
        risk_mitigation_field = next(field for field in article_9.fields if field.id == "risk_mitigation_measures")
        assert EnforcementRule.HUMAN_REVIEW in risk_mitigation_field.enforcement_mapping

    def test_nist_ai_rmf_template_structure(self):
        """Test NIST AI RMF template structure and content."""
        framework = NIST_AI_RMF_TEMPLATE
        
        # Basic framework properties
        assert framework.id == "nist_ai_rmf"
        assert framework.version == "1.0"
        assert len(framework.sections) == 4  # Four core functions
        
        # Check all expected sections (four functions)
        section_ids = [section.id for section in framework.sections]
        expected_sections = ["govern", "map", "measure", "manage"]
        for expected_id in expected_sections:
            assert expected_id in section_ids
        
        # Check GOVERN function in detail
        govern_section = next(section for section in framework.sections if section.id == "govern")
        assert govern_section.title == "GOVERN Function"
        assert len(govern_section.fields) >= 4
        
        # Verify risk tolerance field has enforcement mapping
        risk_tolerance_field = next(
            field for field in govern_section.fields 
            if field.id == "ai_risk_tolerance"
        )
        assert risk_tolerance_field.field_type == FieldType.SELECT
        assert "low" in risk_tolerance_field.options
        assert EnforcementRule.RISK_THRESHOLD in risk_tolerance_field.enforcement_mapping

    def test_nist_privacy_template_structure(self):
        """Test NIST Privacy Framework template structure and content."""
        framework = NIST_PRIVACY_TEMPLATE
        
        # Basic framework properties
        assert framework.id == "nist_privacy"
        assert framework.version == "1.0"
        assert len(framework.sections) == 5  # Five privacy functions
        
        # Check all expected sections
        section_ids = [section.id for section in framework.sections]
        expected_sections = ["identify_p", "govern_p", "control_p", "communicate_p", "protect_p"]
        for expected_id in expected_sections:
            assert expected_id in section_ids
        
        # Check CONTROL-P function in detail
        control_section = next(section for section in framework.sections if section.id == "control_p")
        assert control_section.title == "CONTROL-P Function"
        
        # Verify PII-related enforcement mappings
        collection_control_field = next(
            field for field in control_section.fields 
            if field.id == "collection_controls"
        )
        assert EnforcementRule.PII_RULES in collection_control_field.enforcement_mapping

    def test_compliance_field_structure(self):
        """Test ComplianceField structure and validation."""
        # Test field creation with all properties
        field = ComplianceField(
            id="test_field",
            label="Test Field",
            field_type=FieldType.SELECT,
            description="A test field",
            required=True,
            options=["option1", "option2"],
            validation_rules={"min": 1, "max": 10},
            help_text="This is help text",
            enforcement_mapping={EnforcementRule.RISK_THRESHOLD: 75},
            regulatory_reference="Test Article 1"
        )
        
        assert field.id == "test_field"
        assert field.field_type == FieldType.SELECT
        assert field.required is True
        assert len(field.options) == 2
        assert field.enforcement_mapping[EnforcementRule.RISK_THRESHOLD] == 75

    def test_field_types_enum(self):
        """Test that all expected field types are available."""
        expected_types = ["text", "textarea", "select", "multiselect", "boolean", "number", "date", "url", "email"]
        
        for expected_type in expected_types:
            # Should not raise exception
            field_type = FieldType(expected_type)
            assert field_type.value == expected_type

    def test_enforcement_rules_enum(self):
        """Test that all expected enforcement rules are available."""
        expected_rules = [
            "risk_threshold", "pii_rules", "requires_human_review",
            "blocked_terms", "allowed_sources", "conservative_mode", "intent_rules"
        ]
        
        for expected_rule in expected_rules:
            enforcement_rule = EnforcementRule(expected_rule)
            assert enforcement_rule.value == expected_rule


class TestFrameworkValidation:
    """Test framework configuration validation."""

    def test_validate_complete_eu_ai_act_config(self):
        """Test validation of complete EU AI Act configuration."""
        # Create a complete valid configuration
        config = {
            "article_9": {
                "risk_management_system": "Comprehensive risk management implemented",
                "risk_identification_process": "Systematic risk identification process",
                "risk_mitigation_measures": "Automated filtering and human oversight",
                "residual_risk_evaluation": "Residual risks evaluated monthly",
                "risk_acceptability_threshold": 70
            },
            "article_10": {
                "data_governance_practices": "Strong data governance in place",
                "training_data_quality": "High quality training data validated",
                "bias_monitoring": "Continuous bias monitoring implemented",
                "data_completeness_check": "Regular data quality checks",
                "privacy_protection_measures": "PII protection and anonymization"
            },
            "article_11": {
                "technical_documentation": "Complete technical documentation maintained",
                "system_description": "AI system for content moderation",
                "intended_purpose": "Automated content filtering and policy enforcement",
                "architecture_description": "Distributed microservices architecture"
            },
            "article_12": {
                "automatic_logging": True,
                "logging_duration": 36,
                "logged_data_types": ["input_data", "output_data", "timestamps", "system_decisions"],
                "log_traceability": "Full traceability through structured logging"
            },
            "article_13": {
                "transparency_design": "Transparent decision-making process",
                "user_information_content": "Clear information provided to users",
                "decision_explanation": "Automated decision explanations generated",
                "user_understanding_measures": "User education and clear documentation"
            },
            "article_14": {
                "human_oversight_design": "Human oversight built into system design",
                "oversight_measures_type": ["human_on_the_loop", "human_in_command"],
                "overseer_qualifications": "Trained compliance officers with domain expertise",
                "oversight_effectiveness": "Regular effectiveness reviews conducted",
                "intervention_capability": "Real-time intervention capabilities implemented"
            },
            "article_15": {
                "accuracy_measures": "Rigorous accuracy testing and validation",
                "accuracy_metrics": "95% accuracy target with continuous monitoring",
                "robustness_measures": "Extensive robustness testing against edge cases",
                "cybersecurity_measures": "Multi-layered cybersecurity protection"
            }
        }
        
        result = validate_framework_config("eu_ai_act_high_risk", config)
        assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
        assert len(result["warnings"]) == 0

    def test_validate_incomplete_config(self):
        """Test validation of incomplete configuration."""
        # Missing required fields
        incomplete_config = {
            "article_9": {
                "risk_management_system": "Some description"
                # Missing other required fields
            }
        }
        
        result = validate_framework_config("eu_ai_act_high_risk", incomplete_config)
        assert len(result["errors"]) > 0
        
        # Check that specific missing fields are reported
        error_messages = " ".join(result["errors"])
        assert "Risk Identification Process" in error_messages
        assert "Risk Mitigation Measures" in error_messages

    def test_validate_invalid_field_values(self):
        """Test validation of invalid field values."""
        config = {
            "article_9": {
                "risk_acceptability_threshold": 150  # Invalid: above max of 100
            },
            "article_12": {
                "automatic_logging": True,
                "logging_duration": 3,  # Invalid: below min of 6
                "logged_data_types": ["invalid_type"],  # Invalid option
                "log_traceability": "Valid description"
            }
        }
        
        result = validate_framework_config("eu_ai_act_high_risk", config)
        assert len(result["errors"]) > 0
        
        error_messages = " ".join(result["errors"])
        assert "above maximum" in error_messages  # Risk threshold error
        assert "below minimum" in error_messages  # Logging duration error
        assert "Invalid options" in error_messages  # Invalid logged data type

    def test_validate_nist_ai_rmf_config(self):
        """Test validation of NIST AI RMF configuration."""
        config = {
            "govern": {
                "ai_governance_structure": "Chief AI Officer leads governance committee",
                "ai_risk_tolerance": "medium",  # Valid option
                "stakeholder_engagement": "Regular stakeholder consultations",
                "ai_policy_framework": "Comprehensive AI policies established",
                "accountability_mechanisms": "Clear accountability structures"
            },
            "map": {
                "ai_system_context": "Content moderation system for social media",
                "ai_system_categorization": "high_risk",  # Valid option
                "stakeholder_impact_analysis": "Impact on users, content creators analyzed",
                "risk_identification": "AI-specific risks identified and catalogued",
                "interdependency_mapping": "System dependencies mapped"
            },
            "measure": {
                "trustworthiness_metrics": "Fairness: 90%, Reliability: 95%, Safety: 98%",
                "performance_monitoring": "Continuous performance monitoring in place",
                "bias_testing_procedures": "Regular bias testing using standardized procedures",
                "safety_assessment": "Comprehensive safety assessments conducted",
                "measurement_frequency": "continuous"  # Valid option
            },
            "manage": {
                "risk_treatment_strategy": "Risk mitigation with human oversight",
                "mitigation_controls": "Automated controls with human review escalation",
                "incident_response_plan": "Documented incident response procedures",
                "continuous_monitoring": "24/7 monitoring of AI system performance",
                "improvement_processes": "Regular reviews and improvement cycles"
            }
        }
        
        result = validate_framework_config("nist_ai_rmf", config)
        assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"

    def test_validate_invalid_framework_id(self):
        """Test validation with invalid framework ID."""
        config = {"some_field": "some_value"}
        result = validate_framework_config("invalid_framework", config)
        
        assert len(result["errors"]) == 1
        assert "Unknown regulatory framework" in result["errors"][0]

    def test_multiselect_field_validation(self):
        """Test validation of multiselect fields."""
        config = {
            "article_12": {
                "automatic_logging": True,
                "logging_duration": 12,
                "logged_data_types": ["input_data", "invalid_type", "output_data"],  # Mix of valid and invalid
                "log_traceability": "Valid description"
            }
        }
        
        result = validate_framework_config("eu_ai_act_high_risk", config)
        assert len(result["errors"]) > 0
        
        # Should report the specific invalid option
        error_messages = " ".join(result["errors"])
        assert "invalid_type" in error_messages
        assert "Invalid options" in error_messages

    def test_enforcement_mapping_presence(self):
        """Test that fields with enforcement mappings are correctly defined."""
        # Check EU AI Act fields
        eu_framework = get_framework_template("eu_ai_act_high_risk")
        
        # Find fields that should have enforcement mappings
        human_review_fields = []
        risk_threshold_fields = []
        pii_rule_fields = []
        
        for section in eu_framework.sections:
            for field in section.fields:
                if EnforcementRule.HUMAN_REVIEW in field.enforcement_mapping:
                    human_review_fields.append(field.id)
                if EnforcementRule.RISK_THRESHOLD in field.enforcement_mapping:
                    risk_threshold_fields.append(field.id)
                if EnforcementRule.PII_RULES in field.enforcement_mapping:
                    pii_rule_fields.append(field.id)
        
        # Verify that key fields have appropriate mappings
        assert len(human_review_fields) > 0, "Should have fields that trigger human review"
        assert len(risk_threshold_fields) > 0, "Should have fields that affect risk threshold"
        assert len(pii_rule_fields) > 0, "Should have fields that affect PII rules"
        
        # Check specific expected mappings
        assert "risk_mitigation_measures" in human_review_fields
        assert "human_oversight_design" in human_review_fields

    def test_regulatory_references(self):
        """Test that regulatory references are properly set."""
        eu_framework = get_framework_template("eu_ai_act_high_risk")
        
        # Check that sections have regulatory references
        for section in eu_framework.sections:
            assert section.regulatory_reference != ""
            assert "Article" in section.regulatory_reference
        
        # Check that fields have regulatory references where appropriate
        article_9_section = next(section for section in eu_framework.sections if section.id == "article_9")
        for field in article_9_section.fields:
            if field.regulatory_reference:
                assert "Article" in field.regulatory_reference or "Annex" in field.regulatory_reference
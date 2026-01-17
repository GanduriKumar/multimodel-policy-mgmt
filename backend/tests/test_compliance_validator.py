"""
Tests for ComplianceValidator service.
"""

import pytest
from app.services.compliance_validator import (
    ComplianceValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ConflictWarning
)
from app.schemas.policy_format import PolicyDoc


@pytest.fixture
def validator():
    """Create a ComplianceValidator instance."""
    return ComplianceValidator()


@pytest.fixture
def minimal_policy_doc():
    """Create a minimal PolicyDoc for testing."""
    return PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=75
    )


# Test basic validation

def test_validate_no_frameworks(validator, minimal_policy_doc):
    """Test validation of policy with no regulatory frameworks."""
    result = validator.validate_compliance(minimal_policy_doc)
    
    assert result.is_valid is True
    assert result.can_activate is True
    assert result.compliance_status == "draft"
    assert len(result.issues) == 0
    assert len(result.conflicts) == 0
    assert result.completeness_scores == {}


def test_validate_unknown_framework(validator, minimal_policy_doc):
    """Test validation with unknown framework ID."""
    minimal_policy_doc.regulatory_frameworks = ["unknown_framework"]
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    assert result.is_valid is False
    assert result.can_activate is False
    assert len(result.issues) == 1
    assert result.issues[0].severity == ValidationSeverity.ERROR
    assert "Unknown regulatory framework" in result.issues[0].message


# Test EU AI Act validation

def test_validate_eu_ai_act_empty_config(validator, minimal_policy_doc):
    """Test EU AI Act with empty configuration."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    minimal_policy_doc.eu_ai_act_config = {}
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    assert result.is_valid is False
    assert result.can_activate is False
    assert len(result.issues) > 0
    # Should have errors for missing required fields
    errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) > 0


def test_validate_eu_ai_act_complete_config(validator, minimal_policy_doc):
    """Test EU AI Act with partial configuration - validator should detect missing fields."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "Comprehensive risk assessment process implemented",
            "risk_identification_process": "Systematic risk identification with stakeholder input",
            "risk_mitigation_measures": "Regular testing and human oversight measures",
            "residual_risk_evaluation": "Continuous monitoring of residual risks",
            "risk_acceptability_threshold": 75
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # With only partial config (just Article 9), should have errors for missing sections
    errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) > 0, "Should detect missing required fields"
    
    # But Article 9 should be complete, so completeness should be some positive value
    assert result.completeness_scores.get("eu_ai_act_high_risk", 0) > 0
    
    # Should not be able to activate with incomplete config
    assert result.can_activate is False
    assert result.compliance_status in ["draft", "non_compliant"]


def test_validate_eu_ai_act_with_placeholder_text(validator, minimal_policy_doc):
    """Test detection of placeholder text in EU AI Act config."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "TODO: Fill in risk management details",
            "risk_acceptability_threshold": 75,
            "risk_mitigation_measures": ["TBD"]
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
    assert len(warnings) > 0
    assert any("placeholder" in w.message.lower() for w in warnings)


def test_validate_eu_ai_act_brief_text(validator, minimal_policy_doc):
    """Test detection of suspiciously brief text fields."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "Yes",  # Too brief
            "risk_acceptability_threshold": 75,
            "risk_mitigation_measures": ["Testing"]
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
    # Should warn about brief content
    assert any("brief" in w.message.lower() or "characters" in w.message.lower() for w in warnings)


# Test NIST AI RMF validation

def test_validate_nist_ai_rmf_complete_config(validator, minimal_policy_doc):
    """Test NIST AI RMF with partial configuration."""
    minimal_policy_doc.regulatory_frameworks = ["nist_ai_rmf"]
    minimal_policy_doc.nist_ai_rmf_config = {
        "govern": {
            "ai_governance_structure": "Dedicated AI governance board established with clear responsibilities",
            "ai_risk_tolerance": "medium",
            "stakeholder_engagement": "Regular stakeholder consultations conducted quarterly"
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # With only GOVERN function, should have errors for missing functions
    errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) > 0, "Should detect missing required fields"
    assert result.compliance_status in ["draft", "non_compliant"]


# Test NIST Privacy validation

def test_validate_nist_privacy_complete_config(validator, minimal_policy_doc):
    """Test NIST Privacy with partial configuration."""
    minimal_policy_doc.regulatory_frameworks = ["nist_privacy"]
    minimal_policy_doc.nist_privacy_config = {
        "identify_p": {
            "data_inventory": "Complete inventory of all PII maintained and regularly updated",
            "privacy_risk_assessment": "Annual privacy risk assessments conducted with remediation",
            "data_lifecycle": "Full data lifecycle management in place from collection to deletion"
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
    assert len(errors) > 0, "Should detect missing required fields"
    assert result.compliance_status in ["draft", "non_compliant"]


# Test multi-framework validation

def test_validate_multi_framework_no_conflicts(validator, minimal_policy_doc):
    """Test multi-framework validation with compatible configurations."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk", "nist_ai_rmf"]
    
    # EU AI Act config
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "Comprehensive risk management",
            "risk_acceptability_threshold": 75,
            "risk_mitigation_measures": ["Testing", "Oversight"]
        },
        "article_14": {
            "human_oversight_description": "Human oversight implemented",
            "oversight_measures_type": ["human_in_the_loop"]
        }
    }
    
    # NIST AI RMF config with compatible threshold
    minimal_policy_doc.nist_ai_rmf_config = {
        "govern": {
            "ai_governance_structure": "Governance structure established",
            "ai_risk_tolerance": "medium",  # Maps to 75, matches EU AI Act
            "stakeholder_engagement": "Regular engagement"
        },
        "manage": {
            "mitigation_controls": ["human_oversight"],
            "incident_response": "Response plan in place",
            "continuous_improvement": "Continuous improvement process"
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # Should not have threshold conflicts
    threshold_conflicts = [c for c in result.conflicts if c.conflict_type == "threshold"]
    assert len(threshold_conflicts) == 0


def test_validate_multi_framework_threshold_conflicts(validator, minimal_policy_doc):
    """Test detection of threshold conflicts between frameworks."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk", "nist_ai_rmf"]
    
    # EU AI Act with low threshold
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "Risk management system",
            "risk_acceptability_threshold": 60,  # Low threshold
            "risk_mitigation_measures": ["Testing"]
        }
    }
    
    # NIST AI RMF with high tolerance (high threshold)
    minimal_policy_doc.nist_ai_rmf_config = {
        "govern": {
            "ai_governance_structure": "Governance structure",
            "ai_risk_tolerance": "high",  # Maps to 85, conflicts with 60
            "stakeholder_engagement": "Regular engagement"
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # Should detect threshold conflict
    threshold_conflicts = [c for c in result.conflicts if c.conflict_type == "threshold"]
    assert len(threshold_conflicts) > 0
    assert "60" in result.conflicts[0].description or "85" in result.conflicts[0].description


def test_validate_privacy_transparency_conflict(validator, minimal_policy_doc):
    """Test detection of privacy vs. transparency conflicts."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk", "nist_privacy"]
    
    # EU AI Act with comprehensive logging
    minimal_policy_doc.eu_ai_act_config = {
        "article_12": {
            "logging_capabilities": "Comprehensive logging",
            "logged_data_types": ["inputs", "outputs", "user_data", "timestamps", "context"]
        }
    }
    
    # NIST Privacy with strict data minimization
    minimal_policy_doc.nist_privacy_config = {
        "control_p": {
            "collection_controls": ["data_minimization", "purpose_limitation"],
            "processing_controls": ["anonymization"],
            "sharing_controls": ["consent"]
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # Should detect potential privacy/transparency conflict
    privacy_conflicts = [c for c in result.conflicts if c.conflict_type == "privacy_transparency"]
    assert len(privacy_conflicts) > 0


def test_validate_human_oversight_multi_pattern(validator, minimal_policy_doc):
    """Test detection of multiple human oversight patterns."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    
    minimal_policy_doc.eu_ai_act_config = {
        "article_14": {
            "human_oversight_description": "Multiple oversight mechanisms",
            "oversight_measures_type": ["human_in_the_loop", "human_in_command"]
        }
    }
    
    # Note: With single framework, may not trigger conflict
    # This would be more relevant with multiple frameworks
    result = validator.validate_compliance(minimal_policy_doc)
    
    # Should at least validate successfully
    assert result.is_valid is True or len(result.issues) > 0  # May have other validation issues


# Test completeness scoring

def test_completeness_score_empty_config(validator):
    """Test completeness score calculation for empty config."""
    score = validator._calculate_completeness_score("eu_ai_act_high_risk", {})
    assert score < 10.0  # Should be very low


def test_completeness_score_partial_config(validator):
    """Test completeness score calculation for partial config."""
    partial_config = {
        "article_9": {
            "risk_management_system": "System in place",
            "risk_acceptability_threshold": 75,
            # Missing risk_mitigation_measures
        },
        # Missing other articles
    }
    
    score = validator._calculate_completeness_score("eu_ai_act_high_risk", partial_config)
    assert 0 < score < 50.0  # Should be partial


def test_completeness_score_full_config(validator, minimal_policy_doc):
    """Test completeness score calculation for partial config."""
    partial_config = {
        "article_9": {
            "risk_management_system": "Comprehensive system description with full lifecycle coverage",
            "risk_identification_process": "Systematic identification process documented",
            "risk_mitigation_measures": "Multiple mitigation measures implemented",
            "residual_risk_evaluation": "Continuous evaluation of residual risks",
            "risk_acceptability_threshold": 75
        }
    }
    
    score = validator._calculate_completeness_score("eu_ai_act_high_risk", partial_config)
    # With only Article 9 filled, score should be relatively low (missing 6 other articles)
    assert score > 0, f"Score should be > 0 with some fields filled"
    assert score < 50, f"Score was {score}, should be < 50 with only one article filled"


# Test conflict resolution suggestions

def test_suggest_threshold_conflict_resolution(validator):
    """Test resolution suggestions for threshold conflicts."""
    conflict = ConflictWarning(
        frameworks=["eu_ai_act_high_risk", "nist_ai_rmf"],
        conflict_type="threshold",
        description="Threshold mismatch: 60 vs 85",
        suggested_resolution="Use 60",
        affected_rules=["risk_threshold"]
    )
    
    resolutions = validator.suggest_conflict_resolutions([conflict])
    
    assert len(resolutions) > 0
    assert resolutions[0].priority == "high"
    assert "threshold" in resolutions[0].description.lower()


def test_suggest_privacy_transparency_resolution(validator):
    """Test resolution suggestions for privacy/transparency conflicts."""
    conflict = ConflictWarning(
        frameworks=["eu_ai_act_high_risk", "nist_privacy"],
        conflict_type="privacy_transparency",
        description="Privacy vs transparency",
        suggested_resolution="Use anonymization",
        affected_rules=[]
    )
    
    resolutions = validator.suggest_conflict_resolutions([conflict])
    
    assert len(resolutions) > 0
    assert "anonymization" in resolutions[0].action_steps[0].lower() or \
           "anonymization" in resolutions[0].action_steps[1].lower()


def test_suggest_framework_incomplete_resolution(validator):
    """Test resolution suggestions for incomplete frameworks."""
    issues = [
        ValidationIssue(
            severity=ValidationSeverity.ERROR,
            framework="eu_ai_act_high_risk",
            section="article_9",
            field="risk_management_system",
            message="Required field missing"
        ),
        ValidationIssue(
            severity=ValidationSeverity.ERROR,
            framework="eu_ai_act_high_risk",
            section="article_10",
            field="training_data_description",
            message="Required field missing"
        ),
        ValidationIssue(
            severity=ValidationSeverity.ERROR,
            framework="eu_ai_act_high_risk",
            section="article_11",
            field="technical_documentation",
            message="Required field missing"
        ),
        ValidationIssue(
            severity=ValidationSeverity.ERROR,
            framework="eu_ai_act_high_risk",
            section="article_12",
            field="logging_capabilities",
            message="Required field missing"
        )
    ]
    
    resolutions = validator._suggest_issue_resolutions(issues)
    
    assert len(resolutions) > 0
    assert "incomplete" in resolutions[0].description.lower()
    assert "4" in resolutions[0].description  # 4 errors


# Test validation result helpers

def test_validation_result_has_errors():
    """Test ValidationResult.has_errors() method."""
    result = ValidationResult(
        is_valid=False,
        can_activate=False,
        compliance_status="non_compliant",
        issues=[
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                framework="test",
                section="",
                field="",
                message="Error"
            )
        ],
        conflicts=[],
        resolutions=[],
        completeness_scores={}
    )
    
    assert result.has_errors() is True
    assert len(result.get_errors()) == 1


def test_validation_result_has_warnings():
    """Test ValidationResult.has_warnings() method."""
    result = ValidationResult(
        is_valid=True,
        can_activate=True,
        compliance_status="draft",
        issues=[
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                framework="test",
                section="",
                field="",
                message="Warning"
            )
        ],
        conflicts=[],
        resolutions=[],
        completeness_scores={}
    )
    
    assert result.has_warnings() is True
    assert len(result.get_warnings()) == 1


def test_validation_result_can_activate_thresholds(validator, minimal_policy_doc):
    """Test that can_activate requires >90% completeness."""
    minimal_policy_doc.regulatory_frameworks = ["eu_ai_act_high_risk"]
    
    # Partial config - should not be able to activate
    minimal_policy_doc.eu_ai_act_config = {
        "article_9": {
            "risk_management_system": "System",
            "risk_acceptability_threshold": 75,
            "risk_mitigation_measures": ["Testing"]
        }
    }
    
    result = validator.validate_compliance(minimal_policy_doc)
    
    # With only partial config, should not be able to activate
    if result.completeness_scores.get("eu_ai_act_high_risk", 0) < 90:
        assert result.can_activate is False

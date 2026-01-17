"""
Tests for ComplianceAuditService.
"""

import pytest
from datetime import datetime

from app.services.compliance_audit_service import ComplianceAuditService
from app.schemas.policy_format import PolicyDoc


@pytest.fixture
def audit_service():
    """Create ComplianceAuditService instance."""
    return ComplianceAuditService()


@pytest.fixture
def sample_policy_doc():
    """Create sample PolicyDoc for testing."""
    return PolicyDoc(
        blocked_terms=["weapon", "violence"],
        allowed_sources=["example.com"],
        required_evidence_types=["scientific"],
        pii_rules={"mask_email": True},
        risk_threshold=75,
        regulatory_frameworks=["eu_ai_act_high_risk", "nist_ai_rmf"],
        eu_ai_act_config={
            "article_9": {
                "risk_management_system": "Comprehensive risk management",
                "risk_acceptability_threshold": 75
            }
        },
        nist_ai_rmf_config={
            "govern": {
                "ai_governance_structure": "Governance framework",
                "ai_risk_tolerance": "medium"
            }
        },
        compliance_status="validated",
        requires_human_review=True
    )


# Test build_reasoning_chain

def test_build_reasoning_chain_basic(audit_service):
    """Test basic reasoning chain building."""
    chain = audit_service.build_reasoning_chain(
        decision_path=["load_policy", "check_rules", "make_decision"]
    )
    
    assert "timestamp" in chain
    assert chain["decision_path"] == ["load_policy", "check_rules", "make_decision"]


def test_build_reasoning_chain_with_rules(audit_service):
    """Test reasoning chain with rules evaluated."""
    rules_evaluated = [
        {"rule_id": "rule_1", "triggered": True, "score": 0.95},
        {"rule_id": "rule_2", "triggered": False, "score": 0.2},
        {"rule_id": "rule_3", "triggered": True, "score": 0.88}
    ]
    
    chain = audit_service.build_reasoning_chain(
        rules_evaluated=rules_evaluated
    )
    
    assert "rules_evaluated" in chain
    assert len(chain["rules_evaluated"]) == 3
    assert "rules_summary" in chain
    assert chain["rules_summary"]["total_rules"] == 3
    assert chain["rules_summary"]["triggered_rules"] == 2
    assert set(chain["rules_summary"]["triggered_rule_ids"]) == {"rule_1", "rule_3"}


def test_build_reasoning_chain_with_policy_checks(audit_service):
    """Test reasoning chain with policy checks."""
    policy_checks = [
        {"check": "blocked_terms", "result": False, "matched": ["weapon"]},
        {"check": "pii_detection", "result": True, "detected": []},
        {"check": "evidence_required", "result": False, "missing": ["source"]}
    ]
    
    chain = audit_service.build_reasoning_chain(
        policy_checks=policy_checks
    )
    
    assert "policy_checks" in chain
    assert len(chain["policy_checks"]) == 3
    assert "policy_checks_summary" in chain
    assert chain["policy_checks_summary"]["total_checks"] == 3
    assert chain["policy_checks_summary"]["failed_checks"] == 2
    assert "blocked_terms" in chain["policy_checks_summary"]["failed_check_types"]


def test_build_reasoning_chain_with_intents(audit_service):
    """Test reasoning chain with intent classifications."""
    intent_classifications = [
        {"intent": "weapon_instruction", "score": 0.92, "threshold": 0.7},
        {"intent": "harmless_question", "score": 0.15, "threshold": 0.5}
    ]
    
    chain = audit_service.build_reasoning_chain(
        intent_classifications=intent_classifications
    )
    
    assert "intent_classifications" in chain
    assert len(chain["intent_classifications"]) == 2
    assert "intent_summary" in chain
    assert chain["intent_summary"]["total_intents"] == 2
    assert chain["intent_summary"]["denied_intents"] == 1
    assert chain["intent_summary"]["denied_intent_names"] == ["weapon_instruction"]


def test_build_reasoning_chain_with_risk_factors(audit_service):
    """Test reasoning chain with risk factors."""
    risk_factors = [
        {"factor": "blocked_term_match", "contribution": 40.0},
        {"factor": "high_risk_intent", "contribution": 30.0},
        {"factor": "pii_detected", "contribution": 15.0}
    ]
    
    chain = audit_service.build_reasoning_chain(
        risk_factors=risk_factors
    )
    
    assert "risk_factors" in chain
    assert len(chain["risk_factors"]) == 3
    assert "risk_summary" in chain
    assert chain["risk_summary"]["total_factors"] == 3
    assert chain["risk_summary"]["total_risk_contribution"] == 85.0
    assert chain["risk_summary"]["top_risk_factors"][0]["factor"] == "blocked_term_match"


def test_build_reasoning_chain_with_policy_context(audit_service, sample_policy_doc):
    """Test reasoning chain includes policy context."""
    chain = audit_service.build_reasoning_chain(
        policy_doc=sample_policy_doc
    )
    
    assert "policy_context" in chain
    assert chain["policy_context"]["regulatory_frameworks"] == ["eu_ai_act_high_risk", "nist_ai_rmf"]
    assert chain["policy_context"]["compliance_status"] == "validated"
    assert chain["policy_context"]["requires_human_review"] is True
    assert chain["policy_context"]["risk_threshold"] == 75


# Test extract_regulatory_mappings

def test_extract_regulatory_mappings_eu_ai_act(audit_service, sample_policy_doc):
    """Test extracting EU AI Act regulatory mappings."""
    mappings = audit_service.extract_regulatory_mappings(sample_policy_doc)
    
    assert "eu_ai_act_high_risk" in mappings
    assert "Article 9" in mappings["eu_ai_act_high_risk"]


def test_extract_regulatory_mappings_nist_ai_rmf(audit_service, sample_policy_doc):
    """Test extracting NIST AI RMF regulatory mappings."""
    mappings = audit_service.extract_regulatory_mappings(sample_policy_doc)
    
    assert "nist_ai_rmf" in mappings
    assert "GOVERN" in mappings["nist_ai_rmf"]


def test_extract_regulatory_mappings_with_triggered_rules(audit_service, sample_policy_doc):
    """Test extracting mappings with triggered rules."""
    triggered_rules = [
        {
            "rule_id": "rule_1",
            "triggered": True,
            "enforcement_mapping": {
                "regulatory_reference": "EU AI Act Article 9(2)(a)"
            }
        }
    ]
    
    mappings = audit_service.extract_regulatory_mappings(
        sample_policy_doc,
        triggered_rules
    )
    
    assert "eu_ai_act_high_risk" in mappings
    # Should include both config-based and rule-based mappings
    assert len(mappings["eu_ai_act_high_risk"]) >= 1


def test_extract_regulatory_mappings_empty_policy(audit_service):
    """Test extracting mappings from policy with no frameworks."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=75
    )
    
    mappings = audit_service.extract_regulatory_mappings(policy_doc)
    
    assert mappings == {}


# Test create_policy_version_snapshot

def test_create_policy_version_snapshot(audit_service, sample_policy_doc):
    """Test creating policy version snapshot."""
    snapshot = audit_service.create_policy_version_snapshot(
        policy_doc=sample_policy_doc
    )
    
    assert "snapshot_timestamp" in snapshot
    assert "policy_doc" in snapshot
    assert snapshot["policy_doc"]["blocked_terms"] == ["weapon", "violence"]
    assert snapshot["policy_doc"]["risk_threshold"] == 75
    assert snapshot["policy_doc"]["regulatory_frameworks"] == ["eu_ai_act_high_risk", "nist_ai_rmf"]
    assert snapshot["policy_doc"]["compliance_status"] == "validated"


def test_create_policy_version_snapshot_includes_compliance_configs(audit_service, sample_policy_doc):
    """Test snapshot includes all compliance configurations."""
    snapshot = audit_service.create_policy_version_snapshot(
        policy_doc=sample_policy_doc
    )
    
    assert "eu_ai_act_config" in snapshot["policy_doc"]
    assert snapshot["policy_doc"]["eu_ai_act_config"]["article_9"]["risk_acceptability_threshold"] == 75
    
    assert "nist_ai_rmf_config" in snapshot["policy_doc"]
    assert snapshot["policy_doc"]["nist_ai_rmf_config"]["govern"]["ai_risk_tolerance"] == "medium"


# Test aggregate_engine_scores

def test_aggregate_engine_scores_basic(audit_service):
    """Test basic engine scores aggregation."""
    scores = audit_service.aggregate_engine_scores(
        risk_engine_score=75.5,
        pii_detection_score=20.3
    )
    
    assert scores["risk_engine_score"] == 75.5
    assert scores["pii_detection_score"] == 20.3
    assert "overall_confidence" in scores
    assert scores["overall_confidence"] == pytest.approx((75.5 + 20.3) / 2)
    assert scores["score_count"] == 2


def test_aggregate_engine_scores_with_intent_scores(audit_service):
    """Test aggregation with intent classifier scores."""
    scores = audit_service.aggregate_engine_scores(
        risk_engine_score=80.0,
        intent_classifier_scores={
            "weapon_instruction": 0.92,
            "harmless_question": 0.15
        }
    )
    
    assert "intent_classifier_scores" in scores
    assert scores["intent_classifier_scores"]["weapon_instruction"] == 0.92
    assert scores["intent_classifier_scores"]["harmless_question"] == 0.15


def test_aggregate_engine_scores_all_types(audit_service):
    """Test aggregation with all score types."""
    scores = audit_service.aggregate_engine_scores(
        risk_engine_score=75.0,
        pii_detection_score=20.0,
        intent_classifier_scores={"weapon": 0.9},
        evidence_quality_score=90.0,
        groundedness_score=85.0,
        safety_score=70.0,
        custom_scores={"custom_metric": 65.0}
    )
    
    assert scores["risk_engine_score"] == 75.0
    assert scores["pii_detection_score"] == 20.0
    assert scores["evidence_quality_score"] == 90.0
    assert scores["groundedness_score"] == 85.0
    assert scores["safety_score"] == 70.0
    assert scores["custom_scores"]["custom_metric"] == 65.0
    assert "overall_confidence" in scores
    assert scores["score_count"] == 5  # Doesn't include intent_classifier_scores or custom_scores in overall


def test_aggregate_engine_scores_none_values(audit_service):
    """Test aggregation handles None values properly."""
    scores = audit_service.aggregate_engine_scores(
        risk_engine_score=None,
        pii_detection_score=50.0
    )
    
    assert "risk_engine_score" not in scores
    assert scores["pii_detection_score"] == 50.0


# Test create_compliance_audit_data

def test_create_compliance_audit_data_complete(audit_service, sample_policy_doc):
    """Test creating complete compliance audit data."""
    rules_evaluated = [
        {"rule_id": "rule_1", "triggered": True, "score": 0.95}
    ]
    policy_checks = [
        {"check": "blocked_terms", "result": False, "matched": ["weapon"]}
    ]
    
    audit_data = audit_service.create_compliance_audit_data(
        policy_doc=sample_policy_doc,
        rules_evaluated=rules_evaluated,
        policy_checks=policy_checks,
        decision_path=["load_policy", "evaluate", "decide"],
        engine_scores_kwargs={
            "risk_engine_score": 85.0,
            "pii_detection_score": 10.0
        }
    )
    
    # Check all keys are present
    assert "reasoning_chain" in audit_data
    assert "compliance_frameworks" in audit_data
    assert "regulatory_mappings" in audit_data
    assert "engine_scores" in audit_data
    assert "policy_version_snapshot" in audit_data
    
    # Check data quality
    assert audit_data["compliance_frameworks"] == ["eu_ai_act_high_risk", "nist_ai_rmf"]
    assert "eu_ai_act_high_risk" in audit_data["regulatory_mappings"]
    assert audit_data["engine_scores"]["risk_engine_score"] == 85.0
    assert audit_data["reasoning_chain"]["rules_summary"]["total_rules"] == 1
    assert "policy_doc" in audit_data["policy_version_snapshot"]


def test_create_compliance_audit_data_minimal(audit_service):
    """Test creating audit data with minimal inputs."""
    audit_data = audit_service.create_compliance_audit_data()
    
    # Should still return all keys with default values
    assert "reasoning_chain" in audit_data
    assert "compliance_frameworks" in audit_data
    assert "regulatory_mappings" in audit_data
    assert "engine_scores" in audit_data
    assert "policy_version_snapshot" in audit_data
    
    # Defaults should be empty
    assert audit_data["compliance_frameworks"] == []
    assert audit_data["regulatory_mappings"] == {}


def test_create_compliance_audit_data_with_risk_factors(audit_service, sample_policy_doc):
    """Test audit data creation with risk factors."""
    risk_factors = [
        {"factor": "blocked_term", "contribution": 50.0},
        {"factor": "high_risk_intent", "contribution": 35.0}
    ]
    
    audit_data = audit_service.create_compliance_audit_data(
        policy_doc=sample_policy_doc,
        risk_factors=risk_factors
    )
    
    assert "risk_factors" in audit_data["reasoning_chain"]
    assert audit_data["reasoning_chain"]["risk_summary"]["total_risk_contribution"] == 85.0

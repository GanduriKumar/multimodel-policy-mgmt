"""
Tests for enhanced DecisionLog model with compliance audit fields.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.decision_log import DecisionLog
from app.models.tenant import Tenant
from app.models.request_log import RequestLog


@pytest.fixture
def sample_tenant(db_session: Session):
    """Create a sample tenant for testing."""
    tenant = Tenant(name="test_tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_request_log(db_session: Session, sample_tenant: Tenant):
    """Create a sample request log for testing."""
    request_log = RequestLog(
        tenant_id=sample_tenant.id,
        input_text="Test request",
        input_hash="test_hash"
    )
    db_session.add(request_log)
    db_session.commit()
    db_session.refresh(request_log)
    return request_log


def test_decision_log_basic_fields(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test basic DecisionLog fields still work."""
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["blocked_term:weapon"],
        risk_score=85
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.id is not None
    assert decision.tenant_id == sample_tenant.id
    assert decision.request_log_id == sample_request_log.id
    assert decision.allowed is False
    assert decision.reasons == ["blocked_term:weapon"]
    assert decision.risk_score == 85
    assert decision.created_at is not None


def test_decision_log_reasoning_chain(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test reasoning_chain field."""
    reasoning_chain = {
        "rules_evaluated": [
            {"rule_id": "rule_1", "triggered": True, "score": 0.95},
            {"rule_id": "rule_2", "triggered": False, "score": 0.2}
        ],
        "policy_checks": [
            {"check": "blocked_terms", "result": False, "matched": ["weapon"]}
        ],
        "rules_summary": {
            "total_rules": 2,
            "triggered_rules": 1,
            "triggered_rule_ids": ["rule_1"]
        }
    }
    
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasoning_chain=reasoning_chain
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.reasoning_chain is not None
    assert decision.reasoning_chain["rules_summary"]["total_rules"] == 2
    assert decision.reasoning_chain["rules_summary"]["triggered_rules"] == 1
    assert decision.reasoning_chain["policy_checks"][0]["matched"] == ["weapon"]


def test_decision_log_compliance_frameworks(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test compliance_frameworks field."""
    frameworks = ["eu_ai_act_high_risk", "nist_ai_rmf"]
    
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=True,
        compliance_frameworks=frameworks
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.compliance_frameworks is not None
    assert len(decision.compliance_frameworks) == 2
    assert "eu_ai_act_high_risk" in decision.compliance_frameworks
    assert "nist_ai_rmf" in decision.compliance_frameworks


def test_decision_log_regulatory_mappings(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test regulatory_mappings field."""
    mappings = {
        "eu_ai_act_high_risk": ["Article 9", "Article 14"],
        "nist_ai_rmf": ["GOVERN-1.2", "MEASURE-2.1"]
    }
    
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=True,
        regulatory_mappings=mappings
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.regulatory_mappings is not None
    assert "eu_ai_act_high_risk" in decision.regulatory_mappings
    assert "Article 9" in decision.regulatory_mappings["eu_ai_act_high_risk"]
    assert "GOVERN-1.2" in decision.regulatory_mappings["nist_ai_rmf"]


def test_decision_log_engine_scores(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test engine_scores field."""
    scores = {
        "risk_engine_score": 75.5,
        "pii_detection_score": 20.3,
        "intent_classifier_scores": {"weapon_instruction": 0.85},
        "evidence_quality_score": 90.0,
        "overall_confidence": 67.95
    }
    
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        risk_score=76,
        engine_scores=scores
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.engine_scores is not None
    assert decision.engine_scores["risk_engine_score"] == 75.5
    assert decision.engine_scores["pii_detection_score"] == 20.3
    assert decision.engine_scores["intent_classifier_scores"]["weapon_instruction"] == 0.85


def test_decision_log_policy_version_snapshot(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test policy_version_snapshot field."""
    snapshot = {
        "snapshot_timestamp": datetime.utcnow().isoformat(),
        "policy_version_id": 123,
        "policy_id": 456,
        "version_number": 1,
        "is_active": True,
        "policy_doc": {
            "blocked_terms": ["weapon", "violence"],
            "risk_threshold": 75,
            "regulatory_frameworks": ["eu_ai_act_high_risk"],
            "compliance_status": "validated"
        }
    }
    
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        policy_version_snapshot=snapshot
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    assert decision.policy_version_snapshot is not None
    assert decision.policy_version_snapshot["policy_version_id"] == 123
    assert decision.policy_version_snapshot["policy_doc"]["risk_threshold"] == 75
    assert "eu_ai_act_high_risk" in decision.policy_version_snapshot["policy_doc"]["regulatory_frameworks"]


def test_decision_log_complete_compliance_audit(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test complete compliance audit with all enhanced fields."""
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["blocked_term:weapon", "high_risk_intent"],
        risk_score=85,
        # Enhanced fields
        reasoning_chain={
            "rules_evaluated": [{"rule_id": "block_weapons", "triggered": True}],
            "policy_checks": [{"check": "blocked_terms", "result": False}],
            "decision_path": ["load_policy", "check_blocked_terms", "classify_intent", "calculate_risk", "make_decision"]
        },
        compliance_frameworks=["eu_ai_act_high_risk", "nist_ai_rmf"],
        regulatory_mappings={
            "eu_ai_act_high_risk": ["Article 9", "Article 15"],
            "nist_ai_rmf": ["GOVERN-1.1"]
        },
        engine_scores={
            "risk_engine_score": 85.0,
            "intent_classifier_scores": {"weapon_instruction": 0.92},
            "overall_confidence": 88.5
        },
        policy_version_snapshot={
            "policy_version_id": 1,
            "policy_doc": {
                "blocked_terms": ["weapon"],
                "regulatory_frameworks": ["eu_ai_act_high_risk"]
            }
        }
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    # Verify all fields are persisted correctly
    assert decision.allowed is False
    assert len(decision.reasons) == 2
    assert decision.risk_score == 85
    
    assert len(decision.reasoning_chain["decision_path"]) == 5
    assert len(decision.compliance_frameworks) == 2
    assert "Article 9" in decision.regulatory_mappings["eu_ai_act_high_risk"]
    assert decision.engine_scores["risk_engine_score"] == 85.0
    assert decision.policy_version_snapshot["policy_version_id"] == 1


def test_decision_log_repr_with_frameworks(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test __repr__ includes framework count."""
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=True,
        compliance_frameworks=["eu_ai_act_high_risk", "nist_privacy"]
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    repr_str = repr(decision)
    assert "frameworks=2" in repr_str


def test_decision_log_backward_compatibility(db_session: Session, sample_tenant: Tenant, sample_request_log: RequestLog):
    """Test that decisions without enhanced fields still work."""
    # Create decision with only original fields (no enhanced fields)
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=True,
        reasons=["allowed"],
        risk_score=30
    )
    
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    
    # Enhanced fields should have default values
    assert decision.reasoning_chain == {}
    assert decision.compliance_frameworks == []
    assert decision.regulatory_mappings == {}
    assert decision.engine_scores == {}
    assert decision.policy_version_snapshot == {}

"""
Tests for ReviewRequest and ReviewDecision models.
"""

import pytest
from datetime import datetime, timedelta

from app.models.review_request import ReviewRequest, ReviewStatus, ReviewPriority
from app.models.review_decision import ReviewDecision
from app.models.tenant import Tenant
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog


pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_tenant(db_session):
    """Create sample tenant."""
    tenant = Tenant(name="test_tenant", slug="test_tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_request_log(db_session, sample_tenant):
    """Create sample request log."""
    request_log = RequestLog(
        tenant_id=sample_tenant.id,
        input_text="Test request requiring review",
        input_hash="test_hash_123"
    )
    db_session.add(request_log)
    db_session.commit()
    db_session.refresh(request_log)
    return request_log


@pytest.fixture
def sample_decision_log(db_session, sample_tenant, sample_request_log):
    """Create sample decision log."""
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["high_risk_intent"],
        risk_score=95
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    return decision


# Test ReviewRequest model

def test_create_review_request_basic(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating basic review request."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="High risk score requires human oversight",
        sla_hours=24
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    assert review_request.id is not None
    assert review_request.status == ReviewStatus.PENDING.value
    assert review_request.priority == ReviewPriority.MEDIUM.value
    assert review_request.sla_hours == 24
    assert review_request.sla_deadline is not None
    assert review_request.created_at is not None


def test_review_request_auto_sla_calculation(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test SLA deadline is auto-calculated."""
    created_at = datetime.utcnow()
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        sla_hours=24,
        created_at=created_at
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    expected_deadline = created_at + timedelta(hours=24)
    # Allow 1 second tolerance
    assert abs((review_request.sla_deadline - expected_deadline).total_seconds()) < 1


def test_review_request_with_regulatory_triggers(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test review request with regulatory triggers."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="EU AI Act Article 14 requires human oversight",
        regulatory_triggers=["eu_ai_act_high_risk", "nist_ai_rmf"],
        regulatory_references=["EU AI Act Article 14", "NIST AI RMF MANAGE"]
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    assert len(review_request.regulatory_triggers) == 2
    assert "eu_ai_act_high_risk" in review_request.regulatory_triggers
    assert len(review_request.regulatory_references) == 2
    assert "EU AI Act Article 14" in review_request.regulatory_references


def test_review_request_priority_levels(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test different priority levels."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Critical safety issue",
        priority=ReviewPriority.CRITICAL.value
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    assert review_request.priority == ReviewPriority.CRITICAL.value


def test_review_request_is_overdue_property(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test is_overdue property."""
    # Create review with past deadline
    past_deadline = datetime.utcnow() - timedelta(hours=1)
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        sla_deadline=past_deadline
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    assert review_request.is_overdue is True


def test_review_request_time_remaining_property(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test time_remaining property."""
    future_deadline = datetime.utcnow() + timedelta(hours=12)
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        sla_deadline=future_deadline
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    hours_remaining = review_request.hours_remaining
    assert 11.9 < hours_remaining < 12.1  # Allow small tolerance


def test_review_request_with_decision_context(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test review request with decision context."""
    context = {
        "input_text": "Test request",
        "risk_factors": ["blocked_term", "high_risk_intent"],
        "triggered_rules": ["rule_1", "rule_2"],
        "risk_score": 95
    }
    
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        decision_context=context
    )
    
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    assert review_request.decision_context["risk_score"] == 95
    assert len(review_request.decision_context["risk_factors"]) == 2


# Test ReviewDecision model

def test_create_review_decision_approved(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating approved review decision."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=123,
        reviewer_name="John Reviewer",
        reviewer_email="john@example.com",
        approved=True,
        justification="Risk is acceptable with proper monitoring",
        confidence_level=85
    )
    
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    assert review_decision.id is not None
    assert review_decision.approved is True
    assert review_decision.reviewer_user_id == 123
    assert review_decision.reviewer_name == "John Reviewer"
    assert review_decision.confidence_level == 85


def test_create_review_decision_rejected(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating rejected review decision."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=456,
        approved=False,
        justification="Risk too high, violates safety policy",
        corrective_actions=[
            "Update policy to block this pattern",
            "Add to blocked terms list",
            "Increase risk threshold"
        ]
    )
    
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    assert review_decision.approved is False
    assert len(review_decision.corrective_actions) == 3
    assert "Update policy" in review_decision.corrective_actions[0]


def test_review_decision_with_escalation(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test review decision requiring escalation."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=789,
        approved=False,
        justification="Uncertain, requires senior review",
        requires_escalation=True,
        escalation_reason="Potential legal implications, need legal team review"
    )
    
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    assert review_decision.requires_escalation is True
    assert "legal" in review_decision.escalation_reason.lower()


def test_review_decision_with_compliance_notes(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test review decision with compliance notes."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        regulatory_triggers=["eu_ai_act_high_risk"]
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=111,
        approved=True,
        justification="Compliant with Article 14 requirements",
        compliance_notes="Human oversight provided as required by EU AI Act Article 14. Decision documented for audit trail."
    )
    
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    assert "Article 14" in review_decision.compliance_notes


def test_review_decision_with_risk_assessment(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test review decision with reviewer's risk assessment."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    risk_assessment = {
        "risk_level": "medium",
        "risk_factors": ["potential_misuse", "ambiguous_intent"],
        "mitigation_measures": ["Enhanced monitoring", "User education"],
        "residual_risk": "low"
    }
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=222,
        approved=True,
        justification="Acceptable with mitigation",
        reviewer_risk_assessment=risk_assessment
    )
    
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    assert review_decision.reviewer_risk_assessment["risk_level"] == "medium"
    assert len(review_decision.reviewer_risk_assessment["mitigation_measures"]) == 2


# Test relationship between ReviewRequest and ReviewDecision

def test_review_request_decision_relationship(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test one-to-one relationship between ReviewRequest and ReviewDecision."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=999,
        approved=True,
        justification="Approved"
    )
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_request)
    
    # Test relationship
    assert review_request.review_decision is not None
    assert review_request.review_decision.id == review_decision.id
    assert review_decision.review_request.id == review_request.id


def test_review_request_repr(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test __repr__ method."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        priority=ReviewPriority.HIGH.value
    )
    db_session.add(review_request)
    db_session.commit()
    db_session.refresh(review_request)
    
    repr_str = repr(review_request)
    assert "ReviewRequest" in repr_str
    assert "status='pending'" in repr_str
    assert "priority='high'" in repr_str


def test_review_decision_repr(db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test ReviewDecision __repr__ method."""
    review_request = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    db_session.add(review_request)
    db_session.commit()
    
    review_decision = ReviewDecision(
        review_request_id=review_request.id,
        tenant_id=sample_tenant.id,
        reviewer_user_id=555,
        approved=False,
        justification="Test"
    )
    db_session.add(review_decision)
    db_session.commit()
    db_session.refresh(review_decision)
    
    repr_str = repr(review_decision)
    assert "ReviewDecision" in repr_str
    assert "REJECTED" in repr_str
    assert "reviewer_user_id=555" in repr_str

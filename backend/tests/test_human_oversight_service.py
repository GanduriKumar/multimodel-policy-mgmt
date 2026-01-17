"""
Tests for HumanOversightService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.services.human_oversight_service import HumanOversightService
from app.models.review_request import ReviewRequest, ReviewStatus, ReviewPriority
from app.models.review_decision import ReviewDecision
from app.models.tenant import Tenant
from app.models.request_log import RequestLog
from app.models.decision_log import DecisionLog
from app.models.policy import Policy
from app.models.policy_version import PolicyVersion
from app.schemas.policy_format import PolicyDoc


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
def sample_policy(db_session, sample_tenant):
    """Create sample policy."""
    policy = Policy(
        name="Test Policy",
        slug="test_policy",
        tenant_id=sample_tenant.id
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def sample_request_log(db_session, sample_tenant):
    """Create sample request log."""
    request_log = RequestLog(
        tenant_id=sample_tenant.id,
        input_text="Test request",
        input_hash="test_hash"
    )
    db_session.add(request_log)
    db_session.commit()
    db_session.refresh(request_log)
    return request_log


@pytest.fixture
def sample_decision_log(db_session, sample_tenant, sample_request_log, sample_policy):
    """Create sample decision log."""
    decision = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        policy_id=sample_policy.id,
        allowed=False,
        reasons=["high_risk_score"],
        risk_score=95
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    return decision


@pytest.fixture
def oversight_service(db_session):
    """Create HumanOversightService instance."""
    return HumanOversightService(session=db_session)


# Test create_review_request

def test_create_review_request_basic(oversight_service, db_session, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating basic review request."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="High risk score"
    )
    
    assert review_request.id is not None
    assert review_request.status == ReviewStatus.PENDING.value
    assert review_request.sla_hours == 24  # Default
    assert review_request.sla_deadline is not None
    assert review_request.is_overdue is False


def test_create_review_request_custom_sla(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating review request with custom SLA."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Critical issue",
        sla_hours=4,
        priority=ReviewPriority.CRITICAL.value
    )
    
    assert review_request.sla_hours == 4
    assert review_request.priority == ReviewPriority.CRITICAL.value


def test_create_review_request_with_regulatory_data(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test creating review request with regulatory triggers."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="EU AI Act compliance",
        regulatory_triggers=["eu_ai_act_high_risk"],
        regulatory_references=["Article 14"],
        decision_context={"risk_score": 95}
    )
    
    assert "eu_ai_act_high_risk" in review_request.regulatory_triggers
    assert "Article 14" in review_request.regulatory_references
    assert review_request.decision_context["risk_score"] == 95


# Test should_require_review

def test_should_require_review_explicit_flag(oversight_service, sample_policy):
    """Test should_require_review when requires_human_review is True."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=70,
        requires_human_review=True,
        rules=[],
        outputs={}
    )
    
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=False,
        risk_score=50
    )
    
    assert requires_review is True
    assert "requires_human_review flag is True" in reason


def test_should_require_review_oversight_config(oversight_service, sample_policy):
    """Test should_require_review based on human_oversight_config."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=70,
        human_oversight_config={
            "enabled": True,
            "review_denied_decisions": True,
            "high_risk_threshold": 80
        },
        rules=[],
        outputs={}
    )
    
    # Test denial triggers review
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=False,
        risk_score=50
    )
    
    assert requires_review is True
    assert "review_denied_decisions" in reason


def test_should_require_review_risk_threshold(oversight_service):
    """Test should_require_review based on risk score threshold."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=80,
        human_oversight_config={
            "enabled": True,
            "high_risk_threshold": 80
        },
        rules=[],
        outputs={}
    )
    
    # Risk score above threshold
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=True,
        risk_score=85
    )
    
    assert requires_review is True
    assert "risk score 85 exceeds threshold 80" in reason


def test_should_require_review_eu_ai_act(oversight_service):
    """Test should_require_review for EU AI Act high-risk systems."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=70,
        regulatory_frameworks=["eu_ai_act_high_risk"],
        eu_ai_act_config={
            "is_high_risk_system": True,
            "human_oversight_measures": {
                "enabled": True,
                "oversight_type": "human_in_loop"
            }
        },
        rules=[],
        outputs={}
    )
    
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=False,
        risk_score=70
    )
    
    assert requires_review is True
    assert "EU AI Act Article 14" in reason


def test_should_require_review_nist_ai_rmf(oversight_service):
    """Test should_require_review for NIST AI RMF MANAGE function."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=70,
        regulatory_frameworks=["nist_ai_rmf"],
        nist_ai_rmf_config={
            "manage": {
                "human_ai_configuration": {
                    "enabled": True,
                    "review_high_risk_decisions": True
                }
            }
        },
        rules=[],
        outputs={}
    )
    
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=False,
        risk_score=80
    )
    
    assert requires_review is True
    assert "NIST AI RMF MANAGE" in reason


def test_should_not_require_review(oversight_service):
    """Test should_require_review returns False when no triggers."""
    policy_doc = PolicyDoc(
        blocked_terms=[],
        allowed_sources=[],
        required_evidence_types=[],
        pii_rules={},
        risk_threshold=70,
        requires_human_review=False,
        rules=[],
        outputs={}
    )
    
    requires_review, reason, triggers, references = oversight_service.should_require_review(
        policy_doc=policy_doc,
        decision_allowed=True,
        risk_score=30
    )
    
    assert requires_review is False


# Test assign_review

def test_assign_review(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test assigning review to a reviewer."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    
    updated_request = oversight_service.assign_review(
        review_request_id=review_request.id,
        assigned_to_user_id=123,
        assigned_to_name="Jane Reviewer",
        assigned_to_email="jane@example.com"
    )
    
    assert updated_request.status == ReviewStatus.IN_REVIEW.value
    assert updated_request.assigned_to_user_id == 123
    assert updated_request.assigned_to_name == "Jane Reviewer"
    assert updated_request.assigned_at is not None


# Test complete_review

def test_complete_review_approved(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test completing review with approval."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    
    oversight_service.assign_review(
        review_request_id=review_request.id,
        assigned_to_user_id=123
    )
    
    review_decision = oversight_service.complete_review(
        review_request_id=review_request.id,
        reviewer_user_id=123,
        reviewer_name="John Reviewer",
        reviewer_email="john@example.com",
        approved=True,
        justification="Risk is acceptable",
        confidence_level=90
    )
    
    assert review_decision.approved is True
    assert review_decision.justification == "Risk is acceptable"
    assert review_request.status == ReviewStatus.APPROVED.value
    assert review_request.reviewed_at is not None


def test_complete_review_rejected(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test completing review with rejection."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    
    review_decision = oversight_service.complete_review(
        review_request_id=review_request.id,
        reviewer_user_id=456,
        approved=False,
        justification="Too risky",
        corrective_actions=["Update policy", "Add monitoring"]
    )
    
    assert review_decision.approved is False
    assert review_request.status == ReviewStatus.REJECTED.value
    assert len(review_decision.corrective_actions) == 2


def test_complete_review_with_escalation(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test completing review with escalation."""
    review_request = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    
    review_decision = oversight_service.complete_review(
        review_request_id=review_request.id,
        reviewer_user_id=789,
        approved=False,
        justification="Needs senior review",
        requires_escalation=True,
        escalation_reason="Potential legal issue"
    )
    
    assert review_decision.requires_escalation is True
    assert review_decision.escalation_reason == "Potential legal issue"


# Test get_pending_reviews

def test_get_pending_reviews_basic(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test getting all pending reviews."""
    # Create 2 pending reviews
    oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test 1"
    )
    
    # Create another decision log for second review
    decision2 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=80
    )
    oversight_service.session.add(decision2)
    oversight_service.session.commit()
    
    oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision2.id,
        request_log_id=sample_request_log.id,
        review_reason="Test 2"
    )
    
    pending = oversight_service.get_pending_reviews(tenant_id=sample_tenant.id)
    
    assert len(pending) == 2
    assert all(r.status == ReviewStatus.PENDING.value for r in pending)


def test_get_pending_reviews_assigned_filter(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test filtering pending reviews by assigned user."""
    review1 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Test 1"
    )
    
    oversight_service.assign_review(
        review_request_id=review1.id,
        assigned_to_user_id=123
    )
    
    # Create another unassigned review
    decision2 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=80
    )
    oversight_service.session.add(decision2)
    oversight_service.session.commit()
    
    oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision2.id,
        request_log_id=sample_request_log.id,
        review_reason="Test 2"
    )
    
    assigned_to_123 = oversight_service.get_pending_reviews(
        tenant_id=sample_tenant.id,
        assigned_to_user_id=123
    )
    
    assert len(assigned_to_123) == 1
    assert assigned_to_123[0].assigned_to_user_id == 123


def test_get_pending_reviews_priority_filter(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test filtering pending reviews by priority."""
    oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="High priority",
        priority=ReviewPriority.HIGH.value
    )
    
    high_priority = oversight_service.get_pending_reviews(
        tenant_id=sample_tenant.id,
        priority=ReviewPriority.HIGH.value
    )
    
    assert len(high_priority) == 1
    assert high_priority[0].priority == ReviewPriority.HIGH.value


def test_get_pending_reviews_overdue_only(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test filtering for overdue reviews only."""
    # Create overdue review
    past_deadline = datetime.utcnow() - timedelta(hours=1)
    review1 = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Overdue",
        sla_deadline=past_deadline
    )
    oversight_service.session.add(review1)
    oversight_service.session.commit()
    
    # Create normal review
    decision2 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=80
    )
    oversight_service.session.add(decision2)
    oversight_service.session.commit()
    
    oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision2.id,
        request_log_id=sample_request_log.id,
        review_reason="Normal"
    )
    
    overdue = oversight_service.get_pending_reviews(
        tenant_id=sample_tenant.id,
        overdue_only=True
    )
    
    assert len(overdue) == 1
    assert overdue[0].is_overdue is True


# Test auto_expire_overdue_reviews

def test_auto_expire_overdue_reviews(oversight_service, sample_tenant, sample_decision_log, sample_request_log):
    """Test auto-expiring overdue reviews."""
    # Create overdue review
    past_deadline = datetime.utcnow() - timedelta(hours=2)
    review1 = ReviewRequest(
        tenant_id=sample_tenant.id,
        decision_log_id=sample_decision_log.id,
        request_log_id=sample_request_log.id,
        review_reason="Should expire",
        sla_deadline=past_deadline
    )
    oversight_service.session.add(review1)
    oversight_service.session.commit()
    
    # Create normal review
    decision2 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=80
    )
    oversight_service.session.add(decision2)
    oversight_service.session.commit()
    
    review2 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision2.id,
        request_log_id=sample_request_log.id,
        review_reason="Normal"
    )
    
    expired_count = oversight_service.auto_expire_overdue_reviews(tenant_id=sample_tenant.id)
    
    assert expired_count == 1
    
    # Refresh and check status
    oversight_service.session.refresh(review1)
    assert review1.status == ReviewStatus.EXPIRED.value
    
    # Normal review should still be pending
    oversight_service.session.refresh(review2)
    assert review2.status == ReviewStatus.PENDING.value


# Test get_review_metrics

def test_get_review_metrics_empty(oversight_service, sample_tenant):
    """Test metrics with no reviews."""
    metrics = oversight_service.get_review_metrics(tenant_id=sample_tenant.id)
    
    assert metrics["total_reviews"] == 0
    assert metrics["pending"] == 0
    assert metrics["approved"] == 0
    assert metrics["rejected"] == 0
    assert metrics["expired"] == 0
    assert metrics["overdue"] == 0


def test_get_review_metrics_with_reviews(oversight_service, sample_tenant, sample_request_log):
    """Test metrics with various review states."""
    # Create 3 decisions
    decision1 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=90
    )
    decision2 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=85
    )
    decision3 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=80
    )
    oversight_service.session.add_all([decision1, decision2, decision3])
    oversight_service.session.commit()
    
    # Create 1 pending review
    review1 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision1.id,
        request_log_id=sample_request_log.id,
        review_reason="Pending"
    )
    
    # Create 1 approved review
    review2 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision2.id,
        request_log_id=sample_request_log.id,
        review_reason="Will approve"
    )
    oversight_service.complete_review(
        review_request_id=review2.id,
        reviewer_user_id=123,
        approved=True,
        justification="Approved"
    )
    
    # Create 1 rejected review
    review3 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision3.id,
        request_log_id=sample_request_log.id,
        review_reason="Will reject"
    )
    oversight_service.complete_review(
        review_request_id=review3.id,
        reviewer_user_id=456,
        approved=False,
        justification="Rejected"
    )
    
    metrics = oversight_service.get_review_metrics(tenant_id=sample_tenant.id)
    
    assert metrics["total_reviews"] == 3
    assert metrics["pending"] == 1
    assert metrics["approved"] == 1
    assert metrics["rejected"] == 1
    assert metrics["approval_rate"] == pytest.approx(50.0)  # 1/2 completed = 50%


def test_get_review_metrics_sla_compliance(oversight_service, sample_tenant, sample_request_log):
    """Test SLA compliance rate in metrics."""
    decision1 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=90
    )
    oversight_service.session.add(decision1)
    oversight_service.session.commit()
    
    # Create review and complete within SLA
    review1 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision1.id,
        request_log_id=sample_request_log.id,
        review_reason="Test",
        sla_hours=24
    )
    
    oversight_service.complete_review(
        review_request_id=review1.id,
        reviewer_user_id=123,
        approved=True,
        justification="Quick approval"
    )
    
    metrics = oversight_service.get_review_metrics(tenant_id=sample_tenant.id)
    
    assert metrics["sla_compliance_rate"] == 100.0
    assert metrics["average_response_hours"] is not None
    assert metrics["average_response_hours"] < 24


def test_get_review_metrics_date_range(oversight_service, sample_tenant, sample_request_log):
    """Test metrics with date range filtering."""
    decision1 = DecisionLog(
        tenant_id=sample_tenant.id,
        request_log_id=sample_request_log.id,
        allowed=False,
        reasons=["test"],
        risk_score=90
    )
    oversight_service.session.add(decision1)
    oversight_service.session.commit()
    
    review1 = oversight_service.create_review_request(
        tenant_id=sample_tenant.id,
        decision_log_id=decision1.id,
        request_log_id=sample_request_log.id,
        review_reason="Test"
    )
    
    # Query with date range including today
    start_date = datetime.utcnow() - timedelta(days=1)
    end_date = datetime.utcnow() + timedelta(days=1)
    
    metrics = oversight_service.get_review_metrics(
        tenant_id=sample_tenant.id,
        start_date=start_date,
        end_date=end_date
    )
    
    assert metrics["total_reviews"] == 1




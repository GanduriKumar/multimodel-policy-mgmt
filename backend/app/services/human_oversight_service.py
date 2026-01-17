"""
Human Oversight Service for managing review workflow.

Handles creation, assignment, completion, and SLA tracking of review requests.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.models.review_request import ReviewRequest, ReviewStatus, ReviewPriority
from app.models.review_decision import ReviewDecision
from app.models.decision_log import DecisionLog
from app.schemas.policy_format import PolicyDoc


class HumanOversightService:
    """
    Service for managing human oversight workflow.
    
    Responsibilities:
    - Create review requests for flagged decisions
    - Assign reviews to human reviewers
    - Track SLA compliance (24-hour default)
    - Process review decisions (approve/reject)
    - Auto-expire overdue reviews
    - Generate reviewer metrics
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def create_review_request(
        self,
        *,
        tenant_id: int,
        decision_log_id: int,
        request_log_id: int,
        review_reason: str,
        policy_id: Optional[int] = None,
        policy_version_id: Optional[int] = None,
        regulatory_triggers: Optional[List[str]] = None,
        regulatory_references: Optional[List[str]] = None,
        priority: str = ReviewPriority.MEDIUM.value,
        sla_hours: int = 24,
        decision_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReviewRequest:
        """
        Create a new review request for a flagged decision.
        
        Args:
            tenant_id: Tenant ID
            decision_log_id: ID of decision that triggered review
            request_log_id: ID of original request
            review_reason: Why review is required
            policy_id: Policy ID (optional)
            policy_version_id: Policy version ID (optional)
            regulatory_triggers: Frameworks requiring review
            regulatory_references: Specific articles/controls
            priority: Review priority (low/medium/high/critical)
            sla_hours: SLA in hours (default 24)
            decision_context: Context for reviewer
            metadata: Additional metadata
            
        Returns:
            Created ReviewRequest
        """
        # Calculate SLA deadline
        created_at = datetime.utcnow()
        sla_deadline = created_at + timedelta(hours=sla_hours)
        
        review_request = ReviewRequest(
            tenant_id=tenant_id,
            decision_log_id=decision_log_id,
            request_log_id=request_log_id,
            policy_id=policy_id,
            policy_version_id=policy_version_id,
            status=ReviewStatus.PENDING.value,
            priority=priority,
            review_reason=review_reason,
            regulatory_triggers=regulatory_triggers or [],
            regulatory_references=regulatory_references or [],
            sla_hours=sla_hours,
            created_at=created_at,
            sla_deadline=sla_deadline,
            decision_context=decision_context or {},
            metadata=metadata or {},
        )
        
        self.session.add(review_request)
        self.session.commit()
        self.session.refresh(review_request)
        
        self.logger.info(
            f"Created review request {review_request.id} for decision {decision_log_id} "
            f"with {sla_hours}h SLA (deadline: {sla_deadline})"
        )
        
        return review_request
    
    def should_require_review(
        self,
        policy_doc: PolicyDoc,
        decision_allowed: bool,
        risk_score: Optional[int] = None,
        intent_classifications: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[bool, Optional[str], Optional[List[str]], Optional[List[str]]]:
        """
        Determine if a decision requires human review based on policy configuration.
        
        Args:
            policy_doc: Policy document with compliance configuration
            decision_allowed: Whether decision was allowed
            risk_score: Risk score of decision
            intent_classifications: Intent classification results
            
        Returns:
            Tuple of (requires_review, reason, regulatory_triggers, regulatory_references)
        """
        requires_review = False
        reason = None
        regulatory_triggers = []
        regulatory_references = []
        
        # Check global requires_human_review flag
        if policy_doc.requires_human_review:
            requires_review = True
            reason = "Policy requires human review for all decisions (requires_human_review flag is True)"
        
        # Check human oversight configuration
        oversight_config = policy_doc.human_oversight_config or {}
        
        # Review denied decisions
        if oversight_config.get("review_denied_decisions", False) and not decision_allowed:
            requires_review = True
            reason = "Denied decision requires human review per policy configuration (review_denied_decisions)"
        
        # Review high-risk decisions
        risk_threshold = oversight_config.get("high_risk_threshold")
        if risk_threshold and risk_score and risk_score >= risk_threshold:
            requires_review = True
            reason = f"High risk score ({risk_score}) exceeds threshold ({risk_threshold}) - risk score {risk_score} exceeds threshold {risk_threshold}"
        
        # Review specific intents
        review_intents = oversight_config.get("review_intents", [])
        if review_intents and intent_classifications:
            for classification in intent_classifications:
                if classification.get("intent") in review_intents:
                    requires_review = True
                    reason = f"Intent '{classification.get('intent')}' requires review"
                    break
        
        # Check EU AI Act Article 14 requirements
        if "eu_ai_act_high_risk" in policy_doc.regulatory_frameworks or "EU_AI_ACT" in policy_doc.regulatory_frameworks:
            eu_config = policy_doc.eu_ai_act_config or {}
            
            # Check if it's a high-risk system with human oversight requirements
            is_high_risk = eu_config.get("is_high_risk_system", False)
            oversight_measures = eu_config.get("human_oversight_measures", {})
            oversight_enabled = oversight_measures.get("enabled", False)
            
            if is_high_risk and oversight_enabled:
                requires_review = True
                reason = "EU AI Act Article 14 requires human oversight for high-risk AI systems"
                regulatory_triggers.append("eu_ai_act_high_risk")
                regulatory_references.append("EU AI Act Article 14")
        
        # Check NIST AI RMF MANAGE function
        if "nist_ai_rmf" in policy_doc.regulatory_frameworks or "NIST_AI_RMF" in policy_doc.regulatory_frameworks:
            nist_config = policy_doc.nist_ai_rmf_config or {}
            manage = nist_config.get("manage", {})
            
            # Check for human-AI configuration in MANAGE function
            human_ai_config = manage.get("human_ai_configuration", {})
            if human_ai_config.get("enabled", False) or human_ai_config.get("review_high_risk_decisions", False):
                requires_review = True
                if not reason:
                    reason = "NIST AI RMF MANAGE function requires human oversight"
                regulatory_triggers.append("nist_ai_rmf")
                regulatory_references.append("NIST AI RMF MANAGE")
                regulatory_references.append("NIST AI RMF MANAGE")
        
        return requires_review, reason, regulatory_triggers or None, regulatory_references or None
    
    def assign_review(
        self,
        review_request_id: int,
        assigned_to_user_id: int,
        assigned_to_name: Optional[str] = None,
        assigned_to_email: Optional[str] = None,
        reviewer_user_id: Optional[int] = None  # Backward compatibility
    ) -> ReviewRequest:
        """
        Assign a review request to a specific reviewer.
        
        Args:
            review_request_id: Review request ID
            assigned_to_user_id: User ID of reviewer (or use reviewer_user_id for backward compat)
            assigned_to_name: Name of reviewer (optional)
            assigned_to_email: Email of reviewer (optional)
            reviewer_user_id: Deprecated, use assigned_to_user_id
            
        Returns:
            Updated ReviewRequest
        """
        # Support backward compatibility
        user_id = assigned_to_user_id if assigned_to_user_id is not None else reviewer_user_id
        if user_id is None:
            raise ValueError("Must provide assigned_to_user_id or reviewer_user_id")
        
        review_request = self.session.get(ReviewRequest, review_request_id)
        if not review_request:
            raise ValueError(f"ReviewRequest {review_request_id} not found")
        
        if review_request.status != ReviewStatus.PENDING.value:
            raise ValueError(f"Cannot assign review with status {review_request.status}")
        
        review_request.assigned_to_user_id = user_id
        if assigned_to_name:
            review_request.assigned_to_name = assigned_to_name
        if assigned_to_email:
            review_request.assigned_to_email = assigned_to_email
        review_request.assigned_at = datetime.utcnow()
        review_request.status = ReviewStatus.IN_REVIEW.value
        
        self.session.commit()
        self.session.refresh(review_request)
        
        self.logger.info(f"Assigned review {review_request_id} to user {user_id}")
        
        return review_request
    
    def complete_review(
        self,
        *,
        review_request_id: int,
        reviewer_user_id: int,
        approved: bool,
        justification: str,
        reviewer_name: Optional[str] = None,
        reviewer_email: Optional[str] = None,
        confidence_level: Optional[int] = None,
        corrective_actions: Optional[List[str]] = None,
        requires_escalation: bool = False,
        escalation_reason: Optional[str] = None,
        compliance_notes: Optional[str] = None,
        reviewer_risk_assessment: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReviewDecision:
        """
        Complete a review by recording the reviewer's decision.
        
        Args:
            review_request_id: Review request ID
            reviewer_user_id: User ID of reviewer
            approved: True if approved, False if rejected
            justification: Reviewer's explanation
            reviewer_name: Reviewer name (optional)
            reviewer_email: Reviewer email (optional)
            confidence_level: Confidence in decision (0-100)
            corrective_actions: List of corrective actions if rejected
            requires_escalation: Whether to escalate further
            escalation_reason: Reason for escalation
            compliance_notes: Compliance-related notes
            reviewer_risk_assessment: Reviewer's risk assessment
            metadata: Additional metadata
            
        Returns:
            Created ReviewDecision
        """
        review_request = self.session.get(ReviewRequest, review_request_id)
        if not review_request:
            raise ValueError(f"ReviewRequest {review_request_id} not found")
        
        if review_request.status in [ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value]:
            raise ValueError(f"Review already completed with status {review_request.status}")
        
        # Create review decision
        review_decision = ReviewDecision(
            review_request_id=review_request_id,
            tenant_id=review_request.tenant_id,
            reviewer_user_id=reviewer_user_id,
            reviewer_name=reviewer_name,
            reviewer_email=reviewer_email,
            approved=approved,
            justification=justification,
            confidence_level=confidence_level,
            corrective_actions=corrective_actions,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
            compliance_notes=compliance_notes,
            reviewer_risk_assessment=reviewer_risk_assessment,
            metadata=metadata or {},
        )
        
        # Update review request status
        review_request.status = ReviewStatus.APPROVED.value if approved else ReviewStatus.REJECTED.value
        review_request.completed_at = datetime.utcnow()
        
        self.session.add(review_decision)
        self.session.commit()
        self.session.refresh(review_decision)
        self.session.refresh(review_request)
        
        outcome = "APPROVED" if approved else "REJECTED"
        self.logger.info(f"Review {review_request_id} completed: {outcome} by user {reviewer_user_id}")
        
        return review_decision
    
    def get_pending_reviews(
        self,
        tenant_id: int,
        assigned_to_user_id: Optional[int] = None,
        priority: Optional[str] = None,
        overdue_only: bool = False
    ) -> List[ReviewRequest]:
        """
        Get pending review requests.
        
        Args:
            tenant_id: Tenant ID
            assigned_to_user_id: Filter by assigned reviewer (optional)
            priority: Filter by priority (optional)
            overdue_only: Only return overdue reviews
            
        Returns:
            List of pending ReviewRequests
        """
        query = select(ReviewRequest).where(
            and_(
                ReviewRequest.tenant_id == tenant_id,
                or_(
                    ReviewRequest.status == ReviewStatus.PENDING.value,
                    ReviewRequest.status == ReviewStatus.IN_REVIEW.value
                )
            )
        )
        
        if assigned_to_user_id:
            query = query.where(ReviewRequest.assigned_to_user_id == assigned_to_user_id)
        
        if priority:
            query = query.where(ReviewRequest.priority == priority)
        
        if overdue_only:
            query = query.where(ReviewRequest.sla_deadline < datetime.utcnow())
        
        query = query.order_by(ReviewRequest.sla_deadline.asc())
        
        return list(self.session.execute(query).scalars().all())
    
    def auto_expire_overdue_reviews(self, tenant_id: int) -> int:
        """
        Auto-expire reviews that are past their SLA deadline.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Number of reviews expired
        """
        overdue_reviews = self.session.execute(
            select(ReviewRequest).where(
                and_(
                    ReviewRequest.tenant_id == tenant_id,
                    ReviewRequest.status == ReviewStatus.PENDING.value,
                    ReviewRequest.sla_deadline < datetime.utcnow()
                )
            )
        ).scalars().all()
        
        count = 0
        for review in overdue_reviews:
            review.status = ReviewStatus.EXPIRED.value
            review.completed_at = datetime.utcnow()
            count += 1
        
        if count > 0:
            self.session.commit()
            self.logger.warning(f"Auto-expired {count} overdue reviews for tenant {tenant_id}")
        
        return count
    
    def get_review_metrics(
        self,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get review metrics for reporting.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            
        Returns:
            Dict with metrics
        """
        query = select(ReviewRequest).where(ReviewRequest.tenant_id == tenant_id)
        
        if start_date:
            query = query.where(ReviewRequest.created_at >= start_date)
        if end_date:
            query = query.where(ReviewRequest.created_at <= end_date)
        
        reviews = list(self.session.execute(query).scalars().all())
        
        total = len(reviews)
        pending = sum(1 for r in reviews if r.status == ReviewStatus.PENDING.value)
        in_review = sum(1 for r in reviews if r.status == ReviewStatus.IN_REVIEW.value)
        approved = sum(1 for r in reviews if r.status == ReviewStatus.APPROVED.value)
        rejected = sum(1 for r in reviews if r.status == ReviewStatus.REJECTED.value)
        expired = sum(1 for r in reviews if r.status == ReviewStatus.EXPIRED.value)
        
        overdue = sum(1 for r in reviews if r.is_overdue)
        
        # Calculate average response time for completed reviews
        completed_reviews = [r for r in reviews if r.completed_at]
        if completed_reviews:
            response_times = [
                (r.completed_at - r.created_at).total_seconds() / 3600
                for r in completed_reviews
            ]
            avg_response_hours = sum(response_times) / len(response_times)
        else:
            avg_response_hours = None
        
        # SLA compliance rate
        sla_compliant = sum(
            1 for r in completed_reviews
            if r.completed_at and r.completed_at <= r.sla_deadline
        )
        sla_compliance_rate = (sla_compliant / len(completed_reviews) * 100) if completed_reviews else None
        
        return {
            "total_reviews": total,
            "pending": pending,
            "in_review": in_review,
            "approved": approved,
            "rejected": rejected,
            "expired": expired,
            "overdue": overdue,
            "average_response_hours": avg_response_hours,
            "sla_compliance_rate": sla_compliance_rate,
            "approval_rate": (approved / (approved + rejected) * 100) if (approved + rejected) > 0 else None,
        }

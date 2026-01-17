"""Create a sample policy with compliance configurations for testing."""

import os
import sys

# Ensure we're running from the backend directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if not script_dir.endswith('backend'):
    # If running from root, change to backend directory
    backend_dir = os.path.join(script_dir, 'backend') if os.path.exists(os.path.join(script_dir, 'backend')) else script_dir
    os.chdir(backend_dir)
    print(f"Changed working directory to: {os.getcwd()}")

from app.db.session import SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

# Check if policy already exists and update instead of create
existing_policy = None
try:
    # Try to get by ID first
    existing_policy = repo.get_policy_by_id(1)
except Exception:
    pass

if existing_policy:
    print(f'Found existing policy id={existing_policy.id}, will update version')
    policy = existing_policy
else:
    # Create a new policy
    policy = repo.create_policy(
        tenant_id=1,
        name='AI Content Safety Policy',
        slug='ai-content-safety',
        description='Comprehensive policy with regulatory compliance'
    )

# Create a version with comprehensive compliance configurations
policy_doc = {
    'blocked_terms': ['weapon', 'violence', 'hack'],
    'allowed_sources': ['trusted.com', 'verified.org'],
    'risk_threshold': 70,
    'conservative_mode': True,
    'regulatory_frameworks': ['EU_AI_ACT', 'NIST_AI_RMF', 'NIST_PRIVACY'],
    
    # PII rules configuration
    'pii_rules': {
        'email': {'action': 'mask', 'enabled': True},
        'ssn': {'action': 'block', 'enabled': True},
        'credit_card': {'action': 'redact', 'enabled': True},
        'phone': {'action': 'mask', 'enabled': True},
    },
    
    # EU AI Act Articles 9-15 Compliance Configuration
    'eu_ai_act_config': {
        # Article 9: Risk Management System
        'risk_management_system': 'Comprehensive risk identification and mitigation framework with pattern-based and intent analysis',
        'risk_acceptability_threshold': 70,
        'continuous_risk_monitoring': True,
        'risk_identification_measures': 'Automated risk scoring with pattern detection, intent classification, and violence detection',
        'iterative_risk_management': 'Continuous policy updates based on decision analytics and quarterly compliance reviews',
        
        # Article 10: Data and Data Governance
        'data_quality_measures': 'Automated validation, human review workflows, and evidence-based decision making',
        'data_governance_policies': 'Source validation, citation requirements, and evidence quality checks',
        'training_data_relevance': 'N/A - System uses rule-based policies with pattern matching, not ML training',
        'bias_detection_mitigation': 'Intent classification tested across prompt variations; fairness metrics monitored',
        
        # Article 11: Technical Documentation
        'technical_documentation': 'Complete system architecture documentation with API specs and decision flow diagrams',
        'system_design_documentation': 'FastAPI backend with PolicyEngine, RiskEngine, DecisionService, and HumanOversightService architecture',
        'performance_metrics_documentation': 'Decision latency (<100ms), risk score accuracy (95%+), false positive/negative rates tracked',
        'change_management_procedures': 'Version-controlled policies with rollback capability, change audit trail, and approval workflow',
        
        # Article 12: Record-Keeping
        'record_keeping_automated': True,
        'audit_log_retention_period': '5 years',
        'tamper_proof_logging_mechanism': 'SHA-256 hashing of decision logs with immutable timestamps',
        'log_configuration_details': 'All decisions logged to RequestLog and DecisionLog tables with tenant_id, policy_id, risk_score, reasons, and timestamps',
        
        # Article 13: Transparency and Provision of Information
        'user_transparency_measures': 'Risk scores and detailed reasons provided for all decisions via API response',
        'purpose_and_limitations_disclosure': 'Policy purpose: content safety; Limitations: pattern-based detection may have false positives/negatives',
        'interpretability_documentation': 'Explainable decision reasons with evidence citations, risk factor breakdown, and intent scores',
        
        # Article 14: Human Oversight
        'human_oversight_required': True,
        'human_oversight_measures': 'Human review workflow for high-risk decisions via HumanOversightService and ReviewRequest system',
        'override_capabilities': 'Authorized reviewers can approve/reject decisions, update policy rules, and modify risk thresholds',
        'human_in_the_loop_config': 'Automatic review assignment for decisions exceeding risk threshold or flagged by conservative mode',
        
        # Article 15: Accuracy, Robustness and Cybersecurity
        'accuracy_robustness_cybersecurity': 'Multi-layer security, input validation, and continuous testing',
        'accuracy_metrics_definition': 'Precision: 95%+, Recall: 92%+, F1: 93.5%+ for harmful content detection',
        'robustness_testing_procedures': 'Adversarial testing, edge case validation, prompt injection testing, and fuzzing',
        'cybersecurity_measures_documentation': 'Input validation, SQL injection prevention, rate limiting, HMAC-SHA256 API authentication, TLS encryption',
    },
    
    # NIST AI RMF Four Core Functions Configuration
    'nist_ai_rmf_config': {
        # GOVERN: Accountability and Governance
        'governance_structures': 'Cross-functional AI governance board with quarterly reviews and executive oversight',
        'accountability_mechanisms': 'Clear ownership (PolicyEngine team), escalation paths, and incident response procedures',
        'risk_tolerance_levels': {'low': 30, 'medium': 60, 'high': 90},
        'trustworthiness_metrics': True,
        
        # MAP: Context and Risk Identification
        'system_context_documentation': 'Content safety system for GenAI applications protecting against harmful outputs and policy violations',
        'impact_assessments': 'Privacy impact: Medium, Safety impact: High, Fairness impact: High, Societal impact: High',
        'stakeholder_analysis': 'End users (protected from harmful content), content moderators, application developers, regulatory bodies',
        
        # MEASURE: Metrics and Monitoring
        'fairness_metrics_definition': 'Demographic parity and equalized odds across user groups; intent detection accuracy consistency',
        'bias_testing_results': 'Intent detection accuracy: 95%+ across prompt variations; baseline established Q4 2025',
        'performance_monitoring_config': 'Real-time risk score distribution, decision latency tracking, error rate monitoring, and compliance dashboards',
        
        # MANAGE: Risk Treatment and Continuous Improvement
        'risk_treatment_plans': 'High-risk decisions require human review; extreme risk scores (>90) trigger automatic blocking',
        'incident_response_procedures': 'False positive review process, policy update workflow, escalation to governance board for systemic issues',
        'continuous_improvement_process': 'Weekly analytics review, monthly policy tuning, quarterly compliance audits, and annual framework updates',
    },
    
    # NIST Privacy Framework Five Core Functions Configuration
    'nist_privacy_config': {
        # IDENTIFY-P: Data Processing Inventory
        'data_inventory': 'Complete data processing inventory maintained with data flow diagrams and DPIAs',
        'data_processing_inventory': {
            'user_prompts': {'purpose': 'Content safety analysis', 'retention': '90 days', 'legal_basis': 'Legitimate interest', 'categories': ['text input']},
            'llm_responses': {'purpose': 'Post-generation validation', 'retention': '90 days', 'legal_basis': 'Legitimate interest', 'categories': ['generated text']},
            'decision_logs': {'purpose': 'Audit, compliance, and analytics', 'retention': '5 years', 'legal_basis': 'Legal obligation', 'categories': ['decision metadata', 'risk scores']},
        },
        'data_processing_purposes': 'Content safety enforcement, regulatory compliance reporting, policy optimization, and threat intelligence',
        'privacy_risk_assessments': 'PIA conducted Q4 2025; Risk level: Medium; Mitigation: PII detection, masking, tenant isolation, and encryption',
        'pii_identification_rules': 'Email, SSN, credit card, phone number patterns with 95%+ detection accuracy via regex patterns',
        
        # GOVERN-P: Privacy Governance
        'privacy_governance': 'Privacy-by-design and privacy-by-default principles embedded in system architecture',
        'privacy_governance_policies': 'Privacy board reviews quarterly; DPO assigned; GDPR/CCPA compliance procedures documented',
        'data_minimization_procedures': 'Only essential data collected (prompt text, risk metadata); no user identifiers or session tracking',
        'individual_rights_management': 'Data subject rights (access, deletion, portability) requests handled within 30 days via support portal',
        
        # CONTROL-P: Data Lifecycle Controls
        'pii_controls': {'detection': True, 'masking': True, 'encryption': True},
        'data_lifecycle_controls': {
            'collection': 'Minimal data collection via API; explicit consent for audit log retention',
            'retention': '90 days for decisions (configurable), 5 years for compliance audit logs',
            'deletion': 'Automated purge after retention period; secure deletion with data wiping',
            'access': 'Role-based access control (RBAC) with MFA and audit logging for PII access',
        },
        'pii_detection_masking_config': 'Automated PII detection in risk_engine with configurable masking/blocking/redaction rules',
        'pii_access_controls': 'Restricted to compliance team and DPO; MFA required; all access logged',
        'data_sharing_limitations': 'No third-party sharing; strict tenant isolation; cross-tenant access prevented by design',
        
        # COMMUNICATE-P: Privacy Notices and Transparency
        'transparency_notices': 'Clear privacy notices provided to users via API documentation and policy metadata',
        'privacy_notices_published': 'Privacy policy available at /privacy endpoint; last updated December 2025',
        'consent_mechanisms': 'API usage implies consent to content analysis; explicit opt-in for audit log retention beyond 90 days',
        'privacy_training_program': 'Annual privacy and data protection training for all personnel handling personal data',
        
        # PROTECT-P: Technical Safeguards
        'technical_safeguards': 'Encryption at rest (AES-256), in transit (TLS 1.3), database-level encryption, and key rotation',
        'data_security_measures': 'HMAC-SHA256 API key authentication, rate limiting (100 req/min), SQL injection prevention, input validation, and WAF',
        'privacy_incident_response': 'Breach notification within 72 hours per GDPR; incident response team with runbooks; post-incident reviews',
        'automated_pii_protection_enforced': 'PII detection rules active in risk engine; automatic redaction in logs (phase 2 implementation)',
    },
    
    # Human oversight configuration
    'requires_human_review': True,
    'human_oversight_config': {
        'triggers': ['risk_score >= 70', 'conservative_mode_violation', 'manual_escalation'],
        'sla_hours': 24,
        'escalation_procedures': 'Tier 1: Content moderator review; Tier 2: Senior reviewer; Tier 3: Governance board',
        'override_permissions': ['content_moderator', 'senior_reviewer', 'admin'],
    },
    
    # Compliance status
    'compliance_status': 'validated',
    'compliance_metadata': {
        'last_validated': '2026-01-17',
        'validator': 'Compliance Team',
        'next_review_date': '2026-04-17',
        'validation_notes': 'Comprehensive compliance configuration aligned with EU AI Act, NIST AI RMF, and NIST Privacy Framework',
    },
}

version = repo.add_version(policy_id=policy.id, document=policy_doc, is_active=True)

print(f'✓ Created policy id={policy.id}, slug={policy.slug}')
print(f'✓ Created version {version.version} (id={version.id})')
print(f'✓ Compliance frameworks: {policy_doc["regulatory_frameworks"]}')
print(f'✓ Database location: {os.path.abspath("app.db")}')
print('\nPolicy is ready! Restart your backend server to use it.')

db.close()

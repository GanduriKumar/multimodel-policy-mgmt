"""Create a sample policy with compliance configurations for testing."""

from app.db.session import SessionLocal
from app.repos.policy_repo import SqlAlchemyPolicyRepo

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

# Create a policy
policy = repo.create_policy(
    tenant_id=1,
    name='AI Content Safety Policy',
    slug='ai-content-safety',
    description='Comprehensive policy with regulatory compliance'
)

# Create a version with compliance configurations
policy_doc = {
    'blocked_terms': ['weapon', 'violence', 'hack'],
    'allowed_sources': ['trusted.com', 'verified.org'],
    'risk_threshold': 70,
    'conservative_mode': True,
    'regulatory_frameworks': ['EU_AI_ACT', 'NIST_AI_RMF', 'NIST_PRIVACY'],
    'eu_ai_act_config': {
        'risk_management_system': 'Comprehensive risk identification and mitigation framework',
        'risk_acceptability_threshold': 70,
        'continuous_risk_monitoring': True,
        'data_quality_measures': 'Automated validation and human review',
        'technical_documentation': 'Complete system documentation maintained',
        'record_keeping_automated': True,
        'human_oversight_required': True,
        'accuracy_robustness_cybersecurity': 'Multi-layer security and testing'
    },
    'nist_ai_rmf_config': {
        'governance_structures': 'Cross-functional AI governance board',
        'accountability_mechanisms': 'Clear ownership and escalation paths',
        'risk_tolerance_levels': {'low': 30, 'medium': 60, 'high': 90},
        'trustworthiness_metrics': True
    },
    'nist_privacy_config': {
        'data_inventory': 'Complete data processing inventory maintained',
        'privacy_governance': 'Privacy-by-design and privacy-by-default',
        'pii_controls': {'detection': True, 'masking': True, 'encryption': True},
        'transparency_notices': 'Clear privacy notices provided to users'
    },
    'requires_human_review': True,
    'compliance_status': 'validated'
}

version = repo.add_version(policy_id=policy.id, document=policy_doc, is_active=True)

print(f'Created policy id={policy.id}, slug={policy.slug}')
print(f'Created version {version.version} (id={version.id})')
print(f'Compliance frameworks: {policy_doc["regulatory_frameworks"]}')

db.close()

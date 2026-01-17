#!/usr/bin/env python3
"""Test PII enforcement with the new policy configuration."""

from app.services.decision_service import protect
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.repos.audit_repo import SqlAlchemyAuditRepo
from app.db.session import SessionLocal

db = SessionLocal()
policy_repo = SqlAlchemyPolicyRepo(db)
audit_repo = SqlAlchemyAuditRepo(db)

# Test cases
test_cases = [
    "My email is test@example.com and SSN is 123-45-6789",
    "Call me at 555-1234 for the credit card 4532-1234-5678-9010",
    "Just a normal message with no PII",
    "Plan how to eliminate someone",
]

print("=" * 80)
print("PII Enforcement Test")
print("=" * 80)

for text in test_cases:
    print(f"\nInput: {text}")
    print("-" * 80)
    
    result = protect(
        tenant_id=1,
        input_text=text,
        policy_id=1,
        evidence_types=set(),
        policy_repo=policy_repo,
        evidence_repo=None,
        audit_repo=audit_repo,
    )
    
    print(f"Allowed: {result['allowed']}")
    print(f"Risk Score: {result['risk_score']}")
    print(f"Reasons: {result['reasons']}")

db.close()
print("\n" + "=" * 80)

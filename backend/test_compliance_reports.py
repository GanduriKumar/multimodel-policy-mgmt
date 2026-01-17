#!/usr/bin/env python3
"""Test compliance reporting with comprehensive policy configuration."""

from app.services.eu_ai_act_reporter import EUAIActReporter
from app.services.nist_ai_rmf_reporter import NISTAIRMFReporter
from app.services.nist_privacy_reporter import NISTPrivacyReporter
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.schemas.policy_format import PolicyDoc
from app.db.session import SessionLocal

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

# Get policy
policy_obj = repo.get_policy_by_id(1)
if not policy_obj:
    print("Policy not found!")
    db.close()
    exit(1)

# Get active version
version = repo.get_active_version(policy_obj.id)
if not version:
    print("No active version found!")
    db.close()
    exit(1)

# Build PolicyDoc with metadata
policy_dict = version.document.copy()
policy_dict['id'] = policy_obj.id
policy_dict['name'] = policy_obj.name
policy_dict['version'] = version.version

policy_doc = PolicyDoc(**policy_dict)

print("=" * 80)
print(f"Compliance Report Test - Policy: {policy_doc.name}")
print("=" * 80)

# Generate EU AI Act report
print("\n1. EU AI Act Report")
print("-" * 80)
eu_reporter = EUAIActReporter(db)
eu_report = eu_reporter.generate_report(policy_doc, tenant_id=1)
print(f"Overall Status: {eu_report.overall_status}")
print(f"Compliance Score: {eu_report.compliance_score:.1f}%")
print(f"Articles Assessment:")
for article in eu_report.articles:
    print(f"  Article {article.article_number}: {article.status} ({len(article.evidence)} evidence)")

# Generate NIST AI RMF report
print("\n2. NIST AI RMF Report")
print("-" * 80)
nist_rmf_reporter = NISTAIRMFReporter(db)
nist_rmf_report = nist_rmf_reporter.generate_report(policy_doc, tenant_id=1)
print(f"Overall Status: {nist_rmf_report.overall_status}")
print(f"Compliance Score: {nist_rmf_report.compliance_score:.1f}%")
print(f"Functions Assessment:")
for func in nist_rmf_report.functions:
    print(f"  {func.function_name}: {func.status} ({len(func.categories)} categories)")

# Generate NIST Privacy report
print("\n3. NIST Privacy Framework Report")
print("-" * 80)
nist_privacy_reporter = NISTPrivacyReporter(db)
nist_privacy_report = nist_privacy_reporter.generate_report(policy_doc, tenant_id=1)
print(f"Overall Status: {nist_privacy_report.overall_status}")
print(f"Compliance Score: {nist_privacy_report.compliance_score:.1f}%")
print(f"Functions Assessment:")
for func in nist_privacy_report.functions:
    print(f"  {func.function_name}: {func.status} ({len(func.categories)} categories)")

print("\n" + "=" * 80)
print("Summary:")
print(f"  EU AI Act:      {eu_report.compliance_score:.1f}% compliant")
print(f"  NIST AI RMF:    {nist_rmf_report.compliance_score:.1f}% compliant")
print(f"  NIST Privacy:   {nist_privacy_report.compliance_score:.1f}% compliant")
print("=" * 80)

db.close()

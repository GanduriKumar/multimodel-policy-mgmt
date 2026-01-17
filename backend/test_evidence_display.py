#!/usr/bin/env python3
"""Test that regulatory reports display evidence details in HTML and CSV formats."""

from dataclasses import asdict
from pathlib import Path
from app.services.eu_ai_act_reporter import EUAIActReporter
from app.services.nist_ai_rmf_reporter import NISTAIRMFReporter
from app.services.nist_privacy_reporter import NISTPrivacyReporter
from app.services.reports.compliance_renderers import compliance_to_html, compliance_to_csv
from app.repos.policy_repo import SqlAlchemyPolicyRepo
from app.schemas.policy_format import PolicyDoc
from app.db.session import SessionLocal

db = SessionLocal()
repo = SqlAlchemyPolicyRepo(db)

# Get policy
policy_obj = repo.get_policy_by_id(1)
if not policy_obj:
    print("❌ Policy not found!")
    db.close()
    exit(1)

version = repo.get_active_version(policy_obj.id)
if not version:
    print("❌ No active version found!")
    db.close()
    exit(1)

policy_dict = version.document.copy()
policy_dict['id'] = policy_obj.id
policy_dict['name'] = policy_obj.name
policy_dict['version'] = version.version
policy_doc = PolicyDoc(**policy_dict)

print("=" * 80)
print("Testing Evidence Display in Regulatory Reports")
print("=" * 80)

# Test EU AI Act Report
print("\n1. Testing EU AI Act Report")
print("-" * 80)
eu_reporter = EUAIActReporter(db)
eu_report = eu_reporter.generate_report(policy_doc, tenant_id=1)

# Convert to dict for rendering
report_dict = asdict(eu_report)

# Generate HTML
html_output = compliance_to_html(report_dict)
print(f"✓ HTML generated: {len(html_output)} characters")

# Check for evidence in HTML
evidence_checks = [
    ('evidence' in html_output.lower(), "Evidence mentioned in HTML"),
    ('Evidence Items:' in html_output, "Evidence items section present"),
    ('<li><strong>' in html_output, "Evidence list items present"),
]

for check, description in evidence_checks:
    if check:
        print(f"  ✓ {description}")
    else:
        print(f"  ✗ {description} - MISSING!")

# Count evidence items displayed
evidence_count = html_output.count('Evidence Items:')
print(f"  → Evidence sections found: {evidence_count}")

# Save HTML
output_dir = Path("test_outputs")
output_dir.mkdir(exist_ok=True)
html_file = output_dir / "eu_ai_act_evidence_test.html"
html_file.write_text(html_output, encoding='utf-8')
print(f"  → Saved to: {html_file}")

# Generate CSV
csv_output = compliance_to_csv(report_dict)
print(f"\n✓ CSV generated: {len(csv_output)} bytes")

# Check for evidence in CSV
csv_text = csv_output.decode('utf-8')
csv_checks = [
    ('Evidence Details' in csv_text, "Evidence Details column present"),
    ('configuration' in csv_text or 'threshold' in csv_text, "Evidence types present"),
]

for check, description in csv_checks:
    if check:
        print(f"  ✓ {description}")
    else:
        print(f"  ✗ {description} - MISSING!")

# Save CSV
csv_file = output_dir / "eu_ai_act_evidence_test.csv"
csv_file.write_bytes(csv_output)
print(f"  → Saved to: {csv_file}")

# Test NIST AI RMF Report
print("\n2. Testing NIST AI RMF Report")
print("-" * 80)
nist_rmf_reporter = NISTAIRMFReporter(db)
nist_rmf_report = nist_rmf_reporter.generate_report(policy_doc, tenant_id=1)

report_dict = asdict(nist_rmf_report)
html_output = compliance_to_html(report_dict)
print(f"✓ HTML generated: {len(html_output)} characters")

# Check for category evidence
category_checks = [
    ('Categories:' in html_output, "Categories section present"),
    ('Evidence:' in html_output, "Evidence subsection present"),
]

for check, description in category_checks:
    if check:
        print(f"  ✓ {description}")
    else:
        print(f"  ✗ {description} - MISSING!")

html_file = output_dir / "nist_ai_rmf_evidence_test.html"
html_file.write_text(html_output, encoding='utf-8')
print(f"  → Saved to: {html_file}")

csv_output = compliance_to_csv(report_dict)
csv_text = csv_output.decode('utf-8')
print(f"\n✓ CSV generated: {len(csv_output)} bytes")

if 'Category Evidence' in csv_text:
    print(f"  ✓ Category Evidence column present")
else:
    print(f"  ✗ Category Evidence column - MISSING!")

csv_file = output_dir / "nist_ai_rmf_evidence_test.csv"
csv_file.write_bytes(csv_output)
print(f"  → Saved to: {csv_file}")

# Test NIST Privacy Report
print("\n3. Testing NIST Privacy Framework Report")
print("-" * 80)
nist_privacy_reporter = NISTPrivacyReporter(db)
nist_privacy_report = nist_privacy_reporter.generate_report(policy_doc, tenant_id=1)

report_dict = asdict(nist_privacy_report)
html_output = compliance_to_html(report_dict)
print(f"✓ HTML generated: {len(html_output)} characters")

if 'Evidence:' in html_output:
    print(f"  ✓ Evidence subsection present")
else:
    print(f"  ✗ Evidence subsection - MISSING!")

html_file = output_dir / "nist_privacy_evidence_test.html"
html_file.write_text(html_output, encoding='utf-8')
print(f"  → Saved to: {html_file}")

csv_output = compliance_to_csv(report_dict)
csv_file = output_dir / "nist_privacy_evidence_test.csv"
csv_file.write_bytes(csv_output)
print(f"  → Saved to: {csv_file}")

print("\n" + "=" * 80)
print("✓ All tests completed!")
print(f"✓ Test outputs saved to: {output_dir.absolute()}")
print("=" * 80)

db.close()

# Enhanced Regulatory Reports - User Guide

## What Changed?

Regulatory compliance reports now display **full evidence details** instead of just showing counts. This makes it easier to understand the basis for compliance assessments and prepare for audits.

## How to Generate Reports

### Via API

Generate reports for any policy:

```bash
# EU AI Act Report
curl "http://localhost:8000/api/reports/eu-ai-act/1?format=html" -H "X-API-Key: test-key" > report.html

# NIST AI RMF Report
curl "http://localhost:8000/api/reports/nist-ai-rmf/1?format=html" -H "X-API-Key: test-key" > report.html

# NIST Privacy Framework Report
curl "http://localhost:8000/api/reports/nist-privacy/1?format=html" -H "X-API-Key: test-key" > report.html
```

### Available Formats
- `format=html` - Interactive HTML report (default)
- `format=csv` - Spreadsheet-compatible CSV
- `format=json` - Machine-readable JSON

## What You'll See

### EU AI Act Reports

**Before:**
```
Article 9: Risk Management System
Status: Compliant
Evidence: 5 items
```

**Now:**
```
Article 9: Risk Management System
Status: Compliant
Evidence:
  5 Evidence Items:
  • configuration: risk_management_system = Comprehensive risk identification and mitigation framework...
  • threshold: risk_acceptability_threshold = 70
  • measures: risk_identification_measures = Automated risk scoring with pattern detection...
  • monitoring: continuous_risk_monitoring = True
  • process: iterative_risk_management = Continuous policy updates based on analytics...
```

### NIST Reports

**Before:**
```
GOVERN Function
Status: Compliant
Categories: 4 categories
```

**Now:**
```
GOVERN Function
Status: Compliant
Categories:
  4 Categories:
  • Governance Structures (documented)
    Evidence: Cross-functional AI governance board with quarterly reviews
  • Accountability (documented)
    Evidence: Clear ownership, escalation paths, and incident response procedures
  • Risk Tolerance (configured)
    No evidence
  • Compliance Tracking (validated)
    Evidence: Compliance metadata tracked in policy
```

## Evidence Types You'll See

### EU AI Act Evidence Types
- **configuration**: Policy and system configuration settings
- **threshold**: Risk and quality thresholds
- **quality**: Data quality measures
- **governance**: Data governance policies
- **privacy**: PII protection rules
- **monitoring**: Continuous monitoring capabilities
- **transparency**: User disclosure mechanisms
- **oversight**: Human review workflows

### NIST Evidence Types
- **documented**: Documented policies and procedures
- **configured**: Active system configurations
- **assessed**: Completed assessments
- **analyzed**: Analysis results
- **tracked**: Monitoring and tracking evidence

## Using Reports for Compliance

### For Auditors
1. **Review HTML report** for comprehensive overview
2. **Check evidence details** to verify compliance claims
3. **Export to CSV** for spreadsheet analysis
4. **Note gaps** listed for each requirement
5. **Follow recommendations** for remediation

### For Compliance Officers
1. **Generate monthly** to track progress
2. **Compare over time** to see improvements
3. **Address gaps** listed in recommendations
4. **Prepare evidence** for missing items
5. **Archive reports** with SHA-256 hash for verification

### For Development Teams
1. **Check recommendations** for required changes
2. **Review gaps** to prioritize work
3. **Validate evidence** after implementing features
4. **Regenerate reports** to confirm compliance
5. **Track improvements** in compliance scores

## Report Components

### 1. Metadata Section
- Report ID (for tracking)
- Policy name and ID
- Generation timestamp
- Framework version
- Overall compliance status
- Compliance score (0-100%)

### 2. Summary Section
- Total requirements assessed
- Breakdown by status (compliant/partial/non-compliant)
- Compliance percentage
- Critical gaps highlighted
- Next review date

### 3. Detailed Assessment
**EU AI Act:**
- Article-by-article assessment
- Full evidence list per article
- Specific gaps identified
- Actionable recommendations

**NIST Frameworks:**
- Function-by-function assessment
- Category breakdown with evidence
- Trustworthiness scorecard (AI RMF)
- Privacy metrics (Privacy Framework)
- Gaps and recommendations per function

### 4. Verification Section
- SHA-256 hash of report
- Immutable flag
- Suitable for audit trails

## CSV Format Details

CSV reports include:
- All metadata fields
- Summary statistics
- Evidence details column with pipe-separated values
- Gaps (semicolon-separated)
- Recommendations (semicolon-separated)

Import into Excel or Google Sheets for:
- Filtering by status
- Sorting by compliance
- Pivot tables for analysis
- Tracking over time

## Best Practices

### Regular Reporting
- Generate monthly compliance reports
- Track compliance score trends
- Address declining scores promptly
- Celebrate improvements

### Evidence Management
- Keep evidence current
- Update policy configurations when systems change
- Document new capabilities immediately
- Review and refresh outdated evidence

### Gap Remediation
- Prioritize critical gaps (non-compliant items)
- Create tickets for each recommendation
- Track remediation progress
- Re-generate reports after fixes

### Audit Preparation
1. Generate fresh reports
2. Review all evidence details
3. Prepare supporting documentation
4. Verify hashes for integrity
5. Export to multiple formats

## Troubleshooting

### Missing Evidence
**Problem:** Report shows "No evidence" for a requirement
**Solution:** 
1. Check policy configuration has required fields
2. Verify regulatory framework is enabled
3. Review compliance form completion
4. Update policy and regenerate report

### Low Compliance Score
**Problem:** Overall score below expected level
**Solution:**
1. Review detailed gaps section
2. Prioritize non-compliant items
3. Implement recommendations
4. Update evidence documentation
5. Regenerate to verify improvement

### Report Not Generating
**Problem:** API returns error
**Solution:**
1. Check policy exists and has active version
2. Verify API key is valid
3. Ensure regulatory framework is configured
4. Check server logs for errors

## Related Documentation
- [Regulatory Compliance Implementation Plan](regulatory_compliance_implementation_plan.md)
- [User Guide](UserGuide.md) - Section on Compliance Reports
- [Evidence Display Enhancement](EVIDENCE_DISPLAY_ENHANCEMENT.md) - Technical details

## Support
For issues or questions:
1. Check server logs in `backend/logs/`
2. Review test outputs in `backend/test_outputs/`
3. Run test script: `python backend/test_evidence_display.py`
4. Check API endpoint health: `/api/health`

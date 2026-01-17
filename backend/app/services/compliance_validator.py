"""
Cross-framework compliance validator.

This service validates policy compliance configurations against regulatory
framework requirements and detects cross-framework conflicts with helpful
resolution suggestions.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.schemas.policy_format import PolicyDoc
from app.core.regulatory_templates import (
    get_framework_template,
    get_available_frameworks,
    validate_framework_config,
    ComplianceField,
    FieldType
)
from app.services.compliance_rule_generator import ComplianceRuleGenerator


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"  # Blocks activation
    WARNING = "warning"  # Informational, doesn't block
    INFO = "info"  # Suggestions for improvement


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    framework: str
    section: str
    field: str
    message: str
    regulatory_reference: str = ""
    suggested_fix: str = ""


@dataclass
class ConflictWarning:
    """A conflict between multiple frameworks."""
    frameworks: List[str]
    conflict_type: str  # "threshold", "requirement", "policy"
    description: str
    suggested_resolution: str
    affected_rules: List[str] = field(default_factory=list)


@dataclass
class Resolution:
    """Suggested resolution for a conflict or issue."""
    issue_id: str
    description: str
    action_steps: List[str]
    priority: str  # "high", "medium", "low"


@dataclass
class ValidationResult:
    """Complete validation result."""
    is_valid: bool
    can_activate: bool  # False if there are blocking errors
    compliance_status: str  # "validated", "non_compliant", "draft"
    issues: List[ValidationIssue]
    conflicts: List[ConflictWarning]
    resolutions: List[Resolution]
    completeness_scores: Dict[str, float]  # Framework -> percentage complete
    
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warnings."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]


class ComplianceValidator:
    """
    Service for validating compliance configurations and detecting cross-framework conflicts.
    
    This validator checks:
    1. Framework completeness (all required fields filled)
    2. Field value validity (correct types, within ranges, valid options)
    3. Cross-framework conflicts (contradictory requirements)
    4. Enforcement rule conflicts
    """
    
    # Mapping from framework IDs to PolicyDoc field names
    FRAMEWORK_FIELD_MAPPING = {
        "eu_ai_act_high_risk": "eu_ai_act_config",
        "nist_ai_rmf": "nist_ai_rmf_config",
        "nist_privacy": "nist_privacy_config",
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.rule_generator = ComplianceRuleGenerator()
    
    def validate_compliance(self, policy_doc: PolicyDoc) -> ValidationResult:
        """
        Validate complete policy compliance configuration.
        
        Args:
            policy_doc: PolicyDoc with compliance configurations
            
        Returns:
            ValidationResult with detailed validation information
        """
        frameworks = policy_doc.regulatory_frameworks
        
        if not frameworks:
            return ValidationResult(
                is_valid=True,
                can_activate=True,
                compliance_status="draft",
                issues=[],
                conflicts=[],
                resolutions=[],
                completeness_scores={}
            )
        
        all_issues = []
        all_conflicts = []
        completeness_scores = {}
        
        # Validate each framework independently
        for framework_id in frameworks:
            if framework_id not in get_available_frameworks():
                all_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    framework=framework_id,
                    section="",
                    field="",
                    message=f"Unknown regulatory framework: {framework_id}",
                    suggested_fix="Remove this framework or check the framework ID"
                ))
                continue
            
            # Get framework configuration
            # Map framework ID to PolicyDoc field name
            config_key = self.FRAMEWORK_FIELD_MAPPING.get(framework_id, f"{framework_id}_config")
            framework_config = getattr(policy_doc, config_key, {})
            
            # Check framework completeness
            framework_issues = self.check_framework_completeness(framework_id, framework_config)
            all_issues.extend(framework_issues)
            
            # Calculate completeness score
            completeness_scores[framework_id] = self._calculate_completeness_score(
                framework_id, framework_config
            )
        
        # Detect cross-framework conflicts if multiple frameworks selected
        if len(frameworks) > 1:
            conflicts = self.detect_cross_framework_conflicts(frameworks, policy_doc)
            all_conflicts.extend(conflicts)
        
        # Generate resolutions for issues and conflicts
        resolutions = self.suggest_conflict_resolutions(all_conflicts)
        resolutions.extend(self._suggest_issue_resolutions(all_issues))
        
        # Determine overall validation status
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in all_issues)
        can_activate = not has_errors and all(score >= 90.0 for score in completeness_scores.values())
        
        if can_activate:
            compliance_status = "validated"
        elif has_errors or any(score < 50.0 for score in completeness_scores.values()):
            compliance_status = "non_compliant"
        else:
            compliance_status = "draft"
        
        return ValidationResult(
            is_valid=not has_errors,
            can_activate=can_activate,
            compliance_status=compliance_status,
            issues=all_issues,
            conflicts=all_conflicts,
            resolutions=resolutions,
            completeness_scores=completeness_scores
        )
    
    def check_framework_completeness(
        self,
        framework_id: str,
        config: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """
        Check if all required fields for a framework are properly filled.
        
        Args:
            framework_id: ID of the regulatory framework
            config: Configuration dict for the framework
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            framework = get_framework_template(framework_id)
        except ValueError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                framework=framework_id,
                section="",
                field="",
                message=str(e)
            ))
            return issues
        
        # Use the template's built-in validation
        template_validation = validate_framework_config(framework_id, config)
        
        # Convert template validation errors to ValidationIssues
        for error_msg in template_validation.get("errors", []):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                framework=framework_id,
                section=self._extract_section_from_error(error_msg),
                field=self._extract_field_from_error(error_msg),
                message=error_msg,
                suggested_fix="Complete this required field with appropriate information"
            ))
        
        for warning_msg in template_validation.get("warnings", []):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                framework=framework_id,
                section="",
                field="",
                message=warning_msg
            ))
        
        # Additional semantic validation
        issues.extend(self._validate_field_semantics(framework, config))
        
        return issues
    
    def detect_cross_framework_conflicts(
        self,
        frameworks: List[str],
        policy_doc: PolicyDoc
    ) -> List[ConflictWarning]:
        """
        Detect conflicts between multiple regulatory frameworks.
        
        Args:
            frameworks: List of framework IDs
            policy_doc: PolicyDoc with all configurations
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Generate enforcement rules to check for conflicts
        compliance_config = {
            "regulatory_frameworks": frameworks,
        }
        
        for framework_id in frameworks:
            config_key = self.FRAMEWORK_FIELD_MAPPING.get(framework_id, f"{framework_id}_config")
            compliance_config[config_key] = getattr(policy_doc, config_key, {})
        
        rule_result = self.rule_generator.generate_enforcement_rules(compliance_config)
        
        # Convert rule generation conflicts to ConflictWarnings
        for conflict_msg in rule_result.conflicts:
            conflicts.append(self._parse_rule_conflict(conflict_msg, frameworks))
        
        # Check specific cross-framework scenarios
        conflicts.extend(self._check_threshold_conflicts(frameworks, policy_doc))
        conflicts.extend(self._check_privacy_vs_transparency_conflicts(frameworks, policy_doc))
        conflicts.extend(self._check_human_oversight_conflicts(frameworks, policy_doc))
        
        return conflicts
    
    def suggest_conflict_resolutions(
        self,
        conflicts: List[ConflictWarning]
    ) -> List[Resolution]:
        """
        Generate suggested resolutions for detected conflicts.
        
        Args:
            conflicts: List of conflicts
            
        Returns:
            List of suggested resolutions
        """
        resolutions = []
        
        for i, conflict in enumerate(conflicts):
            if conflict.conflict_type == "threshold":
                resolutions.append(Resolution(
                    issue_id=f"conflict_{i}",
                    description=f"Risk threshold conflict between {', '.join(conflict.frameworks)}",
                    action_steps=[
                        "Review the risk tolerance requirements for each framework",
                        "Use the most restrictive (lowest) threshold to ensure compliance with all frameworks",
                        f"Current suggestion: {conflict.suggested_resolution}"
                    ],
                    priority="high"
                ))
            
            elif conflict.conflict_type == "privacy_transparency":
                resolutions.append(Resolution(
                    issue_id=f"conflict_{i}",
                    description="Data minimization vs. transparency requirements",
                    action_steps=[
                        "Implement anonymization techniques for transparency logs",
                        "Use aggregated data for transparency reporting",
                        "Ensure PII is masked in decision explanations",
                        "Document the balance between privacy and transparency"
                    ],
                    priority="high"
                ))
            
            elif conflict.conflict_type == "human_oversight":
                resolutions.append(Resolution(
                    issue_id=f"conflict_{i}",
                    description="Human oversight configuration mismatch",
                    action_steps=[
                        "Review human oversight requirements from each framework",
                        "Implement the most stringent oversight measures",
                        "Ensure adequate reviewer capacity for volume",
                        "Configure appropriate SLA times"
                    ],
                    priority="medium"
                ))
            
            else:
                resolutions.append(Resolution(
                    issue_id=f"conflict_{i}",
                    description=conflict.description,
                    action_steps=[
                        conflict.suggested_resolution,
                        "Review specific framework requirements",
                        "Consult with compliance team if needed"
                    ],
                    priority="medium"
                ))
        
        return resolutions
    
    def _calculate_completeness_score(
        self,
        framework_id: str,
        config: Dict[str, Any]
    ) -> float:
        """Calculate percentage of required fields completed."""
        try:
            framework = get_framework_template(framework_id)
        except ValueError:
            return 0.0
        
        total_required = 0
        completed = 0
        
        for section in framework.sections:
            section_config = config.get(section.id, {})
            
            for field in section.fields:
                if field.required:
                    total_required += 1
                    if field.id in section_config and section_config[field.id]:
                        # Check if value is not empty
                        value = section_config[field.id]
                        if isinstance(value, str) and value.strip():
                            completed += 1
                        elif isinstance(value, (list, dict)) and value:
                            completed += 1
                        elif isinstance(value, bool):
                            completed += 1
                        elif isinstance(value, (int, float)) and value is not None:
                            completed += 1
        
        if total_required == 0:
            return 100.0
        
        return (completed / total_required) * 100.0
    
    def _validate_field_semantics(
        self,
        framework,
        config: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Perform semantic validation on field values."""
        issues = []
        
        for section in framework.sections:
            section_config = config.get(section.id, {})
            
            for field in section.fields:
                if field.id not in section_config:
                    continue
                
                value = section_config[field.id]
                
                # Check for placeholder or template text
                if isinstance(value, str):
                    placeholder_indicators = [
                        "TODO", "TBD", "PLACEHOLDER", "FILL IN", "EXAMPLE",
                        "lorem ipsum", "sample text"
                    ]
                    if any(indicator.lower() in value.lower() for indicator in placeholder_indicators):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            framework=framework.id,
                            section=section.id,
                            field=field.id,
                            message=f"Field '{field.label}' appears to contain placeholder text",
                            suggested_fix="Replace placeholder with actual implementation details"
                        ))
                
                # Check for suspiciously short required text fields
                if field.required and field.field_type == FieldType.TEXTAREA:
                    if isinstance(value, str) and len(value.strip()) < 20:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            framework=framework.id,
                            section=section.id,
                            field=field.id,
                            message=f"Field '{field.label}' has very brief content (less than 20 characters)",
                            suggested_fix="Provide more detailed information to meet regulatory documentation requirements",
                            regulatory_reference=field.regulatory_reference
                        ))
        
        return issues
    
    def _check_threshold_conflicts(
        self,
        frameworks: List[str],
        policy_doc: PolicyDoc
    ) -> List[ConflictWarning]:
        """Check for conflicting risk threshold requirements."""
        conflicts = []
        thresholds = {}
        
        # Extract risk thresholds from each framework's configuration
        for framework_id in frameworks:
            config_key = self.FRAMEWORK_FIELD_MAPPING.get(framework_id, f"{framework_id}_config")
            framework_config = getattr(policy_doc, config_key, {})
            
            if framework_id == "eu_ai_act_high_risk":
                article_9 = framework_config.get("article_9", {})
                if "risk_acceptability_threshold" in article_9:
                    thresholds[framework_id] = article_9["risk_acceptability_threshold"]
            
            elif framework_id == "nist_ai_rmf":
                govern = framework_config.get("govern", {})
                tolerance = govern.get("ai_risk_tolerance")
                if tolerance:
                    tolerance_map = {"low": 60, "medium": 75, "high": 85}
                    if tolerance in tolerance_map:
                        thresholds[framework_id] = tolerance_map[tolerance]
        
        # Check for significant differences
        if len(thresholds) > 1:
            threshold_values = list(thresholds.values())
            min_threshold = min(threshold_values)
            max_threshold = max(threshold_values)
            
            if max_threshold - min_threshold > 15:  # Significant difference
                conflicts.append(ConflictWarning(
                    frameworks=list(thresholds.keys()),
                    conflict_type="threshold",
                    description=f"Conflicting risk thresholds: {thresholds}",
                    suggested_resolution=f"Use the most restrictive threshold ({min_threshold}) to ensure compliance with all frameworks",
                    affected_rules=["risk_threshold"]
                ))
        
        return conflicts
    
    def _check_privacy_vs_transparency_conflicts(
        self,
        frameworks: List[str],
        policy_doc: PolicyDoc
    ) -> List[ConflictWarning]:
        """Check for conflicts between privacy/data minimization and transparency requirements."""
        conflicts = []
        
        has_privacy = "nist_privacy" in frameworks
        has_transparency = "eu_ai_act_high_risk" in frameworks
        
        if has_privacy and has_transparency:
            privacy_config = getattr(policy_doc, "nist_privacy_config", {})
            eu_config = getattr(policy_doc, "eu_ai_act_config", {})
            
            # Check if strict data minimization is required
            control_p = privacy_config.get("control_p", {})
            has_data_minimization = "collection_controls" in control_p
            
            # Check if comprehensive logging is required
            article_12 = eu_config.get("article_12", {})
            logged_types = article_12.get("logged_data_types", [])
            has_comprehensive_logging = len(logged_types) > 3
            
            if has_data_minimization and has_comprehensive_logging:
                conflicts.append(ConflictWarning(
                    frameworks=["nist_privacy", "eu_ai_act_high_risk"],
                    conflict_type="privacy_transparency",
                    description="NIST Privacy data minimization may conflict with EU AI Act comprehensive logging requirements",
                    suggested_resolution="Use anonymization and aggregation techniques for logged data to satisfy both requirements",
                    affected_rules=["pii_rules", "audit_logging_enabled"]
                ))
        
        return conflicts
    
    def _check_human_oversight_conflicts(
        self,
        frameworks: List[str],
        policy_doc: PolicyDoc
    ) -> List[ConflictWarning]:
        """Check for conflicting human oversight requirements."""
        conflicts = []
        
        oversight_configs = {}
        
        for framework_id in frameworks:
            config_key = self.FRAMEWORK_FIELD_MAPPING.get(framework_id, f"{framework_id}_config")
            framework_config = getattr(policy_doc, config_key, {})
            
            if framework_id == "eu_ai_act_high_risk":
                article_14 = framework_config.get("article_14", {})
                oversight_types = article_14.get("oversight_measures_type", [])
                if oversight_types:
                    oversight_configs[framework_id] = oversight_types
            
            elif framework_id == "nist_ai_rmf":
                manage = framework_config.get("manage", {})
                if "mitigation_controls" in manage:
                    oversight_configs[framework_id] = ["human_review_required"]
        
        # Check if oversight requirements are compatible
        if len(oversight_configs) > 1:
            all_types = []
            for types in oversight_configs.values():
                all_types.extend(types)
            
            # Check for potentially incompatible combinations
            has_in_loop = "human_in_the_loop" in all_types
            has_in_command = "human_in_command" in all_types
            
            if has_in_loop and has_in_command:
                # This isn't necessarily a conflict, but worth noting
                conflicts.append(ConflictWarning(
                    frameworks=list(oversight_configs.keys()),
                    conflict_type="human_oversight",
                    description="Multiple human oversight patterns specified (in-the-loop and in-command)",
                    suggested_resolution="Ensure both oversight patterns are properly implemented with adequate reviewer capacity",
                    affected_rules=["requires_human_review", "human_oversight_types"]
                ))
        
        return conflicts
    
    def _parse_rule_conflict(self, conflict_msg: str, frameworks: List[str]) -> ConflictWarning:
        """Parse a conflict message from rule generation into a ConflictWarning."""
        # Determine conflict type from message
        if "threshold" in conflict_msg.lower():
            conflict_type = "threshold"
        elif "pii" in conflict_msg.lower() or "privacy" in conflict_msg.lower():
            conflict_type = "privacy"
        elif "human" in conflict_msg.lower():
            conflict_type = "human_oversight"
        else:
            conflict_type = "requirement"
        
        return ConflictWarning(
            frameworks=frameworks,
            conflict_type=conflict_type,
            description=conflict_msg,
            suggested_resolution="Review framework requirements and use the most restrictive setting",
            affected_rules=[]
        )
    
    def _suggest_issue_resolutions(self, issues: List[ValidationIssue]) -> List[Resolution]:
        """Generate resolutions for validation issues."""
        resolutions = []
        
        # Group issues by framework and section
        error_count_by_framework = {}
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                if issue.framework not in error_count_by_framework:
                    error_count_by_framework[issue.framework] = 0
                error_count_by_framework[issue.framework] += 1
        
        # Create resolutions for frameworks with multiple errors
        for framework_id, error_count in error_count_by_framework.items():
            if error_count > 3:
                resolutions.append(Resolution(
                    issue_id=f"framework_{framework_id}_incomplete",
                    description=f"{framework_id} configuration is incomplete ({error_count} required fields missing)",
                    action_steps=[
                        f"Complete all required fields for {framework_id}",
                        "Review the compliance form section by section",
                        "Consult framework documentation for guidance on each field",
                        "Ensure no placeholder text remains in completed fields"
                    ],
                    priority="high"
                ))
        
        return resolutions
    
    def _extract_section_from_error(self, error_msg: str) -> str:
        """Extract section name from error message."""
        if "section" in error_msg.lower():
            # Try to extract section name after "section"
            parts = error_msg.split("section")
            if len(parts) > 1:
                section_part = parts[1].strip().strip("'\"")
                return section_part.split("'")[0] if "'" in section_part else ""
        return ""
    
    def _extract_field_from_error(self, error_msg: str) -> str:
        """Extract field name from error message."""
        if "field" in error_msg.lower():
            # Try to extract field name after "field"
            parts = error_msg.split("'")
            if len(parts) >= 2:
                return parts[1]
        return ""

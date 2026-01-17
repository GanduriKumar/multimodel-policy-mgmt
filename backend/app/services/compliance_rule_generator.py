"""
Compliance rule auto-generation engine.

This service automatically generates enforcement rules from regulatory compliance
form configurations. It maps compliance requirements from EU AI Act, NIST AI RMF,
and NIST Privacy Framework to PolicyEngine rules that can be enforced at runtime.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from copy import deepcopy
import logging

from app.core.regulatory_templates import (
    get_framework_template,
    EnforcementRule,
    FieldType,
    ComplianceField
)

logger = logging.getLogger(__name__)


@dataclass
class RuleGenerationResult:
    """Result of rule auto-generation process."""
    enforcement_rules: Dict[str, Any]
    generation_metadata: Dict[str, Any]
    conflicts: List[str]
    warnings: List[str]
    
    def has_conflicts(self) -> bool:
        """Check if there are any rule conflicts."""
        return len(self.conflicts) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class ComplianceRuleGenerator:
    """
    Service for automatically generating enforcement rules from compliance configurations.
    
    This class maps compliance form data from regulatory frameworks to concrete
    PolicyEngine enforcement rules that can be used for real-time policy enforcement.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_enforcement_rules(self, compliance_config: Dict[str, Any]) -> RuleGenerationResult:
        """
        Generate enforcement rules from complete compliance configuration.
        
        Args:
            compliance_config: Dict containing:
                - regulatory_frameworks: List[str]
                - eu_ai_act_config: Dict (if eu_ai_act_high_risk in frameworks)
                - nist_ai_rmf_config: Dict (if nist_ai_rmf in frameworks)  
                - nist_privacy_config: Dict (if nist_privacy in frameworks)
                
        Returns:
            RuleGenerationResult with enforcement rules and metadata
        """
        frameworks = compliance_config.get("regulatory_frameworks", [])
        
        if not frameworks:
            return RuleGenerationResult(
                enforcement_rules={},
                generation_metadata={"frameworks": [], "generated_from": []},
                conflicts=[],
                warnings=["No regulatory frameworks specified"]
            )
        
        # Initialize result containers
        all_rules = {}
        generation_metadata = {
            "frameworks": frameworks,
            "generated_from": [],
            "rule_mappings": {}
        }
        conflicts = []
        warnings = []
        
        # Generate rules for each framework
        for framework_id in frameworks:
            try:
                framework_config = compliance_config.get(f"{framework_id}_config", {})
                
                if framework_id == "eu_ai_act_high_risk":
                    result = self.map_eu_ai_act_to_rules(framework_config)
                elif framework_id == "nist_ai_rmf":
                    result = self.map_nist_ai_rmf_to_rules(framework_config)
                elif framework_id == "nist_privacy":
                    result = self.map_nist_privacy_to_rules(framework_config)
                else:
                    warnings.append(f"Unknown framework: {framework_id}")
                    continue
                
                # Merge rules and detect conflicts
                merge_result = self._merge_rules_with_conflict_detection(
                    all_rules, result["rules"], framework_id
                )
                
                all_rules = merge_result["merged_rules"]
                conflicts.extend(merge_result["conflicts"])
                
                # Track metadata
                generation_metadata["generated_from"].append(framework_id)
                generation_metadata["rule_mappings"][framework_id] = result["mappings"]
                
            except Exception as e:
                self.logger.error(f"Error generating rules for {framework_id}: {str(e)}")
                warnings.append(f"Failed to generate rules for {framework_id}: {str(e)}")
        
        return RuleGenerationResult(
            enforcement_rules=all_rules,
            generation_metadata=generation_metadata,
            conflicts=conflicts,
            warnings=warnings
        )
    
    def map_eu_ai_act_to_rules(self, eu_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map EU AI Act compliance configuration to enforcement rules.
        
        Args:
            eu_config: EU AI Act configuration from compliance form
            
        Returns:
            Dict with 'rules' and 'mappings' keys
        """
        rules = {}
        mappings = {}
        
        try:
            framework = get_framework_template("eu_ai_act_high_risk")
        except ValueError as e:
            self.logger.error(f"Failed to get EU AI Act template: {str(e)}")
            return {"rules": rules, "mappings": mappings}
        
        # Process each section configuration
        for section in framework.sections:
            section_config = eu_config.get(section.id, {})
            
            for field in section.fields:
                if field.id not in section_config or not field.enforcement_mapping:
                    continue
                
                field_value = section_config[field.id]
                self._apply_field_enforcement_mapping(
                    field, field_value, rules, mappings, section.id
                )
        
        # Apply EU AI Act specific rule logic
        self._apply_eu_ai_act_specific_rules(eu_config, rules, mappings)
        
        return {"rules": rules, "mappings": mappings}
    
    def map_nist_ai_rmf_to_rules(self, nist_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map NIST AI RMF compliance configuration to enforcement rules.
        
        Args:
            nist_config: NIST AI RMF configuration from compliance form
            
        Returns:
            Dict with 'rules' and 'mappings' keys
        """
        rules = {}
        mappings = {}
        
        try:
            framework = get_framework_template("nist_ai_rmf")
        except ValueError as e:
            self.logger.error(f"Failed to get NIST AI RMF template: {str(e)}")
            return {"rules": rules, "mappings": mappings}
        
        # Process each function configuration
        for section in framework.sections:
            section_config = nist_config.get(section.id, {})
            
            for field in section.fields:
                if field.id not in section_config or not field.enforcement_mapping:
                    continue
                
                field_value = section_config[field.id]
                self._apply_field_enforcement_mapping(
                    field, field_value, rules, mappings, section.id
                )
        
        # Apply NIST AI RMF specific rule logic
        self._apply_nist_ai_rmf_specific_rules(nist_config, rules, mappings)
        
        return {"rules": rules, "mappings": mappings}
    
    def map_nist_privacy_to_rules(self, privacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map NIST Privacy Framework compliance configuration to enforcement rules.
        
        Args:
            privacy_config: NIST Privacy Framework configuration from compliance form
            
        Returns:
            Dict with 'rules' and 'mappings' keys
        """
        rules = {}
        mappings = {}
        
        try:
            framework = get_framework_template("nist_privacy")
        except ValueError as e:
            self.logger.error(f"Failed to get NIST Privacy template: {str(e)}")
            return {"rules": rules, "mappings": mappings}
        
        # Process each function configuration
        for section in framework.sections:
            section_config = privacy_config.get(section.id, {})
            
            for field in section.fields:
                if field.id not in section_config or not field.enforcement_mapping:
                    continue
                
                field_value = section_config[field.id]
                self._apply_field_enforcement_mapping(
                    field, field_value, rules, mappings, section.id
                )
        
        # Apply NIST Privacy specific rule logic
        self._apply_nist_privacy_specific_rules(privacy_config, rules, mappings)
        
        return {"rules": rules, "mappings": mappings}
    
    def _apply_field_enforcement_mapping(
        self,
        field: ComplianceField,
        field_value: Any,
        rules: Dict[str, Any],
        mappings: Dict[str, Any],
        section_id: str
    ) -> None:
        """Apply enforcement mapping for a specific field."""
        for enforcement_rule, mapping_value in field.enforcement_mapping.items():
            rule_key = enforcement_rule.value
            
            if mapping_value == "field_value":
                # Use the actual field value
                actual_value = field_value
            elif isinstance(mapping_value, dict) and field.field_type == FieldType.SELECT:
                # Map field value through dictionary
                actual_value = mapping_value.get(field_value, field_value)
            else:
                # Use the mapping value directly
                actual_value = mapping_value
            
            # Apply the rule
            if rule_key == "risk_threshold" and isinstance(actual_value, (int, float)):
                rules["risk_threshold"] = int(actual_value)
            elif rule_key == "requires_human_review" and isinstance(actual_value, bool):
                rules["requires_human_review"] = actual_value
            elif rule_key == "conservative_mode" and isinstance(actual_value, bool):
                rules["conservative_mode"] = actual_value
            elif rule_key == "pii_rules" and isinstance(actual_value, dict):
                if "pii_rules" not in rules:
                    rules["pii_rules"] = {}
                rules["pii_rules"].update(actual_value)
            elif rule_key == "intent_rules" and isinstance(actual_value, dict):
                if "intent_rules" not in rules:
                    rules["intent_rules"] = {}
                rules["intent_rules"].update(actual_value)
            elif rule_key == "blocked_terms" and isinstance(actual_value, list):
                if "blocked_terms" not in rules:
                    rules["blocked_terms"] = []
                rules["blocked_terms"].extend(actual_value)
            elif rule_key == "allowed_sources":
                if "allowed_sources" not in rules:
                    rules["allowed_sources"] = []
                if isinstance(actual_value, list):
                    rules["allowed_sources"].extend(actual_value)
                elif isinstance(actual_value, str):
                    # Handle special values
                    pass  # Could implement source restrictions here
            
            # Track mapping for audit purposes
            mapping_key = f"{section_id}.{field.id}"
            if mapping_key not in mappings:
                mappings[mapping_key] = []
            mappings[mapping_key].append({
                "rule": rule_key,
                "value": actual_value,
                "field_type": field.field_type.value,
                "regulatory_reference": field.regulatory_reference
            })
    
    def _apply_eu_ai_act_specific_rules(
        self,
        eu_config: Dict[str, Any],
        rules: Dict[str, Any],
        mappings: Dict[str, Any]
    ) -> None:
        """Apply EU AI Act specific rule generation logic."""
        
        # Article 12: Logging requirements
        article_12_config = eu_config.get("article_12", {})
        if article_12_config.get("automatic_logging"):
            # Enable comprehensive audit logging
            rules["audit_logging_enabled"] = True
            
            logged_types = article_12_config.get("logged_data_types", [])
            if logged_types:
                rules["audit_log_types"] = logged_types
            
            retention_months = article_12_config.get("logging_duration")
            if retention_months:
                rules["audit_retention_months"] = retention_months
        
        # Article 14: Human oversight
        article_14_config = eu_config.get("article_14", {})
        oversight_types = article_14_config.get("oversight_measures_type", [])
        if oversight_types:
            rules["human_oversight_types"] = oversight_types
            
            # Configure human review based on oversight type
            if any(t in oversight_types for t in ["human_in_the_loop", "human_on_the_loop"]):
                rules["requires_human_review"] = True
        
        # Article 15: Accuracy and robustness
        article_15_config = eu_config.get("article_15", {})
        if "accuracy_metrics" in article_15_config:
            # More stringent accuracy requirements = lower risk tolerance
            rules["conservative_mode"] = True
            if "risk_threshold" not in rules:
                rules["risk_threshold"] = 70  # Stricter for high accuracy requirements
        
        mappings["eu_ai_act_specific"] = {
            "logging_requirements": article_12_config.get("automatic_logging", False),
            "human_oversight_types": oversight_types,
            "accuracy_requirements": "accuracy_metrics" in article_15_config
        }
    
    def _apply_nist_ai_rmf_specific_rules(
        self,
        nist_config: Dict[str, Any],
        rules: Dict[str, Any],
        mappings: Dict[str, Any]
    ) -> None:
        """Apply NIST AI RMF specific rule generation logic."""
        
        # GOVERN: Risk tolerance mapping
        govern_config = nist_config.get("govern", {})
        risk_tolerance = govern_config.get("ai_risk_tolerance")
        if risk_tolerance:
            tolerance_map = {"low": 60, "medium": 75, "high": 85}
            if risk_tolerance in tolerance_map:
                rules["risk_threshold"] = tolerance_map[risk_tolerance]
        
        # MEASURE: Bias testing requirements
        measure_config = nist_config.get("measure", {})
        if "bias_testing_procedures" in measure_config:
            if "intent_rules" not in rules:
                rules["intent_rules"] = {}
            if "deny" not in rules["intent_rules"]:
                rules["intent_rules"]["deny"] = []
            rules["intent_rules"]["deny"].extend(["bias", "discrimination", "unfair"])
        
        # MANAGE: Risk mitigation controls
        manage_config = nist_config.get("manage", {})
        if "mitigation_controls" in manage_config:
            rules["conservative_mode"] = True
            rules["requires_human_review"] = True
        
        mappings["nist_ai_rmf_specific"] = {
            "risk_tolerance": risk_tolerance,
            "bias_testing_enabled": "bias_testing_procedures" in measure_config,
            "mitigation_controls_enabled": "mitigation_controls" in manage_config
        }
    
    def _apply_nist_privacy_specific_rules(
        self,
        privacy_config: Dict[str, Any],
        rules: Dict[str, Any],
        mappings: Dict[str, Any]
    ) -> None:
        """Apply NIST Privacy specific rule generation logic."""
        
        # CONTROL-P: Data lifecycle controls
        control_config = privacy_config.get("control_p", {})
        
        # Data minimization requirements
        if "collection_controls" in control_config:
            if "pii_rules" not in rules:
                rules["pii_rules"] = {}
            rules["pii_rules"]["minimize_collection"] = True
            rules["pii_rules"]["deny_unnecessary_pii"] = True
        
        # Data sharing restrictions
        if "sharing_controls" in control_config:
            rules["restrict_data_sharing"] = True
        
        # PROTECT-P: Technical safeguards
        protect_config = privacy_config.get("protect_p", {})
        if "technical_safeguards" in protect_config:
            if "pii_rules" not in rules:
                rules["pii_rules"] = {}
            rules["pii_rules"]["encrypt_pii"] = True
            rules["pii_rules"]["mask_pii"] = True
        
        if "anonymization_measures" in protect_config:
            if "pii_rules" not in rules:
                rules["pii_rules"] = {}
            rules["pii_rules"]["anonymize_pii"] = True
        
        mappings["nist_privacy_specific"] = {
            "data_minimization_enabled": "collection_controls" in control_config,
            "sharing_restrictions": "sharing_controls" in control_config,
            "technical_safeguards": "technical_safeguards" in protect_config,
            "anonymization_enabled": "anonymization_measures" in protect_config
        }
    
    def _merge_rules_with_conflict_detection(
        self,
        existing_rules: Dict[str, Any],
        new_rules: Dict[str, Any],
        framework_id: str
    ) -> Dict[str, Any]:
        """
        Merge new rules with existing rules while detecting conflicts.
        
        Returns:
            Dict with 'merged_rules' and 'conflicts' keys
        """
        merged_rules = deepcopy(existing_rules)
        conflicts = []
        
        for rule_key, new_value in new_rules.items():
            if rule_key in merged_rules:
                existing_value = merged_rules[rule_key]
                
                # Check for conflicts
                conflict_detected = False
                
                if rule_key == "risk_threshold":
                    # Conflicting thresholds - use the more restrictive (lower) one
                    if abs(existing_value - new_value) > 10:  # Significant difference
                        conflicts.append(
                            f"Risk threshold conflict: existing={existing_value}, "
                            f"{framework_id}={new_value}. Using more restrictive value."
                        )
                    merged_rules[rule_key] = min(existing_value, new_value)
                    
                elif rule_key == "conservative_mode":
                    # If either framework requires conservative mode, enable it
                    merged_rules[rule_key] = existing_value or new_value
                    
                elif rule_key == "requires_human_review":
                    # If either framework requires human review, enable it
                    merged_rules[rule_key] = existing_value or new_value
                    
                elif rule_key in ["pii_rules", "intent_rules"]:
                    # Merge dictionary rules
                    if isinstance(existing_value, dict) and isinstance(new_value, dict):
                        merged_rules[rule_key].update(new_value)
                    else:
                        conflicts.append(
                            f"Type conflict for {rule_key}: cannot merge "
                            f"{type(existing_value)} with {type(new_value)}"
                        )
                        
                elif rule_key in ["blocked_terms", "allowed_sources", "audit_log_types"]:
                    # Merge list rules
                    if isinstance(existing_value, list) and isinstance(new_value, list):
                        # Remove duplicates while preserving order
                        merged_list = existing_value.copy()
                        for item in new_value:
                            if item not in merged_list:
                                merged_list.append(item)
                        merged_rules[rule_key] = merged_list
                    else:
                        conflicts.append(
                            f"Type conflict for {rule_key}: cannot merge "
                            f"{type(existing_value)} with {type(new_value)}"
                        )
                        
                else:
                    # For other rules, check for value conflicts
                    if existing_value != new_value:
                        conflicts.append(
                            f"Value conflict for {rule_key}: existing={existing_value}, "
                            f"{framework_id}={new_value}. Keeping existing value."
                        )
                    # Keep existing value in case of conflict
            else:
                # No existing rule, add the new one
                merged_rules[rule_key] = new_value
        
        return {"merged_rules": merged_rules, "conflicts": conflicts}
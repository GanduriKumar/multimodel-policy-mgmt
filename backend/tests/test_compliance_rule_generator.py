"""
Unit tests for ComplianceRuleGenerator service.
"""

import pytest
from app.services.compliance_rule_generator import ComplianceRuleGenerator, RuleGenerationResult


class TestComplianceRuleGenerator:
    """Test compliance rule auto-generation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ComplianceRuleGenerator()

    def test_empty_configuration(self):
        """Test rule generation with empty configuration."""
        result = self.generator.generate_enforcement_rules({})
        
        assert isinstance(result, RuleGenerationResult)
        assert result.enforcement_rules == {}
        assert result.has_warnings()
        assert "No regulatory frameworks specified" in result.warnings

    def test_unknown_framework(self):
        """Test rule generation with unknown framework."""
        config = {
            "regulatory_frameworks": ["unknown_framework"],
            "unknown_framework_config": {}
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        assert result.has_warnings()
        assert "Unknown framework: unknown_framework" in result.warnings

    def test_eu_ai_act_rule_generation(self):
        """Test EU AI Act rule generation."""
        eu_config = {
            "article_9": {
                "risk_acceptability_threshold": 75,
                "risk_mitigation_measures": "Human oversight implemented"
            },
            "article_12": {
                "automatic_logging": True,
                "logging_duration": 36,
                "logged_data_types": ["input_data", "output_data", "timestamps"]
            },
            "article_14": {
                "oversight_measures_type": ["human_on_the_loop", "human_in_command"]
            },
            "article_15": {
                "accuracy_metrics": "95% accuracy target"
            }
        }
        
        result = self.generator.map_eu_ai_act_to_rules(eu_config)
        
        rules = result["rules"]
        mappings = result["mappings"]
        
        # Check generated rules
        assert "requires_human_review" in rules
        assert rules["requires_human_review"] is True
        assert "audit_logging_enabled" in rules
        assert rules["audit_logging_enabled"] is True
        assert "audit_log_types" in rules
        assert "input_data" in rules["audit_log_types"]
        assert "conservative_mode" in rules
        assert rules["conservative_mode"] is True
        
        # Check mappings
        assert "eu_ai_act_specific" in mappings
        assert mappings["eu_ai_act_specific"]["logging_requirements"] is True

    def test_nist_ai_rmf_rule_generation(self):
        """Test NIST AI RMF rule generation."""
        nist_config = {
            "govern": {
                "ai_risk_tolerance": "low"
            },
            "measure": {
                "bias_testing_procedures": "Regular bias testing implemented"
            },
            "manage": {
                "mitigation_controls": "Automated controls with human escalation"
            }
        }
        
        result = self.generator.map_nist_ai_rmf_to_rules(nist_config)
        
        rules = result["rules"]
        mappings = result["mappings"]
        
        # Check generated rules
        assert "risk_threshold" in rules
        assert rules["risk_threshold"] == 60  # Low risk tolerance
        assert "intent_rules" in rules
        assert "bias" in rules["intent_rules"]["deny"]
        assert "requires_human_review" in rules
        assert rules["requires_human_review"] is True
        
        # Check mappings
        assert "nist_ai_rmf_specific" in mappings
        assert mappings["nist_ai_rmf_specific"]["risk_tolerance"] == "low"

    def test_nist_privacy_rule_generation(self):
        """Test NIST Privacy Framework rule generation."""
        privacy_config = {
            "control_p": {
                "collection_controls": "Minimal data collection implemented",
                "sharing_controls": "Restricted data sharing policies"
            },
            "protect_p": {
                "technical_safeguards": "PII encryption and masking",
                "anonymization_measures": "Data anonymization procedures"
            }
        }
        
        result = self.generator.map_nist_privacy_to_rules(privacy_config)
        
        rules = result["rules"]
        mappings = result["mappings"]
        
        # Check generated rules
        assert "pii_rules" in rules
        assert rules["pii_rules"]["minimize_collection"] is True
        assert rules["pii_rules"]["encrypt_pii"] is True
        assert rules["pii_rules"]["anonymize_pii"] is True
        assert "restrict_data_sharing" in rules
        assert rules["restrict_data_sharing"] is True
        
        # Check mappings
        assert "nist_privacy_specific" in mappings
        assert mappings["nist_privacy_specific"]["data_minimization_enabled"] is True

    def test_multi_framework_rule_generation(self):
        """Test rule generation with multiple frameworks."""
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf", "nist_privacy"],
            "eu_ai_act_high_risk_config": {
                "article_9": {
                    "risk_acceptability_threshold": 70
                },
                "article_14": {
                    "oversight_measures_type": ["human_in_the_loop"]
                }
            },
            "nist_ai_rmf_config": {
                "govern": {
                    "ai_risk_tolerance": "medium"
                }
            },
            "nist_privacy_config": {
                "control_p": {
                    "collection_controls": "Data minimization implemented"
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        rules = result.enforcement_rules
        metadata = result.generation_metadata
        
        # Check combined rules
        assert "risk_threshold" in rules
        assert "requires_human_review" in rules
        assert "pii_rules" in rules
        
        # Check metadata
        assert len(metadata["frameworks"]) == 3
        assert "eu_ai_act_high_risk" in metadata["generated_from"]
        assert "nist_ai_rmf" in metadata["generated_from"]
        assert "nist_privacy" in metadata["generated_from"]

    def test_rule_conflict_detection(self):
        """Test detection of conflicts between frameworks."""
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf"],
            "eu_ai_act_high_risk_config": {
                "article_9": {
                    "risk_acceptability_threshold": 80  # Higher threshold
                }
            },
            "nist_ai_rmf_config": {
                "govern": {
                    "ai_risk_tolerance": "low"  # Maps to 60, lower threshold
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        # Should detect risk threshold conflict
        assert result.has_conflicts()
        assert any("Risk threshold conflict" in conflict for conflict in result.conflicts)
        
        # Should use the more restrictive (lower) threshold
        assert result.enforcement_rules["risk_threshold"] == 60

    def test_rule_merging_pii_rules(self):
        """Test merging of PII rules from multiple frameworks."""
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_privacy"],
            "eu_ai_act_high_risk_config": {
                "article_10": {
                    "privacy_protection_measures": "Data anonymization implemented"
                }
            },
            "nist_privacy_config": {
                "control_p": {
                    "collection_controls": "Minimal data collection"
                },
                "protect_p": {
                    "technical_safeguards": "PII encryption"
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        pii_rules = result.enforcement_rules.get("pii_rules", {})
        
        # Should have merged PII rules from both frameworks
        assert "deny_when_any_pii" in pii_rules  # From EU AI Act
        assert "minimize_collection" in pii_rules  # From NIST Privacy
        assert "encrypt_pii" in pii_rules  # From NIST Privacy

    def test_list_rule_merging(self):
        """Test merging of list-type rules (blocked_terms, etc.)."""
        # Mock enforcement mappings for this test
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf"],
            "eu_ai_act_high_risk_config": {
                "article_15": {
                    "cybersecurity_measures": "Anti-malware protection"
                }
            },
            "nist_ai_rmf_config": {
                "measure": {
                    "bias_testing_procedures": "Bias detection implemented"
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        # Check that intent rules were merged
        intent_rules = result.enforcement_rules.get("intent_rules", {})
        denied_intents = intent_rules.get("deny", [])
        
        # Should include terms from both frameworks
        assert "bias" in denied_intents
        assert "discrimination" in denied_intents

    def test_boolean_rule_precedence(self):
        """Test that boolean rules follow OR logic (any framework can enable)."""
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk", "nist_ai_rmf"],
            "eu_ai_act_high_risk_config": {
                "article_14": {
                    "human_oversight_design": "Human oversight implemented"
                }
            },
            "nist_ai_rmf_config": {
                "manage": {
                    "mitigation_controls": "Risk mitigation with human oversight"
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        # Both frameworks enable human review, should be True
        assert result.enforcement_rules.get("requires_human_review") is True
        assert result.enforcement_rules.get("conservative_mode") is True

    def test_enforcement_mapping_field_value(self):
        """Test enforcement mapping with field_value directive."""
        # This tests the case where mapping_value is "field_value"
        # The actual risk threshold value should be used from the form
        eu_config = {
            "article_9": {
                "risk_acceptability_threshold": 85  # This should be used directly
            }
        }
        
        result = self.generator.map_eu_ai_act_to_rules(eu_config)
        
        # The field is configured with "field_value" mapping in templates
        # So it should use the actual value (85) as the risk threshold
        rules = result["rules"]
        assert "risk_threshold" in rules
        assert rules["risk_threshold"] == 85

    def test_rule_generation_with_missing_config(self):
        """Test rule generation when framework config is missing."""
        config = {
            "regulatory_frameworks": ["eu_ai_act_high_risk"],
            # Missing eu_ai_act_high_risk_config
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        # Should not fail, but may generate minimal rules
        assert not result.has_conflicts()
        assert result.generation_metadata["frameworks"] == ["eu_ai_act_high_risk"]

    def test_metadata_tracking(self):
        """Test that rule generation metadata is properly tracked."""
        config = {
            "regulatory_frameworks": ["nist_ai_rmf"],
            "nist_ai_rmf_config": {
                "govern": {
                    "ai_risk_tolerance": "high"
                }
            }
        }
        
        result = self.generator.generate_enforcement_rules(config)
        
        metadata = result.generation_metadata
        
        # Check basic metadata
        assert "frameworks" in metadata
        assert "generated_from" in metadata
        assert "rule_mappings" in metadata
        
        # Check framework-specific mappings
        assert "nist_ai_rmf" in metadata["rule_mappings"]
        rmf_mappings = metadata["rule_mappings"]["nist_ai_rmf"]
        assert "nist_ai_rmf_specific" in rmf_mappings

    def test_logging_and_audit_rules(self):
        """Test generation of logging and audit-related rules."""
        eu_config = {
            "article_12": {
                "automatic_logging": True,
                "logging_duration": 24,
                "logged_data_types": ["input_data", "system_decisions", "error_events"]
            }
        }
        
        result = self.generator.map_eu_ai_act_to_rules(eu_config)
        
        rules = result["rules"]
        
        # Check audit logging configuration
        assert rules["audit_logging_enabled"] is True
        assert rules["audit_retention_months"] == 24
        assert "audit_log_types" in rules
        assert "input_data" in rules["audit_log_types"]
        assert "system_decisions" in rules["audit_log_types"]
        assert "error_events" in rules["audit_log_types"]

    def test_human_oversight_configuration(self):
        """Test generation of human oversight rules."""
        eu_config = {
            "article_14": {
                "oversight_measures_type": ["human_in_the_loop", "human_on_the_loop"]
            }
        }
        
        result = self.generator.map_eu_ai_act_to_rules(eu_config)
        
        rules = result["rules"]
        
        # Should enable human review for in-the-loop or on-the-loop oversight
        assert rules["requires_human_review"] is True
        assert rules["human_oversight_types"] == ["human_in_the_loop", "human_on_the_loop"]

    def test_error_handling(self):
        """Test error handling in rule generation."""
        # Test with invalid template (this will be caught and logged)
        generator = ComplianceRuleGenerator()
        
        # Mock a case where get_framework_template fails
        result = generator.map_eu_ai_act_to_rules({})
        
        # Should return empty rules and mappings, not crash
        assert isinstance(result, dict)
        assert "rules" in result
        assert "mappings" in result
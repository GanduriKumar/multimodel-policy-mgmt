"""
Regulatory framework templates and field definitions for compliance form generation.

This module provides comprehensive templates for:
- EU AI Act (High-Risk AI Systems) - Articles 9-15
- NIST AI Risk Management Framework - Four core functions (Govern, Map, Measure, Manage)
- NIST Privacy Framework - Five functions (Identify-P, Govern-P, Control-P, Communicate-P, Protect-P)
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    """Supported field types for compliance forms."""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"
    NUMBER = "number"
    DATE = "date"
    URL = "url"
    EMAIL = "email"


class EnforcementRule(Enum):
    """Types of enforcement rules that can be auto-generated."""
    RISK_THRESHOLD = "risk_threshold"
    PII_RULES = "pii_rules"
    HUMAN_REVIEW = "requires_human_review"
    BLOCKED_TERMS = "blocked_terms"
    ALLOWED_SOURCES = "allowed_sources"
    CONSERVATIVE_MODE = "conservative_mode"
    INTENT_RULES = "intent_rules"


@dataclass
class ComplianceField:
    """Definition of a compliance form field."""
    id: str
    label: str
    field_type: FieldType
    description: str
    required: bool = False
    options: List[str] = None
    validation_rules: Dict[str, Any] = None
    help_text: str = ""
    enforcement_mapping: Dict[EnforcementRule, Any] = None
    regulatory_reference: str = ""

    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.validation_rules is None:
            self.validation_rules = {}
        if self.enforcement_mapping is None:
            self.enforcement_mapping = {}


@dataclass
class ComplianceSection:
    """A section of compliance form fields."""
    id: str
    title: str
    description: str
    fields: List[ComplianceField]
    regulatory_reference: str = ""


@dataclass
class RegulatoryFramework:
    """Complete regulatory framework definition."""
    id: str
    name: str
    version: str
    description: str
    sections: List[ComplianceSection]


# ===============================
# EU AI ACT (HIGH-RISK AI SYSTEMS)
# ===============================

EU_AI_ACT_HIGH_RISK_TEMPLATE = RegulatoryFramework(
    id="eu_ai_act_high_risk",
    name="EU AI Act - High-Risk AI Systems",
    version="2024",
    description="Compliance requirements for high-risk AI systems under the EU Artificial Intelligence Act",
    sections=[
        ComplianceSection(
            id="article_9",
            title="Article 9 - Risk Management System",
            description="Risk management system throughout the entire lifecycle of high-risk AI systems",
            regulatory_reference="EU AI Act Article 9",
            fields=[
                ComplianceField(
                    id="risk_management_system",
                    label="Risk Management System Description",
                    field_type=FieldType.TEXTAREA,
                    description="Describe the continuous, iterative process for identifying, analyzing, and mitigating risks",
                    required=True,
                    help_text="Detail your systematic approach to risk identification, assessment, and mitigation throughout the AI system lifecycle",
                    regulatory_reference="Article 9(1)"
                ),
                ComplianceField(
                    id="risk_identification_process",
                    label="Risk Identification Process",
                    field_type=FieldType.TEXTAREA,
                    description="How known and foreseeable risks are identified and analyzed",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.CONSERVATIVE_MODE: True,
                        EnforcementRule.RISK_THRESHOLD: 70
                    },
                    regulatory_reference="Article 9(2)(a)"
                ),
                ComplianceField(
                    id="risk_mitigation_measures",
                    label="Risk Mitigation Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Most appropriate risk mitigation measures implemented",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.HUMAN_REVIEW: True
                    },
                    regulatory_reference="Article 9(2)(b)"
                ),
                ComplianceField(
                    id="residual_risk_evaluation",
                    label="Residual Risk Evaluation",
                    field_type=FieldType.TEXTAREA,
                    description="Evaluation of residual risks after mitigation measures",
                    required=True,
                    regulatory_reference="Article 9(4)"
                ),
                ComplianceField(
                    id="risk_acceptability_threshold",
                    label="Risk Acceptability Threshold",
                    field_type=FieldType.NUMBER,
                    description="Numerical threshold for acceptable risk levels (0-100)",
                    required=True,
                    validation_rules={"min": 0, "max": 100},
                    enforcement_mapping={
                        EnforcementRule.RISK_THRESHOLD: "field_value"
                    },
                    regulatory_reference="Article 9(4)"
                )
            ]
        ),
        ComplianceSection(
            id="article_10",
            title="Article 10 - Data and Data Governance",
            description="Data governance and quality requirements for training, validation and testing datasets",
            regulatory_reference="EU AI Act Article 10",
            fields=[
                ComplianceField(
                    id="data_governance_practices",
                    label="Data Governance Practices",
                    field_type=FieldType.TEXTAREA,
                    description="Appropriate data governance and management practices for training, validation and testing data sets",
                    required=True,
                    regulatory_reference="Article 10(1)"
                ),
                ComplianceField(
                    id="training_data_quality",
                    label="Training Data Quality Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Measures to ensure training data quality, relevance, and representativeness",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.ALLOWED_SOURCES: "validated_sources_only"
                    },
                    regulatory_reference="Article 10(2)(a)"
                ),
                ComplianceField(
                    id="bias_monitoring",
                    label="Bias Monitoring and Detection",
                    field_type=FieldType.TEXTAREA,
                    description="Data examination procedures to detect possible biases",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.INTENT_RULES: {"deny": ["discrimination", "bias"]}
                    },
                    regulatory_reference="Article 10(2)(f)"
                ),
                ComplianceField(
                    id="data_completeness_check",
                    label="Data Completeness and Error Detection",
                    field_type=FieldType.TEXTAREA,
                    description="Procedures for detecting and addressing data gaps, errors and inconsistencies",
                    required=True,
                    regulatory_reference="Article 10(2)(e)"
                ),
                ComplianceField(
                    id="privacy_protection_measures",
                    label="Privacy Protection in Data Processing",
                    field_type=FieldType.TEXTAREA,
                    description="Measures to protect privacy including data minimization and anonymization",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.PII_RULES: {"deny_when_any_pii": True, "mask_all_pii": True}
                    },
                    regulatory_reference="Article 10(5)"
                )
            ]
        ),
        ComplianceSection(
            id="article_11",
            title="Article 11 - Technical Documentation",
            description="Comprehensive technical documentation requirements",
            regulatory_reference="EU AI Act Article 11",
            fields=[
                ComplianceField(
                    id="technical_documentation",
                    label="Technical Documentation Package",
                    field_type=FieldType.TEXTAREA,
                    description="Comprehensive technical documentation demonstrating compliance",
                    required=True,
                    regulatory_reference="Article 11(1)"
                ),
                ComplianceField(
                    id="system_description",
                    label="AI System Description",
                    field_type=FieldType.TEXTAREA,
                    description="General characteristics, capabilities and limitations of the AI system",
                    required=True,
                    regulatory_reference="Annex IV(1)(a)"
                ),
                ComplianceField(
                    id="intended_purpose",
                    label="Intended Purpose and Use Cases",
                    field_type=FieldType.TEXTAREA,
                    description="Elements of the AI system and the process for its development",
                    required=True,
                    regulatory_reference="Annex IV(1)(b)"
                ),
                ComplianceField(
                    id="architecture_description",
                    label="System Architecture Description",
                    field_type=FieldType.TEXTAREA,
                    description="Description of the architecture and key components",
                    required=True,
                    regulatory_reference="Annex IV(1)(c)"
                )
            ]
        ),
        ComplianceSection(
            id="article_12",
            title="Article 12 - Record-Keeping",
            description="Automatic recording and log-keeping requirements",
            regulatory_reference="EU AI Act Article 12",
            fields=[
                ComplianceField(
                    id="automatic_logging",
                    label="Automatic Logging Capabilities",
                    field_type=FieldType.BOOLEAN,
                    description="AI system designed to automatically log events while operating",
                    required=True,
                    regulatory_reference="Article 12(1)"
                ),
                ComplianceField(
                    id="logging_duration",
                    label="Log Retention Period",
                    field_type=FieldType.NUMBER,
                    description="Duration for which logs are kept (in months)",
                    required=True,
                    validation_rules={"min": 6, "max": 120},
                    help_text="Logs must be kept for at least 6 months, recommend 36+ months for high-risk systems",
                    regulatory_reference="Article 12(1)"
                ),
                ComplianceField(
                    id="logged_data_types",
                    label="Types of Data Logged",
                    field_type=FieldType.MULTISELECT,
                    description="Categories of data automatically recorded",
                    required=True,
                    options=["input_data", "output_data", "timestamps", "user_interactions", "system_decisions", "confidence_scores", "error_events"],
                    regulatory_reference="Article 12(1)"
                ),
                ComplianceField(
                    id="log_traceability",
                    label="Traceability of Operations",
                    field_type=FieldType.TEXTAREA,
                    description="How logs enable tracing of AI system functioning throughout its lifecycle",
                    required=True,
                    regulatory_reference="Article 12(1)"
                )
            ]
        ),
        ComplianceSection(
            id="article_13",
            title="Article 13 - Transparency and Information to Users",
            description="Transparency obligations and information provision to users",
            regulatory_reference="EU AI Act Article 13",
            fields=[
                ComplianceField(
                    id="transparency_design",
                    label="Transparency by Design",
                    field_type=FieldType.TEXTAREA,
                    description="How the AI system is designed to ensure transparency to users",
                    required=True,
                    regulatory_reference="Article 13(1)"
                ),
                ComplianceField(
                    id="user_information_content",
                    label="Information Provided to Users",
                    field_type=FieldType.TEXTAREA,
                    description="Clear and adequate information provided to users about the AI system",
                    required=True,
                    regulatory_reference="Article 13(1)"
                ),
                ComplianceField(
                    id="decision_explanation",
                    label="Decision Explanation Mechanism",
                    field_type=FieldType.TEXTAREA,
                    description="How users receive explanations for AI system decisions affecting them",
                    required=True,
                    help_text="Must provide meaningful explanations of AI decisions in understandable terms",
                    regulatory_reference="Article 13(1)"
                ),
                ComplianceField(
                    id="user_understanding_measures",
                    label="User Understanding Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Measures taken to ensure users understand AI system capabilities and limitations",
                    required=True,
                    regulatory_reference="Article 13(2)"
                )
            ]
        ),
        ComplianceSection(
            id="article_14",
            title="Article 14 - Human Oversight",
            description="Human oversight requirements and implementation",
            regulatory_reference="EU AI Act Article 14",
            fields=[
                ComplianceField(
                    id="human_oversight_design",
                    label="Human Oversight by Design",
                    field_type=FieldType.TEXTAREA,
                    description="How human oversight is built into the AI system design",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.HUMAN_REVIEW: True
                    },
                    regulatory_reference="Article 14(1)"
                ),
                ComplianceField(
                    id="oversight_measures_type",
                    label="Types of Human Oversight Measures",
                    field_type=FieldType.MULTISELECT,
                    description="Categories of human oversight implemented",
                    required=True,
                    options=["human_in_the_loop", "human_on_the_loop", "human_in_command"],
                    help_text="Select all applicable oversight patterns",
                    regulatory_reference="Article 14(2)"
                ),
                ComplianceField(
                    id="overseer_qualifications",
                    label="Human Overseer Qualifications",
                    field_type=FieldType.TEXTAREA,
                    description="Competence, training and authority of persons assigned to human oversight",
                    required=True,
                    regulatory_reference="Article 14(3)"
                ),
                ComplianceField(
                    id="oversight_effectiveness",
                    label="Oversight Effectiveness Measures",
                    field_type=FieldType.TEXTAREA,
                    description="How the effectiveness of human oversight measures is ensured",
                    required=True,
                    regulatory_reference="Article 14(4)(a)"
                ),
                ComplianceField(
                    id="intervention_capability",
                    label="Human Intervention Capabilities",
                    field_type=FieldType.TEXTAREA,
                    description="Ability of human overseers to intervene or interrupt AI system operation",
                    required=True,
                    regulatory_reference="Article 14(4)(c)"
                )
            ]
        ),
        ComplianceSection(
            id="article_15",
            title="Article 15 - Accuracy, Robustness and Cybersecurity",
            description="Accuracy, robustness and cybersecurity requirements",
            regulatory_reference="EU AI Act Article 15",
            fields=[
                ComplianceField(
                    id="accuracy_measures",
                    label="Accuracy Achievement Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Measures taken to achieve appropriate levels of accuracy",
                    required=True,
                    regulatory_reference="Article 15(1)"
                ),
                ComplianceField(
                    id="accuracy_metrics",
                    label="Accuracy Metrics and Targets",
                    field_type=FieldType.TEXTAREA,
                    description="Specific accuracy metrics and performance targets",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.RISK_THRESHOLD: 80  # Higher accuracy requires lower risk tolerance
                    },
                    regulatory_reference="Article 15(1)"
                ),
                ComplianceField(
                    id="robustness_measures",
                    label="Robustness and Resilience Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Measures to ensure robustness against errors, faults or inconsistencies",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.CONSERVATIVE_MODE: True
                    },
                    regulatory_reference="Article 15(2)"
                ),
                ComplianceField(
                    id="cybersecurity_measures",
                    label="Cybersecurity Protection Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Cybersecurity measures against relevant threats",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.BLOCKED_TERMS: ["malware", "exploit", "attack"]
                    },
                    regulatory_reference="Article 15(3)"
                )
            ]
        )
    ]
)


# ===============================
# NIST AI RISK MANAGEMENT FRAMEWORK
# ===============================

NIST_AI_RMF_TEMPLATE = RegulatoryFramework(
    id="nist_ai_rmf",
    name="NIST AI Risk Management Framework",
    version="1.0",
    description="NIST AI Risk Management Framework for trustworthy AI development and deployment",
    sections=[
        ComplianceSection(
            id="govern",
            title="GOVERN Function",
            description="Organizational structures and processes to support trustworthy AI governance",
            regulatory_reference="NIST AI RMF 1.0 - Govern Function",
            fields=[
                ComplianceField(
                    id="ai_governance_structure",
                    label="AI Governance Structure",
                    field_type=FieldType.TEXTAREA,
                    description="Organizational structure for AI governance and oversight",
                    required=True,
                    help_text="Describe roles, responsibilities, and decision-making processes for AI governance"
                ),
                ComplianceField(
                    id="ai_risk_tolerance",
                    label="AI Risk Tolerance Levels",
                    field_type=FieldType.SELECT,
                    description="Organization's risk tolerance for AI systems",
                    required=True,
                    options=["low", "medium", "high"],
                    enforcement_mapping={
                        EnforcementRule.RISK_THRESHOLD: {"low": 60, "medium": 75, "high": 85}
                    }
                ),
                ComplianceField(
                    id="stakeholder_engagement",
                    label="Stakeholder Engagement Process",
                    field_type=FieldType.TEXTAREA,
                    description="How stakeholders are involved in AI risk management decisions",
                    required=True
                ),
                ComplianceField(
                    id="ai_policy_framework",
                    label="AI Policy and Procedure Framework",
                    field_type=FieldType.TEXTAREA,
                    description="Policies and procedures governing AI development and deployment",
                    required=True
                ),
                ComplianceField(
                    id="accountability_mechanisms",
                    label="Accountability Mechanisms",
                    field_type=FieldType.TEXTAREA,
                    description="Mechanisms for ensuring accountability in AI decision-making",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.HUMAN_REVIEW: True
                    }
                )
            ]
        ),
        ComplianceSection(
            id="map",
            title="MAP Function",
            description="Context establishment and risk identification for AI systems",
            regulatory_reference="NIST AI RMF 1.0 - Map Function",
            fields=[
                ComplianceField(
                    id="ai_system_context",
                    label="AI System Context Documentation",
                    field_type=FieldType.TEXTAREA,
                    description="Detailed context of AI system including intended use, environment, and stakeholders",
                    required=True
                ),
                ComplianceField(
                    id="ai_system_categorization",
                    label="AI System Risk Categorization",
                    field_type=FieldType.SELECT,
                    description="Risk category classification of the AI system",
                    required=True,
                    options=["low_risk", "moderate_risk", "high_risk", "unacceptable_risk"]
                ),
                ComplianceField(
                    id="stakeholder_impact_analysis",
                    label="Stakeholder Impact Analysis",
                    field_type=FieldType.TEXTAREA,
                    description="Analysis of potential impacts on different stakeholder groups",
                    required=True
                ),
                ComplianceField(
                    id="risk_identification",
                    label="AI Risk Identification",
                    field_type=FieldType.TEXTAREA,
                    description="Identification of AI-specific risks including bias, fairness, and safety risks",
                    required=True
                ),
                ComplianceField(
                    id="interdependency_mapping",
                    label="System Interdependency Mapping",
                    field_type=FieldType.TEXTAREA,
                    description="Mapping of AI system interdependencies and potential cascading effects",
                    required=True
                )
            ]
        ),
        ComplianceSection(
            id="measure",
            title="MEASURE Function",
            description="Measurement and monitoring of AI trustworthiness characteristics",
            regulatory_reference="NIST AI RMF 1.0 - Measure Function",
            fields=[
                ComplianceField(
                    id="trustworthiness_metrics",
                    label="Trustworthiness Metrics",
                    field_type=FieldType.TEXTAREA,
                    description="Metrics for measuring AI trustworthiness (validity, reliability, fairness, etc.)",
                    required=True,
                    help_text="Define specific metrics for measuring fairness, reliability, safety, transparency, and other trustworthiness characteristics"
                ),
                ComplianceField(
                    id="performance_monitoring",
                    label="AI Performance Monitoring",
                    field_type=FieldType.TEXTAREA,
                    description="Continuous monitoring of AI system performance and behavior",
                    required=True
                ),
                ComplianceField(
                    id="bias_testing_procedures",
                    label="Bias Testing and Evaluation",
                    field_type=FieldType.TEXTAREA,
                    description="Procedures for testing and evaluating AI system bias",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.INTENT_RULES: {"deny": ["bias", "discrimination", "unfair"]}
                    }
                ),
                ComplianceField(
                    id="safety_assessment",
                    label="AI Safety Assessment",
                    field_type=FieldType.TEXTAREA,
                    description="Assessment of AI system safety and potential harms",
                    required=True
                ),
                ComplianceField(
                    id="measurement_frequency",
                    label="Measurement and Testing Frequency",
                    field_type=FieldType.SELECT,
                    description="Frequency of trustworthiness measurements and evaluations",
                    required=True,
                    options=["continuous", "daily", "weekly", "monthly", "quarterly"]
                )
            ]
        ),
        ComplianceSection(
            id="manage",
            title="MANAGE Function",
            description="Risk response and management of AI systems",
            regulatory_reference="NIST AI RMF 1.0 - Manage Function",
            fields=[
                ComplianceField(
                    id="risk_treatment_strategy",
                    label="Risk Treatment Strategy",
                    field_type=FieldType.TEXTAREA,
                    description="Strategy for treating identified AI risks (avoid, mitigate, transfer, accept)",
                    required=True
                ),
                ComplianceField(
                    id="mitigation_controls",
                    label="Risk Mitigation Controls",
                    field_type=FieldType.TEXTAREA,
                    description="Specific controls implemented to mitigate AI risks",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.CONSERVATIVE_MODE: True,
                        EnforcementRule.HUMAN_REVIEW: True
                    }
                ),
                ComplianceField(
                    id="incident_response_plan",
                    label="AI Incident Response Plan",
                    field_type=FieldType.TEXTAREA,
                    description="Plan for responding to AI system incidents and failures",
                    required=True
                ),
                ComplianceField(
                    id="continuous_monitoring",
                    label="Continuous Risk Monitoring",
                    field_type=FieldType.TEXTAREA,
                    description="Continuous monitoring of AI risks and system performance",
                    required=True
                ),
                ComplianceField(
                    id="improvement_processes",
                    label="Continuous Improvement Processes",
                    field_type=FieldType.TEXTAREA,
                    description="Processes for continuous improvement of AI risk management",
                    required=True
                )
            ]
        )
    ]
)


# ===============================
# NIST PRIVACY FRAMEWORK
# ===============================

NIST_PRIVACY_TEMPLATE = RegulatoryFramework(
    id="nist_privacy",
    name="NIST Privacy Framework",
    version="1.0",
    description="NIST Privacy Framework for comprehensive privacy risk management",
    sections=[
        ComplianceSection(
            id="identify_p",
            title="IDENTIFY-P Function",
            description="Privacy risk identification and data processing inventory",
            regulatory_reference="NIST Privacy Framework - Identify-P",
            fields=[
                ComplianceField(
                    id="data_processing_inventory",
                    label="Data Processing Activity Inventory",
                    field_type=FieldType.TEXTAREA,
                    description="Comprehensive inventory of data processing activities",
                    required=True,
                    help_text="Document all data processing activities including collection, use, sharing, and retention"
                ),
                ComplianceField(
                    id="data_processing_purposes",
                    label="Data Processing Purposes",
                    field_type=FieldType.TEXTAREA,
                    description="Specific purposes for which personal data is processed",
                    required=True
                ),
                ComplianceField(
                    id="data_categories",
                    label="Categories of Personal Data",
                    field_type=FieldType.MULTISELECT,
                    description="Types of personal data processed by the system",
                    required=True,
                    options=["contact_info", "demographic", "biometric", "financial", "health", "location", "behavioral", "preference", "device_data"]
                ),
                ComplianceField(
                    id="privacy_risk_assessment",
                    label="Privacy Risk Assessment",
                    field_type=FieldType.TEXTAREA,
                    description="Assessment of privacy risks to individuals",
                    required=True
                )
            ]
        ),
        ComplianceSection(
            id="govern_p",
            title="GOVERN-P Function",
            description="Privacy governance policies and procedures",
            regulatory_reference="NIST Privacy Framework - Govern-P",
            fields=[
                ComplianceField(
                    id="privacy_governance_structure",
                    label="Privacy Governance Structure",
                    field_type=FieldType.TEXTAREA,
                    description="Organizational structure for privacy governance",
                    required=True
                ),
                ComplianceField(
                    id="data_minimization_policy",
                    label="Data Minimization Policies",
                    field_type=FieldType.TEXTAREA,
                    description="Policies for minimizing data collection and processing",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.PII_RULES: {"minimize_collection": True, "purpose_limitation": True}
                    }
                ),
                ComplianceField(
                    id="individual_rights_procedures",
                    label="Individual Rights Management",
                    field_type=FieldType.TEXTAREA,
                    description="Procedures for handling individual privacy rights requests",
                    required=True
                ),
                ComplianceField(
                    id="privacy_by_design",
                    label="Privacy by Design Implementation",
                    field_type=FieldType.TEXTAREA,
                    description="How privacy by design principles are implemented",
                    required=True
                )
            ]
        ),
        ComplianceSection(
            id="control_p",
            title="CONTROL-P Function",
            description="Data lifecycle controls and privacy protection measures",
            regulatory_reference="NIST Privacy Framework - Control-P",
            fields=[
                ComplianceField(
                    id="data_lifecycle_management",
                    label="Data Lifecycle Management",
                    field_type=FieldType.TEXTAREA,
                    description="Controls for managing data throughout its lifecycle",
                    required=True
                ),
                ComplianceField(
                    id="collection_controls",
                    label="Data Collection Controls",
                    field_type=FieldType.TEXTAREA,
                    description="Controls limiting data collection to what is necessary",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.PII_RULES: {"limit_collection": True}
                    }
                ),
                ComplianceField(
                    id="retention_policy",
                    label="Data Retention Policy",
                    field_type=FieldType.TEXTAREA,
                    description="Policy governing data retention periods and deletion",
                    required=True
                ),
                ComplianceField(
                    id="sharing_controls",
                    label="Data Sharing Controls",
                    field_type=FieldType.TEXTAREA,
                    description="Controls governing data sharing with third parties",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.ALLOWED_SOURCES: "restrict_sharing"
                    }
                ),
                ComplianceField(
                    id="access_controls",
                    label="Data Access Controls",
                    field_type=FieldType.TEXTAREA,
                    description="Controls limiting access to personal data",
                    required=True
                )
            ]
        ),
        ComplianceSection(
            id="communicate_p",
            title="COMMUNICATE-P Function",
            description="Privacy communication and transparency measures",
            regulatory_reference="NIST Privacy Framework - Communicate-P",
            fields=[
                ComplianceField(
                    id="privacy_notices",
                    label="Privacy Notice Content",
                    field_type=FieldType.TEXTAREA,
                    description="Clear and comprehensive privacy notices to individuals",
                    required=True
                ),
                ComplianceField(
                    id="consent_mechanisms",
                    label="Consent Collection Mechanisms",
                    field_type=FieldType.TEXTAREA,
                    description="Mechanisms for obtaining and managing individual consent",
                    required=True
                ),
                ComplianceField(
                    id="transparency_measures",
                    label="Transparency and Disclosure Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Measures to provide transparency about data processing",
                    required=True
                ),
                ComplianceField(
                    id="communication_channels",
                    label="Privacy Communication Channels",
                    field_type=FieldType.MULTISELECT,
                    description="Channels used for privacy-related communications",
                    required=True,
                    options=["website", "email", "mobile_app", "in_person", "phone", "mail"]
                )
            ]
        ),
        ComplianceSection(
            id="protect_p",
            title="PROTECT-P Function",
            description="Privacy protection safeguards and technical measures",
            regulatory_reference="NIST Privacy Framework - Protect-P",
            fields=[
                ComplianceField(
                    id="technical_safeguards",
                    label="Technical Privacy Safeguards",
                    field_type=FieldType.TEXTAREA,
                    description="Technical measures for protecting personal data",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.PII_RULES: {"encrypt_pii": True, "mask_pii": True}
                    }
                ),
                ComplianceField(
                    id="anonymization_measures",
                    label="Anonymization and Pseudonymization",
                    field_type=FieldType.TEXTAREA,
                    description="Techniques used for anonymizing or pseudonymizing data",
                    required=True,
                    enforcement_mapping={
                        EnforcementRule.PII_RULES: {"anonymize_pii": True}
                    }
                ),
                ComplianceField(
                    id="security_measures",
                    label="Data Security Measures",
                    field_type=FieldType.TEXTAREA,
                    description="Security measures protecting personal data from unauthorized access",
                    required=True
                ),
                ComplianceField(
                    id="privacy_incident_response",
                    label="Privacy Incident Response Procedures",
                    field_type=FieldType.TEXTAREA,
                    description="Procedures for responding to privacy incidents and breaches",
                    required=True
                )
            ]
        )
    ]
)


# ===============================
# TEMPLATE REGISTRY
# ===============================

REGULATORY_FRAMEWORKS = {
    "eu_ai_act_high_risk": EU_AI_ACT_HIGH_RISK_TEMPLATE,
    "nist_ai_rmf": NIST_AI_RMF_TEMPLATE,
    "nist_privacy": NIST_PRIVACY_TEMPLATE
}


def get_framework_template(framework_id: str) -> RegulatoryFramework:
    """Get regulatory framework template by ID."""
    if framework_id not in REGULATORY_FRAMEWORKS:
        raise ValueError(f"Unknown regulatory framework: {framework_id}")
    return REGULATORY_FRAMEWORKS[framework_id]


def get_available_frameworks() -> List[str]:
    """Get list of available regulatory framework IDs."""
    return list(REGULATORY_FRAMEWORKS.keys())


def validate_framework_config(framework_id: str, config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate a framework configuration against its template.
    
    Returns:
        Dict with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []
    
    try:
        framework = get_framework_template(framework_id)
    except ValueError as e:
        errors.append(str(e))
        return {"errors": errors, "warnings": warnings}
    
    # Check that all required fields are present
    for section in framework.sections:
        section_config = config.get(section.id, {})
        
        for field in section.fields:
            if field.required and field.id not in section_config:
                errors.append(f"Required field '{field.label}' missing in section '{section.title}'")
            
            # Validate field values if present
            if field.id in section_config:
                value = section_config[field.id]
                field_errors = _validate_field_value(field, value)
                errors.extend(field_errors)
    
    return {"errors": errors, "warnings": warnings}


def _validate_field_value(field: ComplianceField, value: Any) -> List[str]:
    """Validate individual field value against field definition."""
    errors = []
    
    if field.field_type == FieldType.SELECT and value not in field.options:
        errors.append(f"Invalid option '{value}' for field '{field.label}'. Must be one of: {field.options}")
    
    if field.field_type == FieldType.MULTISELECT:
        if not isinstance(value, list):
            errors.append(f"Field '{field.label}' must be a list")
        elif not all(v in field.options for v in value):
            invalid_options = [v for v in value if v not in field.options]
            errors.append(f"Invalid options {invalid_options} for field '{field.label}'. Valid options: {field.options}")
    
    if field.field_type == FieldType.NUMBER and field.validation_rules:
        try:
            num_value = float(value)
            if "min" in field.validation_rules and num_value < field.validation_rules["min"]:
                errors.append(f"Field '{field.label}' value {value} is below minimum {field.validation_rules['min']}")
            if "max" in field.validation_rules and num_value > field.validation_rules["max"]:
                errors.append(f"Field '{field.label}' value {value} is above maximum {field.validation_rules['max']}")
        except (ValueError, TypeError):
            errors.append(f"Field '{field.label}' must be a number")
    
    return errors
from __future__ import annotations

import re
from typing import List, Optional

try:
    # Pydantic v2
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - fallback for v1
    from pydantic import BaseModel, Field  # type: ignore


class SafetyIssue(BaseModel):
    """Represents a detected safety concern in model output."""

    kind: str = Field(description="Category of issue, e.g., 'pii', 'prompt_injection', 'toxicity'")
    severity: str = Field(description="Severity level: low|medium|high")
    message: str = Field(description="Human-readable explanation of the issue")
    start: Optional[int] = Field(default=None, description="Start index of match in text, if applicable")
    end: Optional[int] = Field(default=None, description="End index of match in text, if applicable")


class SafetyReport(BaseModel):
    """Aggregated result of safety evaluation."""

    issues: List[SafetyIssue] = Field(default_factory=list)
    is_safe: bool = Field(description="True when no issues detected")


class ResponseSafetyEngine:
    """Deterministic safety checker using simple regex/keyword heuristics.

    Detects:
    - Potential PII: emails, phone numbers
    - Prompt injection artifacts
    - Basic toxicity indicators
    """

    # Email detection (simplified RFC) - case-insensitive
    EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

    # Phone number detection (international/US-ish, conservative) - examples: +1 555-123-4567, (555) 123-4567, 555.123.4567, 5551234567
    PHONE_RE = re.compile(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
    )

    # Prompt injection phrases (lowercased match)
    PROMPT_INJECTION_PATTERNS = [
        r"\bignore\s+previous\s+instructions\b",
        r"\bdisregard\s+previous\s+instructions\b",
        r"\bignore\s+all\s+prior\s+instructions\b",
        r"\bforget\s+(?:the\s+)?rules\b",
        r"\boverride\s+(?:the\s+)?safety\b",
        r"\bdisable\s+safety\b",
        r"\bjailbreak\b",
        r"\bdeveloper\s+mode\b",
        r"\bdo\s+anything\s+now\b",
        r"\bas\s+an\s+ai\s+language\s+model,?\s*ignore\b",
        r"\bsystem\s+prompt\b",
    ]
    PROMPT_INJECTION_RES = [re.compile(pat, re.IGNORECASE) for pat in PROMPT_INJECTION_PATTERNS]

    # Basic toxicity indicators (non-exhaustive; mild, non-slur list)
    TOXIC_TERMS = [
        r"\bidiot\b",
        r"\bstupid\b",
        r"\bmoron\b",
        r"\bdumb\b",
        r"\bshut\s+up\b",
        r"\bhate\s+you\b",
        r"\bworthless\b",
        r"\btrash\b",
    ]
    TOXICITY_RES = [re.compile(pat, re.IGNORECASE) for pat in TOXIC_TERMS]

    def evaluate(self, text: str) -> SafetyReport:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        issues: List[SafetyIssue] = []

        # Detect PII: emails
        for m in self.EMAIL_RE.finditer(text):
            issues.append(
                SafetyIssue(
                    kind="pii",
                    severity="medium",
                    message="Potential email address detected",
                    start=m.start(),
                    end=m.end(),
                )
            )

        # Detect PII: phone numbers
        for m in self.PHONE_RE.finditer(text):
            issues.append(
                SafetyIssue(
                    kind="pii",
                    severity="medium",
                    message="Potential phone number detected",
                    start=m.start(),
                    end=m.end(),
                )
            )

        # Detect prompt injection phrases
        for rx in self.PROMPT_INJECTION_RES:
            for m in rx.finditer(text):
                issues.append(
                    SafetyIssue(
                        kind="prompt_injection",
                        severity="high",
                        message="Prompt-injection artifact detected",
                        start=m.start(),
                        end=m.end(),
                    )
                )

        # Detect toxicity
        for rx in self.TOXICITY_RES:
            for m in rx.finditer(text):
                issues.append(
                    SafetyIssue(
                        kind="toxicity",
                        severity="medium",
                        message="Toxic or harassing language detected",
                        start=m.start(),
                        end=m.end(),
                    )
                )

        return SafetyReport(issues=issues, is_safe=(len(issues) == 0))


__all__ = ["SafetyIssue", "SafetyReport", "ResponseSafetyEngine"]

"""
Simple pattern detectors for security and safety signals.

Each function returns a list of string markers explaining what was matched.
An empty list means no match.

- detect_prompt_injection: Finds common prompt-injection phrases.
- detect_secret_like: Finds strings that look like secrets or tokens.
- detect_pii_like: Finds common PII like emails, phones, SSNs, credit cards, IPs.

All functions are pure/deterministic and do not mutate inputs.
"""

from __future__ import annotations

import re
from typing import Iterable, List

__all__ = ["detect_prompt_injection", "detect_secret_like", "detect_pii_like"]


# -------------------------------
# Helpers
# -------------------------------

def _search_patterns(text: str, patterns: Iterable[tuple[str, re.Pattern]]) -> list[str]:
    """
    Search text for each compiled regex pattern and collect reason markers for matches.
    """
    hits: set[str] = set()
    for reason, rx in patterns:
        if rx.search(text):
            hits.add(reason)
    return sorted(hits)


def _luhn_valid(num: str) -> bool:
    """
    Validate a numeric string with the Luhn algorithm (used by credit cards).
    Accepts only digits, length 13-19.
    """
    if not num.isdigit():
        return False
    if not (13 <= len(num) <= 19):
        return False

    total = 0
    reverse_digits = list(map(int, num[::-1]))
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 1:  # double every second digit
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# -------------------------------
# Prompt Injection Detection
# -------------------------------

_PROMPT_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore_previous_instructions", re.compile(r"\bignore (all )?(the )?(previous|prior) instructions\b", re.IGNORECASE)),
    ("disregard_above_instructions", re.compile(r"\bdisregard (above|earlier) instructions\b", re.IGNORECASE)),
    ("override_instructions", re.compile(r"\boverride (the )?instructions\b", re.IGNORECASE)),
    ("dont_follow_policies", re.compile(r"\b(do not|don't) follow (any|the) (rules|policies|guidelines)\b", re.IGNORECASE)),
    ("reveal_system_prompt", re.compile(r"\b(reveal|show|print) (the )?(system|hidden) prompt\b", re.IGNORECASE)),
    ("exfiltrate_secrets", re.compile(r"\b(exfiltrat(e|ion)|leak|dump)\b.*\b(secret|key|credential|password|token)s?\b", re.IGNORECASE)),
    ("jailbreak_dan", re.compile(r"\b(jailbreak|do anything now|dan)\b", re.IGNORECASE)),
    ("act_as_system_root", re.compile(r"\bact as (system|root|administrator|sudo)\b", re.IGNORECASE)),
    ("bypass_safety", re.compile(r"\b(bypass|ignore)\b.*\b(safety|guardrails|filters|restrictions)\b", re.IGNORECASE)),
    ("run_shell_commands", re.compile(r"\brun\b.*\b(shell|bash|powershell|cmd) commands?\b", re.IGNORECASE)),
    ("as_a_language_model_bypass", re.compile(r"\bas a language model\b.*\b(ignore|disregard)\b", re.IGNORECASE)),
]


def detect_prompt_injection(text: str) -> list[str]:
    """
    Detect common prompt-injection phrases and tactics.

    Returns a list of reason markers for any matches.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return _search_patterns(text, _PROMPT_INJECTION_PATTERNS)


# -------------------------------
# Secret-like Detection
# -------------------------------

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    # AWS
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_temp_access_key_id", re.compile(r"\bASIA[0-9A-Z]{16}\b")),
    ("aws_secret_keyword", re.compile(r"(?i)\baws(.{0,20})?(secret|access)_?(key|token)\b")),
    # GitHub tokens
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36}\b")),
    ("github_user", re.compile(r"\bghu_[A-Za-z0-9]{36}\b")),
    ("github_server", re.compile(r"\bghs_[A-Za-z0-9]{36}\b")),
    # Slack tokens
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,48}\b")),
    # Google API key
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    # OpenAI style keys
    ("openai_key_like", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    # JWT tokens (3 base64url segments, typically starts with 'eyJ')
    ("jwt_token_like", re.compile(r"\beyJ[0-9A-Za-z_\-]{5,}\.[0-9A-Za-z_\-]{5,}\.[0-9A-Za-z_\-]{5,}\b")),
    # Private keys
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |DSA |EC |PGP |OPENSSH )?PRIVATE KEY-----")),
    # Azure Storage keys in connection strings
    ("azure_storage_key", re.compile(r"(?i)\b(AccountKey|SharedAccessKey)=([A-Za-z0-9+/=]{20,})")),
    # Generic secret assignments
    ("secret_assignment", re.compile(r"(?i)\b(secret|api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][^'\"\\]{8,}['\"]")),
]


def detect_secret_like(text: str) -> list[str]:
    """
    Detect strings that look like secrets, tokens, or private keys.

    Returns a list of reason markers for any matches.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return _search_patterns(text, _SECRET_PATTERNS)


# -------------------------------
# PII-like Detection
# -------------------------------

# Common PII patterns
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email_address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("us_phone_number", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b")),
    ("intl_phone_number", re.compile(r"\b\+\d{1,3}[-.\s]?(?:\d[-.\s]?){6,14}\b")),
    ("us_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("ipv4_address", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b")),
]

# Candidate detector for credit card numbers (validated with Luhn)
_CC_CANDIDATE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def detect_pii_like(text: str) -> list[str]:
    """
    Detect common PII indicators such as emails, phones, SSNs, IPs, and credit cards.

    Returns a list of reason markers for any matches.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    reasons = set(_search_patterns(text, _PII_PATTERNS))

    # Credit card detection with Luhn validation
    for match in _CC_CANDIDATE.findall(text):
        digits_only = re.sub(r"[ -]", "", match)
        if _luhn_valid(digits_only):
            reasons.add("credit_card_number")
            break  # one valid card is enough to flag

    return sorted(reasons)
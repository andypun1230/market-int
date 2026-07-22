from __future__ import annotations

import re
from typing import Iterable


PROMPT_INJECTION_PATTERNS = (
    r"\bignore (?:all |the |any )?(?:previous|prior|system|developer) instructions?\b",
    r"\breveal (?:the )?(?:system|developer|hidden) prompt\b",
    r"\bprint (?:the )?(?:system|developer|hidden) (?:message|instructions|prompt)\b",
    r"\bdisregard (?:the )?(?:rules|policy|instructions)\b",
    r"\byou are now\b",
    r"\b(?:reveal|show|print|expose|return)\b.{0,48}\b(?:api keys?|provider credentials?|authentication tokens?|provider tokens?)\b",
)

DIRECT_RECOMMENDATION_PATTERNS = (
    r"\b(?:you should|i recommend that you)\s+(?:buy|sell|short|own|purchase)\b",
    r"\b(?:buy|sell|short)\s+[A-Z]{1,5}\s+(?:now|today)\b",
    r"\bstrong buy\b",
)

OWNERSHIP_PATTERNS = (
    r"\byour (?:position|positions|holdings|exposure|portfolio beta|unrealized)\b",
    r"\byou (?:own|hold)\b",
)

UNSUPPORTED_CAUSALITY_PATTERNS = (
    r"\bcaused by\b",
    r"\bdrove (?:the |this )?(?:market|stock|move|rally|decline)\b",
    r"\btriggered (?:the |this )?(?:market|stock|move|rally|decline)\b",
    r"\btherefore caused\b",
)

UNSUPPORTED_CERTAINTY_PATTERNS = (
    r"\bwill definitely\b",
    r"\bguaranteed(?: returns?)?\b",
    r"\bcertain to\b",
    r"\bcannot (?:lose|fail)\b",
    r"\brisk[- ]free returns?\b",
)

UNSUPPORTED_FLOW_PATTERNS = (
    r"\binstitutional buying\b",
    r"\binstitutional accumulation\b",
    r"\bsmart money\b",
)

SECRET_PATTERNS = (
    r"\bsk-[A-Za-z0-9_-]{12,}\b",
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b",
    r"\b(?:api[_ -]?key|password|secret|token)\s*[:=]\s*\S+",
)


def contains_prompt_injection(text: str) -> bool:
    return matches_any(text, PROMPT_INJECTION_PATTERNS, ignore_case=True)


def recommendation_violations(text: str) -> list[str]:
    return matching_patterns(text, DIRECT_RECOMMENDATION_PATTERNS, ignore_case=True)


def ownership_violations(text: str) -> list[str]:
    return matching_patterns(text, OWNERSHIP_PATTERNS, ignore_case=True)


def causality_violations(text: str) -> list[str]:
    return matching_patterns(text, UNSUPPORTED_CAUSALITY_PATTERNS, ignore_case=True)


def certainty_violations(text: str) -> list[str]:
    return matching_patterns(text, UNSUPPORTED_CERTAINTY_PATTERNS, ignore_case=True)


def flow_claim_violations(text: str) -> list[str]:
    return matching_patterns(text, UNSUPPORTED_FLOW_PATTERNS, ignore_case=True)


def contains_secret(text: str) -> bool:
    return matches_any(text, SECRET_PATTERNS, ignore_case=True)


def matches_any(text: str, patterns: Iterable[str], *, ignore_case: bool = False) -> bool:
    flags = re.IGNORECASE if ignore_case else 0
    return any(re.search(pattern, text or "", flags=flags) for pattern in patterns)


def matching_patterns(text: str, patterns: Iterable[str], *, ignore_case: bool = False) -> list[str]:
    flags = re.IGNORECASE if ignore_case else 0
    return [pattern for pattern in patterns if re.search(pattern, text or "", flags=flags)]

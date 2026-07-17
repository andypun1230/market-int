from __future__ import annotations

import re
from typing import Any


UNAVAILABLE_LABEL = "Not enough data"


def format_copilot_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.upper() == "N/A":
        return UNAVAILABLE_LABEL
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = text.replace("_", " ").replace("-", " ")
    aliases = {
        "changepercent": "Daily change",
        "change percent": "Daily change",
        "high priority": "High priority",
        "near breakout": "Near breakout",
        "risk score": "Risk score",
        "setup updating": "Setup data updating",
        "mixed source": "Mixed data sources",
        "mixed sources": "Mixed data sources",
    }
    lowered = text.lower()
    if lowered in aliases:
        return aliases[lowered]
    return " ".join(word.capitalize() if word.isupper() is False else word for word in text.split())


def format_copilot_value(value: Any) -> str:
    if value is None or value == "":
        return UNAVAILABLE_LABEL
    if isinstance(value, float):
        return f"{value:.1f}"
    return format_copilot_label(value) if isinstance(value, str) else str(value)


def format_unavailable_reason(value: Any = None) -> str:
    label = format_copilot_label(value)
    if label == UNAVAILABLE_LABEL:
        return "The required app data is not available in this context."
    return f"{label} is unavailable in this context."


def compact_sentence_list(items: list[str], limit: int = 3) -> list[str]:
    output = []
    for item in items:
        cleaned = str(item or "").strip()
        if cleaned and cleaned not in output:
            output.append(cleaned.rstrip("."))
        if len(output) >= limit:
            break
    return output


def compact_answer(text: str, max_words: int = 180) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    truncated = " ".join(words[:max_words])
    last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    return (truncated[: last_period + 1] if last_period > 80 else truncated).strip()

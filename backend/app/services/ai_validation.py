from typing import Any


def valid_string(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback


def valid_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if items:
            return items[:6]

    return fallback


def valid_confidence(value: Any, fallback: int) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, round(value)))

    return fallback

from datetime import datetime, timezone
from typing import Any

from app.services.copilot_safety import remove_sensitive_values

MAX_LIST_ITEMS = 12
MAX_STRING_LENGTH = 900
MAX_DEPTH = 5


def sanitize_copilot_context(context: dict[str, Any]) -> dict[str, Any]:
    cleaned = remove_sensitive_values(context or {})
    if not isinstance(cleaned, dict):
        return {}
    return _compact_value(cleaned, depth=0)


def get_context_source_state(context: dict[str, Any]) -> str:
    source = context.get("sourceState") or context.get("source_state")
    if isinstance(source, str) and source in {"live", "delayed", "cached", "stale", "mock", "mixed", "unavailable"}:
        return source
    for key in ("market", "report", "stock", "sector", "theme", "watchlist"):
        section = context.get(key)
        if isinstance(section, dict):
            nested = section.get("sourceState") or section.get("source_state") or section.get("overall_mode")
            if isinstance(nested, str):
                return nested if nested in {"live", "delayed", "cached", "stale", "mock", "mixed"} else "unavailable"
    return "unavailable"


def build_context_labels(context: dict[str, Any]) -> list[str]:
    labels = []
    focused = context.get("focusedMetric")
    if isinstance(focused, dict):
        labels.append(str(focused.get("title") or "Focused Metric"))
    screen_type = context.get("screenType") or context.get("screen_type")
    if screen_type:
        labels.append(str(screen_type).title())
    for key, label in [
        ("report", "Daily Report"),
        ("market", "Market State"),
        ("stock", "Stock Detail"),
        ("sector", "Sector Context"),
        ("theme", "Theme Context"),
        ("watchlist", "Watchlist"),
    ]:
        if context.get(key):
            labels.append(label)
    return list(dict.fromkeys(labels))[:6]


def generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_value(value: Any, depth: int) -> Any:
    if depth > MAX_DEPTH:
        return None
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_compact_value(item, depth + 1) for item in value[:MAX_LIST_ITEMS]]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in list(value.items())[:80]:
            compacted = _compact_value(item, depth + 1)
            if compacted is not None:
                output[str(key)] = compacted
        return output
    return str(value)[:MAX_STRING_LENGTH]

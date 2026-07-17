from __future__ import annotations

from typing import Any

from app.services.ai_context import build_stock_ai_context
from app.services.copilot_formatting import format_copilot_label, format_copilot_value

STOPWORDS = {
    "AND",
    "THIS",
    "STOCK",
    "SECTOR",
    "THEME",
    "WITH",
    "COMPARE",
    "VS",
}


def resolve_comparison_entities(message: str, context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    symbols = extract_symbol_mentions(message)
    current_stock = current_stock_symbol(context)
    if current_stock and ("THIS" in message.upper() or "THIS STOCK" in message.upper()):
        symbols.insert(0, current_stock)

    context_items = get_context_entities(context)
    entities: list[dict[str, Any]] = []
    missing: list[str] = []

    for symbol in symbols:
        existing = next((item for item in context_items if entity_id(item) == symbol), None)
        if existing:
            entities.append(normalize_entity(existing))
            continue
        loaded = load_stock_entity(symbol)
        if loaded:
            entities.append(loaded)
        else:
            missing.append(symbol)

    if len(entities) < 2:
        for item in context_items:
            normalized = normalize_entity(item)
            if entity_id(normalized) not in {entity_id(entity) for entity in entities}:
                entities.append(normalized)
            if len(entities) >= 2:
                break

    return entities[:2], missing


def extract_symbol_mentions(message: str) -> list[str]:
    symbols: list[str] = []
    for token in message.replace("/", " ").replace(",", " ").split():
        cleaned = token.strip(".,?!:;()[]").upper()
        if not cleaned or cleaned in STOPWORDS:
            continue
        if cleaned.isalnum() and 1 <= len(cleaned) <= 5 and any(char.isalpha() for char in cleaned):
            symbols.append(cleaned)
    return list(dict.fromkeys(symbols))


def current_stock_symbol(context: dict[str, Any]) -> str | None:
    for path in ("stock.symbol", "stock.ticker", "stock.stock.symbol", "stock.stock.ticker"):
        value = value_at(context, path)
        if isinstance(value, str) and value:
            return value.upper()
    return None


def get_context_entities(context: dict[str, Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    stock = context.get("stock")
    if isinstance(stock, dict):
        entities.append(stock)
        nested_stock = stock.get("stock")
        if isinstance(nested_stock, dict):
            entities.append(nested_stock)
    watchlist = context.get("watchlist")
    if isinstance(watchlist, dict):
        items = watchlist.get("items")
        if isinstance(items, list):
            entities.extend(item for item in items if isinstance(item, dict))
    for key in ("sector", "theme"):
        item = context.get(key)
        if isinstance(item, dict):
            entities.append(item)
    return entities


def normalize_entity(item: dict[str, Any]) -> dict[str, Any]:
    symbol = item.get("ticker") or item.get("symbol") or value_at(item, "stock.ticker") or value_at(item, "stock.symbol")
    name = item.get("name") or symbol or item.get("id") or "Entity"
    return {
        "id": str(symbol or item.get("id") or name).upper(),
        "displayName": str(name),
        "type": "stock" if symbol else str(item.get("type") or "entity"),
        "score": item.get("score") or item.get("overall_score") or value_at(item, "stockRating.overall_score"),
        "signal": format_copilot_label(item.get("signal") or item.get("primarySignal") or item.get("rating") or item.get("status") or item.get("main_setup")),
        "risk": format_copilot_label(item.get("risk") or item.get("risk_flag") or item.get("riskLevel") or item.get("risk_level")),
        "dailyChangePercent": item.get("changePercent") or item.get("change_percent") or item.get("dailyChangePercent"),
        "relativeStrength": item.get("relativeStrength") or item.get("rs_rank") or value_at(item, "relativeStrength.score"),
        "momentum": format_copilot_label(item.get("momentum") or item.get("momentumLabel") or value_at(item, "multiTimeframeSignals.overallSignal")),
        "volumeState": format_copilot_label(item.get("volumeState") or value_at(item, "volumeAnalysis.volume_quality")),
        "setup": format_copilot_label(item.get("setup") or item.get("setupState") or item.get("main_setup")),
        "support": item.get("support") or value_at(item, "supportResistance.nearest_support"),
        "resistance": item.get("resistance") or value_at(item, "supportResistance.nearest_resistance"),
        "sourceState": item.get("sourceState") or item.get("dataStatus") or item.get("data_source") or "mixed",
    }


def load_stock_entity(symbol: str) -> dict[str, Any] | None:
    try:
        context = build_stock_ai_context(symbol)
    except Exception:
        return None
    return {
        "id": symbol.upper(),
        "displayName": symbol.upper(),
        "type": "stock",
        "score": context.get("score"),
        "signal": format_copilot_label(context.get("status") or context.get("rating")),
        "risk": format_copilot_label(context.get("risk_level")),
        "relativeStrength": format_copilot_value(context.get("relative_strength_status")),
        "momentum": format_copilot_label(context.get("multi_timeframe_alignment")),
        "volumeState": format_copilot_label(context.get("volume_quality")),
        "setup": format_copilot_label((context.get("main_pattern") or {}).get("name")),
        "sourceState": (context.get("data_quality") or {}).get("overall_mode", "mixed"),
    }


def entity_id(item: dict[str, Any]) -> str:
    return str(
        item.get("id")
        or item.get("ticker")
        or item.get("symbol")
        or value_at(item, "stock.ticker")
        or value_at(item, "stock.symbol")
        or item.get("name")
        or ""
    ).upper()


def value_at(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current

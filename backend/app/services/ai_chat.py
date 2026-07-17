from typing import Any

from app.services.ai_context import build_market_ai_context, build_stock_ai_context
from app.services.ai_prompts import AI_CHAT_SYSTEM_PROMPT
from app.services.ai_validation import valid_confidence, valid_string, valid_string_list
from app.services.openai_client import generate_structured_chat_response
from app.services.pattern_detection import WATCHLIST_SYMBOLS

DISCLAIMER = "This is educational market analysis only and not financial advice."


def answer_ai_chat(message: str, symbol: str | None = None) -> dict[str, Any]:
    normalized_message = message.strip()
    normalized_symbol = symbol.upper().strip() if symbol else None
    market_context = build_market_ai_context()
    stock_context = (
        build_stock_ai_context(normalized_symbol)
        if normalized_symbol
        else None
    )
    watchlist_context = None if normalized_symbol else build_watchlist_ai_context()
    context = {
        "market": market_context,
        "stock": stock_context,
        "watchlist": watchlist_context,
    }
    rule_response = build_rule_chat_response(
        message=normalized_message,
        market_context=market_context,
        stock_context=stock_context,
        watchlist_context=watchlist_context,
        symbol=normalized_symbol,
    )
    openai_response = generate_structured_chat_response(
        AI_CHAT_SYSTEM_PROMPT,
        {
            "question": normalized_message,
            "symbol": normalized_symbol,
            "context": context,
            "fallback_response": rule_response,
            "required_shape": "ai_chat_response",
        },
    )

    if openai_response:
        return merge_openai_chat_response(rule_response, openai_response)

    return rule_response


def build_watchlist_ai_context() -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []

    for symbol in WATCHLIST_SYMBOLS:
        try:
            contexts.append(build_stock_ai_context(symbol))
        except ValueError:
            continue

    return contexts


def build_rule_chat_response(
    message: str,
    market_context: dict[str, Any],
    stock_context: dict[str, Any] | None,
    watchlist_context: list[dict[str, Any]] | None,
    symbol: str | None,
) -> dict[str, Any]:
    if stock_context:
        return build_rule_stock_chat_response(message, stock_context, symbol)

    return build_rule_market_chat_response(market_context, watchlist_context)


def build_rule_market_chat_response(
    market_context: dict[str, Any],
    watchlist_context: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    top_sector_names = [
        sector.get("name", "N/A")
        for sector in market_context.get("top_sectors", [])[:3]
    ]
    related_symbols = [
        item.get("symbol", "")
        for item in (watchlist_context or [])[:3]
        if item.get("symbol")
    ]
    answer = (
        f"The market regime is {market_context.get('market_regime', 'N/A')}. "
        f"Breadth is {market_context.get('breadth_status', 'N/A')} with "
        f"{market_context.get('percent_above_50ema', 'N/A')}% above the 50EMA, "
        f"and institutional bias is {market_context.get('institutional_bias', 'N/A')}. "
        "The main focus is whether leadership remains concentrated or broadens."
    )

    return {
        "type": "ai_chat_response",
        "answer": answer,
        "key_points": [
            f"Market regime: {market_context.get('market_regime', 'N/A')}",
            f"Institutional bias: {market_context.get('institutional_bias', 'N/A')}",
            f"Top sectors: {', '.join(top_sector_names) if top_sector_names else 'N/A'}",
        ],
        "risks": market_context.get("key_risks", [])[:4],
        "what_to_watch": market_context.get("what_to_watch", [])[:4],
        "related_symbols": related_symbols,
        "confidence": 72,
        "generated_by": "rules",
        "disclaimer": DISCLAIMER,
    }


def build_rule_stock_chat_response(
    message: str,
    stock_context: dict[str, Any],
    symbol: str | None,
) -> dict[str, Any]:
    stock_symbol = symbol or stock_context.get("symbol", "N/A")
    advice_prefix = (
        "I cannot provide direct buy or sell instructions, but from an educational analysis view, "
        if asks_for_direct_advice(message)
        else ""
    )
    main_pattern = stock_context.get("main_pattern", {})
    answer = (
        f"{advice_prefix}{stock_symbol} is rated {stock_context.get('rating', 'N/A')} "
        f"with a score of {stock_context.get('score', 'N/A')} and "
        f"{stock_context.get('risk_level', 'N/A')} risk. Relative strength is "
        f"{stock_context.get('relative_strength_status', 'N/A')}, the main pattern is "
        f"{main_pattern.get('name', 'N/A')}, and volume quality is "
        f"{stock_context.get('volume_quality', 'N/A')}. The setup may be worth monitoring, "
        "but confirmation and risk control matter."
    )

    return {
        "type": "ai_chat_response",
        "answer": answer,
        "key_points": [
            f"Rating: {stock_context.get('rating', 'N/A')} / score {stock_context.get('score', 'N/A')}",
            f"Relative strength: {stock_context.get('relative_strength_status', 'N/A')}",
            f"Main pattern: {main_pattern.get('name', 'N/A')}",
            f"Multi-timeframe alignment: {stock_context.get('multi_timeframe_alignment', 'N/A')}",
        ],
        "risks": stock_context.get("warnings", [])[:4],
        "what_to_watch": stock_context.get("what_to_watch", [])[:4],
        "related_symbols": [stock_symbol],
        "confidence": 72,
        "generated_by": "rules",
        "disclaimer": DISCLAIMER,
    }


def asks_for_direct_advice(message: str) -> bool:
    lowered = message.lower()
    advice_phrases = [
        "should i buy",
        "should i sell",
        "buy now",
        "sell now",
        "is it a buy",
        "is it a sell",
    ]
    return any(phrase in lowered for phrase in advice_phrases)


def merge_openai_chat_response(
    fallback: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "ai_chat_response",
        "answer": valid_string(candidate.get("answer"), fallback["answer"]),
        "key_points": valid_string_list(candidate.get("key_points"), fallback["key_points"]),
        "risks": valid_string_list(candidate.get("risks"), fallback["risks"]),
        "what_to_watch": valid_string_list(
            candidate.get("what_to_watch"),
            fallback["what_to_watch"],
        ),
        "related_symbols": valid_string_list(
            candidate.get("related_symbols"),
            fallback["related_symbols"],
        ),
        "confidence": valid_confidence(candidate.get("confidence"), fallback["confidence"]),
        "generated_by": "openai",
        "disclaimer": valid_string(candidate.get("disclaimer"), fallback["disclaimer"]),
    }

from typing import Callable

from fastapi import APIRouter, HTTPException

from app.models.market import (
    AIChatRequest,
    AIChatResponse,
    AllStockAISummaryResponse,
    MarketAISummaryResponse,
    StockAISummaryResponse,
)
from app.services.ai_chat import answer_ai_chat
from app.services.ai_summary import (
    generate_all_stock_narratives,
    generate_market_narrative,
    generate_stock_narrative,
)
from app.services.ai_cache import (
    clear_ai_cache,
    get_ai_cache_status,
    get_cached_ai_summary,
    set_cached_ai_summary,
)
from app.services.openai_client import get_openai_status

router = APIRouter()


@router.get("/ai/market-summary", response_model=MarketAISummaryResponse)
async def get_ai_market_summary() -> MarketAISummaryResponse:
    """Return deterministic analyst-style market commentary."""
    return get_or_generate_cached_summary(
        "ai:market-summary",
        generate_market_narrative,
    )


@router.get("/ai/stock-summary/{symbol}", response_model=StockAISummaryResponse)
async def get_ai_stock_summary(symbol: str) -> StockAISummaryResponse:
    """Return deterministic analyst-style stock commentary."""
    try:
        normalized_symbol = symbol.upper()
        return get_or_generate_cached_summary(
            f"ai:stock-summary:{normalized_symbol}",
            lambda: generate_stock_narrative(normalized_symbol),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/ai/stock-summaries", response_model=AllStockAISummaryResponse)
async def get_ai_stock_summaries() -> AllStockAISummaryResponse:
    """Return deterministic analyst-style commentary for the watchlist universe."""
    return get_or_generate_cached_summary(
        "ai:stock-summaries",
        generate_all_stock_narratives,
    )


@router.get("/ai/status")
async def get_ai_status() -> dict[str, object]:
    """Return whether optional OpenAI summaries are enabled."""
    return get_openai_status()


@router.post("/ai/chat", response_model=AIChatResponse)
async def post_ai_chat(request: AIChatRequest) -> AIChatResponse:
    """Answer a grounded AI chat question using existing market engines."""
    normalized_message = normalize_chat_message(request.message)
    if not normalized_message:
        raise HTTPException(status_code=400, detail="Message is required.")

    normalized_symbol = request.symbol.upper() if request.symbol else None
    cache_key = f"ai:chat:{normalized_symbol or 'market'}:{normalized_message}"
    cached_response = get_cached_ai_summary(cache_key)
    if cached_response:
        return cached_response

    try:
        response = answer_ai_chat(normalized_message, normalized_symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    set_cached_ai_summary(cache_key, response, ttl_seconds=300)
    return response


@router.get("/ai/cache/status")
async def get_ai_cache_status_route() -> dict[str, object]:
    """Return in-memory AI summary cache status."""
    return get_ai_cache_status()


@router.post("/ai/cache/clear")
async def clear_ai_cache_route() -> dict[str, object]:
    """Clear the in-memory AI summary cache."""
    clear_ai_cache()
    return get_ai_cache_status()


def get_or_generate_cached_summary(
    key: str,
    generate: Callable[[], dict[str, object]],
) -> dict[str, object]:
    cached_summary = get_cached_ai_summary(key)
    if cached_summary:
        return with_cached_flag(cached_summary, cached=True)

    summary = generate()
    ttl_seconds = 600 if summary.get("generated_by") == "openai" else 120
    set_cached_ai_summary(key, without_cached_flag(summary), ttl_seconds=ttl_seconds)
    return with_cached_flag(summary, cached=False)


def with_cached_flag(summary: dict[str, object], cached: bool) -> dict[str, object]:
    next_summary = summary.copy()
    next_summary["cached"] = cached
    return next_summary


def without_cached_flag(summary: dict[str, object]) -> dict[str, object]:
    next_summary = summary.copy()
    next_summary.pop("cached", None)
    return next_summary


def normalize_chat_message(message: str) -> str:
    return " ".join(message.strip().split())

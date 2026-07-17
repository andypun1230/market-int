from app.models.market import MarketSentimentResponse, MarketSentimentSignal
from app.providers.selector import get_sentiment_provider
from app.services.service_cache import get_or_compute, get_service_ttl


def build_market_sentiment_dashboard() -> MarketSentimentResponse:
    return get_or_compute(
        "market-sentiment",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_market_sentiment_dashboard_uncached,
    )


def _build_market_sentiment_dashboard_uncached() -> MarketSentimentResponse:
    sentiment = get_sentiment_provider().get_market_sentiment()
    signals = [
        MarketSentimentSignal(
            key=component.key,
            label=component.label,
            score=round(component.score),
            status=component.status,
            value=component.value,
            previous_value=component.previous_value,
            trend=component.trend,
            explanation=component.explanation,
            metadata=component.metadata.model_dump(),
        )
        for component in sentiment.components
    ]
    strongest = max(signals, key=lambda item: item.score)
    weakest = min(signals, key=lambda item: item.score)

    return MarketSentimentResponse(
        score=round(sentiment.score),
        status=sentiment.status,
        confidence=sentiment.confidence,
        signals=signals,
        opportunities=[
            f"{strongest.label} is the strongest sentiment component.",
            "Constructive proxy sentiment supports selective participation when leadership confirms.",
        ],
        risks=[
            f"{weakest.label} is the weakest sentiment component.",
            "Proxy sentiment can reverse quickly if breadth or credit appetite weakens.",
        ],
        summary=sentiment.summary,
        methodology="APInvest Market Sentiment",
        official_index=False,
        metadata=sentiment.metadata.model_dump(),
        overall_mode=get_overall_mode(sentiment.metadata.model_dump(), signals),
        limitations=sentiment.metadata.warnings,
    )


def get_overall_mode(metadata: dict, signals: list[MarketSentimentSignal]) -> str:
    if metadata.get("is_live") and not metadata.get("fallback_used"):
        return "live"
    if any(signal.metadata and signal.metadata.get("is_live") for signal in signals):
        return "mixed"
    if metadata.get("fallback_used"):
        return "mixed"
    return "mock"

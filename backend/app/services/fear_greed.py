from app.models.market import FearGreedComponent, FearGreedResponse
from app.services.market_sentiment import build_market_sentiment_dashboard


def build_fear_greed_index() -> FearGreedResponse:
    sentiment = build_market_sentiment_dashboard()
    components = [
        FearGreedComponent(
            key=signal.key or signal.label.lower().replace(" ", "_"),
            label=signal.label,
            score=signal.score,
            status=classify_fear_greed(signal.score),
            explanation=signal.explanation,
        )
        for signal in sentiment.signals
    ]

    return FearGreedResponse(
        score=sentiment.score,
        status=classify_fear_greed(sentiment.score),
        components=components,
        summary=(
            "CNN-style proxy only: APInvest Market Sentiment components are mapped "
            "to a Fear & Greed-compatible response for backward compatibility."
        ),
    )


def classify_fear_greed(score: int) -> str:
    if score >= 75:
        return "Extreme Greed"
    if score >= 55:
        return "Greed"
    if score >= 45:
        return "Neutral"
    if score >= 25:
        return "Fear"
    return "Extreme Fear"

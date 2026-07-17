from app.providers.intelligence_models import MarketSentimentData
from app.providers.models import ProviderHealth


class SentimentProvider:
    def get_put_call_statistics(self) -> dict[str, object]:
        raise NotImplementedError

    def get_volatility_inputs(self) -> dict[str, object]:
        raise NotImplementedError

    def get_sentiment_health(self) -> ProviderHealth:
        raise NotImplementedError

    def get_market_sentiment(self) -> MarketSentimentData:
        raise NotImplementedError

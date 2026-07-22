from app.providers.news.base import NewsProvider
from app.providers.news.cached import CachedNewsProvider
from app.providers.news.hermetic import HermeticNewsProvider
from app.providers.news.models import (
    NewsProviderCapabilities,
    NewsProviderHealth,
    NewsProviderItem,
    NewsProviderRequest,
    NewsProviderResponse,
)
from app.providers.news.unavailable import UnavailableNewsProvider


def get_default_news_provider() -> NewsProvider:
    """Never infer entitlement from unrelated market-data credentials."""

    return UnavailableNewsProvider()


__all__ = [
    "CachedNewsProvider",
    "HermeticNewsProvider",
    "NewsProvider",
    "NewsProviderCapabilities",
    "NewsProviderHealth",
    "NewsProviderItem",
    "NewsProviderRequest",
    "NewsProviderResponse",
    "UnavailableNewsProvider",
    "get_default_news_provider",
]

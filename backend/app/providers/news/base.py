from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.news.models import (
    NewsProviderCapabilities,
    NewsProviderHealth,
    NewsProviderRequest,
    NewsProviderResponse,
)


class NewsProvider(ABC):
    """Provider-neutral metadata interface for event intelligence ingestion."""

    @abstractmethod
    def fetch_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        raise NotImplementedError

    def fetch_events_by_ticker(
        self,
        request: NewsProviderRequest,
        symbols: tuple[str, ...],
    ) -> NewsProviderResponse:
        return self.fetch_events(
            NewsProviderRequest(**{**request.model_dump(), "symbols": symbols})
        )

    def fetch_macro_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        return self.fetch_events(
            NewsProviderRequest(**{**request.model_dump(), "macro_only": True})
        )

    def fetch_official_releases(self, request: NewsProviderRequest) -> NewsProviderResponse:
        return self.fetch_events(
            NewsProviderRequest(**{**request.model_dump(), "official_only": True})
        )

    def fetch_earnings_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        return self.fetch_events(
            NewsProviderRequest(**{**request.model_dump(), "earnings_only": True})
        )

    @abstractmethod
    def health(self) -> NewsProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> NewsProviderCapabilities:
        raise NotImplementedError

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.intelligence.news.contracts import (
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
)
from app.providers.news.base import NewsProvider
from app.providers.news.models import (
    NewsProviderCapabilities,
    NewsProviderHealth,
    NewsProviderRequest,
    NewsProviderResponse,
)


class UnavailableNewsProvider(NewsProvider):
    """Production-safe default when no licensed provider is configured."""

    def __init__(
        self,
        *,
        reason: str = "No licensed News Intelligence provider is configured.",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.reason = reason
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        return NewsProviderResponse(
            items=(),
            provenance=NewsProviderProvenance(
                provider="unavailable",
                mode=NewsProviderMode.UNAVAILABLE,
                source_state=NewsFreshnessState.UNAVAILABLE,
                as_of=request.as_of,
                fetched_at=self._clock(),
                cache_hit=False,
                fallback_reason=self.reason,
                errors=("news_provider_unavailable",),
                latency_ms=0,
            ),
        )

    def health(self) -> NewsProviderHealth:
        return NewsProviderHealth(
            provider="unavailable",
            mode=NewsProviderMode.UNAVAILABLE,
            reachable=False,
            checked_at=self._clock(),
            message=self.reason,
        )

    def capabilities(self) -> NewsProviderCapabilities:
        return NewsProviderCapabilities(
            provider="unavailable",
            mode=NewsProviderMode.UNAVAILABLE,
            fetch_by_time_range=False,
            fetch_by_ticker=False,
            fetch_macro_events=False,
            fetch_official_releases=False,
            fetch_earnings_events=False,
            supports_pagination=False,
        )

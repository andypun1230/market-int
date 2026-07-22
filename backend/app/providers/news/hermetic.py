from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.intelligence.news.contracts import (
    NewsEventType,
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
)
from app.providers.news.base import NewsProvider
from app.providers.news.models import (
    NewsProviderCapabilities,
    NewsProviderHealth,
    NewsProviderItem,
    NewsProviderRequest,
    NewsProviderResponse,
)


MACRO_EVENT_TYPES = frozenset(
    {
        NewsEventType.MONETARY_POLICY,
        NewsEventType.INFLATION,
        NewsEventType.EMPLOYMENT,
        NewsEventType.ECONOMIC_GROWTH,
        NewsEventType.GOVERNMENT_POLICY,
        NewsEventType.GEOPOLITICS,
    }
)


class HermeticNewsProvider(NewsProvider):
    """Explicit deterministic fixture provider; it can never identify as live."""

    def __init__(
        self,
        items: tuple[NewsProviderItem, ...],
        *,
        provider_name: str = "hermetic-news",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._items = items
        self.provider_name = provider_name
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        selected = [item for item in self._items if self._matches(item, request)]
        offset = int(request.cursor or 0) if (request.cursor or "").isdigit() else 0
        page = tuple(selected[offset : offset + request.limit])
        next_offset = offset + len(page)
        return NewsProviderResponse(
            items=page,
            provenance=NewsProviderProvenance(
                provider=self.provider_name,
                mode=NewsProviderMode.HERMETIC,
                source_state=NewsFreshnessState.TEST,
                as_of=request.as_of,
                fetched_at=self._clock(),
                cache_hit=False,
                errors=(),
                latency_ms=0,
            ),
            next_cursor=str(next_offset) if next_offset < len(selected) else None,
        )

    def health(self) -> NewsProviderHealth:
        return NewsProviderHealth(
            provider=self.provider_name,
            mode=NewsProviderMode.HERMETIC,
            reachable=True,
            checked_at=self._clock(),
            message="Explicit hermetic fixture provider is available.",
        )

    def capabilities(self) -> NewsProviderCapabilities:
        return NewsProviderCapabilities(
            provider=self.provider_name,
            mode=NewsProviderMode.HERMETIC,
            fetch_by_time_range=True,
            fetch_by_ticker=True,
            fetch_macro_events=True,
            fetch_official_releases=True,
            fetch_earnings_events=True,
            supports_pagination=True,
        )

    @staticmethod
    def _matches(item: NewsProviderItem, request: NewsProviderRequest) -> bool:
        published = item.published_at
        if published is not None and request.start_at and published < request.start_at:
            return False
        if published is not None and request.end_at and published > request.end_at:
            return False
        if request.symbols and not set(request.symbols).intersection(item.structured_symbols):
            return False
        if request.event_types and item.structured_event_type not in request.event_types:
            return False
        if request.macro_only and item.structured_event_type not in MACRO_EVENT_TYPES:
            return False
        if request.official_only and not item.is_official_release:
            return False
        if request.earnings_only and item.structured_event_type != NewsEventType.EARNINGS:
            return False
        return True

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.intelligence.news.contracts import (
    CorrectionStatus,
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
from app.repositories.news import NewsMetadataQuery, NewsMetadataReader, StoredNewsEventMetadata


class CachedNewsProvider(NewsProvider):
    """Explicit metadata-cache provider; absence never triggers fixture fallback."""

    def __init__(
        self,
        repository: NewsMetadataReader,
        *,
        event_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.event_id = event_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch_events(self, request: NewsProviderRequest) -> NewsProviderResponse:
        if self.event_id is not None:
            selected = self.repository.get(self.event_id)
            metadata = (
                self.repository.get_cluster(selected.cluster_id)
                if selected is not None and hasattr(self.repository, "get_cluster")
                else (selected,) if selected is not None else ()
            )
        else:
            metadata = self.repository.query(
                NewsMetadataQuery(
                    start_at=request.start_at,
                    end_at=request.end_at,
                    symbols=request.symbols,
                    event_types=request.event_types,
                    limit=request.limit,
                )
            )
        items = tuple(self._to_provider_item(item) for item in metadata)
        return NewsProviderResponse(
            items=items,
            provenance=NewsProviderProvenance(
                provider="news-metadata-cache",
                mode=NewsProviderMode.CACHED,
                source_state=(
                    NewsFreshnessState.CACHED if items else NewsFreshnessState.UNAVAILABLE
                ),
                as_of=request.as_of,
                fetched_at=self._clock(),
                cache_hit=bool(items),
                fallback_reason=(
                    None
                    if items
                    else "news_metadata_event_not_found"
                    if self.event_id is not None
                    else "news_metadata_cache_empty"
                ),
                errors=() if items else ("cached_news_unavailable",),
                latency_ms=0,
            ),
        )

    def health(self) -> NewsProviderHealth:
        return NewsProviderHealth(
            provider="news-metadata-cache",
            mode=NewsProviderMode.CACHED,
            reachable=True,
            checked_at=self._clock(),
            message="Metadata-only News Intelligence cache is readable.",
        )

    def capabilities(self) -> NewsProviderCapabilities:
        return NewsProviderCapabilities(
            provider="news-metadata-cache",
            mode=NewsProviderMode.CACHED,
            fetch_by_time_range=True,
            fetch_by_ticker=True,
            fetch_macro_events=True,
            fetch_official_releases=False,
            fetch_earnings_events=True,
            supports_pagination=False,
        )

    @staticmethod
    def _to_provider_item(item: StoredNewsEventMetadata) -> NewsProviderItem:
        symbols = item.named_symbols
        return NewsProviderItem(
            provider_event_id=item.provider_metadata.provider_event_id,
            headline=item.canonical_headline,
            summary="",
            source_identifier=item.source_identifier,
            source_name=item.source_name,
            source_url=item.source_url,
            published_at=item.published_at,
            updated_at=item.updated_at,
            first_seen_at=item.first_seen_at,
            language=item.language,
            structured_event_type=item.event_type,
            structured_event_subtype=item.event_subtype,
            structured_symbols=symbols,
            confirmed_facts=(),
            event_status=item.event_status,
            correction_status=(
                item.correction.status
                if item.correction.status != CorrectionStatus.SUPERSEDED
                else CorrectionStatus.NONE
            ),
            supersedes_provider_event_id=item.correction.supersedes_event_id,
            superseded_by_provider_event_id=item.correction.superseded_by_event_id,
            correction_reason=item.correction.correction_reason,
            canonical_event_reference=item.cluster_id,
            expected_direction=item.expected_direction,
            is_official_release=item.primary_source,
            origin_provider=item.provider_metadata.provider,
            origin_provider_mode=item.provider_metadata.provider_mode,
            origin_fetched_at=item.provider_metadata.fetched_at,
        )

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from app.analysis_engines.evidence_validation import EvidenceValidationEngine
from app.intelligence.news.contracts import (
    CorrectionStatus,
    NewsContractModel,
    NewsClusterSourceMember,
    NewsEventCluster,
    NewsEventRecord,
    NewsEventStatus,
    SourceQuality,
)


NEWS_CLUSTERING_VERSION = "news-clustering-v1"
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "is",
        "its",
        "of",
        "on",
        "says",
        "the",
        "to",
        "with",
    }
)
QUALITY_RANK = {
    SourceQuality.PRIMARY: 0,
    SourceQuality.HIGH_CONFIDENCE_SECONDARY: 1,
    SourceQuality.SUPPORTING_SECONDARY: 2,
    SourceQuality.UNVERIFIED: 3,
    SourceQuality.UNAVAILABLE: 4,
}
STATUS_RANK = {
    NewsEventStatus.CONFIRMED: 0,
    NewsEventStatus.CORRECTED: 1,
    NewsEventStatus.DEVELOPING: 2,
    NewsEventStatus.DISPUTED: 3,
    NewsEventStatus.UNVERIFIED: 4,
    NewsEventStatus.RETRACTED: 5,
}


class NewsClusteringResult(NewsContractModel):
    events: tuple[NewsEventRecord, ...]
    clusters: tuple[NewsEventCluster, ...]
    exact_duplicate_count: int
    conflicting_duplicate_ids: tuple[str, ...] = ()
    engine_version: str = NEWS_CLUSTERING_VERSION


class NewsClusteringEngine:
    version = NEWS_CLUSTERING_VERSION

    def __init__(self, *, similarity_threshold: float = 0.55, max_hours: int = 48) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_seconds = max_hours * 3600
        self.evidence_engine = EvidenceValidationEngine()

    def cluster(
        self,
        events: tuple[NewsEventRecord, ...],
        *,
        entity_symbols_by_event: dict[str, tuple[str, ...]] | None = None,
    ) -> NewsClusteringResult:
        deduped = self.evidence_engine.deduplicate(
            events,
            identity=lambda event: event.event_id,
            fingerprint=lambda event: event.model_dump(mode="json"),
        )
        items = list(deduped.items)
        if not items:
            return NewsClusteringResult(
                events=(),
                clusters=(),
                exact_duplicate_count=deduped.duplicate_count,
                conflicting_duplicate_ids=tuple(
                    collision.identity for collision in deduped.collisions
                ),
            )

        symbols = entity_symbols_by_event or {}
        parent = list(range(len(items)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[max(left_root, right_root)] = min(left_root, right_root)

        by_reference: dict[str, int] = {}
        by_provider_reference: dict[str, int] = {}
        for index, event in enumerate(items):
            provider_reference = (
                f"provider:{event.provider_metadata.provider}:"
                f"{event.provider_metadata.provider_event_id}"
            )
            by_provider_reference[provider_reference] = index
            canonical = event.provider_metadata.canonical_event_reference
            if canonical:
                if canonical in by_reference:
                    union(index, by_reference[canonical])
                else:
                    by_reference[canonical] = index

        for index, event in enumerate(items):
            for related in (
                event.correction.supersedes_event_id,
                event.correction.superseded_by_event_id,
            ):
                if related and related in by_provider_reference:
                    union(index, by_provider_reference[related])

        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                if find(left) == find(right):
                    continue
                if self._same_underlying_event(items[left], items[right], symbols):
                    union(left, right)

        grouped: dict[int, list[NewsEventRecord]] = defaultdict(list)
        for index, event in enumerate(items):
            grouped[find(index)].append(event)

        output_events: list[NewsEventRecord] = []
        clusters: list[NewsEventCluster] = []
        for members in grouped.values():
            members.sort(key=lambda event: (event.published_at, event.event_id))
            earliest = members[0]
            canonical = min(members, key=self._canonical_rank)
            cluster_id = f"news-cluster-{self._digest(earliest.event_id)}"
            updated_members = tuple(
                self._replace_event(event, cluster_id=cluster_id) for event in members
            )
            output_events.extend(updated_members)
            primary = next((event for event in updated_members if event.primary_source), None)
            corrections = tuple(
                event.event_id
                for event in updated_members
                if event.event_status in {NewsEventStatus.CORRECTED, NewsEventStatus.RETRACTED}
                or event.correction.status != CorrectionStatus.NONE
            )
            contradictions = tuple(
                event.event_id
                for event in updated_members
                if event.event_status in {NewsEventStatus.DISPUTED, NewsEventStatus.RETRACTED}
            )
            clusters.append(
                NewsEventCluster(
                    cluster_id=cluster_id,
                    canonical_event_id=canonical.event_id,
                    member_event_ids=tuple(event.event_id for event in updated_members),
                    earliest_event_id=earliest.event_id,
                    primary_source_event_id=primary.event_id if primary else None,
                    update_event_ids=tuple(
                        event.event_id
                        for event in updated_members
                        if event.event_id != canonical.event_id
                    ),
                    correction_event_ids=corrections,
                    contradiction_event_ids=contradictions,
                    duplicate_count=max(0, len(updated_members) - 1),
                    source_count=len({event.source_identifier for event in updated_members}),
                    source_members=tuple(
                        NewsClusterSourceMember(
                            event_id=event.event_id,
                            source_identifier=event.source_identifier,
                            source_name=event.source_name,
                            source_url=event.source_url,
                            source_quality=event.source_quality,
                            primary_source=event.primary_source,
                            published_at=event.published_at,
                            updated_at=event.updated_at,
                            event_status=event.event_status,
                            correction=event.correction,
                            provider=event.provider_metadata.provider,
                            provider_event_id=event.provider_metadata.provider_event_id,
                        )
                        for event in updated_members
                    ),
                    cluster_version=NEWS_CLUSTERING_VERSION,
                )
            )
        output_events.sort(key=lambda event: (event.published_at, event.event_id))
        clusters.sort(key=lambda cluster: cluster.cluster_id)
        return NewsClusteringResult(
            events=tuple(output_events),
            clusters=tuple(clusters),
            exact_duplicate_count=deduped.duplicate_count,
            conflicting_duplicate_ids=tuple(
                collision.identity for collision in deduped.collisions
            ),
        )

    def _same_underlying_event(
        self,
        left: NewsEventRecord,
        right: NewsEventRecord,
        symbols: dict[str, tuple[str, ...]],
    ) -> bool:
        if left.event_type != right.event_type:
            return False
        if abs((left.published_at - right.published_at).total_seconds()) > self.max_seconds:
            return False
        left_symbols = set(symbols.get(left.event_id, ()))
        right_symbols = set(symbols.get(right.event_id, ()))
        if left_symbols and right_symbols and not left_symbols.intersection(right_symbols):
            return False
        left_tokens = self._tokens(left.canonical_headline)
        right_tokens = self._tokens(right.canonical_headline)
        if not left_tokens or not right_tokens:
            return False
        similarity = len(left_tokens.intersection(right_tokens)) / len(
            left_tokens.union(right_tokens)
        )
        required = self.similarity_threshold if (left_symbols or right_symbols) else 0.65
        return similarity >= required

    @staticmethod
    def _canonical_rank(event: NewsEventRecord) -> tuple[object, ...]:
        return (
            event.quarantined,
            QUALITY_RANK[event.source_quality],
            STATUS_RANK[event.event_status],
            event.published_at,
            event.event_id,
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9]+", value.casefold())
        return {
            NewsClusteringEngine._stem(token)
            for token in tokens
            if len(token) > 1 and token not in STOPWORDS
        }

    @staticmethod
    def _stem(value: str) -> str:
        for suffix in ("ing", "ed", "es", "s"):
            if value.endswith(suffix) and len(value) > len(suffix) + 3:
                return value[: -len(suffix)]
        return value

    @staticmethod
    def _replace_event(event: NewsEventRecord, **updates: object) -> NewsEventRecord:
        payload = event.model_dump(mode="python")
        payload.update(updates)
        return NewsEventRecord.model_validate(payload)

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

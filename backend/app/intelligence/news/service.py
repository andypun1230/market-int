from __future__ import annotations

import hashlib
import threading
from datetime import datetime
from time import perf_counter

from app.analysis_engines.confidence import (
    ConfidenceAdjustmentEngine,
    ConfidenceAdjustmentInput,
)
from app.analysis_engines.contradiction import (
    ContradictionAnalysisInput,
    ContradictionEngine,
    ContradictionFinding,
    ContradictionPreservationInput,
)
from app.analysis_engines.evidence_validation import EvidenceValidationEngine, SourceRecord
from app.analysis_engines.freshness import (
    FreshnessAvailabilityEngine,
    FreshnessAvailabilityInput,
    FreshnessSummaryInput,
)
from app.analysis_engines.news.clustering import NewsClusteringEngine
from app.analysis_engines.news.entity_mapping import (
    NewsEntityMappingContext,
    NewsEntityMappingEngine,
)
from app.analysis_engines.news.materiality import NewsMaterialityEngine
from app.analysis_engines.news.normalization import NewsNormalizationEngine
from app.analysis_engines.news.reaction import NewsMarketReactionEngine
from app.intelligence.news.contracts import (
    ConfidenceLabel,
    EntityType,
    MaterialityInputs,
    MarketReactionObservation,
    NewsAvailability,
    NewsContradiction,
    NewsDeepLink,
    NewsEventCluster,
    NewsEventRecord,
    NewsEventStatus,
    NewsEvidenceRecord,
    NewsFreshness,
    NewsFreshnessState,
    NewsIntelligenceResult,
    NewsProcessingMetrics,
    NewsProviderMode,
    NewsProviderProvenance,
    NewsQuery,
    NewsQueryMode,
    NewsServiceStatus,
    ReactionClassification,
    SourceQuality,
)
from app.providers.news import (
    CachedNewsProvider,
    NewsProvider,
    NewsProviderRequest,
    UnavailableNewsProvider,
    get_default_news_provider,
)
from app.repositories.news import NewsMetadataReader, NewsMetadataWriter


INDEX_ENTITY_ALIASES = {
    "SPY": frozenset({"index:s_p_500"}),
    "QQQ": frozenset({"index:nasdaq_100"}),
    "IWM": frozenset({"index:russell_2000"}),
    "DIA": frozenset({"index:dow_jones_industrial_average"}),
}


class NewsIntelligenceService:
    """Single deterministic News Intelligence orchestration boundary."""

    def __init__(
        self,
        *,
        provider: NewsProvider | None = None,
        repository: NewsMetadataReader | NewsMetadataWriter | None = None,
        normalizer: NewsNormalizationEngine | None = None,
        mapper: NewsEntityMappingEngine | None = None,
        clustering: NewsClusteringEngine | None = None,
        materiality: NewsMaterialityEngine | None = None,
        reaction: NewsMarketReactionEngine | None = None,
    ) -> None:
        self.provider = provider or get_default_news_provider()
        self.repository = repository
        self.normalizer = normalizer or NewsNormalizationEngine()
        self.mapper = mapper or NewsEntityMappingEngine()
        self.clustering = clustering or NewsClusteringEngine()
        self.materiality = materiality or NewsMaterialityEngine()
        self.reaction = reaction or NewsMarketReactionEngine()
        self.freshness_engine = FreshnessAvailabilityEngine()
        self.evidence_engine = EvidenceValidationEngine()
        self.contradiction_engine = ContradictionEngine()
        self.confidence_engine = ConfidenceAdjustmentEngine()

    def query(
        self,
        query: NewsQuery,
        *,
        reaction_observations: tuple[MarketReactionObservation, ...] = (),
        watchlist_symbols: tuple[str, ...] = (),
    ) -> NewsIntelligenceResult:
        started = perf_counter()
        provider_started = perf_counter()
        try:
            response = self.provider.fetch_events(self._provider_request(query))
        except Exception as exc:
            provenance = NewsProviderProvenance(
                provider=type(self.provider).__name__,
                mode=NewsProviderMode.UNAVAILABLE,
                source_state=NewsFreshnessState.UNAVAILABLE,
                as_of=query.as_of,
                fetched_at=query.as_of,
                cache_hit=False,
                fallback_reason="News provider request failed; no replacement data was fabricated.",
                errors=(f"news_provider_failure:{type(exc).__name__}",),
                latency_ms=self._elapsed_ms(provider_started),
            )
            return self._unavailable_result(query, provenance)
        provider_ms = self._elapsed_ms(provider_started)
        if response.provenance.mode == NewsProviderMode.UNAVAILABLE:
            return self._unavailable_result(
                query,
                response.provenance,
                metrics=NewsProcessingMetrics(
                    provider_fetch_ms=provider_ms,
                    total_ms=self._elapsed_ms(started),
                ),
            )

        errors: list[str] = list(response.provenance.errors)
        limitations: list[str] = [
            "No exchange-holiday or shortened-session calendar is available; session phase uses weekday clock boundaries.",
            "Only daily market-reaction windows are supported by configured market data.",
        ]
        normalize_started = perf_counter()
        normalized: list[NewsEventRecord] = []
        evidence: list[NewsEvidenceRecord] = []
        item_by_event: dict[str, object] = {}
        for item in response.items:
            try:
                result = self.normalizer.normalize(item, response.provenance, now=query.as_of)
            except Exception as exc:
                errors.append(
                    f"news_normalization_failure:{item.provider_event_id}:{type(exc).__name__}"
                )
                continue
            errors.extend(issue.code for issue in result.issues)
            if result.event is None:
                continue
            normalized.append(result.event)
            evidence.extend(result.evidence)
            item_by_event[result.event.event_id] = item
        normalization_ms = self._elapsed_ms(normalize_started)

        mapping_started = perf_counter()
        mapped_events: list[NewsEventRecord] = []
        symbols_by_event: dict[str, tuple[str, ...]] = {}
        for event in normalized:
            item = item_by_event[event.event_id]
            candidate_symbols = tuple(getattr(item, "structured_symbols", ()))
            symbols_by_event[event.event_id] = candidate_symbols
            if event.quarantined:
                mapped_events.append(event)
                limitations.append(f"{event.event_id}:untrusted content quarantined")
                continue
            try:
                mapping = self.mapper.map_event(
                    event,
                    NewsEntityMappingContext(
                        candidate_symbols=candidate_symbols,
                        candidate_company_names=tuple(
                            getattr(item, "structured_company_names", ())
                        ),
                        watchlist_symbols=watchlist_symbols,
                    ),
                    now=query.as_of,
                )
            except Exception as exc:
                errors.append(
                    f"news_entity_mapping_failure:{event.event_id}:{type(exc).__name__}"
                )
                mapped_events.append(event)
                continue
            errors.extend(mapping.rejected_candidates)
            evidence.extend(mapping.evidence)
            mapped_events.append(
                self._replace_event(
                    event,
                    affected_entities=mapping.mappings,
                    affected_sectors=tuple(
                        dict.fromkeys(
                            item.display_name
                            for item in mapping.mappings
                            if item.entity_type == EntityType.SECTOR
                        )
                    ),
                    affected_themes=tuple(
                        dict.fromkeys(
                            item.entity_id
                            for item in mapping.mappings
                            if item.entity_type == EntityType.THEME
                        )
                    ),
                    affected_indexes=tuple(
                        dict.fromkeys(
                            item.display_name
                            for item in mapping.mappings
                            if item.entity_type == EntityType.INDEX
                        )
                    ),
                    evidence_ids=tuple(
                        dict.fromkeys(
                            (*event.evidence_ids, *(item.evidence_id for item in mapping.mappings))
                        )
                    ),
                )
            )
        mapping_ms = self._elapsed_ms(mapping_started)

        clustering_started = perf_counter()
        clustered = self.clustering.cluster(
            tuple(mapped_events),
            entity_symbols_by_event=symbols_by_event,
        )
        clustering_ms = self._elapsed_ms(clustering_started)
        errors.extend(
            f"conflicting_duplicate_event:{event_id}"
            for event_id in clustered.conflicting_duplicate_ids
        )

        analysis_started = perf_counter()
        reaction_ms = 0.0
        materiality_ms = 0.0
        cluster_by_event = {
            event_id: cluster
            for cluster in clustered.clusters
            for event_id in cluster.member_event_ids
        }
        cluster_events = self._propagate_cluster_mappings(
            clustered.events,
            clustered.clusters,
        )
        enriched_events: list[NewsEventRecord] = []
        for event in cluster_events:
            observations = tuple(
                self._reaction_for_event(observation, event.event_id)
                for observation in reaction_observations
                if observation.event_id
                in {event.event_id, event.provider_metadata.provider_event_id}
            )
            reaction_started = perf_counter()
            reaction_result = self.reaction.assess(
                event_id=event.event_id,
                expected_direction=event.expected_direction,
                observations=observations,
            )
            reaction_ms += self._elapsed_ms(reaction_started)
            evidence.extend(reaction_result.evidence)
            cluster = cluster_by_event[event.event_id]
            inputs = self._materiality_inputs(
                event,
                duplicate_count=cluster.duplicate_count,
                reaction_result=reaction_result,
            )
            materiality_started = perf_counter()
            assessment = self.materiality.assess(inputs, source_quality=event.source_quality)
            materiality_ms += self._elapsed_ms(materiality_started)
            enriched_events.append(
                self._replace_event(
                    event,
                    materiality_inputs=inputs,
                    materiality=assessment,
                    reaction=reaction_result.assessment,
                    evidence_ids=tuple(
                        dict.fromkeys(
                            (*event.evidence_ids, *(item.evidence_id for item in reaction_result.evidence))
                        )
                    ),
                )
            )
        materiality_reaction_ms = self._elapsed_ms(analysis_started)

        events_by_id = {event.event_id: event for event in enriched_events}
        contradictions = self._contradictions(tuple(enriched_events), clustered.clusters)
        evidence_result = self.evidence_engine.deduplicate(
            evidence,
            identity=lambda item: item.evidence_id,
            fingerprint=lambda item: item.model_dump(mode="json"),
        )
        errors.extend(
            f"conflicting_duplicate_evidence:{collision.identity}"
            for collision in evidence_result.collisions
        )
        validated_evidence = tuple(
            item
            for item in evidence_result.items
            if self._valid_evidence_lineage(item, events_by_id)
        )
        if len(validated_evidence) != len(evidence_result.items):
            errors.append("invalid_evidence_lineage")

        canonical = tuple(
            events_by_id[cluster.canonical_event_id]
            for cluster in clustered.clusters
            if cluster.canonical_event_id in events_by_id
        )
        selected = tuple(
            event
            for event in canonical
            if self._matches_query(event, query)
            and event.materiality is not None
            and event.materiality.market_materiality >= query.minimum_materiality
        )
        selected = tuple(
            sorted(
                selected,
                key=lambda event: (
                    event.materiality.market_materiality if event.materiality else 0,
                    event.published_at,
                    event.event_id,
                ),
                reverse=True,
            )[: query.limit]
        )
        selected_clusters = tuple(
            cluster
            for cluster in clustered.clusters
            if cluster.canonical_event_id in {event.event_id for event in selected}
        )
        selected_member_ids = {
            event_id
            for cluster in selected_clusters
            for event_id in cluster.member_event_ids
        }
        returned_evidence = tuple(
            item for item in validated_evidence if item.event_id in selected_member_ids
        )
        returned_contradictions = tuple(
            item for item in contradictions if item.event_id in selected_member_ids
        )

        if self.repository is not None and hasattr(self.repository, "save_events"):
            persistable = tuple(
                event
                for event in enriched_events
                if not event.quarantined and self._metadata_storage_allowed(event)
            )
            try:
                self.repository.save_events(persistable)  # type: ignore[union-attr]
            except Exception as exc:
                errors.append(f"news_metadata_repository:{type(exc).__name__}")

        freshness = self._aggregate_freshness(
            tuple(enriched_events), response.provenance, query.as_of
        )
        status = self._status(response.provenance, tuple(enriched_events), freshness, errors)
        if not selected and enriched_events:
            limitations.append("No canonical events met the requested filters and materiality threshold.")
        if not enriched_events and response.provenance.source_state != NewsFreshnessState.UNAVAILABLE:
            limitations.append("The provider returned no valid events for this query.")
        if response.provenance.mode == NewsProviderMode.HERMETIC:
            limitations.append("Hermetic fixture news is test data and is not live market news.")
        if any(event.source_quality in {SourceQuality.UNVERIFIED, SourceQuality.UNAVAILABLE} for event in enriched_events):
            limitations.append("Unverified or unregistered sources cannot support confirmed conclusions.")

        confidence = self.confidence_engine.adjust(
            ConfidenceAdjustmentInput(
                intent="news_intelligence",
                evidence_count=len(returned_evidence),
                freshness_state=freshness.state.value,
                missing_evidence_count=sum(
                    event.reaction is None
                    or event.reaction.classification == ReactionClassification.INSUFFICIENT_DATA
                    for event in selected
                ),
                stale_count=sum(event.freshness.state == NewsFreshnessState.STALE for event in selected),
                partial_count=sum(event.freshness.state in {NewsFreshnessState.PARTIAL, NewsFreshnessState.MIXED} for event in selected),
                unavailable_count=sum(event.freshness.state == NewsFreshnessState.UNAVAILABLE for event in selected),
                test_count=sum(event.freshness.state == NewsFreshnessState.TEST for event in selected),
                contradiction_count=len(returned_contradictions),
                unsupported_dimension_count=sum(
                    "intraday_reaction_unavailable_daily_only" in (event.reaction.limitations if event.reaction else ())
                    for event in selected
                ),
                fallback_used=response.provenance.fallback_reason is not None,
                source_quality=(selected[0].source_quality.value if selected else None),
            )
        )

        provider_count = len(response.items)
        cluster_count = len(clustered.clusters)
        metrics = NewsProcessingMetrics(
            provider_fetch_ms=provider_ms,
            normalization_ms=normalization_ms,
            clustering_ms=clustering_ms,
            mapping_ms=mapping_ms,
            materiality_ms=materiality_ms,
            reaction_ms=reaction_ms,
            materiality_reaction_ms=materiality_reaction_ms,
            total_ms=self._elapsed_ms(started),
            provider_event_count=provider_count,
            normalized_event_count=len(normalized),
            cluster_count=cluster_count,
            returned_event_count=len(selected),
            duplicate_reduction_ratio=(
                round(max(0, provider_count - cluster_count) / provider_count, 6)
                if provider_count
                else 0
            ),
            cache_hit=response.provenance.cache_hit,
        )
        return NewsIntelligenceResult(
            query=query,
            status=status,
            provider=response.provenance,
            as_of=query.as_of,
            events=selected,
            clusters=selected_clusters,
            evidence=returned_evidence,
            contradictions=returned_contradictions,
            confidence=ConfidenceLabel(confidence.label),
            confidence_contributions=tuple(
                f"{item.rule}:{item.reason}" for item in confidence.contributions
            ),
            limitations=tuple(dict.fromkeys(limitations)),
            errors=tuple(dict.fromkeys(errors)),
            deep_links=self._deep_links(selected),
            metrics=metrics,
            freshness=freshness,
        )

    def query_cached(
        self,
        query: NewsQuery,
        *,
        watchlist_symbols: tuple[str, ...] = (),
    ) -> NewsIntelligenceResult:
        """Read through the metadata cache only; never invoke the live provider."""

        if self.repository is None or not hasattr(self.repository, "query"):
            provenance = NewsProviderProvenance(
                provider="news-metadata-cache",
                mode=NewsProviderMode.CACHED,
                source_state=NewsFreshnessState.UNAVAILABLE,
                as_of=query.as_of,
                cache_hit=False,
                fallback_reason="news_metadata_repository_not_configured",
                errors=("cached_news_unavailable",),
            )
            return self._unavailable_result(query, provenance)
        cached = NewsIntelligenceService(
            provider=CachedNewsProvider(self.repository),  # type: ignore[arg-type]
            repository=None,
            normalizer=self.normalizer,
            mapper=self.mapper,
            clustering=self.clustering,
            materiality=self.materiality,
            reaction=self.reaction,
        )
        return cached.query(query, watchlist_symbols=watchlist_symbols)

    def query_cached_event(
        self,
        event_id: str,
        *,
        as_of: datetime,
    ) -> NewsIntelligenceResult:
        """Resolve one cached event by ID and rebuild its complete cluster.

        The direct ``get`` boundary prevents an event-detail request from
        depending on a top-N market query.  When the requested ID is a cluster
        member, the cache provider loads every stored member so canonical
        selection, contradictions, evidence, and deep links remain intact.
        """

        query = NewsQuery(mode=NewsQueryMode.MARKET, as_of=as_of, limit=100)
        if self.repository is None or not hasattr(self.repository, "get"):
            provenance = NewsProviderProvenance(
                provider="news-metadata-cache",
                mode=NewsProviderMode.UNAVAILABLE,
                source_state=NewsFreshnessState.UNAVAILABLE,
                as_of=as_of,
                cache_hit=False,
                fallback_reason="news_metadata_repository_not_configured",
                errors=("cached_news_unavailable",),
            )
            return self._unavailable_result(query, provenance)
        cached = NewsIntelligenceService(
            provider=CachedNewsProvider(
                self.repository,  # type: ignore[arg-type]
                event_id=event_id,
            ),
            repository=None,
            normalizer=self.normalizer,
            mapper=self.mapper,
            clustering=self.clustering,
            materiality=self.materiality,
            reaction=self.reaction,
        )
        return cached.query(query)

    latest = query_cached

    def _unavailable_result(
        self,
        query: NewsQuery,
        provenance: NewsProviderProvenance,
        *,
        metrics: NewsProcessingMetrics | None = None,
    ) -> NewsIntelligenceResult:
        evaluated = self.freshness_engine.evaluate(
            FreshnessAvailabilityInput(
                source_state="unavailable",
                provider_status="unavailable",
                generated_at=(provenance.fetched_at or query.as_of).isoformat(),
                completeness=0,
                provider=provenance.provider,
                fallback_used=bool(provenance.fallback_reason),
                warnings=provenance.errors,
                now=query.as_of,
            )
        )
        freshness = self._freshness_contract(evaluated, provenance, query.as_of)
        confidence = self.confidence_engine.adjust(
            ConfidenceAdjustmentInput(
                intent="news_intelligence",
                evidence_count=0,
                freshness_state="unavailable",
                missing_evidence_count=1,
                unavailable_count=1,
                fallback_used=bool(provenance.fallback_reason),
            )
        )
        return NewsIntelligenceResult(
            query=query,
            status=NewsServiceStatus.UNAVAILABLE,
            provider=provenance,
            as_of=query.as_of,
            confidence=ConfidenceLabel(confidence.label),
            confidence_contributions=tuple(
                f"{item.rule}:{item.reason}" for item in confidence.contributions
            ),
            limitations=(
                provenance.fallback_reason
                or "News Intelligence is unavailable because no licensed provider is configured.",
            ),
            errors=provenance.errors,
            freshness=freshness,
            metrics=metrics or NewsProcessingMetrics(cache_hit=provenance.cache_hit),
        )

    @staticmethod
    def _provider_request(query: NewsQuery) -> NewsProviderRequest:
        return NewsProviderRequest(
            as_of=query.as_of,
            start_at=query.start_at,
            end_at=query.end_at or query.as_of,
            # Index scope is resolved from validated benchmark relationships
            # after normalization. Sending only the ETF proxy here would
            # suppress constituent events before entity mapping can run.
            symbols=() if query.mode is NewsQueryMode.INDEX else query.symbols,
            event_types=query.event_types,
            limit=min(500, max(query.limit * 5, query.limit)),
            macro_only=query.mode == NewsQueryMode.MARKET and bool(
                query.event_types
                and all(
                    event_type.value
                    in {
                        "monetary_policy",
                        "inflation",
                        "employment",
                        "economic_growth",
                        "government_policy",
                        "geopolitics",
                    }
                    for event_type in query.event_types
                )
            ),
            earnings_only=bool(
                query.event_types
                and all(event_type.value == "earnings" for event_type in query.event_types)
            ),
        )

    def _materiality_inputs(
        self,
        event: NewsEventRecord,
        *,
        duplicate_count: int,
        reaction_result: object,
    ) -> MaterialityInputs:
        mappings = event.affected_entities
        direct = any(mapping.relationship.value == "directly_named" for mapping in mappings)
        mapped_types = {mapping.entity_type for mapping in mappings}
        macro = event.event_type.value in {
            "monetary_policy",
            "inflation",
            "employment",
            "economic_growth",
            "government_policy",
            "geopolitics",
        }
        market_scope = (
            0.9
            if macro
            else 0.75
            if EntityType.INDEX in mapped_types
            else 0.55
            if EntityType.SECTOR in mapped_types
            else 0.4
            if EntityType.THEME in mapped_types
            else 0.25
            if direct
            else 0
        )
        uncertainty = {
            NewsEventStatus.CONFIRMED: 0.0,
            NewsEventStatus.CORRECTED: 0.15,
            NewsEventStatus.DEVELOPING: 0.4,
            NewsEventStatus.DISPUTED: 1.0,
            NewsEventStatus.UNVERIFIED: 1.0,
            NewsEventStatus.RETRACTED: 1.0,
        }[event.event_status]
        freshness = {
            NewsFreshnessState.LIVE: 1.0,
            NewsFreshnessState.DELAYED: 0.85,
            NewsFreshnessState.CACHED: 0.7,
            NewsFreshnessState.TEST: 0.5,
            NewsFreshnessState.PARTIAL: 0.4,
            NewsFreshnessState.MIXED: 0.3,
            NewsFreshnessState.STALE: 0.0,
            NewsFreshnessState.UNAVAILABLE: 0.0,
        }[event.freshness.state]
        return MaterialityInputs(
            source_credibility={
                SourceQuality.PRIMARY: 1.0,
                SourceQuality.HIGH_CONFIDENCE_SECONDARY: 0.8,
                SourceQuality.SUPPORTING_SECONDARY: 0.5,
                SourceQuality.UNVERIFIED: 0.1,
                SourceQuality.UNAVAILABLE: 0.0,
            }[event.source_quality],
            directness=1.0 if direct else 0.0,
            market_scope=market_scope,
            entity_significance=0.5 if direct else 0.0,
            observed_price_reaction=getattr(reaction_result, "observed_price_strength"),
            observed_volume_reaction=getattr(reaction_result, "observed_volume_strength"),
            breadth_confirmation=getattr(reaction_result, "breadth_strength"),
            cross_asset_confirmation=getattr(reaction_result, "cross_asset_strength"),
            freshness=freshness,
            user_watchlist_relevance=(
                1.0 if EntityType.WATCHLIST in mapped_types else 0.0
            ),
            duplicate_count=duplicate_count,
            uncertainty=uncertainty,
        )

    def _contradictions(
        self,
        events: tuple[NewsEventRecord, ...],
        clusters: tuple[NewsEventCluster, ...],
    ) -> tuple[NewsContradiction, ...]:
        findings: list[ContradictionFinding] = []
        event_by_evidence: dict[str, NewsEventRecord] = {}
        for event in events:
            reaction_rejects = event.reaction is not None and event.reaction.classification in {
                ReactionClassification.REJECTS_POSITIVE,
                ReactionClassification.REJECTS_NEGATIVE,
            }
            evidence_id = (
                event.reaction.evidence_ids[0]
                if reaction_rejects and event.reaction and event.reaction.evidence_ids
                else event.evidence_ids[0]
                if event.evidence_ids
                else f"missing-{event.event_id}"
            )
            explicit = bool(
                reaction_rejects
                or event.event_status in {NewsEventStatus.DISPUTED, NewsEventStatus.RETRACTED}
            )
            findings.append(
                ContradictionFinding(
                    evidence_id=evidence_id,
                    statement=(event.reaction.summary if reaction_rejects and event.reaction else event.canonical_headline),
                    interpretation_class="contradiction" if explicit else "observed_fact",
                    contradicts_claim_ids=(event.cluster_id,) if explicit else (),
                    explicitly_opposing=explicit,
                )
            )
            event_by_evidence[evidence_id] = event
        analysis = self.contradiction_engine.analyze(
            ContradictionAnalysisInput(findings=tuple(findings))
        )
        preservation = self.contradiction_engine.validate_preservation(
            ContradictionPreservationInput(
                expected_evidence_ids=analysis.opposing_evidence_ids,
                cited_evidence_ids=analysis.opposing_evidence_ids,
                truncation_disclosed=True,
            )
        )
        return tuple(
            NewsContradiction(
                contradiction_id=f"news-contradiction-{hashlib.sha256(evidence_id.encode()).hexdigest()[:24]}",
                event_id=event_by_evidence[evidence_id].event_id,
                statement=(
                    event_by_evidence[evidence_id].reaction.summary
                    if event_by_evidence[evidence_id].reaction
                    and event_by_evidence[evidence_id].reaction.classification
                    in {ReactionClassification.REJECTS_POSITIVE, ReactionClassification.REJECTS_NEGATIVE}
                    else "A disputed, retracted, or opposing event record is preserved."
                ),
                evidence_ids=(evidence_id,),
                preserved=preservation.valid and evidence_id in preservation.preserved_evidence_ids,
                engine_version=preservation.engine_version,
            )
            for evidence_id in analysis.opposing_evidence_ids
            if evidence_id in event_by_evidence
        )

    def _valid_evidence_lineage(
        self,
        evidence: NewsEvidenceRecord,
        events_by_id: dict[str, NewsEventRecord],
    ) -> bool:
        event = events_by_id.get(evidence.event_id)
        if event is None:
            return False
        return self.evidence_engine.source_timestamp_is_valid(
            SourceRecord(
                source_id=evidence.source_id,
                provider=event.provider_metadata.provider,
                dataset="news_intelligence_metadata",
                generated_at=event.provider_metadata.fetched_at.isoformat(),
                market_date=evidence.market_date.isoformat() if evidence.market_date else None,
                raw_engine_reference=event.provider_metadata.provider_event_id,
            )
        )

    def _aggregate_freshness(
        self,
        events: tuple[NewsEventRecord, ...],
        provenance: NewsProviderProvenance,
        as_of: datetime,
    ) -> NewsFreshness:
        if not events:
            evaluated = self.freshness_engine.evaluate(
                FreshnessAvailabilityInput(
                    source_state=provenance.source_state.value,
                    generated_at=(provenance.fetched_at or as_of).isoformat(),
                    completeness=1 if provenance.source_state != NewsFreshnessState.UNAVAILABLE else 0,
                    provider=provenance.provider,
                    test_data=provenance.mode == NewsProviderMode.HERMETIC,
                    fallback_used=bool(provenance.fallback_reason),
                    warnings=provenance.errors,
                    now=as_of,
                )
            )
            return self._freshness_contract(evaluated, provenance, as_of)
        summary = self.freshness_engine.summarize(
            FreshnessSummaryInput(
                state=event.freshness.state.value,
                market_date=event.market_date.isoformat(),
                generated_at=event.provider_metadata.fetched_at.isoformat(),
                warnings=event.freshness.warnings,
            )
            for event in events
        )
        latest = max(events, key=lambda event: event.published_at)
        availability = (
            NewsAvailability.UNAVAILABLE
            if summary.overall_state == "unavailable"
            else NewsAvailability.PARTIAL
            if summary.confidence_cap_recommendation
            else NewsAvailability.AVAILABLE
        )
        return NewsFreshness(
            state=NewsFreshnessState(summary.overall_state),
            availability=availability,
            market_date=latest.market_date,
            generated_at=provenance.fetched_at or provenance.as_of,
            observed_at=latest.published_at,
            age_seconds=max(0, (as_of - latest.published_at).total_seconds()),
            completeness=sum(event.freshness.completeness for event in events) / len(events),
            provider=provenance.provider,
            fallback_used=bool(provenance.fallback_reason),
            mixed_sources=len({event.source_identifier for event in events}) > 1,
            confidence_cap_recommendation=summary.confidence_cap_recommendation,
            warnings=summary.warnings,
            engine_version=summary.engine_version,
        )

    @staticmethod
    def _freshness_contract(
        evaluated: object,
        provenance: NewsProviderProvenance,
        as_of: datetime,
    ) -> NewsFreshness:
        return NewsFreshness(
            state=NewsFreshnessState(getattr(evaluated, "state")),
            availability=NewsAvailability(getattr(evaluated, "availability")),
            market_date=None,
            generated_at=provenance.fetched_at or as_of,
            observed_at=None,
            age_seconds=getattr(evaluated, "age_seconds"),
            completeness=getattr(evaluated, "completeness"),
            provider=provenance.provider,
            fallback_used=getattr(evaluated, "fallback_used"),
            mixed_sources=getattr(evaluated, "mixed_sources"),
            confidence_cap_recommendation=getattr(evaluated, "confidence_cap_recommendation"),
            warnings=getattr(evaluated, "warnings"),
            engine_version=getattr(evaluated, "engine_version"),
        )

    @staticmethod
    def _status(
        provenance: NewsProviderProvenance,
        events: tuple[NewsEventRecord, ...],
        freshness: NewsFreshness,
        errors: list[str],
    ) -> NewsServiceStatus:
        if provenance.source_state == NewsFreshnessState.UNAVAILABLE and not events:
            return NewsServiceStatus.UNAVAILABLE
        if freshness.state == NewsFreshnessState.STALE:
            return NewsServiceStatus.STALE
        if errors or freshness.state in {
            NewsFreshnessState.TEST,
            NewsFreshnessState.PARTIAL,
            NewsFreshnessState.MIXED,
        }:
            return NewsServiceStatus.PARTIAL
        return NewsServiceStatus.COMPLETE

    @staticmethod
    def _matches_query(event: NewsEventRecord, query: NewsQuery) -> bool:
        if query.source_qualities and event.source_quality not in query.source_qualities:
            return False
        if query.event_types and event.event_type not in query.event_types:
            return False
        if query.mode is NewsQueryMode.INDEX:
            query_symbols = {symbol.upper() for symbol in query.symbols}
            target_ids = {str(query.entity_id or "").casefold()}
            for value in (query.entity_id, *query.symbols):
                if value:
                    target_ids.update(
                        item.casefold()
                        for item in INDEX_ENTITY_ALIASES.get(value.upper(), ())
                    )
            return any(
                (
                    mapping.entity_type is EntityType.INDEX
                    and mapping.entity_id.casefold() in target_ids
                )
                or (
                    mapping.entity_type in {EntityType.ETF, EntityType.SECURITY}
                    and bool(mapping.symbol)
                    and mapping.symbol.upper() in query_symbols
                )
                for mapping in event.affected_entities
            )
        if query.symbols and not set(query.symbols).intersection(
            mapping.symbol for mapping in event.affected_entities if mapping.symbol
        ):
            return False
        if query.entity_id and query.mode in {
            NewsQueryMode.SECTOR,
            NewsQueryMode.THEME,
        } and not any(mapping.entity_id == query.entity_id for mapping in event.affected_entities):
            return False
        return True

    def _metadata_storage_allowed(self, event: NewsEventRecord) -> bool:
        record = self.normalizer.credibility.registry.get(event.source_identifier)
        return bool(record and record.active and record.metadata_storage_allowed)

    def _propagate_cluster_mappings(
        self,
        events: tuple[NewsEventRecord, ...],
        clusters: tuple[NewsEventCluster, ...],
    ) -> tuple[NewsEventRecord, ...]:
        by_id = {event.event_id: event for event in events}
        for cluster in clusters:
            canonical = by_id.get(cluster.canonical_event_id)
            if canonical is None:
                continue
            members = [
                by_id[event_id]
                for event_id in cluster.member_event_ids
                if event_id in by_id
            ]
            ordered = [canonical, *(event for event in members if event.event_id != canonical.event_id)]
            mappings = self.evidence_engine.deduplicate(
                (mapping for event in ordered for mapping in event.affected_entities),
                identity=lambda mapping: (
                    f"{mapping.entity_type.value}:{mapping.entity_id}:"
                    f"{mapping.relationship.value}"
                ),
                fingerprint=lambda mapping: mapping.model_dump(mode="json"),
            ).items
            by_id[canonical.event_id] = self._replace_event(
                canonical,
                affected_entities=mappings,
                affected_sectors=tuple(
                    dict.fromkeys(
                        mapping.display_name
                        for mapping in mappings
                        if mapping.entity_type == EntityType.SECTOR
                    )
                ),
                affected_themes=tuple(
                    dict.fromkeys(
                        mapping.entity_id
                        for mapping in mappings
                        if mapping.entity_type == EntityType.THEME
                    )
                ),
                affected_indexes=tuple(
                    dict.fromkeys(
                        mapping.display_name
                        for mapping in mappings
                        if mapping.entity_type == EntityType.INDEX
                    )
                ),
                evidence_ids=tuple(
                    dict.fromkeys(
                        (*canonical.evidence_ids, *(mapping.evidence_id for mapping in mappings))
                    )
                ),
            )
        return tuple(by_id[event.event_id] for event in events)

    @staticmethod
    def _deep_links(events: tuple[NewsEventRecord, ...]) -> tuple[NewsDeepLink, ...]:
        links: list[NewsDeepLink] = []
        seen: set[tuple[str, str | None, str | None]] = set()
        for event in events:
            for mapping in event.affected_entities:
                if mapping.entity_type in {EntityType.SECURITY, EntityType.ETF} and mapping.symbol:
                    link = NewsDeepLink(
                        destination="stock_detail",
                        entity_id=mapping.entity_id,
                        symbol=mapping.symbol,
                        parameters=(("section", "stocks"), ("symbol", mapping.symbol)),
                    )
                elif mapping.entity_type == EntityType.SECTOR:
                    link = NewsDeepLink(destination="sector_detail", entity_id=mapping.entity_id)
                elif mapping.entity_type == EntityType.THEME:
                    link = NewsDeepLink(destination="theme_detail", entity_id=mapping.entity_id)
                else:
                    continue
                key = (link.destination, link.entity_id, link.symbol)
                if key not in seen:
                    seen.add(key)
                    links.append(link)
        return tuple(links)

    @staticmethod
    def _replace_event(event: NewsEventRecord, **updates: object) -> NewsEventRecord:
        payload = event.model_dump(mode="python")
        payload.update(updates)
        return NewsEventRecord.model_validate(payload)

    @staticmethod
    def _reaction_for_event(
        observation: MarketReactionObservation,
        event_id: str,
    ) -> MarketReactionObservation:
        payload = observation.model_dump(mode="python")
        payload["event_id"] = event_id
        return MarketReactionObservation.model_validate(payload)

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((perf_counter() - started) * 1000, 3)


_service_lock = threading.RLock()
_service: NewsIntelligenceService | None = None


def get_news_intelligence_service() -> NewsIntelligenceService:
    """Production factory. It intentionally defaults to unavailable, not fixtures."""

    global _service
    with _service_lock:
        if _service is None:
            _service = NewsIntelligenceService(provider=UnavailableNewsProvider())
        return _service


def reset_news_intelligence_service() -> None:
    global _service
    with _service_lock:
        _service = None

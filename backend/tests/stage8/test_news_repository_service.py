from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from app.intelligence.news import (
    ExpectedDirection,
    MarketReactionObservation,
    NewsEventStatus,
    NewsEventType,
    NewsFreshnessState,
    NewsIntelligenceService,
    NewsProviderMode,
    NewsQuery,
    NewsQueryMode,
    NewsServiceStatus,
    ReactionClassification,
    ReactionWindow,
    SourceQuality,
)
from app.analysis_engines.news import NewsEntityMappingEngine
from app.providers.news import HermeticNewsProvider
from app.repositories.news import NewsMetadataRepository
from app.securities.models import SecurityRecord
from tests.stage8.news_helpers import NOW, mapping_engine, provider_item


class NewsRepositoryServiceTests(unittest.TestCase):
    def _service(
        self,
        *items: object,
        repository: NewsMetadataRepository | None = None,
    ) -> NewsIntelligenceService:
        return NewsIntelligenceService(
            provider=HermeticNewsProvider(tuple(items), clock=lambda: NOW),  # type: ignore[arg-type]
            repository=repository,
            mapper=mapping_engine(),
        )

    def test_service_orchestrates_mapping_materiality_evidence_and_shared_engines(self) -> None:
        item = provider_item()
        reaction = MarketReactionObservation(
            event_id=item.provider_event_id,
            entity_id="sec-acme",
            symbol="ACME",
            window=ReactionWindow.CLOSE_TO_CLOSE,
            window_start=NOW - timedelta(days=1),
            window_end=NOW,
            price_return=-0.04,
            benchmark_return=0.005,
            volume_ratio=1.7,
            expected_direction=ExpectedDirection.POSITIVE,
            evidence_ids=("market-price-1",),
            source_id="daily-adjusted-bars:ACME",
            source_quality=SourceQuality.HIGH_CONFIDENCE_SECONDARY,
            source_state=NewsFreshnessState.LIVE,
        )
        result = self._service(item).query(
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW),
            reaction_observations=(reaction,),
            watchlist_symbols=("ACME",),
        )

        self.assertEqual(result.status, NewsServiceStatus.PARTIAL)
        self.assertEqual(result.provider.mode, NewsProviderMode.HERMETIC)
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIsNotNone(event.materiality)
        self.assertEqual(
            event.reaction.classification,  # type: ignore[union-attr]
            ReactionClassification.REJECTS_POSITIVE,
        )
        self.assertTrue(event.affected_entities)
        self.assertTrue(result.evidence)
        self.assertEqual(result.freshness.engine_version, "freshness-availability-v1")
        self.assertEqual(result.confidence.value, "limited")
        self.assertEqual(len(result.contradictions), 1)
        self.assertTrue(result.contradictions[0].preserved)
        self.assertEqual(
            result.contradictions[0].engine_version,
            "contradiction-preservation-v1",
        )
        self.assertEqual(result.metrics.provider_event_count, 1)

    def test_metadata_repository_never_stores_summary_facts_or_article_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "news.sqlite3"
            repository = NewsMetadataRepository(path)
            result = self._service(provider_item(), repository=repository).query(
                NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
            )
            event_id = result.events[0].event_id
            stored = repository.get(event_id)
            self.assertIsNotNone(stored)

            with sqlite3.connect(path) as connection:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(news_event_metadata)")
                }
                payload = connection.execute(
                    "SELECT payload_json FROM news_event_metadata WHERE event_id=?",
                    (event_id,),
                ).fetchone()[0]
            decoded = json.loads(payload)
            self.assertNotIn("article_body", columns)
            self.assertNotIn("body", columns)
            self.assertNotIn("source_summary", decoded)
            self.assertNotIn("confirmed_facts", decoded)
            self.assertNotIn("reaction", decoded)
            self.assertNotIn("materiality", decoded)
            self.assertNotIn("affected_entities", decoded)
            self.assertNotIn("Acme raised its full-year outlook.", payload)

    def test_repository_rejects_forbidden_content_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "article_content_persistence_forbidden"):
            NewsMetadataRepository.assert_metadata_only(
                {"metadata": {"article_body": "must not be stored"}}
            )

    def test_cached_read_preserves_hermetic_origin_and_never_claims_live(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = NewsMetadataRepository(Path(directory) / "news.sqlite3")
            service = self._service(provider_item(), repository=repository)
            original = service.query(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))
            cached = service.query_cached(
                NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
            )

            self.assertEqual(cached.provider.mode, NewsProviderMode.CACHED)
            self.assertTrue(cached.provider.cache_hit)
            self.assertEqual(cached.freshness.state, NewsFreshnessState.TEST)
            self.assertEqual(cached.events[0].provider_metadata.provider_mode, NewsProviderMode.HERMETIC)
            self.assertEqual(cached.events[0].event_id, original.events[0].event_id)
            self.assertNotEqual(cached.freshness.state, NewsFreshnessState.LIVE)

    def test_unregistered_source_remains_unverified_and_low_materiality(self) -> None:
        item = provider_item(
            source_identifier="unknown-publisher",
            source_name="Unknown Publisher",
            source_url="https://unknown.example/event",
            structured_event_type=NewsEventType.OTHER,
            event_status=NewsEventStatus.CONFIRMED,
        )
        result = self._service(item).query(
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
        )

        event = result.events[0]
        self.assertEqual(event.source_quality, SourceQuality.UNAVAILABLE)
        self.assertEqual(event.event_status, NewsEventStatus.UNVERIFIED)
        self.assertEqual(event.confirmed_facts, ())
        self.assertLess(event.materiality.market_materiality, 30)  # type: ignore[union-attr]
        self.assertIn("source_registry_miss", result.errors)

    def test_security_query_filters_unmapped_symbols(self) -> None:
        result = self._service(provider_item(structured_symbols=("OTHER",))).query(
            NewsQuery(
                mode=NewsQueryMode.SECURITY,
                as_of=NOW,
                symbols=("OTHER",),
            )
        )

        self.assertEqual(result.events, ())
        self.assertIn("No canonical events met", " ".join(result.limitations))

    def test_index_proxy_query_matches_validated_constituent_membership(self) -> None:
        record = SecurityRecord(
            security_id="sec-nvda",
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            sector="Information Technology",
            sector_id="information_technology",
            industry="Semiconductors",
            index_memberships=("Nasdaq 100",),
            source="stage8-index-query-fixture",
            verified_at="2026-07-01T00:00:00Z",
        )
        service = NewsIntelligenceService(
            provider=HermeticNewsProvider(
                (provider_item(structured_symbols=("NVDA",)),),
                clock=lambda: NOW,
            ),
            mapper=NewsEntityMappingEngine(
                security_resolver=lambda symbol: record if symbol == "NVDA" else None,
                theme_loader=lambda: [],
            ),
        )

        result = service.query(
            NewsQuery(
                mode=NewsQueryMode.INDEX,
                as_of=NOW,
                entity_id="QQQ",
                symbols=("QQQ",),
            )
        )

        self.assertEqual(len(result.events), 1)
        self.assertTrue(
            any(
                mapping.entity_id == "index:nasdaq_100"
                for mapping in result.events[0].affected_entities
            )
        )


if __name__ == "__main__":
    unittest.main()

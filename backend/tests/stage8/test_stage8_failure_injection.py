from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.analysis_engines.session import (
    IntradayBar,
    MarketCalendarConfig,
)
from app.intelligence.news import (
    NewsFreshnessState,
    NewsIntelligenceService,
    NewsProviderMode,
    NewsProviderProvenance,
    NewsQuery,
    NewsQueryMode,
    NewsServiceStatus,
)
from app.intelligence.session_narrative import SessionNarrativeQuery
from app.providers.news import (
    HermeticNewsProvider,
    NewsProviderItem,
    NewsProviderResponse,
)
from main import app
from tests.stage8.news_helpers import NOW, provider_item


class Stage8FailureInjectionTests(unittest.TestCase):
    def test_provider_timeout_and_rate_limit_fail_closed_without_replacement(self) -> None:
        class RateLimitError(RuntimeError):
            pass

        for failure in (TimeoutError("timeout"), RateLimitError("rate limited")):
            class FailingProvider:
                def fetch_events(self, request):
                    del request
                    raise failure

            with self.subTest(failure=type(failure).__name__):
                result = NewsIntelligenceService(provider=FailingProvider()).query(  # type: ignore[arg-type]
                    NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
                )
                self.assertEqual(result.status, NewsServiceStatus.UNAVAILABLE)
                self.assertEqual(result.provider.mode, NewsProviderMode.UNAVAILABLE)
                self.assertEqual(result.events, ())
                self.assertEqual(result.confidence.value, "limited")
                self.assertIn(type(failure).__name__, result.errors[0])
                self.assertIn("no replacement data", result.limitations[0].casefold())

    def test_malformed_provider_item_and_timestamp_are_rejected_at_ingress(self) -> None:
        valid = provider_item().model_dump(mode="python")
        cases = (
            {**valid, "provider_event_id": ""},
            {**valid, "published_at": NOW.replace(tzinfo=None)},
            {**valid, "article_body": "not an allowed provider field"},
        )
        for payload in cases:
            with self.subTest(fields=tuple(payload)):
                with self.assertRaises(ValidationError):
                    NewsProviderItem.model_validate(payload)

    def test_duplicate_and_conflicting_event_ids_never_count_as_confirmations(self) -> None:
        duplicate = provider_item("same-provider-event")
        exact = NewsIntelligenceService(
            provider=HermeticNewsProvider((duplicate, duplicate), clock=lambda: NOW)
        ).query(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))
        self.assertEqual(exact.metrics.provider_event_count, 2)
        self.assertEqual(exact.metrics.cluster_count, 1)
        self.assertEqual(len(exact.events), 1)
        self.assertEqual(exact.metrics.duplicate_reduction_ratio, 0.5)

        conflicting = provider_item(
            "same-provider-event",
            headline="Acme cuts full-year guidance",
            summary="Acme cut its full-year outlook.",
            confirmed_facts=("Acme cut full-year guidance.",),
        )
        collision = NewsIntelligenceService(
            provider=HermeticNewsProvider((duplicate, conflicting), clock=lambda: NOW)
        ).query(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))
        self.assertEqual(len(collision.events), 1)
        self.assertEqual(collision.status, NewsServiceStatus.PARTIAL)
        self.assertTrue(
            any(error.startswith("conflicting_duplicate_event:") for error in collision.errors),
            collision.errors,
        )

    def test_entity_mapping_failure_returns_partial_unmapped_event(self) -> None:
        class FailingMapper:
            def map_event(self, event, context, *, now):
                del event, context, now
                raise RuntimeError("mapping registry unavailable")

        result = NewsIntelligenceService(
            provider=HermeticNewsProvider((provider_item(),), clock=lambda: NOW),
            mapper=FailingMapper(),  # type: ignore[arg-type]
        ).query(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))

        self.assertEqual(result.status, NewsServiceStatus.PARTIAL)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].affected_entities, ())
        self.assertTrue(
            any(error.startswith("news_entity_mapping_failure:") for error in result.errors)
        )

    def test_stale_cache_is_never_presented_as_current(self) -> None:
        class StaleCacheProvider:
            def fetch_events(self, request):
                item = provider_item(
                    "stale-event",
                    source_identifier="sec-edgar",
                    source_name="U.S. SEC EDGAR",
                    source_url="https://www.sec.gov/Archives/stale-event",
                    published_at=NOW - timedelta(days=5),
                    first_seen_at=NOW - timedelta(days=5),
                )
                return NewsProviderResponse(
                    items=(item,),
                    provenance=NewsProviderProvenance(
                        provider="stale-metadata-cache",
                        mode=NewsProviderMode.CACHED,
                        source_state=NewsFreshnessState.STALE,
                        as_of=request.as_of,
                        fetched_at=NOW - timedelta(days=4),
                        cache_hit=True,
                        fallback_reason="cached_metadata_expired",
                    ),
                )

        result = NewsIntelligenceService(provider=StaleCacheProvider()).query(  # type: ignore[arg-type]
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
        )
        self.assertEqual(result.status, NewsServiceStatus.STALE)
        self.assertEqual(result.provider.mode, NewsProviderMode.CACHED)
        self.assertEqual(result.freshness.state, NewsFreshnessState.STALE)
        self.assertNotEqual(result.freshness.state, NewsFreshnessState.LIVE)

    def test_corrupt_bars_missing_benchmark_and_calendar_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            IntradayBar(
                timestamp=NOW,
                open=100,
                high=99,
                low=98,
                close=101,
                volume=100,
            )
        with self.assertRaises(ValidationError):
            SessionNarrativeQuery(symbol="", as_of=NOW)
        with self.assertRaises(ValidationError):
            MarketCalendarConfig(
                regular_open=MarketCalendarConfig().regular_close,
            )

    def test_endpoint_dependency_failures_return_structured_states_not_http_500(self) -> None:
        class FailingProvider:
            def fetch_events(self, request):
                del request
                raise TimeoutError("upstream timeout")

        news_service = NewsIntelligenceService(provider=FailingProvider())  # type: ignore[arg-type]
        # The failure-path assertions do not require application startup jobs;
        # keeping lifespan workers disabled makes this suite network-hermetic.
        client = TestClient(app)
        try:
            with patch(
                "app.api.intelligence.get_news_intelligence_service",
                return_value=news_service,
            ):
                response = client.get("/intelligence/news/market")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["status"], "unavailable")
                self.assertEqual(response.json()["provider"]["mode"], "unavailable")

            with patch(
                "app.api.intelligence.DailyBarStorage.history",
                side_effect=RuntimeError("corrupt daily storage"),
            ):
                response = client.get("/intelligence/session/NVDA")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["status"], "unavailable")
                self.assertEqual(response.json()["data_mode"], "unavailable")
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()

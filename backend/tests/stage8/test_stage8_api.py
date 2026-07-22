from __future__ import annotations

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.analysis_engines.news import NewsEntityMappingEngine
from app.intelligence.news import NewsIntelligenceService, NewsQuery, NewsQueryMode
from app.providers.news import HermeticNewsProvider
from app.repositories.news import InMemoryNewsMetadataRepository
from main import app
from tests.stage8.news_helpers import NOW, provider_item, security_record


class Stage8IntelligenceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # These endpoint contract tests do not need application startup jobs.
        # Avoid entering the lifespan so the hermetic suite cannot launch the
        # repository's production background refresh workers.
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_all_news_consumers_receive_the_same_typed_unavailable_boundary(self) -> None:
        paths = (
            "/intelligence/news/market",
            "/intelligence/news/index/QQQ",
            "/intelligence/news/security/NVDA",
            "/intelligence/news/sector/technology",
            "/intelligence/news/theme/cybersecurity",
            "/intelligence/news/watchlist?symbols=NVDA,MSFT,NVDA",
            "/intelligence/news/events/news-event-missing",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["status"], "unavailable")
                self.assertEqual(payload["provider"]["mode"], "unavailable")
                self.assertEqual(payload["provider"]["source_state"], "unavailable")
                self.assertEqual(payload["events"], [])
                self.assertEqual(payload["clusters"], [])
                self.assertEqual(payload["confidence"], "limited")
                self.assertTrue(payload["limitations"])
                self.assertFalse(payload["metrics"]["cache_hit"])

    def test_news_filters_are_bounded_and_closed_enums(self) -> None:
        response = self.client.get(
            "/intelligence/news/market",
            params={
                "limit": 3,
                "event_type": "cybersecurity_incident",
                "source_quality": "primary",
                "minimum_materiality": 70,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        query = response.json()["query"]
        self.assertEqual(query["limit"], 3)
        self.assertEqual(query["event_types"], ["cybersecurity_incident"])
        self.assertEqual(query["source_qualities"], ["primary"])
        self.assertEqual(query["minimum_materiality"], 70)

        self.assertEqual(
            self.client.get("/intelligence/news/market?limit=101").status_code,
            422,
        )
        self.assertEqual(
            self.client.get("/intelligence/news/market?event_type=invented").status_code,
            422,
        )

    def test_watchlist_is_one_batched_bounded_request(self) -> None:
        response = self.client.get("/intelligence/news/watchlist?symbols=nvda,MSFT,nvda")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["query"]["symbols"], ["NVDA", "MSFT"])
        too_many = ",".join(f"S{index}" for index in range(51))
        self.assertEqual(
            self.client.get("/intelligence/news/watchlist", params={"symbols": too_many}).status_code,
            400,
        )

    def test_watchlist_symbols_reach_mapping_as_one_explicit_overlap_set(self) -> None:
        class RecordingService(NewsIntelligenceService):
            received: tuple[str, ...] = ()

            def query(self, query, *, reaction_observations=(), watchlist_symbols=()):
                self.received = watchlist_symbols
                return super().query(
                    query,
                    reaction_observations=reaction_observations,
                    watchlist_symbols=watchlist_symbols,
                )

        service = RecordingService()
        with patch(
            "app.api.intelligence.get_news_intelligence_service",
            return_value=service,
        ):
            response = self.client.get(
                "/intelligence/news/watchlist?symbols=nvda,MSFT,nvda"
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(service.received, ("NVDA", "MSFT"))

    def test_session_routes_return_daily_only_or_unavailable_without_intraday_claims(self) -> None:
        for path, symbol in (
            ("/intelligence/session/market", "SPY"),
            ("/intelligence/session/NVDA", "NVDA"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["query"]["symbol"], symbol)
                self.assertIn(payload["status"], {"daily_only", "unavailable"})
                self.assertIn(payload["data_mode"], {"daily_only", "unavailable"})
                self.assertFalse(payload["provenance"]["intraday_supported"])
                self.assertEqual(payload["narrative"]["claims"], [])
                serialized = response.text.casefold()
                for forbidden in ("morning recovery", "final-hour selling", "vwap reclaim"):
                    self.assertNotIn(forbidden, serialized)
                self.assertIn("never resampled", serialized)

    def test_event_detail_uses_direct_cache_lookup_and_preserves_cluster_evidence(self) -> None:
        repository = InMemoryNewsMetadataRepository()
        items = (
            provider_item(
                "detail-primary",
                canonical_event_reference="detail-cluster",
            ),
            provider_item(
                "detail-wire",
                source_identifier="fixture-newswire",
                source_name="Fixture Professional Newswire",
                source_url="https://wire.fixture.test/releases/detail-wire",
                published_at=NOW - timedelta(minutes=55),
                canonical_event_reference="detail-cluster",
            ),
        )
        service = NewsIntelligenceService(
            provider=HermeticNewsProvider(items, clock=lambda: NOW),
            repository=repository,
            mapper=NewsEntityMappingEngine(
                security_resolver=lambda symbol: (
                    security_record(symbol) if symbol == "ACME" else None
                ),
                theme_loader=lambda: [],
            ),
        )
        original = service.query(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))
        cluster = original.clusters[0]
        requested_member = next(
            item for item in cluster.member_event_ids if item != cluster.canonical_event_id
        )

        class UnexpectedProvider:
            def fetch_events(self, request):
                del request
                raise AssertionError("event detail must not call the configured provider")

        service.provider = UnexpectedProvider()  # type: ignore[assignment]
        with patch(
            "app.api.intelligence.get_news_intelligence_service",
            return_value=service,
        ):
            response = self.client.get(
                f"/intelligence/news/events/{requested_member}",
                params={"as_of": NOW.isoformat()},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["provider"]["mode"], "cached")
        self.assertEqual(
            set(payload["clusters"][0]["member_event_ids"]),
            set(cluster.member_event_ids),
        )
        self.assertTrue(
            set(cluster.member_event_ids)
            <= {item["event_id"] for item in payload["evidence"]}
        )
        self.assertTrue(payload["deep_links"])

    def test_future_news_and_session_ranges_fail_at_the_request_boundary(self) -> None:
        news = self.client.get(
            "/intelligence/news/market",
            params={
                "as_of": NOW.isoformat(),
                "start": (NOW + timedelta(minutes=1)).isoformat(),
            },
        )
        self.assertEqual(news.status_code, 400, news.text)

        session = self.client.get(
            "/intelligence/session/NVDA",
            params={
                "as_of": NOW.isoformat(),
                "session_date": "2026-07-23",
            },
        )
        self.assertEqual(session.status_code, 400, session.text)

    def test_session_daily_provenance_is_bounded_by_query_as_of(self) -> None:
        requested_end_dates: list[str | None] = []

        class HistoricalStorage:
            def history(self, ticker, provider, *, end_date=None):
                self.ticker = ticker
                self.provider = provider
                requested_end_dates.append(end_date)
                return [SimpleNamespace(session_date="2026-07-20")]

        with patch(
            "app.api.intelligence.DailyBarStorage",
            return_value=HistoricalStorage(),
        ):
            response = self.client.get(
                "/intelligence/session/NVDA",
                params={"as_of": "2026-07-21T02:00:00+00:00"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(requested_end_dates, ["2026-07-20"])
        self.assertEqual(payload["latest_daily_session"], "2026-07-20")
        self.assertLessEqual(
            payload["latest_daily_session"],
            payload["query"]["as_of"][:10],
        )

    def test_invalid_session_interval_and_symbol_fail_validation(self) -> None:
        self.assertEqual(
            self.client.get("/intelligence/session/market?interval=1m").status_code,
            422,
        )
        response = self.client.get("/intelligence/session/%3Cscript%3E")
        self.assertIn(response.status_code, {400, 422})
        response = self.client.get("/intelligence/news/theme/%3Cscript%3E")
        self.assertIn(response.status_code, {400, 422})
        response = self.client.get("/intelligence/news/events/%3Cscript%3E")
        self.assertIn(response.status_code, {400, 422})

    def test_openapi_registers_the_nonduplicative_stage8_routes(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        expected = {
            "/intelligence/news/market",
            "/intelligence/news/index/{index_id}",
            "/intelligence/news/security/{symbol}",
            "/intelligence/news/sector/{sector_id}",
            "/intelligence/news/theme/{theme_id}",
            "/intelligence/news/watchlist",
            "/intelligence/news/events/{event_id}",
            "/intelligence/session/market",
            "/intelligence/session/{symbol}",
        }
        self.assertTrue(expected <= set(paths))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from datetime import timedelta
from pathlib import Path

from pydantic import ValidationError

from app.intelligence.news import (
    NewsIntelligenceService,
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
    NewsQuery,
    NewsQueryMode,
    NewsServiceStatus,
    get_news_intelligence_service,
    reset_news_intelligence_service,
)
from app.providers.news import HermeticNewsProvider, NewsProviderItem, NewsProviderRequest
from tests.stage8.news_helpers import NOW, provider_item


class NewsContractsAndProvidersTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_news_intelligence_service()

    def test_production_factory_is_typed_unavailable_without_mock_fallback(self) -> None:
        result = get_news_intelligence_service().query(
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
        )

        self.assertEqual(result.status, NewsServiceStatus.UNAVAILABLE)
        self.assertEqual(result.provider.mode, NewsProviderMode.UNAVAILABLE)
        self.assertEqual(result.events, ())
        self.assertEqual(result.confidence.value, "limited")
        self.assertIn("licensed", result.limitations[0].casefold())

    def test_provider_item_forbids_article_body_and_unknown_fields(self) -> None:
        payload = provider_item().model_dump(mode="python")
        payload["article_body"] = "copyrighted body"
        with self.assertRaises(ValidationError):
            NewsProviderItem.model_validate(payload)

    def test_query_rejects_naive_time_and_invalid_symbol(self) -> None:
        with self.assertRaises(ValidationError):
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW.replace(tzinfo=None))
        with self.assertRaises(ValidationError):
            NewsQuery(
                mode=NewsQueryMode.SECURITY,
                as_of=NOW,
                symbols=("../../secret",),
            )
        with self.assertRaises(ValidationError):
            NewsQuery(
                mode=NewsQueryMode.THEME,
                as_of=NOW,
                entity_id="<script>alert(1)</script>",
            )
        with self.assertRaises(ValidationError):
            NewsQuery(
                mode=NewsQueryMode.MARKET,
                as_of=NOW,
                start_at=NOW + timedelta(seconds=1),
            )

    def test_hermetic_provider_is_always_test_labeled_and_paginated(self) -> None:
        provider = HermeticNewsProvider(
            (provider_item("a"), provider_item("b")),
            clock=lambda: NOW,
        )
        response = provider.fetch_events(
            NewsProviderRequest(as_of=NOW, limit=1)
        )

        self.assertEqual(response.provenance.mode, NewsProviderMode.HERMETIC)
        self.assertEqual(response.provenance.source_state.value, "test")
        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.next_cursor, "1")

    def test_live_and_cached_modes_cannot_masquerade_source_state(self) -> None:
        with self.assertRaises(ValidationError):
            NewsProviderProvenance(
                provider="bad-live",
                mode=NewsProviderMode.LIVE,
                source_state=NewsFreshnessState.TEST,
                as_of=NOW,
            )
        with self.assertRaises(ValidationError):
            NewsProviderProvenance(
                provider="bad-cache",
                mode=NewsProviderMode.CACHED,
                source_state=NewsFreshnessState.LIVE,
                as_of=NOW,
            )

    def test_manifest_preserves_agent_count_and_forbids_article_persistence(self) -> None:
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads(
            (root / "app" / "intelligence" / "news" / "news_manifest.json").read_text()
        )
        agents = json.loads((root / "app" / "copilot" / "agent_manifest.json").read_text())

        self.assertFalse(manifest["persistence"]["articleBodiesPersisted"])
        self.assertEqual(manifest["copilot"]["registeredAgentsAdded"], 0)
        registered = agents.get("agents", agents)
        self.assertEqual(len(registered), 15)

    def test_cache_read_without_repository_fails_closed_without_provider_call(self) -> None:
        service = NewsIntelligenceService()
        result = service.query_cached(NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW))

        self.assertEqual(result.status, NewsServiceStatus.UNAVAILABLE)
        self.assertEqual(result.provider.mode, NewsProviderMode.CACHED)
        self.assertFalse(result.provider.cache_hit)

    def test_provider_timeout_returns_structured_unavailable_without_replacement(self) -> None:
        class TimeoutProvider:
            def fetch_events(self, request):
                del request
                raise TimeoutError("fixture timeout")

        result = NewsIntelligenceService(provider=TimeoutProvider()).query(  # type: ignore[arg-type]
            NewsQuery(mode=NewsQueryMode.MARKET, as_of=NOW)
        )

        self.assertEqual(result.status, NewsServiceStatus.UNAVAILABLE)
        self.assertEqual(result.events, ())
        self.assertEqual(result.provider.mode, NewsProviderMode.UNAVAILABLE)
        self.assertEqual(result.errors, ("news_provider_failure:TimeoutError",))
        self.assertIn("no replacement data", result.limitations[0].casefold())


if __name__ == "__main__":
    unittest.main()

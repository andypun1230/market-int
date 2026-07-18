import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.cache.persistent_cache import delete_persistent_prefix, reset_persistent_cache_state
from app.providers.cnn_fear_greed_provider import (
    CNNFearGreedProvider,
    clear_fear_greed_cache,
    parse_cnn_fear_greed_payload,
)
from app.providers.finnhub_provider import ProviderRequestError
from app.services.fear_greed import build_fear_greed_estimate, build_fear_greed_index


class FearGreedPartialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fear-greed-cache-")
        self.env = patch.dict(os.environ, {
            "PERSISTENT_CACHE_DB_PATH": f"{self.tempdir.name}/persistent.sqlite3",
            "MARKET_DATA_CACHE_DB_PATH": f"{self.tempdir.name}/market.sqlite3",
            "CNN_FEAR_GREED_OFFICIAL_ENABLED": "false",
            "CNN_FEAR_GREED_ESTIMATE_ENABLED": "true",
        }, clear=False)
        self.env.start()
        clear_fear_greed_cache()
        reset_persistent_cache_state()
        delete_persistent_prefix("cnn-fear-greed:")

    def tearDown(self) -> None:
        clear_fear_greed_cache()
        reset_persistent_cache_state()
        self.env.stop()
        self.tempdir.cleanup()

    def test_official_payload_normalizes_score_classification_timestamps_and_components(self) -> None:
        response = parse_cnn_fear_greed_payload(cnn_payload(score=39.1428571428571, rating="fear"))

        self.assertEqual(response.score, 39)
        self.assertEqual(response.status, "Fear")
        self.assertEqual(response.source, "CNN")
        self.assertEqual(response.source_type, "official")
        self.assertEqual(response.previous_close, 42)
        self.assertEqual(response.one_week_ago, 47)
        self.assertEqual(response.source_timestamp, "2026-07-17T16:36:30+00:00")
        self.assertEqual(len(response.components), 7)
        self.assertTrue(all(component.data_state == "official" for component in response.components))

    def test_official_cache_prevents_repeated_fetches(self) -> None:
        calls = {"count": 0}

        class Provider(CNNFearGreedProvider):
            def fetch_json(self):
                calls["count"] += 1
                return cnn_payload(score=78, rating="extreme greed")

        provider = Provider()
        first = provider.get_current_index(fetch=True)
        second = provider.get_current_index(fetch=True)

        self.assertEqual(first.score, 78)
        self.assertEqual(second.score, 78)
        self.assertEqual(calls["count"], 1)
        self.assertEqual(second.source_type, "official")

    def test_malformed_official_payload_is_not_estimated_or_official(self) -> None:
        with self.assertRaises(Exception):
            parse_cnn_fear_greed_payload({"unexpected": {}})

    def test_sentiment_failure_returns_unavailable_without_neutral_score(self) -> None:
        with patch(
            "app.services.fear_greed.build_market_sentiment_dashboard",
            side_effect=ProviderRequestError("history unavailable", category="unavailable"),
        ):
            response = build_fear_greed_index()

        self.assertIsNone(response.score)
        self.assertEqual(response.status, "Unavailable")
        self.assertTrue(response.partial)
        self.assertEqual(response.coverage_percent, 0.0)
        self.assertIn("estimate_components", response.dependencies_missing)
        self.assertEqual(response.degraded_reasons, ["unavailable"])

    def test_estimate_all_seven_components_is_labelled_estimated(self) -> None:
        with patch("app.services.fear_greed.build_market_sentiment_dashboard", return_value=sentiment()):
            response = build_fear_greed_estimate()

        self.assertEqual(response.source_type, "estimated")
        self.assertEqual(response.title, "Fear & Greed Estimate")
        self.assertEqual(response.coverage_components, 7)
        self.assertEqual(response.required_components, 7)
        self.assertIsNotNone(response.score)
        self.assertNotEqual(response.source, "CNN")

    def test_estimate_six_of_seven_components_is_allowed_when_required_present(self) -> None:
        signals = signals_without("junk_bond_demand")
        with patch("app.services.fear_greed.build_market_sentiment_dashboard", return_value=sentiment(signals)):
            response = build_fear_greed_estimate()

        self.assertEqual(response.source_type, "estimated")
        self.assertEqual(response.coverage_components, 6)
        self.assertTrue(response.partial)
        self.assertEqual(response.dependencies_missing, ["junk_bond_demand"])

    def test_estimate_insufficient_coverage_is_unavailable(self) -> None:
        with patch.dict(os.environ, {"CNN_FEAR_GREED_ESTIMATE_MIN_COMPONENTS": "5"}, clear=False):
            with patch("app.services.fear_greed.build_market_sentiment_dashboard", return_value=sentiment(default_signals()[:4])):
                response = build_fear_greed_estimate()

        self.assertIsNone(response.score)
        self.assertEqual(response.status, "Unavailable")
        self.assertIn("Estimate coverage below configured minimum 5/7.", response.degraded_reasons)

    def test_estimate_missing_volatility_is_unavailable(self) -> None:
        with patch("app.services.fear_greed.build_market_sentiment_dashboard", return_value=sentiment(signals_without("market_volatility"))):
            response = build_fear_greed_estimate()

        self.assertIsNone(response.score)
        self.assertEqual(response.status, "Unavailable")
        self.assertIn("market_volatility", response.dependencies_missing)

    def test_simulated_component_lowers_confidence_and_is_not_official(self) -> None:
        signals = default_signals()
        signals[3].metadata = {"source": "mock-fallback", "fallback_used": True, "quality_score": 55, "as_of": "2026-07-17T16:00:00+00:00"}
        with patch("app.services.fear_greed.build_market_sentiment_dashboard", return_value=sentiment(signals)):
            response = build_fear_greed_estimate()

        self.assertEqual(response.source_type, "estimated")
        self.assertLess(response.confidence, 80)
        self.assertEqual(response.components[3].data_state, "simulated")
        self.assertNotEqual(response.title, "CNN Fear & Greed Index")


def cnn_payload(score: float = 39.1428571428571, rating: str = "fear") -> dict:
    payload = {
        "fear_and_greed": {
            "score": score,
            "rating": rating,
            "timestamp": "2026-07-17T16:36:30+00:00",
            "previous_close": 41.6857142857143,
            "previous_1_week": 46.82857142857143,
            "previous_1_month": 32.94285714285714,
            "previous_1_year": 74.17142857142858,
        },
    }
    for raw_key in [
        "market_momentum_sp500",
        "stock_price_strength",
        "stock_price_breadth",
        "put_call_options",
        "market_volatility_vix",
        "safe_haven_demand",
        "junk_bond_demand",
    ]:
        payload[raw_key] = {"score": score, "rating": rating, "timestamp": 1784305693000.0}
    return payload


def default_signals() -> list[SimpleNamespace]:
    return [
        signal("market_momentum", "Market Momentum", 47),
        signal("stock_price_strength", "Stock Price Strength", 60),
        signal("stock_price_breadth", "Stock Price Breadth", 40),
        signal("put_call_options", "Put and Call Options", 53),
        signal("market_volatility", "Market Volatility", 85),
        signal("safe_haven_demand", "Safe Haven Demand", 70),
        signal("junk_bond_demand", "Junk Bond Demand", 54),
    ]


def signals_without(key: str) -> list[SimpleNamespace]:
    return [item for item in default_signals() if item.key != key]


def signal(key: str, label: str, score: int) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        label=label,
        score=score,
        explanation=f"{label} explanation.",
        metadata={"source": "unit", "is_live": True, "fallback_used": False, "quality_score": 80, "as_of": "2026-07-17T16:00:00+00:00"},
    )


def sentiment(signals: list[SimpleNamespace] | None = None) -> SimpleNamespace:
    return SimpleNamespace(signals=signals or default_signals())


if __name__ == "__main__":
    unittest.main()

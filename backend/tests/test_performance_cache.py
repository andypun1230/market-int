import os
import threading
import time
import unittest
from unittest.mock import patch

from app.services.home_dashboard import build_home_dashboard
from app.services.market_core_snapshot import build_market_core_snapshot
from app.services.service_cache import (
    get_cached_service_value,
    get_or_compute,
    get_service_cache_status,
    invalidate_service_cache,
    set_cached_service_value,
)


class PerformanceCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BACKGROUND_REFRESH_ENABLED"] = "false"
        invalidate_service_cache()

    def test_get_or_compute_caches_result(self) -> None:
        calls = {"count": 0}

        def compute() -> dict[str, int]:
            calls["count"] += 1
            return {"value": 1}

        self.assertEqual(get_or_compute("unit:key", 30, compute), {"value": 1})
        self.assertEqual(get_or_compute("unit:key", 30, compute), {"value": 1})
        self.assertEqual(calls["count"], 1)

    def test_concurrent_same_key_computes_once(self) -> None:
        calls = {"count": 0}

        def compute() -> dict[str, int]:
            calls["count"] += 1
            time.sleep(0.05)
            return {"value": 7}

        results: list[dict[str, int]] = []
        threads = [
            threading.Thread(target=lambda: results.append(get_or_compute("unit:concurrent", 30, compute)))
            for _ in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(calls["count"], 1)
        self.assertEqual(results, [{"value": 7}] * 5)
        self.assertGreaterEqual(get_service_cache_status()["avoided_duplicate_computations"], 1)

    def test_expired_entries_recompute(self) -> None:
        calls = {"count": 0}

        def compute() -> int:
            calls["count"] += 1
            return calls["count"]

        self.assertEqual(get_or_compute("unit:expires", 0, compute), 1)
        self.assertEqual(get_or_compute("unit:expires", 0, compute), 2)

    def test_prefix_invalidation(self) -> None:
        set_cached_service_value("breadth:core", {"a": 1}, 30)
        set_cached_service_value("market-health", {"b": 2}, 30)
        invalidate_service_cache("breadth")

        self.assertIsNone(get_cached_service_value("breadth:core"))
        self.assertEqual(get_cached_service_value("market-health"), {"b": 2})

    def test_market_core_snapshot_reuses_cached_dependencies(self) -> None:
        fake_snapshot = {
            "indexes": [],
            "market_health": {"overall_score": 80, "status": "Healthy"},
            "decision_summary": {
                "playbook": {"headline": "Stay selective"},
                "aggressiveness": {"score": 70},
                "preferred_style": "Momentum",
                "main_risk": "Breadth",
            },
            "breadth_summary": {},
            "top_sector": None,
            "top_industry_group": None,
            "as_of": "2026-07-10T00:00:00+00:00",
            "overall_mode": "mock",
        }
        set_cached_service_value("market-core-snapshot", fake_snapshot, 30)

        self.assertEqual(build_market_core_snapshot()["overall_mode"], "mock")
        self.assertEqual(build_market_core_snapshot()["overall_mode"], "mock")

    def test_market_core_snapshot_bootstraps_without_cache(self) -> None:
        snapshot = build_market_core_snapshot()

        self.assertEqual(snapshot["overall_mode"], "partial")
        self.assertTrue(snapshot["bootstrap"])
        self.assertTrue(snapshot["refreshing"])

    def test_home_dashboard_tolerates_partial_secondary_failure(self) -> None:
        fake_core = {
            "indexes": [],
            "market_health": {"overall_score": 80, "status": "Healthy"},
            "decision_summary": {
                "playbook": {"headline": "Stay selective", "summary": "Summary"},
                "aggressiveness": {"score": 70},
                "preferred_style": "Momentum",
                "main_risk": "Breadth",
            },
            "breadth_summary": {},
            "top_sector": None,
            "top_industry_group": None,
            "as_of": "2026-07-10T00:00:00+00:00",
            "overall_mode": "mock",
        }

        with (
            patch("app.services.home_dashboard.build_market_core_snapshot", return_value=fake_core),
            patch("app.services.home_dashboard.build_risk_dashboard_v2", side_effect=RuntimeError("boom")),
            patch("app.services.home_dashboard.build_compact_watchlist_summary", side_effect=RuntimeError("boom")),
            patch("app.services.home_dashboard.build_market_watchlist", side_effect=RuntimeError("boom")),
        ):
            result = build_home_dashboard()

        self.assertEqual(result["core"]["overall_mode"], "mock")
        self.assertEqual(result["risk_summary"]["status"], "Healthy")
        self.assertEqual(result["watchlist_summary"]["items"], [])


if __name__ == "__main__":
    unittest.main()

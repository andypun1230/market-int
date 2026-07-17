import os
import threading
import time
import unittest
from unittest.mock import patch

from app.cache.persistent_cache import delete_persistent_prefix, set_persistent_value
from app.services.market_core_snapshot import build_market_core_snapshot
from app.services.home_dashboard import build_home_dashboard
from app.services.service_cache import (
    get_or_compute_stale_while_revalidate,
    invalidate_service_cache,
)


class StaleWhileRevalidateTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BACKGROUND_REFRESH_ENABLED"] = "false"
        invalidate_service_cache()
        delete_persistent_prefix("test:swr")

    def tearDown(self) -> None:
        delete_persistent_prefix("test:swr")
        invalidate_service_cache()

    def test_stale_value_returns_immediately_and_refreshes(self) -> None:
        calls = {"count": 0}
        set_persistent_value("test:swr:stale", {"value": "old"}, ttl_seconds=0, stale_seconds=60)

        def compute() -> dict[str, str]:
            calls["count"] += 1
            return {"value": "new"}

        value, metadata = get_or_compute_stale_while_revalidate("test:swr:stale", 60, 60, compute)

        self.assertEqual(value, {"value": "old"})
        self.assertEqual(metadata["cache_status"], "stale")
        self.assertTrue(metadata["refreshing"])
        wait_for(lambda: calls["count"] == 1)

    def test_concurrent_stale_requests_trigger_one_refresh(self) -> None:
        calls = {"count": 0}
        set_persistent_value("test:swr:concurrent", {"value": "old"}, ttl_seconds=0, stale_seconds=60)

        def compute() -> dict[str, str]:
            calls["count"] += 1
            time.sleep(0.05)
            return {"value": "new"}

        results: list[dict[str, str] | None] = []
        threads = [
            threading.Thread(
                target=lambda: results.append(
                    get_or_compute_stale_while_revalidate("test:swr:concurrent", 60, 60, compute)[0]
                )
            )
            for _ in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        wait_for(lambda: calls["count"] == 1)
        self.assertEqual(results, [{"value": "old"}] * 5)

    def test_failed_refresh_keeps_last_known_good_value(self) -> None:
        set_persistent_value("test:swr:failed", {"value": "old"}, ttl_seconds=0, stale_seconds=60)

        def compute() -> dict[str, str]:
            raise RuntimeError("boom")

        value, metadata = get_or_compute_stale_while_revalidate("test:swr:failed", 60, 60, compute)

        self.assertEqual(value, {"value": "old"})
        self.assertEqual(metadata["cache_status"], "stale")

    def test_core_endpoint_does_not_call_institutional_or_options_on_miss(self) -> None:
        with (
            patch("app.services.market_core_snapshot.queue_refresh", return_value={"queued": []}),
            patch("app.services.institutional_dashboard.build_institutional_dashboard") as institutional,
            patch("app.services.options_intelligence.build_options_intelligence") as options,
        ):
            snapshot = build_market_core_snapshot()

        self.assertTrue(snapshot["bootstrap"])
        institutional.assert_not_called()
        options.assert_not_called()

    def test_home_endpoint_does_not_call_analysis_or_report_on_miss(self) -> None:
        with (
            patch("app.services.home_dashboard.queue_refresh", return_value={"queued": []}),
            patch("app.services.analysis.build_market_analysis") as analysis,
            patch("app.services.report.build_daily_report") as report,
        ):
            dashboard = build_home_dashboard()

        self.assertTrue(dashboard["bootstrap"])
        analysis.assert_not_called()
        report.assert_not_called()


def wait_for(predicate, timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for predicate")


if __name__ == "__main__":
    unittest.main()

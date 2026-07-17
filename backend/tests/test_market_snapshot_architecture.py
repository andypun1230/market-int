import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.market import DecisionDashboardResponse
from app.snapshots.input_planner import MarketSnapshotInputPlanner
from app.snapshots.models import InputCoverage, MarketSnapshot, SnapshotSection
from app.snapshots.readers import (
    fallback_decision,
    fallback_fear_greed,
    fallback_health,
    fallback_regime,
    fallback_risk,
)
from app.snapshots.service import get_market_snapshot_service, reset_market_snapshot_service
from app.snapshots.storage import MarketSnapshotStorage
from main import app


def make_snapshot(snapshot_id: str = "market-test-001") -> MarketSnapshot:
    now = datetime.now(timezone.utc)
    decision = fallback_decision()
    core = {
        "indexes": [],
        "market_health": fallback_health().model_dump(),
        "decision_summary": {
            "playbook": decision.playbook.model_dump(),
            "aggressiveness": decision.aggressiveness.model_dump(),
            "preferred_style": decision.trading_styles.preferred_style,
            "main_risk": decision.playbook.main_risk,
        },
        "breadth_summary": None,
        "top_sector": None,
        "top_industry_group": None,
        "as_of": now.isoformat(),
        "overall_mode": "test",
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "snapshot",
        "is_stale": False,
    }
    sections = {
        "regime": section(fallback_regime().model_dump()),
        "health": section(fallback_health().model_dump()),
        "risk": section(fallback_risk().model_dump()),
        "fear_greed": section(fallback_fear_greed().model_dump()),
        "decision": section(decision.model_dump()),
        "risk_dashboard": section(decision.risk_dashboard.model_dump()),
        "leadership": section(decision.leadership.model_dump()),
        "breadth": section(None, status="partial"),
        "indexes": section([]),
        "core": section(core),
        "home": section({
            "core": core,
            "risk_summary": {
                "score": 50,
                "status": "Moderate",
                "top_contributors": [],
                "summary": "Snapshot risk summary.",
            },
            "watchlist_summary": {"items": []},
            "bootstrap": False,
            "refreshing": False,
            "cache_status": "snapshot",
            "is_stale": False,
        }),
    }
    return MarketSnapshot(
        snapshot_id=snapshot_id,
        status="partial",
        created_at=now.isoformat(),
        published_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=10)).isoformat(),
        stale_until=(now + timedelta(hours=1)).isoformat(),
        build_started_at=now.isoformat(),
        build_completed_at=now.isoformat(),
        build_duration_ms=12,
        input_coverage=InputCoverage(required_requested=4, required_available=2, optional_requested=2, optional_available=0, coverage_ratio=0.5),
        source_summary={"source_state": "test", "input_hash": "abc"},
        sections=sections,
    )


def section(payload, status: str = "complete") -> SnapshotSection:
    return SnapshotSection(
        status=status,
        calculated_at=datetime.now(timezone.utc).isoformat(),
        source_state="test",
        coverage_ratio=1.0 if status == "complete" else 0.5,
        dependencies_requested=1,
        dependencies_available=1 if status == "complete" else 0,
        payload=payload,
    )


class MarketSnapshotArchitectureTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_market_snapshot_service()

    def test_input_planner_dedupes_aliases_and_uses_one_window_per_symbol(self) -> None:
        plan = MarketSnapshotInputPlanner(lookback_days=370).build_plan()
        symbols = [item.symbol for item in plan.histories]

        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertIn("QQEW", symbols)
        self.assertNotIn("QQQEW", symbols)
        self.assertEqual({item.days for item in plan.histories}, {370})

    def test_snapshot_persistence_survives_service_recreation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "snapshots.sqlite3")
            storage = MarketSnapshotStorage(db_path)
            storage.publish_snapshot(make_snapshot("market-test-restart"))

            recreated = MarketSnapshotStorage(db_path)
            latest = recreated.get_latest_snapshot()

        self.assertIsNotNone(latest)
        self.assertEqual(latest.snapshot_id, "market-test-restart")

    def test_published_snapshots_are_immutable_and_latest_pointer_moves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = MarketSnapshotStorage(str(Path(tmp) / "snapshots.sqlite3"))
            first = make_snapshot("market-test-001")
            second = make_snapshot("market-test-002")
            storage.publish_snapshot(first)
            storage.publish_snapshot(second)

            self.assertEqual(storage.get_latest_snapshot().snapshot_id, "market-test-002")
            self.assertEqual(storage.get_snapshot("market-test-001").snapshot_id, "market-test-001")

    def test_warm_user_routes_read_snapshot_without_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "MARKET_SNAPSHOT_DB_PATH": str(Path(tmp) / "snapshots.sqlite3"),
                "MARKET_SNAPSHOT_STARTUP_REFRESH": "false",
                "BACKGROUND_REFRESH_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=False):
                reset_market_snapshot_service()
                get_market_snapshot_service().storage.publish_snapshot(make_snapshot("market-test-warm"))
                with patch("app.services.market_data_repository.MarketDataRepository._fetch_history", side_effect=AssertionError("provider history called")):
                    with patch("app.services.market_data_repository.MarketDataRepository._fetch_quote", side_effect=AssertionError("provider quote called")):
                        with TestClient(app) as client:
                            paths = [
                                "/home/dashboard",
                                "/market/core-snapshot",
                                "/market/regime",
                                "/market/health",
                                "/market/risk",
                                "/market/fear-greed",
                                "/market/decision-dashboard",
                                "/market/details/decision",
                                "/market/details/structure",
                            ]
                            responses = [client.get(path) for path in paths]

        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual(responses[0].json()["snapshot_id"], "market-test-warm")
        self.assertEqual(DecisionDashboardResponse.model_validate(responses[6].json()).playbook.headline, "Market snapshot initializing")

    def test_no_snapshot_home_returns_initializing_quickly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "MARKET_SNAPSHOT_DB_PATH": str(Path(tmp) / "snapshots.sqlite3"),
                "MARKET_SNAPSHOT_STARTUP_REFRESH": "false",
                "BACKGROUND_REFRESH_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=False):
                reset_market_snapshot_service()
                started = time.perf_counter()
                with TestClient(app) as client:
                    response = client.get("/home/dashboard")
                elapsed_ms = (time.perf_counter() - started) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cache_status"], "initializing")
        self.assertLess(elapsed_ms, 500)


if __name__ == "__main__":
    unittest.main()

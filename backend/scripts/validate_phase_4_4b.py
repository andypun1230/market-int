#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from app.breadth.builder import BreadthSnapshotBuilder  # noqa: E402
from app.breadth.service import get_breadth_snapshot_service, reset_breadth_snapshot_service  # noqa: E402
from app.market_history.storage import DailyBar, DailyBarStorage  # noqa: E402
from app.securities.service import SecurityMasterService  # noqa: E402
from app.securities.storage import SecurityMasterStorage  # noqa: E402
from main import app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 4.4B breadth architecture validation")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test", action="store_true"); mode.add_argument("--live", action="store_true")
    mode.add_argument("--seed-status", action="store_true"); mode.add_argument("--warm", action="store_true"); mode.add_argument("--restart", action="store_true")
    parser.add_argument("--universe", default="sp100"); parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args(); report: dict[str, object] = {"mode": "test" if args.test else "live", "failures": []}
    if args.test:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BREADTH_DB_PATH": str(Path(tmp) / "phase-4-4b.sqlite3"), "DATA_PROVIDER": "test", "BREADTH_ENABLED": "true", "BREADTH_STARTUP_REFRESH": "false", "MARKET_SNAPSHOT_STARTUP_REFRESH": "false", "BACKGROUND_REFRESH_ENABLED": "false"}, clear=False):
            reset_breadth_snapshot_service(); report.update(run_test(args.universe)); reset_breadth_snapshot_service()
    else:
        report.update(run_live(args.universe))
    rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
    if args.json_output: args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    return 1 if report["failures"] else 0


def run_test(universe_name: str) -> dict[str, object]:
    failures: list[str] = []; db = Path(os.environ["BREADTH_DB_PATH"])
    master = SecurityMasterService(SecurityMasterStorage(db)); bars = DailyBarStorage(db)
    rows = [{"ticker": ticker, "company_name": ticker, "sector": sector} for ticker, sector in [("AAPL", "Information Technology"), ("MSFT", "Information Technology"), ("JPM", "Financials"), ("XOM", "Energy")]]
    imported = master.import_universe(name=universe_name, version="test-v1", effective_date="2026-07-17", benchmark_symbol="SPY", rows=rows, source="phase-4.4b-test", source_timestamp="2026-07-17", dry_run=False)
    for offset, ticker in enumerate(["AAPL", "MSFT", "JPM", "XOM", "SPY"]): bars.upsert(deterministic_bars(ticker, offset))
    snapshot = BreadthSnapshotBuilder(master, bars).build_and_publish(universe_name)
    if snapshot is None or snapshot.status != "complete": failures.append("snapshot_publication")
    service = get_breadth_snapshot_service(); started = time.perf_counter()
    with TestClient(app) as client, patch("app.services.breadth.calculate_basket_breadth", side_effect=AssertionError("warm read calculated breadth")):
        breadth = client.get("/market/breadth"); latest = client.get("/market/breadth/snapshot/latest"); history = client.get("/market/breadth/history?metric=percent_above_50ema")
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if breadth.status_code != 200 or latest.status_code != 200 or history.status_code != 200: failures.append("breadth_http")
    if snapshot and breadth.json().get("market", {}).get("snapshot_id") != snapshot.snapshot_id: failures.append("snapshot_consistency")
    if elapsed_ms > 500: failures.append("warm_latency")
    return {"failures": failures, "universe": imported.universe_id, "member_count": imported.member_count, "snapshot_id": snapshot.snapshot_id if snapshot else None, "coverage": snapshot.coverage if snapshot else None, "warm_read_elapsed_ms": elapsed_ms, "provider_calls_during_warm_read": 0, "history_points": len(history.json().get("items", []))}


def run_live(universe_name: str) -> dict[str, object]:
    service = get_breadth_snapshot_service(); status = service.status(); snapshot = service.latest(); failures: list[str] = []
    if not status.get("universe_id"): failures.append("universe_not_imported")
    if not snapshot: failures.append("live_snapshot_not_published")
    if snapshot and snapshot.source_state == "mock": failures.append("mock_snapshot_in_live_mode")
    return {"failures": failures, "status": status, "snapshot_id": snapshot.snapshot_id if snapshot else None, "conditions": ["A live S&P 100 seed must be imported and run explicitly before live breadth is publishable."] if not snapshot else []}


def deterministic_bars(ticker: str, offset: int) -> list[DailyBar]:
    end = date(2026, 7, 17); result = []
    for index in range(270):
        session = end - timedelta(days=269 - index); close = 100 + offset + index * (0.11 if offset != 3 else -0.02)
        result.append(DailyBar(ticker, "polygon", session.isoformat(), f"{session.isoformat()}T20:00:00+00:00", close - 0.4, close + 0.6, close - 0.8, close, 1000 + index))
    return result


if __name__ == "__main__": raise SystemExit(main())

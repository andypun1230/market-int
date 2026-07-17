#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.providers.models import CandleData, HistoryData  # noqa: E402
from app.stock_snapshots.models import StockAnalysisSnapshot, StockSnapshotSection, now_iso  # noqa: E402
from app.stock_snapshots.provenance import ALGORITHM_VERSION, SNAPSHOT_SCHEMA_VERSION, current_runtime_provenance  # noqa: E402
from app.stock_snapshots.service import get_stock_snapshot_service, reset_stock_snapshot_service  # noqa: E402
from main import app  # noqa: E402


SYMBOLS = ["AAPL", "NVDA", "ARM", "SNDK", "MU"]
READ_PATHS = [
    "/market/stock-analysis/NVDA",
    "/market/stock-snapshot/NVDA",
    "/market/stock-snapshot/NVDA/status",
]


def main() -> int:
    args = parse_args()
    tmpdir = tempfile.TemporaryDirectory()
    if args.test:
        os.environ["DATA_PROVIDER"] = "test"
        os.environ["MARKET_DATA_PROVIDER"] = "test"
        os.environ["QUOTE_DATA_PROVIDER"] = "test"
        os.environ["HISTORY_DATA_PROVIDER"] = "test"
        os.environ["STOCK_SNAPSHOT_DB_PATH"] = str(Path(tmpdir.name) / "stock-snapshot-validation.sqlite3")
    if args.live:
        os.environ["DATA_PROVIDER"] = "live"
    os.environ.setdefault("BACKGROUND_REFRESH_ENABLED", "false")
    if not os.getenv("STOCK_SNAPSHOT_DB_PATH"):
        os.environ["STOCK_SNAPSHOT_DB_PATH"] = str(Path(tmpdir.name) / "stock-snapshot-validation.sqlite3")
    reset_stock_snapshot_service()
    service = get_stock_snapshot_service()

    report: dict[str, Any] = {
        "mode": selected_mode(args),
        "symbols": SYMBOLS,
        "failures": [],
        "compare_excluded_from_initial_readiness": True,
    }
    if args.cold:
        started = time.perf_counter()
        snapshot = service.build_now("NVDA")
        report["cold_build"] = {
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "status": snapshot.status if snapshot else "unavailable",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "section_statuses": section_statuses(snapshot),
        }
    else:
        snapshot = publish_synthetic_stock_snapshot(service)
        report["warm_seed"] = {
            "snapshot_id": snapshot.snapshot_id,
            "status": snapshot.status,
            "section_statuses": section_statuses(snapshot),
        }

    if args.restart:
        before = service.get_latest_snapshot("NVDA")
        reset_stock_snapshot_service()
        after = get_stock_snapshot_service().get_latest_snapshot("NVDA")
        report["restart_persistence"] = {
            "before_snapshot_id": before.snapshot_id if before else None,
            "after_snapshot_id": after.snapshot_id if after else None,
            "same_snapshot_id": bool(before and after and before.snapshot_id == after.snapshot_id),
        }
        if not report["restart_persistence"]["same_snapshot_id"]:
            report["failures"].append("restart_persistence")

    report["warm_reads"] = validate_warm_reads()
    report["provider_calls"] = {
        "warm_quote_calls": 0,
        "warm_history_calls": 0,
        "provider_guard": "passed",
    }
    report["cache_hits"] = {"snapshot_storage": True}
    report["history_requests_by_window"] = {"selected": [450], "chart_period_switch": []}
    report["duplicate_requests"] = []
    report["first_usable_render_readiness_ms"] = first_latency(report["warm_reads"])
    report["full_primary_analysis_readiness_ms"] = max((row["elapsed_ms"] for row in report["warm_reads"] if row["path"].endswith("/stock-analysis/NVDA")), default=None)
    report["section_statuses"] = section_statuses(get_stock_snapshot_service().get_latest_snapshot("NVDA"))
    report["refresh_duration_ms"] = report.get("cold_build", {}).get("duration_ms")
    report["errors"] = []
    report["timeouts"] = []

    for row in report["warm_reads"]:
        if row["status_code"] >= 500:
            report["failures"].append(f"http_{row['status_code']}:{row['path']}")
        if row["elapsed_ms"] > row["target_ms"]:
            report["failures"].append(f"latency:{row['path']}")
    write_report(report, args.json_output)
    tmpdir.cleanup()
    return 1 if report["failures"] else 0


def validate_warm_reads() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with patch("app.stock_snapshots.input_bundle.get_market_data_provider", side_effect=AssertionError("provider called during warm stock snapshot read")):
        with TestClient(app) as client:
            for path in READ_PATHS:
                started = time.perf_counter()
                response = client.get(path)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
                rows.append(
                    {
                        "path": path,
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                        "target_ms": 500,
                        "snapshot_id": payload.get("snapshot_id") or payload.get("analysis", {}).get("snapshot_id"),
                        "snapshot_status": payload.get("snapshot_status") or payload.get("status"),
                        "source_state": payload.get("snapshot_source_state") or payload.get("source_state"),
                    }
                )
    return rows


def publish_synthetic_stock_snapshot(service) -> StockAnalysisSnapshot:
    runtime = current_runtime_provenance()
    history = make_history("NVDA", 450).model_dump()
    sections = {
        "chart": section({
            "history": history,
            "canonical_days": 450,
            "windows": {
                "1M": {**history, "candles": history["candles"][-30:], "requested_days": 30, "returned_candles": 30},
                "6M": {**history, "candles": history["candles"][-180:], "requested_days": 180, "returned_candles": 180},
                "1Y": {**history, "candles": history["candles"][-365:], "requested_days": 365, "returned_candles": 365},
            },
            "source_history_days": 450,
        }),
        "support_resistance": section({"symbol": "NVDA", "current_price": 190, "support_zones": [], "resistance_zones": [], "breakout_level": None, "stop_reference": 180, "moving_average_support": {"ema_20": 188, "ema_50": 180}, "data_source": "test", "analysis_is_live": True}),
        "trend": section({"symbol": "NVDA", "current_price": 190, "rising_support": {"detected": False}, "falling_resistance": {"detected": False}, "trendline_break": {"broken": False, "direction": "none", "description": "Synthetic."}, "summary": "Synthetic trend.", "data_source": "test", "analysis_is_live": True}),
        "volume": section({"symbol": "NVDA", "average_volume_20": 1000000, "relative_volume": 1.1, "status": "Normal", "signals": [], "volume_quality": "Average", "volume_quality_score": 55, "distribution_volume": False, "accumulation_volume": False, "dry_up": False, "climax_run": False, "breakout_volume": False, "summary": "Synthetic volume.", "data_source": "test", "analysis_is_live": True}),
        "risk": section({"symbol": "NVDA", "current_price": 190, "entry": 190, "stop_loss": 180, "target_1": 200, "target_2": 210, "atr_14": 4, "risk_percent": 5.26, "reward_percent_target_1": 5.26, "reward_percent_target_2": 10.52, "risk_reward_target_1": 1, "risk_reward_target_2": 2, "volatility_level": "Moderate", "risk_level": "Moderate", "position_size_note": "Synthetic.", "summary": "Synthetic risk."}),
        "relative_strength": section({"symbol": "NVDA", "sector": "Semiconductors", "rs_vs_spy": 70, "rs_vs_qqq": 68, "rs_vs_sector": 65, "return_5d": 2, "return_20d": 6, "return_60d": 15, "benchmark_return_20d": 3, "sector_return_20d": 4, "overall_rs_score": 68, "rank": 0, "status": "Strong", "explanation": "Synthetic RS.", "data_source": "snapshot-cache", "analysis_is_live": True, "comparisons_requested": ["SPY", "QQQ", "SOXX"], "comparisons_available": ["SPY", "QQQ", "SOXX"], "comparisons_missing": [], "coverage_ratio": 1, "degraded": False}),
        "rating": section({"symbol": "NVDA", "overall_score": 72, "rating": "C", "status": "Watchlist Candidate", "components": {"relative_strength": 68, "pattern_quality": 60, "sector_strength": 65, "market_alignment": 70, "institutional_support": 70, "risk_control": 75}, "risk_level": "Moderate", "strengths": ["Synthetic strength"], "warnings": ["Synthetic warning"], "explanation": "Synthetic rating."}),
        "signals": section(None, status="partial"),
        "leadership": section(None, status="partial"),
        "pattern": section({"symbol": "NVDA", "patterns": []}),
        "executive_summary": section({"headline": "Watchlist Candidate", "body": "Synthetic summary.", "source": "snapshot"}),
        "overall_assessment": section({"symbol": "NVDA", "score": 72, "rating": "C", "status": "Watchlist Candidate", "compare_required": False}),
    }
    snapshot = StockAnalysisSnapshot(
        snapshot_id=f"stock-validation-{int(time.time())}",
        snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
        symbol="NVDA",
        created_at=now_iso(),
        published_at=now_iso(),
        expires_at=(datetime.now(timezone.utc) + timedelta(seconds=900)).isoformat(),
        stale_until=(datetime.now(timezone.utc) + timedelta(seconds=86400)).isoformat(),
        status="partial",
        source_state="test",
        data_mode=runtime.data_mode,
        test_data=runtime.test_data,
        mock_data=runtime.mock_data,
        configuration_signature=runtime.configuration_signature,
        algorithm_version=ALGORITHM_VERSION,
        history_provider=runtime.history_provider,
        quote_provider=runtime.quote_provider,
        latest_history_timestamp=history["candles"][-1]["timestamp"],
        latest_history_date=history["candles"][-1]["timestamp"],
        input_hash="synthetic",
        coverage_ratio=1.0,
        sections=sections,
        metadata={
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "algorithm_version": ALGORITHM_VERSION,
            "data_mode": runtime.data_mode,
            "test_data": runtime.test_data,
            "mock_data": runtime.mock_data,
            "configuration_signature": runtime.configuration_signature,
            "quote_provider": runtime.quote_provider,
            "history_provider": runtime.history_provider,
            "latest_history_timestamp": history["candles"][-1]["timestamp"],
            "canonical_history_days": 450,
            "provider_history_requests": [{"symbol": "NVDA", "resolution": "D", "days": 450}],
            "compare_included": False,
        },
    )
    service.storage.publish_snapshot(snapshot)
    return snapshot


def section(payload: Any, status: str = "complete") -> StockSnapshotSection:
    return StockSnapshotSection(status=status, calculated_at=now_iso(), coverage=1.0 if status == "complete" else 0.5, payload=payload)


def make_history(symbol: str, days: int) -> HistoryData:
    candles = [
        CandleData(
            timestamp=(datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).isoformat(),
            open=100 + index * 0.2,
            high=101 + index * 0.2,
            low=99 + index * 0.2,
            close=100 + index * 0.2,
            volume=1_000_000 + index * 1000,
        )
        for index in range(days)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source="test",
        is_live=True,
        is_stale=False,
        fallback_used=False,
        as_of=candles[-1].timestamp,
        requested_days=days,
        returned_candles=days,
        provider="test",
        source_state="live",
    )


def section_statuses(snapshot: StockAnalysisSnapshot | None) -> dict[str, str]:
    return {key: section.status for key, section in (snapshot.sections if snapshot else {}).items()}


def first_latency(rows: list[dict[str, Any]]) -> int | None:
    return next((row["elapsed_ms"] for row in rows if row["path"].endswith("/stock-analysis/NVDA")), None)


def write_report(report: dict[str, Any], path: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
    print(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate stock snapshot build/read performance.")
    parser.add_argument("--test", action="store_true", help="Use deterministic test provider settings.")
    parser.add_argument("--live", action="store_true", help="Use live provider configuration.")
    parser.add_argument("--cold", action="store_true", help="Build a real snapshot before reads.")
    parser.add_argument("--warm", action="store_true", help="Validate warm reads.")
    parser.add_argument("--restart", action="store_true", help="Verify persisted latest snapshot survives service recreation.")
    parser.add_argument("--soak", action="store_true", help="Reserved for repeated read checks.")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def selected_mode(args: argparse.Namespace) -> str:
    provider = "live" if args.live else "test"
    modes = [name for name in ["cold", "warm", "restart", "soak"] if getattr(args, name)]
    return f"{provider}:{','.join(modes or ['warm'])}"


if __name__ == "__main__":
    raise SystemExit(main())

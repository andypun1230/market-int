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

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from app.snapshots.models import InputCoverage, MarketSnapshot, SnapshotSection, now_iso  # noqa: E402
from app.snapshots.readers import fallback_decision, fallback_health  # noqa: E402
from app.snapshots.service import get_market_snapshot_service, reset_market_snapshot_service  # noqa: E402
from app.services.market_data_repository import reset_market_data_repository  # noqa: E402
from app.services.service_cache import invalidate_service_cache  # noqa: E402


CORE_INDEXES = ("SPY", "QQQ", "IWM", "DIA")
ALIASES = {"SPX": "SPY", "NDX": "QQQ", "IXIC": "QQQ", "RUT": "IWM", "DJI": "DIA", "QQQEW": "QQEW"}


def main() -> int:
    args = parse_args()
    configure(args)
    report: dict[str, Any] = {"mode": args.mode, "failures": []}
    reset_market_snapshot_service()
    reset_market_data_repository()
    invalidate_service_cache()

    tmp: tempfile.TemporaryDirectory[str] | None = None
    if args.mode == "test" and not os.getenv("MARKET_SNAPSHOT_DB_PATH"):
        tmp = tempfile.TemporaryDirectory()
        os.environ["MARKET_SNAPSHOT_DB_PATH"] = str(Path(tmp.name) / "phase-4-4a.sqlite3")
        reset_market_snapshot_service()
    try:
        if args.mode == "test":
            snapshot = publish_synthetic_snapshot()
            report["synthetic_snapshot_id"] = snapshot.snapshot_id
        with TestClient(app) as client:
            report["indexes"] = validate_indexes(client, report["failures"])
            report["aliases"] = validate_aliases(client, report["failures"])
            report["watchlist"] = validate_watchlist(client, report["failures"])
    finally:
        if tmp is not None:
            tmp.cleanup()

    write_report(report, args.json_output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["failures"] else 0


def configure(args: argparse.Namespace) -> None:
    os.environ.setdefault("MARKET_SNAPSHOT_STARTUP_REFRESH", "false")
    os.environ.setdefault("BACKGROUND_REFRESH_ENABLED", "false")
    if args.mode == "test":
        os.environ["DATA_PROVIDER"] = "test"
        os.environ["MARKET_DATA_PROVIDER"] = "test"
    if args.mode == "live":
        os.environ["DATA_PROVIDER"] = "live"
        os.environ["QUOTE_DATA_PROVIDER"] = os.getenv("QUOTE_DATA_PROVIDER", "finnhub")
        os.environ["HISTORY_DATA_PROVIDER"] = os.getenv("HISTORY_DATA_PROVIDER", "polygon")
        os.environ["MARKET_DATA_ALLOW_MOCK_FALLBACK"] = os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "false")


def validate_indexes(client: TestClient, failures: list[str]) -> dict[str, Any]:
    home = timed_get(client, "/home/dashboard")
    core = timed_get(client, "/market/core-snapshot")
    indexes = timed_get(client, "/market/indexes")
    home_indexes = by_symbol(((home["payload"].get("core") or {}).get("indexes") or []))
    core_indexes = by_symbol(core["payload"].get("indexes") or [])
    market_indexes = by_symbol(indexes["payload"].get("indexes") or [])
    mismatches: list[str] = []
    for symbol in CORE_INDEXES:
        if symbol not in home_indexes or symbol not in core_indexes or symbol not in market_indexes:
            mismatches.append(f"{symbol}:missing")
            continue
        home_value = home_indexes[symbol].get("change_percent")
        market_value = market_indexes[symbol].get("change_percent")
        if home_value != market_value:
            mismatches.append(f"{symbol}:change_percent")
        if home_indexes[symbol].get("quote_provider") != market_indexes[symbol].get("quote_provider"):
            mismatches.append(f"{symbol}:quote_provider")
    snapshot_ids = {home["payload"].get("snapshot_id"), core["payload"].get("snapshot_id")}
    if len(snapshot_ids - {None}) > 1:
        mismatches.append("snapshot_id")
    if mismatches:
        failures.append("index_consistency")
    return {
        "latency": {row["path"]: row["elapsed_ms"] for row in [home, core, indexes]},
        "snapshot_ids": sorted(value for value in snapshot_ids if value),
        "symbols": sorted(market_indexes),
        "mismatches": mismatches,
    }


def validate_aliases(client: TestClient, failures: list[str]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for alias, expected in ALIASES.items():
        response = timed_get(client, f"/market/live/history/{alias}?resolution=D&days=20")
        payload = response["payload"]
        rows[alias] = {
            "status_code": response["status_code"],
            "requested_symbol": payload.get("requested_symbol"),
            "provider_symbol": payload.get("provider_symbol"),
            "symbol": payload.get("symbol"),
            "elapsed_ms": response["elapsed_ms"],
        }
        if response["status_code"] >= 500 or payload.get("provider_symbol") != expected or payload.get("symbol") != expected:
            failures.append(f"alias:{alias}")
    return rows


def validate_watchlist(client: TestClient, failures: list[str]) -> dict[str, Any]:
    first = timed_get(client, "/watchlist/summary")
    with (
        patch("app.services.market_data_repository.MarketDataRepository._fetch_quote", side_effect=AssertionError("warm watchlist fetched quote")),
        patch("app.services.market_data_repository.MarketDataRepository._fetch_history", side_effect=AssertionError("watchlist fetched history")),
    ):
        warm = timed_get(client, "/watchlist/summary")
    payload = warm["payload"]
    if warm["status_code"] != 200:
        failures.append("watchlist_http")
    if warm["elapsed_ms"] > 800:
        failures.append("watchlist_latency")
    if not payload.get("membership_hash") or not isinstance(payload.get("items"), list):
        failures.append("watchlist_contract")
    return {
        "first_elapsed_ms": first["elapsed_ms"],
        "warm_elapsed_ms": warm["elapsed_ms"],
        "membership_hash": payload.get("membership_hash"),
        "status": payload.get("status"),
        "coverage_ratio": payload.get("coverage_ratio"),
        "symbols_unavailable": payload.get("symbols_unavailable"),
    }


def timed_get(client: TestClient, path: str) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.get(path)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
    return {"path": path, "status_code": response.status_code, "elapsed_ms": elapsed_ms, "payload": payload}


def by_symbol(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("symbol") or item.get("display_symbol")): item for item in items if isinstance(item, dict)}


def publish_synthetic_snapshot() -> MarketSnapshot:
    now = datetime.now(timezone.utc)
    indexes = [synthetic_index(symbol, index, now.isoformat()) for index, symbol in enumerate(CORE_INDEXES)]
    decision = fallback_decision()
    core = {
        "indexes": indexes,
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
        "indexes": section(indexes),
        "core": section(core),
        "home": section({
            "core": core,
            "risk_summary": {"score": 50, "status": "Moderate", "top_contributors": [], "summary": "Synthetic risk."},
            "watchlist_summary": {"items": []},
            "bootstrap": False,
            "refreshing": False,
            "cache_status": "snapshot",
            "is_stale": False,
        }),
    }
    snapshot = MarketSnapshot(
        snapshot_id=f"phase-4-4a-{int(time.time())}",
        status="complete",
        created_at=now.isoformat(),
        published_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=10)).isoformat(),
        stale_until=(now + timedelta(hours=1)).isoformat(),
        build_started_at=now.isoformat(),
        build_completed_at=now.isoformat(),
        build_duration_ms=0,
        input_coverage=InputCoverage(required_requested=4, required_available=4, optional_requested=0, optional_available=0, coverage_ratio=1.0),
        source_summary={"source_state": "test", "input_hash": "phase-4-4a"},
        sections=sections,
    )
    get_market_snapshot_service().storage.publish_snapshot(snapshot)
    return snapshot


def synthetic_index(symbol: str, offset: int, timestamp: str) -> dict[str, Any]:
    price = 100.0 + offset
    previous = 99.0 + offset
    return {
        "symbol": symbol,
        "display_symbol": symbol,
        "provider_symbol": symbol,
        "display_name": {"SPY": "S&P 500", "QQQ": "Nasdaq-100", "IWM": "Russell 2000", "DIA": "Dow Jones"}[symbol],
        "price": price,
        "change": price - previous,
        "change_percent": ((price - previous) / previous) * 100,
        "previous_close": previous,
        "volume": 1000,
        "ema_20": price - 1,
        "ema_50": price - 2,
        "ema_200": price - 3,
        "sma_50": price - 2,
        "rsi_14": 55.0,
        "quote_timestamp": timestamp,
        "history_latest_date": timestamp,
        "quote_provider": "finnhub",
        "history_provider": "polygon",
        "source_state": "live",
        "stale": False,
        "data_source": "quote:finnhub;history:polygon",
        "is_live": True,
        "is_stale": False,
        "fallback_used": False,
        "as_of": timestamp,
    }


def section(payload: Any) -> SnapshotSection:
    return SnapshotSection(
        status="complete",
        calculated_at=now_iso(),
        source_state="live",
        coverage_ratio=1.0,
        dependencies_requested=1,
        dependencies_available=1,
        payload=payload,
    )


def write_report(report: dict[str, Any], path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.4A index/watchlist consistency.")
    parser.add_argument("--mode", choices=("test", "live"), default="test")
    parser.add_argument("--test", action="store_const", const="test", dest="mode")
    parser.add_argument("--live", action="store_const", const="live", dest="mode")
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())

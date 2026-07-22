#!/usr/bin/env python3
"""Focused runtime gate for the remaining Phase 4.4C Rotation and Watchlist blockers."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.providers.selector import get_provider_status
from app.sector_snapshots.service import get_sector_snapshot_service, reset_sector_snapshot_service
from app.services.ai_context import build_market_ai_context, build_stock_ai_context
from app.services.analysis import build_market_analysis
from app.services.market_data_repository import get_market_data_repository
from app.services.report import build_daily_report
from app.services.theme_intelligence import build_theme_intelligence_context
from app.services.theme_provenance import is_live_theme_intelligence
from app.stock_snapshots.service import get_stock_snapshot_service, reset_stock_snapshot_service


PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
MANUAL = "MANUAL REQUIRED"
CANONICAL_SECTOR_COUNT = 11
ROTATION_INTERVALS = ("1W", "1M", "3M")
WATCHLIST_SYMBOLS = ("AAPL", "MSFT")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.4C runtime blockers")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--copilot-context", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def add(matrix: dict[str, Any], key: str, passed: bool, details: Any, remediation: str) -> None:
    matrix[key] = {"status": PASS if passed else FAIL, "details": details, "remediation": remediation}


def get_json(client: TestClient, path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    response = client.get(path)
    payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
    return payload if isinstance(payload, dict) else {}, {
        "path": path,
        "status": response.status_code,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def rotation_details(payload: dict[str, Any], interval: str) -> dict[str, Any]:
    series = [item for item in payload.get("series", []) if item.get("interval") == interval]
    current = [item for item in series if isinstance(item.get("current_point"), dict)]
    trails = [point for item in series for point in item.get("trail_points", []) if isinstance(point, dict)]
    valid = (
        len({item.get("entity_id") for item in series}) == CANONICAL_SECTOR_COUNT
        and len(current) == CANONICAL_SECTOR_COUNT
        and all(item["current_point"] == (item.get("trail_points") or [None])[-1] for item in current)
        and all(not point.get("is_synthetic") and point.get("source_provider") == "polygon" for point in trails)
        and all(
            [point.get("market_date") for point in item.get("trail_points", [])]
            == sorted(point.get("market_date") for point in item.get("trail_points", []))
            for item in series
        )
        and all(len({point.get("market_date") for point in item.get("trail_points", [])}) == len(item.get("trail_points", [])) for item in series)
    )
    return {
        "valid": valid,
        "snapshot_id": payload.get("snapshot_id"),
        "market_date": payload.get("market_date"),
        "interval": interval,
        "sector_count": len({item.get("entity_id") for item in series}),
        "current_point_count": len(current),
        "trail_point_count": len(trails),
        "source_state": payload.get("source_state"),
        "formula_version": payload.get("formula_version"),
        "normalization_version": payload.get("normalization_version"),
        "current_positions_available": payload.get("current_positions_available"),
        "etf_trails_available": payload.get("etf_trails_available"),
        "snapshot_transition_history_available": payload.get("snapshot_transition_history_available"),
        "transition_snapshot_count": payload.get("transition_snapshot_count"),
        "limited_history_reason": payload.get("limited_history_reason"),
        "warnings": payload.get("warnings"),
    }


def audit_rotation(matrix: dict[str, Any], client: TestClient, endpoints: dict[str, Any]) -> dict[str, Any]:
    interval_details: dict[str, Any] = {}
    for interval in ROTATION_INTERVALS:
        payload, endpoint = get_json(client, f"/market/sectors/rotation?interval={interval.lower()}")
        detail = rotation_details(payload, interval)
        endpoints[endpoint["path"]] = endpoint
        interval_details[interval] = detail
        add(
            matrix,
            f"rotation_{interval.lower()}_renderable",
            endpoint["status"] == 200 and detail["valid"] and detail["current_positions_available"] is True,
            detail,
            "Current canonical points must remain independent from snapshot-transition alert history.",
        )
    shallow_ok = all(
        detail["current_positions_available"] and detail["valid"]
        for detail in interval_details.values()
    ) and not any(detail["snapshot_transition_history_available"] for detail in interval_details.values())
    add(
        matrix,
        "rotation_shallow_transition_history_is_non_blocking",
        shallow_ok,
        interval_details,
        "Do not use transition-history depth as a chart availability gate.",
    )
    return interval_details


def audit_watchlist(matrix: dict[str, Any], client: TestClient, endpoints: dict[str, Any]) -> dict[str, Any]:
    summary, endpoint = get_json(client, "/watchlist/summary?symbols=AAPL,MSFT")
    endpoints[endpoint["path"]] = endpoint
    items = {item.get("symbol") or item.get("ticker"): item for item in summary.get("items", []) if isinstance(item, dict)}
    initial_pending_symbols = [
        symbol
        for symbol in WATCHLIST_SYMBOLS
        if items.get(symbol, {}).get("overall_status") == "pending" and items.get(symbol, {}).get("refreshing") is True
    ]
    if initial_pending_symbols:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and any(get_stock_snapshot_service().is_refreshing(symbol) for symbol in initial_pending_symbols):
            time.sleep(0.05)
        summary, endpoint = get_json(client, "/watchlist/summary?symbols=AAPL,MSFT")
        endpoints[endpoint["path"]] = endpoint
        items = {item.get("symbol") or item.get("ticker"): item for item in summary.get("items", []) if isinstance(item, dict)}
    details: dict[str, Any] = {
        "summary_snapshot_id": summary.get("snapshot_id"),
        "summary_status": summary.get("status"),
        "initial_pending_symbols": initial_pending_symbols,
        "symbols": {},
    }
    all_valid = endpoint["status"] == 200
    for symbol in WATCHLIST_SYMBOLS:
        analysis, analysis_endpoint = get_json(client, f"/market/stock-analysis/{symbol}")
        snapshot, snapshot_endpoint = get_json(client, f"/market/stock-snapshot/{symbol}")
        endpoints[analysis_endpoint["path"]] = analysis_endpoint
        endpoints[snapshot_endpoint["path"]] = snapshot_endpoint
        item = items.get(symbol, {})
        snapshot_id = item.get("analysis_snapshot_id")
        compatible_id = snapshot_id == analysis.get("snapshot_id") and (
            snapshot.get("snapshot_id") in {None, snapshot_id} or snapshot.get("snapshot", {}).get("snapshot_id") == snapshot_id
        )
        useful = bool(item.get("quote_price") is not None or item.get("price") is not None or item.get("available_fields"))
        state_ok = item.get("overall_status") != "unavailable" if useful else item.get("status_reason_code") is not None
        reason_ok = bool(item.get("status_reason_code")) or item.get("overall_status") == "complete"
        details["symbols"][symbol] = {
            "watchlist_status": item.get("overall_status"),
            "reason_code": item.get("status_reason_code"),
            "reason": item.get("status_reason"),
            "quote_price": item.get("quote_price"),
            "quote_source": item.get("quote_source"),
            "analysis_snapshot_id": snapshot_id,
            "analysis_status": item.get("analysis_status"),
            "available_fields": item.get("available_fields"),
            "missing_fields": item.get("missing_fields"),
            "refreshing": item.get("refreshing"),
            "stock_analysis_snapshot_id": analysis.get("snapshot_id"),
            "stock_snapshot_id": snapshot.get("snapshot_id"),
            "compatible_snapshot_id": compatible_id,
        }
        all_valid = all_valid and bool(item) and compatible_id and state_ok and reason_ok
    add(
        matrix,
        "watchlist_canonical_snapshot_evaluation",
        all_valid,
        details,
        "Watchlist rows must retain quotes and use the same compatible StockAnalysisSnapshot as Stock Detail.",
    )
    return details


def audit_themes(matrix: dict[str, Any]) -> None:
    industry = build_market_analysis().get("industry_groups") or {}
    static_provenance = industry.get("theme_provenance") or {}
    static_items = industry.get("items") or []
    live = build_theme_intelligence_context()
    live_items = live.get("items") or []

    # Industry-group preferences remain a separately labelled static surface.
    # A reviewed ThemeSnapshot may now coexist beside it for the approved pilot,
    # but it must never be silently represented as one of those static items.
    static_boundary_ok = (
        not is_live_theme_intelligence(static_provenance)
        and all(
            not is_live_theme_intelligence(item.get("provenance"))
            for item in static_items
            if isinstance(item, dict)
        )
    )
    if live.get("available"):
        live_boundary_ok = (
            live.get("source_state") == "live"
            and bool(live.get("snapshot_id"))
            and bool(live_items)
            and all(
                ((item.get("provenance") or {}).get("source_state") == "live")
                for item in live_items
                if isinstance(item, dict)
            )
        )
    else:
        live_boundary_ok = True
    add(
        matrix,
        "theme_intelligence_boundary",
        static_boundary_ok and live_boundary_ok,
        {
            "static_provenance": static_provenance,
            "static_item_count": len(static_items),
            "live_theme": {
                "available": live.get("available"),
                "snapshot_id": live.get("snapshot_id"),
                "source_state": live.get("source_state"),
                "item_count": len(live_items),
            },
        },
        "Keep static strategy preferences separately labelled; allow only a published, reviewed live ThemeSnapshot alongside them.",
    )


def audit_report_and_copilot(matrix: dict[str, Any], client: TestClient, endpoints: dict[str, Any], *, include_report: bool, include_copilot: bool, watchlist: dict[str, Any]) -> None:
    if include_report:
        market_snapshot, market_endpoint = get_json(client, "/market/snapshot/latest")
        breadth, breadth_endpoint = get_json(client, "/market/breadth")
        sector_snapshot, sector_endpoint = get_json(client, "/market/sectors/snapshot/latest")
        theme_snapshot, theme_endpoint = get_json(client, "/market/themes/snapshot/latest")
        endpoints[market_endpoint["path"]] = market_endpoint
        endpoints[breadth_endpoint["path"]] = breadth_endpoint
        endpoints[sector_endpoint["path"]] = sector_endpoint
        endpoints[theme_endpoint["path"]] = theme_endpoint
        pre_report_canonical_ids = {
            "market": market_snapshot.get("snapshot_id"),
            "breadth": (breadth.get("market") or {}).get("snapshot_id"),
            "sector": sector_snapshot.get("snapshot_id"),
            "theme": theme_snapshot.get("snapshot_id"),
        }
        payload, endpoint = get_json(client, "/report/daily")
        endpoints[endpoint["path"]] = endpoint
        report = build_daily_report()
        market_snapshot, market_endpoint = get_json(client, "/market/snapshot/latest")
        breadth, breadth_endpoint = get_json(client, "/market/breadth")
        sector_snapshot, sector_endpoint = get_json(client, "/market/sectors/snapshot/latest")
        theme_snapshot, theme_endpoint = get_json(client, "/market/themes/snapshot/latest")
        endpoints[market_endpoint["path"]] = market_endpoint
        endpoints[breadth_endpoint["path"]] = breadth_endpoint
        endpoints[sector_endpoint["path"]] = sector_endpoint
        endpoints[theme_endpoint["path"]] = theme_endpoint
        endpoint_snapshot_ids = (payload.get("semantic_context") or {}).get("snapshot_ids") or {}
        snapshot_ids = report.semantic_context.get("snapshot_ids", {}) if report.semantic_context else {}
        canonical_ids = {
            "market": market_snapshot.get("snapshot_id"),
            "breadth": (breadth.get("market") or {}).get("snapshot_id"),
            "sector": sector_snapshot.get("snapshot_id"),
            "theme": theme_snapshot.get("snapshot_id"),
        }
        ok = endpoint["status"] == 200 and endpoint_snapshot_ids == canonical_ids and all(snapshot_ids.get(key) for key in ("market", "breadth", "sector"))
        add(matrix, "report_snapshot_consistency", ok, {"http_report_id": payload.get("report_id"), "report_id": report.report_id, "pre_report_canonical_ids": pre_report_canonical_ids, "endpoint_snapshot_ids": endpoint_snapshot_ids, "canonical_ids": canonical_ids, "rebuilt_snapshot_ids": snapshot_ids}, "Build the report from the canonical Market, Breadth, Sector, and published Theme snapshots.")
    if include_copilot:
        first_market = build_market_ai_context(build_market_analysis())
        second_market = build_market_ai_context(build_market_analysis())
        stock_contexts = {symbol: build_stock_ai_context(symbol) for symbol in WATCHLIST_SYMBOLS}
        ok = first_market == second_market and all(context.get("symbol") == symbol for symbol, context in stock_contexts.items())
        add(matrix, "copilot_context_consistency", ok, {"market_theme": first_market.get("industry_groups"), "watchlist": watchlist.get("symbols"), "stocks": stock_contexts}, "Copilot context must retain canonical Watchlist states and static-theme provenance.")


def audit_warm(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        return
    from main import app

    routes = ("/home/dashboard", "/watchlist/summary?symbols=AAPL,MSFT", "/market/stock-analysis/AAPL", "/market/stock-analysis/MSFT", "/market/sectors/rotation?interval=1w", "/market/sectors/rotation?interval=1m", "/market/sectors/rotation?interval=3m", "/report/daily")
    results: dict[str, Any] = {}
    with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm navigation called Polygon history")) as polygon:
        for route in routes:
            _payload, endpoint = get_json(client, route)
            results[route] = endpoint
    ok = polygon.call_count == 0 and all(item["status"] == 200 for item in results.values())
    add(matrix, "warm_navigation_provider_isolation", ok, {"polygon_history_calls": polygon.call_count, "routes": results}, "Warm navigation must not trigger Polygon history calls or snapshot rebuilding.")


def audit_restart(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        return
    before = {
        "sector": getattr(get_sector_snapshot_service().latest(), "snapshot_id", None),
        "aapl": getattr(get_stock_snapshot_service().get_latest_snapshot("AAPL"), "snapshot_id", None),
        "msft": getattr(get_stock_snapshot_service().get_latest_snapshot("MSFT"), "snapshot_id", None),
    }
    reset_sector_snapshot_service()
    reset_stock_snapshot_service()
    after = {
        "sector": getattr(get_sector_snapshot_service().latest(), "snapshot_id", None),
        "aapl": getattr(get_stock_snapshot_service().get_latest_snapshot("AAPL"), "snapshot_id", None),
        "msft": getattr(get_stock_snapshot_service().get_latest_snapshot("MSFT"), "snapshot_id", None),
    }
    add(matrix, "restart_persistence", before == after and all(before.values()), {"before": before, "after": after}, "Latest durable rotation and stock snapshots must survive service reinitialization unchanged.")


def audit_regressions(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        return
    commands = [
        [sys.executable, "-m", "unittest", "tests.test_sector_snapshot", "tests.test_watchlist_evaluation", "tests.test_request_stability"],
        ["npx", "tsx", "tests/sectorSnapshot.test.ts"],
        ["npx", "tsx", "tests/watchlistPhase2.test.ts"],
    ]
    outputs = []
    ok = True
    for command in commands:
        result = subprocess.run(command, cwd=BACKEND_ROOT if command[0] == sys.executable else REPO_ROOT / "frontend", capture_output=True, text=True)
        ok = ok and result.returncode == 0
        outputs.append({"command": " ".join(command), "returncode": result.returncode, "output": (result.stdout + result.stderr)[-2000:]})
    add(matrix, "blocker_regressions", ok, outputs, "Keep canonical rotation availability and Watchlist evaluation regressions green.")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = ["# Phase 4.4C Blocker Runtime Proof", "", f"Overall result: **{report['overall_result']}**", "", "| Check | Status |", "| --- | --- |"]
    lines.extend(f"| {name.replace('_', ' ')} | {value['status']} |" for name, value in report["matrix"].items())
    lines.extend(["", "## Conditions", "", *[f"- {condition}" for condition in report["conditions"]]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    from main import app

    report: dict[str, Any] = {"phase": "4.4c-blockers", "matrix": {}, "endpoints": {}, "conditions": ["Native simulator gesture/layout validation remains manual."], "provider_status": get_provider_status()}
    with TestClient(app) as client:
        rotation = audit_rotation(report["matrix"], client, report["endpoints"])
        watchlist = audit_watchlist(report["matrix"], client, report["endpoints"])
        audit_themes(report["matrix"])
        audit_report_and_copilot(report["matrix"], client, report["endpoints"], include_report=args.report, include_copilot=args.copilot_context, watchlist=watchlist)
    audit_warm(report["matrix"], args.warm)
    audit_restart(report["matrix"], args.restart)
    audit_regressions(report["matrix"], args.test)
    report["rotation"] = rotation
    report["watchlist"] = watchlist
    report["provider_calls"] = get_market_data_repository().get_cache_status().get("repository_metrics", {})
    report["http_500_count"] = sum(1 for item in report["endpoints"].values() if item["status"] == 500)
    report["unexpected_http_503_count"] = sum(1 for item in report["endpoints"].values() if item["status"] == 503)
    failures = [name for name, value in report["matrix"].items() if value["status"] == FAIL]
    report["failed_checks"] = failures
    report["overall_result"] = "FAIL" if failures else "PASS WITH CONDITIONS"
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    if args.markdown_output:
        write_markdown(report, args.markdown_output)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

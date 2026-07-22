#!/usr/bin/env python3
"""Phase 4.4D Theme Intelligence architecture and rollout gate validator.

The test path uses a temporary database and explicitly test-only reviewed
definitions. It never imports a proposed definition package or calls a market
provider. The live path is intentionally a review gate: without reviewed,
active definitions it records a condition rather than publishing a theme.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.market_history.storage import DailyBar, DailyBarStorage
from app.theme_snapshots.builder import ThemeSnapshotBuilder
from app.theme_snapshots.readers import rotation_payload
from app.theme_snapshots.service import get_theme_snapshot_service, reset_theme_snapshot_service
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.models import ThemeDefinition, ThemeMember
from app.themes.storage import ThemeStorage
from app.services.background_refresh import reset_background_refresh_state
from app.securities.service import reset_security_master_service


PILOT_MEMBERS = {
    "memory_storage": ("MU", "SNDK", "WDC", "STX", "MRVL", "NTAP", "P"),
    "cybersecurity": ("CRWD", "PANW", "FTNT", "ZS", "OKTA", "CHKP", "S"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.4D Theme Intelligence")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--copilot-context", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def test_definition(theme_id: str, display_name: str, members: tuple[str, ...], secondary: str) -> tuple[ThemeDefinition, list[ThemeMember]]:
    definition = ThemeDefinition(
        theme_id=theme_id, display_name=display_name, description="Test-only reviewed definition used by the architecture validator.",
        version="validator-v1", status="active", effective_from="2025-01-01", methodology="equal weight current basket",
        inclusion_criteria="test-only", exclusion_criteria="test-only", weighting_policy="equal_weight_v1",
        primary_benchmark="SPY", secondary_benchmark=secondary, parent_sector_ids=("information_technology",), minimum_members=4,
        complete_coverage_threshold=.9, partial_coverage_threshold=.75,
        source_references=({"title": "test-only validator", "url": "https://example.test/phase-4.4d", "retrieved_at": "2025-01-01"},),
        verification_date="2025-01-01", reviewed_at="2025-01-01", reviewed_by="test-only-human-reviewer",
        notes="Never import this definition into a live database.",
    )
    return definition, [
        ThemeMember(theme_id=theme_id, theme_version="validator-v1", ticker=ticker, security_id=f"validator-{ticker}", company_name=ticker,
                    role="core", weight=round(1 / len(members), 8), effective_from="2025-01-01", active=True,
                    membership_source="validator-test-only", inclusion_reason="Test-only reviewed constituent.", reviewed_at="2025-01-01", reviewed_by="test-only-human-reviewer")
        for ticker in members
    ]


def daily_bars(ticker: str, start: float, slope: float, sessions: int = 310) -> list[DailyBar]:
    first = date(2025, 1, 2)
    result: list[DailyBar] = []
    for offset in range(sessions):
        close = max(1.0, start + slope * offset)
        session = (first + timedelta(days=offset)).isoformat()
        result.append(DailyBar(ticker=ticker, provider="polygon", session_date=session, timestamp=f"{session}T00:00:00+00:00", open=close, high=close, low=close, close=close, volume=1000, adjusted=True))
    return result


def add(checks: dict[str, Any], name: str, passed: bool, **evidence: Any) -> None:
    checks[name] = {"passed": passed, **evidence}


def run_test_path(args: argparse.Namespace, checks: dict[str, Any]) -> None:
    original = {key: os.environ.get(key) for key in ("BREADTH_DB_PATH", "DATA_PROVIDER", "HISTORY_DATA_PROVIDER", "BACKGROUND_REFRESH_ENABLED", "STARTUP_REFRESH_MODE")}
    db_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="phase-4-4d-") as directory:
        db_path = Path(directory) / "theme-validator.sqlite3"
        try:
            os.environ.update({"BREADTH_DB_PATH": str(db_path), "DATA_PROVIDER": "test", "HISTORY_DATA_PROVIDER": "polygon", "BACKGROUND_REFRESH_ENABLED": "false", "STARTUP_REFRESH_MODE": "none"})
            reset_theme_snapshot_service(); reset_security_master_service(); reset_background_refresh_state()
            theme_storage, bar_storage, snapshot_storage = ThemeStorage(db_path), DailyBarStorage(db_path), ThemeSnapshotStorage(db_path)
            memory, memory_members = test_definition("memory_storage", "Memory & Storage", ("MEM1", "MEM2", "MEM3", "MEM4"), "XLK")
            cyber, cyber_members = test_definition("cybersecurity", "Cybersecurity", ("CYB1", "CYB2", "CYB3", "CYB4"), "CIBR")
            theme_storage.save_definition(memory, memory_members); theme_storage.save_definition(cyber, cyber_members)
            durable = daily_bars("SPY", 400, .4)
            for index, ticker in enumerate([member.ticker for member in memory_members + cyber_members]):
                durable.extend(daily_bars(ticker, 75 + index * 5, .25 + index * .08))
            inserted, updated = bar_storage.upsert(durable)
            snapshot = ThemeSnapshotBuilder(theme_storage=theme_storage, snapshot_storage=snapshot_storage, bars=bar_storage).build()
            rows = list(snapshot.rows) if snapshot else []
            add(checks, "reviewed_definition_gate", snapshot is not None and len(rows) == 2, snapshot_id=snapshot.snapshot_id if snapshot else None, themes=[row.get("theme_id") for row in rows])
            add(checks, "durable_polygon_adjusted_bars", inserted == len(durable) and updated == 0, inserted=inserted, updated=updated, total=len(durable))
            basket_counts = {row.get("theme_id"): len(theme_storage.basket_history(row["theme_id"], row["version"])) for row in rows}
            add(checks, "equal_weight_baskets", all(count >= 250 for count in basket_counts.values()), basket_counts=basket_counts)
            rotations = {interval: rotation_payload(snapshot, interval) if snapshot else {} for interval in ("1W", "1M", "3M")}
            rotation_ok = all(payload.get("current_point_count") == 2 and payload.get("basket_trails_available") and all(series.get("current_point") == (series.get("trail_points") or [None])[-1] and not any(point.get("is_synthetic") for point in series.get("trail_points") or []) for series in payload.get("series", [])) for payload in rotations.values())
            add(checks, "rotation_real_basket_trails", rotation_ok, intervals={key: {"points": value.get("current_point_count"), "trail_points": value.get("trail_point_count")} for key, value in rotations.items()})
            overlap = list(snapshot.overlap_matrix) if snapshot else []
            add(checks, "overlap_disclosure", len(overlap) == 1 and overlap[0].get("shared_count") == 0, overlap=overlap)
            participation_ok = all(row.get("participation", {}).get("formula_version") == "positive-return-and-contribution-v1" and "distinct from EMA50 breadth" in row.get("participation", {}).get("definition", "") for row in rows)
            add(checks, "participation_is_not_breadth_alias", participation_ok, formulas=[row.get("participation", {}).get("formula_version") for row in rows])

            # Verify restart persistence with fresh service instances against the same durable DB.
            before = snapshot.snapshot_id if snapshot else None
            reset_theme_snapshot_service(); after = get_theme_snapshot_service().latest()
            add(checks, "restart_persistence", before is not None and after is not None and after.snapshot_id == before, before=before, after=after.snapshot_id if after else None)

            if args.warm:
                from fastapi.testclient import TestClient
                from main import app
                paths = ["/market/themes/snapshot/latest", "/market/themes", "/market/themes/rotation?interval=1m", "/market/themes/alerts", "/market/themes/overlap", "/market/themes/status"]
                responses: dict[str, Any] = {}
                with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm Theme read called Polygon")) as provider:
                    for path in paths:
                        started = perf_counter(); response = client.get(path)
                        responses[path] = {"status": response.status_code, "latency_ms": round((perf_counter() - started) * 1000, 2), "snapshot_id": response.json().get("snapshot_id")}
                warm_ok = provider.call_count == 0 and all(value["status"] == 200 and value["latency_ms"] < 750 for value in responses.values())
                add(checks, "warm_api_reads", warm_ok, provider_history_calls=provider.call_count, routes=responses)

            if args.report:
                from app.services.theme_intelligence import build_theme_intelligence_context
                context = build_theme_intelligence_context()
                add(checks, "report_adapter_contract", context.get("available") is False and context.get("reason") == "no_reviewed_theme_snapshot", context=context)
                # Test-only data is intentionally not eligible to be described as live report content.
            if args.copilot_context:
                from app.services.ai_context import build_market_ai_context
                context = build_market_ai_context({"theme_intelligence": {"available": False, "availability": "Live Theme Intelligence is not yet available.", "source_state": "unavailable", "leaders": [], "warnings": []}})
                add(checks, "copilot_theme_provenance", context.get("theme_intelligence", {}).get("available") is False, theme=context.get("theme_intelligence"))
        finally:
            reset_theme_snapshot_service(); reset_security_master_service(); reset_background_refresh_state()
            for key, value in original.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
    add(checks, "temporary_database_cleanup", db_path is not None and not db_path.exists(), db_path=str(db_path) if db_path else None)


def run_live_gate(args: argparse.Namespace, checks: dict[str, Any], conditions: list[str]) -> None:
    service = get_theme_snapshot_service()
    status = service.status()
    ready = bool(status.get("live_theme_intelligence"))
    add(checks, "live_review_gate", ready, status=status)
    if not ready:
        conditions.append("No reviewed active ThemeDefinition is present; live ThemeSnapshot, pilot seeding, and full rollout remain blocked pending human review.")
    if args.pilot or args.full:
        add(checks, "live_rollout_authorization", ready, requested="full" if args.full else "pilot")
        if not ready:
            conditions.append("Pilot/full live history seeding was intentionally not started because definitions are proposed, not active and reviewed.")
    snapshot = service.latest()
    if not ready or snapshot is None:
        return

    rows = {row.get("theme_id"): row for row in snapshot.rows}
    if args.pilot:
        membership = {theme_id: tuple(member.get("ticker") for member in rows.get(theme_id, {}).get("members", [])) for theme_id in PILOT_MEMBERS}
        coverage = {theme_id: snapshot.member_coverage.get(theme_id, {}) for theme_id in PILOT_MEMBERS}
        add(
            checks,
            "pilot_membership_contract",
            set(rows) == set(PILOT_MEMBERS)
            and all(set(membership[theme_id]) == set(expected) and len(membership[theme_id]) == len(expected) for theme_id, expected in PILOT_MEMBERS.items())
            and all("CYBR" not in values for values in membership.values()),
            membership=membership,
            active_theme_versions=list(snapshot.active_theme_versions),
        )
        add(
            checks,
            "pilot_live_coverage_and_provenance",
            snapshot.source_state == "live"
            and snapshot.status in {"complete", "partial"}
            and tuple(snapshot.providers) == ("polygon",)
            and all(value.get("coverage_ratio", 0) >= 0.75 and value.get("eligible_count") == 7 for value in coverage.values()),
            snapshot_id=snapshot.snapshot_id,
            source_state=snapshot.source_state,
            status=snapshot.status,
            providers=list(snapshot.providers),
            coverage=coverage,
        )
        p_history = DailyBarStorage().history("P")
        p_member = next((member for member in rows.get("memory_storage", {}).get("members", []) if member.get("ticker") == "P"), None)
        boundary = [bar for bar in p_history if bar.session_date in {"2026-04-16", "2026-04-17"}]
        add(
            checks,
            "pilot_pstg_p_continuity",
            p_member is not None
            and p_member.get("previous_ticker") == "PSTG"
            and p_member.get("continuity_status") == "verified"
            and len(p_history) == len({bar.session_date for bar in p_history})
            and [bar.source_symbol for bar in boundary] == ["PSTG", "P"],
            member=p_member,
            bar_count=len(p_history),
            boundary=[{"session": bar.session_date, "source_symbol": bar.source_symbol, "close": bar.close} for bar in boundary],
        )

    if args.restart:
        before = snapshot.snapshot_id
        reset_theme_snapshot_service()
        after = get_theme_snapshot_service().latest()
        add(checks, "live_restart_persistence", after is not None and after.snapshot_id == before, before=before, after=after.snapshot_id if after else None)

    if args.warm:
        from fastapi.testclient import TestClient
        from main import app
        paths = [
            "/market/themes/status", "/market/themes/snapshot/latest", "/market/themes",
            "/market/themes/memory_storage", "/market/themes/cybersecurity",
            "/market/themes/rotation?interval=1w", "/market/themes/rotation?interval=1m",
            "/market/themes/rotation?interval=3m", "/market/themes/alerts", "/market/themes/overlap",
            "/home/dashboard", "/market/core-snapshot", "/market/decision-dashboard", "/report/daily",
        ]
        responses: dict[str, Any] = {}
        original_market_snapshot_enabled = os.environ.get("MARKET_SNAPSHOT_ENABLED")
        os.environ["MARKET_SNAPSHOT_ENABLED"] = "false"
        try:
            with TestClient(app) as client:
                # Populate unrelated market caches before asserting the second read path.
                for path in paths:
                    client.get(path)
                with patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm read called Polygon")) as polygon, patch("app.providers.finnhub_provider.FinnhubMarketDataProvider.get_quote", side_effect=AssertionError("warm read called Finnhub")) as finnhub, patch("app.theme_snapshots.builder.ThemeSnapshotBuilder.build", side_effect=AssertionError("warm read rebuilt ThemeSnapshot")) as snapshot_build, patch("app.themes.basket.build_equal_weight_basket", side_effect=AssertionError("warm read rebuilt Theme basket")) as basket_build, patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol", side_effect=AssertionError("warm read seeded history")) as symbol_seed, patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol_history_segments", side_effect=AssertionError("warm read stitched history")) as stitch_seed:
                    for path in paths:
                        started = perf_counter(); response = client.get(path); payload = response.json()
                        responses[path] = {
                            "status": response.status_code,
                            "latency_ms": round((perf_counter() - started) * 1000, 2),
                            "theme_snapshot_id": theme_snapshot_id(payload),
                        }
        finally:
            if original_market_snapshot_enabled is None:
                os.environ.pop("MARKET_SNAPSHOT_ENABLED", None)
            else:
                os.environ["MARKET_SNAPSHOT_ENABLED"] = original_market_snapshot_enabled
        warm_ok = polygon.call_count == 0 and finnhub.call_count == 0 and snapshot_build.call_count == 0 and basket_build.call_count == 0 and symbol_seed.call_count == 0 and stitch_seed.call_count == 0 and all(
            row["status"] == 200 and row["latency_ms"] < 750 and row["theme_snapshot_id"] == snapshot.snapshot_id
            for row in responses.values()
        )
        add(checks, "live_warm_reads_and_consumer_identity", warm_ok, polygon_history_calls=polygon.call_count, finnhub_quote_calls=finnhub.call_count, theme_snapshot_builds=snapshot_build.call_count, basket_rebuilds=basket_build.call_count, history_seed_calls=symbol_seed.call_count, history_stitch_calls=stitch_seed.call_count, routes=responses)

    if args.report:
        from app.services.theme_intelligence import build_theme_intelligence_context
        context = build_theme_intelligence_context()
        add(checks, "live_report_theme_contract", context.get("available") and context.get("snapshot_id") == snapshot.snapshot_id, context=context)
    if args.copilot_context:
        from app.services.ai_context import build_market_ai_context
        context = build_market_ai_context({"theme_intelligence": {"available": True, "snapshot_id": snapshot.snapshot_id, "market_date": snapshot.market_date, "source_state": snapshot.source_state, "leaders": [], "warnings": []}})
        theme = context.get("theme_intelligence", {})
        add(checks, "live_copilot_theme_contract", theme.get("available") and theme.get("snapshot_id") == snapshot.snapshot_id, theme=theme)


def theme_snapshot_id(payload: dict[str, Any]) -> str | None:
    theme = payload.get("theme_intelligence")
    if isinstance(theme, dict):
        return theme.get("snapshot_id")
    core = payload.get("core")
    if isinstance(core, dict) and isinstance(core.get("theme_intelligence"), dict):
        return core["theme_intelligence"].get("snapshot_id")
    decision = payload.get("decision_dashboard")
    if isinstance(decision, dict) and isinstance(decision.get("theme_intelligence"), dict):
        return decision["theme_intelligence"].get("snapshot_id")
    return payload.get("snapshot_id")


def markdown_report(report: dict[str, Any]) -> str:
    lines = [f"# Phase 4.4D Validation", "", f"Status: **{report['status']}**", "", "## Checks"]
    for name, check in report["checks"].items():
        lines.append(f"- {'PASS' if check['passed'] else 'CONDITION'}: `{name}`")
    if report["conditions"]:
        lines.extend(["", "## Conditions", *[f"- {condition}" for condition in report["conditions"]]])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args(); checks: dict[str, Any] = {}; conditions: list[str] = []
    if not any((args.test, args.live, args.pilot, args.full)):
        args.test = True
    if args.test:
        run_test_path(args, checks)
    if args.live or args.pilot or args.full:
        run_live_gate(args, checks, conditions)
    excluded = {"live_review_gate", "live_rollout_authorization"} if not (args.pilot or args.full) else set()
    failed = [name for name, check in checks.items() if not check["passed"] and name not in excluded]
    status = "PILOT PASS" if args.pilot and not failed and not conditions else "ARCHITECTURE PASS" if not failed and not conditions else "ARCHITECTURE PASS WITH CONDITIONS" if not failed else "FAIL"
    report = {"phase": "4.4d", "status": status, "passed": not failed, "conditions": conditions, "checks": checks}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True); args.markdown_output.write_text(markdown_report(report))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

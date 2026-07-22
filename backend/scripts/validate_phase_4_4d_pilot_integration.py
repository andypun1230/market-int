#!/usr/bin/env python3
"""Read-only integration gate for the reviewed Phase 4.4D two-Theme pilot.

The live checks read the published immutable ThemeSnapshot. They never seed
history, refresh a snapshot, or call a market provider. The test path uses a
temporary SQLite database solely to prove current-version selection and
Decision qualification semantics.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_history.storage import DailyBarStorage
from app.securities.service import reset_security_master_service
from app.services.background_refresh import reset_background_refresh_state
from app.services.copilot_service import answer_copilot_chat
from app.services.theme_intelligence import decision_theme_signal, enrich_copilot_theme_context
from app.theme_snapshots.service import get_theme_snapshot_service, reset_theme_snapshot_service
from app.themes.models import ThemeDefinition, ThemeMember
from app.themes.service import ThemeDefinitionService
from app.themes.storage import ThemeStorage


MEMORY_APPROVED = {
    "MU": ("core", 100, 10), "SNDK": ("core", 100, 9),
    "WDC": ("core", 95, 8), "STX": ("core", 95, 8),
    "MRVL": ("infrastructure", 70, 6), "NTAP": ("infrastructure", 80, 5),
    "P": ("infrastructure", 90, 6),
}
CYBER_APPROVED = {
    "CRWD": ("core", 100), "PANW": ("core", 95), "FTNT": ("core", 95),
    "ZS": ("core", 100), "OKTA": ("core", 90), "CHKP": ("core", 95),
    "S": ("beneficiary", 90),
}
WARM_PATHS = (
    "/market/themes/status", "/market/themes/snapshot/latest", "/market/themes",
    "/market/themes/memory_storage", "/market/themes/cybersecurity",
    "/market/themes/rotation?interval=1w", "/market/themes/rotation?interval=1m",
    "/market/themes/rotation?interval=3m", "/market/themes/alerts", "/market/themes/overlap",
    "/home/dashboard", "/market/decision-dashboard", "/report/daily",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Phase 4.4D two-Theme pilot integration.")
    for flag in ("test", "live", "warm", "restart", "report", "copilot-context", "basket-audit"):
        parser.add_argument(f"--{flag}", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def add(checks: dict[str, Any], name: str, passed: bool, **evidence: Any) -> None:
    checks[name] = {"passed": bool(passed), **evidence}


def restore_environment(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_definition(version: str) -> ThemeDefinition:
    return ThemeDefinition(
        theme_id="memory_storage", display_name="Memory & Storage", description="Temporary validator definition.",
        version=version, status="active", effective_from="2026-01-01", methodology="reviewed current basket",
        inclusion_criteria="test", exclusion_criteria="test", weighting_policy="equal_weight_v1",
        primary_benchmark="SPY", secondary_benchmark="XLK", parent_sector_ids=("information_technology",),
        minimum_members=4, complete_coverage_threshold=.9, partial_coverage_threshold=.75,
        source_references=({"title": "test", "url": "https://example.test", "retrieved_at": "2026-01-01"},),
        verification_date="2026-01-01", reviewed_at="2026-01-01", reviewed_by="validator-human",
    )


def test_members(version: str) -> list[ThemeMember]:
    return [ThemeMember(
        theme_id="memory_storage", theme_version=version, ticker=ticker, security_id=f"test-{ticker}",
        company_name=ticker, role="core", weight=.25, effective_from="2026-01-01", active=True,
        membership_source="validator", inclusion_reason="Temporary validator member.", reviewed_at="2026-01-01",
        reviewed_by="validator-human",
    ) for ticker in ("AAA", "BBB", "CCC", "DDD")]


def run_test_path(checks: dict[str, Any]) -> None:
    keys = ("BREADTH_DB_PATH", "DATA_PROVIDER", "HISTORY_DATA_PROVIDER", "BACKGROUND_REFRESH_ENABLED", "STARTUP_REFRESH_MODE")
    previous = {key: os.environ.get(key) for key in keys}
    db_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="phase-4-4d-pilot-integration-") as directory:
        db_path = Path(directory) / "validator.sqlite3"
        try:
            os.environ.update({
                "BREADTH_DB_PATH": str(db_path), "DATA_PROVIDER": "test", "HISTORY_DATA_PROVIDER": "polygon",
                "BACKGROUND_REFRESH_ENABLED": "false", "STARTUP_REFRESH_MODE": "none",
            })
            reset_theme_snapshot_service(); reset_security_master_service(); reset_background_refresh_state()
            storage = ThemeStorage(db_path)
            storage.save_definition(test_definition("v1.1"), test_members("v1.1"))
            storage.save_definition(test_definition("v1.2"), test_members("v1.2"))
            active = ThemeDefinitionService(storage).active()
            add(checks, "test_current_definition_selection", len(active) == 1 and active[0][0].version == "v1.2", selected_versions=[item[0].version for item in active])

            snapshot = SimpleNamespace(snapshot_id="theme-test", status="complete")
            qualifying_row = {
                "theme_id": "cybersecurity", "display_name": "Cybersecurity", "coverage_ratio": 1.0,
                "composite_score": 100.0, "classification": "Leading",
                "signal_confidence": {"score": 90}, "data_confidence": {"score": 90},
                "concentration": {"classification": "moderate"},
            }
            nonqualifying = {**qualifying_row, "concentration": {"classification": "high"}}
            promoted = decision_theme_signal(snapshot, qualifying_row)
            rejected = decision_theme_signal(snapshot, nonqualifying)
            add(
                checks, "test_decision_live_provenance", promoted["source_type"] == "live_theme_signal" and promoted["qualified"]
                and rejected["source_type"] == "live_theme_signal" and not rejected["qualified"]
                and "high" in (rejected["disqualification_reason"] or ""),
                qualifying=promoted, nonqualifying=rejected,
            )
        finally:
            reset_theme_snapshot_service(); reset_security_master_service(); reset_background_refresh_state()
            restore_environment(previous)
    add(checks, "test_temporary_database_cleanup", db_path is not None and not db_path.exists(), db_path=str(db_path) if db_path else None)


def rows_by_id(snapshot: Any) -> dict[str, dict[str, Any]]:
    return {str(row.get("theme_id")): row for row in snapshot.rows}


def member_metadata(row: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
    return {str(member.get("ticker")): (member.get("role"), member.get("purity"), member.get("importance")) for member in row.get("members", [])}


def find_theme_snapshot_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    theme = payload.get("theme_intelligence")
    if isinstance(theme, dict) and isinstance(theme.get("snapshot_id"), str):
        return theme["snapshot_id"]
    if isinstance(payload.get("snapshot_id"), str) and str(payload.get("snapshot_id")).startswith("theme-"):
        return str(payload["snapshot_id"])
    for value in payload.values():
        if isinstance(value, dict):
            resolved = find_theme_snapshot_id(value)
            if resolved:
                return resolved
    return None


def live_contract(snapshot: Any, checks: dict[str, Any]) -> None:
    rows = rows_by_id(snapshot)
    active_versions = {item.get("theme_id"): item.get("version") for item in snapshot.active_theme_versions}
    add(
        checks, "live_theme_snapshot_provenance",
        snapshot.source_state == "live" and set(rows) == {"memory_storage", "cybersecurity"}
        and active_versions == {"memory_storage": "v1.2", "cybersecurity": "v1.2"},
        snapshot_id=snapshot.snapshot_id, market_date=snapshot.market_date, status=snapshot.status,
        source_state=snapshot.source_state, active_versions=active_versions,
    )
    memory = member_metadata(rows.get("memory_storage", {}))
    cyber = member_metadata(rows.get("cybersecurity", {}))
    memory_ok = memory == MEMORY_APPROVED
    cyber_ok = set(cyber) == set(CYBER_APPROVED) and all(cyber[ticker][:2] == expected and cyber[ticker][2] is None for ticker, expected in CYBER_APPROVED.items())
    p_member = next((member for member in rows.get("memory_storage", {}).get("members", []) if member.get("ticker") == "P"), {})
    add(checks, "approved_memory_member_metadata", memory_ok, actual=memory, expected=MEMORY_APPROVED)
    add(checks, "approved_cyber_member_metadata", cyber_ok, actual=cyber, expected=CYBER_APPROVED)
    add(
        checks, "pilot_membership_and_identity_contract",
        "CYBR" not in {*memory, *cyber} and "PSTG" not in {*memory, *cyber}
        and p_member.get("previous_ticker") == "PSTG" and p_member.get("continuity_status") == "verified",
        p_member=p_member, active_members=sorted([*memory, *cyber]),
    )
    metrics_ok = all(
        isinstance(row.get("participation"), dict)
        and {"positive_return_member_count", "negative_return_member_count", "positive_return_participation_pct", "positive_contribution_share_pct", "participation_horizon", "participation_score"} <= set(row["participation"])
        and isinstance(row.get("concentration"), dict)
        and {"top_one_absolute_contribution_share_pct", "top_three_absolute_contribution_share_pct", "concentration_hhi", "concentration_quality_score", "classification"} <= set(row["concentration"])
        for row in rows.values()
    )
    add(checks, "metric_units_are_explicit", metrics_ok, metrics={theme_id: {"participation": row.get("participation"), "concentration": row.get("concentration")} for theme_id, row in rows.items()})
    scores = {}
    scoring_ok = True
    for theme_id, row in rows.items():
        contributions = row.get("weighted_contributions", {})
        total = round(sum(float(value.get("weighted_contribution") or 0) for value in contributions.values()), 2)
        semantics = row.get("score_semantics", {})
        scores[theme_id] = {"displayed": row.get("composite_score"), "contribution_total": total, "semantics": semantics, "rank": row.get("rank")}
        scoring_ok = scoring_ok and total == row.get("composite_score") and semantics.get("score_type") == "absolute_weighted_composite"
    add(checks, "absolute_composite_score_semantics", scoring_ok and scores.get("cybersecurity", {}).get("displayed") == 100.0 and scores.get("cybersecurity", {}).get("contribution_total") == 100.0, scores=scores)
    scope = next(iter(rows.values())).get("pilot_scope", {}) if rows else {}
    add(checks, "pilot_rank_scope_disclosure", scope.get("active_reviewed_theme_count") == 2 and "2" in str(scope.get("rank_scope")), pilot_scope=scope)
    add(checks, "overlap_disclosure", len(snapshot.overlap_matrix) == 1 and snapshot.overlap_matrix[0].get("shared_count") == 0, overlap=list(snapshot.overlap_matrix))


def api_contract(snapshot: Any, checks: dict[str, Any], *, report: bool, warm: bool) -> None:
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        payloads: dict[str, Any] = {}
        endpoint_rows: dict[str, Any] = {}
        for path in WARM_PATHS:
            if path == "/report/daily" and not report and not warm:
                continue
            started = perf_counter()
            response = client.get(path)
            endpoint_rows[path] = {"status": response.status_code, "latency_ms": round((perf_counter() - started) * 1000, 2)}
            try:
                payloads[path] = response.json()
            except ValueError:
                payloads[path] = {}
        direct = payloads.get("/market/themes", {})
        direct_rows = direct.get("items", []) if isinstance(direct, dict) else []
        add(
            checks, "theme_api_current_snapshot_consistency",
            all(item.get("status") == 200 for item in endpoint_rows.values())
            and direct.get("snapshot_id") == snapshot.snapshot_id
            and len(direct_rows) == 2,
            routes=endpoint_rows, theme_snapshot_id=direct.get("snapshot_id"), item_count=len(direct_rows),
        )
        if report:
            report_payload = payloads.get("/report/daily", {})
            context = report_payload.get("theme_intelligence", {}) if isinstance(report_payload, dict) else {}
            items = context.get("items", []) if isinstance(context, dict) else []
            text_blob = json.dumps(report_payload, sort_keys=True)
            add(
                checks, "fresh_report_theme_snapshot_contract",
                endpoint_rows.get("/report/daily", {}).get("status") == 200
                and context.get("snapshot_id") == snapshot.snapshot_id and len(items) == 2
                and [item.get("theme_id") for item in items] == ["cybersecurity", "memory_storage"]
                and "Theme Intelligence unavailable" not in text_blob,
                snapshot_id=context.get("snapshot_id"), items=items, latency_ms=endpoint_rows.get("/report/daily", {}).get("latency_ms"),
            )
        decision = payloads.get("/market/decision-dashboard", {})
        intelligence = decision.get("theme_intelligence", {}) if isinstance(decision, dict) else {}
        signals = intelligence.get("decision_theme_signals", []) if isinstance(intelligence, dict) else []
        cyber = next((item for item in signals if item.get("theme_id") == "cybersecurity"), {})
        static = [item for item in signals if item.get("theme_id") == "cybersecurity" and item.get("source_type") == "static_strategy_preference"]
        add(
            checks, "decision_live_static_theme_provenance",
            cyber.get("source_type") == "live_theme_signal" and cyber.get("qualified") is True
            and cyber.get("theme_snapshot_id") == snapshot.snapshot_id and not static,
            cybersecurity_signal=cyber, duplicate_static_signals=static,
        )
        if warm:
            warm_contract(client, snapshot, checks)


def warm_contract(client: Any, snapshot: Any, checks: dict[str, Any]) -> None:
    # First pass fills only product caches. The asserted pass is fully patched
    # to make accidental provider or build work fail deterministically.
    for path in WARM_PATHS:
        client.get(path)
    routes: dict[str, Any] = {}
    with patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm read called Polygon")) as polygon, \
         patch("app.providers.finnhub_provider.FinnhubMarketDataProvider.get_quote", side_effect=AssertionError("warm read called Finnhub")) as finnhub, \
         patch("app.theme_snapshots.builder.ThemeSnapshotBuilder.build", side_effect=AssertionError("warm read rebuilt ThemeSnapshot")) as snapshot_build, \
         patch("app.themes.basket.build_equal_weight_basket", side_effect=AssertionError("warm read rebuilt Theme basket")) as basket_build, \
         patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol", side_effect=AssertionError("warm read seeded history")) as history_update, \
         patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol_history_segments", side_effect=AssertionError("warm read stitched history")) as history_stitch:
        for path in WARM_PATHS:
            started = perf_counter(); response = client.get(path)
            payload = response.json()
            routes[path] = {
                "status": response.status_code,
                "latency_ms": round((perf_counter() - started) * 1000, 2),
                "theme_snapshot_id": find_theme_snapshot_id(payload),
            }
    expected_paths = {"/market/themes/status", "/market/themes/snapshot/latest", "/market/themes", "/market/themes/memory_storage", "/market/themes/cybersecurity", "/market/themes/rotation?interval=1w", "/market/themes/rotation?interval=1m", "/market/themes/rotation?interval=3m", "/market/themes/alerts", "/market/themes/overlap"}
    consistent = all(routes[path]["theme_snapshot_id"] == snapshot.snapshot_id for path in expected_paths)
    calls = {
        "polygon_history_calls": polygon.call_count, "finnhub_quote_calls": finnhub.call_count,
        "theme_snapshot_builds": snapshot_build.call_count, "basket_rebuilds": basket_build.call_count,
        "history_update_calls": history_update.call_count, "history_stitch_calls": history_stitch.call_count,
    }
    add(
        checks, "warm_runtime_zero_work", all(value == 0 for value in calls.values())
        and all(row["status"] == 200 and row["latency_ms"] < 500 for row in routes.values()) and consistent,
        **calls, routes=routes,
    )


def copilot_contract(snapshot: Any, checks: dict[str, Any]) -> None:
    base = {"screenType": "general", "screenTitle": "Market Copilot", "routeName": "/ai", "sourceState": "live"}
    cyber_context = enrich_copilot_theme_context("Why is cybersecurity leading?", base)
    memory_context = enrich_copilot_theme_context("Explain Memory & Storage", base)
    cyber_focused = (cyber_context.get("theme") or {}).get("focused", {})
    memory_focused = (memory_context.get("theme") or {}).get("focused", {})
    with patch("app.services.copilot_service.generate_structured_chat_response", return_value=None):
        response = answer_copilot_chat("Why is cybersecurity leading?", base)
    answer = str(response.get("answer") or "")
    add(
        checks, "copilot_live_theme_grounding",
        cyber_focused.get("snapshot_id") == snapshot.snapshot_id and cyber_focused.get("theme_id") == "cybersecurity"
        and memory_focused.get("snapshot_id") == snapshot.snapshot_id and memory_focused.get("theme_id") == "memory_storage"
        and "Cybersecurity" in answer and "unavailable" not in answer.lower(),
        cyber_context=cyber_context.get("theme"), memory_context=memory_context.get("theme"), controlled_answer=response,
    )


def restart_contract(snapshot: Any, checks: dict[str, Any]) -> None:
    before = snapshot.snapshot_id
    reset_theme_snapshot_service()
    restored = get_theme_snapshot_service().latest()
    add(checks, "restart_persistence", restored is not None and restored.snapshot_id == before, before=before, after=restored.snapshot_id if restored else None)


def basket_contract(checks: dict[str, Any]) -> None:
    from audit_theme_basket_returns import audit_snapshot

    audit = audit_snapshot()
    add(
        checks, "basket_and_identity_forensic_audit", audit.get("status") == "PASS" and not audit.get("return_defect_found"),
        audit=audit,
    )


def snapshot_history_contract(snapshot: Any, checks: dict[str, Any]) -> None:
    history = get_theme_snapshot_service().history(260)
    old = [item for item in history if item.get("snapshot_id") == "theme-2026-07-17-82f25d1e5d"]
    add(
        checks, "immutable_snapshot_correction_history",
        snapshot.snapshot_id != "theme-2026-07-17-82f25d1e5d" and bool(old),
        latest=snapshot.snapshot_id, preserved_pre_correction=old,
    )


def markdown_report(report: dict[str, Any]) -> str:
    lines = ["# Phase 4.4D Pilot Integration", "", f"Status: **{report['status']}**", "", "## Checks"]
    for name, check in report["checks"].items():
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'}: `{name}`")
    if report["conditions"]:
        lines.extend(["", "## Conditions", *[f"- {condition}" for condition in report["conditions"]]])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if not any((args.test, args.live)):
        args.live = True
    checks: dict[str, Any] = {}
    conditions: list[str] = []
    if args.test:
        run_test_path(checks)
    if args.live:
        snapshot = get_theme_snapshot_service().latest()
        if snapshot is None:
            add(checks, "live_theme_snapshot_provenance", False, reason="no_published_theme_snapshot")
        else:
            live_contract(snapshot, checks)
            snapshot_history_contract(snapshot, checks)
            api_contract(snapshot, checks, report=args.report, warm=args.warm)
            if args.restart:
                restart_contract(snapshot, checks)
            if args.copilot_context:
                copilot_contract(snapshot, checks)
            if args.basket_audit:
                basket_contract(checks)
            conditions.extend([
                "Historical Theme returns use the current reviewed basket until historical membership versions are available.",
                "Ranks cover only the two active reviewed pilot themes; four proposed Themes remain inactive.",
                "Native Expo visual QA remains manual; this validator exercises the API and deterministic UI contracts.",
                "The controlled Copilot proof uses the deterministic rules renderer; external-model wording remains optional manual QA.",
            ])
    failed = [name for name, check in checks.items() if not check["passed"]]
    status = "FAIL" if failed else "PILOT INTEGRATION PASS WITH CONDITIONS" if conditions else "PILOT INTEGRATION PASS"
    report = {"status": status, "checks": checks, "conditions": conditions, "failed_checks": failed}
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown_report(report))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

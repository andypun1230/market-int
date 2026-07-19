#!/usr/bin/env python3
"""Validate the Phase 4.4C semantic contract without fetching constituents."""
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
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.breadth.service import get_breadth_snapshot_service
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.ai_context import build_market_ai_context
from app.services.breadth import calculate_market_breadth
from app.services.report import build_report_semantic_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.4C market semantic integrity")
    parser.add_argument("--test", action="store_true", help="Run deterministic breadth and sector regressions.")
    parser.add_argument("--live", action="store_true", help="Audit the current durable live snapshots.")
    parser.add_argument("--warm", action="store_true", help="Verify UI routes read snapshots without provider history calls.")
    parser.add_argument("--report", action="store_true", help="Verify report and Copilot semantic context.")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def add_check(report: dict[str, Any], name: str, passed: bool, details: Any, failure: str | None = None) -> None:
    report["checks"][name] = {"passed": passed, "details": details}
    if not passed and failure:
        report["failures"].append(failure)


def number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def model_data(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}


def load_before() -> dict[str, Any]:
    path = Path("/tmp/phase_4_4c_semantic_before.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def before_sector_rows(before: dict[str, Any]) -> list[dict[str, Any]]:
    payload = before.get("/market/sectors/snapshot/latest", {}).get("payload", {})
    rows = payload.get("sectors") if isinstance(payload, dict) else None
    return [row for row in rows or [] if isinstance(row, dict)]


def audit_breadth(breadth: Any, report: dict[str, Any]) -> None:
    data = model_data(breadth)
    advancing = int(data.get("advancing_stocks") or 0)
    declining = int(data.get("declining_stocks") or 0)
    raw = data.get("advance_decline_ratio")
    display = data.get("advance_decline_ratio_display")
    smoothed = data.get("advance_decline_ratio_smoothed")
    expected_raw = advancing / declining if declining else None
    raw_ok = (
        (declining == 0 and raw is None and display == ("No decliners" if advancing else "N/A"))
        or (declining > 0 and number(raw) is not None and abs(float(raw) - expected_raw) < 0.0001)
    )
    add_check(report, "advance_decline_semantics", raw_ok and number(smoothed) is not None, {
        "advancing": advancing,
        "declining": declining,
        "raw_ratio": raw,
        "display": display,
        "smoothed_ratio": smoothed,
        "ratio_method": data.get("ratio_method"),
    }, "advance_decline_semantics_invalid")

    dimensions = data.get("coverage_dimensions") or {}
    universe = dimensions.get("universe") if isinstance(dimensions, dict) else None
    ema200 = dimensions.get("ema200") if isinstance(dimensions, dict) else None
    dimensions_ok = all(isinstance(value, dict) and value.get("display") for value in (universe, ema200))
    add_check(report, "coverage_eligibility", dimensions_ok, {
        "universe": universe,
        "ema200": ema200,
        "data_confidence": data.get("data_confidence"),
        "signal_confidence": data.get("signal_confidence"),
    }, "coverage_eligibility_metadata_missing")


def audit_sectors(snapshot: Any, before: dict[str, Any], report: dict[str, Any]) -> None:
    rows = list(getattr(snapshot, "sectors", ()) or ())
    zero_denominator_rows: list[str] = []
    composite_failures: list[str] = []
    participation_failures: list[str] = []
    sample_failures: list[str] = []
    for row in rows:
        breadth = row.get("breadth_metrics") or {}
        if breadth.get("declining") == 0:
            zero_denominator_rows.append(row.get("sector_id", "unknown"))
            if breadth.get("advance_decline_ratio") is not None or breadth.get("advance_decline_ratio_display") != "No decliners":
                composite_failures.append(f"{row.get('sector_id')}:ad")
        audit = row.get("composite_audit") or {}
        contributions = audit.get("contributions") or {}
        total_weight = sum(float(item.get("weight") or 0) for item in contributions.values() if isinstance(item, dict))
        weighted_total = sum(float(item.get("weighted_contribution") or 0) for item in contributions.values() if isinstance(item, dict))
        score = number(row.get("composite_score"))
        expected_score = weighted_total / total_weight if total_weight else None
        if (
            audit.get("formula") != "equal_weight_mean_of_available_component_scores"
            or audit.get("formula_version") != "sector-composite-v1"
            or abs(total_weight - float(audit.get("total_weight") or 0)) > 0.00001
            or (score is not None and (expected_score is None or abs(score - expected_score) > 0.011))
        ):
            composite_failures.append(row.get("sector_id", "unknown"))
        participation = row.get("participation_metrics") or {}
        if participation.get("definition") != "Percent of eligible constituents with a positive 21-session return." or participation.get("is_distinct_from_ema50") is not True:
            participation_failures.append(row.get("sector_id", "unknown"))
        eligible = row.get("eligible_members")
        represented = row.get("breadth_representativeness")
        if not isinstance(eligible, int) or represented not in {"High", "Moderate", "Limited"} or not row.get("representativeness_reason"):
            sample_failures.append(row.get("sector_id", "unknown"))

    add_check(report, "sector_zero_denominator_semantics", not composite_failures or all(item != f"{sector}:ad" for sector in zero_denominator_rows for item in composite_failures), {
        "zero_decliner_sectors": zero_denominator_rows,
        "invalid_rows": [item for item in composite_failures if item.endswith(":ad")],
    }, "sector_zero_denominator_semantics_invalid")
    add_check(report, "sector_composite_audit", not [item for item in composite_failures if not item.endswith(":ad")], {
        "schema_version": getattr(snapshot, "schema_version", None),
        "invalid_rows": [item for item in composite_failures if not item.endswith(":ad")],
    }, "sector_composite_audit_invalid")
    add_check(report, "participation_is_distinct", not participation_failures, {"invalid_rows": participation_failures}, "participation_definition_invalid")
    add_check(report, "sector_sample_reliability", not sample_failures, {
        "invalid_rows": sample_failures,
        "samples": [{"sector": row.get("sector_id"), "eligible_members": row.get("eligible_members"), "representativeness": row.get("breadth_representativeness")} for row in rows],
    }, "sector_sample_reliability_missing")

    previous = {row.get("sector_id"): row for row in before_sector_rows(before)}
    changed: list[dict[str, Any]] = []
    for row in rows:
        old = previous.get(row.get("sector_id"))
        if not old:
            continue
        if old.get("rank") != row.get("rank") or number(old.get("composite_score")) != number(row.get("composite_score")):
            changed.append({
                "sector": row.get("sector_id"),
                "before_rank": old.get("rank"),
                "after_rank": row.get("rank"),
                "before_composite": old.get("composite_score"),
                "after_composite": row.get("composite_score"),
            })
    if not previous:
        report["conditions"].append("pre_change_sector_snapshot_unavailable_for_rank_comparison")
    add_check(report, "rank_and_score_stability", not changed, {"compared_rows": len(previous), "changed": changed}, "unreviewed_sector_rank_or_score_change")


def audit_live(report: dict[str, Any]) -> tuple[Any | None, Any | None]:
    breadth_snapshot = get_breadth_snapshot_service().latest()
    sector_snapshot = get_sector_snapshot_service().latest()
    breadth = calculate_market_breadth()
    add_check(report, "live_snapshot_provenance", bool(breadth_snapshot and sector_snapshot and breadth_snapshot.source_state == "live" and sector_snapshot.source_state == "live"), {
        "breadth_snapshot_id": getattr(breadth_snapshot, "snapshot_id", None),
        "breadth_source_state": getattr(breadth_snapshot, "source_state", None),
        "sector_snapshot_id": getattr(sector_snapshot, "snapshot_id", None),
        "sector_source_state": getattr(sector_snapshot, "source_state", None),
    }, "live_semantic_snapshots_unavailable")
    if breadth_snapshot:
        audit_breadth(breadth, report)
    else:
        add_check(report, "advance_decline_semantics", False, {}, "advance_decline_snapshot_missing")
    if sector_snapshot:
        audit_sectors(sector_snapshot, load_before(), report)
    else:
        add_check(report, "sector_composite_audit", False, {}, "sector_snapshot_missing")
    return breadth, sector_snapshot


def audit_warm(report: dict[str, Any]) -> dict[str, Any]:
    from main import app

    paths = [
        "/market/breadth",
        "/market/breadth/snapshot/latest",
        "/market/sectors/snapshot/latest",
        "/home/dashboard",
        "/market/health",
        "/market/decision-dashboard",
        "/market/details/decision",
        "/market/snapshot/latest",
    ]
    responses: dict[str, dict[str, Any]] = {}
    with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm semantic read called Polygon history")) as history:
        for path in paths:
            started = time.perf_counter()
            response = client.get(path)
            responses[path] = {
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "payload": response.json() if response.headers.get("content-type", "").startswith("application/json") else {},
            }
    status_ok = all(item["status"] == 200 for item in responses.values())
    latency_ok = all(item["latency_ms"] < 500 for item in responses.values())
    add_check(report, "warm_snapshot_reads", status_ok and latency_ok and history.call_count == 0, {
        "provider_history_calls": history.call_count,
        "routes": {path: {"status": item["status"], "latency_ms": item["latency_ms"]} for path, item in responses.items()},
    }, "warm_snapshot_navigation_failed")

    health = responses["/market/health"]["payload"].get("decision_confidence") or {}
    decision = responses["/market/decision-dashboard"]["payload"].get("decision_confidence") or {}
    detail = (responses["/market/details/decision"]["payload"].get("decisionDashboard") or {}).get("decision_confidence") or {}
    home = ((responses["/home/dashboard"]["payload"].get("core") or {}).get("decision_summary") or {}).get("decision_confidence") or {}
    snapshot = ((responses["/market/snapshot/latest"]["payload"].get("sections") or {}).get("decision") or {}).get("payload") or {}
    snapshot_confidence = snapshot.get("decision_confidence") or {}
    candidates = [health, decision, detail, home, snapshot_confidence]
    canonical = decision
    keys = ("score", "status", "reason", "source_snapshot_id")
    consistent = bool(canonical) and all(all(candidate.get(key) == canonical.get(key) for key in keys) for candidate in candidates)
    add_check(report, "decision_confidence_consistency", consistent, {
        "canonical": canonical,
        "sources": {"health": health, "detail": detail, "home": home, "snapshot": snapshot_confidence},
    }, "decision_confidence_mismatch")

    sectors = responses["/market/sectors/snapshot/latest"]["payload"].get("sectors") or []
    core = responses["/home/dashboard"]["payload"].get("core") or {}
    expected_laggard = sectors[-1] if sectors else None
    actual_laggard = core.get("lagging_sector")
    laggard_ok = bool(expected_laggard) and isinstance(actual_laggard, dict) and actual_laggard.get("rank") == expected_laggard.get("rank") and actual_laggard.get("name") == expected_laggard.get("display_name")
    add_check(report, "home_laggard_consistency", laggard_ok, {
        "expected": {"name": expected_laggard.get("display_name"), "rank": expected_laggard.get("rank")} if expected_laggard else None,
        "actual": actual_laggard,
    }, "home_laggard_not_from_canonical_sector_snapshot")
    return {"responses": responses, "canonical_confidence": canonical}


def audit_report_and_copilot(report: dict[str, Any], breadth: Any | None, canonical_confidence: dict[str, Any]) -> None:
    if breadth is None:
        breadth = calculate_market_breadth()
    context = build_report_semantic_context(breadth, type("Decision", (), {"model_dump": lambda self: canonical_confidence})())
    analysis = {
        "breadth": {"market": model_data(breadth)},
        "decision_confidence": canonical_confidence,
        "decision_dashboard": {"decision_confidence": canonical_confidence},
        "semantic_context": context,
    }
    copilot = build_market_ai_context(analysis)
    required = {"advance_decline", "coverage_dimensions", "data_confidence", "signal_confidence", "decision_confidence", "sector_breadth_representativeness"}
    context_ok = required.issubset(context) and copilot.get("breadth_semantics", {}).get("advance_decline") == context.get("advance_decline")
    add_check(report, "report_and_copilot_semantics", context_ok, {
        "report_context": context,
        "copilot_breadth_semantics": copilot.get("breadth_semantics"),
        "copilot_sector_samples": len(copilot.get("sector_breadth_representativeness") or []),
    }, "report_or_copilot_semantic_context_incomplete")


def run_tests(report: dict[str, Any]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_breadth_snapshot", "tests.test_sector_snapshot"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    add_check(report, "semantic_regressions", result.returncode == 0, {
        "output": (result.stdout + result.stderr)[-4000:],
    }, "semantic_regression_tests_failed")


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {"phase": "4.4c-semantics", "passed": False, "failures": [], "conditions": [], "checks": {}}
    if not any((args.test, args.live, args.warm, args.report)):
        report["conditions"].append("no_validation_mode_selected")
    if args.test:
        run_tests(report)
    breadth: Any | None = None
    if args.live or args.report:
        breadth, _ = audit_live(report)
    warm = audit_warm(report) if args.warm else {"canonical_confidence": {}}
    if args.report:
        audit_report_and_copilot(report, breadth, warm["canonical_confidence"])
    report["passed"] = not report["failures"]
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

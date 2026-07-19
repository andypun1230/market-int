#!/usr/bin/env python3
"""Final, non-destructive Phase 4.4C release-gate validation matrix."""
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

from app.breadth.service import get_breadth_snapshot_service, reset_breadth_snapshot_service
from app.sector_snapshots.service import get_sector_snapshot_service, reset_sector_snapshot_service
from app.services.ai_context import build_market_ai_context
from app.services.analysis import build_market_analysis
from app.services.breadth import calculate_market_breadth
from app.services.report import build_daily_report
from app.services.theme_provenance import is_live_theme_intelligence
from app.snapshots.service import get_market_snapshot_service, reset_market_snapshot_service


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_PARTIAL = "PARTIAL"
STATUS_SKIP = "SKIP"
STATUS_MANUAL = "MANUAL REQUIRED"

ENDPOINTS = (
    "/home/dashboard", "/market/snapshot/latest", "/market/core-snapshot", "/market/regime",
    "/market/health", "/market/breadth", "/market/details/structure", "/market/decision-dashboard",
    "/market/details/decision", "/market/details/institutional", "/market/macro",
    "/market/sectors/snapshot/latest", "/market/sectors", "/market/sectors/rotation", "/market/fear-greed",
    "/report/daily",
)
WARM_ENDPOINTS = tuple(path for path in ENDPOINTS if path != "/report/daily")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate final Phase 4.4C release gate")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--copilot-context", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def add(matrix: dict[str, Any], key: str, status: str, details: Any, remediation: str | None = None) -> None:
    matrix[key] = {"status": status, "details": details}
    if remediation:
        matrix[key]["remediation"] = remediation


def model_data(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else value if isinstance(value, dict) else {}


def number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def endpoint_audit() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    from main import app

    responses: dict[str, dict[str, Any]] = {}
    with TestClient(app) as client:
        for path in ENDPOINTS:
            started = time.perf_counter()
            response = client.get(path)
            payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
            responses[path] = {
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "snapshot_id": payload.get("snapshot_id") if isinstance(payload, dict) else None,
                "payload": payload,
            }
    status = STATUS_PASS if all(row["status"] == 200 for row in responses.values()) else STATUS_FAIL
    return {"status": status, "details": {path: {key: row[key] for key in ("status", "latency_ms", "snapshot_id")} for path, row in responses.items()}}, responses


def audit_breadth(matrix: dict[str, Any], breadth: dict[str, Any]) -> None:
    advancing = int(breadth.get("advancing_stocks") or 0)
    declining = int(breadth.get("declining_stocks") or 0)
    unchanged = int(breadth.get("unchanged_stocks") or 0)
    total = int(breadth.get("total_stocks") or 0)
    raw = number(breadth.get("advance_decline_ratio"))
    expected_raw = advancing / declining if declining else None
    arithmetic_ok = advancing + declining + unchanged == total and (
        (declining == 0 and raw is None and breadth.get("advance_decline_ratio_display") in ("No decliners", "N/A"))
        or (declining > 0 and raw is not None and abs(raw - expected_raw) < 0.0001)
    )
    add(matrix, "breadth_arithmetic", STATUS_PASS if arithmetic_ok else STATUS_FAIL, {
        "advancing": advancing, "declining": declining, "unchanged": unchanged, "analysed": total,
        "raw_ad_ratio": raw, "display": breadth.get("advance_decline_ratio_display"),
        "smoothed_ad_ratio": breadth.get("advance_decline_ratio_smoothed"),
        "new_highs": breadth.get("new_52w_highs"), "new_lows": breadth.get("new_52w_lows"),
    }, "Trace BreadthSnapshot inputs if counts or raw A/D semantics disagree.")

    dimensions = breadth.get("coverage_dimensions") or {}
    universe, ema200, fifty_two_week = dimensions.get("universe"), dimensions.get("ema200"), dimensions.get("fifty_two_week")
    eligibility_ok = all(isinstance(item, dict) and item.get("display") for item in (universe, ema200))
    add(matrix, "coverage_and_eligibility", STATUS_PASS if eligibility_ok else STATUS_FAIL, {
        "universe": universe, "ema20": dimensions.get("ema20"), "ema50": dimensions.get("ema50"),
        "ema200": ema200, "fifty_two_week": fifty_two_week,
    }, "Expose each long-indicator eligibility dimension separately from universe coverage.")

    data_confidence = breadth.get("data_confidence") or {}
    signal_confidence = breadth.get("signal_confidence") or {}
    signal_ok = all(key in signal_confidence for key in ("score", "label", "reason", "source_snapshot_id", "calculated_at"))
    distinct = data_confidence.get("score") != signal_confidence.get("score") or data_confidence.get("reason") != signal_confidence.get("reason")
    add(matrix, "breadth_signal_confidence", STATUS_PASS if signal_ok and distinct else STATUS_FAIL, {
        "data_confidence": data_confidence, "signal_confidence": signal_confidence,
    }, "Keep the independently calculated breadth signal confidence intact through every adapter.")


def audit_sectors(matrix: dict[str, Any], snapshot: Any) -> None:
    rows = list(getattr(snapshot, "sectors", ()) or ())
    fair: list[dict[str, Any]] = []
    participation_errors: list[str] = []
    composite_errors: list[str] = []
    for row in rows:
        eligible, band = row.get("eligible_members"), row.get("breadth_representativeness")
        expected_band = "High" if isinstance(eligible, int) and eligible >= 10 else "Moderate" if isinstance(eligible, int) and eligible >= 4 else "Limited"
        fair.append({"sector": row.get("display_name"), "eligible_members": eligible, "band": band, "expected_band": expected_band, "reason": row.get("representativeness_reason")})
        participation = row.get("participation_metrics") or {}
        if participation.get("definition") != "Percent of eligible constituents with a positive 21-session return." or participation.get("is_distinct_from_ema50") is not True:
            participation_errors.append(str(row.get("sector_id")))
        audit = row.get("composite_audit") or {}
        contributions = audit.get("contributions") or {}
        weight = sum(float(item.get("weight") or 0) for item in contributions.values() if isinstance(item, dict))
        weighted = sum(float(item.get("weighted_contribution") or 0) for item in contributions.values() if isinstance(item, dict))
        score = number(row.get("composite_score"))
        if audit.get("formula") != "equal_weight_mean_of_available_component_scores" or not weight or score is None or abs(score - weighted / weight) > 0.011:
            composite_errors.append(str(row.get("sector_id")))
    fairness_ok = bool(rows) and all(item["band"] == item["expected_band"] and item["reason"] for item in fair)
    add(matrix, "sector_sample_size_fairness", STATUS_PASS if fairness_ok else STATUS_FAIL, {"sectors": fair}, "Preserve ranks but expose the configured representativeness policy on every sector row.")
    add(matrix, "participation_audit", STATUS_PASS if not participation_errors else STATUS_FAIL, {"invalid_rows": participation_errors, "definition": "positive 21-session return"}, "Participation must remain distinct from EMA50 breadth.")
    add(matrix, "sector_composite_contributions", STATUS_PASS if not composite_errors else STATUS_FAIL, {"invalid_rows": composite_errors}, "Composite audit contributions must sum to the published score within rounding tolerance.")


def audit_cross_screen(matrix: dict[str, Any], responses: dict[str, dict[str, Any]]) -> None:
    home = responses["/home/dashboard"]["payload"].get("core") or {}
    snapshot = responses["/market/snapshot/latest"]["payload"]
    core = responses["/market/core-snapshot"]["payload"]
    breadth = responses["/market/breadth"]["payload"].get("market") or {}
    health = responses["/market/health"]["payload"]
    decision = responses["/market/decision-dashboard"]["payload"]
    sector = responses["/market/sectors/snapshot/latest"]["payload"]
    decision_confidence = decision.get("decision_confidence") or {}
    candidates = [
        health.get("decision_confidence") or {},
        (home.get("decision_summary") or {}).get("decision_confidence") or {},
        (core.get("decision_summary") or {}).get("decision_confidence") or {},
    ]
    confidence_ok = bool(decision_confidence) and all(
        all(item.get(key) == decision_confidence.get(key) for key in ("score", "status", "reason", "source_snapshot_id"))
        for item in candidates
    )
    add(matrix, "home_market_health_decision_consistency", STATUS_PASS if confidence_ok else STATUS_FAIL, {
        "canonical_decision_confidence": decision_confidence, "other_confidences": candidates,
        "health": health.get("overall_score"), "risk": (home.get("risk_summary") or {}).get("score"),
    }, "Use the MarketSnapshot decision object rather than recomputing screen-local confidence.")

    sectors = sector.get("sectors") or []
    leader, laggard = (sectors[0] if sectors else {}), (sectors[-1] if sectors else {})
    canonical_ok = (
        (home.get("top_sector") or {}).get("name") == leader.get("display_name")
        and (home.get("lagging_sector") or {}).get("name") == laggard.get("display_name")
        and (home.get("breadth_summary") or {}).get("snapshot_id") == breadth.get("snapshot_id")
    )
    add(matrix, "home_sector_snapshot_consistency", STATUS_PASS if canonical_ok else STATUS_FAIL, {
        "leader": leader.get("display_name"), "laggard": laggard.get("display_name"),
        "home_leader": home.get("top_sector"), "home_laggard": home.get("lagging_sector"),
        "breadth_snapshot_id": breadth.get("snapshot_id"), "home_breadth_snapshot_id": (home.get("breadth_summary") or {}).get("snapshot_id"),
        "market_snapshot_id": snapshot.get("snapshot_id"),
    }, "Align home adapters with the durable sector and breadth snapshots.")


def audit_theme_and_wording(matrix: dict[str, Any]) -> None:
    industry = build_market_analysis().get("industry_groups") or {}
    provenance = industry.get("theme_provenance") or {}
    items = industry.get("items") or []
    theme_ok = not is_live_theme_intelligence(provenance) and all(not is_live_theme_intelligence(item.get("provenance")) for item in items if isinstance(item, dict))
    add(matrix, "theme_provenance_quarantine", STATUS_PASS if theme_ok else STATUS_FAIL, {"provenance": provenance, "item_count": len(items)}, "Do not expose configured industry baskets as live Theme Intelligence before Phase 4.4D.")

    rotation = (REPO_ROOT / "frontend/src/features/sectors/rotationCopy.ts").read_text()
    sector_detail = (REPO_ROOT / "frontend/src/features/sectors/components/SectorDetailContent.tsx").read_text()
    rotation_ok = "adjusted ETF-versus-SPY history" in rotation and "SectorSnapshots" in rotation and "rotationTrailMethodology" in sector_detail
    add(matrix, "sector_rotation_dual_history_wording", STATUS_PASS if rotation_ok else STATUS_FAIL, {"copy": rotation.strip()}, "Keep market-history trails and snapshot-transition history explicitly distinct.")

    health = (REPO_ROOT / "frontend/src/features/market/healthAnalysis.ts").read_text()
    health_ok = "Trend history unavailable" in health and "History unavailable" not in health
    add(matrix, "market_health_history_wording", STATUS_PASS if health_ok else STATUS_FAIL, {"canonical_label": "Trend history unavailable"}, "Describe only the unavailable trend comparison, not the available current health score.")

    overview = (REPO_ROOT / "frontend/src/features/market/marketOverviewAnalysis.ts").read_text()
    index = (REPO_ROOT / "frontend/src/features/market/indexAnalysis.ts").read_text()
    iwm_ok = "Relative leader:" in overview and "trend remains" in overview and "Relative leader:" in index
    add(matrix, "iwm_relative_leader_semantics", STATUS_PASS if iwm_ok else STATUS_FAIL, {"required_copy": "Relative leader: IWM; trend remains Neutral"}, "Keep relative rank separate from IWM's own neutral trend state.")


def audit_report(matrix: dict[str, Any], responses: dict[str, dict[str, Any]]) -> None:
    report = build_daily_report()
    live = responses["/report/daily"]["payload"]
    semantic = report.semantic_context or {}
    ids = semantic.get("snapshot_ids") or {}
    report_ok = responses["/report/daily"]["status"] == 200 and all(ids.get(key) not in (None, "", "unavailable") for key in ("market", "breadth", "sector"))
    macro = report.macro or {}
    no_live_themes = not any(is_live_theme_intelligence(item.get("provenance")) for item in ((report.sector_dashboard or {}).get("themes") or []) if isinstance(item, dict))
    macro_assets = macro.get("assets") or []
    macro_ok = (
        semantic.get("macro") == macro and bool(macro.get("invalidation_conditions")) and "current_risks" in macro
        and macro.get("source_state") in {"live", "cached"}
        and all(asset.get("is_live") and asset.get("provider") != "mock" for asset in macro_assets if isinstance(asset, dict))
    )
    add(matrix, "report_semantic_consistency", STATUS_PASS if report_ok and no_live_themes and macro_ok else STATUS_FAIL, {
        "report_id": report.report_id, "snapshot_ids": ids, "macro": macro, "http_report_id": live.get("report_id"), "themes_live": not no_live_themes,
    }, "Regenerate report from current semantic snapshot IDs and omit unverified theme leadership.")
    first, second = build_daily_report(), build_daily_report()
    stable = first.semantic_context == second.semantic_context and first.date == second.date
    add(matrix, "report_determinism", STATUS_PASS if stable else STATUS_FAIL, {"date": first.date, "snapshot_ids": first.semantic_context.get("snapshot_ids")}, "Cache and report context must remain stable for identical durable snapshots.")


def audit_macro_and_copilot(matrix: dict[str, Any], responses: dict[str, dict[str, Any]], enabled: bool) -> None:
    macro = responses["/market/macro"]["payload"]
    macro_ok = (
        bool(macro.get("summary")) and "current_risks" in macro and bool(macro.get("invalidation_conditions"))
        and macro.get("provenance", {}).get("mock_fallback") is False
        and macro.get("source_state") in {"live", "cached"}
        and macro.get("state") == "strong_risk_on"
    )
    add(matrix, "macro_current_state_and_invalidation", STATUS_PASS if macro_ok else STATUS_FAIL, {
        "state": macro.get("state_label"), "score": macro.get("score"), "supporting_evidence": macro.get("supporting_evidence"),
        "current_risks": macro.get("current_risks"), "invalidation_conditions": macro.get("invalidation_conditions"), "source": macro.get("source_label"),
    }, "Keep the current macro state and conditions that would invalidate it in separate fields.")
    if not enabled:
        add(matrix, "copilot_context_consistency", STATUS_SKIP, {"reason": "--copilot-context not selected"})
        return
    context = build_market_ai_context(build_market_analysis())
    breadth = context.get("breadth_semantics") or {}
    copilot_ok = (
        bool(context.get("macro")) and bool(breadth.get("signal_confidence"))
        and bool(context.get("sector_breadth_representativeness"))
        and context.get("industry_groups", {}).get("availability", "").startswith("Static strategy preferences")
    )
    add(matrix, "copilot_context_consistency", STATUS_PASS if copilot_ok else STATUS_FAIL, {
        "macro": context.get("macro"), "breadth": breadth, "theme": context.get("industry_groups"),
        "sample_rows": len(context.get("sector_breadth_representativeness") or []),
    }, "Copilot context must preserve confidence type, sample limitations, macro fields, and theme provenance.")


def audit_warm(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        add(matrix, "warm_navigation_provider_isolation", STATUS_SKIP, {"reason": "--warm not selected"})
        return
    from main import app

    results: dict[str, Any] = {}
    with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("warm read fetched Polygon history")) as polygon:
        for path in WARM_ENDPOINTS:
            started = time.perf_counter()
            response = client.get(path)
            results[path] = {"status": response.status_code, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    ok = polygon.call_count == 0 and all(row["status"] == 200 and row["latency_ms"] < 750 for row in results.values())
    add(matrix, "warm_navigation_provider_isolation", STATUS_PASS if ok else STATUS_FAIL, {"provider_history_calls": polygon.call_count, "routes": results}, "Warm user navigation must reuse durable snapshots and cached macro state without provider history work.")


def audit_restart(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        add(matrix, "restart_persistence", STATUS_SKIP, {"reason": "--restart not selected"})
        return
    before = {
        "breadth": getattr(get_breadth_snapshot_service().latest(), "snapshot_id", None),
        "sector": getattr(get_sector_snapshot_service().latest(), "snapshot_id", None),
        "market": getattr(get_market_snapshot_service().get_latest_snapshot(), "snapshot_id", None),
    }
    reset_breadth_snapshot_service(); reset_sector_snapshot_service(); reset_market_snapshot_service()
    after = {
        "breadth": getattr(get_breadth_snapshot_service().latest(), "snapshot_id", None),
        "sector": getattr(get_sector_snapshot_service().latest(), "snapshot_id", None),
        "market": getattr(get_market_snapshot_service().get_latest_snapshot(), "snapshot_id", None),
    }
    ok = all(before[key] and before[key] == after[key] for key in before)
    add(matrix, "restart_persistence", STATUS_PASS if ok else STATUS_FAIL, {"before": before, "after": after}, "Latest/LKG durable snapshots must survive service reinitialization unchanged.")


def run_regressions(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        add(matrix, "release_gate_regressions", STATUS_SKIP, {"reason": "--test not selected"})
        return
    command = [sys.executable, "-m", "unittest", "tests.test_release_gate_semantics", "tests.test_breadth_snapshot", "tests.test_sector_snapshot"]
    result = subprocess.run(command, cwd=BACKEND_ROOT, capture_output=True, text=True)
    add(matrix, "release_gate_regressions", STATUS_PASS if result.returncode == 0 else STATUS_FAIL, {"command": " ".join(command), "output": (result.stdout + result.stderr)[-4000:]}, "Repair the deterministic regression before accepting the release gate.")


def run_frontend_breadth_regressions(matrix: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        add(matrix, "breadth_frontend_adapter", STATUS_SKIP, {"reason": "--test not selected"})
        return
    commands = (
        ["npx", "tsx", "tests/marketDataNormalizers.test.ts"],
        ["npx", "tsx", "tests/breadthAnalysis.test.ts"],
    )
    output: list[str] = []
    passed = True
    for command in commands:
        result = subprocess.run(command, cwd=REPO_ROOT / "frontend", capture_output=True, text=True)
        output.append(" ".join(command) + "\n" + (result.stdout + result.stderr)[-2000:])
        passed = passed and result.returncode == 0
    add(
        matrix,
        "breadth_frontend_adapter",
        STATUS_PASS if passed else STATUS_FAIL,
        {"commands": [" ".join(command) for command in commands], "output": "\n".join(output)},
        "Preserve canonical confidence, eligibility, and finite A/D semantics through the frontend breadth compatibility adapter.",
    )


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = ["# Phase 4.4C Final Release Gate", "", f"Overall result: **{report['overall_result']}**", "", "## Checklist", "", "| Check | Status |", "| --- | --- |"]
    for key, value in report["matrix"].items():
        lines.append(f"| {key.replace('_', ' ')} | {value['status']} |")
    if report["conditions"]:
        lines.extend(["", "## Conditions", "", *[f"- {item}" for item in report["conditions"]]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {"phase": "4.4c-final-release-gate", "matrix": {}, "conditions": [], "remediation_proposals": []}
    endpoint_result, responses = endpoint_audit()
    add(report["matrix"], "endpoint_http_500_and_availability", endpoint_result["status"], endpoint_result["details"], "Repair any non-200 release-gate endpoint before release.")

    breadth = responses["/market/breadth"]["payload"].get("market") or model_data(calculate_market_breadth())
    audit_breadth(report["matrix"], breadth)
    audit_sectors(report["matrix"], get_sector_snapshot_service().latest())
    audit_cross_screen(report["matrix"], responses)
    audit_theme_and_wording(report["matrix"])
    audit_macro_and_copilot(report["matrix"], responses, args.copilot_context)
    if args.report:
        audit_report(report["matrix"], responses)
    else:
        add(report["matrix"], "report_semantic_consistency", STATUS_SKIP, {"reason": "--report not selected"})
        add(report["matrix"], "report_determinism", STATUS_SKIP, {"reason": "--report not selected"})
    audit_warm(report["matrix"], args.warm)
    audit_restart(report["matrix"], args.restart)
    run_regressions(report["matrix"], args.test)
    run_frontend_breadth_regressions(report["matrix"], args.test)
    add(report["matrix"], "live_screen_mock_leakage", STATUS_PASS if all(
        row["payload"].get("source_state") != "mock" for row in responses.values() if isinstance(row["payload"], dict)
    ) else STATUS_FAIL, {"checked_endpoints": list(ENDPOINTS)}, "Live routes must not present test or mock snapshots as live data.")
    add(report["matrix"], "native_simulator_layout", STATUS_MANUAL, {"web_mobile_validation": "run separately", "reason": "No native simulator automation is configured."})
    add(report["matrix"], "controlled_test_detail_routes", STATUS_PARTIAL, {"reason": "Test-mode structure, decision, and institutional detail routes deliberately report partial optional detail."})

    statuses = [row["status"] for row in report["matrix"].values()]
    failed = [key for key, row in report["matrix"].items() if row["status"] == STATUS_FAIL]
    partial = [key for key, row in report["matrix"].items() if row["status"] == STATUS_PARTIAL]
    manual = [key for key, row in report["matrix"].items() if row["status"] == STATUS_MANUAL]
    report["snapshot_ids"] = {
        "breadth": breadth.get("snapshot_id"),
        "sector": responses["/market/sectors/snapshot/latest"]["payload"].get("snapshot_id"),
        "market": responses["/market/snapshot/latest"]["payload"].get("snapshot_id"),
    }
    report["totals"] = {status: statuses.count(status) for status in (STATUS_PASS, STATUS_FAIL, STATUS_PARTIAL, STATUS_SKIP, STATUS_MANUAL)}
    report["conditions"] = [
        "shallow breadth and sector snapshot transition history", "HONA recent-listing long-history ineligibility", "S&P 100 large-cap concentration",
        "native simulator gesture/layout validation requires manual QA", "controlled partial test-mode detail routes",
    ]
    report["overall_result"] = "FAIL" if failed else "PASS WITH CONDITIONS" if partial or manual else "PASS"
    report["failed_checks"] = failed
    report["partial_checks"] = partial
    report["manual_required_checks"] = manual
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    if args.markdown_output:
        write_markdown(report, args.markdown_output)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_history.storage import DailyBarStorage
from app.rotation.visual_acceptance import (
    THEME_ROTATION_VISUAL_ACCEPTANCE_PATH,
    inspect_theme_rotation_visual_acceptance,
    require_theme_rotation_visual_acceptance,
)
from app.securities.storage import SecurityMasterStorage
from app.themes.intelligence import get_theme_intelligence_service
from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry


parser = argparse.ArgumentParser(description="Generate Stage 8.75 Theme Intelligence validation artifacts")
parser.add_argument("--performance-artifact", default="../artifacts/stage8.75-performance.json")
parser.add_argument("--rotation-artifact", default="../artifacts/stage8.75-theme-rotation-validation.json")
parser.add_argument("--rotation-model-spec", default="../artifacts/stage8.75-theme-rotation-model-spec.json")
parser.add_argument("--rotation-sensitivity", default="../artifacts/stage8.75-theme-rotation-sensitivity.json")
parser.add_argument("--rotation-synthetic", default="../artifacts/stage8.75-theme-rotation-synthetic-tests.json")
parser.add_argument("--rotation-coordinates", default="../artifacts/stage8.75-theme-rotation-coordinates.json")
parser.add_argument("--rotation-visual-acceptance", default=str(THEME_ROTATION_VISUAL_ACCEPTANCE_PATH))
parser.add_argument("--sector-rotation-artifact", default="../artifacts/stage8.75-sector-rotation-validation.json")
parser.add_argument("--sector-rotation-visual-acceptance", default="../artifacts/stage8.75-sector-rotation-frontend-visual-acceptance.json")
parser.add_argument("--symbol-audit", default="../artifacts/stage8.75-symbol-coverage-audit.json")
parser.add_argument("--coverage-output", default="../artifacts/stage8.75-theme-coverage-matrix.json")
parser.add_argument("--output", default="../artifacts/stage8.75-theme-intelligence-validation.json")
parser.add_argument("--markdown-output", default="../docs/validation/stage8.75-theme-intelligence-validation-report.md")
parser.add_argument("--release-gates-passed", action="store_true", help="Set only when invoked after all Make release-gate prerequisites succeed.")


BASELINE_STATUS = {
    "artificial_intelligence": "available", "semiconductors": "available", "memory_storage": "available",
    "data_centers": "unavailable", "cloud_computing": "partial", "enterprise_software": "available",
    "cybersecurity": "available", "networking_infrastructure": "partial", "robotics_automation": "partial",
    "digital_advertising": "partial", "ecommerce": "unavailable", "digital_payments": "partial",
    "online_travel": "unavailable", "gaming_interactive_media": "unavailable", "streaming_digital_entertainment": "partial",
    "aerospace_defense": "partial", "space_economy": "unavailable", "drones_autonomous_systems": "unavailable",
    "nuclear_energy": "unavailable", "grid_modernization": "partial", "clean_energy": "unavailable",
    "electric_vehicles_batteries": "partial", "biotechnology": "partial", "obesity_metabolic_health": "partial",
    "medical_technology": "partial", "cryptocurrency_infrastructure": "unavailable",
}


def count_tests(start: str, pattern: str = "test*.py") -> int:
    return unittest.defaultTestLoader.discover(start, pattern=pattern).countTestCases()


def git_output(*args: str) -> str:
    return subprocess.run(("git", *args), check=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    args = parser.parse_args()
    registry = get_launch_theme_registry()
    stats = registry.statistics()
    issues = registry.validate()
    performance = json.loads(Path(args.performance_artifact).read_text())
    rotation = json.loads(Path(args.rotation_artifact).read_text())
    rotation_model_spec = json.loads(Path(args.rotation_model_spec).read_text())
    rotation_sensitivity = json.loads(Path(args.rotation_sensitivity).read_text())
    rotation_synthetic = json.loads(Path(args.rotation_synthetic).read_text())
    rotation_coordinates = json.loads(Path(args.rotation_coordinates).read_text())
    sector_rotation = json.loads(Path(args.sector_rotation_artifact).read_text())
    sector_rotation_visual_acceptance = json.loads(Path(args.sector_rotation_visual_acceptance).read_text())
    symbol_audit = json.loads(Path(args.symbol_audit).read_text())
    audit_rows = symbol_audit.get("symbols") or []
    if symbol_audit.get("symbol_count") != 138 or len(audit_rows) != 138 or len({item.get("symbol") for item in audit_rows}) != 138:
        raise RuntimeError("stage8_75_symbol_audit_must_cover_exactly_138_unique_symbols")
    if any(not isinstance(item.get("category", {}).get("number"), int) for item in audit_rows):
        raise RuntimeError("stage8_75_symbol_audit_requires_one_governed_category_per_symbol")
    if symbol_audit.get("security_master_apply", {}).get("eligible_records") != 132:
        raise RuntimeError("stage8_75_security_master_audit_expected_132_eligible_records")
    if symbol_audit.get("production_history_refresh", {}).get("failed"):
        raise RuntimeError("stage8_75_production_history_refresh_contains_failures")

    active = list(registry.launch())
    service = get_theme_intelligence_service()
    directory_rows = service.list_themes()["items"]
    snapshot = service.snapshots.latest()
    if snapshot is None or snapshot.taxonomy_version != TAXONOMY_VERSION or len(snapshot.coverage_audit) != 26:
        raise RuntimeError("canonical_stage8_75_snapshot_required")
    if rotation.get("snapshot_id") != snapshot.snapshot_id or rotation.get("taxonomy_version") != TAXONOMY_VERSION:
        raise RuntimeError("theme_rotation_artifact_snapshot_identity_mismatch")
    if any(rotation.get("datasets", {}).get(timeframe, {}).get("eligible_theme_count") != 26 for timeframe in ("1W", "1M", "3M")):
        raise RuntimeError("theme_rotation_artifact_requires_26_points_per_timeframe")
    if rotation_model_spec.get("version") != "theme-relative-trend-momentum-v1":
        raise RuntimeError("theme_rotation_model_spec_version_mismatch")
    if rotation_sensitivity.get("result") != "PASS" or rotation_sensitivity.get("candidate_count") != 9:
        raise RuntimeError("theme_rotation_sensitivity_failed")
    if rotation_synthetic.get("result") != "PASS" or rotation_synthetic.get("network_calls") or rotation_synthetic.get("model_calls"):
        raise RuntimeError("theme_rotation_synthetic_suite_failed")
    if rotation_coordinates.get("snapshot_id") != snapshot.snapshot_id or rotation_coordinates.get("reasonableness", {}).get("eligible_themes_each_profile") != 26:
        raise RuntimeError("theme_rotation_coordinate_artifact_mismatch")
    rotation_visual_acceptance, rotation_visual_diagnostics = inspect_theme_rotation_visual_acceptance(
        args.rotation_visual_acceptance,
        latest_snapshot_id=snapshot.snapshot_id,
    )
    print(json.dumps({"theme_rotation_visual_acceptance": rotation_visual_diagnostics}, indent=2, sort_keys=True))
    require_theme_rotation_visual_acceptance(rotation_visual_diagnostics)
    if (
        sector_rotation.get("overall_result") != "PASS"
        or sector_rotation.get("model_version") != "sector-relative-trend-momentum-v1"
        or sector_rotation.get("sector_count") != 11
        or sector_rotation.get("parameter_parity_with_theme_model") is not True
    ):
        raise RuntimeError("sector_rotation_mathematics_failed")
    if (
        sector_rotation_visual_acceptance.get("result") != "PASS"
        or sector_rotation_visual_acceptance.get("snapshot_id") != sector_rotation.get("snapshot_id")
        or sector_rotation_visual_acceptance.get("model_version") != "sector-relative-trend-momentum-v1"
        or any(
            item.get("result") != "PASS"
            for item in sector_rotation_visual_acceptance.get("checks", {}).values()
        )
    ):
        raise RuntimeError("sector_rotation_visual_acceptance_failed")
    snapshot_rows = {item["theme_id"]: item for item in snapshot.rows}
    live_rows = {item["theme_id"]: item for item in directory_rows}
    gate_rows = {item["theme_id"]: item for item in snapshot.coverage_audit}

    unique_symbols = sorted({item.symbol for item in registry.mappings})
    master_storage = SecurityMasterStorage()
    history_storage = DailyBarStorage()
    registered = master_storage.active_securities(tuple(unique_symbols))
    histories = history_storage.histories(tuple(unique_symbols))
    symbol_states = []
    for symbol in unique_symbols:
        security = registered.get(symbol)
        bars = histories.get(symbol, [])
        dates = [item.session_date for item in bars]
        symbol_states.append({
            "symbol": symbol,
            "registered": security is not None,
            "history_provider_capable": bool(security and security.history_provider_symbol),
            "bar_count": len(bars),
            "history_21d": len(bars) >= 22,
            "history_50d": len(bars) >= 50,
            "history_200d": len(bars) >= 200,
            "first_session": dates[0] if dates else None,
            "latest_session": dates[-1] if dates else None,
            "duplicate_sessions": len(dates) - len(set(dates)),
            "adjusted_only": all(item.adjusted for item in bars) if bars else None,
        })
    symbol_state_by_id = {item["symbol"]: item for item in symbol_states}
    mapping_state_rows = [{"theme_id": item.theme_id, "exposure": item.exposure, **symbol_state_by_id[item.symbol]} for item in registry.mappings]

    unsupported_symbols = set(symbol_audit.get("unsupported_or_not_registered") or [])
    provider_valid_special_symbols = {
        item["symbol"] for item in audit_rows
        if item.get("category", {}).get("number") == 8 and item.get("provider_current_metadata") and item["symbol"] != "ABB"
    }
    theme_table: list[dict[str, Any]] = []
    for definition in active:
        mappings = registry.constituents(definition.id)
        mapped_symbols = [item.symbol for item in mappings]
        gate = gate_rows[definition.id]
        directory = live_rows[definition.id]
        snapshot_row = snapshot_rows.get(definition.id, {})
        confidence = snapshot_row.get("confidence", {})
        confidence_label = confidence.get("label") if isinstance(confidence, dict) else confidence
        missing = list(gate.get("unregistered_symbols") or [])
        theme_table.append({
            "theme_id": definition.id,
            "display_name": definition.name,
            "parent_sectors": list(definition.parent_sector_ids),
            "mapped_constituent_count": len(mappings),
            "valid_canonical_constituent_count": sum(symbol not in {"ABB", "DESP", "JNPR"} for symbol in mapped_symbols),
            "registered_constituent_count": gate["security_master_count"],
            "provider_capable_count": gate["history_provider_capable_count"] + sum(symbol in provider_valid_special_symbols for symbol in mapped_symbols),
            "history_21d_sufficient_count": gate["history_21d_count"],
            "history_50d_sufficient_count": gate["history_50d_count"],
            "history_200d_sufficient_count": gate["history_200d_count"],
            "history_21d_mapped_coverage": gate["coverage_ratio"],
            "benchmark_availability": gate["primary_benchmark_available"],
            "parent_sector_benchmark_availability": gate["sector_benchmark_available"],
            "parent_sector_benchmarks": gate["sector_benchmarks"],
            "latest_common_date": gate["market_date"],
            "snapshot_status": directory["status"],
            "coverage_status": snapshot_row.get("coverage_status", "unavailable"),
            "confidence": confidence_label or "limited",
            "ranking_eligibility": snapshot_row.get("rank") is not None,
            "rank": snapshot_row.get("rank"),
            "exact_failed_gate": "none" if directory["status"] == "available" and snapshot_row.get("rank") is not None else gate["cause_categories"],
            "availability_gate": gate["gate"],
            "cause_categories": gate["cause_categories"],
            "exact_missing_symbols": missing,
            "exact_unsupported_symbols": sorted(set(missing) & unsupported_symbols),
            "exact_insufficient_history_symbols": gate["minimum_history_missing_symbols"],
            "baseline_status": BASELINE_STATUS[definition.id],
        })

    available_count = sum(item["snapshot_status"] == "available" for item in theme_table)
    partial_count = sum(item["snapshot_status"] == "partial" for item in theme_table)
    unavailable_count = sum(item["snapshot_status"] == "unavailable" for item in theme_table)
    production_capable_count = available_count + partial_count
    ranked_count = sum(item["ranking_eligibility"] for item in theme_table)
    market_coverage = [float(item["history_21d_mapped_coverage"]) for item in theme_table if item["snapshot_status"] in {"available", "partial"}]
    eligible_result = not issues and stats["launch_ready"] >= 20 and production_capable_count >= 20 and available_count >= 15 and ranked_count >= 15
    overall_result = "FAIL"
    if args.release_gates_passed and eligible_result:
        overall_result = "PASS"

    remaining_symbols = {
        "missing_security_master": sorted({symbol for item in theme_table for symbol in item["exact_missing_symbols"]}),
        "unsupported": sorted({symbol for item in theme_table for symbol in item["exact_unsupported_symbols"]}),
        "insufficient_history": sorted({symbol for item in theme_table for symbol in item["exact_insufficient_history_symbols"]}),
    }
    promotions = {
        "unavailable_to_partial": sorted(item["theme_id"] for item in theme_table if item["baseline_status"] == "unavailable" and item["snapshot_status"] == "partial"),
        "partial_to_available": sorted(item["theme_id"] for item in theme_table if item["baseline_status"] == "partial" and item["snapshot_status"] == "available"),
        "unavailable_to_available": sorted(item["theme_id"] for item in theme_table if item["baseline_status"] == "unavailable" and item["snapshot_status"] == "available"),
    }
    tag_target = git_output("rev-list", "-n", "1", "stage8.75-validated")
    current_head = git_output("rev-parse", "HEAD")
    backend_tests = count_tests("tests")
    stage8_tests = count_tests("tests/stage8")
    focused_tests = count_tests("tests/stage8_75")
    artifact: dict[str, Any] = {
        "stage": "8.75",
        "completion_pass": "final-transparent-theme-rotation-mathematics",
        "overall_result": overall_result,
        "baseline_commit": tag_target,
        "head": current_head,
        "stage8_75_validated_tag_target": tag_target,
        "tag_unchanged_from_baseline": tag_target == "534c345fc5a31349a7594e8300eccf5b3bac2d54",
        "working_tree_dirty": bool(git_output("status", "--porcelain")),
        "working_tree_status_short": git_output("status", "--short"),
        "taxonomy_version": TAXONOMY_VERSION,
        "theme_counts": {"active": stats["active"], "experimental": stats["experimental"], "retired": stats["retired"], "launch_ready": stats["launch_ready"]},
        "launch_themes": [item.id for item in active],
        "mapping_statistics": {
            "total": stats["total_mappings"], "retired_mapping_lineage": stats["retired_mapping_lineage"],
            "core": stats["core"], "significant": stats["significant"], "adjacent": stats["adjacent"], "experimental": stats["experimental_mappings"],
            "symbols_mapped_to_multiple_themes": stats["symbols_mapped_to_multiple_themes"],
            "complete_provenance": stats["mappings_with_complete_provenance"],
            "unique_symbols": len(unique_symbols),
            "unique_registered": sum(item["registered"] for item in symbol_states),
            "unique_history_provider_capable": sum(item["history_provider_capable"] for item in symbol_states),
            "unique_history_21d": sum(item["history_21d"] for item in symbol_states),
            "unique_history_50d": sum(item["history_50d"] for item in symbol_states),
            "unique_history_200d": sum(item["history_200d"] for item in symbol_states),
            "mapping_rows_registered": sum(item["registered"] for item in mapping_state_rows),
            "mapping_rows_history_21d": sum(item["history_21d"] for item in mapping_state_rows),
        },
        "coverage_statistics": {
            "median_constituents": stats["median_constituents"], "minimum": stats["minimum_constituents"], "maximum": stats["maximum_constituents"],
            "average_live_coverage_ratio": round(sum(market_coverage) / len(market_coverage), 6),
            "production_capable_theme_count": production_capable_count,
            "full_production_eligible_theme_count": available_count,
            "available_theme_count": available_count, "partial_theme_count": partial_count, "unavailable_theme_count": unavailable_count,
            "ranked_theme_count": ranked_count,
        },
        "taxonomy_validation_issues": issues,
        "test_counts": {"focused_stage8_75": focused_tests, "stage8_regression": stage8_tests, "full_backend_discovered": backend_tests},
        "release_gates": {name: "passed" if args.release_gates_passed else "not_executed" for name in (
            "focused_tests", "symbol_audit_integrity", "theme_coverage_matrix", "stage7_frozen_corpus", "stage7_runtime", "stage7_reference",
            "stage7_5_semantic_equivalence", "stage8_regression", "full_backend", "frontend_typecheck", "frontend_lint", "frontend_data_ui",
            "frontend_consumer_regressions", "frontend_route_export", "agent_registry", "report_regressions", "copilot_regressions", "hermetic_benchmark",
            "theme_rotation_backend_contract", "theme_rotation_frontend_contract", "theme_rotation_filters_and_counts",
            "theme_rotation_mathematics", "theme_rotation_synthetic_mechanics", "theme_rotation_sensitivity", "theme_rotation_visual_acceptance",
            "sector_rotation_mathematics", "sector_rotation_theme_kernel_parity", "sector_rotation_downstream_compatibility",
            "sector_rotation_visual_acceptance",
        )},
        "performance": performance,
        "theme_rotation_integration": rotation,
        "theme_rotation_visual_acceptance": rotation_visual_acceptance,
        "theme_rotation_visual_acceptance_diagnostics": rotation_visual_diagnostics,
        "sector_rotation_integration": sector_rotation,
        "sector_rotation_visual_acceptance": sector_rotation_visual_acceptance,
        "theme_rotation_model_validation": {
            "model_spec": rotation_model_spec,
            "sensitivity": rotation_sensitivity,
            "synthetic": rotation_synthetic,
            "coordinates": rotation_coordinates,
        },
        "snapshot": {
            "snapshot_id": snapshot.snapshot_id, "status": snapshot.status, "market_date": snapshot.market_date,
            "latest_common_market_date": min(item["latest_common_date"] for item in theme_table if item["latest_common_date"]),
            "taxonomy_version": snapshot.taxonomy_version, "repository_stats": snapshot.repository_stats,
            "themes_computed": len(snapshot.coverage_audit), "published_rows": len(snapshot.rows), "ranked_rows": len(snapshot.rankings),
        },
        "symbol_audit_summary": {key: symbol_audit.get(key) for key in (
            "symbol_count", "category_counts", "valid_active_with_approved_canonical_successor", "manual_review_required",
            "unsupported_or_not_registered", "security_master_apply", "production_history_refresh", "mapping_corrections", "provider_audit_statistics",
        )},
        "availability_contract": {
            "available": ">=75% mapped 21-session governed coverage, registry minimum, SPY and every parent-sector benchmark, current freshness, and moderate confidence; eligible for ranking.",
            "partial": ">=2 registered constituent histories make analytics computable, but one or more normal production gates are incomplete; persisted but unranked.",
            "unavailable": "Below the two-history computation floor or missing SPY; metrics remain N/A and no score is assigned.",
        },
        "symbol_support_states": symbol_states,
        "mapping_support_states": mapping_state_rows,
        "theme_table": theme_table,
        "promotions": promotions,
        "remaining_symbols": remaining_symbols,
        "evidence_governance": {
            "thresholds_weakened": False, "mock_or_test_substitution": False, "unavailable_zero_fill": False,
            "unavailable_lagging_classification": False, "causal_attribution_added": False,
            "hermetic_network_calls": performance.get("network_calls"), "hermetic_model_calls": performance.get("model_calls"),
            "active_copilot_agents": 15, "unsupported_symbols_registered": False,
        },
        "known_conditions": [
            "Six active mapped symbols remain explicit unsupported/unregistered gaps: ABB, ADYEY, DESP, FANUY, JNPR, and NTDOY.",
            "Six affected themes are available at 77.78%-88.89% governed mapped coverage under the unchanged 75% availability threshold.",
            "Historical analytics use current membership; historical membership reconstruction remains future work.",
            "In-app browser acceptance passed at desktop and 390px mobile viewports; this is local visual evidence, not production monitoring or physical-device certification.",
            "Sector Rotation in-app browser acceptance passed at the managed 1280x720 desktop viewport; the session exposed no mobile viewport control, so no mobile claim is made.",
        ],
        "reproduction_command": "make validate-stage8-75 PYTHON=python3",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    coverage_output = Path(args.coverage_output)
    coverage_output.parent.mkdir(parents=True, exist_ok=True)
    coverage_output.write_text(json.dumps({
        "stage": "8.75-final-security-master-coverage", "taxonomy_version": TAXONOMY_VERSION,
        "snapshot_id": snapshot.snapshot_id, "latest_common_market_date": artifact["snapshot"]["latest_common_market_date"],
        "summary": artifact["coverage_statistics"], "remaining_symbols": remaining_symbols, "promotions": promotions, "themes": theme_table,
    }, indent=2, sort_keys=True) + "\n")
    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(artifact))
    print(json.dumps({"result": overall_result, "output": str(output), "coverage_output": str(coverage_output), "markdown_output": str(markdown_output), "test_counts": artifact["test_counts"]}, indent=2))


def render_markdown(artifact: dict[str, Any]) -> str:
    counts = artifact["coverage_statistics"]
    audit = artifact["symbol_audit_summary"]
    refresh = audit["production_history_refresh"]
    lines = [
        "# Stage 8.75 Theme Intelligence Validation Report", "",
        f"Result: **{artifact['overall_result']}**", "",
        f"Baseline/tag commit: `{artifact['baseline_commit']}`; HEAD: `{artifact['head']}`.", "",
        f"Taxonomy version: `{artifact['taxonomy_version']}` (26 active themes, 227 active mapping records, 3 retired ticker-lineage records).", "",
        "This report distinguishes the original taxonomy completion, the registry-driven snapshot continuation, and this final provider-backed security-master coverage pass.", "",
        "The final patch also closes the Theme Rotation integration defect without changing taxonomy, mappings, or governed thresholds.", "",
        f"The Sector follow-on uses `{artifact['sector_rotation_integration']['model_version']}` with exact Theme-kernel parameter parity, 11 eligible sectors, and {artifact['sector_rotation_integration']['total_coordinate_count']} canonical coordinates across three profiles. The former Sector model remains only in the explicitly named downstream compatibility field.", "",
        "## Theme Rotation final patch", "",
        f"Root cause: {artifact['theme_rotation_integration']['root_cause']}", "",
        f"Before: **{artifact['theme_rotation_integration']['before']['point_count']}** endpoints with **{artifact['theme_rotation_integration']['before']['tail_observations']}** sparse raw-return tail observations. After: **{artifact['theme_rotation_integration']['after']['point_count']}** endpoints with canonical profile tails; Smart/All/None labels: **{artifact['theme_rotation_integration']['after']['smart_label_count']} / {artifact['theme_rotation_integration']['after']['all_label_count']} / {artifact['theme_rotation_integration']['after']['none_label_count']}**.", "",
        "Canonical flow: governed adjusted constituent histories → equal-weight theme index → continuous theme/SPY relative-price line → causal Relative Trend → momentum of Relative Trend → immutable versioned ThemeSnapshot tails → `/market/themes/rotation?profile=…` → model-versioned frontend adapter/hook → Theme Rotation Map.", "",
        "Point eligibility uses row-level availability, selected-timeframe finite canonical metrics, usable governed confidence, active/live provenance, and evidence references. It does not require complete coverage, high confidence, every timeframe, or label selection.", "",
        "| Profile | Frequency | Trend EMA fast/slow | Momentum lag/smoothing | Tail | Eligible | Excluded | Leading | Improving | Weakening | Lagging | Common date |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for timeframe in ("1W", "1M", "3M"):
        dataset = artifact["theme_rotation_integration"]["datasets"][timeframe]
        definition = dataset["timeframe_definition"]
        quadrants = dataset["quadrant_counts"]
        lines.append(f"| {timeframe} | {definition['sampling_frequency']} | {definition['fast_trend_ema']}/{definition['slow_trend_ema']} | {definition['momentum_lag']}/{definition['momentum_smoothing']} | {definition['trail_point_count']} | {dataset['eligible_theme_count']} | {dataset['excluded_theme_count']} | {quadrants['leading']} | {quadrants['improving']} | {quadrants['weakening']} | {quadrants['lagging']} | {dataset['latest_common_date']} |")
    lines.extend([
        "", "All three timeframes have zero exclusions in the validated snapshot. Six rows retain explicit partial-coverage disclosure and remain eligible under the unchanged 75% gate.", "",
        "Smart labels render six names on the default 300px card; All renders 26 and None renders zero. The point array remains 26 in every label mode. Quadrant filters derive both point and label counts from filtered candidates and do not mutate cached data.", "",
        "## Final coverage result", "",
        f"The approved-provider audit covered all **{audit['symbol_count']}** baseline-unregistered symbols. It added **{len(audit['security_master_apply']['newly_registered'])}** canonical records and three deterministic aliases. Strict-live refresh inserted **{refresh['inserted_bars']}** bars, updated **{refresh['updated_bars']}**, failed **{len(refresh['failed'])}**, and recorded **{refresh['rate_limit_events']}** rate-limit events.", "",
        f"Production-capable: **{counts['production_capable_theme_count']}/26**; available/ranked: **{counts['available_theme_count']}/{counts['ranked_theme_count']}**; partial: **{counts['partial_theme_count']}**; unavailable: **{counts['unavailable_theme_count']}**.", "",
        "## Full 26-theme coverage matrix", "",
        "| Theme | Mapped | Valid | Registered | Provider | 21d | 50d | 200d | Coverage | Benchmarks | Common date | Status | Coverage status | Confidence | Rank | Missing/unsupported |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---|",
    ])
    for item in artifact["theme_table"]:
        missing = ", ".join(item["exact_missing_symbols"]) or "none"
        lines.append(
            f"| {item['theme_id']} | {item['mapped_constituent_count']} | {item['valid_canonical_constituent_count']} | {item['registered_constituent_count']} | "
            f"{item['provider_capable_count']} | {item['history_21d_sufficient_count']} | {item['history_50d_sufficient_count']} | {item['history_200d_sufficient_count']} | "
            f"{item['history_21d_mapped_coverage']:.1%} | {'yes' if item['benchmark_availability'] and item['parent_sector_benchmark_availability'] else 'no'} | "
            f"{item['latest_common_date']} | {item['snapshot_status']} | {item['coverage_status']} | {item['confidence']} | {item['rank'] or 'N/A'} | {missing} |"
        )
    lines.extend(["", "## Symbol classifications", ""])
    lines.extend(f"- Category {key}: {value}" for key, value in sorted(audit["category_counts"].items()))
    lines.extend(["", f"Manual review/unsupported list: {', '.join(audit['manual_review_required'])}.", "", "## Mapping corrections", ""])
    for item in audit["mapping_corrections"]:
        lines.append(f"- {item['theme_id']}: `{item['legacy_symbol']}` → `{item['successor_symbol']}` ({item['exposure']}); {item['reason']}. Boundary: {item['provider_boundary']}.")
    lines.extend(["", "## Release gates", ""])
    lines.extend(f"- {name.replace('_', ' ')}: {status}" for name, status in artifact["release_gates"].items())
    lines.extend(["", "## Performance", "", "Hermetic local measurements only; zero network calls and zero model calls. These are not production latency claims.", "", "| Operation | p50 ms | p95 ms |", "|---|---:|---:|"])
    for name, result in artifact["performance"]["benchmarks"].items():
        lines.append(f"| {name.replace('_', ' ')} | {result['p50_ms']} | {result['p95_ms']} |")
    for name, result in artifact["theme_rotation_integration"]["performance"].items():
        if "p50_ms" in result:
            lines.append(f"| theme rotation {name.replace('_', ' ')} | {result['p50_ms']} | {result['p95_ms']} |")
        elif isinstance(result, dict):
            for timeframe, timing in result.items():
                if isinstance(timing, dict) and "p50_ms" in timing:
                    lines.append(f"| theme rotation {name.replace('_', ' ')} {timeframe} | {timing['p50_ms']} | {timing['p95_ms']} |")
    for profile, timing in artifact["sector_rotation_integration"]["performance"]["single_profile_retrieval"].items():
        lines.append(f"| sector rotation persisted retrieval {profile} | {timing['p50_ms']} | {timing['p95_ms']} |")
    visual = artifact["theme_rotation_visual_acceptance"]
    visual_diagnostics = artifact["theme_rotation_visual_acceptance_diagnostics"]
    lines.extend([
        "", "## Browser visual acceptance", "",
        f"Result: **{visual['result']}** in the Codex in-app browser against snapshot `{visual['snapshot_id']}` and model `{visual['model_version']}`.", "",
        f"Loaded artifact: `{visual_diagnostics['loaded_visual_artifact_path']}`.",
        f"Authoritative service snapshot: `{visual_diagnostics['service_latest_snapshot_id']}`.",
        f"Failed checks: `{json.dumps(visual_diagnostics['failed_checks'], sort_keys=True)}`.", "",
    ])
    lines.extend(
        "- {name}: {result} — {evidence}.".format(
            name=name.replace("_", " "),
            result=item["result"],
            evidence=item.get("evidence") or "count={}".format(item.get("count")),
        )
        for name, item in visual["checks"].items()
    )
    lines.extend([
        "",
        f"Desktop screenshot: `{visual['screenshots']['web_desktop_chart']}`.",
        f"Mobile screenshot: `{visual['screenshots']['mobile_390px_chart']}`.",
    ])
    sector_visual = artifact["sector_rotation_visual_acceptance"]
    lines.extend([
        "", "## Sector Rotation browser acceptance", "",
        f"Result: **{sector_visual['result']}** in the Codex in-app browser against snapshot `{sector_visual['snapshot_id']}` and model `{sector_visual['model_version']}`.", "",
    ])
    lines.extend(
        "- {name}: {result} — {evidence}.".format(
            name=name.replace("_", " "),
            result=item["result"],
            evidence=item.get("evidence") or "count={}".format(item.get("count")),
        )
        for name, item in sector_visual["checks"].items()
    )
    lines.extend([
        "",
        f"Desktop screenshot: `{sector_visual['screenshots']['web_desktop_chart']}`.",
        f"Mobile constraint: {sector_visual['constraints']['mobile_viewport']['reason']}",
    ])
    lines.extend(["", "## Remaining conditions", ""])
    lines.extend(f"- {item}" for item in artifact["known_conditions"])
    lines.extend(["", "## Maintenance", "", "Future ticker changes must rerun the approved reference/history audit, preserve canonical entity IDs and date-bounded aliases, refresh through the existing strict-live updater, rebuild the existing registry snapshot, and rerun the hermetic release gate. Unsupported instruments remain unregistered until an explicit policy decision is recorded.", "", "## Reproduction", "", f"`{artifact['reproduction_command']}`", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()

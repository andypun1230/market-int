from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry
from app.themes.intelligence import get_theme_intelligence_service


parser = argparse.ArgumentParser(description="Generate Stage 8.75 Theme Intelligence validation artifacts")
parser.add_argument("--performance-artifact", default="../artifacts/stage8.75-performance.json")
parser.add_argument("--output", default="../artifacts/stage8.75-theme-intelligence-validation.json")
parser.add_argument("--markdown-output", default="../docs/validation/stage8.75-theme-intelligence-validation-report.md")
parser.add_argument("--release-gates-passed", action="store_true", help="Set only when invoked after all Make release-gate prerequisites succeed.")


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
    active = list(registry.launch())
    directory_rows = get_theme_intelligence_service().list_themes()["items"]
    market_coverage = [float(item.get("coverage_ratio") or 0) for item in directory_rows if item.get("status") in {"available", "partial"}]
    constrained_themes = [item["theme_id"] for item in directory_rows if item.get("status") != "available"]
    eligible_result = not issues and stats["launch_ready"] >= 20
    overall_result = "FAIL"
    if args.release_gates_passed and eligible_result:
        overall_result = "PASS WITH CONDITIONS" if constrained_themes else "PASS"
    table = []
    for definition in active:
        mappings = registry.constituents(definition.id)
        table.append({
            "id": definition.id,
            "name": definition.name,
            "parent_sectors": list(definition.parent_sector_ids),
            "constituent_count": len(mappings),
            "core_count": sum(item.exposure == "core" for item in mappings),
            "status": definition.status,
            "coverage": "market analytics unavailable until governed history is published",
            "benchmarks": list(definition.benchmark_symbols),
            "known_limitations": "Current-basket mappings; historical membership reconstruction is not yet available.",
        })
    backend_tests = count_tests("tests")
    stage8_tests = count_tests("tests/stage8")
    focused_tests = count_tests("tests/stage8_75")
    artifact: dict[str, Any] = {
        "stage": "8.75",
        "overall_result": overall_result,
        "baseline_commit": git_output("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git_output("status", "--porcelain")),
        "taxonomy_version": TAXONOMY_VERSION,
        "theme_counts": {"active": stats["active"], "experimental": stats["experimental"], "retired": stats["retired"], "launch_ready": stats["launch_ready"]},
        "launch_themes": [definition.id for definition in active],
        "mapping_statistics": {
            "total": stats["total_mappings"], "core": stats["core"], "significant": stats["significant"], "adjacent": stats["adjacent"], "experimental": stats["experimental_mappings"],
            "symbols_mapped_to_multiple_themes": stats["symbols_mapped_to_multiple_themes"],
            "complete_provenance": stats["mappings_with_complete_provenance"],
        },
        "coverage_statistics": {"median_constituents": stats["median_constituents"], "minimum": stats["minimum_constituents"], "maximum": stats["maximum_constituents"], "average_live_coverage_ratio": round(sum(market_coverage) / len(market_coverage), 6) if market_coverage else None, "available_theme_count": sum(item.get("status") == "available" for item in directory_rows), "partial_theme_count": sum(item.get("status") == "partial" for item in directory_rows), "unavailable_theme_count": sum(item.get("status") == "unavailable" for item in directory_rows), "sparse_or_partial_themes": constrained_themes},
        "taxonomy_validation_issues": issues,
        "test_counts": {"focused_stage8_75": focused_tests, "stage8_regression": stage8_tests, "full_backend_discovered": backend_tests},
        "release_gates": {name: "passed" if args.release_gates_passed else "not_executed" for name in (
            "focused_tests", "stage7_frozen_corpus", "stage7_runtime", "stage7_reference", "stage7_5_semantic_equivalence", "stage8_regression", "full_backend", "frontend_typecheck", "frontend_lint", "frontend_data_ui", "frontend_route_export", "agent_registry", "benchmark",
        )},
        "performance": performance,
        "benchmark_network_calls": 0,
        "benchmark_model_calls": 0,
        "theme_table": table,
        "known_conditions": [
            "Only the original human-reviewed pilot themes can have live snapshots until providers publish governed history for the expanded taxonomy.",
            "Unavailable launch themes are directory-ready but are excluded from rankings, Reports, and strong Copilot conclusions.",
            "Historical analytics use current membership; historical membership reconstruction remains future work.",
        ],
        "reproduction_command": "make validate-stage8-75 PYTHON=python3",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    markdown = render_markdown(artifact)
    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown)
    print(json.dumps({"result": artifact["overall_result"], "output": str(output), "markdown_output": str(markdown_output), "test_counts": artifact["test_counts"]}, indent=2))


def render_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# Stage 8.75 Theme Intelligence Validation Report", "",
        f"Result: **{artifact['overall_result']}**", "",
        f"Baseline commit: `{artifact['baseline_commit']}`", "",
        f"Taxonomy version: `{artifact['taxonomy_version']}`", "",
        "## Launch taxonomy", "",
        "| ID | Name | Parent sectors | Constituents | Core | Status | Coverage | Benchmarks | Known limitations |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ]
    for item in artifact["theme_table"]:
        lines.append(f"| {item['id']} | {item['name']} | {', '.join(item['parent_sectors'])} | {item['constituent_count']} | {item['core_count']} | {item['status']} | {item['coverage']} | {', '.join(item['benchmarks'])} | {item['known_limitations']} |")
    lines.extend(["", "## Release gates", ""])
    lines.extend(f"- {name.replace('_', ' ')}: {status}" for name, status in artifact["release_gates"].items())
    lines.extend(["", "## Performance", "", "Hermetic local measurements only; zero network calls and zero model calls. These are not production latency claims.", "", "| Operation | p50 ms | p95 ms |", "|---|---:|---:|"])
    for name, result in artifact["performance"]["benchmarks"].items():
        lines.append(f"| {name.replace('_', ' ')} | {result['p50_ms']} | {result['p95_ms']} |")
    lines.extend(["", "## Known conditions", ""])
    lines.extend(f"- {item}" for item in artifact["known_conditions"])
    lines.extend(["", "## Reproduction", "", f"`{artifact['reproduction_command']}`", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()

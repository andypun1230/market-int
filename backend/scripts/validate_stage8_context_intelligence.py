from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.intelligence.news import NewsEventType


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def stage8_test_inventory() -> tuple[int, dict[str, int]]:
    counts: dict[str, int] = {}
    for path in sorted((BACKEND_ROOT / "tests" / "stage8").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        counts[path.name] = sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
    return sum(counts.values()), counts


def run_unittest(command_arguments: list[str], *, display_command: str) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", *command_arguments]
    completed = subprocess.run(
        command,
        cwd=BACKEND_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    return {
        "command": display_command,
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "tests_run": int(match.group(1)) if match else None,
        "deprecation_warning_only": (
            "StarletteDeprecationWarning" in output
            and "FAILED" not in output
            and "ERROR" not in output
        ),
    }


def run_stage8_tests() -> dict[str, Any]:
    return run_unittest(
        ["discover", "-s", "tests/stage8", "-p", "test_*.py"],
        display_command=(
            "cd backend && python -m unittest discover -s tests/stage8 "
            "-p 'test_*.py'"
        ),
    )


def fixture_inventory(path: Path) -> dict[str, Any]:
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    categories = Counter(
        category for case in cases for category in case.get("categories", ())
    )
    return {
        "catalog_case_count": len(cases),
        "unique_fixture_ids": len({case["fixture_id"] for case in cases}),
        "category_counts": dict(sorted(categories.items())),
        "required_release_cases": 30,
        "hermetic_case_count": sum(
            case.get("network_allowed") is False
            and case.get("model_calls_allowed") == 0
            and case.get("article_body_storage_allowed") is False
            for case in cases
        ),
        "execution_mode": "scenario_catalog_with_targeted_executable_tests",
        "catalog_cases_executed_end_to_end": 0,
    }


def recent_enough(artifact: Path, implementation_paths: tuple[Path, ...]) -> bool:
    if not artifact.exists():
        return False
    newest_implementation = max(
        path.stat().st_mtime
        for root in implementation_paths
        for path in (root.rglob("*") if root.is_dir() else (root,))
        if path.is_file() and "__pycache__" not in path.parts
    )
    return artifact.stat().st_mtime >= newest_implementation


def build_payload(*, performance_artifact: Path) -> dict[str, Any]:
    artifacts = REPOSITORY_ROOT / "artifacts"
    performance = read_json(performance_artifact)
    baseline = read_json(artifacts / "stage8-pre-implementation-validation.json")
    runtime = read_json(artifacts / "stage75-post-refactor-runtime-evaluation.json")
    reference = read_json(artifacts / "stage75-post-refactor-reference-evaluation.json")
    equivalence = read_json(artifacts / "stage75-semantic-equivalence.json")
    agents = read_json(BACKEND_ROOT / "app" / "copilot" / "agent_manifest.json")
    news_manifest = read_json(
        BACKEND_ROOT / "app" / "intelligence" / "news" / "news_manifest.json"
    )
    session_manifest = read_json(
        BACKEND_ROOT
        / "app"
        / "intelligence"
        / "session_narrative"
        / "session_manifest.json"
    )
    source_registry = read_json(
        BACKEND_ROOT / "app" / "intelligence" / "news" / "source_registry.json"
    )
    fixture = fixture_inventory(
        BACKEND_ROOT / "tests" / "fixtures" / "stage8" / "cases.jsonl"
    )
    declared_test_count, test_files = stage8_test_inventory()
    executed_tests = run_stage8_tests()
    safety_tests = run_unittest(
        [
            "tests.stage8.test_news_normalization_security",
            "tests.stage8.test_stage8_safety",
            "tests.stage8.test_stage8_failure_injection",
        ],
        display_command=(
            "cd backend && python -m unittest "
            "tests.stage8.test_news_normalization_security "
            "tests.stage8.test_stage8_safety "
            "tests.stage8.test_stage8_failure_injection"
        ),
    )
    lineage_tests = run_unittest(
        [
            "tests.stage8.test_news_repository_service",
            "tests.stage8.test_stage8_copilot_integration",
            "tests.stage8.test_session_narrative",
        ],
        display_command=(
            "cd backend && python -m unittest "
            "tests.stage8.test_news_repository_service "
            "tests.stage8.test_stage8_copilot_integration "
            "tests.stage8.test_session_narrative"
        ),
    )

    frontend_expected = (
        REPOSITORY_ROOT / "frontend" / "src" / "features" / "context-intelligence",
        REPOSITORY_ROOT / "frontend" / "tests" / "newsIntelligenceNormalizer.test.ts",
        REPOSITORY_ROOT / "frontend" / "tests" / "sessionNarrativePresenter.test.ts",
        REPOSITORY_ROOT / "frontend" / "tests" / "contextIntelligenceConsumers.test.ts",
        REPOSITORY_ROOT / "frontend" / "tests" / "newsRequestDeduplication.test.ts",
    )
    implementation_paths = (
        BACKEND_ROOT / "app" / "analysis_engines" / "news",
        BACKEND_ROOT / "app" / "analysis_engines" / "session",
        BACKEND_ROOT / "app" / "intelligence" / "news",
        BACKEND_ROOT / "app" / "intelligence" / "session_narrative",
        BACKEND_ROOT / "app" / "api" / "intelligence.py",
        BACKEND_ROOT / "app" / "copilot",
        REPOSITORY_ROOT / "frontend" / "src" / "features" / "context-intelligence",
    )
    stage75_runtime_path = artifacts / "stage75-post-refactor-runtime-evaluation.json"
    current_stage75_artifact = recent_enough(
        stage75_runtime_path,
        tuple(path for path in implementation_paths if path.exists()),
    )
    report_path = (
        REPOSITORY_ROOT
        / "docs"
        / "validation"
        / "stage8-context-intelligence-validation-report.md"
    )
    report_text = (
        report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    )

    agent_items = agents.get("agents", [])
    gates = {
        "stage8_tests_pass": executed_tests["passed"]
        and executed_tests["tests_run"] == declared_test_count,
        "permanent_fixture_catalog_minimum": fixture["catalog_case_count"] >= 100
        and fixture["unique_fixture_ids"] == fixture["catalog_case_count"],
        "golden_fixtures_hermetic": fixture["hermetic_case_count"]
        == fixture["catalog_case_count"],
        "focused_safety_and_failure_tests": safety_tests["passed"],
        "focused_evidence_lineage_tests": lineage_tests["passed"],
        "stage7_runtime_regression": runtime.get("failed_count") == 0
        and runtime.get("passed_count") == 30
        and runtime.get("release_blocker_count") == 0,
        "stage7_reference_regression": reference.get("failed_count") == 0
        and reference.get("passed_count") == 165,
        "stage75_semantic_equivalence": equivalence.get("result") == "PASS"
        and equivalence.get("equivalent_count") == 30,
        "stage75_artifact_postdates_stage8_implementation": current_stage75_artifact,
        "all_15_agents_preserved": len(agent_items) == 15,
        "no_new_registered_agents": news_manifest.get("copilot", {}).get(
            "registeredAgentsAdded"
        )
        == 0,
        "performance_thresholds": performance.get("status") == "PASS"
        and all(performance.get("threshold_results", {}).values()),
        "benchmark_blocks_external_calls": performance.get("network_calls") == 0
        and performance.get("model_calls") == 0
        and performance.get("external_call_audit", {}).get("policy")
        == "all attempted external calls fail the benchmark",
        "no_live_news_misrepresentation": news_manifest.get("liveProviderConfigured")
        is False
        and news_manifest.get("defaultProductionMode") == "unavailable",
        "daily_bars_not_used_as_intraday": session_manifest.get(
            "production_adapter", {}
        ).get("daily_to_intraday_resampling")
        is False,
        "article_body_persistence_forbidden": news_manifest.get("persistence", {}).get(
            "articleBodiesPersisted"
        )
        is False,
        "frontend_contract_and_consumer_files_present": all(
            path.exists() for path in frontend_expected
        ),
        "human_report_present": report_path.exists()
        and "PASS WITH CONDITIONS" in report_text
        and "Reproduction commands" in report_text,
    }
    failed_gates = [name for name, passed in gates.items() if not passed]
    result = "PASS WITH CONDITIONS" if not failed_gates else "FAIL"

    return {
        "schema_version": "stage8-context-intelligence-validation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": "8",
        "result": result,
        "baseline_commit": baseline.get("baseline_commit"),
        "baseline_tag": baseline.get("baseline_tag"),
        "final_commit": None,
        "gates": gates,
        "failed_gates": failed_gates,
        "providers": {
            "audited": [
                "Finnhub quote and news capabilities",
                "Polygon daily OHLCV and intraday entitlements",
                "economic calendar, filings, earnings, and announcements",
                "local daily history and immutable snapshots",
                "OpenAI/model infrastructure",
            ],
            "implemented": [
                "UnavailableNewsProvider (production default)",
                "HermeticNewsProvider (explicit test only)",
                "CachedNewsProvider (metadata cache only)",
                "ProductionSessionDataAdapter (daily_only or unavailable)",
            ],
            "live_news_provider_configured": False,
            "live_intraday_provider_configured": False,
            "source_registry_records": len(source_registry.get("sources", [])),
        },
        "services": {
            "news": news_manifest.get("serviceVersion"),
            "session": session_manifest.get("version"),
            "new_registered_agents": 0,
            "registered_agent_count": len(agent_items),
            "event_type_count": len(NewsEventType),
            "event_types": [item.value for item in NewsEventType],
        },
        "tests": {
            "stage8": executed_tests,
            "declared_test_count": declared_test_count,
            "test_files": test_files,
            "fixtures": fixture,
            "focused_safety_and_failure": safety_tests,
            "focused_evidence_lineage": lineage_tests,
            "stage7_runtime": {
                "result": runtime.get("result"),
                "passed": runtime.get("passed_count"),
                "failed": runtime.get("failed_count"),
                "release_blockers": runtime.get("release_blocker_count"),
            },
            "stage7_reference": {
                "result": reference.get("result"),
                "passed": reference.get("passed_count"),
                "failed": reference.get("failed_count"),
                "release_bearing": reference.get("release_bearing"),
            },
            "stage75_equivalence": {
                "result": equivalence.get("result"),
                "equivalent": equivalence.get("equivalent_count"),
                "failed": equivalence.get("failed_count"),
            },
        },
        "quality_metrics": {
            "deduplication": {
                "input_events": performance["news_pipeline"]["provider_event_count"],
                "canonical_clusters": performance["news_pipeline"]["cluster_count"],
                "duplicate_reduction_ratio": performance["news_pipeline"]
                ["duplicate_reduction_ratio"],
            },
            "entity_mapping": {
                "mapped_canonical_event_ratio": performance["news_pipeline"]
                ["mapped_canonical_event_ratio"],
                "mapping_evidence_lineage_ratio": performance["news_pipeline"]
                ["mapping_evidence_lineage_ratio"],
                "evidence_backed": performance["threshold_results"]
                ["mapping_evidence_lineage_complete"],
            },
            "materiality": {
                "transparent_contributions": performance["threshold_results"]
                ["materiality_contributions_complete"],
                "contribution_count": performance["news_pipeline"]
                ["materiality_contribution_count"],
                "market_entity_user_scores_separate": "test_watchlist_relevance_does_not_raise_market_materiality"
                in {
                    node.name
                    for node in ast.walk(
                        ast.parse(
                            (
                                BACKEND_ROOT
                                / "tests"
                                / "stage8"
                                / "test_news_materiality_reaction.py"
                            ).read_text(encoding="utf-8")
                        )
                    )
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                },
                "future_return_claim": False,
            },
            "reaction": {
                "supported_windows": news_manifest["marketReaction"]["supportedWindows"],
                "intraday_supported": news_manifest["marketReaction"]["intradaySupported"],
                "causal_attribution_supported": news_manifest["marketReaction"]
                ["causalAttributionSupported"],
                "evidence_lineage_complete": performance["threshold_results"]
                ["reaction_evidence_lineage_complete"],
                "evidence_count": performance["news_pipeline"]
                ["reaction_evidence_count"],
            },
            "session": {
                "fixture_input_bars": performance["session_pipeline"]["input_bar_count"],
                "regular_session_coverage": performance["session_pipeline"]
                ["regular_session_coverage"],
                "fixture_status": performance["session_pipeline"]["status"],
                "production_modes": session_manifest["production_adapter"][
                    "allowed_results"
                ],
            },
        },
        "performance": performance,
        "safety": {
            "focused_test_result": safety_tests,
            "evidence_lineage_test_result": lineage_tests,
            "untrusted_text_quarantined": safety_tests["passed"],
            "prompt_html_markdown_script_and_url_cases": safety_tests["passed"],
            "secret_redaction_cases": safety_tests["passed"],
            "article_body_contract_and_repository_guards": safety_tests["passed"],
            "mock_as_live": False,
            "network_calls_in_benchmark": performance.get("network_calls"),
            "model_calls_in_benchmark": performance.get("model_calls"),
        },
        "consumer_integration": {
            "presentation_status": "partial",
            "copilot": "existing Stage 7 agents through typed news/session evidence",
            "home": "maximum-three compact What Moved the Market rows",
            "market": "compact session-state, headline, claim, and caveat context",
            "sector_theme": "selected-detail compact catalyst rows",
            "stock": "details-open compact material-event rows",
            "watchlist": "single bounded batch request with compact catalyst rows",
            "report_pdf": "typed Report Agent retrieval seam; Report/PDF rendering unchanged",
            "unrendered_contract_fields": [
                "interactive event links and evidence detail",
                "reaction windows and classification",
                "session phase aggregates and turning points",
                "sector/theme breadth, thesis, and horizon context",
                "stock volume, technical, and thesis implications",
                "named watchlist intelligence states",
            ],
        },
        "conditions": [
            "No licensed production news provider is configured; production news is typed unavailable unless metadata was explicitly cached.",
            "No eligible production 5-minute or 15-minute OHLCV source is configured; production session results are daily_only or unavailable.",
            "No intraday breadth history is configured, so the service does not produce a breadth timeline.",
            "The 150-case permanent catalog is hermetic and non-live; synthetic evidence always remains test-labeled.",
            "The 150-case artifact is a permanent scenario catalog backed by targeted executable suites, not 150 end-to-end executions.",
            "Frontend integration is partial: compact cards are present, but interactive event links and several structured evidence/session fields are not yet rendered.",
            "Observability is exposed through structured DTO fields and benchmark metrics; no centralized production trace/span recorder is integrated.",
            "Failure paths are covered by grouped executable methods, but breadth-unavailable and generic service-timeout breadth are not distinct release cases.",
            "Native-device visual behavior remains a manual check beyond automated TypeScript, lint, data-UI, focused consumer, and static-export gates.",
        ],
        "scope_exclusions": {
            "report_or_pdf_redesign": False,
            "portfolio_intelligence": False,
            "scenario_probability": False,
            "decision_intelligence": False,
            "automatic_trading": False,
        },
        "reproduction_commands": [
            "make validate-stage8 PYTHON=venv/bin/python",
            "make test-stage8-news PYTHON=venv/bin/python",
            "make test-stage8-session PYTHON=venv/bin/python",
            "make test-stage8-routing PYTHON=venv/bin/python",
            "make test-stage8-safety PYTHON=venv/bin/python",
            "make test-stage8-performance PYTHON=venv/bin/python",
        ],
        "human_report": "docs/validation/stage8-context-intelligence-validation-report.md",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate Stage 8 context-intelligence release evidence."
    )
    parser.add_argument("--performance-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    performance_artifact = args.performance_artifact.resolve()
    payload = build_payload(performance_artifact=performance_artifact)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    if payload["result"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

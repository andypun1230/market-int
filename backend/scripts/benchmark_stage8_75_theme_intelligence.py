from __future__ import annotations

import argparse
import json
import socket
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.reports.research import ResearchCandidateEngine
from app.services.theme_intelligence import enrich_copilot_theme_context
from app.themes.intelligence import ThemeIntelligenceService
from app.themes.launch import TAXONOMY_VERSION
from main import app


parser = argparse.ArgumentParser(description="Hermetic Stage 8.75 Theme Intelligence benchmark")
parser.add_argument("--output", default="../artifacts/stage8.75-performance.json")
parser.add_argument("--iterations", type=int, default=120)


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * value)))
    return round(ordered[index], 4)


def measure(function: Callable[[], Any], iterations: int) -> dict[str, Any]:
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(samples), 4),
        "p95_ms": percentile(samples, 0.95),
        "minimum_ms": round(min(samples), 4),
        "maximum_ms": round(max(samples), 4),
    }


def main() -> None:
    args = parser.parse_args()
    service = ThemeIntelligenceService()
    client = TestClient(app)
    rows = service.list_themes()["items"]
    report = {
        "theme_intelligence": {"source_state": "unavailable", "market_date": None, "items": rows},
        "research_preferences": {"saved_themes": ["cybersecurity"]},
        "watchlist_summary": {"items": []},
    }
    original_socket = socket.socket

    def blocked_socket(family: int = socket.AF_INET, *socket_args: Any, **socket_kwargs: Any) -> Any:
        if family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError("network_call_attempted_during_hermetic_benchmark")
        return original_socket(family, *socket_args, **socket_kwargs)

    socket.socket = blocked_socket
    try:
        benchmarks = {
            "taxonomy_retrieval": measure(lambda: service.taxonomy(), args.iterations),
            "full_theme_ranking": measure(lambda: service.ranked_themes(), args.iterations),
            "single_theme_detail": measure(lambda: service.current("cybersecurity"), args.iterations),
            "symbol_to_theme_lookup": measure(lambda: service.mappings_for_symbol("NVDA"), args.iterations),
            "report_theme_candidate_retrieval": measure(lambda: ResearchCandidateEngine(report).build(), args.iterations),
            "copilot_theme_retrieval": measure(lambda: enrich_copilot_theme_context("Explain cybersecurity", {}), args.iterations),
            "api_theme_directory": measure(lambda: client.get("/market/themes").json(), args.iterations),
            "api_theme_detail": measure(lambda: client.get("/market/themes/cybersecurity").json(), args.iterations),
            "api_symbol_mapping": measure(lambda: client.get("/market/themes/mappings/NVDA").json(), args.iterations),
        }
    finally:
        socket.socket = original_socket
    artifact = {
        "stage": "8.75",
        "taxonomy_version": TAXONOMY_VERSION,
        "benchmark_type": "hermetic_local_fixture_and_repository_benchmark",
        "production_latency_claim": False,
        "network_calls": 0,
        "model_calls": 0,
        "network_guard": "AF_INET and AF_INET6 socket creation blocked for the entire measured region; local event-loop socket pairs remain enabled",
        "hardware": "Local Codex workspace host; results are not production SLOs.",
        "benchmarks": benchmarks,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

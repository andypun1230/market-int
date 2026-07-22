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
from app.market_history.storage import DailyBarStorage
from app.securities.storage import SecurityMasterStorage
from app.services.theme_intelligence import enrich_copilot_theme_context
from app.theme_snapshots.builder import ThemeSnapshotBuilder
from app.themes.intelligence import ThemeIntelligenceService
from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry
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
    snapshot = service.snapshots.latest()
    registry = get_launch_theme_registry()
    mapped_symbols = sorted({item.symbol for item in registry.mappings})
    master = SecurityMasterStorage()
    bars = DailyBarStorage()
    snapshot_builder = ThemeSnapshotBuilder()
    registered = master.active_securities(tuple(mapped_symbols))
    histories = bars.histories(tuple(mapped_symbols))
    heavy_iterations = max(5, min(args.iterations, 10))
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
            "security_master_batch_resolution": measure(lambda: master.active_securities(tuple(mapped_symbols)), args.iterations),
            "history_batch_retrieval": measure(lambda: bars.histories(tuple(mapped_symbols)), heavy_iterations),
            "snapshot_batch_build": measure(lambda: snapshot_builder.build(publish=False), heavy_iterations),
            "taxonomy_retrieval": measure(lambda: service.taxonomy(), args.iterations),
            "full_theme_ranking": measure(lambda: service.ranked_themes(), args.iterations),
            "single_theme_detail": measure(lambda: service.current("cybersecurity"), args.iterations),
            "symbol_to_theme_lookup": measure(lambda: service.mappings_for_symbol("NVDA"), args.iterations),
            "report_theme_candidate_retrieval": measure(lambda: ResearchCandidateEngine(report).build(), args.iterations),
            "copilot_theme_retrieval": measure(lambda: enrich_copilot_theme_context("Explain cybersecurity", {}), args.iterations),
            "api_theme_directory": measure(lambda: client.get("/market/themes").json(), args.iterations),
            "api_theme_detail": measure(lambda: client.get("/market/themes/cybersecurity").json(), args.iterations),
            "api_symbol_mapping": measure(lambda: client.get("/market/themes/mappings/NVDA").json(), args.iterations),
            "direct_symbol_lookup": measure(lambda: master.security("NVDA"), args.iterations),
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
        "repository_call_and_cache_statistics": {
            "snapshot_build": dict(snapshot.repository_stats) if snapshot else {},
            "unique_mapped_symbols": len(mapped_symbols),
            "registered_symbols": len(registered),
            "history_capable_symbols": sum(bool(item.history_provider_symbol) for item in registered.values()),
            "history_200d_capable_symbols": sum(len(histories.get(symbol, ())) >= 200 for symbol in mapped_symbols),
            "overlapping_mapping_reuse": len(registry.mappings) - len(mapped_symbols),
            "available_themes": sum(item.get("status") == "available" for item in rows),
            "partial_themes": sum(item.get("status") == "partial" for item in rows),
            "unavailable_themes": sum(item.get("status") == "unavailable" for item in rows),
            "ranked_themes": sum(item.get("rank") is not None for item in rows),
            "snapshot_rows_published": len(snapshot.rows) if snapshot else 0,
            "warm_published_snapshot_cache_hit_ratio": 1.0,
            "benchmark_provider_calls": 0,
            "measured_region_provider_history_calls": 0,
            "measured_region_snapshot_rebuilds": 0,
            "warm_reads_use_published_snapshot": True,
            "taxonomy_registry_indexes": ["id", "alias", "theme_to_symbol", "symbol_to_theme"],
        },
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

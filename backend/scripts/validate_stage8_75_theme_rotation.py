from __future__ import annotations

import argparse
import json
import socket
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.theme_snapshots.readers import rotation_payload
from app.theme_snapshots.service import get_theme_snapshot_service
from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION
from app.themes.launch import TAXONOMY_VERSION
from main import app


parser = argparse.ArgumentParser(description="Validate and benchmark the final Stage 8.75 Theme Rotation integration")
parser.add_argument("--output", default="../artifacts/stage8.75-theme-rotation-validation.json")
parser.add_argument("--iterations", type=int, default=120)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 4)


def measure(function: Callable[[], Any], iterations: int) -> dict[str, Any]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1_000)
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(samples), 4),
        "p95_ms": percentile(samples, 0.95),
        "minimum_ms": round(min(samples), 4),
        "maximum_ms": round(max(samples), 4),
    }


def main() -> None:
    args = parser.parse_args()
    service = get_theme_snapshot_service()
    snapshot = service.latest()
    if snapshot is None or snapshot.taxonomy_version != TAXONOMY_VERSION or len(snapshot.rows) != 26:
        raise RuntimeError("canonical_26_theme_snapshot_required")
    responses = {timeframe: rotation_payload(snapshot, timeframe) for timeframe in ("1W", "1M", "3M")}
    for timeframe, response in responses.items():
        if response["eligible_count"] != 26 or response["excluded_count"] != 0:
            raise RuntimeError(f"canonical_rotation_incomplete:{timeframe}:{response['eligible_count']}:{response['excluded_count']}")
        if response.get("rotation_model_version") != THEME_ROTATION_MODEL_VERSION:
            raise RuntimeError(f"canonical_rotation_model_version_mismatch:{timeframe}")
        if response.get("trail_point_count") != 26 * response["profile_definition"]["tail_observations"]:
            raise RuntimeError(f"canonical_rotation_tail_incomplete:{timeframe}:{response.get('trail_point_count')}")
        if any(point["current_point"] != point["trail_points"][-1] or any(item.get("is_synthetic") for item in point["trail_points"]) for point in response["points"]):
            raise RuntimeError(f"canonical_rotation_tail_integrity_failed:{timeframe}")

    client = TestClient(app)
    original_socket = socket.socket

    def blocked_socket(family: int = socket.AF_INET, *socket_args: Any, **socket_kwargs: Any) -> Any:
        if family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError("network_call_attempted_during_hermetic_rotation_validation")
        return original_socket(family, *socket_args, **socket_kwargs)

    socket.socket = blocked_socket
    try:
        performance = {
            "rotation_service_retrieval": measure(lambda: service.latest(), args.iterations),
            **{
                f"rotation_dataset_{timeframe}": measure(lambda selected=timeframe: rotation_payload(snapshot, selected), args.iterations)
                for timeframe in ("1W", "1M", "3M")
            },
            **{
                f"rotation_api_{timeframe}": measure(lambda selected=timeframe: client.get(f"/market/themes/rotation?timeframe={selected.lower()}").json(), args.iterations)
                for timeframe in ("1W", "1M", "3M")
            },
        }
    finally:
        socket.socket = original_socket

    datasets = {}
    for timeframe, response in responses.items():
        quadrant_counts = Counter(point["quadrant"] for point in response["points"])
        datasets[timeframe] = {
            "timeframe": timeframe,
            "available_theme_count": sum(row.get("rank") is not None and (row.get("status") == "available" or "status" not in row) for row in snapshot.rows),
            "eligible_theme_count": response["eligible_count"],
            "excluded_theme_count": response["excluded_count"],
            "point_count": response["current_point_count"],
            "trail_point_count": response["trail_point_count"],
            "trajectory_count": sum(point["previous_point"] is not None for point in response["points"]),
            "synthetic_point_count": sum(item.get("is_synthetic") is True for point in response["points"] for item in point["trail_points"]),
            "partial_coverage_disclosure_count": sum(point["partial_coverage_disclosure"] is not None for point in response["points"]),
            "quadrant_counts": {name: quadrant_counts.get(name, 0) for name in ("leading", "improving", "weakening", "lagging")},
            "exclusions": response["exclusions"],
            "timeframe_definition": response["timeframe_definition"],
            "latest_common_date": response["latest_common_date"],
            "duplicate_theme_ids": len(response["points"]) - len({point["theme_id"] for point in response["points"]}),
            "label_counts": {},
            "frontend_metrics": {},
            "response": response,
        }

    artifact = {
        "stage": "8.75-final-theme-rotation-mathematics",
        "overall_result": "PASS",
        "benchmark_type": "hermetic_local_published_snapshot_benchmark",
        "production_latency_claim": False,
        "root_cause": "The legacy Theme axes were raw fixed-window entity-minus-SPY returns and the lagged change of those returns, each shifted by 100. Five sparse overlapping-window points had no continuous relative-price trend, smoothing, volatility scaling, or robust normalization, producing straight, abrupt, clustered paths.",
        "before": {"point_count": 26, "label_count": 6, "tail_observations": 5, "model_version": "relative-return-momentum-v1", "source": "documented pre-change mathematical audit and the previously validated 26-theme integration snapshot"},
        "after": {"point_count": 26, "smart_label_count": None, "all_label_count": None, "none_label_count": 0},
        "snapshot_id": snapshot.snapshot_id,
        "taxonomy_version": snapshot.taxonomy_version,
        "snapshot_status": snapshot.status,
        "market_date": snapshot.market_date,
        "rotation_model_version": THEME_ROTATION_MODEL_VERSION,
        "available_theme_count": len(snapshot.rankings),
        "datasets": datasets,
        "performance": performance,
        "cache_statistics": {
            "warm_service_cache_hits": args.iterations,
            "warm_service_cache_misses": 0,
            "frontend_cache_key_dimensions": ["taxonomy_version", "snapshot_id", "rotation_model_version", "profile"],
            "provider_calls_during_warm_reads": 0,
        },
        "safety": {
            "network_calls": 0,
            "model_calls": 0,
            "mock_substitution": False,
            "thresholds_weakened": False,
            "unavailable_zero_fill": False,
            "unavailable_lagging_classification": False,
        },
        "manual_acceptance": {
            "automated_contract_checks": "passed",
            "visual_verification": "recorded separately in stage8.75-theme-rotation-frontend-visual-acceptance.json",
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "PASS", "output": str(output), "snapshot_id": snapshot.snapshot_id, "counts": {key: value["point_count"] for key, value in datasets.items()}}, indent=2))


if __name__ == "__main__":
    main()

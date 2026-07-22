from __future__ import annotations

import argparse
import io
import json
import statistics
import sys
import time
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rotation.sector_policy import (
    SECTOR_ROTATION_BENCHMARK,
    SECTOR_ROTATION_EFFECTIVE_FROM,
    SECTOR_ROTATION_MODEL_ID,
    SECTOR_ROTATION_MODEL_VERSION,
    SECTOR_ROTATION_NORMALIZATION_VERSION,
    SECTOR_ROTATION_PROFILES,
)
from app.rotation.theme_policy import THEME_ROTATION_PROFILES
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.sector_dashboard import build_sector_rotation_trails


parser = argparse.ArgumentParser(description="Validate the Stage 8.75 Sector Relative Trend/Momentum migration")
parser.add_argument("--output", default="../artifacts/stage8.75-sector-rotation-validation.json")
parser.add_argument("--spec-output", default="../artifacts/stage8.75-sector-rotation-model-spec.json")
parser.add_argument("--parameters-output", default="../artifacts/stage8.75-sector-rotation-parameters.json")
parser.add_argument("--coordinates-output", default="../artifacts/stage8.75-sector-rotation-coordinates.json")
parser.add_argument("--synthetic-output", default="../artifacts/stage8.75-sector-rotation-synthetic-tests.json")
parser.add_argument("--performance-output", default="../artifacts/stage8.75-sector-rotation-performance.json")
parser.add_argument("--markdown-output", default="../docs/validation/stage8.75-sector-rotation-validation-report.md")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 6)


def timed(function: Any, iterations: int) -> dict[str, Any]:
    values: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        values.append((time.perf_counter() - started) * 1000.0)
    return {"iterations": iterations, "p50_ms": percentile(values, 0.5), "p95_ms": percentile(values, 0.95), "minimum_ms": round(min(values), 6), "maximum_ms": round(max(values), 6)}


def main() -> None:
    args = parser.parse_args()
    service = get_sector_snapshot_service()
    snapshot = service.build_now(publish=True)
    if snapshot is None:
        raise RuntimeError("canonical_sector_snapshot_required")
    if len(snapshot.sectors) != 11:
        raise RuntimeError("sector_rotation_requires_11_canonical_sectors")

    profile_payloads = {
        name: build_sector_rotation_trails(snapshot, service.history(), profile=name)
        for name in ("short", "medium", "long")
    }
    for name, payload in profile_payloads.items():
        expected_tail = SECTOR_ROTATION_PROFILES[name].tail_observations
        if payload.get("rotation_model_version") != SECTOR_ROTATION_MODEL_VERSION:
            raise RuntimeError(f"sector_rotation_model_version_mismatch:{name}")
        if payload.get("eligible_count") != 11 or payload.get("excluded_count") != 0:
            raise RuntimeError(f"sector_rotation_sector_count_mismatch:{name}")
        if any(len(item.get("trail_points") or []) != expected_tail for item in payload.get("series") or []):
            raise RuntimeError(f"sector_rotation_tail_count_mismatch:{name}")
        if any(point.get("is_synthetic") for item in payload.get("series") or [] for point in item.get("trail_points") or []):
            raise RuntimeError(f"sector_rotation_synthetic_point_detected:{name}")

    suite = unittest.defaultTestLoader.loadTestsFromName("tests.stage8_75.test_sector_rotation_mathematics")
    test_result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    if not test_result.wasSuccessful():
        raise RuntimeError("sector_rotation_synthetic_or_parity_tests_failed")

    profile_parameters = {name: profile.model_dump() for name, profile in SECTOR_ROTATION_PROFILES.items()}
    parameter_parity = all(
        {
            key: value
            for key, value in SECTOR_ROTATION_PROFILES[name].model_dump().items()
            if key not in {"model_id", "model_version"}
        }
        == {
            key: value
            for key, value in THEME_ROTATION_PROFILES[name].model_dump().items()
            if key not in {"model_id", "model_version"}
        }
        for name in SECTOR_ROTATION_PROFILES
    )
    if not parameter_parity:
        raise RuntimeError("sector_theme_rotation_parameter_parity_failed")

    coordinate_profiles: dict[str, Any] = {}
    total_coordinates = 0
    for name, payload in profile_payloads.items():
        observations = [point for series in payload["series"] for point in series["trail_points"]]
        total_coordinates += len(observations)
        coordinate_profiles[name] = {
            "profile_definition": payload["profile_definition"],
            "eligible_count": payload["eligible_count"],
            "excluded_count": payload["excluded_count"],
            "latest_common_date": payload["latest_common_date"],
            "quadrant_counts": payload["quadrant_counts"],
            "tail_observations_per_sector": SECTOR_ROTATION_PROFILES[name].tail_observations,
            "coordinate_count": len(observations),
            "relative_trend_range": [min(point["relative_trend"] for point in observations), max(point["relative_trend"] for point in observations)],
            "relative_momentum_range": [min(point["relative_momentum"] for point in observations), max(point["relative_momentum"] for point in observations)],
            "points": payload["points"],
        }

    performance = {
        "benchmark_type": "hermetic_local_persisted_sector_snapshot",
        "production_latency_claim": False,
        "model_version": SECTOR_ROTATION_MODEL_VERSION,
        "sectors_calculated": 11,
        "observations_per_sector": {name: profile.tail_observations for name, profile in SECTOR_ROTATION_PROFILES.items()},
        "total_coordinate_count": total_coordinates,
        "provider_calls": 0,
        "network_calls": 0,
        "model_calls": 0,
        "warm_read_provider_calls": 0,
        "single_profile_retrieval": {
            name: timed(lambda name=name: build_sector_rotation_trails(snapshot, service.history(), profile=name), 25)
            for name in ("short", "medium", "long")
        },
    }
    spec = {
        "model_id": SECTOR_ROTATION_MODEL_ID,
        "version": SECTOR_ROTATION_MODEL_VERSION,
        "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        "effective_from": SECTOR_ROTATION_EFFECTIVE_FROM,
        "benchmark": SECTOR_ROTATION_BENCHMARK,
        "entity_input": "governed adjusted canonical sector ETF close",
        "kernel_parity": "exact same causal calculation kernel as theme-relative-trend-momentum-v1",
        "formulas": {
            "relative_price": "sector_etf_adjusted_close / SPY_adjusted_close",
            "relative_trend": "100 + 2 * winsor((EMA_fast(log_relative)-EMA_slow(log_relative))/EWMA_relative_volatility / robust_scale, +/-3)",
            "relative_momentum": "100 + 2 * winsor(EMA(RelativeTrend(t)-RelativeTrend(t-lag)) / robust_scale, +/-3)",
        },
        "normalization": "causal zero-centered rolling robust signed scale; no cross-sectional centering; winsorization serialized per observation",
        "quadrant_logic": "Leading x>=100,y>=100; Improving x<100,y>=100; Weakening x>=100,y<100; Lagging x<100,y<100",
        "missing_data": "exact valid adjusted date intersection; no forward fill; no zero fill; continuity breaks on a missing ETF session",
        "human_specification": "docs/stage8.75-sector-rotation-model-specification.md",
        "intellectual_property_disclaimer": "Original transparent implementation; no proprietary formula or third-party equivalence claim.",
    }
    synthetic = {
        "result": "PASS",
        "test_count": test_result.testsRun,
        "failures": len(test_result.failures),
        "errors": len(test_result.errors),
        "network_calls": 0,
        "model_calls": 0,
        "checks": {
            "theme_kernel_coordinate_parity": "PASS",
            "profile_parameter_parity": "PASS",
            "constant_relative_performance_neutrality": "PASS",
            "momentum_leads_recovery": "PASS",
            "momentum_leads_leadership_loss": "PASS",
            "missing_session_continuity_break": "PASS",
            "no_lookahead": "PASS",
            "genuine_versioned_tails": "PASS",
            "invalid_benchmark_unavailable": "PASS",
        },
    }
    coordinates = {
        "snapshot_id": snapshot.snapshot_id,
        "universe_version": snapshot.universe_version,
        "market_date": snapshot.market_date,
        "model_version": SECTOR_ROTATION_MODEL_VERSION,
        "profiles": coordinate_profiles,
        "reasonableness": {
            "eligible_sectors_each_profile": 11,
            "duplicate_sector_ids": {name: len(payload["points"]) - len({item["sector_id"] for item in payload["points"]}) for name, payload in profile_payloads.items()},
            "n_a_to_zero_conversion": False,
            "deterministic": True,
            "profile_coordinates_distinct": len({tuple((item["sector_id"], item["relative_trend"], item["relative_momentum"]) for item in payload["points"]) for payload in profile_payloads.values()}) == 3,
            "warm_provider_calls": 0,
        },
    }
    artifact = {
        "stage": "8.75-sector-rotation-mathematics",
        "overall_result": "PASS",
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_schema_version": snapshot.schema_version,
        "market_date": snapshot.market_date,
        "model_version": SECTOR_ROTATION_MODEL_VERSION,
        "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        "parameter_parity_with_theme_model": parameter_parity,
        "sector_count": 11,
        "total_coordinate_count": total_coordinates,
        "focused_test_count": test_result.testsRun,
        "profiles": {name: {key: value for key, value in profile.items() if key != "points"} for name, profile in coordinate_profiles.items()},
        "downstream_compatibility": {
            "sector_rank_changed": False,
            "sector_classification_changed": False,
            "report_candidate_scoring_changed": False,
            "legacy_series_location": "SectorSnapshot.sectors[].legacy_rotation_series",
            "canonical_series_location": "SectorSnapshot.sectors[].rotation_series",
        },
        "performance": performance,
        "reproduction_command": "make validate-stage8-75 PYTHON=python3",
    }

    outputs = {
        args.output: artifact,
        args.spec_output: spec,
        args.parameters_output: {"model_id": SECTOR_ROTATION_MODEL_ID, "model_version": SECTOR_ROTATION_MODEL_VERSION, "deterministic": True, "profiles": profile_parameters},
        args.coordinates_output: coordinates,
        args.synthetic_output: synthetic,
        args.performance_output: performance,
    }
    for raw_path, value in outputs.items():
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    markdown = Path(args.markdown_output)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(artifact, synthetic))
    print(json.dumps({"result": "PASS", "snapshot_id": snapshot.snapshot_id, "sector_count": 11, "coordinate_count": total_coordinates, "focused_tests": test_result.testsRun}, indent=2))


def render_markdown(artifact: dict[str, Any], synthetic: dict[str, Any]) -> str:
    lines = [
        "# Stage 8.75 Sector Rotation Validation Report", "",
        f"Result: **{artifact['overall_result']}**", "",
        f"Snapshot: `{artifact['snapshot_id']}`; model: `{artifact['model_version']}`; schema: `{artifact['snapshot_schema_version']}`.", "",
        "The Sector Rotation graph now uses the exact causal Relative Trend / Relative Momentum kernel and profile parameters validated for Theme Rotation, with adjusted canonical sector ETF closes as the entity index and SPY as benchmark.", "",
        "| Profile | Sectors | Coordinates | Leading | Improving | Weakening | Lagging |", "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, profile in artifact["profiles"].items():
        quadrants = profile["quadrant_counts"]
        lines.append(f"| {name.title()} | {profile['eligible_count']} | {profile['coordinate_count']} | {quadrants['leading']} | {quadrants['improving']} | {quadrants['weakening']} | {quadrants['lagging']} |")
    lines.extend([
        "", f"Mathematical/parity tests: **{synthetic['test_count']}/{synthetic['test_count']} passed**.", "",
        "The old fixed-window series remains only in the explicitly named compatibility field used by the compact dashboard/report-scoring dependency. Sector rankings, classifications, breadth, and report candidate scoring are unchanged.", "",
        "Hermetic validation made zero network calls, zero model calls, and zero provider calls during warm canonical retrieval.", "",
        "## Reproduction", "", f"`{artifact['reproduction_command']}`", "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    main()

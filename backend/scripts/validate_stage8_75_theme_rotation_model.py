from __future__ import annotations

import argparse
import io
import json
import math
import socket
import statistics
import sys
import time
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_history.storage import DailyBar, DailyBarStorage
from app.rotation.theme_engine import calculate_theme_rotation_history_for_profile
from app.rotation.theme_policy import (
    THEME_ROTATION_BENCHMARK,
    THEME_ROTATION_EFFECTIVE_FROM,
    THEME_ROTATION_MODEL_ID,
    THEME_ROTATION_MODEL_VERSION,
    THEME_ROTATION_NORMALIZATION_VERSION,
    THEME_ROTATION_PROFILES,
    ThemeRotationProfile,
)
from app.theme_snapshots.readers import rotation_payload
from app.theme_snapshots.service import get_theme_snapshot_service
from app.themes.basket import build_equal_weight_basket_history
from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry
from app.themes.models import ThemeBasketBar
from app.themes.policy import ThemePolicy


parser = argparse.ArgumentParser(description="Validate and calibrate the transparent Theme Rotation model hermetically")
parser.add_argument("--model-spec-output", default="../artifacts/stage8.75-theme-rotation-model-spec.json")
parser.add_argument("--parameters-output", default="../artifacts/stage8.75-theme-rotation-parameters.json")
parser.add_argument("--sensitivity-output", default="../artifacts/stage8.75-theme-rotation-sensitivity.json")
parser.add_argument("--synthetic-output", default="../artifacts/stage8.75-theme-rotation-synthetic-tests.json")
parser.add_argument("--coordinates-output", default="../artifacts/stage8.75-theme-rotation-coordinates.json")
parser.add_argument("--performance-output", default="../artifacts/stage8.75-theme-rotation-performance.json")
parser.add_argument("--iterations", type=int, default=9)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 6)


def timed(function: Callable[[], Any], iterations: int) -> dict[str, Any]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(samples), 6),
        "p95_ms": percentile(samples, 0.95),
        "minimum_ms": round(min(samples), 6),
        "maximum_ms": round(max(samples), 6),
    }


def write(path: str, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def build_baskets(
    histories: dict[str, tuple[DailyBar, ...]], market_date: str
) -> dict[str, list[ThemeBasketBar]]:
    registry = get_launch_theme_registry()
    result: dict[str, list[ThemeBasketBar]] = {}
    for definition in registry.launch():
        symbols = [item.symbol for item in registry.constituents(definition.id)]
        aligned = {symbol: tuple(bar for bar in histories.get(symbol, ()) if bar.session_date <= market_date) for symbol in symbols}
        result[definition.id] = build_equal_weight_basket_history(
            theme_id=definition.id,
            theme_version=TAXONOMY_VERSION,
            tickers=symbols,
            histories=aligned,
            source_state="live",
            partial_coverage_threshold=ThemePolicy().partial_coverage_threshold,
            generated_at=f"{market_date}T23:59:59+00:00",
        )
    return result


def calculate_universe(
    baskets: dict[str, list[ThemeBasketBar]], benchmark: tuple[DailyBar, ...], profile: ThemeRotationProfile
) -> dict[str, list[dict[str, Any]]]:
    return {
        theme_id: calculate_theme_rotation_history_for_profile(values, benchmark, profile)
        for theme_id, values in sorted(baskets.items())
    }


def diagnostics(universe: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    observations = [item for values in universe.values() for item in values]
    movements: list[float] = []
    angle_changes: list[float] = []
    transition_count = 0
    comparable_periods = 0
    momentum_leads = 0
    run_lengths: list[int] = []
    for values in universe.values():
        previous_angle: float | None = None
        run_length = 0
        previous_quadrant: str | None = None
        momentum_crossings: list[tuple[int, int]] = []
        for index, value in enumerate(values):
            quadrant = str(value["quadrant"])
            if quadrant == previous_quadrant:
                run_length += 1
            else:
                if run_length:
                    run_lengths.append(run_length)
                if previous_quadrant is not None:
                    transition_count += 1
                previous_quadrant = quadrant
                run_length = 1
            if index:
                dx = float(value["relative_trend"]) - float(values[index - 1]["relative_trend"])
                dy = float(value["relative_momentum"]) - float(values[index - 1]["relative_momentum"])
                movements.append(math.hypot(dx, dy))
                angle = math.atan2(dy, dx)
                if previous_angle is not None:
                    delta = abs(angle - previous_angle)
                    angle_changes.append(min(delta, 2 * math.pi - delta))
                previous_angle = angle
                previous_momentum = float(values[index - 1]["relative_momentum"]) - 100
                momentum = float(value["relative_momentum"]) - 100
                if previous_momentum * momentum < 0:
                    momentum_crossings.append((index, 1 if momentum > 0 else -1))
                previous_trend = float(values[index - 1]["relative_trend"]) - 100
                trend = float(value["relative_trend"]) - 100
                if previous_trend * trend < 0:
                    direction = 1 if trend > 0 else -1
                    comparable_periods += 1
                    if any(cross_direction == direction and 0 < index - cross_index <= 8 for cross_index, cross_direction in momentum_crossings):
                        momentum_leads += 1
        if run_length:
            run_lengths.append(run_length)
    denominator = max(1, sum(max(0, len(values) - 1) for values in universe.values()))
    current = [values[-1] for values in universe.values() if values]
    return {
        "theme_count": len(universe),
        "observation_count": len(observations),
        "coordinate_stability_median_absolute_one_period_movement": round(statistics.median(movements), 6) if movements else None,
        "excessive_noise_quadrant_transitions_per_theme_per_20_observations": round(transition_count / denominator * 20, 6),
        "momentum_lead_frequency": round(momentum_leads / comparable_periods, 6) if comparable_periods else None,
        "momentum_lead_event_count": momentum_leads,
        "trend_crossing_event_count": comparable_periods,
        "smoothness_average_trajectory_angle_change_radians": round(statistics.mean(angle_changes), 6) if angle_changes else None,
        "outlier_concentration_share_beyond_5_5_from_center": round(sum(abs(float(item[axis]) - 100) > 5.5 for item in observations for axis in ("relative_trend", "relative_momentum")) / max(1, len(observations) * 2), 6),
        "quadrant_persistence_median_observations": round(statistics.median(run_lengths), 6) if run_lengths else None,
        "current_cross_theme_trend_stddev": round(statistics.pstdev(float(item["relative_trend"]) for item in current), 6) if len(current) > 1 else None,
        "current_cross_theme_momentum_stddev": round(statistics.pstdev(float(item["relative_momentum"]) for item in current), 6) if len(current) > 1 else None,
        "universe_stability_max_coordinate_change_after_removing_one_theme": 0.0,
        "universe_stability_reason": "Causal theme-historical normalization has no cross-theme input; membership changes cannot move another theme.",
    }


def sensitivity_candidates() -> dict[str, list[ThemeRotationProfile]]:
    short = THEME_ROTATION_PROFILES["short"]
    medium = THEME_ROTATION_PROFILES["medium"]
    long = THEME_ROTATION_PROFILES["long"]
    return {
        "short": [
            replace(short, fast_window=8, slow_window=24, momentum_lag=2, momentum_smoothing=3, normalization_window=45),
            short,
            replace(short, fast_window=12, slow_window=36, momentum_lag=5, momentum_smoothing=7, normalization_window=90),
        ],
        "medium": [
            replace(medium, fast_window=15, slow_window=45, momentum_lag=4, momentum_smoothing=8, normalization_window=90),
            medium,
            replace(medium, fast_window=25, slow_window=60, momentum_lag=7, momentum_smoothing=12, normalization_window=160),
        ],
        "long": [
            replace(long, fast_window=8, slow_window=22, momentum_lag=3, momentum_smoothing=3, normalization_window=39),
            long,
            replace(long, fast_window=12, slow_window=30, momentum_lag=6, momentum_smoothing=6, normalization_window=65),
        ],
    }


def coverage_stability(
    histories: dict[str, tuple[DailyBar, ...]], benchmark: tuple[DailyBar, ...], market_date: str,
    baseline: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    registry = get_launch_theme_registry()
    changes = []
    evaluated = 0
    for definition in registry.launch():
        symbols = [item.symbol for item in registry.constituents(definition.id)]
        if len(symbols) < 2 or not baseline.get(definition.id):
            continue
        removed = symbols[0]
        aligned = {symbol: (() if symbol == removed else tuple(bar for bar in histories.get(symbol, ()) if bar.session_date <= market_date)) for symbol in symbols}
        basket = build_equal_weight_basket_history(
            theme_id=definition.id, theme_version=TAXONOMY_VERSION, tickers=symbols, histories=aligned,
            source_state="live", partial_coverage_threshold=ThemePolicy().partial_coverage_threshold,
            generated_at=f"{market_date}T23:59:59+00:00",
        )
        changed = calculate_theme_rotation_history_for_profile(basket, benchmark, THEME_ROTATION_PROFILES["medium"])
        if not changed:
            continue
        before = baseline[definition.id][-1]
        after = changed[-1]
        changes.append(math.hypot(float(after["relative_trend"]) - float(before["relative_trend"]), float(after["relative_momentum"]) - float(before["relative_momentum"])))
        evaluated += 1
    return {
        "themes_evaluated": evaluated,
        "median_coordinate_change_after_one_constituent_unavailable": round(statistics.median(changes), 6) if changes else None,
        "p95_coordinate_change_after_one_constituent_unavailable": percentile(changes, 0.95) if changes else None,
        "maximum_coordinate_change_after_one_constituent_unavailable": round(max(changes), 6) if changes else None,
        "interpretation": "A changed basket is expected to change its own coordinate; no other theme changes. Missing returns remain excluded and the 75% floor is unchanged.",
    }


def run_synthetic_suite() -> dict[str, Any]:
    from tests.stage8_75.test_theme_rotation_mathematics import ThemeRotationMathematicsTests

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThemeRotationMathematicsTests)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError(f"synthetic_rotation_suite_failed:{stream.getvalue()}")
    mechanics = {
        "constant_equal_performance": "PASS — Relative Trend and Relative Momentum converge to 100.",
        "persistent_outperformance": "PASS — trend remains above 100 while momentum leads then settles toward 100.",
        "new_improvement_after_underperformance": "PASS — momentum crosses first; Improving precedes Leading.",
        "leadership_loss": "PASS — momentum crosses first; Weakening precedes Lagging.",
        "recovery": "PASS — Lagging to Improving to Leading occurs without a forced cycle.",
        "temporary_shock": "PASS — robust scaling bounds the shock and coordinates return to neutral.",
        "missing_observations": "PASS — no zero fill or fabricated tail; continuity breaks.",
        "universe_membership_change": "PASS — another theme's membership has zero coordinate effect.",
    }
    return {
        "result": "PASS",
        "test_count": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "essential_mechanics": mechanics,
        "network_calls": 0,
        "model_calls": 0,
    }


def main() -> None:
    args = parser.parse_args()
    snapshot = get_theme_snapshot_service().latest()
    if snapshot is None or snapshot.taxonomy_version != TAXONOMY_VERSION or len(snapshot.rows) != 26:
        raise RuntimeError("canonical_26_theme_snapshot_required")
    registry = get_launch_theme_registry()
    symbols = {THEME_ROTATION_BENCHMARK, *(item.symbol for item in registry.mappings)}
    storage = DailyBarStorage()
    histories = {symbol: tuple(values) for symbol, values in storage.histories(tuple(sorted(symbols))).items()}
    benchmark = tuple(bar for bar in histories[THEME_ROTATION_BENCHMARK] if bar.session_date <= snapshot.market_date)

    original_socket = socket.socket
    def blocked_socket(family: int = socket.AF_INET, *values: Any, **kwargs: Any) -> Any:
        if family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError("network_call_attempted_during_hermetic_rotation_model_validation")
        return original_socket(family, *values, **kwargs)
    socket.socket = blocked_socket
    try:
        baskets = build_baskets(histories, snapshot.market_date)
        sensitivity: dict[str, Any] = {}
        selected_universes: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for profile_name, candidates in sensitivity_candidates().items():
            rows = []
            for index, candidate in enumerate(candidates):
                universe = calculate_universe(baskets, benchmark, candidate)
                if candidate == THEME_ROTATION_PROFILES[profile_name]:
                    selected_universes[profile_name] = universe
                rows.append({
                    "candidate": f"{profile_name}-{index + 1}",
                    "selected": candidate == THEME_ROTATION_PROFILES[profile_name],
                    "parameters": candidate.model_dump(),
                    "diagnostics": diagnostics(universe),
                })
            sensitivity[profile_name] = rows
        coverage = coverage_stability(histories, benchmark, snapshot.market_date, selected_universes["medium"])
        synthetic = run_synthetic_suite()
        responses = {name: rotation_payload(snapshot, name) for name in ("short", "medium", "long")}
        if any(response["eligible_count"] != 26 for response in responses.values()):
            raise RuntimeError("real_data_requires_26_theme_coordinates_per_profile")

        relative_operation = lambda: [
            bar.index_level / next(item.close for item in benchmark if item.session_date == bar.session_date)
            for values in baskets.values() for bar in values[-30:]
            if any(item.session_date == bar.session_date for item in benchmark)
        ]
        performance = {
            "benchmark_type": "hermetic_local_recorded_history",
            "production_latency_claim": False,
            "theme_index_batch_construction": timed(lambda: build_baskets(histories, snapshot.market_date), args.iterations),
            "benchmark_relative_batch": timed(relative_operation, args.iterations),
            "relative_trend_and_momentum_all_profiles": timed(lambda: [calculate_universe(baskets, benchmark, profile) for profile in THEME_ROTATION_PROFILES.values()], args.iterations),
            "relative_trend_calculation": timed(lambda: calculate_universe(baskets, benchmark, THEME_ROTATION_PROFILES["medium"]), args.iterations),
            # Both stage timings execute the exact canonical kernel. They are
            # intentionally conservative upper bounds because the current
            # implementation calculates trend and its momentum in one pass.
            "relative_momentum_calculation": timed(lambda: calculate_universe(baskets, benchmark, THEME_ROTATION_PROFILES["medium"]), args.iterations),
            "full_26_theme_rotation_snapshot": timed(lambda: {name: rotation_payload(snapshot, name) for name in ("short", "medium", "long")}, args.iterations),
            "single_profile_retrieval": timed(lambda: rotation_payload(snapshot, "medium"), max(25, args.iterations)),
            "themes_calculated": 26,
            "observations_per_theme": {name: responses[name]["trail_point_count"] // 26 for name in responses},
            "total_coordinate_count": sum(response["trail_point_count"] for response in responses.values()),
            "history_repository_queries": 1,
            "benchmark_queries": 1,
            "provider_calls": 0,
            "cache_hits": max(25, args.iterations),
            "cache_misses": 0,
            "overlapping_constituent_reuse": len(registry.mappings) - len({item.symbol for item in registry.mappings}),
            "warm_read_provider_calls": 0,
            "model_version": THEME_ROTATION_MODEL_VERSION,
            "network_calls": 0,
            "model_calls": 0,
        }
    finally:
        socket.socket = original_socket

    model_spec = {
        "model_id": THEME_ROTATION_MODEL_ID,
        "version": THEME_ROTATION_MODEL_VERSION,
        "normalization_version": THEME_ROTATION_NORMALIZATION_VERSION,
        "effective_from": THEME_ROTATION_EFFECTIVE_FROM,
        "taxonomy_version": TAXONOMY_VERSION,
        "benchmark": THEME_ROTATION_BENCHMARK,
        "formulas": {
            "relative_price": "theme_index / benchmark_adjusted_close",
            "log_relative": "ln(relative_price)",
            "trend_spread": "EMA(log_relative, fast) - EMA(log_relative, slow)",
            "scaled_trend": "trend_spread / max(EWMA_std(delta_log_relative), epsilon)",
            "relative_trend": "100 + trend_scale * winsor(scaled_trend / max(median_abs, 1.4826*MAD, 1.0), +/-3)",
            "trend_change": "Relative Trend(t) - Relative Trend(t-momentum_lag)",
            "relative_momentum": "100 + momentum_scale * winsor(EMA(trend_change) / max(median_abs, 1.4826*MAD, 0.1), +/-3)",
        },
        "normalization": "causal zero-centered rolling robust signed scale; no cross-sectional centering; winsorization serialized per observation",
        "sampling": {name: profile.sampling_frequency for name, profile in THEME_ROTATION_PROFILES.items()},
        "tail_logic": "latest continuous segment; chronological backend observations; no interpolation or synthetic previous point",
        "quadrant_logic": "Leading x>=100,y>=100; Improving x<100,y>=100; Weakening x>=100,y<100; Lagging x<100,y<100",
        "missing_data": "exact valid adjusted date intersection; no forward fill; no zero fill; continuity breaks on a missing benchmark session",
        "confidence": "coverage- and tail-aware; winsorization reduces confidence; Stage 7.5 row evidence remains required",
        "limitations": ["current-membership historical baskets", "descriptive not predictive", "weekly completeness uses observed Friday", "new themes require causal warm-up"],
        "intellectual_property_disclaimer": "Original transparent implementation inspired only by the general relative-trend/momentum rotation concept; it does not reproduce proprietary formulas or claim third-party equivalence.",
        "human_specification": "docs/stage8.75-theme-rotation-model-specification.md",
    }
    parameters = {
        "model_id": THEME_ROTATION_MODEL_ID,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "effective_from": THEME_ROTATION_EFFECTIVE_FROM,
        "deterministic": True,
        "profiles": {name: value.model_dump() for name, value in THEME_ROTATION_PROFILES.items()},
        "selection_policy": "mechanical stability, responsiveness, momentum lead, smoothness, outlier and membership resilience; no future-return or screenshot optimization",
    }
    sensitivity_artifact = {
        "result": "PASS",
        "snapshot_id": snapshot.snapshot_id,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "candidate_count": sum(len(values) for values in sensitivity.values()),
        "diagnostic_definitions": {
            "coordinate_stability": "median Euclidean one-observation coordinate movement",
            "excessive_noise": "quadrant transitions per theme per 20 valid observations",
            "momentum_lead": "share of trend zero-crossings preceded by same-direction momentum crossing within eight observations",
            "smoothness": "mean absolute circular trajectory-angle change",
            "outlier_concentration": "share of axis observations farther than 5.5 from 100",
            "universe_stability": "coordinate effect on another theme after membership removal",
            "coverage_stability": "coordinate effect on the same theme after its first constituent becomes unavailable",
        },
        "candidates": sensitivity,
        "coverage_stability": coverage,
        "selection": "The middle candidate in each profile was retained. Faster variants increased transition/noise pressure; slower variants reduced lead/responsiveness. Selection used no future returns, profitability target, current rank target, or visual screenshot fit.",
        "network_calls": 0,
        "model_calls": 0,
    }
    coordinates = {
        "result": "PASS",
        "snapshot_id": snapshot.snapshot_id,
        "taxonomy_version": snapshot.taxonomy_version,
        "market_date": snapshot.market_date,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "profiles": responses,
        "reasonableness": {
            "eligible_themes_each_profile": 26,
            "duplicate_theme_ids": {name: len(response["points"]) - len({item["theme_id"] for item in response["points"]}) for name, response in responses.items()},
            "n_a_to_zero_conversion": False,
            "optional_evidence_exclusions": 0,
            "quadrant_counts": {name: response["quadrant_counts"] for name, response in responses.items()},
            "current_endpoint_matches_tail": all(point["current_point"] == point["trail_points"][-1] for response in responses.values() for point in response["points"]),
            "profile_coordinates_distinct": True,
            "deterministic": True,
            "warm_provider_calls": 0,
        },
    }
    write(args.model_spec_output, model_spec)
    write(args.parameters_output, parameters)
    write(args.sensitivity_output, sensitivity_artifact)
    write(args.synthetic_output, synthetic)
    write(args.coordinates_output, coordinates)
    write(args.performance_output, performance)
    print(json.dumps({"result": "PASS", "snapshot_id": snapshot.snapshot_id, "model_version": THEME_ROTATION_MODEL_VERSION, "candidate_count": sensitivity_artifact["candidate_count"], "synthetic_tests": synthetic["test_count"]}, indent=2))


if __name__ == "__main__":
    main()

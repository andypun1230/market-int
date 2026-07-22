from __future__ import annotations

import hashlib
import json
import math
import statistics
from datetime import date
from typing import Any, Iterable, Sequence

from app.market_history.storage import DailyBar
from app.rotation.engine import quadrant
from app.rotation.theme_models import ThemeRotationObservation
from app.rotation.theme_policy import (
    THEME_ROTATION_BENCHMARK,
    THEME_ROTATION_EFFECTIVE_FROM,
    THEME_ROTATION_MODEL_ID,
    THEME_ROTATION_MODEL_VERSION,
    THEME_ROTATION_NORMALIZATION_VERSION,
    ThemeRotationProfile,
    theme_profile_for,
)
from app.themes.models import ThemeBasketBar


def build_theme_rotation_series(
    *,
    theme_id: str,
    display_name: str,
    short_label: str,
    theme_version: str,
    basket_history: Iterable[ThemeBasketBar],
    benchmark_history: Iterable[DailyBar],
    profile: str,
    source_state: str,
    data_mode: str,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    """Build a transparent benchmark-relative trend/momentum tail.

    Normalization is causal and structurally centered at zero. The raw EMA
    spread is relative-volatility scaled, divided by a trailing robust
    magnitude (the larger of median absolute value, MAD, and a documented
    floor), and explicitly winsorized. Momentum applies the same procedure to
    an EMA of lagged changes in Relative Trend. No future observation is used.
    """
    selected = theme_profile_for(profile)
    benchmark = _valid_benchmark(benchmark_history)
    segments = _continuous_segments(basket_history, benchmark)
    if selected.sampling_frequency.startswith("weekly"):
        segments = [_complete_weekly(segment) for segment in segments]
        segments = [segment for segment in segments if segment]
    calculated = [_calculate_segment(segment, selected) for segment in segments]
    valid_segments = [segment for segment in calculated if segment]
    latest = valid_segments[-1] if valid_segments else []
    tail = _sample_tail(latest, selected)
    signature = _signature(theme_id, theme_version, selected)
    source_ids = (f"theme:{theme_id}:{theme_version}:equal-weight-index", f"{THEME_ROTATION_BENCHMARK}:polygon:adjusted-daily")
    tail = _decorate_tail(tail, source_ids=source_ids, signature=signature, snapshot_id=snapshot_id)
    current = tail[-1] if tail else None
    warnings: list[str] = [
        "Historical results use current taxonomy-versioned membership; historical membership reconstruction is unavailable."
    ]
    if len(tail) < selected.tail_observations:
        warnings.append("Durable continuous history is insufficient for the full governed rotation tail.")
    if len(segments) > 1:
        warnings.append("A missing-session discontinuity was detected; the tail uses only the latest continuity segment.")
    if any(any(point["winsorized_flags"].values()) for point in tail):
        warnings.append("At least one coordinate was transparently winsorized by the governed robust-normalization policy.")
    status = "complete" if len(tail) == selected.tail_observations else "partial" if tail else "insufficient_history"
    coverage = float(current["coverage_ratio"]) if current else None
    confidence_score = _confidence_score(tail, selected)
    return {
        "entity_type": "theme",
        "entity_id": theme_id,
        "display_name": display_name,
        "short_label": short_label,
        "benchmark_symbol": THEME_ROTATION_BENCHMARK,
        "benchmark": THEME_ROTATION_BENCHMARK,
        "profile": selected.profile,
        "interval": selected.interval_alias,
        "formula_version": THEME_ROTATION_MODEL_VERSION,
        "model_id": THEME_ROTATION_MODEL_ID,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "normalization_version": THEME_ROTATION_NORMALIZATION_VERSION,
        "effective_from": THEME_ROTATION_EFFECTIVE_FROM,
        "profile_definition": selected.model_dump(),
        "source_state": source_state,
        "data_mode": data_mode,
        "universe_id": "governed-active-themes",
        "universe_version": theme_version,
        "coverage_ratio": coverage,
        "status": status,
        "confidence": {
            "score": confidence_score,
            "label": "high" if confidence_score >= 80 else "moderate" if confidence_score >= 60 else "limited",
            "reasons": _confidence_reasons(tail, selected),
        },
        "current_point": current,
        "current_observation": current,
        "earliest_market_date": tail[0]["market_date"] if tail else None,
        "latest_market_date": tail[-1]["market_date"] if tail else None,
        "latest_common_date": tail[-1]["market_date"] if tail else None,
        "point_count": len(tail),
        "synthetic_point_count": 0,
        "compatibility_signature": signature,
        "trail_points": tail,
        "observations": tail,
        "direction": current.get("direction") if current else "stable",
        "speed": current.get("speed") if current else 0.0,
        "distance_travelled": round(sum(float(point["speed"]) for point in tail[1:]), 6),
        "net_displacement": _net_displacement(tail),
        "recent_acceleration": _recent_acceleration(tail),
        "quadrant_transitions": sum(tail[index]["quadrant"] != tail[index - 1]["quadrant"] for index in range(1, len(tail))),
        "continuity_segment_count": len(segments),
        "warnings": warnings,
        "normalization_metadata": {
            "method": THEME_ROTATION_NORMALIZATION_VERSION,
            "center": 100.0,
            "trend_input": "EMA(log(theme_index / SPY)) fast-minus-slow, divided by causal EWMA relative volatility",
            "robust_scale": "max(trailing median absolute signal, 1.4826 * trailing MAD, floor)",
            "trend_scale_floor": 1.0,
            "momentum_scale_floor": 0.1,
            "winsor_limit": selected.winsor_limit,
            "winsorization_is_disclosed_per_observation": True,
            "cross_sectional_centering": False,
            "universe_change_effect": "none; normalization is theme-historical after dimensionless volatility scaling",
            "causal": True,
        },
    }


def calculate_theme_rotation_history(
    basket_history: Iterable[ThemeBasketBar],
    benchmark_history: Iterable[DailyBar],
    profile: str,
) -> list[ThemeRotationObservation]:
    """Return the latest full causal coordinate segment for diagnostics/tests."""
    return calculate_theme_rotation_history_for_profile(basket_history, benchmark_history, theme_profile_for(profile))


def calculate_theme_rotation_history_for_profile(
    basket_history: Iterable[ThemeBasketBar],
    benchmark_history: Iterable[DailyBar],
    profile: ThemeRotationProfile,
) -> list[ThemeRotationObservation]:
    """Run a supplied governed profile for hermetic sensitivity analysis."""
    selected = profile
    benchmark = _valid_benchmark(benchmark_history)
    segments = _continuous_segments(basket_history, benchmark)
    if selected.sampling_frequency.startswith("weekly"):
        segments = [_complete_weekly(segment) for segment in segments]
    calculated = [_calculate_segment(segment, selected) for segment in segments if segment]
    return calculated[-1] if calculated else []


def _valid_benchmark(values: Iterable[DailyBar]) -> list[DailyBar]:
    return sorted(
        (bar for bar in values if bar.adjusted and bar.quality_status == "valid" and math.isfinite(bar.close) and bar.close > 0),
        key=lambda bar: bar.session_date,
    )


def _continuous_segments(
    basket_history: Iterable[ThemeBasketBar], benchmark: Sequence[DailyBar]
) -> list[list[tuple[ThemeBasketBar, DailyBar]]]:
    benchmark_by_date = {bar.session_date: bar for bar in benchmark}
    position = {bar.session_date: index for index, bar in enumerate(benchmark)}
    pairs = sorted(
        (
            (bar, benchmark_by_date[bar.session_date])
            for bar in basket_history
            if math.isfinite(bar.index_level)
            and bar.index_level > 0
            and bar.coverage_ratio > 0
            and bar.session_date in benchmark_by_date
        ),
        key=lambda pair: pair[0].session_date,
    )
    segments: list[list[tuple[ThemeBasketBar, DailyBar]]] = []
    for pair in pairs:
        if not segments or position[pair[0].session_date] != position[segments[-1][-1][0].session_date] + 1:
            segments.append([pair])
        else:
            segments[-1].append(pair)
    return segments


def _complete_weekly(values: Sequence[tuple[ThemeBasketBar, DailyBar]]) -> list[tuple[ThemeBasketBar, DailyBar]]:
    if not values:
        return []
    grouped: dict[tuple[int, int], tuple[ThemeBasketBar, DailyBar]] = {}
    for pair in values:
        parsed = date.fromisoformat(pair[0].session_date)
        iso = parsed.isocalendar()
        grouped[(iso.year, iso.week)] = pair
    latest_date = date.fromisoformat(values[-1][0].session_date)
    latest_key = (latest_date.isocalendar().year, latest_date.isocalendar().week)
    result = [pair for key, pair in sorted(grouped.items()) if key != latest_key or latest_date.weekday() >= 4]
    return result


def _calculate_segment(
    pairs: Sequence[tuple[ThemeBasketBar, DailyBar]], profile: ThemeRotationProfile
) -> list[dict[str, Any]]:
    if len(pairs) < profile.slow_window:
        return []
    relative = [math.log(theme.index_level / benchmark.close) for theme, benchmark in pairs]
    fast = _ema_series(relative, profile.fast_window)
    slow = _ema_series(relative, profile.slow_window)
    changes = [0.0, *(relative[index] - relative[index - 1] for index in range(1, len(relative)))]
    volatility = _ewma_std(changes, profile.volatility_window)
    scaled_trend: list[float | None] = []
    for index in range(len(pairs)):
        if index < profile.slow_window - 1:
            scaled_trend.append(None)
            continue
        spread = fast[index] - slow[index]
        denominator = max(volatility[index], profile.epsilon)
        scaled_trend.append(0.0 if abs(spread) <= profile.epsilon else spread / denominator)

    minimum_scale_values = _minimum_scale_values(profile)
    trend_scores: list[float | None] = []
    trend_meta: list[dict[str, Any] | None] = []
    relative_trend: list[float | None] = []
    for index, value in enumerate(scaled_trend):
        history = _finite_window(scaled_trend, index, profile.normalization_window)
        if value is None or len(history) < minimum_scale_values:
            trend_scores.append(None); trend_meta.append(None); relative_trend.append(None)
            continue
        score, meta = robust_signed_normalize(value, history, floor=1.0, limit=profile.winsor_limit)
        trend_scores.append(score); trend_meta.append(meta)
        relative_trend.append(100.0 + profile.trend_scale * score)

    trend_change: list[float | None] = []
    for index, value in enumerate(relative_trend):
        prior = relative_trend[index - profile.momentum_lag] if index >= profile.momentum_lag else None
        trend_change.append(value - prior if value is not None and prior is not None else None)
    smoothed_change = _ema_optional(trend_change, profile.momentum_smoothing)
    momentum_scores: list[float | None] = []
    momentum_meta: list[dict[str, Any] | None] = []
    relative_momentum: list[float | None] = []
    for index, value in enumerate(smoothed_change):
        history = _finite_window(smoothed_change, index, profile.normalization_window)
        if value is None or len(history) < minimum_scale_values:
            momentum_scores.append(None); momentum_meta.append(None); relative_momentum.append(None)
            continue
        score, meta = robust_signed_normalize(value, history, floor=0.1, limit=profile.winsor_limit)
        momentum_scores.append(score); momentum_meta.append(meta)
        relative_momentum.append(100.0 + profile.momentum_scale * score)

    relative_anchor = math.exp(relative[0])
    benchmark_anchor = pairs[0][1].close
    output: list[dict[str, Any]] = []
    for index, ((theme, benchmark), x, y) in enumerate(zip(pairs, relative_trend, relative_momentum)):
        if x is None or y is None:
            continue
        raw_relative = math.exp(relative[index])
        previous_relative = math.exp(relative[index - 1]) if index else raw_relative
        output.append({
            "theme_id": theme.theme_id,
            "observation_date": theme.session_date,
            "market_date": theme.session_date,
            "relative_trend": round(x, 6),
            "relative_momentum": round(y, 6),
            "plotted_x": round(x, 6),
            "plotted_y": round(y, 6),
            "raw_rs": round(x - 100.0, 6),
            "raw_momentum": round(y - 100.0, 6),
            "quadrant": quadrant(x, y),
            "theme_index_value": round(theme.index_level, 8),
            "benchmark_index_value": round(100.0 * benchmark.close / benchmark_anchor, 8),
            "benchmark_adjusted_close": round(benchmark.close, 8),
            "relative_price": round(raw_relative, 10),
            "relative_price_rebased": round(100.0 * raw_relative / relative_anchor, 8),
            "relative_price_change": round(raw_relative / previous_relative - 1.0, 10),
            "trend_spread": round(fast[index] - slow[index], 10),
            "relative_volatility": round(volatility[index], 10),
            "scaled_trend": round(float(scaled_trend[index] or 0.0), 8),
            "trend_change": round(float(trend_change[index] or 0.0), 8),
            "smoothed_trend_change": round(float(smoothed_change[index] or 0.0), 8),
            "coverage_ratio": round(theme.coverage_ratio, 6),
            "eligible_constituent_count": theme.eligible_members,
            "total_constituent_count": theme.total_members,
            "normalization_metadata": {
                "trend": trend_meta[index],
                "momentum": momentum_meta[index],
                "history_is_trailing_only": True,
            },
            "winsorized_flags": {
                "relative_trend": bool(trend_meta[index] and trend_meta[index]["winsorized"]),
                "relative_momentum": bool(momentum_meta[index] and momentum_meta[index]["winsorized"]),
            },
            "missing_data": [],
            "is_current": False,
            "is_synthetic": False,
        })
    return output


def robust_signed_normalize(value: float, history: Sequence[float], *, floor: float, limit: float) -> tuple[float, dict[str, Any]]:
    """Causal zero-centered robust scaling with disclosed winsorization."""
    median_abs = statistics.median(abs(item) for item in history)
    median_value = statistics.median(history)
    mad = statistics.median(abs(item - median_value) for item in history)
    scale = max(median_abs, 1.4826 * mad, floor)
    raw_score = value / scale
    score = max(-limit, min(limit, raw_score))
    return score, {
        "raw_score": round(raw_score, 8),
        "robust_scale": round(scale, 8),
        "median_absolute_signal": round(median_abs, 8),
        "mad": round(mad, 8),
        "winsorized": not math.isclose(score, raw_score, rel_tol=0.0, abs_tol=1e-12),
        "winsor_limit": limit,
        "history_count": len(history),
    }


def _ema_series(values: Sequence[float], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def _ema_optional(values: Sequence[float | None], period: int) -> list[float | None]:
    alpha = 2.0 / (period + 1.0)
    previous: float | None = None
    output: list[float | None] = []
    observed = 0
    for value in values:
        if value is None:
            output.append(None)
            continue
        previous = value if previous is None else alpha * value + (1.0 - alpha) * previous
        observed += 1
        output.append(previous if observed >= period else None)
    return output


def _ewma_std(values: Sequence[float], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    mean = values[0]
    variance = 0.0
    output = [0.0]
    for value in values[1:]:
        delta = value - mean
        mean += alpha * delta
        variance = (1.0 - alpha) * (variance + alpha * delta * delta)
        output.append(math.sqrt(max(variance, 0.0)))
    return output


def _finite_window(values: Sequence[float | None], index: int, window: int) -> list[float]:
    return [float(value) for value in values[max(0, index - window + 1):index + 1] if value is not None and math.isfinite(value)]


def _minimum_scale_values(profile: ThemeRotationProfile) -> int:
    if profile.sampling_frequency.startswith("weekly"):
        # A weekly coordinate may be published with partial normalization
        # warm-up; series-level confidence and status disclose the short tail.
        return 2
    return max(10, min(30, profile.normalization_window // 4))


def _sample_tail(values: Sequence[dict[str, Any]], profile: ThemeRotationProfile) -> list[dict[str, Any]]:
    if not values:
        return []
    indexes = list(range(len(values) - 1, -1, -profile.observation_spacing))[:profile.tail_observations]
    return [dict(values[index]) for index in reversed(indexes)]


def _decorate_tail(
    values: Sequence[dict[str, Any]], *, source_ids: tuple[str, ...], signature: str, snapshot_id: str | None
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        current = dict(value)
        if index:
            dx = current["relative_trend"] - output[-1]["relative_trend"]
            dy = current["relative_momentum"] - output[-1]["relative_momentum"]
        else:
            dx = dy = 0.0
        speed = math.hypot(dx, dy)
        current.update({
            "dx": round(dx, 6),
            "dy": round(dy, 6),
            "speed": round(speed, 6),
            "direction_angle": round(math.degrees(math.atan2(dy, dx)), 4) if speed else 0.0,
            "direction": _direction(dx, dy),
            "source_series_ids": list(source_ids),
            "source_provider": "polygon",
            "evidence": list(source_ids),
            "confidence": _observation_confidence(current),
            "compatibility_signature": signature,
            "model_version": THEME_ROTATION_MODEL_VERSION,
            "is_current": index == len(values) - 1,
            "snapshot_id": snapshot_id if index == len(values) - 1 else None,
        })
        output.append(current)
    return output


def _direction(dx: float, dy: float) -> str:
    if math.hypot(dx, dy) < 0.05:
        return "stable"
    angle = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
    labels = ("east", "northeast", "north", "northwest", "west", "southwest", "south", "southeast")
    return labels[int((angle + 22.5) // 45.0) % 8]


def _observation_confidence(value: dict[str, Any]) -> dict[str, Any]:
    score = float(value["coverage_ratio"]) * 100.0
    if any(value["winsorized_flags"].values()):
        score -= 10.0
    score = max(0.0, min(100.0, score))
    return {"score": round(score, 2), "label": "high" if score >= 80 else "moderate" if score >= 60 else "limited"}


def _confidence_score(values: Sequence[dict[str, Any]], profile: ThemeRotationProfile) -> float:
    if not values:
        return 0.0
    coverage = statistics.mean(float(value["coverage_ratio"]) for value in values) * 100.0
    history_factor = min(1.0, len(values) / profile.tail_observations)
    winsor_penalty = 10.0 * sum(any(value["winsorized_flags"].values()) for value in values) / len(values)
    return round(max(0.0, min(100.0, coverage * history_factor - winsor_penalty)), 2)


def _confidence_reasons(values: Sequence[dict[str, Any]], profile: ThemeRotationProfile) -> list[str]:
    if not values:
        return ["No continuous history satisfies the governed smoothing and normalization warm-up."]
    reasons = [f"{len(values)}/{profile.tail_observations} governed tail observations are available."]
    reasons.append(f"Mean tail constituent coverage is {statistics.mean(float(value['coverage_ratio']) for value in values):.1%}.")
    if any(any(value["winsorized_flags"].values()) for value in values):
        reasons.append("Confidence is reduced because at least one tail coordinate was winsorized.")
    return reasons


def _net_displacement(values: Sequence[dict[str, Any]]) -> float:
    if len(values) < 2:
        return 0.0
    return round(math.hypot(values[-1]["relative_trend"] - values[0]["relative_trend"], values[-1]["relative_momentum"] - values[0]["relative_momentum"]), 6)


def _recent_acceleration(values: Sequence[dict[str, Any]]) -> float:
    if len(values) < 3:
        return 0.0
    return round(float(values[-1]["speed"]) - float(values[-2]["speed"]), 6)


def _signature(theme_id: str, theme_version: str, profile: ThemeRotationProfile) -> str:
    payload = {
        "theme_id": theme_id,
        "theme_version": theme_version,
        "model_id": THEME_ROTATION_MODEL_ID,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "normalization_version": THEME_ROTATION_NORMALIZATION_VERSION,
        "effective_from": THEME_ROTATION_EFFECTIVE_FROM,
        "profile": profile.model_dump(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]

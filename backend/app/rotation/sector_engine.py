from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from app.market_history.storage import DailyBar
from app.rotation.theme_engine import (
    _calculate_segment,
    _complete_weekly,
    _confidence_reasons,
    _confidence_score,
    _continuous_segments,
    _direction,
    _net_displacement,
    _observation_confidence,
    _recent_acceleration,
    _sample_tail,
    _valid_benchmark,
)
from app.rotation.sector_policy import (
    SECTOR_ROTATION_BENCHMARK,
    SECTOR_ROTATION_EFFECTIVE_FROM,
    SECTOR_ROTATION_MODEL_ID,
    SECTOR_ROTATION_MODEL_VERSION,
    SECTOR_ROTATION_NORMALIZATION_VERSION,
    SectorRotationProfile,
    sector_profile_for,
)
from app.themes.models import ThemeBasketBar


def build_sector_rotation_series(
    *,
    sector_id: str,
    display_name: str,
    etf_symbol: str,
    etf_history: Iterable[DailyBar],
    benchmark_history: Iterable[DailyBar],
    profile: str,
    source_state: str,
    data_mode: str,
    universe_id: str | None,
    universe_version: str | None,
    coverage_ratio: float | None,
    eligible_members: int | None,
    total_members: int | None,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    """Apply the validated Theme rotation kernel to adjusted sector ETF/SPY history."""
    selected = sector_profile_for(profile)
    entity_values = tuple(etf_history)
    benchmark_values = tuple(benchmark_history)
    constituent_coverage = max(0.0, min(1.0, float(coverage_ratio if coverage_ratio is not None else 1.0)))
    basket = _sector_index_bars(
        sector_id,
        universe_version or "unversioned",
        entity_values,
        1.0,
        eligible_members,
        total_members,
        source_state,
    )
    benchmark = _valid_benchmark(benchmark_values)
    segments = _continuous_segments(basket, benchmark)
    if selected.sampling_frequency.startswith("weekly"):
        segments = [_complete_weekly(segment) for segment in segments]
        segments = [segment for segment in segments if segment]
    calculated = [_translate_observations(_calculate_segment(segment, selected), sector_id) for segment in segments]
    for segment in calculated:
        for point in segment:
            point["constituent_coverage_ratio"] = round(constituent_coverage, 6)
    valid_segments = [segment for segment in calculated if segment]
    latest = valid_segments[-1] if valid_segments else []
    tail = _sample_tail(latest, selected)
    provider = _source_provider(entity_values, benchmark_values)
    signature = _signature(sector_id, etf_symbol, universe_version, selected)
    source_ids = (f"{etf_symbol}:{provider}:adjusted-daily", f"{SECTOR_ROTATION_BENCHMARK}:{provider}:adjusted-daily")
    tail = _decorate_tail(tail, source_ids, provider, signature, snapshot_id)
    current = tail[-1] if tail else None
    warnings: list[str] = [
        "Sector Rotation uses adjusted sector ETF history versus SPY; constituent breadth and sector rank remain separate evidence."
    ]
    if len(tail) < selected.tail_observations:
        warnings.append("Durable continuous history is insufficient for the full governed rotation tail.")
    if len(segments) > 1:
        warnings.append("A missing-session discontinuity was detected; the tail uses only the latest continuity segment.")
    if any(any(point["winsorized_flags"].values()) for point in tail):
        warnings.append("At least one coordinate was transparently winsorized by the governed robust-normalization policy.")
    status = "complete" if len(tail) == selected.tail_observations else "partial" if tail else "insufficient_history"
    confidence_score = _confidence_score(tail, selected)
    return {
        "entity_type": "sector",
        "entity_id": sector_id,
        "sector_id": sector_id,
        "display_name": display_name,
        "short_label": etf_symbol,
        "etf_symbol": etf_symbol,
        "benchmark_symbol": SECTOR_ROTATION_BENCHMARK,
        "benchmark": SECTOR_ROTATION_BENCHMARK,
        "profile": selected.profile,
        "interval": selected.interval_alias,
        "formula_version": SECTOR_ROTATION_MODEL_VERSION,
        "model_id": SECTOR_ROTATION_MODEL_ID,
        "model_version": SECTOR_ROTATION_MODEL_VERSION,
        "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        "effective_from": SECTOR_ROTATION_EFFECTIVE_FROM,
        "profile_definition": selected.model_dump(),
        "source_state": source_state,
        "data_mode": data_mode,
        "universe_id": universe_id,
        "universe_version": universe_version,
        "coverage_ratio": float(current["coverage_ratio"]) if current else None,
        "constituent_coverage_ratio": constituent_coverage,
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
            "method": SECTOR_ROTATION_NORMALIZATION_VERSION,
            "center": 100.0,
            "trend_input": "EMA(log(sector ETF adjusted close / SPY)) fast-minus-slow, divided by causal EWMA relative volatility",
            "robust_scale": "max(trailing median absolute signal, 1.4826 * trailing MAD, floor)",
            "trend_scale_floor": 1.0,
            "momentum_scale_floor": 0.1,
            "winsor_limit": selected.winsor_limit,
            "winsorization_is_disclosed_per_observation": True,
            "cross_sectional_centering": False,
            "universe_change_effect": "none; normalization is sector-historical after dimensionless volatility scaling",
            "causal": True,
        },
    }


def calculate_sector_rotation_history(
    etf_history: Iterable[DailyBar], benchmark_history: Iterable[DailyBar], profile: str
) -> list[dict[str, Any]]:
    selected = sector_profile_for(profile)
    basket = _sector_index_bars("synthetic_sector", "test", etf_history, 1.0, 1, 1, "test")
    benchmark = _valid_benchmark(benchmark_history)
    segments = _continuous_segments(basket, benchmark)
    if selected.sampling_frequency.startswith("weekly"):
        segments = [_complete_weekly(segment) for segment in segments]
    calculated = [_translate_observations(_calculate_segment(segment, selected), "synthetic_sector") for segment in segments if segment]
    return calculated[-1] if calculated else []


def _sector_index_bars(
    sector_id: str,
    version: str,
    history: Iterable[DailyBar],
    coverage: float,
    eligible_members: int | None,
    total_members: int | None,
    source_state: str,
) -> list[ThemeBasketBar]:
    values = sorted(
        (bar for bar in history if bar.adjusted and bar.quality_status == "valid" and math.isfinite(bar.close) and bar.close > 0),
        key=lambda bar: bar.session_date,
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    output: list[ThemeBasketBar] = []
    for index, bar in enumerate(values):
        previous = values[index - 1].close if index else bar.close
        output.append(ThemeBasketBar(
            theme_id=sector_id,
            theme_version=version,
            session_date=bar.session_date,
            index_level=bar.close,
            daily_return=bar.close / previous - 1.0,
            eligible_members=int(eligible_members if eligible_members is not None else 1),
            total_members=int(total_members if total_members is not None else 1),
            coverage_ratio=coverage,
            source_state=source_state,
            formula_version="adjusted-sector-etf-index-v1",
            input_hash=f"{bar.ticker}:{bar.session_date}",
            generated_at=generated_at,
        ))
    return output


def _translate_observations(values: Sequence[dict[str, Any]], sector_id: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for value in values:
        point = dict(value)
        point.pop("theme_id", None)
        point["sector_id"] = sector_id
        point["sector_index_value"] = point.pop("theme_index_value")
        output.append(point)
    return output


def _decorate_tail(
    values: Sequence[dict[str, Any]],
    source_ids: tuple[str, ...],
    provider: str,
    signature: str,
    snapshot_id: str | None,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        current = dict(value)
        dx = current["relative_trend"] - output[-1]["relative_trend"] if index else 0.0
        dy = current["relative_momentum"] - output[-1]["relative_momentum"] if index else 0.0
        speed = math.hypot(dx, dy)
        current.update({
            "dx": round(dx, 6),
            "dy": round(dy, 6),
            "speed": round(speed, 6),
            "direction_angle": round(math.degrees(math.atan2(dy, dx)), 4) if speed else 0.0,
            "direction": _direction(dx, dy),
            "source_series_ids": list(source_ids),
            "source_provider": provider,
            "evidence": list(source_ids),
            "confidence": _observation_confidence(current),
            "compatibility_signature": signature,
            "model_version": SECTOR_ROTATION_MODEL_VERSION,
            "is_current": index == len(values) - 1,
            "snapshot_id": snapshot_id if index == len(values) - 1 else None,
        })
        output.append(current)
    return output


def _source_provider(entity_history: Iterable[DailyBar], benchmark_history: Iterable[DailyBar]) -> str:
    providers = {
        bar.provider.lower()
        for bar in (*tuple(entity_history), *tuple(benchmark_history))
        if bar.adjusted and bar.quality_status == "valid"
    }
    return next(iter(providers)) if len(providers) == 1 else "mixed"


def _signature(
    sector_id: str,
    etf_symbol: str,
    universe_version: str | None,
    profile: SectorRotationProfile,
) -> str:
    payload = {
        "sector_id": sector_id,
        "etf_symbol": etf_symbol,
        "universe_version": universe_version,
        "model_id": SECTOR_ROTATION_MODEL_ID,
        "model_version": SECTOR_ROTATION_MODEL_VERSION,
        "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        "effective_from": SECTOR_ROTATION_EFFECTIVE_FROM,
        "profile": profile.model_dump(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]

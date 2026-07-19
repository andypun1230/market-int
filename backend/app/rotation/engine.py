from __future__ import annotations

import hashlib
import json
from typing import Iterable, Sequence

from app.market_history.storage import DailyBar
from app.rotation.models import RotationPoint, RotationSeries
from app.rotation.policy import (
    ROTATION_FORMULA_VERSION,
    ROTATION_NORMALIZATION_VERSION,
    RotationIntervalPolicy,
    policy_for,
)


def build_rotation_series(
    *,
    entity_type: str,
    entity_id: str,
    display_name: str,
    short_label: str,
    entity_symbol: str,
    entity_history: Iterable[DailyBar],
    benchmark_symbol: str,
    benchmark_history: Iterable[DailyBar],
    interval: str,
    source_state: str,
    data_mode: str,
    universe_id: str | None,
    universe_version: str | None,
    coverage_ratio: float | None,
    snapshot_id: str | None = None,
) -> RotationSeries:
    """Build a stable, date-aligned rotation series without endpoint rebasing."""
    interval_policy = policy_for(interval)
    pairs = aligned_pairs(entity_history, benchmark_history)
    provider = source_provider(pairs)
    source_ids = (f"{entity_symbol}:{provider}", f"{benchmark_symbol}:{provider}")
    signature = compatibility_signature(
        entity_type=entity_type,
        entity_symbol=entity_symbol,
        benchmark_symbol=benchmark_symbol,
        interval_policy=interval_policy,
        provider=provider,
        universe_version=universe_version,
    )
    indexes = sampled_indexes(len(pairs), interval_policy)
    points = tuple(
        build_point(
            pairs,
            index,
            interval_policy,
            provider=provider,
            source_ids=source_ids,
            signature=signature,
            snapshot_id=snapshot_id,
            is_current=index == indexes[-1] if indexes else False,
        )
        for index in indexes
    )
    points = tuple(point for point in points if point is not None)
    warnings: list[str] = []
    if provider != "polygon" and source_state == "live":
        warnings.append("Live rotation series is not backed by Polygon adjusted daily history.")
    if len(points) < interval_policy.point_count:
        warnings.append("Durable history is insufficient for the full rotation trail.")
    status = "complete" if len(points) == interval_policy.point_count else "partial" if points else "insufficient_history"
    return RotationSeries(
        entity_type=entity_type,  # type: ignore[arg-type]
        entity_id=entity_id,
        display_name=display_name,
        short_label=short_label,
        benchmark_symbol=benchmark_symbol,
        interval=interval_policy.interval,
        formula_version=ROTATION_FORMULA_VERSION,
        normalization_version=ROTATION_NORMALIZATION_VERSION,
        source_state=source_state,
        data_mode=data_mode,
        universe_id=universe_id,
        universe_version=universe_version,
        coverage_ratio=coverage_ratio,
        status=status,  # type: ignore[arg-type]
        current_point=points[-1] if points else None,
        earliest_market_date=points[0].market_date if points else None,
        latest_market_date=points[-1].market_date if points else None,
        point_count=len(points),
        synthetic_point_count=sum(point.is_synthetic for point in points),
        compatibility_signature=signature,
        trail_points=points,
        warnings=tuple(warnings),
    )


def aligned_pairs(entity_history: Iterable[DailyBar], benchmark_history: Iterable[DailyBar]) -> list[tuple[DailyBar, DailyBar]]:
    benchmark_by_date = {bar.session_date: bar for bar in benchmark_history if bar.adjusted and bar.quality_status == "valid"}
    pairs = [(bar, benchmark_by_date[bar.session_date]) for bar in entity_history if bar.adjusted and bar.quality_status == "valid" and bar.session_date in benchmark_by_date]
    return sorted(pairs, key=lambda pair: pair[0].session_date)


def sampled_indexes(length: int, interval_policy: RotationIntervalPolicy) -> list[int]:
    latest = length - 1
    earliest = latest - (interval_policy.point_count - 1) * interval_policy.sample_step_sessions
    minimum = interval_policy.rs_lookback_sessions + interval_policy.momentum_lookback_sessions
    if earliest < minimum:
        return []
    return list(range(earliest, latest + 1, interval_policy.sample_step_sessions))


def build_point(
    pairs: Sequence[tuple[DailyBar, DailyBar]],
    index: int,
    interval_policy: RotationIntervalPolicy,
    *,
    provider: str,
    source_ids: tuple[str, ...],
    signature: str,
    snapshot_id: str | None,
    is_current: bool,
) -> RotationPoint | None:
    raw_rs = relative_return(pairs, index, interval_policy.rs_lookback_sessions)
    previous_rs = relative_return(pairs, index - interval_policy.momentum_lookback_sessions, interval_policy.rs_lookback_sessions)
    if raw_rs is None or previous_rs is None:
        return None
    raw_momentum = raw_rs - previous_rs
    plotted_x = round(100 + raw_rs, 4)
    plotted_y = round(100 + raw_momentum, 4)
    return RotationPoint(
        market_date=pairs[index][0].session_date,
        raw_rs=round(raw_rs, 4),
        raw_momentum=round(raw_momentum, 4),
        plotted_x=plotted_x,
        plotted_y=plotted_y,
        quadrant=quadrant(plotted_x, plotted_y),
        source_series_ids=source_ids,
        source_provider=provider,
        is_current=is_current,
        is_synthetic=False,
        compatibility_signature=signature,
        snapshot_id=snapshot_id if is_current else None,
    )


def relative_return(pairs: Sequence[tuple[DailyBar, DailyBar]], index: int, lookback: int) -> float | None:
    start = index - lookback
    if start < 0:
        return None
    entity, benchmark = pairs[index]
    starting_entity, starting_benchmark = pairs[start]
    if starting_entity.close <= 0 or starting_benchmark.close <= 0:
        return None
    entity_return = entity.close / starting_entity.close - 1
    benchmark_return = benchmark.close / starting_benchmark.close - 1
    return (entity_return - benchmark_return) * 100


def quadrant(plotted_x: float, plotted_y: float) -> str:
    if plotted_x >= 100 and plotted_y >= 100:
        return "leading"
    if plotted_x >= 100:
        return "weakening"
    if plotted_y < 100:
        return "lagging"
    return "improving"


def source_provider(pairs: Sequence[tuple[DailyBar, DailyBar]]) -> str:
    providers = {entity.provider.lower() for entity, _ in pairs} | {benchmark.provider.lower() for _, benchmark in pairs}
    return next(iter(providers)) if len(providers) == 1 else "mixed"


def compatibility_signature(
    *,
    entity_type: str,
    entity_symbol: str,
    benchmark_symbol: str,
    interval_policy: RotationIntervalPolicy,
    provider: str,
    universe_version: str | None,
) -> str:
    payload = {
        "entity_type": entity_type,
        "entity_symbol": entity_symbol,
        "benchmark_symbol": benchmark_symbol,
        "formula_version": ROTATION_FORMULA_VERSION,
        "normalization_version": ROTATION_NORMALIZATION_VERSION,
        "interval": interval_policy.interval,
        "rs_lookback_sessions": interval_policy.rs_lookback_sessions,
        "momentum_lookback_sessions": interval_policy.momentum_lookback_sessions,
        "provider": provider,
        "universe_version": universe_version,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]

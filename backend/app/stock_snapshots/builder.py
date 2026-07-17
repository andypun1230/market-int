from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.models.market import (
    MovingAverageSupport,
    MultiTimeframeTechnicalSignals,
    PriceZone,
    RelativeStrengthItem,
    RiskPlan,
    StockRatingComponents,
    StockRatingItem,
    SupportResistanceResponse,
    VolumeAnalysis,
)
from app.providers.models import CandleData, HistoryData, QuoteData
from app.services.candle_data import build_dependency_quality, build_history_metadata, candles_to_dicts
from app.services.leadership_signal_service import calculate_leadership_signal
from app.services.multi_timeframe import analyze_multi_timeframe
from app.services.pattern_detection import detect_patterns
from app.services.relative_strength import (
    SECTOR_BENCHMARK,
    SYMBOL_SECTOR,
    calculate_return as calculate_rs_return,
    get_status as get_rs_status,
    score_comparison,
    weighted_available_score,
)
from app.services.risk import _build_summary as build_risk_summary
from app.services.risk import _classify_risk, _classify_volatility, _position_size_note, calculate_atr
from app.services.stock_rating import (
    build_explanation,
    build_strengths,
    build_warnings,
    calculate_overall_score,
    get_rating,
    get_risk_control_score,
    get_risk_level,
    get_status as get_rating_status,
)
from app.services.support_resistance import (
    build_price_zones,
    calculate_breakout_level,
    calculate_stop_reference,
    cluster_price_levels,
    find_recent_swing_highs,
    find_recent_swing_lows,
)
from app.services.technical_indicators import calculate_ema, calculate_macd, calculate_rsi
from app.services.timeframe_signal_service import (
    build_indicator_context,
    build_long_factors,
    build_medium_factors,
    build_pattern_factor,
    build_short_factors,
    calculate_timeframe_signal,
    collect_input_statuses,
    derive_overall_status,
    get_history_status,
)
from app.services.trendline import (
    _build_break_status,
    _build_summary as build_trendline_summary,
    _build_trendline_detail,
    _empty_trendline_detail,
    find_swing_highs,
    find_swing_lows,
)
from app.services.volume_analysis import (
    _build_volume_summary,
    _calculate_previous_average_volume,
    _calculate_volume_quality_score,
    _classify_volume_quality,
    _classify_volume_status,
    calculate_relative_volume,
    detect_accumulation_volume,
    detect_breakout_volume,
    detect_climax_run,
    detect_distribution_volume,
    detect_volume_dry_up,
    detect_volume_surge,
)
from app.stock_snapshots.input_bundle import StockDetailInputBundle, build_input_bundle
from app.stock_snapshots.input_planner import StockDetailInputPlanner
from app.stock_snapshots.models import StockAnalysisSnapshot, StockSnapshotSection, iso_after, now_iso
from app.stock_snapshots.provenance import (
    ALGORITHM_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    build_snapshot_metadata,
    current_runtime_provenance,
    is_snapshot_compatible,
)
from app.stock_snapshots.storage import StockSnapshotStorage, unique_snapshot_id


class StockAnalysisSnapshotBuilder:
    algorithm_version = ALGORITHM_VERSION

    def __init__(self, storage: StockSnapshotStorage | None = None) -> None:
        self.storage = storage or StockSnapshotStorage()
        self.planner = StockDetailInputPlanner()

    def build_and_publish(self, symbol: str) -> StockAnalysisSnapshot | None:
        started = time.perf_counter()
        normalized = self.planner.plan(symbol).symbol
        try:
            snapshot = self.build(normalized, started=started)
        except Exception as exc:
            self.storage.set_build_error(normalized, f"{type(exc).__name__}: {exc}")
            return None
        if snapshot.status == "unavailable":
            self.storage.set_build_error(normalized, "selected history unavailable")
            return None
        compatible, reason = is_snapshot_compatible(snapshot)
        if not compatible:
            self.storage.set_build_error(normalized, f"incompatible snapshot not published: {reason}")
            return None
        self.storage.publish_snapshot(snapshot)
        return snapshot

    def build(self, symbol: str, *, started: float | None = None) -> StockAnalysisSnapshot:
        start = started or time.perf_counter()
        plan = self.planner.plan(symbol)
        bundle = build_input_bundle(plan)
        created_at = now_iso()
        if not bundle.selected_history or not bundle.selected_history.candles:
            runtime = current_runtime_provenance()
            return StockAnalysisSnapshot(
                snapshot_id=unique_snapshot_id(plan.symbol, {"status": "unavailable", "symbol": plan.symbol, "input_hash": bundle.input_hash}),
                snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
                symbol=plan.symbol,
                created_at=created_at,
                published_at=created_at,
                expires_at=iso_after(ttl_seconds()),
                stale_until=iso_after(ttl_seconds() + stale_seconds()),
                status="unavailable",
                source_state="unavailable",
                data_mode=runtime.data_mode,
                test_data=runtime.test_data,
                mock_data=runtime.mock_data,
                configuration_signature=runtime.configuration_signature,
                algorithm_version=self.algorithm_version,
                quote_provider=runtime.quote_provider,
                history_provider=runtime.history_provider,
                input_hash=bundle.input_hash,
                coverage_ratio=0.0,
                missing_dependencies=sorted(bundle.unavailable_inputs),
                build_duration_ms=round((time.perf_counter() - start) * 1000),
                metadata={
                    "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
                    "algorithm_version": self.algorithm_version,
                    "data_mode": runtime.data_mode,
                    "test_data": runtime.test_data,
                    "mock_data": runtime.mock_data,
                    "configuration_signature": runtime.configuration_signature,
                    "quote_provider": runtime.quote_provider,
                    "history_provider": runtime.history_provider,
                    "canonical_history_days": plan.history_days,
                    "fetch_duration_ms": bundle.fetch_duration_ms,
                },
            )

        sections = self._build_sections(bundle)
        completed = sum(1 for item in sections.values() if item.status == "complete")
        partial = any(item.status in {"partial", "unavailable"} for item in sections.values())
        status = "partial" if partial else "complete"
        required_available = 2 - sum(1 for key in ("quote", "selected_history") if key in bundle.unavailable_inputs)
        optional_available = len(bundle.benchmark_histories)
        coverage = round((required_available + optional_available) / (2 + len(plan.benchmark_symbols)), 2)
        history = bundle.selected_history
        latest = history.candles[-1]
        published_at = now_iso()
        source_states = [getattr(history, "source_state", None) or ("live" if history.is_live else history.source)]
        if bundle.quote is not None:
            source_states.append(getattr(bundle.quote, "source_state", None) or ("live" if bundle.quote.is_live else bundle.quote.source))
        source_state = aggregate_source_state(source_states)
        history_warnings = validate_history_consistency(plan.symbol, history, bundle.quote)
        metadata = build_snapshot_metadata(
            quote=bundle.quote,
            history=history,
            source_state=source_state,
            latest_history_timestamp=latest.timestamp,
            extra={
                "canonical_history_days": plan.history_days,
                "fetch_duration_ms": bundle.fetch_duration_ms,
                "cache_hits": bundle.cache_hits,
                "provider_history_requests": [{"symbol": plan.symbol, "resolution": plan.resolution, "days": plan.history_days}],
                "compare_included": False,
                "history_warnings": history_warnings,
            },
        )

        payload = {
            "symbol": plan.symbol,
            "input_hash": bundle.input_hash,
            "sections": {key: section.payload for key, section in sections.items()},
            "latest_history_date": latest.timestamp,
        }
        return StockAnalysisSnapshot(
            snapshot_id=unique_snapshot_id(plan.symbol, payload),
            snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
            symbol=plan.symbol,
            created_at=created_at,
            published_at=published_at,
            expires_at=iso_after(ttl_seconds()),
            stale_until=iso_after(ttl_seconds() + stale_seconds()),
            status=status,
            source_state=source_state,
            data_mode=str(metadata["data_mode"]),
            test_data=bool(metadata["test_data"]),
            mock_data=bool(metadata["mock_data"]),
            configuration_signature=str(metadata["configuration_signature"]),
            algorithm_version=self.algorithm_version,
            history_provider=str(metadata["history_provider"]),
            quote_provider=str(metadata["quote_provider"]),
            latest_history_timestamp=latest.timestamp,
            latest_history_date=latest.timestamp,
            input_hash=bundle.input_hash,
            coverage_ratio=coverage,
            warnings=build_snapshot_warnings(bundle, sections) + history_warnings,
            missing_dependencies=sorted(bundle.unavailable_inputs),
            build_duration_ms=round((time.perf_counter() - start) * 1000),
            sections=sections,
            metadata=metadata,
        )

    def _build_sections(self, bundle: StockDetailInputBundle) -> dict[str, StockSnapshotSection]:
        builders: dict[str, Callable[[StockDetailInputBundle], Any]] = {
            "chart": build_chart_section,
            "technical": build_technical_section,
            "support_resistance": build_support_resistance_section,
            "trend": build_trend_section,
            "volume": build_volume_section,
            "risk": build_risk_section,
            "relative_strength": build_relative_strength_section,
            "pattern": build_pattern_section,
            "rating": build_rating_section,
            "signals": build_signals_section,
            "leadership": build_leadership_section,
            "executive_summary": build_executive_summary_section,
            "overall_assessment": build_overall_assessment_section,
        }
        sections: dict[str, StockSnapshotSection] = {}
        for name, fn in builders.items():
            started = time.perf_counter()
            try:
                payload = fn(bundle)
                status = "complete"
                warnings: list[str] = []
                if name == "relative_strength" and getattr(payload, "degraded", False):
                    status = "partial"
                    warnings = [payload.degradation_reason or "Benchmark comparison is partial."]
                sections[name] = StockSnapshotSection(
                    status=status,
                    calculated_at=now_iso(),
                    coverage=1.0 if status == "complete" else 0.5,
                    warnings=warnings,
                    payload=to_jsonable(payload),
                )
            except Exception as exc:
                sections[name] = StockSnapshotSection(
                    status="unavailable",
                    calculated_at=now_iso(),
                    coverage=0.0,
                    warnings=[f"{name} unavailable: {type(exc).__name__}"],
                    payload=None,
                )
        return sections


def build_chart_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    history = require_history(bundle)
    return {
        "history": history.model_dump(),
        "canonical_days": bundle.plan.history_days,
        "windows": {
            "1D": slice_history(history, 2).model_dump(),
            "1W": slice_history(history, 7).model_dump(),
            "1M": slice_history(history, 30).model_dump(),
            "6M": slice_history(history, 180).model_dump(),
            "1Y": slice_history(history, 365).model_dump(),
        },
        "source_history_days": bundle.plan.history_days,
    }


def build_technical_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    history = require_history(bundle)
    closes = [candle.close for candle in history.candles]
    return {
        "symbol": bundle.plan.symbol,
        "current_price": round(closes[-1], 2),
        "ema_10": calculate_ema(closes, 10),
        "ema_20": calculate_ema(closes, 20),
        "ema_50": calculate_ema(closes, 50),
        "ema_150": calculate_ema(closes, 150),
        "ema_200": calculate_ema(closes, 200),
        "rsi_14": calculate_rsi(closes, 14),
        "macd": calculate_macd(closes),
        "return_20d": calculate_rs_return(closes, 20),
        "return_60d": calculate_rs_return(closes, 60),
        "return_252d": calculate_rs_return(closes, 252),
        "data_source": history.source,
        "analysis_is_live": history.is_live,
        "as_of": history.as_of,
    }


def build_support_resistance_section(bundle: StockDetailInputBundle) -> SupportResistanceResponse:
    history = require_history(bundle)
    metadata = metadata_for(history)
    candles = candles_to_dicts(history.candles)
    current_price = candles[-1]["close"]
    closes = [candle["close"] for candle in candles]
    recent_candles = candles[-30:]
    support_levels = find_recent_swing_lows(candles) + [
        min(candle["low"] for candle in recent_candles),
        min(candle["close"] for candle in recent_candles),
    ]
    resistance_levels = find_recent_swing_highs(candles) + [
        max(candle["high"] for candle in recent_candles),
        max(candle["close"] for candle in recent_candles),
    ]
    support_zones = build_price_zones(cluster_price_levels(support_levels), "Repeated swing lows", current_price, "support")
    resistance_zones = build_price_zones(cluster_price_levels(resistance_levels), "Recent swing highs / neckline or breakout area", current_price, "resistance")
    return SupportResistanceResponse(
        symbol=bundle.plan.symbol,
        current_price=round(current_price, 2),
        support_zones=support_zones,
        resistance_zones=resistance_zones,
        breakout_level=calculate_breakout_level(resistance_zones, current_price),
        stop_reference=calculate_stop_reference(support_zones, current_price),
        moving_average_support=MovingAverageSupport(ema_20=calculate_ema(closes, 20), ema_50=calculate_ema(closes, 50)),
        data_source=metadata["data_source"],
        analysis_is_live=metadata["analysis_is_live"],
        fallback_used=metadata["fallback_used"],
        as_of=metadata["as_of"],
        history_quality_score=metadata["history_quality_score"],
    )


def build_trend_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    history = require_history(bundle)
    metadata = metadata_for(history)
    candles = candles_to_dicts(history.candles)
    current_index = len(candles) - 1
    current_price = round(candles[-1]["close"], 2)
    rising_support = _build_trendline_detail(find_swing_lows(candles), current_price, current_index, "rising support")
    falling_resistance = _build_trendline_detail(find_swing_highs(candles), current_price, current_index, "falling resistance")
    trendline_break = _build_break_status(current_price, rising_support, falling_resistance)
    return {
        "symbol": bundle.plan.symbol,
        "current_price": current_price,
        "rising_support": rising_support or _empty_trendline_detail(),
        "falling_resistance": falling_resistance or _empty_trendline_detail(),
        "trendline_break": trendline_break,
        "summary": build_trendline_summary(bundle.plan.symbol, rising_support, falling_resistance, trendline_break),
        "data_source": metadata["data_source"],
        "analysis_is_live": metadata["analysis_is_live"],
        "fallback_used": metadata["fallback_used"],
        "as_of": metadata["as_of"],
        "history_quality_score": metadata["history_quality_score"],
    }


def build_volume_section(bundle: StockDetailInputBundle) -> VolumeAnalysis:
    history = require_history(bundle)
    metadata = metadata_for(history)
    candles = candles_to_dicts(history.candles)
    current_volume = int(candles[-1]["volume"])
    average_volume_20 = _calculate_previous_average_volume(candles, 20)
    relative_volume = calculate_relative_volume(current_volume, average_volume_20)
    breakout_volume = detect_breakout_volume(candles, relative_volume)
    distribution_volume = detect_distribution_volume(candles)
    accumulation_volume = detect_accumulation_volume(candles)
    dry_up = detect_volume_dry_up(relative_volume)
    climax_run = detect_climax_run(candles)
    signals: list[str] = []
    if detect_volume_surge(relative_volume):
        signals.append("Volume Surge")
    if breakout_volume:
        signals.append("Breakout Volume")
    if accumulation_volume:
        signals.append("Accumulation Volume")
    if distribution_volume:
        signals.append("Distribution Volume")
    if dry_up:
        signals.append("Volume Dry-Up")
    if climax_run:
        signals.append("Climax Run")
    quality_score = _calculate_volume_quality_score(relative_volume, breakout_volume, accumulation_volume, distribution_volume, dry_up, climax_run)
    quality = _classify_volume_quality(quality_score)
    return VolumeAnalysis(
        symbol=bundle.plan.symbol,
        average_volume_20=average_volume_20,
        relative_volume=relative_volume,
        status=_classify_volume_status(relative_volume),
        signals=signals,
        volume_quality=quality,
        volume_quality_score=quality_score,
        distribution_volume=distribution_volume,
        accumulation_volume=accumulation_volume,
        dry_up=dry_up,
        climax_run=climax_run,
        breakout_volume=breakout_volume,
        summary=_build_volume_summary(breakout_volume, accumulation_volume, distribution_volume, dry_up, climax_run, quality),
        data_source=metadata["data_source"],
        analysis_is_live=metadata["analysis_is_live"],
        fallback_used=metadata["fallback_used"],
        as_of=metadata["as_of"],
        history_quality_score=metadata["history_quality_score"],
    )


def build_risk_section(bundle: StockDetailInputBundle) -> RiskPlan:
    history = require_history(bundle)
    metadata = metadata_for(history)
    candles = candles_to_dicts(history.candles)
    current_price = round(candles[-1]["close"], 2)
    support_resistance = build_support_resistance_section(bundle)
    atr_14 = calculate_atr(candles, 14)
    fallback_atr = atr_14 if atr_14 is not None else current_price * 0.03
    entry = support_resistance.breakout_level or current_price
    stop_loss = support_resistance.stop_reference or current_price - 2 * fallback_atr
    if stop_loss >= entry:
        stop_loss = current_price - 2 * fallback_atr
    risk_amount = max(entry - stop_loss, 0.01)
    target_1 = entry + risk_amount
    target_2 = entry + 2 * risk_amount
    risk_percent = round(risk_amount / entry * 100, 2) if entry > 0 else 0
    risk_reward_target_1 = round((target_1 - entry) / risk_amount, 2)
    risk_reward_target_2 = round((target_2 - entry) / risk_amount, 2)
    risk_level = _classify_risk(risk_percent)
    return RiskPlan(
        symbol=bundle.plan.symbol,
        current_price=current_price,
        entry=round(entry, 2),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        atr_14=atr_14,
        risk_percent=risk_percent,
        reward_percent_target_1=round((target_1 - entry) / entry * 100, 2) if entry > 0 else 0,
        reward_percent_target_2=round((target_2 - entry) / entry * 100, 2) if entry > 0 else 0,
        risk_reward_target_1=risk_reward_target_1,
        risk_reward_target_2=risk_reward_target_2,
        volatility_level=_classify_volatility(atr_14, current_price),
        risk_level=risk_level,
        position_size_note=_position_size_note(risk_level),
        summary=build_risk_summary(bundle.plan.symbol, risk_level, risk_reward_target_1),
        data_quality=build_dependency_quality(metadata, mock_components=["pattern_levels"]),
    )


def build_relative_strength_section(bundle: StockDetailInputBundle) -> RelativeStrengthItem:
    history = require_history(bundle)
    stock_closes = [candle.close for candle in history.candles]
    sector = SYMBOL_SECTOR.get(bundle.plan.symbol, "Market")
    sector_benchmark = SECTOR_BENCHMARK.get(sector, "SPY")
    spy_closes = closes_for(bundle.benchmark_histories.get("SPY"))
    qqq_closes = closes_for(bundle.benchmark_histories.get("QQQ"))
    sector_closes = closes_for(bundle.benchmark_histories.get(sector_benchmark))
    return_5d = calculate_rs_return(stock_closes, 5)
    return_20d = calculate_rs_return(stock_closes, 20)
    return_60d = calculate_rs_return(stock_closes, 59)
    benchmark_return_20d = calculate_rs_return(spy_closes, 20)
    qqq_return_20d = calculate_rs_return(qqq_closes, 20)
    sector_return_20d = calculate_rs_return(sector_closes, 20)
    rs_vs_spy = score_comparison(return_20d, benchmark_return_20d, spy_closes)
    rs_vs_qqq = score_comparison(return_20d, qqq_return_20d, qqq_closes)
    rs_vs_sector = score_comparison(return_20d, sector_return_20d, sector_closes)
    overall = weighted_available_score([(rs_vs_spy, 0.4, spy_closes), (rs_vs_qqq, 0.3, qqq_closes), (rs_vs_sector, 0.3, sector_closes)])
    requested = ["SPY", "QQQ", sector_benchmark]
    available = [symbol for symbol, closes in [("SPY", spy_closes), ("QQQ", qqq_closes), (sector_benchmark, sector_closes)] if closes]
    missing = [symbol for symbol in requested if symbol not in available]
    coverage = round(len(available) / len(requested), 2)
    return RelativeStrengthItem(
        symbol=bundle.plan.symbol,
        sector=sector,
        rs_vs_spy=rs_vs_spy,
        rs_vs_qqq=rs_vs_qqq,
        rs_vs_sector=rs_vs_sector,
        return_5d=return_5d,
        return_20d=return_20d,
        return_60d=return_60d,
        benchmark_return_20d=benchmark_return_20d,
        sector_return_20d=sector_return_20d,
        overall_rs_score=overall,
        rank=0,
        status=get_rs_status(overall),
        explanation=f"{bundle.plan.symbol} relative strength uses cached benchmark comparisons." if not missing else f"{bundle.plan.symbol} relative strength is partial; missing cached benchmark history: {', '.join(missing)}.",
        data_source="snapshot-cache",
        analysis_is_live=history.is_live and bool(available),
        fallback_used=history.fallback_used,
        as_of=history.as_of,
        history_quality_score=metadata_for(history)["history_quality_score"],
        comparisons_requested=requested,
        comparisons_available=available,
        comparisons_missing=missing,
        coverage_ratio=coverage,
        degraded=bool(missing),
        degradation_reason=f"Missing cached benchmark history: {', '.join(missing)}" if missing else None,
        confidence_state="full" if coverage == 1 else "partial" if coverage >= 0.5 else "limited",
    )


def build_pattern_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    return detect_patterns(bundle.plan.symbol).model_dump()


def build_rating_section(bundle: StockDetailInputBundle) -> StockRatingItem:
    relative_strength = build_relative_strength_section(bundle)
    volume = build_volume_section(bundle)
    risk = build_risk_section(bundle)
    support = build_support_resistance_section(bundle)
    trend = build_trend_section(bundle)
    pattern_quality = max(45, min(85, 55 + (10 if volume.accumulation_volume else 0) + (8 if volume.breakout_volume else 0) - (10 if volume.distribution_volume else 0)))
    sector_strength = max(45, min(90, relative_strength.rs_vs_sector))
    components = StockRatingComponents(
        relative_strength=relative_strength.overall_rs_score,
        pattern_quality=pattern_quality,
        sector_strength=sector_strength,
        market_alignment=70,
        institutional_support=60 if volume.distribution_volume else 70,
        risk_control=get_risk_control_score(risk.risk_level),
    )
    overall = calculate_overall_score(components)
    rating_status = get_rating_status(overall)
    risk_level = get_risk_level(components.risk_control)
    return StockRatingItem(
        symbol=bundle.plan.symbol,
        overall_score=overall,
        rating=get_rating(overall),
        status=rating_status,
        components=components,
        risk_level=risk_level,
        strengths=build_strengths(bundle.plan.symbol, components, "Uptrend Under Pressure"),
        warnings=build_warnings(components, risk_level),
        explanation=build_explanation(bundle.plan.symbol, components, rating_status),
        data_quality={
            "overall_mode": aggregate_source_state([source_status_from_payload(relative_strength.model_dump()), source_status_from_payload(volume.model_dump()), source_status_from_payload(support.model_dump()), source_status_from_payload(trend)]),
            "history_quality_score": metadata_for(require_history(bundle))["history_quality_score"],
        },
    )


def build_signals_section(bundle: StockDetailInputBundle) -> MultiTimeframeTechnicalSignals:
    history = require_history(bundle)
    support = to_jsonable(build_support_resistance_section(bundle))
    trend = build_trend_section(bundle)
    volume = to_jsonable(build_volume_section(bundle))
    relative_strength = to_jsonable(build_relative_strength_section(bundle))
    patterns = build_pattern_section(bundle)
    closes = [float(candle.close) for candle in history.candles if candle.close and candle.close > 0]
    indicators = build_indicator_context(closes)
    statuses = collect_input_statuses(get_history_status(history), support, trend, volume, relative_strength)
    pattern_factor = build_pattern_factor(patterns, support)
    factors = {
        "short": build_short_factors(indicators, statuses, volume, relative_strength, support, pattern_factor),
        "medium": build_medium_factors(indicators, statuses, volume, relative_strength, support, trend, pattern_factor),
        "long": build_long_factors(indicators, statuses, relative_strength, support),
    }
    signals = {timeframe: calculate_timeframe_signal(timeframe, items, history.as_of) for timeframe, items in factors.items()}
    return MultiTimeframeTechnicalSignals(
        short=signals["short"],
        medium=signals["medium"],
        long=signals["long"],
        overallDataStatus=derive_overall_status([signals["short"].dataStatus, signals["medium"].dataStatus, signals["long"].dataStatus]),
        generatedAt=now_iso(),
        methodologyVersion="1",
    )


def build_leadership_section(bundle: StockDetailInputBundle) -> Any:
    return calculate_leadership_signal(
        bundle.plan.symbol,
        relative_strength=to_jsonable(build_relative_strength_section(bundle)),
        volume_analysis=to_jsonable(build_volume_section(bundle)),
        multi_timeframe_signals=to_jsonable(build_signals_section(bundle)),
        stock_rating=to_jsonable(build_rating_section(bundle)),
    )


def build_executive_summary_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    rating = build_rating_section(bundle)
    risk = build_risk_section(bundle)
    return {
        "headline": rating.status,
        "body": rating.explanation,
        "evidence": rating.strengths[:2] + rating.warnings[:2],
        "risk_level": risk.risk_level,
        "source": "snapshot",
    }


def build_overall_assessment_section(bundle: StockDetailInputBundle) -> dict[str, Any]:
    rating = build_rating_section(bundle)
    relative_strength = build_relative_strength_section(bundle)
    return {
        "symbol": bundle.plan.symbol,
        "score": rating.overall_score,
        "rating": rating.rating,
        "status": rating.status,
        "relative_strength_status": relative_strength.status,
        "compare_required": False,
    }


def require_history(bundle: StockDetailInputBundle) -> HistoryData:
    if bundle.selected_history is None or not bundle.selected_history.candles:
        raise ValueError("Selected history is unavailable")
    return bundle.selected_history


def metadata_for(history: HistoryData) -> dict[str, Any]:
    validation = {"valid": bool(history.candles), "quality_score": 100 if len(history.candles) >= 60 else 60, "warnings": [], "errors": []}
    return build_history_metadata(history, validation)


def slice_history(history: HistoryData, days: int) -> HistoryData:
    candles = history.candles[-days:]
    return history.model_copy(update={"candles": candles, "requested_days": days, "returned_candles": len(candles)})


def closes_for(history: HistoryData | None) -> list[float]:
    return [candle.close for candle in history.candles] if history else []


def build_snapshot_warnings(bundle: StockDetailInputBundle, sections: dict[str, StockSnapshotSection]) -> list[str]:
    warnings = [f"{key}: {value}" for key, value in sorted(bundle.unavailable_inputs.items()) if key != "selected_history"]
    warnings.extend(f"{name}: {', '.join(section.warnings)}" for name, section in sections.items() if section.warnings)
    return warnings


def validate_history_consistency(symbol: str, history: HistoryData, quote: QuoteData | None) -> list[str]:
    warnings: list[str] = []
    normalized = symbol.upper()
    if history.symbol.upper() != normalized:
        warnings.append(f"history symbol mismatch: {history.symbol}")
    if quote is not None and quote.symbol.upper() != normalized:
        warnings.append(f"quote symbol mismatch: {quote.symbol}")
    if len(history.candles) < 60:
        warnings.append("insufficient selected history")
    seen: set[str] = set()
    future_count = 0
    previous: datetime | None = None
    now = datetime.now(timezone.utc)
    for candle in history.candles:
        if candle.timestamp in seen:
            warnings.append("duplicate history bars")
            break
        seen.add(candle.timestamp)
        try:
            stamp = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        except ValueError:
            warnings.append("invalid history timestamp")
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if previous and stamp < previous:
            warnings.append("history bars out of order")
            break
        previous = stamp
        if stamp > now:
            future_count += 1
    if future_count:
        warnings.append("future history bars present")
    latest = previous
    if latest:
        age_days = (now - latest).total_seconds() / 86400
        if age_days > 10:
            warnings.append(f"latest history is unusually old: {round(age_days, 1)} days")
    if quote and history.candles:
        latest_close = history.candles[-1].close
        if latest_close > 0 and abs((quote.price - latest_close) / latest_close) >= 0.18:
            warnings.append("live quote and latest history close differ materially")
    return sorted(set(warnings))


def aggregate_source_state(states: list[str | None]) -> str:
    clean = [str(item) for item in states if item]
    if not clean:
        return "unavailable"
    if any(item == "live" for item in clean) and len(set(clean)) > 1:
        return "mixed"
    if "stale" in clean:
        return "stale"
    if len(set(clean)) > 1:
        return "mixed"
    return clean[0]


def source_status_from_payload(payload: dict[str, Any]) -> str:
    if payload.get("analysis_is_live") or payload.get("is_live"):
        return "live"
    if payload.get("fallback_used"):
        return "fallback"
    return str(payload.get("data_source") or payload.get("source_state") or "mixed")


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def ttl_seconds() -> int:
    return int_env("STOCK_SNAPSHOT_TTL_SECONDS", 900)


def stale_seconds() -> int:
    return int_env("STOCK_SNAPSHOT_STALE_SECONDS", 86400)


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

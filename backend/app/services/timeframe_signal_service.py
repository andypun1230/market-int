from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.models.market import (
    MultiTimeframeTechnicalSignals,
    TimeframeSignalEvidence,
    TimeframeSignalInput,
    TimeframeTechnicalSignal,
)
from app.services.candle_data import get_symbol_history
from app.services.technical_indicators import calculate_ema, calculate_macd, calculate_rsi

TimeframeKey = Literal["short", "medium", "long"]

METHODOLOGY_VERSION = "1"
SIGNAL_BANDS = [
    (0, 19, "strong_bearish"),
    (20, 39, "bearish"),
    (40, 60, "neutral"),
    (61, 80, "bullish"),
    (81, 100, "strong_bullish"),
]
TIMEFRAME_HORIZONS: dict[TimeframeKey, str] = {
    "short": "1–10 trading days",
    "medium": "2–8 weeks",
    "long": "3–12 months",
}


@dataclass(frozen=True)
class TechnicalSignalFactor:
    key: str
    label: str
    timeframe: TimeframeKey
    value: Any
    contribution: float | None
    weight: float
    source_status: str

    @property
    def available(self) -> bool:
        return self.contribution is not None and self.source_status != "mock"


def build_multi_timeframe_technical_signals(
    symbol: str,
    *,
    support_resistance: dict[str, Any] | None = None,
    trendline: dict[str, Any] | None = None,
    volume_analysis: dict[str, Any] | None = None,
    relative_strength: dict[str, Any] | None = None,
    patterns: dict[str, Any] | None = None,
) -> MultiTimeframeTechnicalSignals:
    normalized = symbol.upper()
    history, validation = get_symbol_history(normalized, days=365, minimum_candles=20)
    history_status = get_history_status(history)
    candles = [] if history_status == "mock" else list(history.candles)
    closes = [float(candle.close) for candle in candles if candle.close and candle.close > 0]
    indicators = build_indicator_context(closes)
    input_statuses = collect_input_statuses(
        history_status,
        support_resistance,
        trendline,
        volume_analysis,
        relative_strength,
    )
    pattern_factor = build_pattern_factor(patterns, support_resistance)
    as_of = history.as_of or max(
        [
            text_or_none(source.get("as_of") if isinstance(source, dict) else None) or ""
            for source in [support_resistance, trendline, volume_analysis, relative_strength]
        ],
        default="",
    ) or None

    timeframe_factors = {
        "short": build_short_factors(indicators, input_statuses, volume_analysis, relative_strength, support_resistance, pattern_factor),
        "medium": build_medium_factors(indicators, input_statuses, volume_analysis, relative_strength, support_resistance, trendline, pattern_factor),
        "long": build_long_factors(indicators, input_statuses, relative_strength, support_resistance),
    }
    signals = {
        timeframe: calculate_timeframe_signal(timeframe, factors, as_of)
        for timeframe, factors in timeframe_factors.items()
    }

    return MultiTimeframeTechnicalSignals(
        short=signals["short"],
        medium=signals["medium"],
        long=signals["long"],
        overallDataStatus=derive_overall_status([signals["short"].dataStatus, signals["medium"].dataStatus, signals["long"].dataStatus]),
        generatedAt=datetime.now(timezone.utc).isoformat(),
        methodologyVersion=METHODOLOGY_VERSION,
    )


def build_indicator_context(closes: list[float]) -> dict[str, Any]:
    current = closes[-1] if closes else None
    return {
        "current": current,
        "ema10": calculate_ema(closes, 10),
        "ema20": calculate_ema(closes, 20),
        "ema50": calculate_ema(closes, 50),
        "ema150": calculate_ema(closes, 150),
        "ema200": calculate_ema(closes, 200),
        "ema10_slope": calculate_ema_slope(closes, 10, 5),
        "ema20_slope": calculate_ema_slope(closes, 20, 10),
        "ema50_slope": calculate_ema_slope(closes, 50, 20),
        "ema150_slope": calculate_ema_slope(closes, 150, 30),
        "ema200_slope": calculate_ema_slope(closes, 200, 30),
        "return5": calculate_return(closes, 5),
        "return10": calculate_return(closes, 10),
        "return20": calculate_return(closes, 20),
        "return60": calculate_return(closes, 60),
        "return126": calculate_return(closes, 126),
        "return252": calculate_return(closes, 252),
        "rsi14": calculate_rsi(closes, 14),
        "macd": calculate_macd(closes),
        "history_count": len(closes),
    }


def build_short_factors(
    indicators: dict[str, Any],
    statuses: dict[str, str],
    volume: dict[str, Any] | None,
    relative_strength: dict[str, Any] | None,
    support_resistance: dict[str, Any] | None,
    pattern_factor: TechnicalSignalFactor | None,
) -> list[TechnicalSignalFactor]:
    current = indicators["current"]
    factors = [
        compare_factor("above_ema10", "Price is above EMA10", "short", current, indicators["ema10"], 0.15, statuses["history"]),
        compare_factor("above_ema20", "Price is above EMA20", "short", current, indicators["ema20"], 0.15, statuses["history"]),
        compare_factor("ema10_above_ema20", "EMA10 is above EMA20", "short", indicators["ema10"], indicators["ema20"], 0.15, statuses["history"]),
        numeric_factor("short_ema_slope", "Short-term averages are rising", "short", average_available([indicators["ema10_slope"], indicators["ema20_slope"]]), 0.10, statuses["history"], slope_contribution),
        numeric_factor("short_momentum", "Short-term momentum", "short", average_available([indicators["return5"], indicators["return10"], indicators["macd"].get("histogram")]), 0.20, statuses["history"], momentum_contribution),
        rs_factor("short_relative_strength", "Relative strength is constructive", "short", relative_strength, 0.10, statuses["relative_strength"]),
        volume_factor("volume_confirmation", "Volume confirms the move", "short", volume, 0.10, statuses["volume"]),
        breakout_factor("breakout_state", "Current breakout/support state", "short", current, support_resistance, 0.05, statuses["support_resistance"]),
    ]
    if pattern_factor is not None:
        factors.append(pattern_factor)
    return factors


def build_medium_factors(
    indicators: dict[str, Any],
    statuses: dict[str, str],
    volume: dict[str, Any] | None,
    relative_strength: dict[str, Any] | None,
    support_resistance: dict[str, Any] | None,
    trendline: dict[str, Any] | None,
    pattern_factor: TechnicalSignalFactor | None,
) -> list[TechnicalSignalFactor]:
    current = indicators["current"]
    factors = [
        compare_factor("above_ema20", "Price is above EMA20", "medium", current, indicators["ema20"], 0.15, statuses["history"]),
        compare_factor("above_ema50", "Price is above EMA50", "medium", current, indicators["ema50"], 0.15, statuses["history"]),
        compare_factor("ema20_above_ema50", "EMA20 is above EMA50", "medium", indicators["ema20"], indicators["ema50"], 0.15, statuses["history"]),
        numeric_factor("medium_ema_slope", "EMA20 and EMA50 are rising", "medium", average_available([indicators["ema20_slope"], indicators["ema50_slope"]]), 0.10, statuses["history"], slope_contribution),
        numeric_factor("medium_performance", "20D and 60D performance", "medium", average_available([indicators["return20"], indicators["return60"]]), 0.10, statuses["history"], momentum_contribution),
        rs_factor("medium_relative_strength", "Medium-term relative strength", "medium", relative_strength, 0.15, statuses["relative_strength"]),
        trendline_factor("trendline_structure", "Rising support trendline", trendline, 0.10, statuses["trendline"]),
        support_position_factor("support_resistance_position", "Position versus support/resistance", "medium", current, support_resistance, 0.05, statuses["support_resistance"]),
        market_alignment_factor("market_sector_alignment", "Market and sector alignment", "medium", relative_strength, volume, 0.05, derive_status([statuses["relative_strength"], statuses["volume"]])),
    ]
    if pattern_factor is not None:
        factors.append(TechnicalSignalFactor(
            key="compatible_pattern",
            label=pattern_factor.label,
            timeframe="medium",
            value=pattern_factor.value,
            contribution=pattern_factor.contribution,
            weight=min(pattern_factor.weight, 0.10),
            source_status=pattern_factor.source_status,
        ))
    return factors


def build_long_factors(
    indicators: dict[str, Any],
    statuses: dict[str, str],
    relative_strength: dict[str, Any] | None,
    support_resistance: dict[str, Any] | None,
) -> list[TechnicalSignalFactor]:
    current = indicators["current"]
    return [
        compare_factor("above_ema50", "Price is above EMA50", "long", current, indicators["ema50"], 0.10, statuses["history"]),
        compare_factor("above_ema150", "Price is above EMA150", "long", current, indicators["ema150"], 0.15, statuses["history"]),
        compare_factor("above_ema200", "Price is above EMA200", "long", current, indicators["ema200"], 0.15, statuses["history"]),
        numeric_factor("long_ema_stack", "EMA50 is above major averages", "long", average_available([
            compare_values(indicators["ema50"], indicators["ema150"]),
            compare_values(indicators["ema50"], indicators["ema200"]),
        ]), 0.15, statuses["history"], identity_contribution),
        numeric_factor("major_average_slopes", "Major averages are rising", "long", average_available([indicators["ema150_slope"], indicators["ema200_slope"]]), 0.10, statuses["history"], slope_contribution),
        numeric_factor("long_performance", "6M and 1Y performance", "long", average_available([indicators["return126"], indicators["return252"]]), 0.10, statuses["history"], momentum_contribution),
        rs_factor("long_relative_strength", "Long-term relative strength", "long", relative_strength, 0.10, statuses["relative_strength"]),
        stage_factor("major_trend_structure", "Major trend structure", current, indicators, 0.10, statuses["history"]),
        market_alignment_factor("sector_market_alignment", "Sector and market alignment", "long", relative_strength, None, 0.05, statuses["relative_strength"]),
        support_position_factor("major_support_position", "Price remains above key support", "long", current, support_resistance, 0.05, statuses["support_resistance"]),
    ]


def calculate_timeframe_signal(timeframe: TimeframeKey, factors: list[TechnicalSignalFactor], as_of: str | None) -> TimeframeTechnicalSignal:
    required = len(factors)
    available = [factor for factor in factors if factor.available]
    available_weight = sum(factor.weight for factor in available)
    configured_weight = sum(factor.weight for factor in factors)
    minimum_inputs = 4
    minimum_weight = 0.60 if timeframe == "long" else 0.55

    if len(available) < minimum_inputs or not configured_weight or available_weight / configured_weight < minimum_weight:
        return unavailable_signal(timeframe, factors, as_of)

    weighted_sum = sum((factor.contribution or 0) * factor.weight for factor in available)
    normalized = weighted_sum / available_weight
    score = round(max(0, min(100, (normalized + 1) * 50)))
    signal = map_score_to_signal(score)
    positive = build_evidence(available, positive=True)
    negative = build_evidence(available, positive=False)
    data_status = derive_timeframe_status([factor.source_status for factor in available], len(available) < required)
    strength = calculate_signal_strength(score, len(available) / required, positive, negative)

    return TimeframeTechnicalSignal(
        timeframe=timeframe,
        horizonLabel=TIMEFRAME_HORIZONS[timeframe],
        signal=signal,
        score=score,
        strength=strength,
        headline=build_headline(timeframe, signal),
        explanation=build_explanation(timeframe, signal, positive, negative),
        positiveEvidence=positive[:3],
        negativeEvidence=negative[:3],
        availableInputs=len(available),
        requiredInputs=required,
        dataStatus=data_status,
        asOf=as_of,
        inputs=[factor_to_input(factor) for factor in factors],
    )


def unavailable_signal(timeframe: TimeframeKey, factors: list[TechnicalSignalFactor], as_of: str | None) -> TimeframeTechnicalSignal:
    return TimeframeTechnicalSignal(
        timeframe=timeframe,
        horizonLabel=TIMEFRAME_HORIZONS[timeframe],
        signal="unavailable",
        score=None,
        strength="unavailable",
        headline=f"{display_timeframe(timeframe)} signal unavailable.",
        explanation=f"{display_timeframe(timeframe)} technical data is insufficient for a reliable signal.",
        positiveEvidence=[],
        negativeEvidence=[],
        availableInputs=sum(1 for factor in factors if factor.available),
        requiredInputs=len(factors),
        dataStatus="unavailable",
        asOf=as_of,
        inputs=[factor_to_input(factor) for factor in factors],
    )


def map_score_to_signal(score: int) -> str:
    for low, high, signal in SIGNAL_BANDS:
        if low <= score <= high:
            return signal
    return "neutral"


def calculate_signal_strength(
    score: int,
    completeness: float,
    positive: list[TimeframeSignalEvidence],
    negative: list[TimeframeSignalEvidence],
) -> str:
    if 45 <= score <= 55 or completeness < 0.65:
        return "weak"
    if (score <= 15 or score >= 85) and completeness >= 0.8 and min(len(positive), len(negative)) == 0:
        return "strong"
    if score <= 30 or score >= 70:
        return "moderate" if positive and negative else "strong"
    return "moderate"


def build_evidence(factors: list[TechnicalSignalFactor], *, positive: bool) -> list[TimeframeSignalEvidence]:
    selected = [
        factor for factor in factors
        if factor.contribution is not None and ((factor.contribution > 0.1) if positive else (factor.contribution < -0.1))
    ]
    selected.sort(key=lambda factor: abs(factor.contribution or 0) * factor.weight, reverse=True)
    return [
        TimeframeSignalEvidence(
            key=factor.key,
            label=factor.label,
            value=factor.value,
            sourceStatus=factor.source_status,
        )
        for factor in selected
    ]


def factor_to_input(factor: TechnicalSignalFactor) -> TimeframeSignalInput:
    return TimeframeSignalInput(
        key=factor.key,
        label=factor.label,
        timeframe=factor.timeframe,
        contribution=round(factor.contribution, 3) if factor.contribution is not None else None,
        weight=factor.weight,
        value=factor.value,
        sourceStatus=factor.source_status,
        available=factor.available,
    )


def build_headline(timeframe: TimeframeKey, signal: str) -> str:
    label = signal.replace("_", " ")
    if signal == "unavailable":
        return f"{display_timeframe(timeframe)} signal unavailable."
    return f"{display_timeframe(timeframe)} trend is {label}."


def build_explanation(
    timeframe: TimeframeKey,
    signal: str,
    positive: list[TimeframeSignalEvidence],
    negative: list[TimeframeSignalEvidence],
) -> str:
    if signal == "unavailable":
        return f"{display_timeframe(timeframe)} history and indicator coverage are not sufficient for a reliable signal."
    leading = positive if signal in {"bullish", "strong_bullish"} else negative if signal in {"bearish", "strong_bearish"} else positive
    limiting = negative if leading is positive else positive
    lead_text = join_labels(leading[:2]) or "Evidence is balanced"
    if limiting:
        return f"{lead_text}. Limiting factor: {limiting[0].label.lower()}."
    return f"{lead_text}. Evidence is broadly aligned."


def compare_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    first: float | None,
    second: float | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    return TechnicalSignalFactor(key, label, timeframe, build_compare_value(first, second), compare_values(first, second), weight, status)


def numeric_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    value: float | None,
    weight: float,
    status: str,
    mapper: Any,
) -> TechnicalSignalFactor:
    return TechnicalSignalFactor(key, label, timeframe, round(value, 2) if value is not None else None, mapper(value), weight, status)


def rs_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    relative_strength: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    score = number(relative_strength, "overall_rs_score")
    contribution = None
    if score is not None:
        contribution = max(-1, min(1, (score - 50) / 35))
    return TechnicalSignalFactor(key, label, timeframe, score, contribution, weight, status)


def volume_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    volume: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    score = number(volume, "volume_quality_score")
    contribution = None if score is None else max(-1, min(1, (score - 50) / 40))
    if volume and volume.get("distribution_volume"):
        contribution = min(contribution or 0, -0.8)
    elif volume and (volume.get("breakout_volume") or volume.get("accumulation_volume")):
        contribution = max(contribution or 0, 0.5)
    return TechnicalSignalFactor(key, label, timeframe, score, contribution, weight, status)


def breakout_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    current: float | None,
    support_resistance: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    if current is None or not support_resistance:
        return TechnicalSignalFactor(key, label, timeframe, None, None, weight, status)
    breakout = number(support_resistance, "breakout_level")
    stop = number(support_resistance, "stop_reference")
    if breakout and current >= breakout:
        return TechnicalSignalFactor(key, "Price has confirmed above breakout level", timeframe, current, 1, weight, status)
    if stop and current <= stop:
        return TechnicalSignalFactor(key, "Price is below invalidation level", timeframe, current, -1, weight, status)
    return TechnicalSignalFactor(key, label, timeframe, current, 0, weight, status)


def support_position_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    current: float | None,
    support_resistance: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    if current is None or not support_resistance:
        return TechnicalSignalFactor(key, label, timeframe, None, None, weight, status)
    stop = number(support_resistance, "stop_reference")
    breakout = number(support_resistance, "breakout_level")
    if stop and current < stop:
        contribution = -1
    elif breakout and current > breakout:
        contribution = 0.8
    elif stop and current > stop:
        contribution = 0.4
    else:
        contribution = 0
    return TechnicalSignalFactor(key, label, timeframe, current, contribution, weight, status)


def trendline_factor(
    key: str,
    label: str,
    trendline: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    if not trendline:
        return TechnicalSignalFactor(key, label, "medium", None, None, weight, status)
    broken = bool(trendline.get("trendline_break", {}).get("broken"))
    rising = bool(trendline.get("rising_support", {}).get("detected"))
    if broken:
        contribution = -1
        value = "broken"
    elif rising:
        contribution = 1
        value = trendline.get("rising_support", {}).get("status")
    else:
        contribution = 0
        value = "not detected"
    return TechnicalSignalFactor(key, label, "medium", value, contribution, weight, status)


def market_alignment_factor(
    key: str,
    label: str,
    timeframe: TimeframeKey,
    relative_strength: dict[str, Any] | None,
    volume: dict[str, Any] | None,
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    rs = number(relative_strength, "rs_vs_sector")
    volume_score = number(volume, "volume_quality_score") if volume else None
    contribution = average_available([
        None if rs is None else max(-1, min(1, (rs - 50) / 35)),
        None if volume_score is None else max(-1, min(1, (volume_score - 50) / 40)),
    ])
    return TechnicalSignalFactor(key, label, timeframe, round(contribution, 2) if contribution is not None else None, contribution, weight, status)


def stage_factor(
    key: str,
    label: str,
    current: float | None,
    indicators: dict[str, Any],
    weight: float,
    status: str,
) -> TechnicalSignalFactor:
    ema50 = indicators.get("ema50")
    ema150 = indicators.get("ema150")
    ema200 = indicators.get("ema200")
    if current is None or ema50 is None or (ema150 is None and ema200 is None):
        return TechnicalSignalFactor(key, label, "long", None, None, weight, status)
    major = ema200 or ema150
    if current > ema50 and ema50 > major:
        contribution = 1
        value = "major uptrend"
    elif current < ema50 and ema50 < major:
        contribution = -1
        value = "major downtrend"
    else:
        contribution = 0
        value = "transitional"
    return TechnicalSignalFactor(key, label, "long", value, contribution, weight, status)


def build_pattern_factor(patterns: dict[str, Any] | None, support_resistance: dict[str, Any] | None) -> TechnicalSignalFactor | None:
    pattern_list = patterns.get("patterns", []) if isinstance(patterns, dict) else []
    pattern = pattern_list[0] if pattern_list else None
    if not isinstance(pattern, dict) or not is_pattern_compatible(pattern, support_resistance):
        return None
    direction = str(pattern.get("direction", "")).lower()
    contribution = 1 if direction == "bullish" else -1 if direction == "bearish" else 0
    return TechnicalSignalFactor(
        key="compatible_pattern",
        label="Live-compatible pattern supports current setup",
        timeframe="short",
        value=pattern.get("name"),
        contribution=contribution,
        weight=0.10,
        source_status="live",
    )


def is_pattern_compatible(pattern: dict[str, Any], support_resistance: dict[str, Any] | None) -> bool:
    source = str(pattern.get("data_source") or "").lower()
    if source in {"mock", "fallback"} or "mock" in source or "fallback" in source or pattern.get("is_live") is False:
        return False
    if not support_resistance:
        return True
    key_levels = pattern.get("key_levels") or {}
    breakout = as_float(key_levels.get("breakout"))
    current_breakout = number(support_resistance, "breakout_level")
    if breakout is None or current_breakout is None:
        return True
    return abs((breakout - current_breakout) / current_breakout) < 0.08


def get_history_status(history: Any) -> str:
    source = str(getattr(history, "source", "") or "").lower()
    if getattr(history, "is_stale", False):
        return "stale"
    if getattr(history, "fallback_used", False) or "fallback" in source:
        return "fallback"
    if source == "mock":
        return "mock"
    if getattr(history, "is_live", False):
        return "live"
    if source:
        return "cached"
    return "unavailable"


def collect_input_statuses(history_status: str, *sources: dict[str, Any] | None) -> dict[str, str]:
    names = ["support_resistance", "trendline", "volume", "relative_strength"]
    statuses = {"history": history_status}
    for name, source in zip(names, sources):
        statuses[name] = get_source_status(source)
    return statuses


def get_source_status(source: dict[str, Any] | None) -> str:
    if not source:
        return "unavailable"
    data_source = str(source.get("data_source") or "").lower()
    if source.get("is_stale"):
        return "stale"
    if source.get("fallback_used") or "fallback" in data_source:
        return "fallback"
    if "mock" in data_source:
        return "mock"
    if source.get("analysis_is_live") or source.get("is_live") or "live" in data_source:
        return "live"
    if source.get("as_of") or data_source:
        return "cached"
    return "unavailable"


def derive_timeframe_status(statuses: list[str], partial: bool) -> str:
    clean = [status for status in statuses if status != "unavailable"]
    if not clean:
        return "unavailable"
    if "stale" in clean:
        return "stale"
    if "fallback" in clean:
        return "fallback" if len(set(clean)) == 1 else "mixed"
    if partial:
        return "partial"
    if len(set(clean)) > 1:
        return "mixed"
    return clean[0]


def derive_overall_status(statuses: list[str]) -> str:
    if all(status == "unavailable" for status in statuses):
        return "unavailable"
    return derive_timeframe_status(statuses, any(status in {"partial", "unavailable"} for status in statuses))


def derive_status(statuses: list[str]) -> str:
    return derive_timeframe_status(statuses, any(status == "unavailable" for status in statuses))


def calculate_ema_slope(closes: list[float], period: int, lookback: int) -> float | None:
    if len(closes) < period + lookback:
        return None
    current = calculate_ema(closes, period)
    previous = calculate_ema(closes[:-lookback], period)
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def calculate_return(closes: list[float], lookback: int) -> float | None:
    if lookback <= 0 or len(closes) <= lookback:
        return None
    start = closes[-lookback - 1]
    end = closes[-1]
    if start <= 0:
        return None
    return round(((end - start) / start) * 100, 2)


def compare_values(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    if first > second:
        return 1
    if first < second:
        return -1
    return 0


def build_compare_value(first: float | None, second: float | None) -> str | None:
    if first is None or second is None:
        return None
    relation = "above" if first > second else "below" if first < second else "at"
    return f"{round(first, 2)} {relation} {round(second, 2)}"


def momentum_contribution(value: float | None) -> float | None:
    if value is None:
        return None
    if value >= 5:
        return 1
    if value >= 1:
        return 0.5
    if value <= -5:
        return -1
    if value <= -1:
        return -0.5
    return 0


def slope_contribution(value: float | None) -> float | None:
    if value is None:
        return None
    if value >= 1:
        return 1
    if value > 0.1:
        return 0.5
    if value <= -1:
        return -1
    if value < -0.1:
        return -0.5
    return 0


def identity_contribution(value: float | None) -> float | None:
    return value


def average_available(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def number(source: dict[str, Any] | None, key: str) -> float | None:
    return as_float(source.get(key)) if isinstance(source, dict) else None


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def text_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def display_timeframe(timeframe: TimeframeKey) -> str:
    return {"short": "Short-term", "medium": "Medium-term", "long": "Long-term"}[timeframe]


def join_labels(items: list[TimeframeSignalEvidence]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0].label
    return f"{items[0].label}; {items[1].label.lower()}"

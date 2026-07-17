from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models.market import StockLeadershipSignal

METHODOLOGY_VERSION = "1"
MINIMUM_AVAILABLE_WEIGHT = 0.58


@dataclass(frozen=True)
class LeadershipFactor:
    key: str
    label: str
    contribution: float | None
    weight: float
    source_status: str
    positive_label: str
    limiting_label: str

    @property
    def available(self) -> bool:
        return self.contribution is not None and self.source_status not in {"mock", "fallback", "unavailable"}


def calculate_leadership_signal(
    symbol: str,
    *,
    relative_strength: dict[str, Any] | None = None,
    volume_analysis: dict[str, Any] | None = None,
    multi_timeframe_signals: dict[str, Any] | None = None,
    stock_rating: dict[str, Any] | None = None,
) -> StockLeadershipSignal:
    factors = [
        rs_overall_factor(relative_strength),
        rs_sector_factor(relative_strength),
        rs_market_factor(relative_strength),
        timeframe_factor(multi_timeframe_signals),
        volume_participation_factor(volume_analysis),
        market_alignment_factor(stock_rating),
    ]
    available = [factor for factor in factors if factor.available]
    available_weight = sum(factor.weight for factor in available)
    configured_weight = sum(factor.weight for factor in factors)
    required_inputs = len(factors)
    as_of = latest_text([
        relative_strength.get("as_of") if relative_strength else None,
        volume_analysis.get("as_of") if volume_analysis else None,
        nested_text(multi_timeframe_signals, "generatedAt") if multi_timeframe_signals else None,
    ])

    if not configured_weight or available_weight / configured_weight < MINIMUM_AVAILABLE_WEIGHT:
        return StockLeadershipSignal(
            signal="unavailable",
            score=None,
            strength="unavailable",
            explanation=f"Not enough reliable leadership inputs are available for {symbol.upper()}.",
            positiveEvidence=[],
            limitingEvidence=[factor.limiting_label for factor in factors if not factor.available][:3],
            availableInputs=len(available),
            requiredInputs=required_inputs,
            dataStatus="unavailable",
            asOf=as_of,
            methodologyVersion=METHODOLOGY_VERSION,
        )

    weighted_sum = sum((factor.contribution or 0) * factor.weight for factor in available)
    normalized = weighted_sum / available_weight
    score = round(max(0, min(100, (normalized + 1) * 50)))
    signal = map_leadership_score(score)
    strength = map_strength(score)
    positive_evidence = [factor.positive_label for factor in available if (factor.contribution or 0) > 0.18][:3]
    limiting_evidence = [factor.limiting_label for factor in available if (factor.contribution or 0) < 0.18][:3]

    return StockLeadershipSignal(
        signal=signal,
        score=score,
        strength=strength,
        explanation=build_explanation(signal, positive_evidence, limiting_evidence),
        positiveEvidence=positive_evidence,
        limitingEvidence=limiting_evidence,
        availableInputs=len(available),
        requiredInputs=required_inputs,
        dataStatus=derive_data_status([factor.source_status for factor in available]),
        asOf=as_of,
        methodologyVersion=METHODOLOGY_VERSION,
    )


def rs_overall_factor(relative_strength: dict[str, Any] | None) -> LeadershipFactor:
    score = number_or_none(relative_strength, "overall_rs_score")
    return LeadershipFactor(
        key="overall_relative_strength",
        label="Overall relative strength",
        contribution=score_to_contribution(score),
        weight=0.30,
        source_status=source_status(relative_strength),
        positive_label="Overall relative strength is constructive",
        limiting_label="Overall relative strength is not yet leadership-grade",
    )


def rs_sector_factor(relative_strength: dict[str, Any] | None) -> LeadershipFactor:
    score = number_or_none(relative_strength, "rs_vs_sector")
    return LeadershipFactor(
        key="sector_relative_strength",
        label="Sector-relative strength",
        contribution=score_to_contribution(score),
        weight=0.20,
        source_status=source_status(relative_strength),
        positive_label="Strong sector-relative performance",
        limiting_label="Sector-relative strength needs improvement",
    )


def rs_market_factor(relative_strength: dict[str, Any] | None) -> LeadershipFactor:
    spy = number_or_none(relative_strength, "rs_vs_spy")
    qqq = number_or_none(relative_strength, "rs_vs_qqq")
    value = average_available([spy, qqq])
    return LeadershipFactor(
        key="market_relative_strength",
        label="Market-relative strength",
        contribution=score_to_contribution(value),
        weight=0.15,
        source_status=source_status(relative_strength),
        positive_label="Outperforming key market benchmarks",
        limiting_label="SPY/QQQ-relative strength remains unconfirmed",
    )


def timeframe_factor(signals: dict[str, Any] | None) -> LeadershipFactor:
    short = timeframe_contribution(nested_dict(signals, "short"))
    medium = timeframe_contribution(nested_dict(signals, "medium"))
    value = average_available([short, medium])
    return LeadershipFactor(
        key="multi_timeframe_trend",
        label="Short and medium-term trend",
        contribution=value,
        weight=0.15,
        source_status=status_or_unavailable(signals.get("overallDataStatus") if signals else None),
        positive_label="Short and medium-term trend are constructive",
        limiting_label="Short/medium trend confirmation is incomplete",
    )


def volume_participation_factor(volume: dict[str, Any] | None) -> LeadershipFactor:
    status = source_status(volume)
    score = number_or_none(volume, "volume_quality_score")
    if status in {"mock", "fallback"}:
        contribution = None
    else:
        contribution = score_to_contribution(score)
    return LeadershipFactor(
        key="volume_participation",
        label="Volume participation",
        contribution=contribution,
        weight=0.10,
        source_status=status,
        positive_label="Strong participation supports the move",
        limiting_label="Participation is not reliable enough for leadership confirmation",
    )


def market_alignment_factor(stock_rating: dict[str, Any] | None) -> LeadershipFactor:
    components = stock_rating.get("components") if isinstance(stock_rating, dict) else None
    value = number_or_none(components if isinstance(components, dict) else None, "market_alignment")
    return LeadershipFactor(
        key="market_alignment",
        label="Market alignment",
        contribution=score_to_contribution(value),
        weight=0.10,
        source_status="mixed" if value is not None else "unavailable",
        positive_label="Market alignment is supportive",
        limiting_label="Market alignment is not fully supportive",
    )


def timeframe_contribution(signal: dict[str, Any] | None) -> float | None:
    if not signal:
        return None
    state = str(signal.get("signal") or "").lower()
    score = number_or_none(signal, "score")
    if state == "unavailable" or score is None:
        return None
    if state == "strong_bullish":
        return 1.0
    if state == "bullish":
        return 0.55
    if state == "neutral":
        return 0.0
    if state == "bearish":
        return -0.55
    if state == "strong_bearish":
        return -1.0
    return score_to_contribution(score)


def map_leadership_score(score: int) -> str:
    if score >= 80:
        return "leader"
    if score >= 65:
        return "emerging_leader"
    if score >= 40:
        return "follower"
    return "lagging"


def map_strength(score: int) -> str:
    if score >= 80 or score < 40:
        return "strong"
    if score >= 65:
        return "moderate"
    return "weak"


def build_explanation(signal: str, positives: list[str], limits: list[str]) -> str:
    top_positive = positives[0] if positives else "Available inputs are not yet strongly aligned"
    top_limit = limits[0] if limits else "no major limiting factor is visible"
    if signal == "leader":
        return f"{top_positive}, with {top_limit}."
    if signal == "emerging_leader":
        return f"{top_positive}, but {top_limit}."
    if signal == "lagging":
        return f"{top_limit}, and leadership confirmation remains limited."
    return f"Performance remains close to the market average, with {top_limit}."


def derive_data_status(statuses: list[str]) -> str:
    clean = [status_or_unavailable(status) for status in statuses if status]
    if not clean:
        return "unavailable"
    if any(status in {"fallback", "stale"} for status in clean):
        return "stale" if "stale" in clean else "fallback"
    if any(status in {"mixed", "partial"} for status in clean):
        return "mixed"
    if all(status in {"live", "cached"} for status in clean):
        return "live" if "live" in clean else "cached"
    return clean[0]


def source_status(source: dict[str, Any] | None) -> str:
    if not source:
        return "unavailable"
    if bool(source.get("fallback_used")):
        return "fallback"
    data_source = str(source.get("data_source") or source.get("source") or "").lower()
    if data_source == "mock" or data_source == "mock-fallback":
        return "mock" if data_source == "mock" else "fallback"
    if bool(source.get("analysis_is_live")) or bool(source.get("is_live")):
        return "live"
    if data_source:
        return "mixed"
    return "unavailable"


def status_or_unavailable(value: Any) -> str:
    if not value:
        return "unavailable"
    return str(value).lower()


def score_to_contribution(score: float | None) -> float | None:
    if score is None:
        return None
    return max(-1.0, min(1.0, (score - 50) / 50))


def number_or_none(source: dict[str, Any] | None, key: str) -> float | None:
    if not source:
        return None
    value = source.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def average_available(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return sum(valid) / len(valid) if valid else None


def nested_dict(source: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    value = source.get(key) if isinstance(source, dict) else None
    return value if isinstance(value, dict) else None


def nested_text(source: dict[str, Any] | None, key: str) -> str | None:
    value = source.get(key) if isinstance(source, dict) else None
    return str(value) if value else None


def latest_text(values: list[Any]) -> str | None:
    texts = [str(value) for value in values if value]
    return max(texts) if texts else datetime.now(timezone.utc).isoformat()

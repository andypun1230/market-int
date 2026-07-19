from datetime import datetime, timezone
from typing import Any

from app.models.market import DecisionConfidenceContributor, DecisionConfidenceResponse
from app.services.service_cache import get_or_compute, get_service_ttl


def calculate_decision_confidence() -> DecisionConfidenceResponse:
    return get_or_compute(
        "decision-confidence",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _calculate_decision_confidence_uncached,
    )


def _calculate_decision_confidence_uncached() -> DecisionConfidenceResponse:
    from app.services.breadth import calculate_market_breadth
    from app.services.fear_greed import build_fear_greed_index
    from app.services.institutional_activity import calculate_institutional_bias
    from app.services.market_cap_rotation import build_market_cap_rotation
    from app.services.market_health import calculate_market_health
    from app.services.regime import build_market_regime
    from app.services.sectors import build_market_sectors

    return calculate_decision_confidence_from_inputs(
        market_health=calculate_market_health(),
        breadth=calculate_market_breadth(),
        regime=build_market_regime(),
        institutional=calculate_institutional_bias(),
        fear_greed=build_fear_greed_index(),
        sectors=build_market_sectors(),
        cap_rotation=build_market_cap_rotation(),
    )


def calculate_decision_confidence_from_inputs(
    market_health: Any,
    breadth: Any,
    regime: Any,
    institutional: Any,
    fear_greed: Any,
    sectors: Any,
    cap_rotation: Any,
) -> DecisionConfidenceResponse:
    sector_strength = sectors.leaders[0].relative_strength_score if sectors.leaders else 55
    stage_score = get_market_stage_score(regime.status, cap_rotation.leader)
    contributor_rows = [
        ("Market Health", market_health.overall_score, market_health.status),
        ("Breadth", round(breadth.percent_above_50ema), f"{breadth.percent_above_50ema:.1f}% above 50EMA"),
        ("Trend", get_trend_score(regime.status), regime.status),
        ("Institutional", get_institutional_score(institutional.bias), institutional.bias),
        ("Fear & Greed", get_sentiment_alignment_score(fear_greed.status), fear_greed.status),
        ("Sector Leadership", sector_strength, sectors.leaders[0].name if sectors.leaders else "N/A"),
        ("Market Stage", stage_score, f"{regime.status} / {cap_rotation.leader} leadership"),
    ]
    contributors = [
        DecisionConfidenceContributor(label=label, score=score, signal=signal)
        for label, score, signal in contributor_rows
    ]
    score = round(sum(item.score for item in contributors) / len(contributors))
    disagreements = build_disagreements(contributors)

    status = get_confidence_status(score)
    reason = f"{len(contributors) - len(disagreements)} of {len(contributors)} decision inputs meet the confirmation threshold."
    return DecisionConfidenceResponse(
        score=score,
        status=status,
        contributors=contributors,
        disagreements=disagreements,
        summary=(
            f"Decision confidence is {status.lower()} because {reason.lower()}"
        ),
        reason=reason,
        calculated_at=datetime.now(timezone.utc).isoformat(),
        source_snapshot_id=getattr(breadth, "snapshot_id", None),
    )


def get_trend_score(status: str) -> int:
    return {
        "Confirmed Uptrend": 90,
        "Uptrend Under Pressure": 70,
        "Choppy / Sideways": 55,
        "Correction": 30,
    }.get(status, 55)


def get_institutional_score(bias: str) -> int:
    return {
        "Bullish": 90,
        "Neutral": 65,
        "Cautious": 50,
        "Bearish": 25,
    }.get(bias, 55)


def get_sentiment_alignment_score(status: str) -> int:
    if status == "Extreme Greed":
        return 50
    if status == "Greed":
        return 72
    if status == "Neutral":
        return 80
    if status == "Fear":
        return 45
    if status == "Extreme Fear":
        return 25
    return 60


def get_market_stage_score(regime_status: str, cap_leader: str) -> int:
    if regime_status == "Confirmed Uptrend" and cap_leader in ("Mega Cap", "Large Cap"):
        return 88
    if regime_status == "Uptrend Under Pressure":
        return 68
    if regime_status == "Choppy / Sideways":
        return 55
    if regime_status == "Correction":
        return 30
    return 60


def build_disagreements(contributors: list[DecisionConfidenceContributor]) -> list[str]:
    disagreements = [
        f"{item.label} is below confirmation level ({item.signal})."
        for item in contributors
        if item.score < 65
    ]
    return disagreements or ["No major disagreement among the current decision signals."]


def get_confidence_status(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 70:
        return "Moderate"
    if score >= 55:
        return "Mixed"
    return "Limited"

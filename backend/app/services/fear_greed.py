from __future__ import annotations

import os
from typing import Any

from app.models.market import FearGreedComponent, FearGreedResponse
from app.providers.cnn_fear_greed_provider import (
    ESTIMATE_CACHE_KEY,
    CNNFearGreedProvider,
    classify_fear_greed,
    get_persistent_index,
    persist_index,
    set_memory_cache,
)
from app.providers.finnhub_provider import ProviderRequestError
from app.services.market_sentiment import build_market_sentiment_dashboard

ESTIMATE_REQUIRED_COMPONENTS = {"market_momentum", "market_volatility"}
ESTIMATE_COMPONENT_KEYS = {
    "market_momentum",
    "stock_price_strength",
    "stock_price_breadth",
    "put_call_options",
    "put_call_ratio",
    "market_volatility",
    "safe_haven_demand",
    "junk_bond_demand",
}
ESTIMATE_COMPONENTS_REQUIRED = 7


def build_fear_greed_index() -> FearGreedResponse:
    provider = CNNFearGreedProvider()
    official = provider.get_current_index(allow_stale=True, fetch=official_fetch_enabled())
    if official is not None:
        return official

    if estimate_enabled():
        estimate = build_fear_greed_estimate()
        if estimate.score is not None:
            set_memory_cache(ESTIMATE_CACHE_KEY, estimate)
            persist_index(ESTIMATE_CACHE_KEY, estimate)
        return estimate

    stale_estimate = get_persistent_index(ESTIMATE_CACHE_KEY, allow_stale=True)
    if stale_estimate is not None:
        return stale_estimate.model_copy(update={"stale": True, "cache_status": "stale"})
    return unavailable_response("official_source_unavailable")


def build_fear_greed_estimate() -> FearGreedResponse:
    try:
        sentiment = build_market_sentiment_dashboard()
    except Exception as exc:
        reason = error_reason(exc)
        return unavailable_response(reason)

    components = [estimate_component(signal) for signal in sentiment.signals]
    available = [component for component in components if not component.missing]
    present_keys = {component.key for component in components}
    present_keys_for_coverage = present_keys | ({"put_call_options"} if "put_call_ratio" in present_keys else set())
    missing_keys = [
        component.key for component in components if component.missing
    ] + sorted((ESTIMATE_COMPONENT_KEYS - {"put_call_ratio"}) - present_keys_for_coverage)
    available_keys = {component.key for component in available}
    missing_required = sorted(ESTIMATE_REQUIRED_COMPONENTS - available_keys)
    min_components = int_env("CNN_FEAR_GREED_ESTIMATE_MIN_COMPONENTS", 5)
    warnings = [
        "This is an internal estimate based on CNN methodology, not CNN's official published value.",
        "No component is silently replaced with neutral 50 when unavailable.",
    ]
    if missing_required:
        warnings.append(f"Required estimate component(s) missing: {', '.join(missing_required)}.")
    if len(available) < min_components:
        warnings.append(f"Estimate coverage below configured minimum {min_components}/7.")

    if missing_required or len(available) < min_components:
        return FearGreedResponse(
            score=None,
            status="Unavailable",
            components=components,
            summary="Fear & Greed estimate unavailable because required component coverage was not met.",
            title="Fear & Greed unavailable",
            subtitle="Latest verified reading could not be retrieved",
            source="APInvest estimate",
            source_type="estimated",
            fetched_at=None,
            source_timestamp=None,
            stale=False,
            confidence=0,
            parser_version=None,
            cache_status="unavailable",
            partial=True,
            coverage_percent=round(len(available) / ESTIMATE_COMPONENTS_REQUIRED * 100, 2),
            coverage_components=len(available),
            required_components=ESTIMATE_COMPONENTS_REQUIRED,
            overall_mode="unavailable",
            dependencies_requested=ESTIMATE_COMPONENTS_REQUIRED,
            dependencies_available=len(available),
            dependencies_missing=missing_keys + missing_required,
            degraded_reasons=warnings,
        )

    score = round(sum(component.score for component in available) / len(available))
    confidence = estimate_confidence(available, len(available))
    simulated = [component.label for component in available if component.data_state == "simulated"]
    if simulated:
        warnings.append(f"Simulated/fallback component(s) lowered confidence: {', '.join(simulated)}.")

    return FearGreedResponse(
        score=score,
        status=classify_fear_greed(score),
        components=components,
        summary="Internal estimate based on CNN's seven-category methodology. It is not CNN's official published index.",
        title="Fear & Greed Estimate",
        subtitle="Based on CNN methodology",
        source="APInvest estimate",
        source_type="estimated",
        fetched_at=max((component.source_timestamp for component in available if component.source_timestamp), default=None),
        source_timestamp=max((component.source_timestamp for component in available if component.source_timestamp), default=None),
        previous_close=None,
        one_week_ago=None,
        one_month_ago=None,
        one_year_ago=None,
        stale=False,
        confidence=confidence,
        parser_version="cnn-methodology-estimate-v1",
        cache_status="estimate",
        partial=bool(missing_keys),
        coverage_percent=round(len(available) / ESTIMATE_COMPONENTS_REQUIRED * 100, 2),
        coverage_components=len(available),
        required_components=ESTIMATE_COMPONENTS_REQUIRED,
        overall_mode="estimated",
        dependencies_requested=ESTIMATE_COMPONENTS_REQUIRED,
        dependencies_available=len(available),
        dependencies_missing=missing_keys,
        degraded_reasons=warnings,
    )


def estimate_component(signal: Any) -> FearGreedComponent:
    metadata = signal.metadata if isinstance(signal.metadata, dict) else {}
    source = str(metadata.get("source") or "market_proxy")
    fallback = bool(metadata.get("fallback_used")) or "mock" in source or "generated_test_data" in source
    score = getattr(signal, "score", None)
    if score is None:
        return FearGreedComponent(
            key=signal.key,
            label=signal.label,
            score=0,
            status="Unavailable",
            explanation=f"{signal.label} unavailable; no neutral default was substituted.",
            source=source,
            source_timestamp=metadata.get("as_of"),
            data_state="missing",
            confidence=0,
            missing=True,
            warnings=["Missing component."],
        )
    data_state = "simulated" if fallback else "live" if metadata.get("is_live") else "cached"
    confidence = max(25, min(95, round(float(metadata.get("quality_score") or 60))))
    if fallback:
        confidence = min(confidence, 45)
    return FearGreedComponent(
        key=signal.key,
        label=signal.label,
        score=round(score),
        status=classify_fear_greed(round(score)),
        explanation=signal.explanation,
        source=source,
        source_timestamp=metadata.get("as_of"),
        data_state=data_state,
        confidence=confidence,
        missing=False,
        warnings=metadata.get("warnings") or [],
    )


def estimate_confidence(components: list[FearGreedComponent], coverage: int) -> int:
    if not components:
        return 0
    average = sum(component.confidence or 0 for component in components) / len(components)
    coverage_penalty = (ESTIMATE_COMPONENTS_REQUIRED - coverage) * 8
    simulated_penalty = sum(8 for component in components if component.data_state == "simulated")
    return max(0, min(95, round(average - coverage_penalty - simulated_penalty)))


def unavailable_response(reason: str) -> FearGreedResponse:
    return FearGreedResponse(
        score=None,
        status="Unavailable",
        components=[],
        summary="CNN Fear & Greed unavailable; no official value or sufficiently covered estimate is available.",
        title="Fear & Greed unavailable",
        subtitle="Latest verified reading could not be retrieved",
        source=None,
        source_type=None,
        fetched_at=None,
        source_timestamp=None,
        stale=False,
        confidence=0,
        parser_version=None,
        cache_status="unavailable",
        partial=True,
        coverage_percent=0.0,
        coverage_components=0,
        required_components=ESTIMATE_COMPONENTS_REQUIRED,
        overall_mode="unavailable",
        dependencies_requested=ESTIMATE_COMPONENTS_REQUIRED,
        dependencies_available=0,
        dependencies_missing=["official_cnn", "estimate_components"],
        degraded_reasons=[reason],
    )


def official_fetch_enabled() -> bool:
    explicit = os.getenv("CNN_FEAR_GREED_OFFICIAL_ENABLED")
    if explicit is not None:
        return explicit.lower() in {"1", "true", "yes", "on"}
    providers = {
        (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "").lower(),
        (os.getenv("QUOTE_DATA_PROVIDER") or "").lower(),
        (os.getenv("HISTORY_DATA_PROVIDER") or "").lower(),
    }
    return not (providers & {"test", "mock", "generated_test_data"})


def estimate_enabled() -> bool:
    return os.getenv("CNN_FEAR_GREED_ESTIMATE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def error_reason(error: BaseException) -> str:
    if isinstance(error, ProviderRequestError):
        return error.category
    return type(error).__name__

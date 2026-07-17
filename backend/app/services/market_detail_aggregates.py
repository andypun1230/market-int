from __future__ import annotations

from typing import Any, Callable

from app.services.service_cache import (
    get_cached_service_value,
    get_persistent_service_value,
    get_service_ttl,
    set_l1_service_value,
    set_cached_service_value,
    trigger_background_refresh,
)
from app.services.breadth import calculate_market_breadth, calculate_sector_breadth
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.decision_intelligence import build_decision_dashboard
from app.services.industry_groups import build_industry_groups
from app.services.industry_rotation import build_industry_rotation_dashboard
from app.services.institutional_activity import build_institutional_activity
from app.services.institutional_dashboard import build_institutional_dashboard
from app.services.leadership import build_leadership_dashboard
from app.services.liquidity_dashboard import build_liquidity_dashboard
from app.services.market_sentiment import build_market_sentiment_dashboard
from app.services.money_flow import build_money_flow_dashboard
from app.services.options_intelligence import build_options_intelligence
from app.services.probability_engine import build_probability_engine
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.sectors import build_market_sectors


def build_market_decision_details() -> dict[str, Any]:
    return build_stale_first_aggregate(
        key="materialized:market-details:decision",
        partial_fn=build_market_decision_partial,
        refresh_fn=refresh_market_decision_details,
    )


def build_market_institutional_details() -> dict[str, Any]:
    return build_stale_first_aggregate(
        key="materialized:market-details:institutional",
        partial_fn=build_market_institutional_partial,
        refresh_fn=refresh_market_institutional_details,
    )


def build_market_structure_details() -> dict[str, Any]:
    return build_stale_first_aggregate(
        key="materialized:market-details:structure",
        partial_fn=build_market_structure_partial,
        refresh_fn=refresh_market_structure_details,
    )


def build_stale_first_aggregate(
    key: str,
    partial_fn: Callable[[], dict[str, Any]],
    refresh_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    cached = get_cached_service_value(key)
    if isinstance(cached, dict):
        return {**cached, "cache_status": cached.get("cache_status", "fresh"), "refreshing": False}

    stale = get_persistent_service_value(key, allow_stale=True)
    if stale is not None and isinstance(stale.value, dict):
        set_l1_service_value(key, stale.value, min(30, get_detail_ttl()))
        trigger_background_refresh(key, get_detail_ttl(), refresh_fn)
        return {
            **stale.value,
            "cache_status": "stale",
            "refreshing": True,
            "cache_age_seconds": round(stale.age_seconds, 2),
        }

    trigger_background_refresh(key, get_detail_ttl(), refresh_fn)
    return {
        **partial_fn(),
        "cache_status": "miss",
        "refreshing": True,
        "partial": True,
    }


def refresh_market_decision_details() -> dict[str, Any]:
    value = build_partial(
        {
            "decisionDashboard": build_decision_dashboard,
            "probabilities": build_probability_engine,
            "comparison": build_dashboard_comparison,
            "riskDashboard": build_risk_dashboard_v2,
        }
    )
    value["cache_status"] = "fresh"
    set_cached_service_value("materialized:market-details:decision", value, get_detail_ttl())
    return value


def refresh_market_institutional_details() -> dict[str, Any]:
    value = build_partial(
        {
            "sentiment": build_market_sentiment_dashboard,
            "moneyFlow": build_money_flow_dashboard,
            "institutionalActivity": build_institutional_activity,
            "institutional": build_institutional_dashboard,
            "options": build_options_intelligence,
            "liquidity": build_liquidity_dashboard,
        }
    )
    value["cache_status"] = "fresh"
    set_cached_service_value("materialized:market-details:institutional", value, get_detail_ttl())
    return value


def refresh_market_structure_details() -> dict[str, Any]:
    value = build_partial(
        {
            "breadth": lambda: {"market": calculate_market_breadth(), "sectors": calculate_sector_breadth()},
            "sectors": build_market_sectors,
            "industryGroups": build_industry_groups,
            "industryRotation": build_industry_rotation_dashboard,
            "leadership": build_leadership_dashboard,
        }
    )
    value["cache_status"] = "fresh"
    set_cached_service_value("materialized:market-details:structure", value, get_detail_ttl())
    return value


def build_market_decision_partial() -> dict[str, Any]:
    return {
        "decisionDashboard": to_jsonable(get_cached_service_value("decision-dashboard")),
        "probabilities": to_jsonable(get_cached_service_value("probabilities")),
        "comparison": to_jsonable(get_cached_service_value("dashboard-comparison")),
        "riskDashboard": to_jsonable(get_cached_service_value("risk-dashboard-v2")),
        "errors": {},
    }


def build_market_institutional_partial() -> dict[str, Any]:
    return {
        "sentiment": to_jsonable(get_cached_service_value("market-sentiment")),
        "moneyFlow": to_jsonable(get_cached_service_value("money-flow")),
        "institutionalActivity": to_jsonable(get_cached_service_value("institutional-activity")),
        "institutional": to_jsonable(get_cached_service_value("institutional-dashboard")),
        "options": to_jsonable(get_cached_service_value("options-intelligence")),
        "liquidity": to_jsonable(get_cached_service_value("liquidity-dashboard")),
        "errors": {},
    }


def build_market_structure_partial() -> dict[str, Any]:
    breadth = to_jsonable(get_cached_service_value("service-breadth:core"))
    sector_breadth = to_jsonable(get_cached_service_value("service-sector-breadth:core"))
    return {
        "breadth": {"market": breadth, "sectors": sector_breadth or []} if breadth else None,
        "sectors": to_jsonable(get_cached_service_value("sectors")),
        "sectorEtfs": to_jsonable(get_cached_service_value("sector-etfs")),
        "industryGroups": to_jsonable(get_cached_service_value("industry-groups")),
        "industryRotation": to_jsonable(get_cached_service_value("industry-rotation")),
        "leadership": to_jsonable(get_cached_service_value("leadership")),
        "errors": {},
    }


def build_partial(tasks: dict[str, Callable[[], Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"partial": False, "errors": {}, "cache_status": "cached_or_current"}
    for key, fn in tasks.items():
        try:
            result[key] = to_jsonable(fn())
        except Exception as exc:
            result["partial"] = True
            result["errors"][key] = safe_error_summary(exc)
            result[key] = None
    return result


def safe_error_summary(error: Exception) -> dict[str, str]:
    category = getattr(error, "category", None)
    if category:
        return {
            "category": str(category),
            "message": "Data dependency unavailable.",
        }
    return {
        "category": "calculation_error",
        "message": "Section unavailable due to a recoverable calculation error.",
    }


def get_detail_ttl() -> int:
    return get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 120)


def to_jsonable(value: object) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value

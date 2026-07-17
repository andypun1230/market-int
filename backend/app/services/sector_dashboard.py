from __future__ import annotations

from typing import Any, Literal

from app.services.industry_groups import build_industry_groups, _build_industry_groups_uncached
from app.services.sector_etfs import build_sector_etf_dashboard, _build_sector_etf_dashboard_uncached
from app.services.service_cache import get_or_compute, get_service_ttl
from app.providers.test_provider import TEST_DATA_SOURCE

RotationInterval = Literal["1w", "1m", "3m"]


def build_sector_dashboard() -> dict[str, Any]:
    return get_or_compute(
        "sector-dashboard:v2",
        get_service_ttl("SERVICE_CACHE_SECTORS_TTL_SECONDS", 900),
        _build_sector_dashboard_uncached,
    )


def _build_sector_dashboard_uncached() -> dict[str, Any]:
    sector_etfs = build_sector_etf_dashboard()
    industry_groups = build_industry_groups()
    if response_missing_long_intervals(sector_etfs):
        sector_etfs = _build_sector_etf_dashboard_uncached()
    if response_missing_long_intervals(industry_groups):
        industry_groups = _build_industry_groups_uncached()
    sectors = [build_sector_item(item) for item in sector_etfs.items]
    themes = [build_theme_item(item) for item in industry_groups.items]
    modes = {
        mode
        for mode in [
            sector_etfs.overall_mode,
            industry_groups.overall_mode,
        ]
        if mode
    }

    return {
        "status": "success",
        "source": TEST_DATA_SOURCE,
        "data_status": "test",
        "benchmark": "SPY",
        "sectors": sectors,
        "themes": themes,
        "theme_legacy_source": "industry_groups",
        "summary": "Sector and theme rotation is based on relative strength and momentum versus SPY.",
        "as_of": max(
            [value for value in [sector_etfs.as_of, industry_groups.as_of] if value],
            default=None,
        ),
        "cache_status": "fresh",
        "partial": False,
    }


def build_sector_item(item: object) -> dict[str, Any]:
    name = getattr(item, "sector")
    return_1w = get_number(item, "return_1w")
    return_1m = get_number(item, "return_1m") or get_number(item, "return_mtd")
    return_3m = get_number(item, "return_3m")
    return_6m = get_number(item, "return_6m")
    return_1y = get_number(item, "return_1y") or get_number(item, "return_ytd")
    returns = build_returns(
        one_day=get_number(item, "return_1d"),
        one_week=return_1w,
        one_month=return_1m,
        three_months=return_3m,
        six_months=return_6m,
        one_year=return_1y,
    )

    return {
        "id": slugify(name),
        "name": name,
        "symbol": getattr(item, "symbol", None),
        "returns": returns,
        "rotation": build_rotation_map(
            relative_strength_score=get_number(item, "relative_strength_score"),
            return_1w=return_1w,
            return_1m=return_1m,
            return_3m=return_3m,
            return_6m=return_6m,
        ),
        "source": TEST_DATA_SOURCE,
        "data_status": "test",
        "metadata": {
            "status": getattr(item, "status", None),
            "rotation_score": getattr(item, "rotation_score", None),
            "coverage_percent": getattr(item, "coverage_percent", None),
            "history_quality_score": getattr(item, "history_quality_score", None),
            "fallback_used": getattr(item, "fallback_used", None),
            "as_of": getattr(item, "as_of", None),
        },
    }


def build_theme_item(item: object) -> dict[str, Any]:
    name = getattr(item, "name")
    return_1w = get_number(item, "return_1w")
    return_1m = get_number(item, "return_1m") or get_number(item, "return_mtd")
    return_3m = get_number(item, "return_3m")
    return_6m = get_number(item, "return_6m")
    return_1y = get_number(item, "return_1y") or get_number(item, "return_ytd")
    returns = build_returns(
        one_day=get_number(item, "return_1d"),
        one_week=return_1w,
        one_month=return_1m,
        three_months=return_3m,
        six_months=return_6m,
        one_year=return_1y,
    )

    return {
        "id": slugify(name),
        "name": name,
        "parent_sector": getattr(item, "parent_sector", None),
        "returns": returns,
        "rotation": build_rotation_map(
            relative_strength_score=get_number(item, "relative_strength_score"),
            return_1w=return_1w,
            return_1m=return_1m,
            return_3m=return_3m,
            return_6m=return_6m,
        ),
        "source": TEST_DATA_SOURCE,
        "data_status": "test",
        "metadata": {
            "status": getattr(item, "status", None),
            "coverage_percent": getattr(item, "coverage_percent", None),
            "successful_symbols": getattr(item, "successful_symbols", None),
            "history_quality_score": getattr(item, "history_quality_score", None),
            "fallback_used": getattr(item, "fallback_used", None),
            "as_of": getattr(item, "as_of", None),
        },
    }


def build_returns(
    one_day: float | None,
    one_week: float | None,
    one_month: float | None,
    three_months: float | None,
    six_months: float | None,
    one_year: float | None,
) -> dict[str, float | None]:
    return {
        "1d": one_day,
        "1w": one_week,
        "1m": one_month,
        "3m": three_months,
        "6m": six_months,
        "1y": one_year,
    }


def build_rotation_map(
    relative_strength_score: float | None,
    return_1w: float | None,
    return_1m: float | None,
    return_3m: float | None,
    return_6m: float | None,
) -> dict[str, dict[str, Any] | None]:
    return {
        "1w": build_rotation(relative_strength_score, return_1w, return_1m),
        "1m": build_rotation(relative_strength_score, return_1m, return_3m),
        "3m": build_rotation(relative_strength_score, return_3m, return_6m),
    }


def build_rotation(
    relative_strength_score: float | None,
    short_return: float | None,
    long_return: float | None,
) -> dict[str, Any] | None:
    if relative_strength_score is None or short_return is None or long_return is None:
        return None
    relative_strength = round(100 + ((relative_strength_score - 55) / 2), 2)
    relative_momentum = round(100 + ((short_return - long_return) * 2), 2)
    return {
        "relative_strength": relative_strength,
        "relative_momentum": relative_momentum,
        "quadrant": classify_quadrant(relative_strength, relative_momentum),
        "history": [],
    }


def classify_quadrant(relative_strength: float, relative_momentum: float) -> str:
    if relative_strength >= 100 and relative_momentum >= 100:
        return "leading"
    if relative_strength >= 100 and relative_momentum < 100:
        return "weakening"
    if relative_strength < 100 and relative_momentum < 100:
        return "lagging"
    return "improving"


def get_number(item: object, field: str) -> float | None:
    value = getattr(item, field, None)
    return value if isinstance(value, (int, float)) else None


def response_missing_long_intervals(response: object) -> bool:
    items = getattr(response, "items", None)
    if not items:
        return False
    return any(
        getattr(item, "return_3m", None) is None or getattr(item, "return_6m", None) is None
        for item in items
    )


def get_source_mode(item: object) -> str:
    return TEST_DATA_SOURCE


def combine_modes(modes: set[str]) -> str:
    return "test"


def slugify(value: str) -> str:
    return value.lower().replace("&", "and").replace("/", "-").replace(" ", "-")

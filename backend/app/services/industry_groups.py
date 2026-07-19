import os

from app.data.universes import INDUSTRY_GROUP_BASKETS
from app.models.market import IndustryGroupItem, IndustryGroupResponse
from app.providers.cache import get_cached_value, set_cached_value
from app.services.basket_data import (
    calculate_basket_breadth,
    calculate_basket_relative_strength,
    get_equal_weight_returns,
)
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.theme_provenance import static_strategy_preference_provenance


def build_industry_groups() -> IndustryGroupResponse:
    response = get_or_compute(
        "industry-groups:v2",
        get_service_ttl("SERVICE_CACHE_INDUSTRY_GROUPS_TTL_SECONDS", 900),
        _build_industry_groups_uncached,
    )
    return normalize_industry_group_response(response)


def _build_industry_groups_uncached() -> IndustryGroupResponse:
    cache_key = f"industry-groups:v2:{os.getenv('INDUSTRY_GROUP_HISTORY_DAYS', '260')}"
    cached = get_cached_value(cache_key)
    if cached is not None and has_long_interval_fields(cached):
        return cached

    days = int(os.getenv("INDUSTRY_GROUP_HISTORY_DAYS", "260"))
    rows = [build_group_row(group, days) for group in INDUSTRY_GROUP_BASKETS]
    ranked_rows = sorted(
        rows,
        key=lambda item: (
            item["score"],
            item["relative_strength_score"],
            item["return_1w"],
        ),
        reverse=True,
    )
    as_of = max((item["as_of"] for item in ranked_rows if item.get("as_of")), default=None)
    provenance = static_strategy_preference_provenance(as_of)
    items = [IndustryGroupItem(rank=index + 1, provenance=provenance, **row) for index, row in enumerate(ranked_rows)]
    leaders = ", ".join(item.name for item in items[:3]) if items else "N/A"
    modes = {item.overall_mode for item in items if item.overall_mode}
    overall_mode = "live" if modes == {"live"} else "mixed" if "live" in modes or "mixed" in modes else "mock"
    coverage_values = [
        item.coverage_percent for item in items if item.coverage_percent is not None
    ]

    result = IndustryGroupResponse(
        items=items,
        summary=(
            f"{leaders} are configured strategy baskets. They are static preferences, not live Theme Intelligence."
        ),
        overall_mode=overall_mode,
        coverage_percent=(
            round(sum(coverage_values) / len(coverage_values), 2)
            if coverage_values else None
        ),
        as_of=as_of,
        theme_provenance=provenance,
    )
    set_cached_value(cache_key, result, int(os.getenv("INDUSTRY_GROUP_CACHE_TTL_SECONDS", "900")))
    return result


def normalize_industry_group_response(value: object) -> IndustryGroupResponse:
    """Keep old cached data truthful without mutating the cached object."""
    response = value if isinstance(value, IndustryGroupResponse) else IndustryGroupResponse.model_validate(value)
    provenance = static_strategy_preference_provenance(response.as_of)
    items = [item.model_copy(update={"provenance": provenance}) for item in response.items]
    leaders = ", ".join(item.name for item in items[:3]) if items else "No configured baskets"
    return response.model_copy(update={
        "items": items,
        "summary": f"{leaders} are configured strategy baskets. They are static preferences, not live Theme Intelligence.",
        "theme_provenance": provenance,
    })


def has_long_interval_fields(response: object) -> bool:
    items = getattr(response, "items", None)
    if not items:
        return False
    first = items[0]
    return getattr(first, "return_3m", None) is not None and getattr(first, "return_6m", None) is not None


def build_group_row(group: dict, days: int) -> dict:
    symbols = group["symbols"]
    benchmark = group.get("benchmark", "SPY")
    breadth = calculate_basket_breadth(symbols, days=days)
    metadata = breadth["metadata"]
    relative_strength = calculate_basket_relative_strength(symbols, benchmark_symbol=benchmark, days=days)
    returns = {
        "return_1d": get_equal_weight_returns(symbols, "1d", days=days)["return"],
        "return_1w": get_equal_weight_returns(symbols, "1w", days=days)["return"],
        "return_1m": get_equal_weight_returns(symbols, "1m", days=days)["return"],
        "return_3m": get_equal_weight_returns(symbols, "3m", days=days)["return"],
        "return_6m": get_equal_weight_returns(symbols, "6m", days=days)["return"],
        "return_1y": get_equal_weight_returns(symbols, "1y", days=days)["return"],
        "return_mtd": get_equal_weight_returns(symbols, "mtd", days=days)["return"],
        "return_ytd": get_equal_weight_returns(symbols, "ytd", days=days)["return"],
    }
    relative_strength_score = relative_strength["score"]
    rotation_score = calculate_group_score(
        relative_strength_score,
        returns["return_1w"],
        returns["return_mtd"],
        breadth["percent_above_50ema"],
    )
    status = get_group_status(rotation_score, returns["return_1w"], breadth["percent_above_50ema"])

    return {
        "name": group["name"],
        "parent_sector": group["parent_sector"],
        "score": rotation_score,
        "status": status,
        **returns,
        "relative_strength_score": relative_strength_score,
        "breadth_above_50ema": breadth["percent_above_50ema"],
        "percent_above_20ema": breadth["percent_above_20ema"],
        "percent_above_50ema": breadth["percent_above_50ema"],
        "percent_above_200ema": breadth["percent_above_200ema"],
        "advancing_stocks": breadth["advancing_stocks"],
        "declining_stocks": breadth["declining_stocks"],
        "unchanged_stocks": breadth["unchanged_stocks"],
        "new_highs": breadth["new_52w_highs"],
        "new_lows": breadth["new_52w_lows"],
        "volume_participation": breadth["volume_participation"],
        "trend_direction": get_trend_direction(returns["return_1w"], returns["return_mtd"]),
        "data_source": metadata["overall_mode"],
        "overall_mode": metadata["overall_mode"],
        "coverage_percent": metadata["coverage_percent"],
        "successful_symbols": metadata["successful_symbols"],
        "fallback_used": metadata["fallback_symbols"] > 0,
        "as_of": metadata["as_of"],
        "history_quality_score": metadata["history_quality_score"],
    }


def calculate_group_score(
    relative_strength_score: int,
    return_1w: float,
    return_mtd: float,
    percent_above_50ema: float,
) -> int:
    weekly_score = normalize_return(return_1w, -6, 10)
    mtd_score = normalize_return(return_mtd, -10, 18)
    return max(
        0,
        min(
            100,
            round(
                (relative_strength_score * 0.40)
                + (weekly_score * 0.25)
                + (mtd_score * 0.20)
                + (percent_above_50ema * 0.15)
            ),
        ),
    )


def get_group_status(score: int, return_1w: float, percent_above_50ema: float) -> str:
    if score >= 85 and percent_above_50ema >= 60:
        return "Leading"
    if score >= 72:
        return "Strong"
    if return_1w > 0 and percent_above_50ema >= 50:
        return "Improving"
    if score < 45 or return_1w < 0:
        return "Weak"
    return "Neutral"


def get_trend_direction(return_1w: float, return_mtd: float) -> str:
    if return_1w > 0 and return_mtd > 0:
        return "Improving"
    if return_1w < 0 and return_mtd < 0:
        return "Deteriorating"
    return "Stable"


def normalize_return(value: float, low: float, high: float) -> int:
    if high == low:
        return 50
    return max(0, min(100, round(((value - low) / (high - low)) * 100)))

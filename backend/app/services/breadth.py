import os
from collections import defaultdict
from typing import Any

from app.data.universes import CORE_BREADTH_UNIVERSE, get_core_symbols
from app.models.market import MarketBreadthResponse, SectorBreadthItem
from app.providers.cache import get_cached_value, set_cached_value
from app.services.basket_data import calculate_basket_breadth
from app.services.service_cache import get_or_compute, get_service_ttl


def get_breadth_universe_symbols() -> list[str]:
    universe = os.getenv("BREADTH_UNIVERSE", "core").lower()
    max_symbols = int(os.getenv("BREADTH_MAX_SYMBOLS", "120"))

    if universe == "custom":
        custom_symbols = [
            symbol.strip().upper()
            for symbol in os.getenv("BREADTH_CUSTOM_SYMBOLS", "").split(",")
            if symbol.strip()
        ]
        return custom_symbols[:max_symbols] if custom_symbols else get_core_symbols(max_symbols)

    return get_core_symbols(max_symbols)


def calculate_market_breadth() -> MarketBreadthResponse:
    return get_or_compute(
        build_cache_key("service-breadth"),
        get_service_ttl("SERVICE_CACHE_BREADTH_TTL_SECONDS", 900),
        _calculate_market_breadth_uncached,
    )


def _calculate_market_breadth_uncached() -> MarketBreadthResponse:
    cache_key = build_cache_key("breadth")
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    symbols = get_breadth_universe_symbols()
    days = int(os.getenv("BREADTH_HISTORY_DAYS", "260"))
    breadth = calculate_basket_breadth(symbols, days=days)
    metadata = breadth["metadata"]
    breadth_score = round(
        (breadth["percent_above_50ema"] * 0.55)
        + ((breadth["advance_decline_ratio"] or 1) * 15)
        + (breadth["percent_above_20ema"] * 0.20)
    )
    breadth_score = max(0, min(100, breadth_score))

    result = MarketBreadthResponse(
        total_stocks=breadth["total_stocks"],
        advancing_stocks=breadth["advancing_stocks"],
        declining_stocks=breadth["declining_stocks"],
        unchanged_stocks=breadth["unchanged_stocks"],
        advance_decline_ratio=breadth["advance_decline_ratio"],
        percent_above_20ema=breadth["percent_above_20ema"],
        percent_above_50ema=breadth["percent_above_50ema"],
        percent_above_200ema=breadth["percent_above_200ema"],
        new_52w_highs=breadth["new_52w_highs"],
        new_52w_lows=breadth["new_52w_lows"],
        breadth_score=breadth_score,
        breadth_status=get_breadth_status(breadth["percent_above_50ema"]),
        universe=os.getenv("BREADTH_UNIVERSE", "core"),
        universe_size=metadata["requested_symbols"],
        successful_symbols=metadata["successful_symbols"],
        coverage_percent=metadata["coverage_percent"],
        overall_mode=metadata["overall_mode"],
        fallback_used=metadata["fallback_symbols"] > 0,
        as_of=metadata["as_of"],
        history_quality_score=metadata["history_quality_score"],
    )
    set_cached_value(cache_key, result, get_breadth_ttl())
    return result


def calculate_sector_breadth() -> list[SectorBreadthItem]:
    return get_or_compute(
        build_cache_key("service-sector-breadth"),
        get_service_ttl("SERVICE_CACHE_BREADTH_TTL_SECONDS", 900),
        _calculate_sector_breadth_uncached,
    )


def _calculate_sector_breadth_uncached() -> list[SectorBreadthItem]:
    cache_key = build_cache_key("sector-breadth")
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    sector_symbols: dict[str, list[str]] = defaultdict(list)
    allowed_symbols = set(get_breadth_universe_symbols())
    for item in CORE_BREADTH_UNIVERSE:
        if item["symbol"] in allowed_symbols:
            sector_symbols[item["sector"]].append(item["symbol"])

    days = int(os.getenv("BREADTH_HISTORY_DAYS", "260"))
    sector_breadth: list[SectorBreadthItem] = []
    for sector, symbols in sector_symbols.items():
        breadth = calculate_basket_breadth(symbols, days=days)
        metadata = breadth["metadata"]
        sector_breadth.append(
            SectorBreadthItem(
                sector=sector,
                total_stocks=breadth["total_stocks"],
                advancing_stocks=breadth["advancing_stocks"],
                declining_stocks=breadth["declining_stocks"],
                percent_above_50ema=breadth["percent_above_50ema"],
                overall_mode=metadata["overall_mode"],
                coverage_percent=metadata["coverage_percent"],
                successful_symbols=metadata["successful_symbols"],
                universe_size=metadata["requested_symbols"],
                as_of=metadata["as_of"],
                history_quality_score=metadata["history_quality_score"],
            )
        )

    result = sorted(sector_breadth, key=lambda item: item.percent_above_50ema, reverse=True)
    set_cached_value(cache_key, result, get_breadth_ttl())
    return result


def get_universe_status() -> dict[str, Any]:
    breadth = calculate_market_breadth()
    metadata = calculate_basket_breadth(
        get_breadth_universe_symbols(),
        days=int(os.getenv("BREADTH_HISTORY_DAYS", "260")),
    )["metadata"]
    return {
        "breadth_universe": breadth.universe or "core",
        "configured_symbols": breadth.universe_size or 0,
        "last_successful_symbols": breadth.successful_symbols or 0,
        "coverage_percent": breadth.coverage_percent or 0,
        "live_symbols": metadata.get("live_symbols", 0),
        "fallback_symbols": metadata.get("fallback_symbols", 0),
        "failed_symbols_count": metadata.get("failed_symbols_count", 0),
        "overall_mode": breadth.overall_mode,
        "as_of": breadth.as_of,
    }


def get_breadth_status(percent_above_50ema: float) -> str:
    if percent_above_50ema >= 60:
        return "Healthy"
    if percent_above_50ema >= 45:
        return "Mixed"
    return "Weak"


def build_cache_key(prefix: str) -> str:
    return (
        f"{prefix}:{os.getenv('BREADTH_UNIVERSE', 'core')}:"
        f"{os.getenv('BREADTH_MAX_SYMBOLS', '120')}:"
        f"{os.getenv('BREADTH_HISTORY_DAYS', '260')}"
    )


def get_breadth_ttl() -> int:
    return int(os.getenv("BREADTH_CACHE_TTL_SECONDS", "900"))

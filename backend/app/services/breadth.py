import os
from collections import defaultdict
from typing import Any

from app.data.universes import CORE_BREADTH_UNIVERSE, get_core_symbols
from app.models.market import MarketBreadthResponse, SectorBreadthItem
from app.providers.cache import get_cached_value, set_cached_value
from app.services.basket_data import calculate_basket_breadth
from app.services.service_cache import get_or_compute, get_service_ttl
from app.breadth.service import get_breadth_snapshot_service


def get_breadth_universe_symbols() -> list[str]:
    universe = os.getenv("BREADTH_UNIVERSE", "core").lower()
    max_symbols = int(os.getenv("BREADTH_MAX_SYMBOLS", str(default_breadth_max_symbols())))

    if universe == "custom":
        custom_symbols = [
            symbol.strip().upper()
            for symbol in os.getenv("BREADTH_CUSTOM_SYMBOLS", "").split(",")
            if symbol.strip()
        ]
        return custom_symbols[:max_symbols] if custom_symbols else get_core_symbols(max_symbols)

    return get_core_symbols(max_symbols)


def calculate_market_breadth() -> MarketBreadthResponse:
    snapshot = get_breadth_snapshot_service().latest()
    if snapshot is not None:
        return market_breadth_from_snapshot(snapshot)
    if is_live_without_mock_fallback():
        return unavailable_market_breadth()
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
    snapshot = get_breadth_snapshot_service().latest()
    if snapshot is not None:
        return sector_breadth_from_snapshot(snapshot)
    if is_live_without_mock_fallback():
        return []
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
    status = get_breadth_snapshot_service().status()
    snapshot = get_breadth_snapshot_service().latest()
    coverage = snapshot.coverage if snapshot else {}
    return {
        "breadth_universe": status["configured_universe"],
        "universe_version": status.get("universe_version"),
        "configured_symbols": coverage.get("members_requested", 0),
        "last_successful_symbols": coverage.get("members_available", 0),
        "coverage_percent": round(float(coverage.get("coverage_ratio", 0)) * 100, 2),
        "live_symbols": coverage.get("members_available", 0),
        "fallback_symbols": 0,
        "failed_symbols_count": len(coverage.get("members_missing", [])),
        "overall_mode": snapshot.source_state if snapshot else "unavailable",
        "as_of": snapshot.market_date if snapshot else None,
        **status,
    }


def market_breadth_from_snapshot(snapshot: Any) -> MarketBreadthResponse:
    core = {**snapshot.advance_decline, **snapshot.moving_average_breadth, **snapshot.highs_lows}
    coverage = snapshot.coverage
    return MarketBreadthResponse(
        total_stocks=coverage.get("members_eligible", 0),
        advancing_stocks=core.get("advancing_count", 0),
        declining_stocks=core.get("declining_count", 0),
        unchanged_stocks=core.get("unchanged_count", 0),
        advance_decline_ratio=core.get("advance_decline_ratio"),
        percent_above_20ema=core.get("percent_above_20ema") or 0.0,
        percent_above_50ema=core.get("percent_above_50ema") or 0.0,
        percent_above_200ema=core.get("percent_above_200ema") or 0.0,
        new_52w_highs=core.get("new_52_week_highs", 0),
        new_52w_lows=core.get("new_52_week_lows", 0),
        breadth_score=round(snapshot.score) if snapshot.score is not None else None,
        breadth_status=snapshot.classification,
        universe="sp100",
        universe_size=coverage.get("universe_size"),
        successful_symbols=coverage.get("members_available"),
        coverage_percent=round(float(coverage.get("coverage_ratio", 0)) * 100, 2),
        overall_mode=snapshot.source_state,
        fallback_used=False,
        as_of=snapshot.market_date,
        snapshot_id=snapshot.snapshot_id,
        universe_version=snapshot.universe_version,
        market_date=snapshot.market_date,
        coverage_status=coverage.get("coverage_status"),
        trend=snapshot.trend,
        confidence=snapshot.confidence,
        source_state=snapshot.source_state,
        providers=snapshot.providers,
        warnings=snapshot.warnings,
    )


def sector_breadth_from_snapshot(snapshot: Any) -> list[SectorBreadthItem]:
    coverage = snapshot.coverage
    return [
        SectorBreadthItem(
            sector=item["sector"], total_stocks=item.get("member_count", 0),
            advancing_stocks=item.get("advancing_count", 0), declining_stocks=item.get("declining_count", 0),
            percent_above_50ema=item.get("percent_above_50ema") or 0.0,
            unchanged_stocks=item.get("unchanged_count"), percent_above_20ema=item.get("percent_above_20ema"),
            percent_above_200ema=item.get("percent_above_200ema"), new_52w_highs=item.get("new_52_week_highs"),
            new_52w_lows=item.get("new_52_week_lows"), breadth_score=item.get("sector_breadth_score"),
            breadth_status=item.get("status"), overall_mode=snapshot.source_state,
            coverage_percent=round(float(item.get("coverage_ratio", 0)) * 100, 2), successful_symbols=item.get("available_count"),
            universe_size=item.get("member_count"), as_of=snapshot.market_date,
        ) for item in snapshot.sector_breadth
    ]


def unavailable_market_breadth() -> MarketBreadthResponse:
    return MarketBreadthResponse(
        total_stocks=0, advancing_stocks=0, declining_stocks=0, unchanged_stocks=0,
        advance_decline_ratio=None, percent_above_20ema=0.0, percent_above_50ema=0.0,
        percent_above_200ema=0.0, new_52w_highs=0, new_52w_lows=0,
        breadth_status="unavailable", universe="sp100", universe_size=0,
        successful_symbols=0, coverage_percent=0.0, overall_mode="unavailable",
        source_state="unavailable", coverage_status="unavailable",
        warnings=["No durable breadth snapshot has been published."],
    )


def get_breadth_status(percent_above_50ema: float) -> str:
    if percent_above_50ema >= 60:
        return "Healthy"
    if percent_above_50ema >= 45:
        return "Mixed"
    return "Weak"


def build_cache_key(prefix: str) -> str:
    return (
        f"{prefix}:{os.getenv('BREADTH_UNIVERSE', 'core')}:"
        f"{os.getenv('BREADTH_MAX_SYMBOLS', str(default_breadth_max_symbols()))}:"
        f"{os.getenv('BREADTH_HISTORY_DAYS', '260')}"
    )


def get_breadth_ttl() -> int:
    return int(os.getenv("BREADTH_CACHE_TTL_SECONDS", "900"))


def default_breadth_max_symbols() -> int:
    if is_live_without_mock_fallback():
        return int_env("BREADTH_LIVE_MAX_SYMBOLS", 15)
    return 120


def is_live_without_mock_fallback() -> bool:
    provider_mode = (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "").lower()
    history_provider = (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "").lower()
    allow_fallback = os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
    return not allow_fallback and (provider_mode in {"live", "auto", "finnhub", "polygon", "massive"} or history_provider in {"polygon", "massive"})


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

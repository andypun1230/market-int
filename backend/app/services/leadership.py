import os

from app.data.universes import CORE_BREADTH_UNIVERSE, INDUSTRY_GROUP_BASKETS, get_symbol_sector
from app.models.market import LeadershipCategory, LeadershipResponse, LeadershipStock
from app.providers.cache import get_cached_value, set_cached_value
from app.services.candle_data import get_symbol_history
from app.services.pattern_detection import WATCHLIST_SYMBOLS
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.technical_indicators import calculate_ema


def build_leadership_dashboard() -> LeadershipResponse:
    return get_or_compute(
        "leadership",
        get_service_ttl("SERVICE_CACHE_LEADERSHIP_TTL_SECONDS", 900),
        _build_leadership_dashboard_uncached,
    )


def _build_leadership_dashboard_uncached() -> LeadershipResponse:
    cache_key = f"leadership:{os.getenv('LEADERSHIP_HISTORY_DAYS', '260')}"
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    days = int(os.getenv("LEADERSHIP_HISTORY_DAYS", "260"))
    symbols = build_leadership_universe()
    spy_history, _ = get_symbol_history("SPY", days=days, minimum_candles=60)
    spy_closes = [candle.close for candle in spy_history.candles]
    spy_return_20 = calculate_window_return(spy_closes, 20)
    spy_return_60 = calculate_window_return(spy_closes, 60)

    candidates: list[LeadershipStock] = []
    live_count = 0
    fallback_count = 0
    as_of_values: list[str] = []

    for symbol in symbols:
        try:
            history, validation = get_symbol_history(symbol, days=days, minimum_candles=60)
            closes = [candle.close for candle in history.candles]
            if len(closes) < 70:
                continue

            return_20 = calculate_window_return(closes, 20)
            return_60 = calculate_window_return(closes, 60)
            prior_return_20 = calculate_prior_window_return(closes, 20, offset=10)
            rs_score = clamp_score(55 + ((return_20 - spy_return_20) * 2) + ((return_60 - spy_return_60) * 1.2))
            prior_rs_score = clamp_score(55 + ((prior_return_20 - spy_return_20) * 2))
            change_in_rs = round(rs_score - prior_rs_score, 2)
            ema_20 = calculate_ema(closes, 20)
            ema_50 = calculate_ema(closes, 50)
            trend_status = get_trend_status(closes[-1], ema_20, ema_50)
            score = clamp_score((rs_score * 0.65) + (get_trend_score(trend_status) * 0.35))
            category = classify_leadership(score, rs_score, change_in_rs, trend_status)

            if history.is_live:
                live_count += 1
            if history.fallback_used:
                fallback_count += 1
            if history.as_of:
                as_of_values.append(history.as_of)

            candidates.append(
                LeadershipStock(
                    symbol=symbol,
                    category=category,
                    score=score,
                    reason=build_leadership_reason(score, rs_score, change_in_rs, trend_status),
                    relative_strength=rs_score,
                    change_in_rs=change_in_rs,
                    trend_status=trend_status,
                    sector=get_symbol_sector(symbol),
                    industry_group=get_symbol_industry_group(symbol),
                    data_source=history.source,
                    overall_mode=get_overall_mode(history.is_live, history.fallback_used),
                )
            )
        except Exception:
            continue

    categories = [
        LeadershipCategory(
            category="New Leaders",
            items=select_category(candidates, "New Leaders", 3),
        ),
        LeadershipCategory(
            category="Current Leaders",
            items=select_category(candidates, "Current Leaders", 4),
        ),
        LeadershipCategory(
            category="Weakening Leaders",
            items=select_category(candidates, "Weakening Leaders", 3),
        ),
        LeadershipCategory(
            category="Former Leaders",
            items=select_category(candidates, "Former Leaders", 3),
        ),
    ]
    current_leaders = categories[1].items or sorted(candidates, key=lambda item: item.score, reverse=True)[:2]
    modes = {item.overall_mode for item in candidates if item.overall_mode}
    overall_mode = "live" if modes == {"live"} else "mixed" if "live" in modes or "mixed" in modes else "mock"

    result = LeadershipResponse(
        categories=categories,
        summary=(
            f"{current_leaders[0].symbol} and {current_leaders[1].symbol} remain the strongest current leaders."
            if len(current_leaders) >= 2
            else "Leadership data is available, but no broad leadership cluster is confirmed."
        ),
        overall_mode=overall_mode,
        coverage_percent=round((len(candidates) / len(symbols)) * 100, 2) if symbols else 0,
        as_of=max(as_of_values) if as_of_values else None,
    )
    set_cached_value(cache_key, result, int(os.getenv("BREADTH_CACHE_TTL_SECONDS", "900")))
    return result


def build_leadership_universe() -> list[str]:
    core_symbols = [item["symbol"] for item in CORE_BREADTH_UNIVERSE[:30]]
    return list(dict.fromkeys([*WATCHLIST_SYMBOLS, *core_symbols]))


def calculate_window_return(closes: list[float], lookback: int) -> float:
    if len(closes) <= lookback or closes[-lookback - 1] == 0:
        return 0.0
    return round(((closes[-1] - closes[-lookback - 1]) / closes[-lookback - 1]) * 100, 2)


def calculate_prior_window_return(closes: list[float], lookback: int, offset: int) -> float:
    end_index = len(closes) - offset
    start_index = end_index - lookback - 1
    if start_index < 0 or end_index <= 0 or closes[start_index] == 0:
        return 0.0
    return round(((closes[end_index - 1] - closes[start_index]) / closes[start_index]) * 100, 2)


def classify_leadership(score: int, relative_strength: int, change_in_rs: float, trend_status: str) -> str:
    if relative_strength >= 78 and change_in_rs >= 4 and "Above" in trend_status:
        return "New Leaders"
    if score >= 78 and relative_strength >= 75 and "Above EMA50" in trend_status:
        return "Current Leaders"
    if score >= 65 and change_in_rs < -3:
        return "Weakening Leaders"
    if relative_strength < 55 or "Below EMA50" in trend_status:
        return "Former Leaders"
    return "Current Leaders"


def select_category(candidates: list[LeadershipStock], category: str, limit: int) -> list[LeadershipStock]:
    items = [item for item in candidates if item.category == category]
    return sorted(items, key=lambda item: item.score, reverse=True)[:limit]


def build_leadership_reason(score: int, relative_strength: int, change_in_rs: float, trend_status: str) -> str:
    if score >= 85 and change_in_rs >= 0:
        return f"Strong RS, {trend_status.lower()}, and stable leadership versus the prior window."
    if change_in_rs > 3:
        return f"Relative strength improved by {change_in_rs} points while trend remains {trend_status.lower()}."
    if change_in_rs < -3:
        return f"Relative strength slipped by {abs(change_in_rs)} points despite a score of {score}."
    if relative_strength < 60:
        return "Relative strength is below leadership thresholds."
    return f"Trend is {trend_status.lower()} with relative strength at {relative_strength}."


def get_trend_status(price: float, ema_20: float | None, ema_50: float | None) -> str:
    if ema_20 is not None and ema_50 is not None and price > ema_20 > ema_50:
        return "Above EMA20/EMA50"
    if ema_50 is not None and price > ema_50:
        return "Above EMA50"
    if ema_50 is not None:
        return "Below EMA50"
    return "Trend unavailable"


def get_trend_score(trend_status: str) -> int:
    if trend_status == "Above EMA20/EMA50":
        return 90
    if trend_status == "Above EMA50":
        return 75
    if trend_status == "Below EMA50":
        return 35
    return 50


def get_symbol_industry_group(symbol: str) -> str:
    normalized = symbol.upper()
    for group in INDUSTRY_GROUP_BASKETS:
        if normalized in group["symbols"]:
            return group["name"]
    return "Unclassified"


def get_overall_mode(is_live: bool, fallback_used: bool) -> str:
    if is_live and not fallback_used:
        return "live"
    if is_live or fallback_used:
        return "mixed"
    return "mock"


def clamp_score(value: float | int) -> int:
    return max(0, min(100, round(value)))

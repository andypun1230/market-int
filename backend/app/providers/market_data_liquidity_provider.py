from datetime import datetime, timezone

from app.providers.cache import get_cached_value, set_cached_value
from app.providers.intelligence_models import LiquidityData, SourceMetadata
from app.providers.liquidity_base import LiquidityProvider
from app.providers.models import ProviderCapabilities, ProviderHealth
from app.providers.selector import get_int_env, get_market_data_provider
from app.services.candle_data import get_symbol_history


class MarketDataLiquidityProvider(LiquidityProvider):
    def get_quote_liquidity(self, symbol: str) -> LiquidityData:
        normalized = symbol.upper()
        cache_key = f"liquidity:{normalized}:{time_bucket()}"
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached

        provider = get_market_data_provider()
        quote = provider.get_quote(normalized)
        history, validation = get_symbol_history(normalized, days=60, minimum_candles=20)
        candles = history.candles
        average_daily_volume = (
            sum(candle.volume for candle in candles[-20:]) / min(len(candles), 20)
            if candles else None
        )
        average_price = (
            sum(candle.close for candle in candles[-20:]) / min(len(candles), 20)
            if candles else quote.price
        )
        average_dollar_volume = (
            average_daily_volume * average_price
            if average_daily_volume is not None and average_price is not None
            else None
        )
        bid = quote.previous_close if quote.previous_close and quote.price else None
        ask = quote.price if quote.price else None
        spread = abs(ask - bid) if bid is not None and ask is not None else None
        spread_percent = (spread / ask) * 100 if spread is not None and ask else None
        relative_volume = (
            candles[-1].volume / average_daily_volume
            if candles and average_daily_volume and average_daily_volume > 0
            else None
        )
        score = calculate_liquidity_score(average_dollar_volume, spread_percent, relative_volume)
        metadata = SourceMetadata(
            source=history.source if history.source == quote.source else f"quote:{quote.source};history:{history.source}",
            is_live=quote.is_live or history.is_live,
            is_stale=quote.is_stale or history.is_stale,
            fallback_used=quote.fallback_used or history.fallback_used,
            as_of=max(quote.timestamp, history.as_of),
            quality_score=validation.get("quality_score"),
            warnings=build_warnings(spread_percent, average_dollar_volume, quote.is_stale),
        )
        result = LiquidityData(
            symbol=normalized,
            average_daily_volume=round(average_daily_volume, 2) if average_daily_volume is not None else None,
            average_dollar_volume=round(average_dollar_volume, 2) if average_dollar_volume is not None else None,
            bid=bid,
            ask=ask,
            spread=round(spread, 4) if spread is not None else None,
            spread_percent=round(spread_percent, 4) if spread_percent is not None else None,
            relative_volume=round(relative_volume, 2) if relative_volume is not None else None,
            liquidity_score=score,
            status=get_liquidity_status(score),
            institutional_capacity=get_capacity_tier(average_dollar_volume),
            summary=f"{normalized} liquidity is {get_liquidity_status(score).lower()} based on spread, volume, and dollar-volume proxies.",
            metadata=metadata,
        )
        set_cached_value(cache_key, result, get_int_env("LIQUIDITY_CACHE_TTL_SECONDS", 300))
        return result

    def get_liquidity_health(self) -> ProviderHealth:
        health = get_market_data_provider().get_provider_health()
        return ProviderHealth(
            provider="market_data",
            enabled=True,
            configured=True,
            reachable=health.reachable,
            last_successful_request=health.last_successful_request,
            last_error=health.last_error,
            fallback_active=health.fallback_active,
            capabilities=ProviderCapabilities(
                quotes=True,
                daily_history=True,
                intraday_history=False,
                adjusted_history=True,
                volume=True,
            ),
        )


def calculate_liquidity_score(
    average_dollar_volume: float | None,
    spread_percent: float | None,
    relative_volume: float | None,
) -> float:
    score = 50.0
    if average_dollar_volume is not None:
        if average_dollar_volume >= 5_000_000_000:
            score += 30
        elif average_dollar_volume >= 1_000_000_000:
            score += 24
        elif average_dollar_volume >= 250_000_000:
            score += 15
        elif average_dollar_volume < 50_000_000:
            score -= 15

    if spread_percent is not None:
        if spread_percent <= 0.05:
            score += 15
        elif spread_percent <= 0.15:
            score += 8
        elif spread_percent > 0.5:
            score -= 20

    if relative_volume is not None:
        if relative_volume >= 1.2:
            score += 8
        elif relative_volume < 0.6:
            score -= 8

    return max(0, min(100, round(score, 2)))


def get_liquidity_status(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 72:
        return "Strong"
    if score >= 58:
        return "Adequate"
    if score >= 40:
        return "Thin"
    return "Poor"


def get_capacity_tier(average_dollar_volume: float | None) -> str:
    if average_dollar_volume is None:
        return "Unknown"
    if average_dollar_volume >= 5_000_000_000:
        return "Very High"
    if average_dollar_volume >= 1_000_000_000:
        return "High"
    if average_dollar_volume >= 250_000_000:
        return "Moderate"
    return "Low"


def build_warnings(
    spread_percent: float | None,
    average_dollar_volume: float | None,
    is_stale: bool,
) -> list[str]:
    warnings: list[str] = []
    if spread_percent is None:
        warnings.append("Incomplete quote data; spread is estimated.")
    elif spread_percent > 0.5:
        warnings.append("Wide spread")
    if average_dollar_volume is not None and average_dollar_volume < 50_000_000:
        warnings.append("Low dollar volume")
    if is_stale:
        warnings.append("Stale quote")
    return warnings


def time_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M")

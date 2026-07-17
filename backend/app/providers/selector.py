import os
from pathlib import Path
from typing import Callable, TypeVar

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app.providers.base import MarketDataProvider
from app.providers.cache import get_provider_cache_status, set_cached_value
from app.providers.circuit_breaker import get_circuit_breaker_status
from app.providers.mock_provider import MockMarketDataProvider
from app.providers.models import HistoryData, ProviderHealth, QuoteData
from app.providers.test_provider import GeneratedTestMarketDataProvider, TEST_DATA_SOURCE
from app.services.market_data_repository import get_market_data_repository
from app.test_data.repository import get_test_data_status

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"

if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH)

T = TypeVar("T", QuoteData, HistoryData)
_fallback_active = False


class FallbackMarketDataProvider(MarketDataProvider):
    """Wrap a live provider and clearly mark mock fallback responses."""

    def __init__(
        self,
        primary_provider: MarketDataProvider,
        fallback_provider: MockMarketDataProvider,
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.fallback_active = False

    def get_quote(self, symbol: str) -> QuoteData:
        try:
            result = self.primary_provider.get_quote(symbol)
            self.fallback_active = False
            return result
        except Exception:
            self.fallback_active = True
            set_global_fallback_active()
            fallback_quote = mark_mock_fallback(self.fallback_provider.get_quote(symbol))
            set_cached_value(
                f"quote:{symbol.upper()}",
                fallback_quote,
                get_int_env("MARKET_DATA_CACHE_TTL_SECONDS", 60),
            )
            return fallback_quote

    def get_history(
        self,
        symbol: str,
        resolution: str = "D",
        days: int = 240,
    ) -> HistoryData:
        normalized_symbol = symbol.upper()
        normalized_resolution = resolution.upper()
        safe_days = max(1, min(days, 1500))

        try:
            result = self.primary_provider.get_history(normalized_symbol, normalized_resolution, safe_days)
            self.fallback_active = False
            return result
        except Exception:
            self.fallback_active = True
            set_global_fallback_active()
            fallback_history = mark_mock_fallback(
                self.fallback_provider.get_history(normalized_symbol, normalized_resolution, safe_days)
            )
            set_cached_value(
                f"history:{normalized_symbol}:{normalized_resolution}:{safe_days}",
                fallback_history,
                get_int_env("MARKET_DATA_HISTORY_CACHE_TTL_SECONDS", 900),
            )
            return fallback_history

    def get_provider_health(self) -> ProviderHealth:
        health = self.primary_provider.get_provider_health()
        return health.model_copy(update={"fallback_active": self.fallback_active or _fallback_active})

    def get_index_snapshots(self) -> dict[str, object]:
        return self.fallback_provider.get_index_snapshots()

    def get_sector_etfs(self) -> dict[str, object]:
        return self.fallback_provider.get_sector_etfs()

    def get_watchlist_symbols(self) -> list[str]:
        return self.fallback_provider.get_watchlist_symbols()

    def with_fallback(self, primary: Callable[[], T], fallback: Callable[[], T]) -> T:
        global _fallback_active

        try:
            result = primary()
            self.fallback_active = False
            return result
        except Exception:
            self.fallback_active = True
            _fallback_active = True
            return mark_mock_fallback(fallback())


def get_market_data_provider() -> MarketDataProvider:
    """Return the configured market-data repository.

    Default mode remains generated test data so automated tests and UI
    development never call live providers accidentally. Set DATA_PROVIDER or
    MARKET_DATA_PROVIDER to finnhub/live/auto to use the live pilot path.
    """
    return get_market_data_repository()


def get_provider_status() -> dict[str, object]:
    provider = get_market_data_repository()
    health = provider.get_provider_health()
    quote_health = health.model_dump()
    history_health = health.model_dump()
    test_data = get_test_data_status()
    selected = get_selected_provider_name()
    active = health.provider
    live_ready = selected in {"finnhub", "live", "auto"} and bool(health.configured)
    cache_status = provider.get_cache_status()
    routing = cache_status.get("provider_routing", {}) if isinstance(cache_status, dict) else {}
    configured_quote = str(routing.get("configured_quote_provider") or get_quote_provider_name())
    configured_history = str(routing.get("configured_history_provider") or get_history_provider_name())
    capabilities = routing.get("capabilities", {}) if isinstance(routing, dict) else {}
    history_capability = capabilities.get(configured_history, {}) if isinstance(capabilities, dict) else {}
    quote_capability = capabilities.get(configured_quote, {}) if isinstance(capabilities, dict) else {}

    return {
        "mode": selected.upper(),
        "data_status": "test" if selected in {"test", "mock"} else health.status or "unavailable",
        "source": active,
        "data_provider": selected,
        "market_data_provider": selected,
        "quote_provider": configured_quote,
        "history_provider": configured_history,
        "configured_provider": selected,
        "configured_quote_provider": configured_quote,
        "configured_history_provider": configured_history,
        "active_provider": active,
        "active_quote_provider": configured_quote,
        "active_history_provider": configured_history,
        "live_ready": live_ready,
        "history_ready": history_capability.get("daily_history_access_state") == "available" if isinstance(history_capability, dict) else bool(health.capabilities.daily_history if health.capabilities else health.reachable),
        "fallback_enabled": is_mock_fallback_enabled(),
        "fallback_active": health.fallback_active,
        "cache_status": {
            "repository": cache_status,
            "provider_cache": get_provider_cache_status(),
        },
        "provider_routing": routing,
        "provider_capabilities": capabilities,
        "quote_capability": quote_capability,
        "history_capability": history_capability,
        "circuit_breakers": get_circuit_breaker_status(),
        "health": health.model_dump(),
        "quote_health": quote_health,
        "history_health": history_health,
        "test_data": test_data,
        "sentiment_provider": "generated_test_data",
        "options_provider": "generated_test_data",
        "trade_flow_provider": "generated_test_data",
        "liquidity_provider": "generated_test_data",
        "sentiment_health": get_sentiment_provider().get_sentiment_health().model_dump(),
        "options_health": get_options_provider().get_options_health().model_dump(),
        "trade_flow_health": get_trade_flow_provider().get_trade_flow_health().model_dump(),
        "liquidity_health": get_liquidity_provider().get_liquidity_health().model_dump(),
    }


def get_sentiment_provider():
    from app.providers.market_proxy_sentiment_provider import MarketProxySentimentProvider

    return MarketProxySentimentProvider()


def get_options_provider():
    from app.providers.mock_intelligence_provider import MockOptionsDataProvider

    return MockOptionsDataProvider()


def get_trade_flow_provider():
    from app.providers.mock_intelligence_provider import MockTradeFlowProvider

    return MockTradeFlowProvider()


def get_liquidity_provider():
    from app.providers.market_data_liquidity_provider import MarketDataLiquidityProvider

    return MarketDataLiquidityProvider()


def get_intelligence_status() -> dict[str, object]:
    sentiment_health = get_sentiment_provider().get_sentiment_health().model_dump()
    options_health = get_options_provider().get_options_health().model_dump()
    trade_flow_health = get_trade_flow_provider().get_trade_flow_health().model_dump()
    liquidity_health = get_liquidity_provider().get_liquidity_health().model_dump()
    health_items = {
        "sentiment": sentiment_health,
        "options": options_health,
        "trade_flow": trade_flow_health,
        "liquidity": liquidity_health,
    }
    return {
        **health_items,
        "overall_mode": "test",
        "data_status": "test",
        "source": TEST_DATA_SOURCE,
        "fallback_enabled": False,
        "sentiment_provider": "generated_test_data",
        "options_provider": "generated_test_data",
        "trade_flow_provider": "generated_test_data",
        "liquidity_provider": "generated_test_data",
        "limitations": [
            "All market intelligence values are generated test data for interface development.",
            "Large-print activity, money flow, and gamma exposure are deterministic scenarios.",
        ],
        "cache_status": get_provider_cache_status(),
    }


def get_selected_provider_name() -> str:
    return get_env_provider("DATA_PROVIDER", get_env_provider("MARKET_DATA_PROVIDER", "test"))


def get_quote_provider_name() -> str:
    return get_env_provider("QUOTE_DATA_PROVIDER", get_env_provider("QUOTE_PROVIDER", get_selected_provider_name()))


def get_history_provider_name() -> str:
    return get_env_provider("HISTORY_DATA_PROVIDER", get_env_provider("HISTORY_PROVIDER", get_selected_provider_name()))


def build_provider(provider_name: str) -> MarketDataProvider:
    if provider_name == "mock":
        return MockMarketDataProvider()
    if provider_name in {"test", "generated_test_data"}:
        return GeneratedTestMarketDataProvider()
    if provider_name in {"finnhub", "live", "auto"}:
        from app.providers.finnhub_provider import FinnhubMarketDataProvider

        return FinnhubMarketDataProvider()
    return GeneratedTestMarketDataProvider()


def get_env_provider(name: str, default: str = "mock") -> str:
    return (os.getenv(name) or default).lower()


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def is_mock_fallback_enabled() -> bool:
    return str(os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "true")).lower() in {"1", "true", "yes", "on"}


def mark_mock_fallback(value: T) -> T:
    return value.model_copy(
        update={
            "source": "mock-fallback",
            "is_live": False,
            "fallback_used": True,
            "is_stale": False,
        }
    )


def set_global_fallback_active() -> None:
    global _fallback_active
    _fallback_active = True

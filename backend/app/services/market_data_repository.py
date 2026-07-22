from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from app.providers.base import MarketDataProvider
from app.providers.finnhub_provider import FinnhubMarketDataProvider, ProviderRequestError
from app.providers.mock_provider import MockMarketDataProvider
from app.providers.models import (
    BatchQuoteResult,
    HistoryData,
    ProviderCapabilities,
    ProviderHealth,
    QuoteData,
)
from app.providers.router import MarketDataProviderRouter, is_stable_permission_error
from app.providers.symbols import normalize_market_symbol
from app.providers.test_provider import GeneratedTestMarketDataProvider, TEST_DATA_SOURCE
from app.cache.market_data_cache import (
    CacheLookupResult,
    LayeredMarketDataCache,
    build_history_cache_key,
    build_quote_cache_key,
)
from app.services.history_request_coordinator import get_history_request_coordinator
from app.services.report_read_context import ReportReadCacheMiss, is_report_snapshot_read


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    expires_at: float


@dataclass
class InFlight:
    event: threading.Event
    result: Any = None
    error: BaseException | None = None


class MemoryMarketDataCache:
    def __init__(self, max_items: int = 1000) -> None:
        self.max_items = max_items
        self._items: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0

    def get(self, key: str) -> tuple[Any | None, int | None]:
        now = time.time()
        with self._lock:
            entry = self._items.get(key)
            if not entry:
                self.miss_count += 1
                return None, None
            if entry.expires_at <= now:
                self._items.pop(key, None)
                self.miss_count += 1
                return None, None
            self.hit_count += 1
            return clone_model(entry.value), int(now - entry.created_at)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            if len(self._items) >= self.max_items:
                oldest = min(self._items.items(), key=lambda item: item[1].created_at)[0]
                self._items.pop(oldest, None)
            now = time.time()
            self._items[key] = CacheEntry(clone_model(value), now, now + max(1, ttl_seconds))

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._items.clear()
                return
            for key in [key for key in self._items if key.startswith(prefix)]:
                self._items.pop(key, None)

    def status(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            return {
                "items": len(self._items),
                "keys": sorted(self._items.keys()),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "oldest_item_age_seconds": int(max((now - item.created_at for item in self._items.values()), default=0)),
                "newest_item_age_seconds": int(min((now - item.created_at for item in self._items.values()), default=0)),
            }


class MarketDataRepository(MarketDataProvider):
    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        fallback_provider: MockMarketDataProvider | None = None,
        *,
        data_provider: str | None = None,
        cache: MemoryMarketDataCache | None = None,
    ) -> None:
        self.data_provider = (data_provider or os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test").lower()
        self.router = MarketDataProviderRouter()
        self.primary_provider = provider or build_provider_for_mode(self.data_provider)
        self._explicit_provider = provider is not None
        self.fallback_provider = fallback_provider or MockMarketDataProvider()
        self.cache = cache or LayeredMarketDataCache()
        self.cache_enabled = env_bool("MARKET_DATA_CACHE_ENABLED", True)
        self.allow_mock_fallback = env_bool("MARKET_DATA_ALLOW_MOCK_FALLBACK", True)
        self.quote_ttl_seconds = env_int("MARKET_DATA_QUOTE_TTL_SECONDS", env_int("MARKET_DATA_CACHE_TTL_SECONDS", 20))
        self.history_ttl_seconds = env_int("MARKET_DATA_HISTORY_TTL_SECONDS", env_int("MARKET_DATA_HISTORY_CACHE_TTL_SECONDS", 1800))
        self.max_batch_quotes = env_int("MARKET_DATA_MAX_BATCH_QUOTES", 50)
        self.stale_while_revalidate = env_bool("MARKET_DATA_STALE_WHILE_REVALIDATE", True)
        self._inflight: dict[str, InFlight] = {}
        self._inflight_lock = threading.RLock()
        self._background_refresh: dict[str, InFlight] = {}
        self.last_successful_quote_request: str | None = None
        self.last_successful_history_request: str | None = None
        self.last_fallback_reason: str | None = None
        self.fallback_active = False
        self.provider_call_count = 0
        self.background_refresh_count = 0
        self.background_refresh_failure_count = 0
        self.unavailable_count = 0

    def get_quote(self, symbol: str) -> QuoteData:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        provider_name = self.get_provider_name_for("quotes")
        key = build_quote_cache_key(provider_name, normalized)
        return self._get_or_compute(
            key,
            self.quote_ttl_seconds,
            lambda: self._fetch_quote(normalized),
            mark_cached_quote,
            domain="quotes",
        )

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        normalized, _ = normalize_batch_symbols(symbols, limit=self.max_batch_quotes)
        return [self.get_quote(symbol) for symbol in normalized]

    def get_batch_quotes(self, symbols: list[str]) -> BatchQuoteResult:
        quotes: list[QuoteData] = []
        normalized, unavailable = normalize_batch_symbols(symbols, limit=self.max_batch_quotes)
        for symbol in normalized:
            try:
                quote = self.get_quote(symbol)
                quotes.append(quote)
                if quote.source_state == "unavailable":
                    unavailable.append(symbol)
            except Exception:
                unavailable.append(symbol)
        return BatchQuoteResult(
            quotes=quotes,
            unavailable_symbols=unavailable,
            provider=self.active_provider_name,
            source_state=aggregate_source_state([quote.source_state or source_state_from_quote(quote) for quote in quotes]),
            fetched_at=datetime.now(timezone.utc),
        )

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        requested_symbol = normalize_market_symbol(symbol, apply_alias=False)
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        normalized_resolution = resolution.upper()
        safe_days = max(1, min(int(days), 1500))
        provider_name = self.get_provider_name_for("daily_history")
        key = build_history_cache_key(provider_name, normalized, normalized_resolution, safe_days)
        compatible = self._get_compatible_history_cache(provider_name, normalized, normalized_resolution, safe_days, key)
        if compatible is not None:
            return mark_history_symbol_metadata(compatible, requested_symbol=requested_symbol, provider_symbol=normalized)
        result = self._get_or_compute(
            key,
            self.history_ttl_seconds,
            lambda: self._fetch_history(normalized, normalized_resolution, safe_days),
            mark_cached_history,
            domain="daily_history",
        )
        return mark_history_symbol_metadata(result, requested_symbol=requested_symbol, provider_symbol=normalized)

    def get_provider_health(self) -> ProviderHealth:
        health = self.get_provider_for("quotes").get_provider_health()
        status = health.status or classify_health_status(health, self.data_provider)
        return health.model_copy(update={
            "provider": self.active_provider_name,
            "fallback_active": self.fallback_active,
            "status": status,
            "checked_at": now_iso(),
            "message": health.message or provider_mode_message(self.data_provider),
        })

    def get_capabilities(self) -> ProviderCapabilities:
        return self.get_provider_for("quotes").get_capabilities()

    def get_index_snapshots(self) -> dict[str, Any]:
        return {"indexes": [quote.model_dump() for quote in self.get_quotes(["SPY", "QQQ", "IWM", "DIA"])]}

    def get_sector_etfs(self) -> dict[str, Any]:
        return self.get_provider_for("quotes").get_sector_etfs()

    def get_watchlist_symbols(self) -> list[str]:
        return self.get_provider_for("quotes").get_watchlist_symbols()

    def invalidate_quote(self, symbol: str) -> None:
        self.cache.invalidate(f"quote:{self.active_provider_name}:{normalize_market_symbol(symbol, apply_alias=True)}")

    def invalidate_history(self, symbol: str) -> None:
        self.cache.invalidate(f"history:{self.active_history_provider_name}:{normalize_market_symbol(symbol, apply_alias=True)}")

    def get_cache_status(self) -> dict[str, Any]:
        status = self.cache.status()
        status["repository_metrics"] = {
            "provider_calls": self.provider_call_count,
            "background_refreshes": self.background_refresh_count,
            "background_refresh_failures": self.background_refresh_failure_count,
            "fallback_active": self.fallback_active,
            "unavailable_results": self.unavailable_count,
        }
        status["history_request_coordinator"] = get_history_request_coordinator().status()
        status["provider_routing"] = self.router.status() if not self._explicit_provider else {"mode": "explicit_provider"}
        return status

    @property
    def active_provider_name(self) -> str:
        health = self.get_provider_for("quotes").get_provider_health()
        return health.provider

    @property
    def active_history_provider_name(self) -> str:
        return self.get_provider_name_for("daily_history")

    def get_provider_for(self, domain: str) -> MarketDataProvider:
        if self._explicit_provider or self.data_provider in {"test", "generated_test_data", "mock"}:
            return self.primary_provider
        if domain == "daily_history":
            return self.router.get_provider_for("daily_history")
        return self.router.get_provider_for("quotes")

    def get_provider_name_for(self, domain: str) -> str:
        if self._explicit_provider or self.data_provider in {"test", "generated_test_data", "mock"}:
            return self.primary_provider.get_provider_health().provider
        return self.router.get_provider_name_for("daily_history" if domain == "daily_history" else "quotes")

    def _get_or_compute(self, key: str, ttl: int, compute: Callable[[], Any], mark_cached: Callable[[Any, int], Any], *, domain: str) -> Any:
        if self.cache_enabled:
            cached, age = self.cache.get(key)
            if cached is not None:
                return mark_cached(cached, age or 0)
            stale = self._get_stale_cache_value(key)
            if stale.value is not None and stale.stale:
                result = mark_stale_cached_value(stale.value, stale.age_seconds or 0, refresh_started=False)
                if self.stale_while_revalidate and not is_report_snapshot_read():
                    started = self._start_background_refresh(key, ttl, compute, domain=domain)
                    result = mark_background_refresh(result, started)
                return result

        if self._report_read_blocks_provider_fetch():
            raise ReportReadCacheMiss(f"Report read has no captured cache value for {key}.")

        inflight, owner = self._get_or_create_inflight(key)
        if not owner:
            inflight.event.wait(timeout=env_float("MARKET_DATA_TIMEOUT_SECONDS", 8) + 2)
            if inflight.error:
                raise inflight.error
            return clone_model(inflight.result)

        try:
            result = compute()
            if self.cache_enabled:
                self._set_cache_value(key, result, ttl, domain=domain)
            inflight.result = clone_model(result)
            return result
        except BaseException as exc:
            inflight.error = exc
            raise
        finally:
            inflight.event.set()
            with self._inflight_lock:
                self._inflight.pop(key, None)

    def _get_or_create_inflight(self, key: str) -> tuple[InFlight, bool]:
        with self._inflight_lock:
            existing = self._inflight.get(key)
            if existing:
                return existing, False
            created = InFlight(event=threading.Event())
            self._inflight[key] = created
            return created, True

    def _report_read_blocks_provider_fetch(self) -> bool:
        # Deterministic test providers are local fixtures, not external
        # provider work. Live report reads must use durable values only.
        return is_report_snapshot_read() and self.data_provider not in {
            "mock",
            "test",
            "generated_test_data",
        }

    def _fetch_quote(self, symbol: str) -> QuoteData:
        provider = self.get_provider_for("quotes")
        provider_name = self.get_provider_name_for("quotes")
        try:
            self.provider_call_count += 1
            quote = provider.get_quote(symbol)
            self.fallback_active = False
            self.last_successful_quote_request = now_iso()
            return annotate_quote(quote, provider=provider.get_provider_health().provider, source_state=source_state_from_provider(provider_name, quote))
        except Exception as exc:
            return self._fallback_quote(symbol, exc, original_provider=provider_name)

    def _fetch_history(self, symbol: str, resolution: str, days: int) -> HistoryData:
        provider_name = self.get_provider_name_for("daily_history")
        try:
            provider = self.get_provider_for("daily_history")
            def fetch() -> HistoryData:
                self.provider_call_count += 1
                return provider.get_history(symbol, resolution=resolution, days=days)

            if provider_name in {"polygon", "massive"}:
                key = f"{provider_name}:{symbol}:{resolution}:{days}"
                history = get_history_request_coordinator().run(key, fetch)
            else:
                history = fetch()
            self.fallback_active = False
            self.last_successful_history_request = now_iso()
            return annotate_history(history, provider=provider.get_provider_health().provider, source_state=source_state_from_provider(provider_name, history))
        except Exception as exc:
            if is_stable_permission_error(exc) and not self._explicit_provider:
                self.router.mark_restricted(provider_name, "daily_history", safe_error_reason(exc))
            return self._fallback_history(symbol, resolution, days, exc, original_provider=provider_name)

    def _fallback_quote(self, symbol: str, error: BaseException, *, original_provider: str | None = None) -> QuoteData:
        if not self.allow_mock_fallback:
            self.unavailable_count += 1
            raise ProviderRequestError("Quote unavailable and mock fallback is disabled.", category="unavailable") from error
        self.fallback_active = True
        self.last_fallback_reason = safe_error_reason(error)
        fallback = self.fallback_provider.get_quote(symbol)
        return annotate_quote(
            fallback.model_copy(update={"source": "mock-fallback", "fallback_used": True, "is_live": False}),
            provider="mock",
            source_state="mock",
            fallback_reason=self.last_fallback_reason,
            original_provider=original_provider,
        )

    def _fallback_history(self, symbol: str, resolution: str, days: int, error: BaseException, *, original_provider: str | None = None) -> HistoryData:
        if not self.allow_mock_fallback:
            self.unavailable_count += 1
            raise ProviderRequestError("History unavailable and mock fallback is disabled.", category="unavailable") from error
        self.fallback_active = True
        self.last_fallback_reason = safe_error_reason(error)
        fallback = self.fallback_provider.get_history(symbol, resolution=resolution, days=days)
        return annotate_history(
            fallback.model_copy(update={"source": "mock-fallback", "fallback_used": True, "is_live": False}),
            provider="mock",
            source_state="mock",
            fallback_reason=self.last_fallback_reason,
            original_provider=original_provider,
        )

    def _get_stale_cache_value(self, key: str) -> CacheLookupResult:
        if hasattr(self.cache, "get_stale"):
            return self.cache.get_stale(key)
        return CacheLookupResult(None, False, False, "unsupported")

    def _get_compatible_history_cache(self, provider: str, symbol: str, resolution: str, days: int, key: str) -> HistoryData | None:
        if not self.cache_enabled or not isinstance(self.cache, LayeredMarketDataCache):
            return None
        cached, age = self.cache.get(key)
        if cached is not None:
            return mark_cached_history(cached, age or 0)
        found, found_age, _source_key = self.cache.find_history_covering(provider, symbol, resolution, days)
        if found is None:
            return None
        return mark_cached_history(found, found_age or 0)

    def _set_cache_value(self, key: str, result: Any, ttl: int, *, domain: str) -> None:
        if isinstance(self.cache, LayeredMarketDataCache):
            self.cache.set(
                key,
                result,
                ttl,
                domain=domain,
                provider=getattr(result, "provider", None) or getattr(result, "source", None),
                source_state=getattr(result, "source_state", None) or source_state_from_provider(getattr(result, "provider", None) or "", result),
            )
        else:
            self.cache.set(key, result, ttl)

    def _start_background_refresh(self, key: str, ttl: int, compute: Callable[[], Any], *, domain: str) -> bool:
        with self._inflight_lock:
            if key in self._background_refresh:
                return False
            inflight = InFlight(event=threading.Event())
            self._background_refresh[key] = inflight

        def refresh() -> None:
            try:
                result = compute()
                if getattr(result, "fallback_used", False) or getattr(result, "source_state", None) == "mock":
                    inflight.error = RuntimeError("Background refresh returned fallback data; preserving stale cache.")
                    self.background_refresh_failure_count += 1
                    return
                self._set_cache_value(key, result, ttl, domain=domain)
                inflight.result = result
                self.background_refresh_count += 1
            except BaseException as exc:
                inflight.error = exc
                self.background_refresh_failure_count += 1
            finally:
                inflight.event.set()
                with self._inflight_lock:
                    self._background_refresh.pop(key, None)

        threading.Thread(target=refresh, name=f"market-cache-refresh:{key}", daemon=True).start()
        return True


_repository_lock = threading.RLock()
_repository: MarketDataRepository | None = None
_repository_signature: tuple[str | None, ...] | None = None


def get_market_data_repository() -> MarketDataRepository:
    global _repository, _repository_signature
    with _repository_lock:
        provider_mode = os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test"
        signature = repository_config_signature(provider_mode)
        if (
            _repository is None
            or _repository.data_provider != provider_mode.lower()
            or _repository_signature != signature
        ):
            _repository = MarketDataRepository(data_provider=provider_mode)
            _repository_signature = signature
        return _repository


def reset_market_data_repository() -> None:
    global _repository, _repository_signature
    with _repository_lock:
        _repository = None
        _repository_signature = None


def repository_config_signature(provider_mode: str) -> tuple[str | None, ...]:
    return (
        provider_mode.lower(),
        (os.getenv("MARKET_DATA_PROVIDER") or "").lower(),
        (os.getenv("QUOTE_DATA_PROVIDER") or os.getenv("QUOTE_PROVIDER") or "").lower(),
        (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "").lower(),
        (os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK") or "").lower(),
    )


def build_provider_for_mode(provider_name: str) -> MarketDataProvider:
    normalized = provider_name.lower()
    if normalized in {"test", "generated_test_data"}:
        return GeneratedTestMarketDataProvider()
    if normalized == "mock":
        return MockMarketDataProvider()
    if normalized in {"finnhub", "live", "auto"}:
        return FinnhubMarketDataProvider()
    if normalized in {"polygon", "massive"}:
        from app.providers.polygon_provider import PolygonMarketDataProvider

        return PolygonMarketDataProvider()
    return GeneratedTestMarketDataProvider()


def annotate_quote(
    quote: QuoteData,
    *,
    provider: str,
    source_state: str,
    fallback_reason: str | None = None,
    original_provider: str | None = None,
) -> QuoteData:
    return quote.model_copy(update={
        "provider": provider,
        "requested_provider": original_provider or provider,
        "source_state": source_state,
        "fetched_at": now_iso(),
        "cache_hit": False,
        "cache_age_seconds": None,
        "fallback_reason": fallback_reason,
        "original_provider": original_provider,
    })


def annotate_history(
    history: HistoryData,
    *,
    provider: str,
    source_state: str,
    fallback_reason: str | None = None,
    original_provider: str | None = None,
) -> HistoryData:
    return history.model_copy(update={
        "provider": provider,
        "provider_symbol": history.provider_symbol or history.symbol,
        "requested_provider": original_provider or provider,
        "source_state": source_state,
        "fetched_at": now_iso(),
        "cache_hit": False,
        "cache_age_seconds": None,
        "fallback_reason": fallback_reason,
        "original_provider": original_provider,
    })


def mark_history_symbol_metadata(history: HistoryData, *, requested_symbol: str, provider_symbol: str) -> HistoryData:
    return history.model_copy(update={
        "requested_symbol": requested_symbol,
        "provider_symbol": provider_symbol,
        "symbol": provider_symbol,
    })


def mark_cached_quote(quote: QuoteData, age_seconds: int) -> QuoteData:
    if quote.is_stale or quote.source_state == "stale":
        return mark_stale_cached_value(quote, age_seconds, refresh_started=False)
    return quote.model_copy(update={
        "source_state": "cached",
        "cache_hit": True,
        "cache_age_seconds": age_seconds,
        "is_stale": False,
        "memory_cache_hit": age_seconds == 0,
    })


def mark_cached_history(history: HistoryData, age_seconds: int) -> HistoryData:
    if history.is_stale or history.source_state == "stale":
        return mark_stale_cached_value(history, age_seconds, refresh_started=False)
    return history.model_copy(update={
        "source_state": "cached",
        "cache_hit": True,
        "cache_age_seconds": age_seconds,
        "is_stale": False,
        "memory_cache_hit": age_seconds == 0,
    })


def mark_stale_cached_value(value: Any, age_seconds: int, *, refresh_started: bool) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={
            "source_state": "stale",
            "cache_hit": True,
            "cache_age_seconds": age_seconds,
            "is_stale": True,
            "background_refresh_started": refresh_started,
        })
    return value


def mark_background_refresh(value: Any, started: bool) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"background_refresh_started": started})
    return value


def source_state_from_provider(provider: str, value: QuoteData | HistoryData) -> str:
    if value.source_state:
        return value.source_state
    if value.fallback_used:
        return "mock"
    if value.is_stale:
        return "stale"
    if value.is_live:
        return "live"
    if provider in {"mock", TEST_DATA_SOURCE} or value.source in {"mock", TEST_DATA_SOURCE}:
        return "mock"
    return "unavailable"


def source_state_from_quote(quote: QuoteData) -> str:
    return quote.source_state or source_state_from_provider(quote.provider or quote.source, quote)


def aggregate_source_state(states: list[str]) -> str:
    if not states:
        return "unavailable"
    unique = set(states)
    if len(unique) > 1:
        return "mixed"
    return states[0]


def normalize_batch_symbols(symbols: list[str], *, limit: int) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    unavailable: list[str] = []
    for symbol in symbols:
        try:
            value = normalize_market_symbol(symbol, apply_alias=True)
        except ValueError:
            raw = str(symbol or "").strip().upper() or "UNKNOWN"
            if raw not in unavailable:
                unavailable.append(raw)
            continue
        if value not in normalized:
            normalized.append(value)
        if len(normalized) >= limit:
            break
    return normalized, unavailable


def classify_health_status(health: ProviderHealth, provider_name: str) -> str:
    if provider_name in {"test", "generated_test_data"}:
        return "mock"
    if provider_name == "mock":
        return "mock"
    if not health.configured:
        return "not_configured"
    if health.reachable:
        return "healthy"
    return "unavailable"


def provider_mode_message(provider_name: str) -> str:
    if provider_name in {"test", "generated_test_data"}:
        return "Generated test-data provider is active."
    if provider_name == "mock":
        return "Deterministic mock provider is active."
    return f"{provider_name} provider is configured through the backend only."


def safe_error_reason(error: BaseException) -> str:
    if isinstance(error, ProviderRequestError):
        return error.category
    return type(error).__name__


def clone_model(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(deep=True)
    return value


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

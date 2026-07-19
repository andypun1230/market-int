import copy
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from pydantic import TypeAdapter

from app.cache.persistent_cache import (
    delete_persistent_value,
    delete_persistent_prefix,
    get_persistent_cache_status,
    get_persistent_value,
    set_persistent_value,
)
from app.models.market import (
    DashboardComparisonResponse,
    DecisionConfidenceResponse,
    DecisionDashboardResponse,
    IndustryGroupResponse,
    IndustryRotationResponse,
    InstitutionalDashboardResponse,
    InstitutionalIntelligenceResponse,
    LeadershipResponse,
    LiquidityDashboardResponse,
    MarketBreadthResponse,
    MarketHealthResponse,
    IndexSnapshot,
    MoneyFlowResponse,
    OptionsIntelligenceResponse,
    ProbabilityResponse,
    RiskDashboardV2Response,
    SectorBreadthItem,
    SectorEtfResponse,
    SectorsResponse,
    StockRatingResponse,
    WatchlistResponse,
    MarketSentimentResponse,
)
from app.utils.performance import measure_service

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class ServiceCacheEntry:
    value: object
    created_at: float
    expires_at: float


_cache: dict[str, ServiceCacheEntry] = {}
_locks: dict[str, threading.Lock] = {}
_global_lock = threading.RLock()
_stats = {
    "hits": 0,
    "misses": 0,
    "computes": 0,
    "duplicate_computations_avoided": 0,
}
_refreshing_keys: set[str] = set()

SERVICE_MODEL_BY_KEY = {
    "dashboard-comparison": DashboardComparisonResponse,
    "decision-confidence": DecisionConfidenceResponse,
    "decision-dashboard": DecisionDashboardResponse,
    "industry-groups": IndustryGroupResponse,
    "industry-groups:v2": IndustryGroupResponse,
    "industry-rotation": IndustryRotationResponse,
    "institutional-dashboard": InstitutionalDashboardResponse,
    "institutional-intelligence": InstitutionalIntelligenceResponse,
    "leadership": LeadershipResponse,
    "liquidity-dashboard": LiquidityDashboardResponse,
    "market-health": MarketHealthResponse,
    "market-sentiment": MarketSentimentResponse,
    "money-flow": MoneyFlowResponse,
    "options-intelligence": OptionsIntelligenceResponse,
    "probabilities": ProbabilityResponse,
    "risk-dashboard-v2": RiskDashboardV2Response,
    "sector-etfs": SectorEtfResponse,
    "sectors": SectorsResponse,
    "stock-ratings": StockRatingResponse,
    "watchlist": WatchlistResponse,
}


def get_service_ttl(env_name: str, default_seconds: int) -> int:
    try:
        return int(os.getenv(env_name, str(default_seconds)))
    except ValueError:
        return default_seconds


def get_cached_service_value(key: str) -> object | None:
    now = time.time()
    with _global_lock:
        entry = _cache.get(key)
        if entry is not None:
            if entry.expires_at > now:
                _stats["hits"] += 1
                return copy.deepcopy(entry.value)
            _cache.pop(key, None)

    persistent = get_persistent_service_value(key, allow_stale=False)
    if persistent is not None:
        ttl = max(1, int(persistent.expires_in_seconds))
        set_l1_service_value(key, persistent.value, ttl)
        _stats["hits"] += 1
        return copy.deepcopy(persistent.value)

    with _global_lock:
        _stats["misses"] += 1
    return None


def set_cached_service_value(key: str, value: object, ttl_seconds: int) -> object:
    set_l1_service_value(key, value, ttl_seconds)
    set_persistent_value(
        key,
        value,
        ttl_seconds=ttl_seconds,
        stale_seconds=get_stale_ttl_seconds(key),
        data_source=get_data_source(value),
        metadata={"service_cache": True},
    )
    return copy.deepcopy(value)


def set_l1_service_value(key: str, value: object, ttl_seconds: int) -> None:
    now = time.time()
    with _global_lock:
        _cache[key] = ServiceCacheEntry(
            value=copy.deepcopy(value),
            created_at=now,
            expires_at=now + max(0, ttl_seconds),
        )


def get_or_compute(key: str, ttl_seconds: int, compute_fn: Callable[[], T]) -> T:
    cached = get_cached_service_value(key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    lock = get_key_lock(key)
    acquired_without_wait = lock.acquire(blocking=False)
    if not acquired_without_wait:
        _stats["duplicate_computations_avoided"] += 1
        lock.acquire()

    try:
        cached_after_wait = get_cached_service_value(key)
        if cached_after_wait is not None:
            return cached_after_wait  # type: ignore[return-value]

        with measure_service(key):
            value = compute_fn()
        _stats["computes"] += 1
        return set_cached_service_value(key, value, ttl_seconds)  # type: ignore[return-value]
    finally:
        lock.release()


def get_or_compute_stale_while_revalidate(
    key: str,
    fresh_ttl_seconds: int,
    stale_ttl_seconds: int,
    compute_fn: Callable[[], T],
    background_refresh_fn: Callable[[], T] | None = None,
) -> tuple[T | None, dict[str, object]]:
    cached = get_cached_service_value(key)
    if cached is not None:
        return cached, build_cache_metadata("fresh", refreshing=False, age_seconds=0)

    stale = get_persistent_service_value(key, allow_stale=True)
    if stale is not None:
        trigger_background_refresh(
            key,
            fresh_ttl_seconds,
            compute_fn=background_refresh_fn or compute_fn,
        )
        set_l1_service_value(key, stale.value, min(30, fresh_ttl_seconds))
        return stale.value, build_cache_metadata(
            "stale",
            refreshing=True,
            age_seconds=stale.age_seconds,
            generated_at=stale.created_at,
            next_refresh_at=stale.expires_at,
        )

    trigger_background_refresh(
        key,
        fresh_ttl_seconds,
        compute_fn=background_refresh_fn or compute_fn,
    )
    return None, build_cache_metadata("miss", refreshing=True, age_seconds=None)


def invalidate_service_cache(prefix: str | None = None) -> dict[str, object]:
    with _global_lock:
        if prefix is None:
            removed = len(_cache)
            _cache.clear()
            delete_persistent_prefix("")
        else:
            keys = [key for key in _cache if key.startswith(prefix)]
            removed = len(keys)
            for key in keys:
                _cache.pop(key, None)
            removed += delete_persistent_prefix(prefix)
    return get_service_cache_status(removed=removed)


def get_service_cache_status(removed: int | None = None) -> dict[str, object]:
    now = time.time()
    with _global_lock:
        ages = [now - entry.created_at for entry in _cache.values()]
        status = {
            "items": len(_cache),
            "keys": sorted(_cache.keys()),
            "hit_count": _stats["hits"],
            "miss_count": _stats["misses"],
            "compute_count": _stats["computes"],
            "avoided_duplicate_computations": _stats["duplicate_computations_avoided"],
            "oldest_item_age": round(max(ages), 2) if ages else None,
            "newest_item_age": round(min(ages), 2) if ages else None,
            "persistent": get_persistent_cache_status(),
        }
        if removed is not None:
            status["removed"] = removed
        return status


def get_key_lock(key: str) -> threading.Lock:
    with _global_lock:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def get_persistent_service_value(key: str, allow_stale: bool):
    result = get_persistent_value(key, allow_stale=allow_stale)
    if result is None:
        return None
    try:
        result.value = deserialize_service_value(key, result.value)
    except Exception as exc:
        # A persisted value from an older schema (or a damaged record) must
        # behave as a cache miss, never make a read endpoint fail.
        logger.warning("Discarding invalid persistent service cache entry %s: %s", key, type(exc).__name__)
        delete_persistent_value(key)
        return None
    return result


def deserialize_service_value(key: str, value: object) -> object:
    model = SERVICE_MODEL_BY_KEY.get(key)
    if model is not None:
        return model.model_validate(value)
    if key.startswith("service-breadth:"):
        return MarketBreadthResponse.model_validate(value)
    if key.startswith("service-sector-breadth:"):
        return TypeAdapter(list[SectorBreadthItem]).validate_python(value)
    if key == "index-snapshots":
        return TypeAdapter(list[IndexSnapshot]).validate_python(value)
    return value


def get_stale_ttl_seconds(key: str) -> int:
    if key in {"market-core-snapshot", "home-dashboard"}:
        return 24 * 60 * 60
    if key.startswith("service-breadth") or key in {
        "sector-etfs",
        "sectors",
        "industry-groups",
        "industry-rotation",
        "leadership",
    }:
        return 7 * 24 * 60 * 60
    return 30 * 60


def get_data_source(value: object) -> str | None:
    if isinstance(value, dict):
        return value.get("overall_mode") or value.get("data_source")
    return getattr(value, "overall_mode", None) or getattr(value, "data_source", None)


def build_cache_metadata(
    status: str,
    refreshing: bool,
    age_seconds: float | None,
    generated_at: float | None = None,
    next_refresh_at: float | None = None,
) -> dict[str, object]:
    return {
        "cache_status": status,
        "cache_age_seconds": round(age_seconds, 2) if age_seconds is not None else None,
        "refreshing": refreshing,
        "generated_at": epoch_to_iso(generated_at),
        "next_refresh_at": epoch_to_iso(next_refresh_at),
    }


def epoch_to_iso(value: float | None) -> str | None:
    if value is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def trigger_background_refresh(key: str, ttl_seconds: int, compute_fn: Callable[[], T]) -> None:
    with _global_lock:
        if key in _refreshing_keys:
            _stats["duplicate_computations_avoided"] += 1
            return
        _refreshing_keys.add(key)

    def refresh() -> None:
        try:
            value = compute_fn()
            set_cached_service_value(key, value, ttl_seconds)
            _stats["computes"] += 1
        except Exception as exc:
            logger.warning("Service cache refresh failed for %s: %s: %s", key, type(exc).__name__, exc)
        finally:
            with _global_lock:
                _refreshing_keys.discard(key)

    try:
        from app.services.background_refresh import submit_background_task

        submitted = submit_background_task(f"service-cache:{key}", refresh)
        if not submitted:
            thread = threading.Thread(target=refresh, daemon=True)
            thread.start()
    except Exception:
        thread = threading.Thread(target=refresh, daemon=True)
        thread.start()

from fastapi import APIRouter, Query

from app.cache.persistent_cache import (
    delete_persistent_prefix,
    get_persistent_cache_status,
    vacuum_expired_entries,
)
from app.providers.cache import clear_provider_cache, get_provider_cache_status
from app.providers.selector import get_intelligence_status, get_provider_status
from app.services.client_activity import get_client_activity_status
from app.services.background_refresh import get_refresh_status, queue_refresh
from app.services.breadth import get_universe_status
from app.services.materialized_market_state import get_materialized_state_status
from app.services.service_cache import (
    get_service_cache_status,
    invalidate_service_cache,
)
from app.services.market_data_repository import get_market_data_repository
from app.services.workload_manager import get_workload_status

router = APIRouter()


@router.get("/system/provider-status")
async def get_system_provider_status() -> dict[str, object]:
    """Return the market data provider scaffold status for Phase 4 readiness."""
    return get_provider_status()


@router.get("/market-data/status")
async def get_market_data_status() -> dict[str, object]:
    """Return provider-neutral market-data diagnostics without exposing secrets."""
    return get_provider_status()


@router.get("/market-data/cache/status")
async def get_market_data_cache_status() -> dict[str, object]:
    """Return Phase 4.2 layered market-data cache diagnostics."""
    return get_market_data_repository().get_cache_status()


@router.post("/market-data/cache/cleanup")
async def cleanup_market_data_cache() -> dict[str, object]:
    """Clear expired/stale-expired market-data cache records."""
    cache = get_market_data_repository().cache
    if hasattr(cache, "cleanup"):
        return cache.cleanup()
    return {"deleted": 0, "supported": False}


@router.post("/market-data/cache/invalidate")
async def invalidate_market_data_cache(
    prefix: str | None = Query(default=None),
    domain: str | None = Query(default=None),
) -> dict[str, object]:
    """Invalidate a safe subset of layered market-data cache records."""
    cache = get_market_data_repository().cache
    deleted = 0
    if domain and hasattr(cache, "clear_domain"):
        deleted = cache.clear_domain(domain)
    elif prefix:
        deleted = cache.invalidate(prefix)
    else:
        deleted = cache.invalidate()
    return {"deleted": deleted, "prefix": prefix, "domain": domain, "status": get_market_data_repository().get_cache_status()}


@router.get("/system/provider-cache")
async def get_system_provider_cache() -> dict[str, object]:
    """Return in-memory provider cache status."""
    return {
        "repository": get_market_data_repository().get_cache_status(),
        "provider_cache": get_provider_cache_status(),
    }


@router.post("/system/provider-cache/clear")
async def clear_system_provider_cache() -> dict[str, object]:
    """Clear the in-memory provider cache."""
    clear_provider_cache()
    get_market_data_repository().cache.invalidate()
    return {
        "repository": get_market_data_repository().get_cache_status(),
        "provider_cache": get_provider_cache_status(),
    }


@router.get("/system/universe-status")
async def get_system_universe_status() -> dict[str, object]:
    """Return compact breadth-universe coverage diagnostics."""
    return get_universe_status()


@router.get("/system/intelligence-status")
async def get_system_intelligence_status() -> dict[str, object]:
    """Return live-aware intelligence provider diagnostics without exposing secrets."""
    return get_intelligence_status()


@router.get("/system/service-cache")
async def get_system_service_cache() -> dict[str, object]:
    """Return service-level cache diagnostics without exposing payloads."""
    return get_service_cache_status()


@router.post("/system/service-cache/clear")
async def clear_system_service_cache(prefix: str | None = Query(default=None)) -> dict[str, object]:
    """Clear all service cache entries or entries matching a prefix."""
    return invalidate_service_cache(prefix)


@router.get("/system/refresh-status")
async def get_system_refresh_status() -> dict[str, object]:
    """Return background refresh and snapshot diagnostics."""
    return {
        **get_refresh_status(),
        "client_activity": get_client_activity_status(),
        "materialized_market_state": get_materialized_state_status(),
    }


@router.post("/system/refresh")
async def trigger_system_refresh(scope: str = Query(default="core")) -> dict[str, object]:
    """Queue a background refresh without waiting for completion."""
    if scope not in {"core", "tier1", "light", "snapshots", "market-structure", "intelligence", "full", "all"}:
        return {"queued": [], "scope": scope, "error": "Unsupported scope"}
    return queue_refresh(scope)


@router.get("/system/persistent-cache")
async def get_system_persistent_cache() -> dict[str, object]:
    """Return persistent cache diagnostics without exposing payloads."""
    vacuum_expired_entries()
    return get_persistent_cache_status()


@router.post("/system/persistent-cache/clear")
async def clear_system_persistent_cache(prefix: str | None = Query(default=None)) -> dict[str, object]:
    """Clear all persistent cache entries or entries matching a prefix."""
    delete_persistent_prefix(prefix or "")
    return get_persistent_cache_status()


@router.get("/system/performance-summary")
async def get_system_performance_summary() -> dict[str, object]:
    """Return compact cache/workload diagnostics for performance triage."""
    service_cache = get_service_cache_status()
    hits = int(service_cache.get("hit_count") or 0)
    misses = int(service_cache.get("miss_count") or 0)
    total = hits + misses
    return {
        "workload": get_workload_status(),
        "service_cache": service_cache,
        "cache_hit_ratio": round((hits / total) * 100, 2) if total else None,
        "materialized_market_state": get_materialized_state_status(),
        "client_activity": get_client_activity_status(),
    }

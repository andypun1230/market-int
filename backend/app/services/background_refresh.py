from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.utils.performance import monotonic_ms
from app.services.workload_manager import background_job, get_workload_status, has_interactive_demand, mark_background_queued

logger = logging.getLogger(__name__)

RefreshFn = Callable[[], Any]

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()
_lock = threading.RLock()
_worker_semaphore: threading.BoundedSemaphore | None = None
_running_jobs: dict[str, dict[str, Any]] = {}
_worker_threads: dict[str, threading.Thread] = {}
_last_completed: dict[str, dict[str, Any]] = {}
_last_errors: dict[str, dict[str, Any]] = {}
_job_tiers: dict[str, str] = {}
_tier_heavy_lock = threading.Lock()

TIER_1_REALTIME = "tier_1_realtime"
TIER_2_DAILY_MARKET_STRUCTURE = "tier_2_daily_market_structure"
TIER_3_INTELLIGENCE = "tier_3_intelligence"
TIER_4_REPORT_AI = "tier_4_report_ai"


def is_background_refresh_enabled() -> bool:
    return os.getenv("BACKGROUND_REFRESH_ENABLED", "true").lower() != "false"


def get_max_workers() -> int:
    try:
        return max(1, int(os.getenv("BACKGROUND_REFRESH_MAX_WORKERS", "3")))
    except ValueError:
        return 3


def start_background_refresh_coordinator() -> None:
    global _scheduler_thread, _worker_semaphore
    if not is_background_refresh_enabled():
        return

    with _lock:
        if _worker_semaphore is None:
            _worker_semaphore = threading.BoundedSemaphore(get_max_workers())
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return
        _stop_event.clear()
        _scheduler_thread = threading.Thread(target=_scheduler_loop, name="market-refresh-scheduler", daemon=True)
        _scheduler_thread.start()
        queue_startup_refresh()


def stop_background_refresh_coordinator() -> None:
    _stop_event.set()
    thread = _scheduler_thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)


def wait_for_background_tasks(timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while True:
        with _lock:
            threads = [thread for thread in _worker_threads.values() if thread.is_alive()]
            running = bool(_running_jobs)
        if not threads and not running:
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        for thread in threads:
            thread.join(timeout=min(0.1, remaining))


def reset_background_refresh_state(timeout_seconds: float = 5.0) -> bool:
    global _scheduler_thread, _worker_semaphore
    stop_background_refresh_coordinator()
    drained = wait_for_background_tasks(timeout_seconds)
    with _lock:
        _running_jobs.clear()
        _worker_threads.clear()
        _job_tiers.clear()
        _worker_semaphore = None
        _scheduler_thread = None
    return drained


def submit_background_task(name: str, fn: RefreshFn, tier: str = TIER_2_DAILY_MARKET_STRUCTURE) -> bool:
    if not is_background_refresh_enabled():
        return False

    with _lock:
        if name in _running_jobs:
            return False
        if _worker_semaphore is None:
            start_background_refresh_coordinator()
        if _worker_semaphore is None:
            return False
        _running_jobs[name] = {"started_at": now_iso(), "status": "queued", "tier": tier}
        _job_tiers[name] = tier
        mark_background_queued(1)
        thread = threading.Thread(
            target=_run_job_with_semaphore,
            args=(name, fn),
            name=f"market-refresh-{name}",
            daemon=True,
        )
        _worker_threads[name] = thread
        thread.start()
        return True


def queue_refresh(scope: str = "core") -> dict[str, Any]:
    queued: list[str] = []
    if scope in {"tier1", "light", "core", "full", "all"}:
        if submit_background_task("refresh:tier1-quotes", refresh_tier1_realtime, TIER_1_REALTIME):
            queued.append("refresh:tier1-quotes")
    if scope in {"snapshots", "full", "all"}:
        if submit_background_task("refresh:market-snapshot", refresh_market_snapshot, TIER_2_DAILY_MARKET_STRUCTURE):
            queued.append("refresh:market-snapshot")
    if scope in {"full", "all"}:
        if submit_background_task("refresh:market-core", refresh_market_core_snapshot, TIER_2_DAILY_MARKET_STRUCTURE):
            queued.append("refresh:market-core")
        if submit_background_task("refresh:home-dashboard", refresh_home_dashboard, TIER_2_DAILY_MARKET_STRUCTURE):
            queued.append("refresh:home-dashboard")
    if scope in {"market-structure", "full", "all"}:
        for name, fn in [
            ("refresh:breadth", refresh_breadth),
            ("refresh:sector-rotation", refresh_sector_rotation),
            ("refresh:themes", refresh_theme_snapshot),
            ("refresh:industry-groups", refresh_industry_groups),
            ("refresh:leadership", refresh_leadership),
        ]:
            if submit_background_task(name, fn, TIER_2_DAILY_MARKET_STRUCTURE):
                queued.append(name)
    if scope in {"intelligence", "full", "all"}:
        if submit_background_task("refresh:institutional-intelligence", refresh_institutional_intelligence, TIER_3_INTELLIGENCE):
            queued.append("refresh:institutional-intelligence")
    return {"queued": queued, "scope": scope}


def get_refresh_status() -> dict[str, Any]:
    from app.services.snapshot_store import get_snapshot_status

    with _lock:
        return {
            "running_jobs": sorted(_running_jobs.keys()),
            "running_job_details": {
                name: {
                    **details,
                    "elapsed_seconds": round(time.time() - iso_to_epoch(details["started_at"]), 2),
                }
                for name, details in sorted(_running_jobs.items())
            },
            "last_completed": dict(_last_completed),
            "last_errors": dict(_last_errors),
            "workload": get_workload_status(),
            **get_snapshot_status(),
        }


def _run_job(name: str, fn: RefreshFn) -> None:
    started = monotonic_ms()
    with _lock:
        if name in _running_jobs:
            _running_jobs[name]["status"] = "running"
    mark_background_queued(-1)
    try:
        with background_job():
            fn()
        duration_ms = monotonic_ms() - started
        with _lock:
            _last_completed[name] = {
                "completed_at": now_iso(),
                "duration_ms": round(duration_ms, 2),
            }
            _last_errors.pop(name, None)
    except Exception as exc:
        with _lock:
            _last_errors[name] = {
                "failed_at": now_iso(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        logger.warning("Background refresh failed for %s: %s: %s", name, type(exc).__name__, exc)
    finally:
        with _lock:
            _running_jobs.pop(name, None)
            _worker_threads.pop(name, None)


def _run_job_with_semaphore(name: str, fn: RefreshFn) -> None:
    semaphore = _worker_semaphore
    if semaphore is None:
        _run_job(name, fn)
        return
    with semaphore:
        tier = _job_tiers.get(name)
        if tier in {TIER_2_DAILY_MARKET_STRUCTURE, TIER_3_INTELLIGENCE}:
            if has_interactive_demand():
                time.sleep(0.25)
            with _tier_heavy_lock:
                _run_job(name, fn)
        else:
            _run_job(name, fn)


def _scheduler_loop() -> None:
    current = time.time()
    next_core = current + get_interval("BACKGROUND_CORE_REFRESH_SECONDS", 60)
    next_structure = current + get_interval("BACKGROUND_MARKET_STRUCTURE_REFRESH_SECONDS", 900)
    next_intelligence = current + get_interval("BACKGROUND_INTELLIGENCE_REFRESH_SECONDS", 300)

    while not _stop_event.wait(1):
        current = time.time()
        if current >= next_core and should_refresh_core():
            queue_refresh("tier1")
            next_core = current + get_interval("BACKGROUND_CORE_REFRESH_SECONDS", 60)
        if current >= next_structure and should_refresh_market_structure():
            queue_refresh("market-structure")
            next_structure = current + get_interval("BACKGROUND_MARKET_STRUCTURE_REFRESH_SECONDS", 900)
        if current >= next_intelligence and should_refresh_intelligence():
            queue_refresh("intelligence")
            next_intelligence = current + get_interval("BACKGROUND_INTELLIGENCE_REFRESH_SECONDS", 300)


def queue_startup_refresh() -> None:
    mode = os.getenv("STARTUP_REFRESH_MODE", "light").lower()
    if mode == "none":
        return
    if mode == "full":
        queue_refresh("full")
        return
    queue_refresh("tier1")


def should_refresh_core() -> bool:
    from app.services.client_activity import any_recently_active

    return any_recently_active(["home", "market"], within_seconds=600)


def should_refresh_market_structure() -> bool:
    from app.services.client_activity import any_recently_active

    return any_recently_active(["market", "sectors"], within_seconds=600)


def should_refresh_intelligence() -> bool:
    from app.services.client_activity import any_recently_active

    return any_recently_active(["institutional"], within_seconds=600)


def refresh_tier1_realtime() -> dict[str, Any]:
    from app.providers.selector import get_market_data_provider
    from app.services.materialized_market_state import update_market_state_component

    provider = get_market_data_provider()
    symbols = ["SPY", "QQQ", "IWM", "DIA", *provider.get_watchlist_symbols()]
    unique_symbols = list(dict.fromkeys(symbols))
    quotes = []
    deadline = time.monotonic() + 4.5
    for symbol in unique_symbols:
        if time.monotonic() >= deadline:
            break
        try:
            quotes.append(provider.get_quote(symbol).model_dump())
        except Exception as exc:
            logger.debug("Tier 1 quote refresh skipped %s: %s", symbol, exc)

    state = update_market_state_component(
        "quote_summary",
        {"items": quotes, "requested_symbols": len(unique_symbols), "returned_symbols": len(quotes)},
        {"overall_mode": get_quote_mode(quotes), "tier": TIER_1_REALTIME},
    )
    return state


def refresh_market_core_snapshot() -> dict[str, Any]:
    from app.services.market_core_snapshot import _build_market_core_snapshot_uncached
    from app.services.service_cache import get_service_ttl, set_cached_service_value
    from app.services.snapshot_store import save_market_core_snapshot

    snapshot = _build_market_core_snapshot_uncached()
    set_cached_service_value(
        "market-core-snapshot",
        snapshot,
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
    )
    save_market_core_snapshot(snapshot)
    return snapshot


def refresh_market_snapshot() -> dict[str, Any]:
    from app.snapshots.service import get_market_snapshot_service

    snapshot = get_market_snapshot_service().build_now()
    return snapshot.model_dump() if snapshot is not None else {"status": "unavailable"}


def refresh_home_dashboard() -> dict[str, Any]:
    from app.services.home_dashboard import _build_home_dashboard_uncached
    from app.services.service_cache import get_service_ttl, set_cached_service_value
    from app.services.snapshot_store import save_home_dashboard

    dashboard = _build_home_dashboard_uncached()
    set_cached_service_value(
        "home-dashboard",
        dashboard,
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
    )
    save_home_dashboard(dashboard)
    return dashboard


def refresh_breadth() -> None:
    from app.services.breadth import calculate_market_breadth, calculate_sector_breadth

    calculate_market_breadth()
    calculate_sector_breadth()


def refresh_sector_rotation() -> None:
    from app.breadth.service import get_breadth_snapshot_service
    from app.sector_snapshots.service import get_sector_snapshot_service
    # Sector publication is ordered after durable breadth publication. Both
    # builders read only persisted bars, so this cannot create request-time I/O.
    get_breadth_snapshot_service().builder.build_and_publish()
    get_sector_snapshot_service().build_now()


def refresh_industry_groups() -> None:
    from app.services.industry_groups import build_industry_groups
    from app.services.industry_rotation import build_industry_rotation_dashboard

    build_industry_groups()
    build_industry_rotation_dashboard()


def refresh_theme_snapshot() -> object:
    """Build only from reviewed durable inputs; never fetch constituents during navigation."""
    from app.theme_snapshots.service import get_theme_snapshot_service

    service = get_theme_snapshot_service()
    status = service.status()
    if not status.get("reviewed_definition_count"):
        return {"status": "skipped", "reason_code": "human_review_required"}
    return service.build_now()


def refresh_leadership() -> None:
    from app.services.leadership import build_leadership_dashboard

    build_leadership_dashboard()


def refresh_institutional_intelligence() -> None:
    from app.services.institutional_intelligence import build_institutional_intelligence_dashboard

    build_institutional_intelligence_dashboard()


def get_interval(env_name: str, default_seconds: int) -> int:
    try:
        return max(5, int(os.getenv(env_name, str(default_seconds))))
    except ValueError:
        return default_seconds


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_to_epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return time.time()


def get_quote_mode(quotes: list[dict[str, Any]]) -> str:
    if not quotes:
        return "stale"
    live_count = sum(1 for quote in quotes if quote.get("is_live"))
    fallback_count = sum(1 for quote in quotes if quote.get("fallback_used"))
    if live_count == len(quotes):
        return "live"
    if live_count or fallback_count:
        return "mixed"
    return "mock"

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.services.breadth import calculate_market_breadth
from app.services.background_refresh import queue_refresh
from app.services.decision_intelligence import calculate_aggressiveness, build_market_playbook, recommend_trading_styles
from app.services.industry_groups import build_industry_groups
from app.services.market_data import INDEX_SYMBOLS, PROVIDER_INDEX_SYMBOLS, get_index_snapshots, safe_get_quote
from app.services.market_health import calculate_market_health
from app.services.sectors import build_market_sectors
from app.services.service_cache import (
    get_cached_service_value,
    get_persistent_service_value,
    get_service_ttl,
    set_l1_service_value,
)
from app.services.snapshot_store import get_last_market_core_snapshot, save_market_core_snapshot


def build_market_core_snapshot() -> dict[str, Any]:
    cached = get_cached_service_value("market-core-snapshot")
    if cached is not None and is_usable_core_snapshot(cached):
        return decorate_snapshot(cached, cache_status="fresh", refreshing=False, bootstrap=False)

    stored = get_last_market_core_snapshot()
    if stored is not None and is_usable_core_snapshot(stored.value):
        ttl = max(1, int(stored.expires_in_seconds)) if stored.fresh else 30
        set_l1_service_value("market-core-snapshot", stored.value, ttl)
        if stored.stale:
            queue_refresh("snapshots")
        return decorate_snapshot(
            stored.value,
            cache_status="stale" if stored.stale else "fresh",
            refreshing=stored.stale,
            bootstrap=False,
            age_seconds=stored.age_seconds,
            generated_at=stored.created_at,
            is_stale=stored.stale,
        )

    queue_refresh("snapshots")
    return build_bootstrap_snapshot()


def _build_market_core_snapshot_uncached() -> dict[str, Any]:
    indexes = get_index_snapshots()
    market_health = calculate_market_health()
    breadth = calculate_market_breadth()
    playbook = build_market_playbook()
    aggressiveness = calculate_aggressiveness()
    trading_styles = recommend_trading_styles()
    sectors = build_market_sectors()
    industry_groups = build_industry_groups()

    top_sector = sectors.leaders[0].model_dump() if sectors.leaders else None
    top_group = industry_groups.items[0].model_dump() if industry_groups.items else None
    modes = {
        item
        for item in [
            (get_field(market_health, "data_quality") or {}).get("overall_mode"),
            get_field(breadth, "overall_mode"),
            get_field(sectors, "overall_mode"),
            get_field(industry_groups, "overall_mode"),
        ]
        if item
    }

    snapshot = {
        "indexes": [to_jsonable(index) for index in indexes],
        "market_health": to_jsonable(market_health),
        "decision_summary": {
            "playbook": playbook.model_dump(),
            "aggressiveness": aggressiveness.model_dump(),
            "preferred_style": trading_styles.preferred_style,
            "main_risk": playbook.main_risk,
        },
        "breadth_summary": {
            "breadth_score": get_field(breadth, "breadth_score"),
            "breadth_status": get_field(breadth, "breadth_status"),
            "percent_above_50ema": get_field(breadth, "percent_above_50ema"),
            "coverage_percent": get_field(breadth, "coverage_percent"),
            "overall_mode": get_field(breadth, "overall_mode"),
            "universe": get_field(breadth, "universe"),
        },
        "top_sector": top_sector,
        "top_industry_group": top_group,
        "as_of": max(
            [
                value
                for value in [
                    *(get_field(index, "as_of") for index in indexes if get_field(index, "as_of")),
                    get_field(breadth, "as_of"),
                    get_field(sectors, "as_of"),
                    get_field(industry_groups, "as_of"),
                ]
                if value
            ],
            default=datetime.now(timezone.utc).isoformat(),
        ),
        "overall_mode": get_overall_mode(modes),
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "fresh",
        "is_stale": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_market_core_snapshot(snapshot)
    return snapshot


def build_bootstrap_snapshot() -> dict[str, Any]:
    indexes = to_jsonable(get_cached_service_value("index-snapshots")) or []
    if not indexes:
        indexes = build_quote_only_index_snapshots()
    market_health = to_jsonable(get_cached_service_value("market-health"))
    decision_dashboard = to_jsonable(get_cached_service_value("decision-dashboard"))
    breadth = to_jsonable(get_cached_service_value("service-breadth:core"))
    sectors = to_jsonable(get_cached_service_value("sectors"))
    industry_groups = to_jsonable(get_cached_service_value("industry-groups"))

    playbook = (decision_dashboard or {}).get("playbook") if isinstance(decision_dashboard, dict) else None
    aggressiveness = (decision_dashboard or {}).get("aggressiveness") if isinstance(decision_dashboard, dict) else None
    trading_styles = (decision_dashboard or {}).get("trading_styles") if isinstance(decision_dashboard, dict) else None

    return {
        "indexes": indexes,
        "market_health": market_health,
        "decision_summary": {
            "playbook": playbook,
            "aggressiveness": aggressiveness,
            "preferred_style": (trading_styles or {}).get("preferred_style") if isinstance(trading_styles, dict) else None,
            "main_risk": (playbook or {}).get("main_risk") if isinstance(playbook, dict) else None,
        },
        "breadth_summary": build_cached_breadth_summary(breadth),
        "top_sector": first_item(sectors, "leaders"),
        "top_industry_group": first_item(industry_groups, "items"),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "overall_mode": "partial",
        "bootstrap": True,
        "refreshing": True,
        "cache_status": "miss",
        "is_stale": True,
    }


def is_usable_core_snapshot(snapshot: object) -> bool:
    value = to_jsonable(snapshot)
    if not isinstance(value, dict):
        return False
    if value.get("market_health") or value.get("top_sector") or value.get("top_industry_group"):
        return True
    indexes = value.get("indexes")
    if isinstance(indexes, list) and len(indexes) > 0:
        return True
    decision_summary = value.get("decision_summary")
    if isinstance(decision_summary, dict) and (
        decision_summary.get("playbook") or decision_summary.get("aggressiveness")
    ):
        return True
    return False


def build_quote_only_index_snapshots() -> list[dict[str, Any]]:
    try:
        from app.providers.selector import get_market_data_provider

        provider = get_market_data_provider()
    except Exception:
        return []

    snapshots: list[dict[str, Any]] = []
    for public_symbol in INDEX_SYMBOLS:
        provider_symbol = PROVIDER_INDEX_SYMBOLS[public_symbol]
        try:
            quote = safe_get_quote(provider, provider_symbol)
        except Exception:
            continue
        snapshots.append(
            {
                "symbol": public_symbol,
                "price": quote.price,
                "change": quote.change,
                "change_percent": quote.change_percent,
                "volume": quote.volume,
                "ema_20": None,
                "ema_50": None,
                "ema_200": None,
                "sma_50": None,
                "rsi_14": None,
                "data_source": f"quote:{quote.source};history:unavailable",
                "is_live": False,
                "is_stale": quote.is_stale,
                "fallback_used": quote.fallback_used,
                "as_of": quote.timestamp,
                "quote_is_live": quote.is_live,
                "history_is_live": False,
                "analysis_is_live": False,
                "history_quality_score": None,
            }
        )
    return snapshots


def get_overall_mode(modes: set[str]) -> str:
    if modes == {"live"}:
        return "live"
    if "live" in modes or "mixed" in modes:
        return "mixed"
    return "mock"


def decorate_snapshot(
    snapshot: object,
    cache_status: str,
    refreshing: bool,
    bootstrap: bool,
    age_seconds: float | None = None,
    generated_at: float | None = None,
    is_stale: bool = False,
) -> dict[str, Any]:
    value = to_jsonable(snapshot) or {}
    if not isinstance(value, dict):
        value = {}
    decorated = deepcopy(value)
    decorated.setdefault("bootstrap", bootstrap)
    decorated["refreshing"] = refreshing
    decorated["cache_status"] = cache_status
    decorated["is_stale"] = is_stale
    if age_seconds is not None:
        decorated["cache_age_seconds"] = round(age_seconds, 2)
    if generated_at is not None:
        decorated["generated_at"] = datetime.fromtimestamp(generated_at, timezone.utc).isoformat()
    return decorated


def build_cached_breadth_summary(breadth: object) -> dict[str, Any] | None:
    if not isinstance(breadth, dict):
        return None
    return {
        "breadth_score": breadth.get("breadth_score"),
        "breadth_status": breadth.get("breadth_status"),
        "percent_above_50ema": breadth.get("percent_above_50ema"),
        "coverage_percent": breadth.get("coverage_percent"),
        "overall_mode": breadth.get("overall_mode"),
        "universe": breadth.get("universe"),
    }


def first_item(value: object, key: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    items = value.get(key)
    if isinstance(items, list) and items:
        first = items[0]
        return first if isinstance(first, dict) else to_jsonable(first)
    return None


def to_jsonable(value: object) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def get_field(value: object, field: str) -> Any:
    if isinstance(value, dict):
        return value.get(field)
    return getattr(value, field, None)

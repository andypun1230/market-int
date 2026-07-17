from typing import Any

from app.services.background_refresh import queue_refresh
from app.services.market_core_snapshot import build_market_core_snapshot, to_jsonable
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.service_cache import (
    get_cached_service_value,
    get_service_ttl,
    set_l1_service_value,
)
from app.services.snapshot_store import get_last_home_dashboard, save_home_dashboard
from app.services.stock_rating import build_stock_ratings
from app.services.watchlist import build_market_watchlist
from app.services.watchlist_summary import build_watchlist_summary as build_compact_watchlist_summary


def build_home_dashboard() -> dict[str, Any]:
    cached = get_cached_service_value("home-dashboard")
    if cached is not None and is_usable_home_dashboard(cached):
        return decorate_home_dashboard(cached, cache_status="fresh", refreshing=False, bootstrap=False)

    stored = get_last_home_dashboard()
    if stored is not None and is_usable_home_dashboard(stored.value):
        ttl = max(1, int(stored.expires_in_seconds)) if stored.fresh else 30
        set_l1_service_value("home-dashboard", stored.value, ttl)
        if stored.stale:
            queue_refresh("snapshots")
        return decorate_home_dashboard(
            stored.value,
            cache_status="stale" if stored.stale else "fresh",
            refreshing=stored.stale,
            bootstrap=False,
            is_stale=stored.stale,
            cache_age_seconds=stored.age_seconds,
        )

    queue_refresh("snapshots")
    return build_home_bootstrap()


def _build_home_dashboard_uncached() -> dict[str, Any]:
    core = build_market_core_snapshot()
    if not is_usable_core(core):
        from app.services.market_core_snapshot import _build_market_core_snapshot_uncached

        core = _build_market_core_snapshot_uncached()
    risk_summary = build_risk_summary()
    watchlist_summary = build_watchlist_summary()
    dashboard = {
        "core": core,
        "risk_summary": risk_summary,
        "watchlist_summary": watchlist_summary,
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "fresh",
        "is_stale": False,
    }
    save_home_dashboard(dashboard)
    return dashboard


def build_home_bootstrap() -> dict[str, Any]:
    core = build_market_core_snapshot()
    return {
        "core": core,
        "risk_summary": build_cached_risk_summary(core),
        "watchlist_summary": build_cached_watchlist_summary(),
        "bootstrap": True,
        "refreshing": True,
        "cache_status": "miss",
        "is_stale": True,
    }


def build_risk_summary() -> dict[str, Any]:
    try:
        risk = build_risk_dashboard_v2()
        return {
            "score": risk.score,
            "status": classify_risk_score(risk.score),
            "top_contributors": [
                item.model_dump() for item in risk.contributors[:3]
            ],
            "summary": risk.summary,
        }
    except Exception as error:
        return {
            "score": None,
            "status": "Unavailable",
            "top_contributors": [],
            "summary": f"Risk summary unavailable: {type(error).__name__}",
        }


def build_watchlist_summary() -> dict[str, Any]:
    try:
        compact = build_compact_watchlist_summary()
        rows = []
        for item in compact.get("items", [])[:3]:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol") or item.get("ticker")
            rows.append(
                {
                    "symbol": symbol,
                    "price": item.get("price"),
                    "change_percent": item.get("change_percent"),
                    "rating": item.get("rating"),
                    "score": item.get("overall_score") or item.get("score"),
                    "main_setup": item.get("pattern_name") or item.get("setup"),
                    "source": item.get("data_source") or item.get("source"),
                    "is_live": item.get("is_live"),
                    "fallback_used": item.get("fallback_used"),
                }
            )
        if rows:
            return {"items": rows}
    except Exception:
        pass

    try:
        watchlist = build_market_watchlist()
        ratings = {item.symbol: item for item in build_stock_ratings().items}
    except Exception:
        return {"items": []}

    rows = []
    for item in watchlist.items[:3]:
        rating = ratings.get(item.ticker)
        rows.append(
            {
                "symbol": item.ticker,
                "price": item.price,
                "change_percent": item.change_percent,
                "rating": rating.rating if rating else None,
                "score": rating.overall_score if rating else None,
                "main_setup": item.setup,
                "source": item.data_source,
                "is_live": item.is_live,
                "fallback_used": item.fallback_used,
            }
        )

    return {"items": rows}


def build_cached_risk_summary(core: dict[str, Any] | None = None) -> dict[str, Any]:
    risk = to_jsonable(get_cached_service_value("risk-dashboard-v2"))
    if not isinstance(risk, dict):
        core = core if isinstance(core, dict) else {}
        market_health = core.get("market_health")
        decision_summary = core.get("decision_summary")
        main_risk = (
            decision_summary.get("main_risk")
            if isinstance(decision_summary, dict)
            else None
        )
        if isinstance(market_health, dict) or main_risk:
            score = market_health.get("overall_score") if isinstance(market_health, dict) else None
            status = market_health.get("status") if isinstance(market_health, dict) else "Updating"
            return {
                "score": score,
                "status": status,
                "top_contributors": [],
                "summary": main_risk or (market_health or {}).get("summary") or "Risk summary is updating.",
            }
        return {
            "score": None,
            "status": "Unavailable",
            "top_contributors": [],
            "summary": "Risk summary is updating.",
        }
    return {
        "score": risk.get("score"),
        "status": classify_risk_score(risk.get("score")),
        "top_contributors": (risk.get("contributors") or [])[:3],
        "summary": risk.get("summary"),
    }


def build_cached_watchlist_summary() -> dict[str, Any]:
    try:
        compact = build_compact_watchlist_summary()
        rows = []
        for item in compact.get("items", [])[:3]:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "symbol": item.get("symbol") or item.get("ticker"),
                    "price": item.get("price"),
                    "change_percent": item.get("change_percent"),
                    "rating": item.get("rating"),
                    "score": item.get("overall_score") or item.get("score"),
                    "main_setup": item.get("pattern_name") or item.get("setup"),
                    "source": item.get("data_source") or item.get("source"),
                    "is_live": item.get("is_live"),
                    "fallback_used": item.get("fallback_used"),
                }
            )
        if rows:
            return {"items": rows}
    except Exception:
        pass

    watchlist = to_jsonable(get_cached_service_value("watchlist"))
    ratings = to_jsonable(get_cached_service_value("stock-ratings"))
    if not isinstance(watchlist, dict):
        return {"items": []}
    rating_items = {
        item.get("symbol"): item
        for item in (ratings or {}).get("items", [])
        if isinstance(item, dict)
    } if isinstance(ratings, dict) else {}
    rows = []
    for item in (watchlist.get("items") or [])[:3]:
        if not isinstance(item, dict):
            continue
        symbol = item.get("ticker")
        rating = rating_items.get(symbol)
        rows.append(
            {
                "symbol": symbol,
                "price": item.get("price"),
                "change_percent": item.get("change_percent"),
                "rating": rating.get("rating") if rating else None,
                "score": rating.get("overall_score") if rating else None,
                "main_setup": item.get("setup"),
                "source": item.get("data_source"),
                "is_live": item.get("is_live"),
                "fallback_used": item.get("fallback_used"),
            }
        )
    return {"items": rows}


def is_usable_home_dashboard(value: object) -> bool:
    dashboard = to_jsonable(value)
    if not isinstance(dashboard, dict):
        return False
    core = dashboard.get("core")
    if is_usable_core(core):
        return True
    risk = dashboard.get("risk_summary")
    if isinstance(risk, dict) and risk.get("score") is not None:
        return True
    watchlist = dashboard.get("watchlist_summary")
    if isinstance(watchlist, dict):
        items = watchlist.get("items")
        if isinstance(items, list) and len(items) > 0:
            return True
    return False


def is_usable_core(value: object) -> bool:
    core = to_jsonable(value)
    if not isinstance(core, dict):
        return False
    if core.get("market_health") or core.get("top_sector") or core.get("top_industry_group"):
        return True
    indexes = core.get("indexes")
    if isinstance(indexes, list) and len(indexes) > 0:
        return True
    decision_summary = core.get("decision_summary")
    return isinstance(decision_summary, dict) and bool(
        decision_summary.get("playbook") or decision_summary.get("aggressiveness")
    )


def decorate_home_dashboard(
    value: object,
    cache_status: str,
    refreshing: bool,
    bootstrap: bool,
    is_stale: bool = False,
    cache_age_seconds: float | None = None,
) -> dict[str, Any]:
    dashboard = to_jsonable(value) or {}
    if not isinstance(dashboard, dict):
        dashboard = {}
    dashboard.setdefault("bootstrap", bootstrap)
    dashboard["refreshing"] = refreshing
    dashboard["cache_status"] = cache_status
    dashboard["is_stale"] = is_stale
    if cache_age_seconds is not None:
        dashboard["cache_age_seconds"] = round(cache_age_seconds, 2)
    return dashboard


def classify_risk_score(score: int | None) -> str:
    if score is None:
        return "Unavailable"
    if score >= 70:
        return "Elevated"
    if score >= 45:
        return "Moderate"
    return "Low"

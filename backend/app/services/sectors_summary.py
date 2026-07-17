from __future__ import annotations

from typing import Any

from app.services.materialized_market_state import get_materialized_market_state
from app.services.service_cache import get_cached_service_value, get_or_compute, get_service_ttl


def build_sectors_summary() -> dict[str, Any]:
    return get_or_compute(
        "sectors-summary",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        _build_sectors_summary_uncached,
    )


def _build_sectors_summary_uncached() -> dict[str, Any]:
    sectors = to_jsonable(get_cached_service_value("sectors")) or {}
    sector_etfs = to_jsonable(get_cached_service_value("sector-etfs")) or {}
    industry_groups = to_jsonable(get_cached_service_value("industry-groups")) or {}
    industry_rotation = to_jsonable(get_cached_service_value("industry-rotation")) or {}
    materialized = get_materialized_market_state()

    top_sectors = (sectors.get("leaders") if isinstance(sectors, dict) else None) or []
    top_etfs = (sector_etfs.get("items") if isinstance(sector_etfs, dict) else None) or []
    top_groups = (industry_groups.get("items") if isinstance(industry_groups, dict) else None) or []

    return {
        "top_sectors": top_sectors,
        "top_sector_etfs": top_etfs[:5],
        "top_industry_groups": top_groups[:5],
        "rotation_summary": (
            sectors.get("summary")
            if isinstance(sectors, dict) and sectors.get("summary")
            else industry_rotation.get("summary") if isinstance(industry_rotation, dict) else None
        ),
        "return_interval_default": "1d",
        "as_of": first_present(
            sectors.get("as_of") if isinstance(sectors, dict) else None,
            sector_etfs.get("as_of") if isinstance(sector_etfs, dict) else None,
            industry_groups.get("as_of") if isinstance(industry_groups, dict) else None,
            materialized.get("generated_at"),
        ),
        "overall_mode": first_present(
            sectors.get("overall_mode") if isinstance(sectors, dict) else None,
            sector_etfs.get("overall_mode") if isinstance(sector_etfs, dict) else None,
            industry_groups.get("overall_mode") if isinstance(industry_groups, dict) else None,
            materialized.get("overall_mode"),
            "stale",
        ),
        "cache_status": "cached_or_bootstrap",
        "refreshing": False,
    }


def first_present(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


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

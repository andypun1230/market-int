from __future__ import annotations
from typing import Any
from app.sector_snapshots.service import get_sector_snapshot_service


def build_sectors_summary() -> dict[str, Any]:
    snapshot = get_sector_snapshot_service().latest()
    if snapshot is None:
        return {"top_sectors": [], "top_sector_etfs": [], "top_industry_groups": [], "rotation_summary": "Sector snapshot is unavailable.", "overall_mode": "unavailable", "snapshot_id": None}
    ordered = sorted(snapshot.sectors, key=lambda row: row["composite_score"] if row["composite_score"] is not None else -1, reverse=True)
    leaders = [{"rank": row.get("rank", index), "name": row["display_name"], "sector_id": row["sector_id"], "etf_symbol": row["etf_symbol"], "status": row["classification"], "composite_score": row.get("composite_score"), "relative_strength_score": round((row.get("component_scores") or {}).get("relative_strength") or 0), "relative_strength_1m": (row.get("relative_strength_metrics") or {}).get("vs_spy_1m"), "percent_above_50ema": (row.get("breadth_metrics") or {}).get("percent_above_ema50"), "eligible_members": row.get("eligible_members"), "total_members": row.get("total_members"), "snapshot_id": snapshot.snapshot_id, "market_date": snapshot.market_date, "universe_version": snapshot.universe_version} for index, row in enumerate(ordered, 1)]
    return {"top_sectors": leaders, "top_sector_etfs": [{"symbol": row["etf_symbol"], "sector": row["display_name"], "return_1m": row["price_metrics"]["return_1m"], "snapshot_id": snapshot.snapshot_id} for row in ordered[:5]], "top_industry_groups": [], "rotation_summary": snapshot.rotation_summary, "return_interval_default": "1m", "as_of": snapshot.market_date, "overall_mode": snapshot.source_state, "snapshot_id": snapshot.snapshot_id, "universe_id": snapshot.universe_id, "universe_version": snapshot.universe_version, "market_date": snapshot.market_date, "coverage": snapshot.coverage, "source_state": snapshot.source_state, "cache_status": "snapshot", "refreshing": False}

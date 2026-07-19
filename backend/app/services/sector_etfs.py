from app.models.market import SectorEtfItem, SectorEtfResponse
from app.providers.models import HistoryData
from app.securities.registry import SECTOR_BY_ID
from app.sector_snapshots.service import get_sector_snapshot_service


def build_sector_etf_dashboard() -> SectorEtfResponse:
    snapshot = get_sector_snapshot_service().latest()
    if snapshot is None:
        return SectorEtfResponse(items=[], summary="Sector snapshot is unavailable.", overall_mode="unavailable", coverage_percent=0.0)
    items = []
    for row in snapshot.sectors:
        price = row["price_metrics"]
        items.append(SectorEtfItem(symbol=row["etf_symbol"], name=f"{row['display_name']} Select Sector SPDR", sector=row["display_name"], price=0.0, change_percent=0.0, return_1d=0.0, return_1w=price["return_1w"] or 0.0, return_mtd=price["return_1m"] or 0.0, return_ytd=price["return_3m"] or 0.0, return_1m=price["return_1m"] or 0.0, return_3m=price["return_3m"], return_6m=None, return_1y=None, relative_strength_score=round(row["component_scores"]["relative_strength"] or 0), volume_trend="Unavailable", status=row["classification"], data_source="polygon-durable", quote_source="durable daily history", history_source="polygon", quote_is_live=False, history_is_live=snapshot.source_state == "live", fallback_used=False, as_of=snapshot.market_date, history_quality_score=100 if row["confidence"] == "high" else 60, ema_20=price["ema20"], ema_50=price["ema50"], trend_status=row["classification"], rotation_score=round(row["composite_score"] or 0)))
    return SectorEtfResponse(items=items, summary=snapshot.rotation_summary, overall_mode=snapshot.source_state, coverage_percent=round(snapshot.coverage["etf_coverage_ratio"] * 100, 2), as_of=snapshot.market_date)


# Compatibility only: the sector snapshot contains all eleven ETF histories.
def get_sector_etfs_for_runtime() -> list[dict[str, str]]:
    snapshot = get_sector_snapshot_service().latest()
    if snapshot:
        return [{"symbol": row["etf_symbol"], "sector": row["display_name"]} for row in snapshot.sectors]
    # Retained for old callers/tests only; the public sector API never uses it.
    return [{"symbol": value["etf_symbol"], "sector": value["display_name"]} for value in list(SECTOR_BY_ID.values())[:4]]


def safe_get_history(provider: object, symbol: str, days: int) -> HistoryData:
    """Legacy helper retained for import compatibility; no mock fallback."""
    try:
        return provider.get_history(symbol, resolution="D", days=days)
    except Exception:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        return HistoryData(symbol=symbol, candles=[], timeframe="D", source="unavailable", is_live=False, is_stale=False, fallback_used=False, as_of=now, requested_days=days, returned_candles=0, provider="unavailable", source_state="unavailable", fetched_at=now)

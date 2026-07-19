from app.models.market import SectorLeader, SectorsResponse
from app.sector_snapshots.service import get_sector_snapshot_service


def build_market_sectors() -> SectorsResponse:
    snapshot = get_sector_snapshot_service().latest()
    if snapshot is None:
        return SectorsResponse(leaders=[], summary="Sector snapshot is unavailable.", overall_mode="unavailable", coverage_percent=0.0, source_state="unavailable")
    rows = sorted(snapshot.sectors, key=lambda row: row["composite_score"] if row["composite_score"] is not None else -1, reverse=True)
    leaders = []
    for rank, row in enumerate(rows, 1):
        price = row["price_metrics"]; breadth = row["breadth_metrics"]
        leaders.append(SectorLeader(rank=rank, name=row["display_name"], status=row["classification"], change=f"{(price['return_1w'] or 0):+.1f}%", return_1d=0.0, return_1w=price["return_1w"] or 0.0, return_mtd=price["return_1m"] or 0.0, return_ytd=price["return_3m"] or 0.0, daily_change_percent=0.0, weekly_change_percent=price["return_1w"] or 0.0, monthly_change_percent=price["return_1m"] or 0.0, relative_strength_score=round(row["component_scores"]["relative_strength"] or 0), percent_above_50ema=breadth["percent_above_ema50"] or 0.0, advancing_stocks=breadth["advancing"], declining_stocks=breadth["declining"], data_source="polygon-durable", overall_mode=snapshot.source_state, coverage_percent=round(row["coverage_ratio"] * 100, 2), successful_symbols=row["eligible_members"], fallback_used=False, as_of=snapshot.market_date, history_quality_score=100 if row["confidence"] == "high" else 60))
    return SectorsResponse(leaders=leaders, summary=snapshot.rotation_summary, overall_mode=snapshot.source_state, coverage_percent=round(snapshot.coverage["constituent_coverage_ratio"] * 100, 2), as_of=snapshot.market_date, snapshot_id=snapshot.snapshot_id, universe_id=snapshot.universe_id, universe_version=snapshot.universe_version, market_date=snapshot.market_date, source_state=snapshot.source_state)


def calculate_sector_rotation() -> list[SectorLeader]:
    """Legacy consumers now receive the same immutable snapshot leaders."""
    return build_market_sectors().leaders

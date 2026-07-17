from app.models.market import IndustryRotationResponse, IndustryRotationSector
from app.services.industry_groups import build_industry_groups
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl


def build_industry_rotation_dashboard() -> IndustryRotationResponse:
    return get_or_compute(
        "industry-rotation",
        get_service_ttl("SERVICE_CACHE_INDUSTRY_GROUPS_TTL_SECONDS", 900),
        _build_industry_rotation_dashboard_uncached,
    )


def _build_industry_rotation_dashboard_uncached() -> IndustryRotationResponse:
    sectors = build_market_sectors().leaders
    group_response = build_industry_groups()
    groups = group_response.items
    rows: list[IndustryRotationSector] = []

    for sector in sectors:
        sector_groups = [group for group in groups if group.parent_sector == sector.name]
        strongest = sorted(sector_groups, key=lambda group: group.score, reverse=True)[:3]
        weakest = sorted(sector_groups, key=lambda group: group.score)[:2]
        improving = [
            group for group in sector_groups
            if group.return_1w > 2 or group.status in ("Leading", "Strong")
        ][:3]
        deteriorating = [
            group for group in sector_groups
            if group.return_1d < 0 or group.return_1w < 1
        ][:2]

        rows.append(
            IndustryRotationSector(
                sector=sector.name,
                strongest_industry_groups=[group.name for group in strongest],
                weakest_industry_groups=[group.name for group in weakest],
                improving=[group.name for group in improving],
                deteriorating=[group.name for group in deteriorating],
            )
        )

    technology = next((row for row in rows if row.sector == "Technology"), None)
    leader_text = (
        ", ".join(technology.strongest_industry_groups[:3])
        if technology and technology.strongest_industry_groups
        else "No clear group leadership"
    )

    return IndustryRotationResponse(
        sectors=rows,
        summary=f"Technology has the clearest industry group leadership, led by {leader_text}.",
        overall_mode=group_response.overall_mode,
        coverage_percent=group_response.coverage_percent,
        as_of=group_response.as_of,
    )

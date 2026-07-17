from app.models.market import SectorLeader, SectorsResponse
from app.services.breadth import calculate_sector_breadth
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.service_cache import get_or_compute, get_service_ttl


def format_change(change_percent: float) -> str:
    prefix = "+" if change_percent >= 0 else ""
    return f"{prefix}{change_percent:.1f}%"


def calculate_sector_rotation() -> list[SectorLeader]:
    breadth_by_sector = {item.sector: item for item in calculate_sector_breadth()}
    etf_dashboard = build_sector_etf_dashboard()
    rows: list[dict] = []

    for etf in etf_dashboard.items:
        breadth = breadth_by_sector.get(etf.sector)
        percent_above_50ema = breadth.percent_above_50ema if breadth else 0.0
        advancing = breadth.advancing_stocks if breadth else 0
        declining = breadth.declining_stocks if breadth else 0
        score = round(
            ((etf.rotation_score or etf.relative_strength_score) * 0.75)
            + (percent_above_50ema * 0.25),
            2,
        )
        rows.append(
            {
                "name": etf.sector,
                "status": etf.status,
                "change": format_change(etf.return_1d),
                "return_1d": etf.return_1d,
                "return_1w": etf.return_1w,
                "return_mtd": etf.return_mtd,
                "return_ytd": etf.return_ytd,
                "daily_change_percent": etf.return_1d,
                "weekly_change_percent": etf.return_1w,
                "monthly_change_percent": etf.return_mtd,
                "relative_strength_score": etf.relative_strength_score,
                "percent_above_50ema": percent_above_50ema,
                "advancing_stocks": advancing,
                "declining_stocks": declining,
                "score": score,
                "data_source": etf.data_source,
                "overall_mode": get_overall_mode(etf.history_is_live, etf.fallback_used),
                "coverage_percent": breadth.coverage_percent if breadth else etf_dashboard.coverage_percent,
                "successful_symbols": breadth.successful_symbols if breadth else None,
                "fallback_used": etf.fallback_used,
                "as_of": etf.as_of,
                "history_quality_score": etf.history_quality_score,
            }
        )

    ranked_rows = sorted(
        rows,
        key=lambda row: (
            row["score"],
            row["relative_strength_score"],
            row["weekly_change_percent"],
        ),
        reverse=True,
    )

    return [
        SectorLeader(rank=index + 1, **row)
        for index, row in enumerate(ranked_rows)
    ]


def build_market_sectors() -> SectorsResponse:
    return get_or_compute(
        "sectors",
        get_service_ttl("SERVICE_CACHE_SECTORS_TTL_SECONDS", 900),
        _build_market_sectors_uncached,
    )


def _build_market_sectors_uncached() -> SectorsResponse:
    leaders = calculate_sector_rotation()
    top_names = ", ".join(item.name for item in leaders[:2]) if leaders else "N/A"
    modes = {item.overall_mode for item in leaders if item.overall_mode}
    overall_mode = "live" if modes == {"live"} else "mixed" if "live" in modes or "mixed" in modes else "mock"
    coverage_values = [
        item.coverage_percent for item in leaders if item.coverage_percent is not None
    ]

    return SectorsResponse(
        leaders=leaders,
        summary=(
            f"{top_names} are leading broad sector rotation based on sector ETF "
            "history, relative strength, and core-universe breadth."
        ),
        overall_mode=overall_mode,
        coverage_percent=(
            round(sum(coverage_values) / len(coverage_values), 2)
            if coverage_values else None
        ),
        as_of=max((item.as_of for item in leaders if item.as_of), default=None),
    )


def get_overall_mode(history_is_live: bool | None, fallback_used: bool | None) -> str:
    if history_is_live and not fallback_used:
        return "live"
    if history_is_live or fallback_used:
        return "mixed"
    return "mock"

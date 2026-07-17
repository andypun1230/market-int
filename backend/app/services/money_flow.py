from statistics import mean

from app.models.market import MoneyFlowItem, MoneyFlowResponse
from app.services.block_trade_analysis import build_institutional_large_print_dashboard
from app.services.industry_groups import build_industry_groups
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.service_cache import get_or_compute, get_service_ttl


def build_money_flow_dashboard() -> MoneyFlowResponse:
    return get_or_compute(
        "money-flow",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_money_flow_dashboard_uncached,
    )


def _build_money_flow_dashboard_uncached() -> MoneyFlowResponse:
    sector_etfs = build_sector_etf_dashboard()
    industry_groups = build_industry_groups()
    large_prints = build_institutional_large_print_dashboard()

    sector_items = [
        MoneyFlowItem(
            area=item.sector,
            score=calculate_flow_score(item.return_1w, item.relative_strength_score, item.volume_trend),
            status=item.status,
            flow=classify_flow(calculate_flow_score(item.return_1w, item.relative_strength_score, item.volume_trend)),
            change_1d=item.return_1d,
            change_1w=item.return_1w,
            summary=f"Estimated sector flow uses {item.symbol} return, relative strength, and volume trend.",
            metadata={
                "source": item.data_source,
                "overall_mode": item.overall_mode if hasattr(item, "overall_mode") else None,
                "fallback_used": item.fallback_used,
            },
        )
        for item in sector_etfs.items[:6]
    ]
    group_items = [
        MoneyFlowItem(
            area=item.name,
            score=calculate_flow_score(item.return_1w, item.relative_strength_score, "Accumulation" if (item.volume_participation or 0) >= 60 else "Neutral"),
            status=item.status,
            flow=classify_flow(calculate_flow_score(item.return_1w, item.relative_strength_score, "Accumulation" if (item.volume_participation or 0) >= 60 else "Neutral")),
            change_1d=item.return_1d,
            change_1w=item.return_1w,
            summary=f"Estimated industry-group flow uses equal-weight basket return and participation.",
            metadata={
                "source": item.data_source,
                "overall_mode": item.overall_mode,
                "coverage_percent": item.coverage_percent,
            },
        )
        for item in industry_groups.items[:5]
    ]
    items = sorted(sector_items + group_items, key=lambda item: item.score, reverse=True)
    score = round(mean(item.score for item in items[:6])) if items else 55

    return MoneyFlowResponse(
        score=score,
        status=classify_flow(score),
        items=items,
        summary=(
            f"Estimated money flow favors {items[0].area if items else 'N/A'}; "
            "large-print candidates are supporting context only."
        ),
        methodology="Estimated money flow = return, relative volume/participation, relative strength, and cautious large-print context.",
        inflow_leaders=[item.area for item in items if item.score >= 70][:5],
        outflow_leaders=[item.area for item in sorted(items, key=lambda item: item.score) if item.score < 50][:5],
        metadata={
            "overall_mode": combine_modes(sector_etfs.overall_mode, industry_groups.overall_mode, large_prints["metadata"].get("overall_mode")),
            "large_print_candidates": len(large_prints["largest_block_candidates"]),
            "fallback_used": large_prints["metadata"].get("fallback_used", False),
            "limitations": [
                "Estimated money flow is a normalized proxy, not exact capital inflow.",
                "Large-print activity is not confirmed institutional buying or selling.",
            ],
        },
    )


def calculate_flow_score(return_1w: float, relative_strength: int, volume_trend: str) -> int:
    score = 50 + (return_1w * 3) + ((relative_strength - 50) * 0.45)
    if volume_trend == "Accumulation":
        score += 10
    elif volume_trend == "Distribution":
        score -= 10
    return max(0, min(100, round(score)))


def classify_flow(score: int) -> str:
    if score >= 80:
        return "Strong Inflow"
    if score >= 65:
        return "Moderate Inflow"
    if score >= 45:
        return "Neutral"
    if score >= 30:
        return "Moderate Outflow"
    return "Strong Outflow"


def combine_modes(*modes: str | None) -> str:
    clean = {mode for mode in modes if mode}
    if clean == {"live"}:
        return "live"
    if "live" in clean or "mixed" in clean:
        return "mixed"
    return "mock"

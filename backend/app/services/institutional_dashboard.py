from app.models.market import InstitutionalDashboardResponse
from app.services.block_trade_analysis import (
    analyze_block_trade_candidates,
    build_institutional_large_print_dashboard,
)
from app.services.institutional_activity import calculate_institutional_bias
from app.services.service_cache import get_or_compute, get_service_ttl


def build_institutional_dashboard() -> InstitutionalDashboardResponse:
    return get_or_compute(
        "institutional-dashboard",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_institutional_dashboard_uncached,
    )


def _build_institutional_dashboard_uncached() -> InstitutionalDashboardResponse:
    bias = calculate_institutional_bias()
    large_prints = build_institutional_large_print_dashboard()
    score = get_bias_score(bias.bias)
    if large_prints["largest_block_candidates"]:
        score = min(100, score + 4)

    if bias.accumulation_count > bias.distribution_count:
        accumulation_distribution = "Accumulation leading distribution"
    elif bias.distribution_count > bias.accumulation_count:
        accumulation_distribution = "Distribution leading accumulation"
    else:
        accumulation_distribution = "Balanced accumulation and distribution"

    return InstitutionalDashboardResponse(
        score=score,
        status=bias.bias,
        accumulation_distribution=accumulation_distribution,
        block_trade_bias="Large-print activity is present but buyer/seller identity is not inferred",
        dark_pool_bias="Not assessed without a licensed classified dataset",
        program_trading="Orderly two-way activity",
        signals=[
            f"Accumulation days: {bias.accumulation_count}",
            f"Distribution days: {bias.distribution_count}",
            f"Follow-through day: {'Triggered' if bias.follow_through_day.triggered else 'Not triggered'}",
            f"Block-trade candidates: {len(large_prints['largest_block_candidates'])}",
        ],
        risks=[
            "Distribution would become more important if it clusters across SPY and QQQ.",
            "Stall or churning days can warn of institutional hesitation.",
            "Large-print activity is not proof of institutional buying or selling.",
        ],
        summary=f"{bias.summary} Large-print activity is treated as block-trade candidates only.",
        block_trade_candidates=large_prints["largest_block_candidates"],
        block_notional_by_symbol=large_prints["block_notional_by_symbol"],
        block_notional_by_sector=large_prints["block_notional_by_sector"],
        repeated_large_print_symbols=large_prints["repeated_large_print_symbols"],
        confidence=large_prints["confidence"],
        limitations=large_prints["limitations"],
        metadata=large_prints["metadata"],
    )


def build_symbol_institutional_dashboard(symbol: str) -> dict:
    return analyze_block_trade_candidates(symbol)


def get_bias_score(status: str) -> int:
    scores = {
        "Bullish": 88,
        "Neutral": 62,
        "Cautious": 50,
        "Bearish": 25,
    }
    return scores.get(status, 55)

from app.models.market import RelativeStrengthItem, RelativeStrengthResponse
from app.services.candle_data import build_history_metadata, get_symbol_history
from app.services.service_cache import get_or_compute, get_service_ttl

WATCHLIST_SYMBOLS = ["MU", "NVDA", "ARM", "SNDK"]

SYMBOL_SECTOR = {
    "AAPL": "Technology",
    "AMD": "Semiconductors",
    "DIA": "Industrials",
    "DJI": "Industrials",
    "IWM": "Small Caps",
    "MSFT": "Technology",
    "MU": "Semiconductors",
    "NVDA": "Semiconductors",
    "QQQ": "Technology",
    "SOXX": "Semiconductors",
    "SPY": "Market",
    "ARM": "Semiconductors",
    "SNDK": "Technology",
    "TSLA": "Consumer Discretionary",
    "XLK": "Technology",
}

SECTOR_BENCHMARK = {
    "Consumer Discretionary": "XLY",
    "Industrials": "XLI",
    "Market": "SPY",
    "Semiconductors": "SOXX",
    "Software": "IGV",
    "Small Caps": "IWM",
    "Technology": "XLK",
}

MOCK_HISTORY_CONFIG = {
    "SPY": {"start": 600.0, "return_60d": 6.0, "wave": 0.25},
    "QQQ": {"start": 520.0, "return_60d": 8.0, "wave": 0.35},
    "SOXX": {"start": 245.0, "return_60d": 14.0, "wave": 0.5},
    "IGV": {"start": 94.0, "return_60d": 10.0, "wave": 0.3},
    "XLK": {"start": 232.0, "return_60d": 9.0, "wave": 0.28},
    "MU": {"start": 102.0, "return_60d": 38.0, "wave": 0.8},
    "NVDA": {"start": 132.0, "return_60d": 32.0, "wave": 0.75},
    "ARM": {"start": 142.0, "return_60d": 18.0, "wave": 0.5},
    "SNDK": {"start": 61.0, "return_60d": 8.0, "wave": 0.45},
}


def generate_mock_price_history(symbol: str, days: int = 60) -> list[float]:
    normalized_symbol = symbol.upper()
    config = MOCK_HISTORY_CONFIG[normalized_symbol]
    closes: list[float] = []

    for day in range(days):
        progress = day / (days - 1)
        trend = config["start"] * (1 + (config["return_60d"] / 100) * progress)
        wave = ((day % 7) - 3) * config["wave"] * (0.3 + progress * 0.3)
        closes.append(round(trend + wave, 2))

    return closes


MOCK_PRICE_HISTORY = {
    symbol: generate_mock_price_history(symbol)
    for symbol in MOCK_HISTORY_CONFIG
}


def get_mock_closes(symbol: str) -> list[float]:
    return MOCK_PRICE_HISTORY[symbol.upper()]


def get_provider_closes(symbol: str, days: int = 240) -> tuple[list[float], dict]:
    history, validation = get_symbol_history(symbol.upper(), days=days, minimum_candles=40)
    metadata = build_history_metadata(history, validation)
    closes = [candle.close for candle in history.candles]
    return closes, metadata


def try_get_provider_closes(symbol: str, days: int = 240) -> tuple[list[float], dict]:
    try:
        return get_provider_closes(symbol, days)
    except Exception as exc:
        return [], unavailable_history_metadata(symbol, exc)


def unavailable_history_metadata(symbol: str, error: Exception) -> dict:
    category = getattr(error, "category", "unavailable")
    return {
        "data_source": "unavailable",
        "history_source": "unavailable",
        "provider": None,
        "requested_provider": None,
        "source_state": "unavailable",
        "analysis_is_live": False,
        "history_is_live": False,
        "history_is_stale": False,
        "fallback_used": False,
        "fallback_reason": f"history unavailable ({category})",
        "cache_hit": False,
        "cache_age_seconds": None,
        "as_of": None,
        "history_quality_score": 0,
        "history_warnings": [],
        "history_errors": [f"{symbol.upper()} history unavailable ({category})"],
    }


def get_relative_strength_history(symbol: str, benchmark: str) -> list[float]:
    stock_closes, _ = get_provider_closes(symbol, 60)
    benchmark_closes, _ = get_provider_closes(benchmark, 60)

    return [
        round(stock_close / benchmark_close, 4)
        for stock_close, benchmark_close in zip(stock_closes, benchmark_closes)
    ]


def calculate_return(closes: list[float], lookback: int) -> float:
    if lookback <= 0 or len(closes) <= lookback:
        return 0.0

    start = closes[-lookback - 1]
    end = closes[-1]

    if start == 0:
        return 0.0

    return round(((end - start) / start) * 100, 2)


def score_relative_outperformance(stock_return: float, benchmark_return: float) -> int:
    outperformance = stock_return - benchmark_return
    score = 50 + outperformance * 5
    return round(max(0, min(100, score)))


def get_status(overall_rs_score: int) -> str:
    if overall_rs_score >= 85:
        return "Leading"
    if overall_rs_score >= 70:
        return "Strong"
    if overall_rs_score >= 50:
        return "Neutral"
    return "Weak"


def calculate_rs_score(symbol: str) -> RelativeStrengthItem:
    normalized_symbol = symbol.upper()
    sector = SYMBOL_SECTOR.get(normalized_symbol, "Market")
    sector_benchmark = SECTOR_BENCHMARK.get(sector, "SPY")
    stock_closes, stock_metadata = get_provider_closes(normalized_symbol, 240)
    spy_closes, spy_metadata = try_get_provider_closes("SPY", 240)
    qqq_closes, qqq_metadata = try_get_provider_closes("QQQ", 240)
    sector_closes, sector_metadata = try_get_provider_closes(sector_benchmark, 240)
    return_5d = calculate_return(stock_closes, 5)
    return_20d = calculate_return(stock_closes, 20)
    return_60d = calculate_return(stock_closes, 59)
    benchmark_return_20d = calculate_return(spy_closes, 20)
    qqq_return_20d = calculate_return(qqq_closes, 20)
    sector_return_20d = calculate_return(sector_closes, 20)
    rs_vs_spy = score_comparison(return_20d, benchmark_return_20d, spy_closes)
    rs_vs_qqq = score_comparison(return_20d, qqq_return_20d, qqq_closes)
    rs_vs_sector = score_comparison(return_20d, sector_return_20d, sector_closes)
    overall_rs_score = weighted_available_score(
        [
            (rs_vs_spy, 0.4, spy_closes),
            (rs_vs_qqq, 0.3, qqq_closes),
            (rs_vs_sector, 0.3, sector_closes),
        ]
    )
    all_metadata = [stock_metadata, spy_metadata, qqq_metadata, sector_metadata]
    fallback_used = any(item.get("fallback_used") for item in all_metadata)
    analysis_is_live = bool(stock_metadata.get("analysis_is_live")) and any(
        item.get("analysis_is_live") for item in [spy_metadata, qqq_metadata, sector_metadata]
    )
    unavailable_benchmarks = [
        label
        for label, closes in [("SPY", spy_closes), ("QQQ", qqq_closes), (sector_benchmark, sector_closes)]
        if not closes
    ]
    comparisons_requested = ["SPY", "QQQ", sector_benchmark]
    comparisons_available = [
        label
        for label, closes in [("SPY", spy_closes), ("QQQ", qqq_closes), (sector_benchmark, sector_closes)]
        if closes
    ]
    coverage_ratio = round(len(comparisons_available) / len(comparisons_requested), 2) if comparisons_requested else 0.0
    degraded = bool(unavailable_benchmarks)

    return RelativeStrengthItem(
        symbol=normalized_symbol,
        sector=sector,
        rs_vs_spy=rs_vs_spy,
        rs_vs_qqq=rs_vs_qqq,
        rs_vs_sector=rs_vs_sector,
        return_5d=return_5d,
        return_20d=return_20d,
        return_60d=return_60d,
        benchmark_return_20d=benchmark_return_20d,
        sector_return_20d=sector_return_20d,
        overall_rs_score=overall_rs_score,
        rank=0,
        status=get_status(overall_rs_score),
        explanation=(
            f"{normalized_symbol} is {get_status(overall_rs_score).lower()} versus SPY, "
            f"QQQ, and its {sector.lower()} benchmark over the last 20 and 60 sessions."
            if not unavailable_benchmarks
            else (
                f"{normalized_symbol} relative strength uses available market comparisons; "
                f"missing benchmark history: {', '.join(unavailable_benchmarks)}."
            )
        ),
        data_source=build_source_label(all_metadata),
        analysis_is_live=analysis_is_live,
        fallback_used=fallback_used,
        as_of=max(item.get("as_of") or "" for item in all_metadata),
        history_quality_score=min(
            item.get("history_quality_score") or 0
            for item in all_metadata
        ),
        comparisons_requested=comparisons_requested,
        comparisons_available=comparisons_available,
        comparisons_missing=unavailable_benchmarks,
        coverage_ratio=coverage_ratio,
        degraded=degraded,
        degradation_reason=(
            f"Missing benchmark history: {', '.join(unavailable_benchmarks)}"
            if unavailable_benchmarks
            else None
        ),
        confidence_state=(
            "full" if coverage_ratio == 1
            else "partial" if coverage_ratio >= 0.5
            else "limited"
        ),
    )


def score_comparison(stock_return: float, benchmark_return: float, benchmark_closes: list[float]) -> int:
    if not benchmark_closes:
        return 50
    return score_relative_outperformance(stock_return, benchmark_return)


def weighted_available_score(scores: list[tuple[int, float, list[float]]]) -> int:
    available = [(score, weight) for score, weight, closes in scores if closes]
    if not available:
        return 50
    total_weight = sum(weight for _, weight in available)
    return round(sum(score * weight for score, weight in available) / total_weight)


def rank_relative_strength() -> list[RelativeStrengthItem]:
    ranked_items = sorted(
        [calculate_rs_score(symbol) for symbol in WATCHLIST_SYMBOLS],
        key=lambda item: (
            item.overall_rs_score,
            item.return_60d,
            item.return_20d,
        ),
        reverse=True,
    )

    for index, item in enumerate(ranked_items):
        item.rank = index + 1

    return ranked_items


def build_source_label(metadata_items: list[dict]) -> str:
    sources = sorted({item.get("data_source", "mock") for item in metadata_items})
    return "+".join(sources)


def build_relative_strength() -> RelativeStrengthResponse:
    return get_or_compute(
        "relative-strength",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        _build_relative_strength_uncached,
    )


def _build_relative_strength_uncached() -> RelativeStrengthResponse:
    items = rank_relative_strength()
    leaders = [item.symbol for item in items[:2]]

    return RelativeStrengthResponse(
        items=items,
        summary=(
            f"{leaders[0]} and {leaders[1]} show the strongest relative strength "
            "versus the market and sector benchmarks."
        ),
    )

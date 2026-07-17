from app.models.market import RelativeStrengthItem, RelativeStrengthResponse
from app.services.candle_data import build_history_metadata, get_symbol_history
from app.services.service_cache import get_or_compute, get_service_ttl

WATCHLIST_SYMBOLS = ["MU", "NVDA", "ARM", "SNDK"]

SYMBOL_SECTOR = {
    "MU": "Semiconductors",
    "NVDA": "Semiconductors",
    "ARM": "Semiconductors",
    "SNDK": "Technology",
}

SECTOR_BENCHMARK = {
    "Semiconductors": "SOXX",
    "Software": "IGV",
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
    sector = SYMBOL_SECTOR[normalized_symbol]
    sector_benchmark = SECTOR_BENCHMARK[sector]
    stock_closes, stock_metadata = get_provider_closes(normalized_symbol, 240)
    spy_closes, spy_metadata = get_provider_closes("SPY", 240)
    qqq_closes, qqq_metadata = get_provider_closes("QQQ", 240)
    sector_closes, sector_metadata = get_provider_closes(sector_benchmark, 240)
    return_5d = calculate_return(stock_closes, 5)
    return_20d = calculate_return(stock_closes, 20)
    return_60d = calculate_return(stock_closes, 59)
    benchmark_return_20d = calculate_return(spy_closes, 20)
    qqq_return_20d = calculate_return(qqq_closes, 20)
    sector_return_20d = calculate_return(sector_closes, 20)
    rs_vs_spy = score_relative_outperformance(return_20d, benchmark_return_20d)
    rs_vs_qqq = score_relative_outperformance(return_20d, qqq_return_20d)
    rs_vs_sector = score_relative_outperformance(return_20d, sector_return_20d)
    overall_rs_score = round((rs_vs_spy * 0.4) + (rs_vs_qqq * 0.3) + (rs_vs_sector * 0.3))
    all_metadata = [stock_metadata, spy_metadata, qqq_metadata, sector_metadata]
    fallback_used = any(item.get("fallback_used") for item in all_metadata)
    analysis_is_live = all(item.get("analysis_is_live") for item in all_metadata)

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
        ),
        data_source=build_source_label(all_metadata),
        analysis_is_live=analysis_is_live,
        fallback_used=fallback_used,
        as_of=max(item.get("as_of") or "" for item in all_metadata),
        history_quality_score=min(
            item.get("history_quality_score") or 0
            for item in all_metadata
        ),
    )


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

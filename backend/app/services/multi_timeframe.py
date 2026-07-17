from app.models.market import MultiTimeframeItem, MultiTimeframeResponse, TimeframeAnalysis
from app.services.pattern_detection import WATCHLIST_SYMBOLS

TIMEFRAME_ORDER = ["Weekly", "Daily", "4H", "1H"]

MOCK_TIMEFRAME_DATA: dict[str, dict[str, dict[str, object]]] = {
    "MU": {
        "Weekly": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Higher highs / higher lows",
            "score": 88,
        },
        "Daily": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Base breakout attempt",
            "score": 86,
        },
        "4H": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Higher lows into resistance",
            "score": 84,
        },
        "1H": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Tight consolidation near highs",
            "score": 82,
        },
    },
    "NVDA": {
        "Weekly": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Strong uptrend",
            "score": 90,
        },
        "Daily": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Bull flag near highs",
            "score": 84,
        },
        "4H": {
            "trend": "Mixed",
            "price_vs_ema20": "Near",
            "price_vs_ema50": "Above",
            "momentum": "Neutral",
            "structure": "Controlled pullback",
            "score": 68,
        },
        "1H": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Near",
            "momentum": "Positive",
            "structure": "Breakout watch",
            "score": 74,
        },
    },
    "ARM": {
        "Weekly": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Prior uptrend intact",
            "score": 78,
        },
        "Daily": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Neutral",
            "structure": "Tight sideways range",
            "score": 72,
        },
        "4H": {
            "trend": "Neutral",
            "price_vs_ema20": "Near",
            "price_vs_ema50": "Above",
            "momentum": "Neutral",
            "structure": "Compression",
            "score": 62,
        },
        "1H": {
            "trend": "Neutral",
            "price_vs_ema20": "Near",
            "price_vs_ema50": "Near",
            "momentum": "Neutral",
            "structure": "Range-bound",
            "score": 58,
        },
    },
    "SNDK": {
        "Weekly": {
            "trend": "Mixed",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Near",
            "momentum": "Neutral",
            "structure": "Recovering trend",
            "score": 58,
        },
        "Daily": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Bullish reversal",
            "score": 68,
        },
        "4H": {
            "trend": "Bullish",
            "price_vs_ema20": "Above",
            "price_vs_ema50": "Above",
            "momentum": "Positive",
            "structure": "Follow-through move",
            "score": 70,
        },
        "1H": {
            "trend": "Mixed",
            "price_vs_ema20": "Near",
            "price_vs_ema50": "Above",
            "momentum": "Neutral",
            "structure": "Volatile pullback",
            "score": 54,
        },
    },
}


def analyze_timeframe(symbol: str, timeframe: str) -> TimeframeAnalysis:
    normalized_symbol = symbol.upper()
    normalized_timeframe = timeframe.upper()
    matched_timeframe = next(
        (item for item in TIMEFRAME_ORDER if item.upper() == normalized_timeframe),
        timeframe,
    )
    symbol_data = MOCK_TIMEFRAME_DATA.get(normalized_symbol, {})
    timeframe_data = symbol_data.get(matched_timeframe)

    if timeframe_data is None:
        return TimeframeAnalysis(
            timeframe=matched_timeframe,
            trend="Unknown",
            price_vs_ema20="N/A",
            price_vs_ema50="N/A",
            momentum="N/A",
            structure="No deterministic timeframe data available",
            score=0,
        )

    return TimeframeAnalysis(
        timeframe=matched_timeframe,
        trend=str(timeframe_data["trend"]),
        price_vs_ema20=str(timeframe_data["price_vs_ema20"]),
        price_vs_ema50=str(timeframe_data["price_vs_ema50"]),
        momentum=str(timeframe_data["momentum"]),
        structure=str(timeframe_data["structure"]),
        score=int(timeframe_data["score"]),
    )


def _classify_alignment(timeframes: list[TimeframeAnalysis], average_score: int) -> str:
    weekly = next((item for item in timeframes if item.timeframe == "Weekly"), None)
    daily = next((item for item in timeframes if item.timeframe == "Daily"), None)
    weekly_daily_bullish = (
        weekly is not None
        and daily is not None
        and weekly.trend == "Bullish"
        and daily.trend == "Bullish"
    )

    if average_score >= 80 and weekly_daily_bullish:
        return "Strong Bullish Alignment"
    if average_score >= 65:
        return "Bullish but Mixed"
    if average_score >= 50:
        return "Neutral / Choppy"
    return "Bearish Alignment"


def _build_summary(symbol: str, alignment: str, timeframes: list[TimeframeAnalysis]) -> str:
    weekly = next((item for item in timeframes if item.timeframe == "Weekly"), None)
    daily = next((item for item in timeframes if item.timeframe == "Daily"), None)

    if alignment == "Strong Bullish Alignment":
        return (
            f"{symbol} shows bullish alignment across weekly and daily timeframes, "
            "with shorter timeframes supporting the setup."
        )
    if alignment == "Bullish but Mixed":
        return (
            f"{symbol} has constructive weekly/daily context, but intraday "
            "timeframes are more mixed."
        )
    if alignment == "Neutral / Choppy":
        return (
            f"{symbol} is not fully aligned yet; weekly and daily trends need "
            "stronger confirmation."
        )

    weekly_trend = weekly.trend if weekly else "Unknown"
    daily_trend = daily.trend if daily else "Unknown"
    return f"{symbol} has weak alignment with weekly trend {weekly_trend} and daily trend {daily_trend}."


def analyze_multi_timeframe(symbol: str) -> MultiTimeframeItem:
    normalized_symbol = symbol.upper()
    timeframes = [
        analyze_timeframe(normalized_symbol, timeframe)
        for timeframe in TIMEFRAME_ORDER
    ]
    alignment_score = round(sum(item.score for item in timeframes) / len(timeframes))
    alignment = _classify_alignment(timeframes, alignment_score)

    return MultiTimeframeItem(
        symbol=normalized_symbol,
        alignment=alignment,
        alignment_score=alignment_score,
        timeframes=timeframes,
        summary=_build_summary(normalized_symbol, alignment, timeframes),
    )


def analyze_all_multi_timeframes() -> list[MultiTimeframeItem]:
    return [analyze_multi_timeframe(symbol) for symbol in WATCHLIST_SYMBOLS]


def build_multi_timeframe_response() -> MultiTimeframeResponse:
    items = analyze_all_multi_timeframes()
    strongest = max(items, key=lambda item: item.alignment_score)
    weakest = min(items, key=lambda item: item.alignment_score)

    return MultiTimeframeResponse(
        items=items,
        summary=(
            f"{strongest.symbol} has the strongest multi-timeframe alignment, "
            f"while {weakest.symbol} is the most mixed."
        ),
    )


def build_daily_multi_timeframe_summary() -> dict[str, str]:
    items = analyze_all_multi_timeframes()
    strongest = max(items, key=lambda item: item.alignment_score)
    weakest = min(items, key=lambda item: item.alignment_score)

    return {
        "strongest_alignment_stock": (
            f"{strongest.symbol}: {strongest.alignment} ({strongest.alignment_score})"
        ),
        "weakest_alignment_stock": (
            f"{weakest.symbol}: {weakest.alignment} ({weakest.alignment_score})"
        ),
        "summary": (
            f"{strongest.symbol} has the best multi-timeframe confirmation. "
            f"{weakest.symbol} needs more alignment before risk can be pressed."
        ),
    }

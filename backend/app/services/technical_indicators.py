def calculate_sma(values: list[float], period: int) -> float | None:
    """Return the average of the last `period` values, or None without enough data."""
    if period <= 0 or len(values) < period:
        return None

    return round(sum(values[-period:]) / period, 2)


def calculate_ema(values: list[float], period: int) -> float | None:
    """Return the standard EMA using smoothing factor 2 / (period + 1).

    The first EMA seed is the SMA of the first `period` values, then each later
    value applies: EMA_today = price * k + EMA_yesterday * (1 - k).
    """
    if period <= 0 or len(values) < period:
        return None

    smoothing = 2 / (period + 1)
    ema = sum(values[:period]) / period

    for value in values[period:]:
        ema = (value * smoothing) + (ema * (1 - smoothing))

    return round(ema, 2)


def calculate_rsi(values: list[float], period: int = 14) -> float | None:
    """Return standard RSI from average gains and losses over `period`.

    This MVP implementation uses the last `period` price changes. If average
    loss is zero, RSI is 100 because there was no downside over the window.
    """
    if period <= 0 or len(values) < period + 1:
        return None

    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    recent_changes = changes[-period:]
    gains = [change for change in recent_changes if change > 0]
    losses = [-change for change in recent_changes if change < 0]

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return round(rsi, 2)


def extract_closes_from_history(history: object) -> list[float]:
    """Extract close values from normalized provider HistoryData without fetching data."""
    candles = getattr(history, "candles", [])
    closes: list[float] = []

    for candle in candles:
        close = getattr(candle, "close", None)
        if close is not None:
            closes.append(float(close))

    return closes


def calculate_atr_from_candles(candles: list[object], period: int = 14) -> float | None:
    if period <= 0 or len(candles) < period + 1:
        return None

    true_ranges: list[float] = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous = candles[index - 1]
        high = float(get_candle_value(current, "high"))
        low = float(get_candle_value(current, "low"))
        previous_close = float(get_candle_value(previous, "close"))
        true_ranges.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )

    return round(sum(true_ranges[-period:]) / period, 2)


def calculate_macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, float | None]:
    if len(values) < slow_period + signal_period:
        return {"macd": None, "signal": None, "histogram": None}

    macd_series: list[float] = []
    for end_index in range(slow_period, len(values) + 1):
        window = values[:end_index]
        fast = calculate_ema(window, fast_period)
        slow = calculate_ema(window, slow_period)
        if fast is not None and slow is not None:
            macd_series.append(round(fast - slow, 4))

    signal = calculate_ema(macd_series, signal_period)
    macd = macd_series[-1] if macd_series else None
    histogram = round(macd - signal, 2) if macd is not None and signal is not None else None

    return {
        "macd": round(macd, 2) if macd is not None else None,
        "signal": signal,
        "histogram": histogram,
    }


def get_candle_value(candle: object, key: str) -> float:
    if isinstance(candle, dict):
        return float(candle[key])

    return float(getattr(candle, key))

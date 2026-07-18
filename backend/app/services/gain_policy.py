from __future__ import annotations

import math


def finite_number(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def quote_gain(current_price: float | int | None, previous_close: float | int | None) -> tuple[float | None, float | None]:
    price = finite_number(current_price)
    previous = finite_number(previous_close)
    if price is None or previous is None:
        return None, None
    change = price - previous
    if previous == 0:
        return change, None
    return change, (change / previous) * 100


def period_gain(first_visible_close: float | int | None, last_visible_close: float | int | None) -> float | None:
    first = finite_number(first_visible_close)
    last = finite_number(last_visible_close)
    if first is None or last is None or first == 0:
        return None
    return (last / first) - 1

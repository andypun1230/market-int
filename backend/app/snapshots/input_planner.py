from __future__ import annotations

import os
from dataclasses import dataclass

from app.providers.symbols import normalize_market_symbol


@dataclass(frozen=True)
class HistoryInput:
    symbol: str
    days: int
    required: bool
    reason: str
    resolution: str = "D"


@dataclass(frozen=True)
class QuoteInput:
    symbol: str
    required: bool
    reason: str


@dataclass(frozen=True)
class MarketSnapshotInputPlan:
    histories: list[HistoryInput]
    quotes: list[QuoteInput]


class MarketSnapshotInputPlanner:
    def __init__(self, lookback_days: int | None = None) -> None:
        self.lookback_days = lookback_days or int_env("MARKET_SNAPSHOT_HISTORY_DAYS", 370)

    def build_plan(self) -> MarketSnapshotInputPlan:
        required_history = {
            "SPY": "core index trend",
            "QQQ": "core index trend",
            "DIA": "core index trend",
            "IWM": "core index trend",
        }
        optional_history = {
            "RSP": "equal weight confirmation",
            "QQQEW": "equal weight confirmation",
            "IEF": "cross asset confirmation",
            "TLT": "cross asset confirmation",
            "GLD": "cross asset confirmation",
            "USO": "cross asset confirmation",
            "UUP": "cross asset confirmation",
            "HYG": "credit appetite",
        }
        history_by_symbol: dict[str, HistoryInput] = {}
        for symbol, reason in required_history.items():
            normalized = normalize_market_symbol(symbol, apply_alias=True)
            history_by_symbol[normalized] = HistoryInput(normalized, self.lookback_days, True, reason)
        for symbol, reason in optional_history.items():
            normalized = normalize_market_symbol(symbol, apply_alias=True)
            existing = history_by_symbol.get(normalized)
            if existing is None or existing.days < self.lookback_days:
                history_by_symbol[normalized] = HistoryInput(normalized, self.lookback_days, False, reason)

        quote_symbols = list(history_by_symbol)
        return MarketSnapshotInputPlan(
            histories=sorted(history_by_symbol.values(), key=lambda item: (not item.required, item.symbol)),
            quotes=[QuoteInput(symbol, symbol in required_history, "snapshot quote") for symbol in quote_symbols],
        )


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

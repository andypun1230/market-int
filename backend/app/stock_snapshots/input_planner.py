from __future__ import annotations

import os
from dataclasses import dataclass

from app.providers.symbols import normalize_market_symbol
from app.services.relative_strength import SECTOR_BENCHMARK, SYMBOL_SECTOR


@dataclass(frozen=True)
class StockDetailInputPlan:
    symbol: str
    resolution: str
    history_days: int
    benchmark_symbols: tuple[str, ...]
    sector_benchmark: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]


class StockDetailInputPlanner:
    def __init__(self, history_days: int | None = None) -> None:
        self.history_days = history_days or int_env("STOCK_SNAPSHOT_HISTORY_DAYS", 450)

    def plan(self, symbol: str) -> StockDetailInputPlan:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        sector = SYMBOL_SECTOR.get(normalized, "Market")
        sector_benchmark = SECTOR_BENCHMARK.get(sector, "SPY")
        benchmarks = tuple(dict.fromkeys(["SPY", "QQQ", sector_benchmark]))
        return StockDetailInputPlan(
            symbol=normalized,
            resolution="D",
            history_days=max(370, min(self.history_days, 1500)),
            benchmark_symbols=benchmarks,
            sector_benchmark=sector_benchmark,
            required_inputs=("quote", "selected_history"),
            optional_inputs=tuple(f"benchmark_history:{item}" for item in benchmarks),
        )


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


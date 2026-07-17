from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.providers.models import HistoryData, QuoteData
from app.providers.selector import get_market_data_provider
from app.stock_snapshots.input_planner import StockDetailInputPlan


@dataclass
class StockDetailInputBundle:
    plan: StockDetailInputPlan
    quote: QuoteData | None = None
    selected_history: HistoryData | None = None
    benchmark_histories: dict[str, HistoryData] = field(default_factory=dict)
    unavailable_inputs: dict[str, str] = field(default_factory=dict)
    cache_hits: dict[str, bool] = field(default_factory=dict)
    fetch_duration_ms: int = 0

    @property
    def input_hash(self) -> str:
        latest = self.selected_history.candles[-1] if self.selected_history and self.selected_history.candles else None
        payload = {
            "symbol": self.plan.symbol,
            "history_days": self.plan.history_days,
            "latest_history": {
                "timestamp": latest.timestamp if latest else None,
                "close": latest.close if latest else None,
                "count": len(self.selected_history.candles) if self.selected_history else 0,
                "provider": self.selected_history.provider or self.selected_history.source if self.selected_history else None,
            },
            "benchmarks": {
                symbol: history.candles[-1].timestamp if history.candles else None
                for symbol, history in sorted(self.benchmark_histories.items())
            },
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def build_input_bundle(plan: StockDetailInputPlan) -> StockDetailInputBundle:
    started = time.perf_counter()
    bundle = StockDetailInputBundle(plan=plan)
    provider = get_market_data_provider()

    try:
        bundle.quote = provider.get_quote(plan.symbol)
        bundle.cache_hits["quote"] = bool(getattr(bundle.quote, "cache_hit", False))
    except Exception as exc:
        bundle.unavailable_inputs["quote"] = error_category(exc)

    try:
        history = provider.get_history(plan.symbol, resolution=plan.resolution, days=plan.history_days)
        if history.candles:
            bundle.selected_history = history
            bundle.cache_hits["selected_history"] = bool(getattr(history, "cache_hit", False))
        else:
            bundle.unavailable_inputs["selected_history"] = history.error_message or "empty_history"
    except Exception as exc:
        bundle.unavailable_inputs["selected_history"] = error_category(exc)

    for benchmark in plan.benchmark_symbols:
        cached = get_cached_history(provider, benchmark, plan.resolution, min(plan.history_days, 450))
        if cached is None:
            bundle.unavailable_inputs[f"benchmark_history:{benchmark}"] = "cache_miss"
            continue
        bundle.benchmark_histories[benchmark] = cached
        bundle.cache_hits[f"benchmark_history:{benchmark}"] = True

    bundle.fetch_duration_ms = round((time.perf_counter() - started) * 1000)
    return bundle


def get_cached_history(provider: Any, symbol: str, resolution: str, days: int) -> HistoryData | None:
    cache = getattr(provider, "cache", None)
    if cache is None or not hasattr(cache, "find_history_covering"):
        return None
    try:
        provider_name = provider.get_provider_name_for("daily_history") if hasattr(provider, "get_provider_name_for") else provider.get_provider_health().provider
        found, _age, _key = cache.find_history_covering(provider_name, symbol, resolution, days)
        return found
    except Exception:
        return None


def error_category(error: BaseException) -> str:
    return str(getattr(error, "category", None) or type(error).__name__)


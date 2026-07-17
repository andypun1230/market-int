from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.providers.models import HistoryData, QuoteData
from app.services.market_data_repository import MarketDataRepository
from app.snapshots.input_planner import MarketSnapshotInputPlan


@dataclass
class MarketSnapshotInputBundle:
    quotes: dict[str, QuoteData] = field(default_factory=dict)
    histories: dict[str, HistoryData] = field(default_factory=dict)
    unavailable_inputs: dict[str, str] = field(default_factory=dict)
    input_latency_ms: dict[str, int] = field(default_factory=dict)
    requested_required: int = 0
    requested_optional: int = 0

    @property
    def required_available(self) -> int:
        return sum(1 for key in self.histories if key in {"SPY", "QQQ", "DIA", "IWM"})

    @property
    def optional_available(self) -> int:
        return max(0, len(self.histories) - self.required_available)

    def input_hash(self) -> str:
        rows: list[dict[str, Any]] = []
        for symbol, history in sorted(self.histories.items()):
            latest = history.candles[-1] if history.candles else None
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": latest.timestamp if latest else None,
                    "close": latest.close if latest else None,
                    "provider": history.provider or history.source,
                    "source_state": history.source_state,
                }
            )
        for symbol, quote in sorted(self.quotes.items()):
            rows.append(
                {
                    "symbol": symbol,
                    "quote_timestamp": quote.timestamp,
                    "quote_price": quote.price,
                    "provider": quote.provider or quote.source,
                    "source_state": quote.source_state,
                }
            )
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def fetch_input_bundle(plan: MarketSnapshotInputPlan, repository: MarketDataRepository) -> MarketSnapshotInputBundle:
    bundle = MarketSnapshotInputBundle(
        requested_required=sum(1 for item in plan.histories if item.required),
        requested_optional=sum(1 for item in plan.histories if not item.required),
    )
    for item in plan.histories:
        started = time.perf_counter()
        key = f"history:{item.symbol}"
        try:
            history = repository.get_history(item.symbol, resolution=item.resolution, days=item.days)
            if history.candles:
                bundle.histories[item.symbol] = history
            else:
                bundle.unavailable_inputs[key] = history.error_message or "empty_history"
        except Exception as exc:
            bundle.unavailable_inputs[key] = getattr(exc, "category", type(exc).__name__)
        bundle.input_latency_ms[key] = int((time.perf_counter() - started) * 1000)

    for item in plan.quotes:
        started = time.perf_counter()
        key = f"quote:{item.symbol}"
        try:
            bundle.quotes[item.symbol] = repository.get_quote(item.symbol)
        except Exception as exc:
            bundle.unavailable_inputs[key] = getattr(exc, "category", type(exc).__name__)
        bundle.input_latency_ms[key] = int((time.perf_counter() - started) * 1000)
    return bundle

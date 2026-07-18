from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.market_history.storage import DailyBar, DailyBarStorage
from app.services.market_data_repository import MarketDataRepository, get_market_data_repository


class BreadthUniverseHistoryUpdater:
    """Fetches only missing/overlap daily history outside interactive request paths."""
    def __init__(self, storage: DailyBarStorage | None = None, repository: MarketDataRepository | None = None) -> None:
        self.storage = storage or DailyBarStorage()
        self.repository = repository or get_market_data_repository()

    def update_symbol(self, ticker: str, *, provider_symbol: str | None = None, lookback_calendar_days: int = 450, overlap_days: int = 7, strict_live: bool = False) -> dict[str, Any]:
        latest = self.storage.latest_session(ticker)
        if latest:
            start = datetime.fromisoformat(latest).replace(tzinfo=timezone.utc) - timedelta(days=overlap_days)
            requested_days = max(overlap_days + 5, (datetime.now(timezone.utc) - start).days + 2)
        else:
            requested_days = lookback_calendar_days
        requested_symbol = provider_symbol or ticker
        if strict_live:
            history = self.repository.get_provider_for("daily_history").get_history(requested_symbol, resolution="D", days=requested_days)
        else:
            history = self.repository.get_history(requested_symbol, resolution="D", days=requested_days)
        if (strict_live and history.source_state != "live") or (history.source_state == "mock" and not allow_test_breadth()):
            raise RuntimeError("strict live breadth updater rejects mock history")
        bars = [to_daily_bar(ticker, history.provider or "polygon", candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume, history.as_of) for candle in history.candles]
        inserted, updated = self.storage.upsert(bars)
        return {"ticker": ticker.upper(), "provider_symbol": requested_symbol.upper(), "requested_days": requested_days, "received_bars": len(bars), "inserted_bars": inserted, "updated_bars": updated, "earliest_date": bars[0].session_date if bars else None, "latest_date": bars[-1].session_date if bars else None, "provider": history.provider or "polygon", "status": "complete" if bars else "unavailable", "source_state": history.source_state}


def to_daily_bar(ticker: str, provider: str, timestamp: str, open_: float, high: float, low: float, close: float, volume: float, source_timestamp: str | None) -> DailyBar:
    session_date = timestamp[:10]
    return DailyBar(ticker=ticker.upper(), provider=provider.lower(), session_date=session_date, timestamp=timestamp, open=float(open_), high=float(high), low=float(low), close=float(close), volume=float(volume or 0), adjusted=True, source_timestamp=source_timestamp)


def allow_test_breadth() -> bool:
    import os
    return (os.getenv("DATA_PROVIDER") or "").lower() in {"test", "generated_test_data"} and os.getenv("BREADTH_ALLOW_TEST_DATA", "false").lower() in {"1", "true", "yes"}

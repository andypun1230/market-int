from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.providers.mock_provider import MockMarketDataProvider, now_iso, serialize_model
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.test_data.repository import get_test_data_state


TEST_DATA_SOURCE = "generated_test_data"
INDEX_DAILY_CHANGE_BY_SCENARIO = {
    "balanced_market": {
        "SPY": 0.8,
        "QQQ": 1.2,
        "IWM": 0.3,
        "DIA": 0.4,
        "DJI": 0.4,
    },
    "risk_on": {
        "SPY": 1.1,
        "QQQ": 1.5,
        "IWM": 0.8,
        "DIA": 0.6,
        "DJI": 0.6,
    },
    "risk_off": {
        "SPY": -1.1,
        "QQQ": -1.6,
        "IWM": -1.3,
        "DIA": -0.8,
        "DJI": -0.8,
    },
    "rotation": {
        "SPY": 0.2,
        "QQQ": -0.3,
        "IWM": 0.5,
        "DIA": 0.1,
        "DJI": 0.1,
    },
}


class GeneratedTestMarketDataProvider(MockMarketDataProvider):
    """Local deterministic market-data provider used for development mode."""

    def get_quote(self, symbol: str) -> QuoteData:
        normalized_symbol = symbol.upper()
        history = self.get_history(normalized_symbol, days=2)
        latest = history.candles[-1] if history.candles else None
        previous = history.candles[-2] if len(history.candles) > 1 else latest

        if latest is None:
            raise ValueError(f"No generated test quote data available for {normalized_symbol}")

        previous_close = previous.close if previous else latest.close
        change_percent = get_index_daily_change(normalized_symbol)
        if change_percent is not None and previous_close:
            adjusted_close = round(previous_close * (1 + change_percent / 100), 2)
            latest = latest.model_copy(update={
                "close": adjusted_close,
                "high": round(max(latest.high, adjusted_close), 2),
                "low": round(min(latest.low, adjusted_close), 2),
            })
        change = round(latest.close - previous_close, 2)
        change_percent = change_percent if change_percent is not None else round((change / previous_close) * 100, 2) if previous_close else 0.0

        return QuoteData(
            symbol=normalized_symbol,
            price=latest.close,
            change=change,
            change_percent=change_percent,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            previous_close=previous_close,
            volume=latest.volume,
            timestamp=latest.timestamp,
            source=TEST_DATA_SOURCE,
            is_live=False,
            is_stale=False,
            fallback_used=False,
        )

    def get_history(
        self,
        symbol: str,
        resolution: str = "D",
        days: int = 240,
    ) -> HistoryData:
        base = super().get_history(symbol, resolution=resolution, days=days)
        transformed = transform_candles(base.candles, symbol.upper())
        return base.model_copy(
            update={
                "candles": transformed,
                "source": TEST_DATA_SOURCE,
                "is_live": False,
                "is_stale": False,
                "fallback_used": False,
                "as_of": now_iso(),
                "returned_candles": len(transformed),
                "error_message": None,
            }
        )

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=TEST_DATA_SOURCE,
            enabled=True,
            configured=True,
            reachable=True,
            last_successful_request=now_iso(),
            last_error=None,
            fallback_active=False,
            capabilities=self.get_capabilities(),
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=True,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        )

    def get_index_snapshots(self) -> dict[str, Any]:
        return {
            "indexes": [serialize_model(self.get_quote(symbol)) for symbol in ["SPY", "QQQ", "IWM", "DIA"]],
            "source": TEST_DATA_SOURCE,
            "data_status": "test",
        }

    def get_sector_etfs(self) -> dict[str, Any]:
        data = super().get_sector_etfs()
        items = []
        for item in data.get("items", []):
            symbol = str(item.get("symbol") or "")
            if symbol:
                items.append(serialize_model(self.get_quote(symbol)))
        return {
            "items": items,
            "summary": "Generated test sector ETF quotes are available through the local test-data provider.",
            "source": TEST_DATA_SOURCE,
            "data_status": "test",
        }


def transform_candles(candles: list[CandleData], symbol: str) -> list[CandleData]:
    state = get_test_data_state()
    if not candles:
        return candles

    symbol_bias = stable_unit(f"{state.seed}:{symbol}") - 0.5
    scenario_drift = {
        "risk_on": 0.12,
        "risk_off": -0.12,
        "rotation": symbol_bias * 0.18,
        "balanced_market": symbol_bias * 0.06,
    }.get(state.scenario, 0.0)
    base_scale = 1 + (stable_unit(f"{symbol}:{state.seed}:scale") - 0.5) * 0.08
    volume_scale = 1 + (stable_unit(f"{state.seed}:{symbol}:volume") - 0.5) * 0.25
    length = max(len(candles) - 1, 1)
    transformed: list[CandleData] = []

    for index, candle in enumerate(candles):
        progress = index / length
        wave = ((stable_unit(f"{state.seed}:{symbol}:{index // 7}") - 0.5) * 0.018)
        scale = max(0.2, base_scale * (1 + scenario_drift * (progress - 0.5) + wave))
        open_price = round(candle.open * scale, 2)
        close = round(candle.close * scale, 2)
        high = round(max(candle.high * scale, open_price, close), 2)
        low = round(min(candle.low * scale, open_price, close), 2)
        transformed.append(
            CandleData(
                timestamp=candle.timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=round(max(0, candle.volume * volume_scale), 2),
            )
        )

    return transformed


def get_index_daily_change(symbol: str) -> float | None:
    state = get_test_data_state()
    scenario_changes = INDEX_DAILY_CHANGE_BY_SCENARIO.get(state.scenario, INDEX_DAILY_CHANGE_BY_SCENARIO["balanced_market"])
    return scenario_changes.get(symbol)


def stable_unit(value: str) -> float:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)

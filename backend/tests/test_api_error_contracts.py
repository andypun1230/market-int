import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.providers.finnhub_provider import ProviderRequestError
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth
from app.services.market_data_repository import MarketDataRepository, MemoryMarketDataCache
from main import app


class FailingProvider:
    def get_quote(self, symbol: str):
        raise ProviderRequestError("provider quote failed", category="no_data")

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240):
        raise ProviderRequestError("provider history failed", category="network")


class RecordingHistoryProvider:
    def __init__(self) -> None:
        self.history_symbols: list[str] = []

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240):
        self.history_symbols.append(symbol)
        return HistoryData(
            symbol=symbol,
            candles=[
                CandleData(timestamp="2026-01-01T00:00:00+00:00", open=100, high=101, low=99, close=100.5, volume=1000),
                CandleData(timestamp="2026-01-02T00:00:00+00:00", open=101, high=102, low=100, close=101.5, volume=1100),
            ],
            timeframe=resolution,
            source="polygon",
            is_live=True,
            is_stale=False,
            fallback_used=False,
            as_of=datetime.now(timezone.utc).isoformat(),
            requested_days=days,
            returned_candles=2,
            provider="polygon",
            source_state="live",
        )

    def get_quote(self, symbol: str):
        raise NotImplementedError

    def get_quotes(self, symbols: list[str]):
        return []

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="polygon",
            enabled=True,
            configured=True,
            reachable=True,
            last_successful_request=None,
            last_error=None,
            fallback_active=False,
            capabilities=ProviderCapabilities(quotes=False, daily_history=True, intraday_history=False, adjusted_history=True, volume=True),
        )

    def get_capabilities(self):
        return self.get_provider_health().capabilities

    def get_index_snapshots(self):
        return {}

    def get_sector_etfs(self):
        return {}

    def get_watchlist_symbols(self):
        return []


class ApiErrorContractTests(unittest.TestCase):
    def test_provider_quote_failure_returns_structured_unavailable_response(self) -> None:
        with patch("app.api.market.get_market_data_provider", return_value=FailingProvider()):
            with TestClient(app) as client:
                response = client.get("/market/live/quote/ARM")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "unavailable")
        self.assertEqual(payload["source_state"], "unavailable")
        self.assertEqual(payload["category"], "no_data")
        self.assertNotIn("ProviderRequestError", response.text)

    def test_provider_history_failure_returns_structured_unavailable_response(self) -> None:
        with patch("app.api.market.get_market_data_provider", return_value=FailingProvider()):
            with TestClient(app) as client:
                response = client.get("/market/live/history/ARM?resolution=D&days=60")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "unavailable")
        self.assertEqual(payload["source_state"], "unavailable")
        self.assertEqual(payload["category"], "network")
        self.assertNotIn("ProviderRequestError", response.text)

    def test_ndx_history_route_uses_backend_qqq_alias_without_503(self) -> None:
        provider = RecordingHistoryProvider()
        repository = MarketDataRepository(provider=provider, data_provider="polygon", cache=MemoryMarketDataCache())
        with patch("app.api.market.get_market_data_provider", return_value=repository):
            with TestClient(app) as client:
                response = client.get("/market/live/history/NDX?resolution=D&days=110")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(provider.history_symbols, ["QQQ"])
        self.assertEqual(payload["symbol"], "QQQ")
        self.assertEqual(payload["requested_symbol"], "NDX")
        self.assertEqual(payload["provider_symbol"], "QQQ")


if __name__ == "__main__":
    unittest.main()

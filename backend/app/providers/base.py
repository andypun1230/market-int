from abc import ABC, abstractmethod
from typing import Any

from app.providers.models import HistoryData, ProviderCapabilities, ProviderHealth, QuoteData


class MarketDataProvider(ABC):
    """Abstract market data provider interface for Phase 4.

    Existing services still use deterministic mock data directly. This provider
    layer gives the backend a stable path for switching to live data later.
    """

    @abstractmethod
    def get_quote(self, symbol: str) -> QuoteData:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        resolution: str = "D",
        days: int = 240,
    ) -> HistoryData:
        raise NotImplementedError

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    @abstractmethod
    def get_provider_health(self) -> ProviderHealth:
        raise NotImplementedError

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=False,
            daily_history=False,
            intraday_history=False,
            adjusted_history=False,
            volume=False,
        )

    @abstractmethod
    def get_index_snapshots(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_sector_etfs(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_watchlist_symbols(self) -> list[str]:
        raise NotImplementedError

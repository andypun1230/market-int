from app.providers.intelligence_models import TradePrintData
from app.providers.models import ProviderHealth


class TradeFlowProvider:
    def get_recent_trades(
        self,
        symbol: str,
        lookback_minutes: int = 60,
    ) -> list[TradePrintData]:
        raise NotImplementedError

    def get_trade_flow_health(self) -> ProviderHealth:
        raise NotImplementedError

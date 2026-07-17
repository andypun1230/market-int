from app.providers.intelligence_models import LiquidityData
from app.providers.models import ProviderHealth


class LiquidityProvider:
    def get_quote_liquidity(self, symbol: str) -> LiquidityData:
        raise NotImplementedError

    def get_liquidity_health(self) -> ProviderHealth:
        raise NotImplementedError

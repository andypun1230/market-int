from datetime import datetime, timedelta, timezone

from app.providers.intelligence_models import (
    OptionContractData,
    OptionsChainData,
    SourceMetadata,
    TradePrintData,
)
from app.providers.models import ProviderCapabilities, ProviderHealth
from app.providers.options_base import OptionsDataProvider
from app.providers.trade_flow_base import TradeFlowProvider


class MockOptionsDataProvider(OptionsDataProvider):
    def get_option_chain(self, underlying: str, max_expirations: int = 4) -> OptionsChainData:
        symbol = underlying.upper()
        now = datetime.now(timezone.utc)
        price = {"SPY": 625, "QQQ": 555, "NVDA": 150, "MU": 142, "ARM": 162, "SNDK": 64}.get(symbol, 100)
        contracts: list[OptionContractData] = []
        for expiration_index in range(1, max_expirations + 1):
            expiration = (now + timedelta(days=expiration_index * 7)).date().isoformat()
            for offset in (-5, 0, 5):
                strike = round(price * (1 + offset / 100), 2)
                for option_type in ("call", "put"):
                    contracts.append(
                        OptionContractData(
                            ticker=f"O:{symbol}{expiration.replace('-', '')}{option_type[0].upper()}{int(strike * 1000)}",
                            underlying=symbol,
                            expiration=expiration,
                            strike=strike,
                            option_type=option_type,
                            bid=1.1 + abs(offset) * 0.1,
                            ask=1.35 + abs(offset) * 0.1,
                            last=1.2 + abs(offset) * 0.1,
                            volume=520 if option_type == "call" else 390,
                            open_interest=1800 - abs(offset) * 80,
                            implied_volatility=0.34 + abs(offset) * 0.004,
                            delta=0.48 if option_type == "call" else -0.48,
                            gamma=0.012,
                            theta=-0.03,
                            vega=0.08,
                            underlying_price=price,
                            timestamp=now.isoformat(),
                        )
                    )
        return OptionsChainData(
            underlying=symbol,
            contracts=contracts,
            metadata=SourceMetadata(
                source="mock",
                is_live=False,
                is_stale=False,
                fallback_used=False,
                as_of=now.isoformat(),
                quality_score=62,
                warnings=["Mock options chain for deterministic testing."],
            ),
        )

    def get_options_health(self) -> ProviderHealth:
        return mock_health("mock-options")


class MockTradeFlowProvider(TradeFlowProvider):
    def get_recent_trades(self, symbol: str, lookback_minutes: int = 60) -> list[TradePrintData]:
        normalized = symbol.upper()
        now = datetime.now(timezone.utc).isoformat()
        price = {"NVDA": 150, "MU": 142, "ARM": 162, "SNDK": 64}.get(normalized, 100)
        return [
            TradePrintData(
                symbol=normalized,
                price=price + index * 0.1,
                size=size,
                notional=round((price + index * 0.1) * size, 2),
                exchange="mock",
                conditions=[],
                timestamp=now,
            )
            for index, size in enumerate([1200, 1800, 9500, 1400, 11200, 1600, 1300])
        ]

    def get_trade_flow_health(self) -> ProviderHealth:
        return mock_health("mock-trade-flow")


def mock_health(provider: str) -> ProviderHealth:
    return ProviderHealth(
        provider=provider,
        enabled=True,
        configured=True,
        reachable=True,
        last_successful_request=datetime.now(timezone.utc).isoformat(),
        last_error=None,
        fallback_active=False,
        capabilities=ProviderCapabilities(
            quotes=False,
            daily_history=False,
            intraday_history=True,
            adjusted_history=False,
            volume=True,
        ),
    )

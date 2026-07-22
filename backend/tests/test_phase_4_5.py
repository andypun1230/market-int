import os
import unittest
from unittest.mock import patch

from app.providers.cache import clear_provider_cache, get_provider_cache_status
from app.providers.intelligence_models import OptionContractData, OptionsChainData, SourceMetadata


class Phase45InstitutionalIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._provider_environment = patch.dict(
            os.environ,
            {
                "DATA_PROVIDER": "mock",
                "MARKET_DATA_PROVIDER": "mock",
                "QUOTE_DATA_PROVIDER": "mock",
                "HISTORY_DATA_PROVIDER": "mock",
                "QUOTE_PROVIDER": "mock",
                "HISTORY_PROVIDER": "mock",
                "OPTIONS_PROVIDER": "mock",
                "TRADE_FLOW_PROVIDER": "mock",
            },
        )
        self._provider_environment.start()
        self.addCleanup(self._restore_provider_environment)
        clear_provider_cache()

    def _restore_provider_environment(self) -> None:
        from app.services.history_request_coordinator import reset_history_request_coordinator
        from app.services.market_data_repository import reset_market_data_repository

        self._provider_environment.stop()
        clear_provider_cache()
        reset_history_request_coordinator()
        reset_market_data_repository()

    def test_sentiment_component_calculation_and_mixed_put_call(self) -> None:
        from app.services.market_sentiment import build_market_sentiment_dashboard

        sentiment = build_market_sentiment_dashboard()
        put_call = next(signal for signal in sentiment.signals if signal.key == "put_call_ratio")

        self.assertGreater(sentiment.score, 0)
        self.assertFalse(sentiment.official_index)
        self.assertEqual(sentiment.methodology, "APInvest Market Sentiment")
        self.assertTrue(put_call.metadata["fallback_used"])

    def test_option_chain_normalization_and_put_call_calculation(self) -> None:
        from app.services.options_intelligence import analyze_chain

        chain = build_fixture_chain()
        result = analyze_chain(chain)

        self.assertEqual(result.symbol, "TEST")
        self.assertIsNotNone(result.put_call_ratio)
        self.assertIsNotNone(result.expected_move)
        self.assertIn("Estimated Gamma", result.estimated_gamma_regime or "")

    def test_partial_option_fields_do_not_crash(self) -> None:
        from app.services.options_intelligence import analyze_chain

        chain = build_fixture_chain(include_greeks=False)
        result = analyze_chain(chain)

        self.assertIsNotNone(result.score)
        self.assertIn("limitations", result.metadata)

    def test_block_trade_threshold_and_no_identity_inference(self) -> None:
        from app.services.block_trade_analysis import analyze_block_trade_candidates

        result = analyze_block_trade_candidates("NVDA")

        self.assertTrue(result["candidates"])
        joined = " ".join(candidate["reason"] for candidate in result["candidates"])
        self.assertNotIn("Institution bought", joined)
        self.assertNotIn("Institution sold", joined)

    def test_money_flow_proxy_classification(self) -> None:
        from app.services.money_flow import build_money_flow_dashboard

        response = build_money_flow_dashboard()

        self.assertIn(response.status, {"Strong Inflow", "Moderate Inflow", "Neutral", "Moderate Outflow", "Strong Outflow"})
        self.assertIn("Estimated money flow", response.methodology)

    def test_liquidity_score_calculation(self) -> None:
        from app.providers.market_data_liquidity_provider import calculate_liquidity_score

        high_score = calculate_liquidity_score(5_000_000_000, 0.02, 1.4)
        low_score = calculate_liquidity_score(10_000_000, 0.8, 0.3)

        self.assertGreater(high_score, low_score)

    def test_cache_reuse(self) -> None:
        from app.services.options_intelligence import analyze_symbol_options

        analyze_symbol_options("SPY")
        first = get_provider_cache_status()["items"]
        analyze_symbol_options("SPY")
        second = get_provider_cache_status()["items"]

        self.assertEqual(first, second)


def build_fixture_chain(include_greeks: bool = True) -> OptionsChainData:
    metadata = SourceMetadata(
        source="fixture",
        is_live=False,
        is_stale=False,
        fallback_used=False,
        as_of="2026-07-10T00:00:00+00:00",
        quality_score=90,
        warnings=[],
    )
    contracts = []
    for option_type, volume in (("call", 500), ("put", 250)):
        contracts.append(
            OptionContractData(
                ticker=f"TEST-{option_type}",
                underlying="TEST",
                expiration="2026-08-01",
                strike=100,
                option_type=option_type,
                bid=4,
                ask=5,
                last=4.5,
                volume=volume,
                open_interest=1000,
                implied_volatility=0.35,
                delta=0.5 if include_greeks else None,
                gamma=0.01 if include_greeks else None,
                theta=-0.02 if include_greeks else None,
                vega=0.08 if include_greeks else None,
                underlying_price=100,
                timestamp="2026-07-10T00:00:00+00:00",
            )
        )
    return OptionsChainData(underlying="TEST", contracts=contracts, metadata=metadata)


if __name__ == "__main__":
    unittest.main()

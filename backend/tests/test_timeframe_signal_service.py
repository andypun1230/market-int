import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.stock_analysis_aggregate import build_stock_analysis
from app.providers.models import CandleData, HistoryData
from app.services.timeframe_signal_service import (
    TechnicalSignalFactor,
    build_multi_timeframe_technical_signals,
    calculate_timeframe_signal,
    map_score_to_signal,
)


def make_history(closes: list[float], source: str = "polygon", is_live: bool = True) -> HistoryData:
    candles = [
        CandleData(
            timestamp=f"2026-01-{(index % 28) + 1:02d}T20:00:00Z",
            open=close - 0.5,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=1_000_000 + index * 1000,
        )
        for index, close in enumerate(closes)
    ]
    return HistoryData(
        symbol="TEST",
        candles=candles,
        timeframe="D",
        source=source,
        is_live=is_live,
        is_stale=False,
        fallback_used=False,
        as_of="2026-07-12T20:00:00Z",
        requested_days=len(candles),
        returned_candles=len(candles),
    )


class TimeframeSignalServiceTests(unittest.TestCase):
    def test_score_bands_map_consistently(self) -> None:
        self.assertEqual(map_score_to_signal(0), "strong_bearish")
        self.assertEqual(map_score_to_signal(20), "bearish")
        self.assertEqual(map_score_to_signal(40), "neutral")
        self.assertEqual(map_score_to_signal(61), "bullish")
        self.assertEqual(map_score_to_signal(81), "strong_bullish")

    def test_positive_and_negative_factors_drive_direction(self) -> None:
        positive = [
            TechnicalSignalFactor(f"p{index}", f"Positive {index}", "short", True, 1, 0.2, "live")
            for index in range(5)
        ]
        negative = [
            TechnicalSignalFactor(f"n{index}", f"Negative {index}", "short", False, -1, 0.2, "live")
            for index in range(5)
        ]

        self.assertEqual(calculate_timeframe_signal("short", positive, "2026").signal, "strong_bullish")
        self.assertEqual(calculate_timeframe_signal("short", negative, "2026").signal, "strong_bearish")

    def test_missing_inputs_are_excluded_not_bearish(self) -> None:
        factors = [
            TechnicalSignalFactor("a", "Available A", "medium", True, 1, 0.25, "live"),
            TechnicalSignalFactor("b", "Available B", "medium", True, 1, 0.25, "live"),
            TechnicalSignalFactor("c", "Missing C", "medium", None, None, 0.25, "unavailable"),
            TechnicalSignalFactor("d", "Missing D", "medium", None, None, 0.25, "unavailable"),
        ]

        signal = calculate_timeframe_signal("medium", factors, "2026")

        self.assertEqual(signal.signal, "unavailable")
        self.assertEqual(signal.score, None)
        self.assertEqual(signal.availableInputs, 2)

    def test_mock_pattern_is_excluded_from_signal_inputs(self) -> None:
        closes = [100 + index * 0.6 for index in range(260)]
        support = {
            "breakout_level": closes[-1] - 1,
            "stop_reference": closes[-1] - 20,
            "data_source": "live",
            "analysis_is_live": True,
        }
        mock_pattern = {
            "patterns": [{
                "name": "Mock Bull Flag",
                "direction": "bullish",
                "data_source": "mock",
                "is_live": False,
                "key_levels": {"breakout": closes[-1] - 1},
            }]
        }

        with patch("app.services.timeframe_signal_service.get_symbol_history", return_value=(make_history(closes), {"valid": True})):
            result = build_multi_timeframe_technical_signals(
                "TEST",
                support_resistance=support,
                trendline={"rising_support": {"detected": True}, "trendline_break": {"broken": False}, "data_source": "live", "analysis_is_live": True},
                volume_analysis={"volume_quality_score": 70, "accumulation_volume": True, "data_source": "live", "analysis_is_live": True},
                relative_strength={"overall_rs_score": 75, "rs_vs_sector": 70, "data_source": "live", "analysis_is_live": True},
                patterns=mock_pattern,
            )

        input_keys = [item.key for item in result.short.inputs]
        self.assertNotIn("compatible_pattern", input_keys)
        self.assertIn(result.short.signal, {"bullish", "strong_bullish"})

    def test_long_term_unavailable_when_major_history_missing(self) -> None:
        closes = [100 + index * 0.1 for index in range(90)]

        with patch("app.services.timeframe_signal_service.get_symbol_history", return_value=(make_history(closes), {"valid": True})):
            result = build_multi_timeframe_technical_signals("TEST")

        self.assertEqual(result.long.signal, "unavailable")
        self.assertEqual(result.long.score, None)

    def test_stock_analysis_aggregate_attaches_signal_payload(self) -> None:
        class FakeModel:
            def __init__(self, **values):
                self.__dict__.update(values)

            def model_dump(self):
                return dict(self.__dict__)

        signal_payload = {
            "short": {"signal": "bullish", "score": 68},
            "medium": {"signal": "neutral", "score": 52},
            "long": {"signal": "unavailable", "score": None},
            "overallDataStatus": "mixed",
            "generatedAt": "2026-07-12T20:00:00Z",
            "methodologyVersion": "1",
        }

        with (
            patch("app.services.stock_analysis_aggregate.calculate_support_resistance", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.analyze_trendline", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.analyze_volume", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.calculate_risk_plan", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.analyze_multi_timeframe", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.detect_patterns", return_value={"patterns": []}),
            patch("app.services.stock_analysis_aggregate.build_relative_strength", return_value=SimpleNamespace(items=[FakeModel(symbol="NVDA")])),
            patch("app.services.stock_analysis_aggregate.build_stock_ratings", return_value=SimpleNamespace(items=[FakeModel(symbol="NVDA")])),
            patch("app.services.stock_analysis_aggregate.analyze_symbol_options", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.analyze_symbol_liquidity", return_value={"symbol": "NVDA"}),
            patch("app.services.stock_analysis_aggregate.build_multi_timeframe_technical_signals", return_value=signal_payload) as signal_service,
        ):
            result = build_stock_analysis("NVDA")

        signal_service.assert_called_once()
        self.assertEqual(result["multiTimeframeSignals"], signal_payload)
        self.assertFalse(result["partial"])


if __name__ == "__main__":
    unittest.main()

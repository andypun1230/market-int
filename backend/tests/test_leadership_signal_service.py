import unittest

from app.services.leadership_signal_service import calculate_leadership_signal


def rs(overrides: dict | None = None) -> dict:
    data = {
        "overall_rs_score": 82,
        "rs_vs_spy": 76,
        "rs_vs_qqq": 74,
        "rs_vs_sector": 84,
        "data_source": "polygon",
        "analysis_is_live": True,
        "fallback_used": False,
    }
    data.update(overrides or {})
    return data


def volume(overrides: dict | None = None) -> dict:
    data = {
        "volume_quality_score": 82,
        "relative_volume": 1.8,
        "accumulation_volume": True,
        "data_source": "polygon",
        "analysis_is_live": True,
        "fallback_used": False,
    }
    data.update(overrides or {})
    return data


def timeframes(short: str = "bullish", medium: str = "bullish") -> dict:
    return {
        "overallDataStatus": "mixed",
        "short": {"signal": short, "score": 74},
        "medium": {"signal": medium, "score": 76},
        "long": {"signal": "unavailable", "score": None},
    }


def rating(score: int = 75) -> dict:
    return {"components": {"market_alignment": score}}


class LeadershipSignalServiceTests(unittest.TestCase):
    def test_strong_inputs_produce_leader(self) -> None:
        result = calculate_leadership_signal(
            "NVDA",
            relative_strength=rs(),
            volume_analysis=volume(),
            multi_timeframe_signals=timeframes("strong_bullish", "strong_bullish"),
            stock_rating=rating(85),
        )

        self.assertEqual(result.signal, "leader")
        self.assertIsNotNone(result.score)
        self.assertGreaterEqual(result.score or 0, 80)
        self.assertNotIn("buy", result.explanation.lower())

    def test_incomplete_broader_confirmation_produces_emerging_leader(self) -> None:
        result = calculate_leadership_signal(
            "NVDA",
            relative_strength=rs({"overall_rs_score": 70, "rs_vs_spy": 58, "rs_vs_qqq": 54, "rs_vs_sector": 78}),
            volume_analysis=volume({"volume_quality_score": 76}),
            multi_timeframe_signals=timeframes("bullish", "bullish"),
            stock_rating=rating(68),
        )

        self.assertEqual(result.signal, "emerging_leader")
        self.assertEqual(result.dataStatus, "mixed")

    def test_average_rs_produces_follower(self) -> None:
        result = calculate_leadership_signal(
            "MU",
            relative_strength=rs({"overall_rs_score": 52, "rs_vs_spy": 51, "rs_vs_qqq": 48, "rs_vs_sector": 57}),
            volume_analysis=volume({"volume_quality_score": 62}),
            multi_timeframe_signals=timeframes("neutral", "bullish"),
            stock_rating=rating(55),
        )

        self.assertEqual(result.signal, "follower")

    def test_weak_inputs_produce_lagging(self) -> None:
        result = calculate_leadership_signal(
            "ARM",
            relative_strength=rs({"overall_rs_score": 28, "rs_vs_spy": 30, "rs_vs_qqq": 26, "rs_vs_sector": 32}),
            volume_analysis=volume({"volume_quality_score": 35}),
            multi_timeframe_signals=timeframes("bearish", "bearish"),
            stock_rating=rating(35),
        )

        self.assertEqual(result.signal, "lagging")

    def test_missing_inputs_return_unavailable(self) -> None:
        result = calculate_leadership_signal("XYZ", relative_strength=None, volume_analysis=None, multi_timeframe_signals=None, stock_rating=None)

        self.assertEqual(result.signal, "unavailable")
        self.assertIsNone(result.score)

    def test_mock_volume_is_excluded_from_positive_confirmation(self) -> None:
        result = calculate_leadership_signal(
            "NVDA",
            relative_strength=rs({"overall_rs_score": 70, "rs_vs_spy": 61, "rs_vs_qqq": 59, "rs_vs_sector": 68}),
            volume_analysis=volume({"volume_quality_score": 100, "data_source": "mock", "analysis_is_live": False}),
            multi_timeframe_signals=timeframes("bullish", "bullish"),
            stock_rating=rating(65),
        )

        self.assertNotIn("Strong participation supports the move", result.positiveEvidence)


if __name__ == "__main__":
    unittest.main()

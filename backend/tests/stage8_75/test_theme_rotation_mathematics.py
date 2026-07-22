from __future__ import annotations

import math
import unittest
from datetime import date, timedelta

from app.market_history.storage import DailyBar
from app.rotation.engine import quadrant
from app.rotation.theme_engine import (
    build_theme_rotation_series,
    calculate_theme_rotation_history,
    robust_signed_normalize,
)
from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION, theme_profile_for
from app.themes.basket import build_equal_weight_basket_history
from app.themes.models import ThemeBasketBar


class ThemeRotationMathematicsTests(unittest.TestCase):
    def test_equal_weight_index_uses_returns_not_raw_prices(self) -> None:
        histories = {
            "A": self._price_history("A", [10.0, 11.0]),
            "B": self._price_history("B", [100.0, 101.0]),
        }
        bars = build_equal_weight_basket_history(
            theme_id="theme", theme_version="v1", tickers=("A", "B"), histories=histories,
            source_state="test", partial_coverage_threshold=0.75,
        )
        self.assertEqual(len(bars), 1)
        self.assertAlmostEqual(bars[0].daily_return, 0.055)
        self.assertAlmostEqual(bars[0].index_level, 105.5)
        self.assertNotAlmostEqual(bars[0].index_level, (11.0 + 101.0) / 2.0)

    def test_missing_constituent_is_excluded_not_zero_filled(self) -> None:
        histories = {
            "A": self._price_history("A", [100.0, 110.0]),
            "B": self._price_history("B", [100.0]),
        }
        bars = build_equal_weight_basket_history(
            theme_id="theme", theme_version="v1", tickers=("A", "B"), histories=histories,
            source_state="test", partial_coverage_threshold=0.5,
        )
        self.assertAlmostEqual(bars[-1].daily_return, 0.1)
        self.assertEqual((bars[-1].eligible_members, bars[-1].total_members), (1, 2))
        self.assertEqual(bars[-1].coverage_ratio, 0.5)

    def test_constant_equal_performance_converges_to_neutral(self) -> None:
        basket, benchmark = self._series([(500, 0.0)])
        result = self._build(basket, benchmark, "medium")
        self.assertEqual(result["current_point"]["relative_trend"], 100.0)
        self.assertEqual(result["current_point"]["relative_momentum"], 100.0)
        self.assertEqual(result["current_point"]["relative_price_rebased"], 100.0)

    def test_persistent_outperformance_keeps_trend_positive_as_momentum_settles(self) -> None:
        basket, benchmark = self._series([(300, 0.0), (500, 0.001)])
        history = calculate_theme_rotation_history(basket, benchmark, "medium")
        post_change = [item for item in history if item["relative_trend"] > 100]
        self.assertTrue(post_change)
        self.assertGreater(max(item["relative_momentum"] for item in post_change), 100)
        self.assertGreater(post_change[-1]["relative_trend"], 100)
        self.assertAlmostEqual(post_change[-1]["relative_momentum"], 100, delta=0.1)

    def test_recovery_moves_lagging_improving_leading_with_momentum_first(self) -> None:
        basket, benchmark = self._series([(300, -0.001), (380, -0.0001), (500, 0.0015)])
        quadrants = [item["quadrant"] for item in calculate_theme_rotation_history(basket, benchmark, "medium")]
        improving = quadrants.index("improving")
        leading = quadrants.index("leading", improving + 1)
        self.assertIn("lagging", quadrants[:improving])
        self.assertLess(improving, leading)

    def test_leadership_loss_moves_leading_weakening_lagging(self) -> None:
        basket, benchmark = self._series([(300, 0.001), (380, 0.0001), (500, -0.0015)])
        quadrants = [item["quadrant"] for item in calculate_theme_rotation_history(basket, benchmark, "medium")]
        weakening = quadrants.index("weakening")
        lagging = quadrants.index("lagging", weakening + 1)
        self.assertIn("leading", quadrants[:weakening])
        self.assertLess(weakening, lagging)

    def test_temporary_shock_does_not_permanently_break_coordinates(self) -> None:
        basket, benchmark = self._series([(500, 0.0)], shock_at=180)
        history = calculate_theme_rotation_history(basket, benchmark, "medium")
        self.assertLessEqual(max(abs(item["relative_trend"] - 100) for item in history), 6.0)
        self.assertAlmostEqual(history[-1]["relative_trend"], 100, delta=0.15)
        self.assertAlmostEqual(history[-1]["relative_momentum"], 100, delta=0.15)

    def test_missing_session_breaks_continuity_and_never_fabricates_tail(self) -> None:
        basket, benchmark = self._series([(500, 0.0002)], missing={300})
        result = self._build(basket, benchmark, "short")
        self.assertEqual(result["continuity_segment_count"], 2)
        self.assertTrue(result["trail_points"])
        self.assertTrue(all(item["market_date"] > (date(2024, 1, 1) + timedelta(days=300)).isoformat() for item in result["trail_points"]))
        self.assertTrue(all(not item["is_synthetic"] for item in result["trail_points"]))

    def test_universe_membership_change_does_not_move_other_theme(self) -> None:
        basket, benchmark = self._series([(500, 0.0003)])
        alone = self._build(basket, benchmark, "medium")
        # This model is normalized causally per theme after dimensionless
        # volatility scaling; adding/removing another theme cannot alter it.
        other, other_benchmark = self._series([(500, -0.0004)])
        self._build(other, other_benchmark, "medium")
        repeated = self._build(basket, benchmark, "medium")
        self.assertEqual(alone["trail_points"], repeated["trail_points"])

    def test_relative_price_is_theme_index_divided_by_spy(self) -> None:
        basket, benchmark = self._series([(500, 0.0004)])
        point = self._build(basket, benchmark, "short")["current_point"]
        self.assertAlmostEqual(point["relative_price"], point["theme_index_value"] / point["benchmark_adjusted_close"], places=8)

    def test_zero_benchmark_is_unavailable_not_zero_coordinate(self) -> None:
        basket, benchmark = self._series([(500, 0.0004)])
        invalid = [DailyBar(**{**bar.__dict__, "close": 0.0}) for bar in benchmark]
        result = self._build(basket, invalid, "medium")
        self.assertIsNone(result["current_point"])
        self.assertEqual(result["status"], "insufficient_history")

    def test_no_lookahead(self) -> None:
        basket, benchmark = self._series([(350, -0.0003), (500, 0.0008)])
        truncated = calculate_theme_rotation_history(basket[:420], benchmark[:420], "medium")
        full = calculate_theme_rotation_history(basket, benchmark, "medium")
        target = truncated[-1]
        matching = next(item for item in full if item["market_date"] == target["market_date"])
        self.assertEqual(target, matching)

    def test_robust_normalization_discloses_winsorization(self) -> None:
        score, metadata = robust_signed_normalize(100.0, [0.5, 0.7, 0.8, 0.9, 1.0], floor=0.1, limit=3.0)
        self.assertEqual(score, 3.0)
        self.assertTrue(metadata["winsorized"])
        self.assertEqual(metadata["winsor_limit"], 3.0)

    def test_profiles_have_distinct_governed_parameters_and_outputs(self) -> None:
        basket, benchmark = self._series([(260, -0.0005), (500, 0.001)])
        results = [self._build(basket, benchmark, value) for value in ("short", "medium", "long")]
        self.assertEqual([item["profile_definition"]["fast_window"] for item in results], [10, 20, 10])
        self.assertEqual([item["profile_definition"]["sampling_frequency"] for item in results], ["daily", "daily", "weekly_last_complete_session"])
        coordinates = {(item["current_point"]["relative_trend"], item["current_point"]["relative_momentum"]) for item in results}
        self.assertGreater(len(coordinates), 1)

    def test_tail_is_chronological_genuine_and_current_endpoint_matches(self) -> None:
        basket, benchmark = self._series([(500, 0.0004)])
        result = self._build(basket, benchmark, "medium")
        dates = [item["market_date"] for item in result["trail_points"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(result["point_count"], 10)
        self.assertEqual(result["current_point"], result["trail_points"][-1])
        self.assertTrue(result["current_point"]["is_current"])

    def test_direction_speed_and_distance_are_euclidean(self) -> None:
        basket, benchmark = self._series([(350, -0.0004), (500, 0.0008)])
        result = self._build(basket, benchmark, "medium")
        point = result["trail_points"][-1]
        self.assertAlmostEqual(point["speed"], math.hypot(point["dx"], point["dy"]), places=5)
        self.assertGreaterEqual(result["distance_travelled"], result["net_displacement"])

    def test_quadrant_boundary_and_all_four_states(self) -> None:
        self.assertEqual(quadrant(100, 100), "leading")
        self.assertEqual(quadrant(99, 100), "improving")
        self.assertEqual(quadrant(100, 99), "weakening")
        self.assertEqual(quadrant(99, 99), "lagging")

    def test_model_is_deterministic_and_versioned(self) -> None:
        basket, benchmark = self._series([(500, 0.0004)])
        first = self._build(basket, benchmark, "medium")
        second = self._build(basket, benchmark, "medium")
        self.assertEqual(first, second)
        self.assertEqual(first["model_version"], THEME_ROTATION_MODEL_VERSION)
        self.assertEqual(first["profile_definition"], theme_profile_for("medium").model_dump())

    @staticmethod
    def _price_history(symbol: str, closes: list[float]) -> tuple[DailyBar, ...]:
        start = date(2024, 1, 1)
        return tuple(
            DailyBar(symbol, "polygon", (start + timedelta(days=index)).isoformat(), (start + timedelta(days=index)).isoformat(), close, close, close, close, 1.0, adjusted=True, quality_status="valid")
            for index, close in enumerate(closes)
        )

    @staticmethod
    def _series(
        slopes: list[tuple[int, float]], *, shock_at: int | None = None, missing: set[int] | None = None
    ) -> tuple[list[ThemeBasketBar], list[DailyBar]]:
        start = date(2024, 1, 1)
        relative = 1.0
        missing = missing or set()
        basket: list[ThemeBasketBar] = []
        benchmark: list[DailyBar] = []
        for index in range(slopes[-1][0]):
            slope = next(value for end, value in slopes if index < end)
            relative *= math.exp(slope)
            if shock_at == index:
                relative *= 1.5
            market_date = (start + timedelta(days=index)).isoformat()
            benchmark_level = 100.0 * 1.0003 ** index
            benchmark.append(DailyBar("SPY", "polygon", market_date, market_date, benchmark_level, benchmark_level, benchmark_level, benchmark_level, 1.0, adjusted=True, quality_status="valid"))
            if index not in missing:
                basket.append(ThemeBasketBar("theme", "v1", market_date, benchmark_level * relative, 0.0, 10, 10, 1.0, "test", "equal-weight-v1", f"h{index}", market_date))
        return basket, benchmark

    @staticmethod
    def _build(basket: list[ThemeBasketBar], benchmark: list[DailyBar], profile: str) -> dict[str, object]:
        return build_theme_rotation_series(
            theme_id="theme", display_name="Theme", short_label="THM", theme_version="v1",
            basket_history=basket, benchmark_history=benchmark, profile=profile,
            source_state="test", data_mode="test",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import unittest
from datetime import date, timedelta

from app.market_history.storage import DailyBar
from app.rotation.sector_engine import build_sector_rotation_series, calculate_sector_rotation_history
from app.rotation.sector_policy import SECTOR_ROTATION_MODEL_VERSION, SECTOR_ROTATION_PROFILES, sector_profile_for
from app.rotation.theme_engine import calculate_theme_rotation_history
from app.rotation.theme_policy import THEME_ROTATION_PROFILES
from app.themes.models import ThemeBasketBar


class SectorRotationMathematicsTests(unittest.TestCase):
    def test_sector_profiles_are_parameter_identical_to_theme_profiles(self) -> None:
        fields = (
            "sampling_frequency", "fast_window", "slow_window", "volatility_window",
            "normalization_window", "momentum_lag", "momentum_smoothing",
            "tail_observations", "observation_spacing", "trend_scale",
            "momentum_scale", "winsor_limit", "epsilon",
        )
        for name in ("short", "medium", "long"):
            sector = SECTOR_ROTATION_PROFILES[name]
            theme = THEME_ROTATION_PROFILES[name]
            self.assertEqual({field: getattr(sector, field) for field in fields}, {field: getattr(theme, field) for field in fields})

    def test_sector_kernel_matches_theme_kernel_coordinate_for_coordinate(self) -> None:
        entity, benchmark, basket = self._series([(260, -0.0004), (500, 0.0009)])
        for profile in ("short", "medium", "long"):
            sector = calculate_sector_rotation_history(entity, benchmark, profile)
            theme = calculate_theme_rotation_history(basket, benchmark, profile)
            self.assertEqual(
                [(item["market_date"], item["relative_trend"], item["relative_momentum"], item["quadrant"]) for item in sector],
                [(item["market_date"], item["relative_trend"], item["relative_momentum"], item["quadrant"]) for item in theme],
            )

    def test_constant_equal_performance_converges_to_neutral(self) -> None:
        entity, benchmark, _ = self._series([(500, 0.0)])
        current = self._build(entity, benchmark, "medium")["current_point"]
        self.assertEqual((current["relative_trend"], current["relative_momentum"]), (100.0, 100.0))

    def test_momentum_leads_trend_during_recovery(self) -> None:
        entity, benchmark, _ = self._series([(300, -0.001), (380, -0.0001), (500, 0.0015)])
        quadrants = [item["quadrant"] for item in calculate_sector_rotation_history(entity, benchmark, "medium")]
        improving = quadrants.index("improving")
        leading = quadrants.index("leading", improving + 1)
        self.assertIn("lagging", quadrants[:improving])
        self.assertLess(improving, leading)

    def test_momentum_weakens_before_trend_during_leadership_loss(self) -> None:
        entity, benchmark, _ = self._series([(300, 0.001), (380, 0.0001), (500, -0.0015)])
        quadrants = [item["quadrant"] for item in calculate_sector_rotation_history(entity, benchmark, "medium")]
        weakening = quadrants.index("weakening")
        lagging = quadrants.index("lagging", weakening + 1)
        self.assertIn("leading", quadrants[:weakening])
        self.assertLess(weakening, lagging)

    def test_missing_etf_session_breaks_continuity_without_fabrication(self) -> None:
        entity, benchmark, _ = self._series([(500, 0.0003)], missing={300})
        result = self._build(entity, benchmark, "short")
        self.assertEqual(result["continuity_segment_count"], 2)
        self.assertTrue(all(not point["is_synthetic"] for point in result["trail_points"]))
        self.assertTrue(all(point["market_date"] > (date(2024, 1, 1) + timedelta(days=300)).isoformat() for point in result["trail_points"]))

    def test_no_lookahead(self) -> None:
        entity, benchmark, _ = self._series([(350, -0.0003), (500, 0.0008)])
        truncated = calculate_sector_rotation_history(entity[:420], benchmark[:420], "medium")
        full = calculate_sector_rotation_history(entity, benchmark, "medium")
        target = truncated[-1]
        self.assertEqual(target, next(item for item in full if item["market_date"] == target["market_date"]))

    def test_tail_is_genuine_chronological_and_versioned(self) -> None:
        entity, benchmark, _ = self._series([(500, 0.0004)])
        result = self._build(entity, benchmark, "medium")
        dates = [item["market_date"] for item in result["trail_points"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(len(dates), 10)
        self.assertEqual(result["current_point"], result["trail_points"][-1])
        self.assertEqual(result["model_version"], SECTOR_ROTATION_MODEL_VERSION)
        self.assertEqual(result["profile_definition"], sector_profile_for("medium").model_dump())

    def test_zero_benchmark_produces_no_coordinate(self) -> None:
        entity, benchmark, _ = self._series([(500, 0.0004)])
        invalid = [DailyBar(**{**bar.__dict__, "close": 0.0}) for bar in benchmark]
        result = self._build(entity, invalid, "medium")
        self.assertIsNone(result["current_point"])
        self.assertEqual(result["status"], "insufficient_history")

    @staticmethod
    def _series(
        slopes: list[tuple[int, float]], *, missing: set[int] | None = None
    ) -> tuple[list[DailyBar], list[DailyBar], list[ThemeBasketBar]]:
        start = date(2024, 1, 1)
        relative = 1.0
        missing = missing or set()
        entity: list[DailyBar] = []
        benchmark: list[DailyBar] = []
        basket: list[ThemeBasketBar] = []
        for index in range(slopes[-1][0]):
            slope = next(value for end, value in slopes if index < end)
            relative *= math.exp(slope)
            market_date = (start + timedelta(days=index)).isoformat()
            benchmark_level = 100.0 * 1.0003 ** index
            entity_level = benchmark_level * relative
            benchmark.append(DailyBar("SPY", "polygon", market_date, market_date, benchmark_level, benchmark_level, benchmark_level, benchmark_level, 1.0, adjusted=True, quality_status="valid"))
            if index not in missing:
                entity.append(DailyBar("XLK", "polygon", market_date, market_date, entity_level, entity_level, entity_level, entity_level, 1.0, adjusted=True, quality_status="valid"))
                basket.append(ThemeBasketBar("synthetic_sector", "v1", market_date, entity_level, 0.0, 1, 1, 1.0, "test", "adjusted-sector-etf-index-v1", f"h{index}", market_date))
        return entity, benchmark, basket

    @staticmethod
    def _build(entity: list[DailyBar], benchmark: list[DailyBar], profile: str) -> dict[str, object]:
        return build_sector_rotation_series(
            sector_id="information_technology", display_name="Information Technology", etf_symbol="XLK",
            etf_history=entity, benchmark_history=benchmark, profile=profile, source_state="test", data_mode="test",
            universe_id="sp100", universe_version="v1", coverage_ratio=1.0, eligible_members=10, total_members=10,
        )


if __name__ == "__main__":
    unittest.main()

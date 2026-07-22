from __future__ import annotations

import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.providers.models import CandleData, HistoryData
from app.stock_snapshots import builder as snapshot_builder
from app.stock_snapshots.input_bundle import StockDetailInputBundle
from app.stock_snapshots.input_planner import StockDetailInputPlanner


FIXED_NOW = "2026-07-22T12:00:00+00:00"
EMPTY_PATTERN_PAYLOAD = {"symbol": "NVDA", "patterns": []}


def make_history(symbol: str, days: int = 450) -> HistoryData:
    started_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles = [
        CandleData(
            timestamp=(started_at + timedelta(days=index)).isoformat(),
            open=100 + index * 0.2,
            high=101 + index * 0.2,
            low=99 + index * 0.2,
            close=100 + index * 0.2,
            volume=1_000_000 + index * 1_000,
        )
        for index in range(days)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source="test",
        is_live=True,
        is_stale=False,
        fallback_used=False,
        as_of=candles[-1].timestamp,
        requested_days=days,
        returned_candles=days,
        provider="test",
        source_state="live",
    )


def make_bundle() -> StockDetailInputBundle:
    plan = StockDetailInputPlanner(history_days=450).plan("NVDA")
    return StockDetailInputBundle(
        plan=plan,
        selected_history=make_history(plan.symbol),
        benchmark_histories={symbol: make_history(symbol) for symbol in plan.benchmark_symbols},
    )


class StockSnapshotComputationDagTests(unittest.TestCase):
    def build_sections(self, bundle: StockDetailInputBundle):
        builder = snapshot_builder.StockAnalysisSnapshotBuilder.__new__(snapshot_builder.StockAnalysisSnapshotBuilder)
        return builder._build_sections(bundle)

    def test_snapshot_dag_computes_every_section_analysis_once(self) -> None:
        bundle = make_bundle()
        analysis_functions = (
            "build_chart_section",
            "build_technical_section",
            "build_support_resistance_section",
            "build_trend_section",
            "build_volume_section",
            "build_relative_strength_section",
            "_build_risk_section_from_dependencies",
            "_build_rating_section_from_dependencies",
            "_build_signals_section_from_dependencies",
            "_build_leadership_section_from_dependencies",
            "_build_executive_summary_section_from_dependencies",
            "_build_overall_assessment_section_from_dependencies",
        )

        with ExitStack() as stack:
            spies = {
                name: stack.enter_context(patch.object(snapshot_builder, name, wraps=getattr(snapshot_builder, name)))
                for name in analysis_functions
            }
            spies["build_pattern_section"] = stack.enter_context(
                patch.object(snapshot_builder, "build_pattern_section", return_value=EMPTY_PATTERN_PAYLOAD)
            )
            sections = self.build_sections(bundle)

        self.assertTrue(all(section.status == "complete" for section in sections.values()))
        for name, spy in spies.items():
            self.assertEqual(spy.call_count, 1, f"{name} should execute exactly once per snapshot build")

    def test_dag_payloads_match_standalone_builder_semantics(self) -> None:
        bundle = make_bundle()

        with (
            patch.object(snapshot_builder, "now_iso", return_value=FIXED_NOW),
            patch.object(snapshot_builder, "build_pattern_section", return_value=EMPTY_PATTERN_PAYLOAD),
        ):
            standalone_builders = {
                "chart": snapshot_builder.build_chart_section,
                "technical": snapshot_builder.build_technical_section,
                "support_resistance": snapshot_builder.build_support_resistance_section,
                "trend": snapshot_builder.build_trend_section,
                "volume": snapshot_builder.build_volume_section,
                "risk": snapshot_builder.build_risk_section,
                "relative_strength": snapshot_builder.build_relative_strength_section,
                "pattern": snapshot_builder.build_pattern_section,
                "rating": snapshot_builder.build_rating_section,
                "signals": snapshot_builder.build_signals_section,
                "leadership": snapshot_builder.build_leadership_section,
                "executive_summary": snapshot_builder.build_executive_summary_section,
                "overall_assessment": snapshot_builder.build_overall_assessment_section,
            }
            expected = {
                name: snapshot_builder.to_jsonable(section_builder(bundle))
                for name, section_builder in standalone_builders.items()
            }
            actual_sections = self.build_sections(bundle)

        self.assertEqual(
            {name: section.payload for name, section in actual_sections.items()},
            expected,
        )

    def test_failed_dependency_is_attempted_once_and_remains_section_local(self) -> None:
        bundle = make_bundle()

        with patch.object(snapshot_builder, "build_pattern_section", side_effect=RuntimeError("pattern failed")) as pattern_spy:
            sections = self.build_sections(bundle)

        self.assertEqual(pattern_spy.call_count, 1)
        self.assertEqual(sections["pattern"].status, "unavailable")
        self.assertEqual(sections["signals"].status, "unavailable")
        self.assertEqual(sections["leadership"].status, "unavailable")
        self.assertEqual(sections["rating"].status, "complete")
        self.assertEqual(sections["executive_summary"].status, "complete")
        self.assertEqual(sections["overall_assessment"].status, "complete")


if __name__ == "__main__":
    unittest.main()

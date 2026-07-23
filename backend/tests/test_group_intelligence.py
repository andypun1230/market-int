from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.breadth.builder import detect_divergence as detect_market_divergence

from app.group_intelligence import (
    GroupSources,
    build_breadth_history,
    build_sector_alerts,
    compare_groups,
    detect_divergences,
    filter_groups,
    normalize_group_registry,
)


def sector_row(
    entity_id: str,
    rank: int,
    *,
    classification: str = "Leading",
    return_1m: float = 4,
    above20: float = 72,
    above50: float = 68,
    above200: float = 61,
    ad_ratio: float = 1.8,
    highs: int = 5,
    lows: int = 1,
    concentration: float = 68,
    momentum: float = 92,
) -> dict:
    return {
        "sector_id": entity_id,
        "display_name": entity_id.replace("_", " ").title(),
        "rank": rank,
        "classification": classification,
        "status": "available",
        "price_metrics": {"return_1d": 0.2, "return_1w": 1.1, "return_1m": return_1m, "return_3m": 8, "return_6m": 12, "return_1y": 22},
        "relative_strength_metrics": {"vs_spy_1m": 3.2},
        "component_scores": {"relative_strength": 65, "momentum": momentum},
        "breadth_metrics": {
            "percent_above_ema20": above20, "percent_above_ema50": above50,
            "percent_above_ema200": above200, "advance_decline_ratio": ad_ratio,
            "advancing": 7, "declining": 3, "new_52_week_highs": highs, "new_52_week_lows": lows,
        },
        "participation_metrics": {"top_contributor_concentration": concentration},
        "data_confidence": {"label": "High", "score": 90, "reason": "fixture coverage"},
        "signal_confidence": {"label": "Moderate", "score": 72, "reason": "fixture agreement"},
        "warnings": [],
    }


def snapshot(snapshot_id: str, market_date: str, rows: list[dict]) -> dict:
    return {
        "snapshot_id": snapshot_id, "schema_version": 5, "market_date": market_date,
        "generated_at": f"{market_date}T21:00:00Z", "source_state": "test", "status": "complete",
        "sectors": rows, "warnings": [], "input_hash": snapshot_id,
        "provider_provenance": {"rotation_model_version": "sector-relative-trend-momentum-v1"},
    }


class GroupIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = snapshot("sector-previous", "2026-07-21", [
            sector_row("information_technology", 3, classification="Improving", above20=86, above50=78, ad_ratio=2.4, highs=9, lows=0),
            sector_row("financials", 1, classification="Leading", return_1m=-2, above20=40, above50=38, ad_ratio=0.7, concentration=30, momentum=104),
            sector_row("health_care", 2), sector_row("industrials", 4), sector_row("energy", 5),
        ])
        self.current = snapshot("sector-current", "2026-07-22", [
            sector_row("information_technology", 1, above20=62, above50=60, ad_ratio=1.1, highs=4, lows=3),
            sector_row("financials", 2, classification="Improving", return_1m=-2, above20=62, above50=58, ad_ratio=1.4, concentration=30, momentum=105),
            sector_row("health_care", 3), sector_row("industrials", 4), sector_row("energy", 5),
        ])
        self.sources = GroupSources(self.current, [self.previous, self.current])
        self.registry = normalize_group_registry("sector", self.sources)

    def test_registry_is_backend_owned_and_preserves_unavailable_values(self) -> None:
        self.assertEqual("group-intelligence-v1", self.registry["contract_version"])
        self.assertEqual("sector-current", self.registry["snapshot_id"])
        item = self.registry["items"][0]
        self.assertEqual("/sectors", item["canonical_destination"]["route"])
        self.assertEqual(2, item["rank_change"])
        self.assertEqual("gaining", item["movement"]["direction"])
        self.assertEqual("high", item["confidence"]["data"]["label"].lower())
        zero_row = sector_row("zero_relative_strength", 6)
        zero_row["relative_strength_metrics"]["vs_spy_1m"] = 0
        zero_registry = normalize_group_registry(
            "sector",
            GroupSources(snapshot("sector-zero", "2026-07-22", [zero_row]), []),
        )
        self.assertEqual(0, zero_registry["items"][0]["relative_strength"])

    def test_comparison_enforces_selection_limits_and_deterministic_url(self) -> None:
        response = compare_groups(self.registry, ["information_technology", "financials"], "1m")
        self.assertEqual("sector", response["entity_type"])
        self.assertEqual("1M", response["timeframe"])
        self.assertIn("compareType=sector", response["canonical_url"])
        with self.assertRaisesRegex(ValueError, "two_to_five"):
            compare_groups(self.registry, ["information_technology"], "1M")
        with self.assertRaisesRegex(ValueError, "two_to_five"):
            compare_groups(self.registry, [item["id"] for item in self.registry["items"]] + ["utilities"], "1M")
        partial_registry = {**self.registry, "items": [
            {**self.registry["items"][0], "availability": {"state": "partial", "reason": "partial fixture", "source_state": "test"}},
            {**self.registry["items"][1], "availability": {"state": "stale", "reason": "stale fixture", "source_state": "cached"}},
        ]}
        partial = compare_groups(partial_registry, [partial_registry["items"][1]["id"], partial_registry["items"][0]["id"]], "3M")
        self.assertEqual("partial", partial["status"])
        self.assertEqual([partial_registry["items"][1]["id"], partial_registry["items"][0]["id"]], partial["selected_ids"])
        self.assertEqual(["stale", "partial"], [item["availability"]["state"] for item in partial["items"]])

    def test_combined_filters_reset_and_empty_state(self) -> None:
        combined = filter_groups(self.registry, {"state": "leading", "rank_max": 2, "breadth_min": 60, "movement": "gaining", "strong_movement": True})
        self.assertEqual(["information_technology"], [item["id"] for item in combined["items"]])
        empty = filter_groups(self.registry, {"state": "lagging", "breadth_min": 99})
        self.assertEqual("empty", empty["status"])
        reset = filter_groups(self.registry, {})
        self.assertEqual(self.registry["count"], reset["count"])

    def test_breadth_history_uses_only_published_snapshots(self) -> None:
        for timeframe in ("1M", "3M", "6M", "1Y"):
            response = build_breadth_history("sector", "information_technology", self.sources, timeframe)
            self.assertEqual(["sector-previous", "sector-current"], response["snapshot_ids"])
            self.assertEqual(2, response["observation_count"])
            self.assertEqual("weakening", response["interpretation"]["state"])
            self.assertIn("Only immutable snapshots", response["limitation"])
        unavailable = build_breadth_history("sector", "missing_sector", self.sources, "1M")
        self.assertEqual("unavailable", unavailable["status"])
        self.assertEqual("unavailable", unavailable["interpretation"]["state"])

    def test_all_seven_divergence_cases_are_deterministic(self) -> None:
        item = next(value for value in self.registry["items"] if value["id"] == "information_technology")
        alerts = detect_divergences(item, [
            {"market_date": "2026-07-01", "above_20": 86, "above_50": 78, "advance_decline_ratio": 2.4, "highs_minus_lows": 9},
            {"market_date": "2026-07-22", "above_20": 62, "above_50": 60, "advance_decline_ratio": 1.1, "highs_minus_lows": 1},
        ])
        self.assertEqual({
            "sector_price_rising_participation_weakening",
            "rank_improvement_without_persistence",
            "price_up_breadth_down", "rotation_leading_momentum_fading", "price_up_ad_down",
            "price_up_highs_lows_down", "leadership_concentrated",
        }, {alert["rule_id"] for alert in alerts})
        self.assertEqual(len(alerts), len({alert["id"] for alert in alerts}))
        positive_item = {**item, "performance": {**item["performance"], "1M": -2}, "quadrant": "improving"}
        positive = detect_divergences(positive_item, [
            {"market_date": "2026-07-01", "above_20": 40, "above_50": 38},
            {"market_date": "2026-07-22", "above_20": 62, "above_50": 58},
        ])
        self.assertEqual({"price_down_breadth_up", "rotation_improving_price_weak", "rank_improvement_without_persistence"}, {alert["rule_id"] for alert in positive})
        self.assertEqual(alerts, detect_divergences(item, [
            {"market_date": "2026-07-01", "above_20": 86, "above_50": 78, "advance_decline_ratio": 2.4, "highs_minus_lows": 9},
            {"market_date": "2026-07-22", "above_20": 62, "above_50": 60, "advance_decline_ratio": 1.1, "highs_minus_lows": 1},
        ]))

    def test_required_stage92b_divergence_cases_and_insufficient_states(self) -> None:
        template = next(value for value in self.registry["items"] if value["id"] == "health_care")
        base = {
            **template, "performance": {**template["performance"], "1M": 0}, "quadrant": "neutral",
            "relative_strength": 2, "relative_momentum": 50, "concentration": 30,
            "rank_change": 0, "persistence": {"snapshot_count": 3},
        }
        found: set[str] = set()
        market_up = tuple(SimpleNamespace(close=95 + index * 0.5, session_date=f"2026-07-{index + 1:02d}") for index in range(20))
        market_up_alerts = detect_market_divergence(
            market_up,
            [{"value": 70 - index * 2} for index in range(10)],
            [{"value": 12 - index} for index in range(10)],
        )
        found.update(alert["rule_id"] for alert in market_up_alerts)
        self.assertTrue(all({"id", "entity", "direction", "severity", "detected_at", "evidence", "explanation", "why_it_matters", "confirmation_condition", "invalidation_condition", "confidence", "freshness", "availability", "canonical_destination"}.issubset(alert) for alert in market_up_alerts))
        market_down = tuple(SimpleNamespace(close=110 - index * 0.6, session_date=f"2026-07-{index + 1:02d}") for index in range(20))
        found.update(alert["rule_id"] for alert in detect_market_divergence(
            market_down,
            [{"value": 40 + index * 2} for index in range(10)],
            [{"value": 0} for _ in range(10)],
        ))
        sector = {**base, "type": "sector", "performance": {**base["performance"], "1M": 3}}
        found.update(alert["rule_id"] for alert in detect_divergences(sector, [
            {"market_date": "2026-07-01", "above_20": 70, "above_50": 70},
            {"market_date": "2026-07-22", "above_20": 68, "above_50": 60},
        ]))
        theme = {**base, "type": "theme", "performance": {**base["performance"], "1M": 2}}
        found.update(alert["rule_id"] for alert in detect_divergences(theme, [
            {"market_date": "2026-07-01", "above_20": 70, "above_50": 70, "relative_strength": 1},
            {"market_date": "2026-07-22", "above_20": 68, "above_50": 60, "relative_strength": 4},
        ]))
        rank = {**base, "rank_change": 3, "persistence": {"snapshot_count": 1}}
        found.update(alert["rule_id"] for alert in detect_divergences(rank, [{"market_date": "2026-07-01"}, {"market_date": "2026-07-22"}]))
        momentum = {**base, "relative_strength": -2}
        found.update(alert["rule_id"] for alert in detect_divergences(momentum, [
            {"market_date": "2026-07-01", "relative_momentum": 90},
            {"market_date": "2026-07-22", "relative_momentum": 100},
        ]))
        self.assertTrue({
            "index_rising_breadth_falling", "index_falling_breadth_improving",
            "sector_price_rising_participation_weakening", "theme_relative_strength_rising_breadth_falling",
            "index_high_not_confirmed_by_new_highs", "rank_improvement_without_persistence",
            "momentum_improvement_relative_trend_weak",
        }.issubset(found))
        self.assertEqual([], detect_divergences(base, []))
        self.assertEqual([], detect_divergences(base, [{"market_date": "2026-07-01"}, {"market_date": "2026-07-22"}]))

    def test_sector_alert_contract_declares_and_deduplicates_all_typed_families(self) -> None:
        response = build_sector_alerts(self.registry, self.sources)
        self.assertEqual({
            "entered_leading", "exited_leading", "entered_improving", "breadth_deterioration",
            "momentum_reversal", "relative_strength_breakout", "persistence_loss", "rotation_acceleration",
            "concentration_warning",
        }, set(response["types"]))
        self.assertEqual(len(response["items"]), len({item["id"] for item in response["items"]}))
        self.assertTrue(all(item["canonical_destination"]["route"] == "/sectors" for item in response["items"]))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.reports.research import ResearchCandidateEngine
from app.themes.analytics import THEME_ANALYTICS_VERSION, ThemeAnalyticsEngine
from app.themes.intelligence import ThemeIntelligenceService
from app.themes.launch import (
    LAUNCH_THEMES,
    RETIRED_THEMES,
    TAXONOMY_VERSION,
    THEME_MAPPINGS,
    ThemeRegistry,
    get_launch_theme_registry,
)
from main import app


def series(rate: float, days: int = 260, start: float = 100.0) -> list[float]:
    values = [start]
    for _ in range(days - 1):
        values.append(values[-1] * (1 + rate))
    return values


class EmptySnapshots:
    def latest(self):
        return None

    def history(self, _days: int = 90):
        return []


class ThemeTaxonomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_launch_theme_registry()

    def test_launch_catalog_has_20_to_28_active_themes(self) -> None:
        self.assertGreaterEqual(len(self.registry.launch()), 20)
        self.assertLessEqual(len(self.registry.launch()), 28)

    def test_every_launch_theme_is_versioned_and_sufficiently_mapped(self) -> None:
        for definition in self.registry.launch():
            self.assertEqual(definition.taxonomy_version, TAXONOMY_VERSION)
            self.assertGreaterEqual(len(self.registry.constituents(definition.id)), definition.minimum_constituents)

    def test_retired_theme_is_preserved_but_not_launchable(self) -> None:
        self.assertEqual(RETIRED_THEMES[0].status, "retired")
        self.assertNotIn(RETIRED_THEMES[0], self.registry.launch())

    def test_alias_resolution_and_migration(self) -> None:
        self.assertEqual(self.registry.resolve("memory-and-storage"), "memory_storage")
        self.assertEqual(self.registry.resolve("ai_infrastructure"), "artificial_intelligence")
        self.assertEqual(self.registry.resolve("cloud_data_centers"), "data_centers")

    def test_duplicate_alias_is_detected(self) -> None:
        duplicate = replace(LAUNCH_THEMES[1], id="duplicate_theme", aliases=("ai",))
        issues = ThemeRegistry((*LAUNCH_THEMES, duplicate), THEME_MAPPINGS).validate()
        self.assertIn("duplicate_alias", {item["code"] for item in issues})

    def test_duplicate_theme_id_is_detected(self) -> None:
        issues = ThemeRegistry((*LAUNCH_THEMES, LAUNCH_THEMES[0]), THEME_MAPPINGS).validate()
        self.assertIn("duplicate_theme_id", {item["code"] for item in issues})

    def test_invalid_parent_sector_is_detected(self) -> None:
        invalid = replace(LAUNCH_THEMES[0], id="invalid_parent", aliases=("invalid-parent",), parent_sector_ids=())
        issues = ThemeRegistry((*LAUNCH_THEMES, invalid), THEME_MAPPINGS).validate()
        self.assertIn("invalid_parent_sector", {item["code"] for item in issues})

    def test_launch_registry_has_no_quality_issues(self) -> None:
        self.assertEqual(self.registry.validate(), [])


class ThemeMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_launch_theme_registry()

    def test_all_exposure_levels_are_represented(self) -> None:
        exposures = {item.exposure for item in THEME_MAPPINGS}
        self.assertEqual(exposures, {"core", "significant", "adjacent", "experimental"})

    def test_overlapping_memberships_are_explicit(self) -> None:
        nvda = self.registry.themes_for_symbol("NVDA")
        self.assertGreaterEqual(len(nvda), 2)
        self.assertEqual(nvda[0].exposure, "core")

    def test_diversified_company_is_not_core_everywhere(self) -> None:
        microsoft = self.registry.themes_for_symbol("MSFT")
        self.assertTrue(any(item.exposure in {"significant", "adjacent"} for item in microsoft))

    def test_unknown_symbol_validation_is_available(self) -> None:
        known = {item.symbol for item in THEME_MAPPINGS}
        known.remove("NVDA")
        issues = self.registry.validate(known_symbols=known)
        self.assertIn("unknown_symbol", {item["code"] for item in issues})

    def test_every_mapping_has_complete_provenance(self) -> None:
        for item in THEME_MAPPINGS:
            self.assertTrue(item.mapping_source and item.mapping_method and item.rationale)
            self.assertEqual(item.taxonomy_version, TAXONOMY_VERSION)


class ThemeAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_launch_theme_registry()
        self.engine = ThemeAnalyticsEngine(self.registry)
        self.theme_id = "cybersecurity"
        self.symbols = [item.symbol for item in self.registry.constituents(self.theme_id)]
        self.benchmarks = {"SPY": series(0.0002), "QQQ": series(0.00025), "CIBR": series(0.0003)}

    def histories(self, rate: float = 0.001) -> dict[str, list[float]]:
        return {symbol: series(rate + index * 0.00002) for index, symbol in enumerate(self.symbols)}

    def test_broad_leading_theme(self) -> None:
        result = self.engine.compute(self.theme_id, self.histories(), self.benchmarks, as_of="2026-07-22", source_state="live")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["leadership_state"], "leading")
        self.assertEqual(result["concentration"]["classification"], "broad")

    def test_one_stock_concentration_is_narrow(self) -> None:
        histories = self.histories(0.0001)
        histories[self.symbols[0]] = series(0.02)
        result = self.engine.compute(self.theme_id, histories, self.benchmarks, as_of="2026-07-22", source_state="live")
        self.assertEqual(result["concentration"]["classification"], "narrow")
        self.assertNotEqual(result["leadership_state"], "leading")

    def test_conflicting_momentum_is_preserved(self) -> None:
        histories = self.histories(0.002)
        for symbol in self.symbols:
            histories[symbol][-5:] = [histories[symbol][-6] * (0.995 ** (index + 1)) for index in range(5)]
        result = self.engine.compute(self.theme_id, histories, self.benchmarks, as_of="2026-07-22", source_state="live")
        self.assertEqual(result["momentum"]["agreement"], "conflicting")
        self.assertTrue(result["contradictions"])

    def test_missing_benchmark_reduces_confidence(self) -> None:
        result = self.engine.compute(self.theme_id, self.histories(), {"SPY": self.benchmarks["SPY"]}, as_of="2026-07-22", source_state="live")
        self.assertEqual(result["confidence"]["label"], "limited")
        self.assertTrue(any(item["dimension"] == "benchmarks" for item in result["missing_data"]))

    def test_missing_history_is_partial_or_unavailable(self) -> None:
        histories = {symbol: series(0.001, days=10) for symbol in self.symbols[:3]}
        result = self.engine.compute(self.theme_id, histories, self.benchmarks, as_of="2026-07-22", source_state="partial")
        self.assertIn(result["status"], {"partial", "unavailable"})
        self.assertEqual(result["confidence"]["label"], "limited")

    def test_unavailable_constituents_are_not_ranked_as_zero(self) -> None:
        histories = self.histories()
        histories.pop(self.symbols[-1])
        result = self.engine.compute(self.theme_id, histories, self.benchmarks, as_of="2026-07-22", source_state="partial")
        unavailable = next(item for item in result["constituents"] if item["symbol"] == self.symbols[-1])
        self.assertIsNone(unavailable["rank"])
        self.assertEqual(unavailable["availability"], "unavailable")

    def test_test_data_is_always_labeled(self) -> None:
        result = self.engine.compute(self.theme_id, self.histories(), self.benchmarks, as_of="2026-07-22", source_state="test", test_data=True)
        self.assertEqual(result["test_or_mock_label"], "HERMETIC TEST DATA — NOT LIVE")
        self.assertEqual(result["confidence"]["label"], "limited")

    def test_leadership_transition_and_persistence(self) -> None:
        previous = {"leadership_state": "weakening", "persistence": {"sessions_in_state": 4}, "leaders": []}
        result = self.engine.compute(self.theme_id, self.histories(), self.benchmarks, as_of="2026-07-22", source_state="live", previous_snapshot=previous)
        self.assertEqual(result["persistence"]["sessions_in_state"], 1)
        self.assertIn("leadership_transition", {item["type"] for item in result["change_events"]})

    def test_output_is_versioned_and_evidence_backed(self) -> None:
        result = self.engine.compute(self.theme_id, self.histories(), self.benchmarks, as_of="2026-07-22", source_state="live")
        self.assertEqual(result["analytics_version"], THEME_ANALYTICS_VERSION)
        self.assertEqual(result["taxonomy_version"], TAXONOMY_VERSION)
        self.assertGreaterEqual(len(result["evidence"]), 3)


class ThemeConsumerAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.service = ThemeIntelligenceService(snapshot_service=EmptySnapshots())

    def test_directory_exposes_all_launch_themes_without_mocking_live_data(self) -> None:
        payload = self.service.list_themes()
        self.assertEqual(len(payload["items"]), 26)
        self.assertTrue(all(item["status"] == "unavailable" for item in payload["items"]))

    def test_stock_mapping_returns_primary_and_secondary(self) -> None:
        payload = self.service.mappings_for_symbol("NVDA")
        self.assertEqual(payload["status"], "available")
        self.assertIsNotNone(payload["primary"])
        self.assertTrue(payload["secondary"])

    def test_watchlist_saved_theme_aliases_are_canonical(self) -> None:
        payload = self.service.saved_themes(["memory-and-storage", "memory_storage", "bad-theme"])
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["theme_id"], "memory_storage")
        self.assertEqual(payload["status"], "partial")

    def test_search_uses_aliases_without_duplicates(self) -> None:
        payload = self.service.search("ai")
        ids = [item["id"] for item in payload["items"]]
        self.assertIn("artificial_intelligence", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_api_taxonomy_and_mapping_routes(self) -> None:
        taxonomy = self.client.get("/market/themes/taxonomy").json()
        mapping = self.client.get("/market/themes/mappings/NVDA").json()
        self.assertEqual(taxonomy["taxonomy_version"], TAXONOMY_VERSION)
        self.assertEqual(mapping["status"], "available")

    def test_unknown_api_theme_has_stable_unavailable_contract(self) -> None:
        payload = self.client.get("/market/themes/not-a-theme").json()
        self.assertEqual(payload["status"], "unavailable")
        self.assertIsNone(payload["theme"])
        self.assertNotIn("traceback", json.dumps(payload).lower())

    def test_report_taxonomy_expansion_does_not_select_unavailable_themes(self) -> None:
        rows = self.service.list_themes()["items"]
        report = {"theme_intelligence": {"source_state": "unavailable", "market_date": None, "items": rows}, "research_preferences": {"saved_themes": [rows[0]["theme_id"]]}, "watchlist_summary": {"items": []}}
        result = ResearchCandidateEngine(report).build()
        self.assertEqual(len(result.candidates), 26)
        self.assertIsNone(result.decision.selected_candidate_id)
        self.assertTrue(all(candidate.disqualifying_conditions for candidate in result.candidates))

    def test_all_15_copilot_agents_remain_registered(self) -> None:
        manifest = json.loads((Path(__file__).resolve().parents[2] / "app" / "copilot" / "agent_manifest.json").read_text())
        agents = manifest.get("agents") if isinstance(manifest, dict) else manifest
        self.assertEqual(len(agents), 15)


if __name__ == "__main__":
    unittest.main()

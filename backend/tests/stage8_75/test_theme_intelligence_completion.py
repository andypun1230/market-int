from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.reports.research import ResearchCandidateEngine
from app.market_history.storage import DailyBar, DailyBarStorage
from app.providers.finnhub_provider import ProviderRequestError
from app.providers.polygon_provider import PolygonMarketDataProvider
from app.securities.models import SecurityAlias, SecurityRecord
from app.securities.storage import SecurityMasterStorage
from app.theme_snapshots.builder import ThemeSnapshotBuilder
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.analytics import THEME_ANALYTICS_VERSION, ThemeAnalyticsEngine
from app.themes.intelligence import ThemeIntelligenceService
from app.themes.launch import (
    LAUNCH_THEMES,
    RETIRED_THEMES,
    RETIRED_THEME_MAPPINGS,
    TAXONOMY_VERSION,
    THEME_MAPPINGS,
    ThemeRegistry,
    get_launch_theme_registry,
)
from app.themes.storage import ThemeStorage
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

    def test_verified_successors_replace_only_three_legacy_mapping_rows(self) -> None:
        symbols = {item.symbol for item in THEME_MAPPINGS}
        self.assertEqual(len(THEME_MAPPINGS), 227)
        self.assertTrue({"XYZ", "FISV", "PSKY"}.issubset(symbols))
        self.assertTrue({"SQ", "FI", "PARA"}.isdisjoint(symbols))
        self.assertEqual({item.symbol for item in RETIRED_THEME_MAPPINGS}, {"SQ", "FI", "PARA"})
        self.assertTrue(all(item.effective_to and item.mapping_source and item.rationale for item in RETIRED_THEME_MAPPINGS))

    def test_successor_exposure_and_theme_are_preserved(self) -> None:
        active = {(item.theme_id, item.symbol): item.exposure for item in THEME_MAPPINGS}
        retired = {(item.theme_id, item.symbol): item.exposure for item in RETIRED_THEME_MAPPINGS}
        self.assertEqual(active[("digital_payments", "XYZ")], retired[("digital_payments", "SQ")])
        self.assertEqual(active[("digital_payments", "FISV")], retired[("digital_payments", "FI")])
        self.assertEqual(active[("streaming_digital_entertainment", "PSKY")], retired[("streaming_digital_entertainment", "PARA")])


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

    def test_optional_benchmark_is_disclosed_without_weakening_required_gate(self) -> None:
        result = self.engine.compute(
            self.theme_id, self.histories(), {"SPY": self.benchmarks["SPY"], "XLK": series(0.0001)},
            as_of="2026-07-22", source_state="live", required_benchmark_symbols=("SPY", "XLK"),
        )
        self.assertEqual(result["confidence"]["label"], "moderate")
        self.assertTrue(any(item["dimension"] == "optional_benchmarks" and item["symbols"] == ["QQQ", "CIBR"] for item in result["missing_data"]))

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


class RegistryDrivenSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.db = Path(self.temp.name) / "theme-batch.sqlite3"
        self.old_provider = os.environ.get("DATA_PROVIDER"); self.old_history = os.environ.get("HISTORY_DATA_PROVIDER")
        os.environ["DATA_PROVIDER"] = "finnhub"; os.environ["HISTORY_DATA_PROVIDER"] = "polygon"
        launch = get_launch_theme_registry(); definition = launch.definition("cybersecurity"); assert definition is not None
        mappings = launch.constituents("cybersecurity")
        self.registry = ThemeRegistry((definition,), mappings)
        self.bars = DailyBarStorage(self.db); self.securities = SecurityMasterStorage(self.db)

    def tearDown(self) -> None:
        if self.old_provider is None: os.environ.pop("DATA_PROVIDER", None)
        else: os.environ["DATA_PROVIDER"] = self.old_provider
        if self.old_history is None: os.environ.pop("HISTORY_DATA_PROVIDER", None)
        else: os.environ["HISTORY_DATA_PROVIDER"] = self.old_history
        self.temp.cleanup()

    def seed(self, symbol_count: int) -> None:
        symbols = [item.symbol for item in self.registry.constituents("cybersecurity")]
        for symbol in symbols[:symbol_count]:
            self.securities.upsert_security(SecurityRecord(security_id=f"sec-{symbol}", ticker=symbol, company_name=symbol, sector="Information Technology", sector_id="information_technology", history_provider_symbol=symbol, quote_provider_symbol=symbol, source="reviewed-test", verified_at=date.today().isoformat()))
        rows = []
        for symbol_index, symbol in enumerate([*symbols[:symbol_count], "SPY", "XLK"]):
            for offset in range(260):
                session = date.today() - timedelta(days=259 - offset); close = 100 + symbol_index + offset * .1
                rows.append(DailyBar(symbol, "polygon", session.isoformat(), f"{session.isoformat()}T21:00:00+00:00", close, close, close, close, 1000))
        self.bars.upsert(rows)

    def builder(self) -> ThemeSnapshotBuilder:
        return ThemeSnapshotBuilder(theme_storage=ThemeStorage(self.db), snapshot_storage=ThemeSnapshotStorage(self.db), bars=self.bars, securities=self.securities, registry=self.registry, include_launch_registry=True)

    def test_registry_builder_batches_histories_and_ranks_only_full_rows(self) -> None:
        self.seed(7); snapshot = self.builder().build(publish=False); assert snapshot is not None
        self.assertEqual(len(snapshot.rows), 1); self.assertEqual(snapshot.rows[0]["status"], "available")
        self.assertEqual(snapshot.rankings, ("cybersecurity",)); self.assertEqual(snapshot.repository_stats["batch_history_queries"], 1)
        self.assertEqual(snapshot.repository_stats["single_history_queries"], 0); self.assertEqual(snapshot.repository_stats["provider_history_calls"], 0)
        self.assertEqual(snapshot.coverage_audit[0]["history_21d_count"], 7)

    def test_computable_partial_row_is_persistable_but_unranked(self) -> None:
        self.seed(2); snapshot = self.builder().build(publish=False); assert snapshot is not None
        self.assertEqual(snapshot.rows[0]["status"], "partial"); self.assertIsNone(snapshot.rows[0]["rank"])
        self.assertEqual(snapshot.rankings, ()); self.assertIn("missing_security_master_registration", snapshot.coverage_audit[0]["cause_categories"])

    def test_batch_reader_preserves_explicit_empty_symbols(self) -> None:
        self.seed(1); result = self.bars.histories(("CRWD", "MISSING"))
        self.assertEqual(len(result["CRWD"]), 260); self.assertEqual(result["MISSING"], [])
        self.assertEqual(self.bars.query_statistics["batch_history_queries"], 1); self.assertEqual(self.bars.query_statistics["single_history_queries"], 0)


class FinalCoverageGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[3]
        cls.audit = json.loads((root / "artifacts" / "stage8.75-symbol-coverage-audit.json").read_text())
        cls.refresh = json.loads((root / "artifacts" / "stage8.75-history-refresh.json").read_text())

    def test_symbol_audit_covers_exact_baseline_once(self) -> None:
        rows = self.audit["symbols"]
        self.assertEqual(len(rows), 138)
        self.assertEqual(len({item["symbol"] for item in rows}), 138)
        self.assertTrue(all(isinstance(item["category"]["number"], int) for item in rows))
        self.assertEqual(self.audit["category_counts"], {"2": 129, "4": 2, "6": 2, "7": 1, "8": 4})

    def test_unsupported_instruments_remain_unregistered_by_policy(self) -> None:
        self.assertEqual(self.audit["unsupported_or_not_registered"], ["ABB", "ADYEY", "DESP", "FANUY", "JNPR", "NTDOY"])
        applied = set(self.audit["security_master_apply"]["newly_registered"])
        self.assertTrue(applied.isdisjoint(self.audit["unsupported_or_not_registered"]))

    def test_strict_live_refresh_has_no_failures_or_test_data(self) -> None:
        self.assertTrue(self.refresh["strict_live"])
        self.assertTrue(self.refresh["adjusted_policy"])
        self.assertEqual(self.refresh["failed"], [])
        self.assertEqual(self.refresh["test_or_mock_rows"], 0)
        self.assertEqual(self.refresh["rate_limit_events"], 0)

    def test_all_registered_audit_histories_are_adjusted_and_duplicate_free(self) -> None:
        registered = set(self.audit["security_master_apply"]["newly_registered"])
        rows = [item for item in self.audit["symbols"] if str(item["canonical_symbol"]).split()[0] in registered]
        self.assertTrue(rows)
        self.assertTrue(all(item["history_availability"]["adjusted"] for item in rows))
        self.assertTrue(all(item["history_availability"]["duplicate_sessions"] == 0 for item in rows))
        self.assertTrue(all(item["history_availability"]["history_200d_capable"] for item in rows))

    def test_polygon_reference_audit_seam_normalizes_and_returns_metadata(self) -> None:
        provider = PolygonMarketDataProvider(api_key="test")
        provider._request_paginated_json = lambda path, params: [{"results": {"ticker": "XYZ", "active": True}}]  # type: ignore[method-assign]
        self.assertEqual(provider.get_ticker_details(" xyz ")["ticker"], "XYZ")

    def test_polygon_reference_audit_seam_rejects_empty_results(self) -> None:
        provider = PolygonMarketDataProvider(api_key="test")
        provider._request_paginated_json = lambda path, params: [{"results": {}}]  # type: ignore[method-assign]
        with self.assertRaises(ProviderRequestError):
            provider.get_ticker_details("XYZ")

    def test_security_alias_reverse_lookup_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            storage = SecurityMasterStorage(Path(folder) / "master.sqlite3")
            storage.upsert_security(SecurityRecord("sec-xyz", "XYZ", "Block, Inc.", history_provider_symbol="XYZ"))
            storage.upsert_alias(SecurityAlias("SQ", "sec-xyz", "Block, Inc.", "2025-01-17", "ticker_rename", "same_entity", "approved-test", "2026-07-22"))
            self.assertEqual(storage.security("SQ").ticker, "XYZ")
            self.assertEqual(storage.security("XYZ").security_id, storage.security("SQ").security_id)

    def test_duplicate_alias_owner_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            storage = SecurityMasterStorage(Path(folder) / "master.sqlite3")
            storage.upsert_security(SecurityRecord("sec-a", "AAA", "A"))
            storage.upsert_security(SecurityRecord("sec-b", "BBB", "B"))
            storage.upsert_alias(SecurityAlias("OLD", "sec-a", "A", "2025-01-01", "ticker_rename", "same_entity", "test", "2026-07-22"))
            with self.assertRaises(ValueError):
                storage.upsert_alias(SecurityAlias("OLD", "sec-b", "B", "2025-01-01", "ticker_rename", "same_entity", "test", "2026-07-22"))


if __name__ == "__main__":
    unittest.main()

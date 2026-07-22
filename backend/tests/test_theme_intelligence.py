from __future__ import annotations

import os
import json
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.market_history.storage import DailyBar, DailyBarStorage
from app.market_history.updater import BreadthUniverseHistoryUpdater
from app.providers.models import CandleData, HistoryData
from app.theme_snapshots.builder import ThemeSnapshotBuilder, theme_namespace
from app.theme_snapshots.service import reset_theme_snapshot_service
from app.theme_snapshots.readers import rotation_payload
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.basket import build_equal_weight_basket
from app.themes.engine import build_concentration, build_overlap_matrix, build_participation
from app.themes.models import ThemeDefinition, ThemeMember
from app.themes.policy import validate_definition
from app.themes.service import ThemeDefinitionService
from app.themes.storage import ThemeStorage
from app.themes.identifiers import normalize_theme_id
from app.securities.models import SecurityAlias, SecurityProviderSymbol, SecurityRecord
from app.securities.service import reset_security_master_service
from app.securities.storage import SecurityMasterStorage
from app.services.background_refresh import reset_background_refresh_state
from app.services.theme_intelligence import decision_theme_signal, enrich_copilot_theme_context
from app.themes.registry import read_definition_markdown, read_members_csv


def definition(theme_id: str = "memory_storage", *, status: str = "active") -> ThemeDefinition:
    return ThemeDefinition(
        theme_id=theme_id, display_name="Memory & Storage", description="Deterministic test definition.", version="v1", status=status, effective_from="2025-01-01", methodology="reviewed current basket", inclusion_criteria="test", exclusion_criteria="test", weighting_policy="equal_weight_v1", primary_benchmark="SPY", secondary_benchmark="XLK", parent_sector_ids=("information_technology",), minimum_members=4, complete_coverage_threshold=.9, partial_coverage_threshold=.75, source_references=({"title": "test", "url": "https://example.test", "retrieved_at": "2025-01-01"},), verification_date="2025-01-01", reviewed_at="2025-01-01", reviewed_by="human-reviewer",
    )


def members(theme_id: str = "memory_storage") -> list[ThemeMember]:
    return [ThemeMember(theme_id=theme_id, theme_version="v1", ticker=ticker, security_id=f"sec-{ticker}", company_name=ticker, role="core", weight=.25, effective_from="2025-01-01", active=True, membership_source="reviewed-test", inclusion_reason="Reviewed deterministic test constituent.", reviewed_at="2025-01-01", reviewed_by="human-reviewer") for ticker in ("AAA", "BBB", "CCC", "DDD")]


def bars(ticker: str, *, start: float, step: float, sessions: int = 310) -> list[DailyBar]:
    start_date = date(2025, 1, 2)
    result = []
    for offset in range(sessions):
        close = start + step * offset
        session = (start_date + timedelta(days=offset)).isoformat()
        result.append(DailyBar(ticker=ticker, provider="polygon", session_date=session, timestamp=f"{session}T00:00:00+00:00", open=close, high=close, low=close, close=close, volume=1000.0, adjusted=True))
    return result


class ThemeIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.db_path = Path(self.temp.name) / "themes.sqlite3"; self.old_db = os.environ.get("BREADTH_DB_PATH"); self.old_provider = os.environ.get("DATA_PROVIDER"); self.old_history_provider = os.environ.get("HISTORY_DATA_PROVIDER"); self.old_background_refresh = os.environ.get("BACKGROUND_REFRESH_ENABLED"); self.old_startup_refresh = os.environ.get("STARTUP_REFRESH_MODE")
        os.environ["BREADTH_DB_PATH"] = str(self.db_path); os.environ["DATA_PROVIDER"] = "test"; os.environ["HISTORY_DATA_PROVIDER"] = "polygon"; os.environ["BACKGROUND_REFRESH_ENABLED"] = "false"; os.environ["STARTUP_REFRESH_MODE"] = "none"; reset_theme_snapshot_service(); reset_background_refresh_state()
        reset_security_master_service()
        self.theme_storage = ThemeStorage(self.db_path); self.bar_storage = DailyBarStorage(self.db_path); self.snapshot_storage = ThemeSnapshotStorage(self.db_path)

    def tearDown(self) -> None:
        if self.old_db is None: os.environ.pop("BREADTH_DB_PATH", None)
        else: os.environ["BREADTH_DB_PATH"] = self.old_db
        if self.old_provider is None: os.environ.pop("DATA_PROVIDER", None)
        else: os.environ["DATA_PROVIDER"] = self.old_provider
        if self.old_history_provider is None: os.environ.pop("HISTORY_DATA_PROVIDER", None)
        else: os.environ["HISTORY_DATA_PROVIDER"] = self.old_history_provider
        if self.old_background_refresh is None: os.environ.pop("BACKGROUND_REFRESH_ENABLED", None)
        else: os.environ["BACKGROUND_REFRESH_ENABLED"] = self.old_background_refresh
        if self.old_startup_refresh is None: os.environ.pop("STARTUP_REFRESH_MODE", None)
        else: os.environ["STARTUP_REFRESH_MODE"] = self.old_startup_refresh
        reset_theme_snapshot_service(); reset_background_refresh_state()
        reset_security_master_service()
        self.temp.cleanup()

    def test_proposed_definition_cannot_pass_review_gate(self) -> None:
        proposed = definition(status="proposed")
        errors = validate_definition(proposed, members(), require_reviewed=True)
        self.assertIn("definition_not_reviewed", errors)

    def test_theme_id_aliases_are_canonical_and_unknown_is_rejected(self) -> None:
        self.assertEqual(normalize_theme_id("memory_storage"), "memory_storage")
        self.assertEqual(normalize_theme_id("memory-storage"), "memory_storage")
        with self.assertRaisesRegex(ValueError, "unknown_theme_id"):
            normalize_theme_id("Memory & Storage")

    def test_aliases_do_not_create_duplicate_persisted_definitions(self) -> None:
        self.theme_storage.save_definition(definition("memory-storage"), members("memory-storage"))
        self.theme_storage.save_definition(definition("memory_storage"), members("memory_storage"))
        definitions = self.theme_storage.definitions()
        self.assertEqual([item.theme_id for item in definitions], ["memory_storage"])
        self.assertIsNotNone(self.theme_storage.definition("memory-storage", "v1"))

    def test_initialize_migrates_legacy_kebab_primary_keys_without_duplicates(self) -> None:
        legacy_path = Path(self.temp.name) / "legacy-theme.sqlite3"
        storage = ThemeStorage(legacy_path); storage.initialize()
        legacy_definition = definition("memory-storage"); legacy_members = members("memory-storage")
        definition_payload = json.dumps(legacy_definition.model_dump(), sort_keys=True)
        with sqlite3.connect(legacy_path) as connection:
            connection.execute("INSERT INTO theme_definitions VALUES (?, ?, ?, ?, ?, ?, datetime('now'))", ("memory-storage", "v1", legacy_definition.status, legacy_definition.effective_from, definition_payload, hashlib.sha256(definition_payload.encode()).hexdigest()))
            for member in legacy_members:
                payload = json.dumps(member.model_dump(), sort_keys=True)
                connection.execute("INSERT INTO theme_members VALUES (?, ?, ?, ?, ?, ?)", ("memory-storage", "v1", member.ticker, int(member.active), payload, hashlib.sha256(payload.encode()).hexdigest()))
        migrated = ThemeStorage(legacy_path)
        self.assertEqual(migrated.definition("memory_storage", "v1").theme_id, "memory_storage")
        self.assertEqual([member.theme_id for member in migrated.members("memory_storage", "v1")], ["memory_storage"] * 4)
        with sqlite3.connect(legacy_path) as connection:
            self.assertEqual(connection.execute("SELECT theme_id FROM theme_definitions").fetchall(), [("memory_storage",)])
            self.assertEqual(connection.execute("SELECT DISTINCT theme_id FROM theme_members").fetchall(), [("memory_storage",)])

    def test_fixture_pins_history_namespace_after_external_test_state(self) -> None:
        self.assertEqual(theme_namespace(), "test:polygon:themes")

    def test_member_validation_rejects_duplicate_and_weight_mutation(self) -> None:
        values = members(); duplicate = [*values, values[0]]
        self.assertIn("duplicate_active_member", validate_definition(definition(), duplicate, require_reviewed=True))
        invalid = [*values[:-1], ThemeMember(**{**values[-1].model_dump(), "weight": .2})]
        self.assertIn("member_weights_must_sum_to_one", validate_definition(definition(), invalid, require_reviewed=True))

    def test_definition_versions_are_immutable(self) -> None:
        self.theme_storage.save_definition(definition(), members())
        changed = ThemeDefinition(**{**definition().model_dump(), "description": "changed"})
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.theme_storage.save_definition(changed, members())

    def test_current_active_definition_selects_correction_without_mutating_prior_version(self) -> None:
        original = definition(); original_members = members()
        corrected = ThemeDefinition(**{
            **original.model_dump(), "version": "v1.2", "amends_version": "v1",
            "amendment_reason": "reviewed metadata correction", "correction_metadata": {
                "methodology_changed": False, "membership_changed": False, "weighting_changed": False,
            },
        })
        corrected_members = [ThemeMember(**{**member.model_dump(), "theme_version": "v1.2", "purity": 100, "importance": None}) for member in original_members]
        self.theme_storage.save_definition(original, original_members)
        self.theme_storage.save_definition(corrected, corrected_members)
        active = ThemeDefinitionService(self.theme_storage).active()
        self.assertEqual([item[0].version for item in active], ["v1.2"])
        self.assertEqual(self.theme_storage.definition("memory_storage", "v1").model_dump()["correction_metadata"], {})
        self.assertEqual(self.theme_storage.members("memory_storage", "v1")[0].purity, None)
        self.assertEqual(self.theme_storage.members("memory_storage", "v1.2")[0].purity, 100)

    def test_unqualified_live_theme_is_not_recast_as_static_preference(self) -> None:
        row = {
            "theme_id": "cybersecurity", "display_name": "Cybersecurity", "coverage_ratio": 1.0,
            "composite_score": 100.0, "classification": "Leading", "signal_confidence": {"score": 90},
            "data_confidence": {"score": 90}, "concentration": {"classification": "high"},
        }
        signal = decision_theme_signal(SimpleNamespace(snapshot_id="theme-test", status="complete"), row)
        self.assertEqual(signal["source_type"], "live_theme_signal")
        self.assertFalse(signal["qualified"])
        self.assertIn("concentration is high", signal["disqualification_reason"])

    def test_copilot_theme_context_resolves_live_theme_without_legacy_members(self) -> None:
        live = {
            "available": True, "snapshot_id": "theme-test", "market_date": "2026-07-17", "source_state": "live",
            "overlap_matrix": [],
            "items": [{
                "theme_id": "cybersecurity", "display_name": "Cybersecurity", "version": "v1.2", "rank": 1,
                "classification": "Leading", "composite_score": 100.0, "performance": {}, "relative_strength": {},
                "breadth": {}, "participation": {}, "concentration": {"top_contributors": []}, "coverage_ratio": 1.0,
                "signal_confidence": {}, "data_confidence": {}, "representativeness": {}, "members": [{"ticker": "CRWD"}, {"ticker": "S"}],
                "warnings": [], "basket_methodology": {}, "score_semantics": {}, "definition": {"parent_sector_labels": ["Information Technology"]},
            }],
        }
        with patch("app.services.theme_intelligence.build_theme_intelligence_context", return_value=live):
            context = enrich_copilot_theme_context("Why is cybersecurity leading?", {"screenType": "general", "sourceState": "live"})
        focused = context["theme"]["focused"]
        self.assertEqual(focused["snapshot_id"], "theme-test")
        self.assertEqual(focused["theme_id"], "cybersecurity")
        self.assertNotIn("CYBR", [member["ticker"] for member in focused["members"]])
        self.assertNotIn("PSTG", [member["ticker"] for member in focused["members"]])

    def test_equal_weight_basket_and_coverage(self) -> None:
        values = members(); histories = {"AAA": tuple(bars("AAA", start=100, step=1, sessions=3)), "BBB": tuple(bars("BBB", start=100, step=2, sessions=3)), "CCC": tuple(bars("CCC", start=100, step=3, sessions=3)), "DDD": tuple(bars("DDD", start=100, step=4, sessions=3))}
        basket = build_equal_weight_basket(definition(), values, histories, source_state="test")
        self.assertEqual(len(basket), 2); self.assertAlmostEqual(basket[0].daily_return, .025, places=8); self.assertEqual(basket[0].eligible_members, 4); self.assertEqual(basket[0].total_members, 4)

    def test_participation_is_not_ema50_alias_and_concentration_is_bounded(self) -> None:
        values = members(); histories = {member.ticker: tuple(bars(member.ticker, start=100, step=1 if member.ticker in {"AAA", "BBB"} else -.1)) for member in values}
        participation = build_participation(values, histories, 21); concentration = build_concentration(values, histories, 21)
        self.assertIn("positive_contribution_share", participation); self.assertIn("distinct from EMA50 breadth", participation["definition"])
        self.assertGreaterEqual(concentration["contribution_hhi"], 0); self.assertLessEqual(concentration["contribution_hhi"], 1); self.assertEqual(concentration["denominator"], "absolute contribution share")

    def test_overlap_is_explicit(self) -> None:
        first = {"theme_id": "one", "members": [{"ticker": "AAA", "weight": .5}, {"ticker": "BBB", "weight": .5}]}; second = {"theme_id": "two", "members": [{"ticker": "BBB", "weight": .5}, {"ticker": "CCC", "weight": .5}]}
        overlap = build_overlap_matrix([first, second])[0]
        self.assertEqual(overlap["common_members"], ["BBB"]); self.assertAlmostEqual(overlap["jaccard_overlap"], 1 / 3, places=6); self.assertAlmostEqual(overlap["weighted_overlap"], .5)

    def test_snapshot_is_published_from_reviewed_durable_bars_and_rotation_is_real(self) -> None:
        values = members(); self.theme_storage.save_definition(definition(), values)
        daily = bars("SPY", start=400, step=.5)
        for index, member in enumerate(values): daily.extend(bars(member.ticker, start=100 + index, step=.6 + index * .1))
        self.bar_storage.upsert(daily)
        builder = ThemeSnapshotBuilder(theme_storage=self.theme_storage, snapshot_storage=self.snapshot_storage, bars=self.bar_storage)
        snapshot = builder.build()
        self.assertIsNotNone(snapshot); assert snapshot is not None
        self.assertEqual(snapshot.status, "complete"); self.assertEqual(snapshot.rows[0]["theme_id"], "memory_storage")
        row = snapshot.rows[0]
        self.assertEqual(row["score_semantics"]["score_type"], "absolute_weighted_composite")
        self.assertEqual(row["composite_score"], round(sum(item["weighted_contribution"] for item in row["weighted_contributions"].values()), 2))
        self.assertIn("positive_return_member_count", row["participation"])
        self.assertIn("concentration_quality_score", row["concentration"])
        rotation = rotation_payload(snapshot, "1m"); self.assertTrue(rotation["current_positions_available"]); self.assertEqual(rotation["current_point_count"], 1)
        series = rotation["series"][0]; self.assertEqual(series["current_point"], series["trail_points"][-1]); self.assertFalse(any(point["is_synthetic"] for point in series["trail_points"]))

    def test_unavailable_snapshot_preserves_no_live_fixture(self) -> None:
        builder = ThemeSnapshotBuilder(theme_storage=self.theme_storage, snapshot_storage=self.snapshot_storage, bars=self.bar_storage)
        self.assertIsNone(builder.build()); self.assertEqual(self.snapshot_storage.state("test:polygon:themes", "last_error"), "no_reviewed_active_theme_definitions")

    def test_status_endpoint_is_gated_and_does_not_need_provider_history(self) -> None:
        for ticker in ("MU", "PANW", "CRWD", "FTNT", "ZS"):
            SecurityMasterStorage(self.db_path).upsert_security(SecurityRecord(security_id=f"status-{ticker}", ticker=ticker, company_name=ticker, sector="Technology", sector_id="information_technology", history_provider_symbol=ticker, quote_provider_symbol=ticker))
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from main import app
        with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("status called provider")) as provider, patch("app.theme_snapshots.builder.ThemeSnapshotBuilder.build", side_effect=AssertionError("status built a snapshot")) as build:
            response = client.get("/market/themes/status")
        payload = response.json()
        self.assertEqual(response.status_code, 200); self.assertEqual(payload["status"], "awaiting_snapshot")
        self.assertEqual(payload["proposed_definition_count"], 6); self.assertEqual(payload["reviewed_definition_count"], 2); self.assertEqual(payload["active_definition_count"], 0)
        self.assertFalse(payload["published_snapshot"]); self.assertEqual(provider.call_count, 0); self.assertEqual(build.call_count, 0)
        memory = next(item for item in payload["pilot_themes"] if item["theme_id"] == "memory_storage")
        self.assertIn("P", memory["missing_security_records"])
        self.assertNotIn(str(self.db_path), json.dumps(payload))

    def test_background_refresh_skips_snapshot_build_until_definitions_are_reviewed(self) -> None:
        from app.services.background_refresh import refresh_theme_snapshot
        from unittest.mock import Mock, patch
        service = Mock(); service.status.return_value = {"reviewed_definition_count": 0}
        with patch("app.theme_snapshots.service.get_theme_snapshot_service", return_value=service):
            result = refresh_theme_snapshot()
        self.assertEqual(result, {"status": "skipped", "reason_code": "human_review_required"})
        service.build_now.assert_not_called()

    def test_snapshot_storage_and_query_emit_canonical_ids_for_legacy_aliases(self) -> None:
        values = members(); self.theme_storage.save_definition(definition(), values)
        daily = bars("SPY", start=400, step=.5)
        for index, member in enumerate(values): daily.extend(bars(member.ticker, start=100 + index, step=.6 + index * .1))
        self.bar_storage.upsert(daily)
        snapshot = ThemeSnapshotBuilder(theme_storage=self.theme_storage, snapshot_storage=self.snapshot_storage, bars=self.bar_storage).build()
        assert snapshot is not None
        legacy = replace(
            snapshot,
            snapshot_id="theme-legacy-alias",
            active_theme_versions=tuple({**item, "theme_id": "memory-storage"} for item in snapshot.active_theme_versions),
            member_coverage={"memory-storage": next(iter(snapshot.member_coverage.values()))},
            rows=tuple({**row, "theme_id": "memory-storage"} for row in snapshot.rows),
            rankings=("memory-storage",),
        )
        self.snapshot_storage.publish(legacy, theme_namespace())
        restored = self.snapshot_storage.latest(theme_namespace())
        assert restored is not None
        self.assertEqual(restored.rows[0]["theme_id"], "memory_storage")
        self.assertEqual(restored.rankings, ("memory_storage",))
        from fastapi.testclient import TestClient
        from main import app
        reset_theme_snapshot_service()
        with TestClient(app) as client:
            response = client.get("/market/themes/memory-storage")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["canonical_theme_id"], "memory_storage")
        self.assertEqual(response.json()["theme"]["theme_id"], "memory_storage")

    def test_importer_alias_reaches_human_review_gate_and_genuine_mismatch_fails(self) -> None:
        root = Path(__file__).resolve().parents[1]
        output = Path(self.temp.name) / "import.json"
        command = [sys.executable, "scripts/import_theme_definitions.py", "--theme", "memory-storage", "--definition-file", "data/reference/themes/memory-storage-v1.md", "--members-file", "data/reference/themes/memory-storage-v1.csv", "--version", "v1", "--dry-run", "--json-output", str(output)]
        result = subprocess.run(command, cwd=root, env={**os.environ, "BREADTH_DB_PATH": str(self.db_path)}, capture_output=True, text=True)
        report = json.loads(output.read_text())
        self.assertEqual(result.returncode, 0); self.assertEqual(report["theme_id"], "memory_storage")
        self.assertEqual(report["reason_code"], "human_review_required"); self.assertFalse(report["applied"])
        mismatch = subprocess.run([*command[:3], "cybersecurity", *command[4:]], cwd=root, env={**os.environ, "BREADTH_DB_PATH": str(self.db_path)}, capture_output=True, text=True)
        self.assertEqual(mismatch.returncode, 2); self.assertIn("theme_id_mismatch", mismatch.stdout)

    def test_provenance_audit_writes_json_and_markdown_and_rejects_unknown_when_requested(self) -> None:
        root = Path(__file__).resolve().parents[1]; report_path = Path(self.temp.name) / "provenance.json"; markdown_path = Path(self.temp.name) / "provenance.md"
        result = subprocess.run([sys.executable, "scripts/audit_theme_provenance.py", "--all-themes", "--mode", "all", "--json-output", str(report_path), "--markdown-output", str(markdown_path)], cwd=root, env={**os.environ, "BREADTH_DB_PATH": str(self.db_path)}, capture_output=True, text=True)
        report = json.loads(report_path.read_text())
        self.assertEqual(result.returncode, 0); self.assertEqual(report["overall_result"], "PASS")
        self.assertEqual(report["definitions_found"], 10); self.assertTrue(markdown_path.exists())
        unknown = subprocess.run([sys.executable, "scripts/audit_theme_provenance.py", "--theme", "not-a-theme", "--fail-on-unknown"], cwd=root, env={**os.environ, "BREADTH_DB_PATH": str(self.db_path)}, capture_output=True, text=True)
        self.assertEqual(unknown.returncode, 1); self.assertIn("unknown_theme_provenance", unknown.stdout)


class PstgCorporateActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "pstg-p.sqlite3"
        self.security_storage = SecurityMasterStorage(self.db_path)
        self.bar_storage = DailyBarStorage(self.db_path)
        self.security = SecurityRecord(
            security_id="everpure-1474432", ticker="P", company_name="Everpure", exchange="NYSE",
            sector="Information Technology", sector_id="information_technology", history_provider_symbol="P", quote_provider_symbol="P",
            effective_from="2026-04-17", source="test", verified_at="2026-07-19T18:11:25Z",
        )
        self.security_storage.upsert_security(self.security)
        self.security_storage.upsert_alias(SecurityAlias(
            alias_ticker="PSTG", security_id=self.security.security_id, former_company_name="Pure Storage", effective_to="2026-04-16",
            corporate_action_type="ticker_and_name_change", continuity_status="verified", source="test", verified_at="2026-07-19T18:11:25Z",
        ))
        self.segments = [
            SecurityProviderSymbol(self.security.security_id, "polygon", "history", "PSTG", "1900-01-01", "2026-04-16", "test", "2026-07-19T18:11:25Z", "PSTG_to_P_same_issuer_verified"),
            SecurityProviderSymbol(self.security.security_id, "polygon", "history", "P", "2026-04-17", None, "test", "2026-07-19T18:11:25Z", "PSTG_to_P_same_issuer_verified"),
        ]
        for segment in self.segments:
            self.security_storage.upsert_provider_symbol(segment)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_canonical_identity_and_date_aware_symbol_resolution(self) -> None:
        self.assertEqual(self.security_storage.security("P").security_id, self.security.security_id)
        self.assertEqual(self.security_storage.security("PSTG").ticker, "P")
        self.assertEqual([alias.alias_ticker for alias in self.security_storage.aliases("P")], ["PSTG"])
        self.assertEqual(self.security_storage.provider_symbol_for("P", on_date="2026-04-16").provider_symbol, "PSTG")
        self.assertEqual(self.security_storage.provider_symbol_for("PSTG", on_date="2026-04-17").provider_symbol, "P")

    def test_alias_collision_and_unresolved_identity_are_rejected(self) -> None:
        self.security_storage.upsert_security(SecurityRecord(security_id="other", ticker="OTHER", company_name="Other", sector="Information Technology", sector_id="information_technology"))
        with self.assertRaisesRegex(ValueError, "historical_alias_collides"):
            self.security_storage.upsert_alias(SecurityAlias("OTHER", self.security.security_id, None, "2026-04-16", "ticker_and_name_change", "verified", "test", "2026-07-19T18:11:25Z"))
        unresolved = SecurityProviderSymbol("missing", "polygon", "history", "MISSING", "2026-01-01", None, "test", "2026-07-19T18:11:25Z")
        with self.assertRaisesRegex(ValueError, "security_not_found"):
            self.security_storage.upsert_provider_symbol(unresolved)

    def test_history_stitches_once_with_source_provenance_and_no_synthetic_boundary(self) -> None:
        provider = _StitchProvider({
            "PSTG": [
                _candle("2026-04-15", 64.89), _candle("2026-04-16", 67.80),
            ],
            "P": [
                _candle("2026-04-17", 66.97), _candle("2026-04-20", 68.00),
            ],
        })
        report = BreadthUniverseHistoryUpdater(storage=self.bar_storage, repository=provider).update_symbol_history_segments(
            "P", security_id=self.security.security_id, segments=self.segments, strict_live=True,
        )
        history = self.bar_storage.history("P")
        self.assertEqual([bar.session_date for bar in history], ["2026-04-15", "2026-04-16", "2026-04-17", "2026-04-20"])
        self.assertEqual([bar.source_symbol for bar in history], ["PSTG", "PSTG", "P", "P"])
        self.assertEqual({bar.canonical_security_id for bar in history}, {self.security.security_id})
        self.assertEqual(report["stitching"]["duplicate_count"], 0)
        transition = report["stitching"]["transitions"][0]
        self.assertEqual(transition["gap_count"], 0)
        self.assertFalse(transition["synthetic_return"])
        self.assertAlmostEqual(transition["boundary_return"], 66.97 / 67.80 - 1, places=8)
        self.assertEqual(provider.calls, ["PSTG", "P"])
        self.security_storage.provider_symbol_for("PSTG", on_date="2026-04-16")
        self.assertEqual(provider.calls, ["PSTG", "P"], "warm alias lookup must not call a provider")

    def test_stitched_resume_reuses_closed_ticker_era(self) -> None:
        provider = _StitchProvider({
            "PSTG": [_candle("2026-04-15", 64.89), _candle("2026-04-16", 67.80)],
            "P": [_candle("2026-04-17", 66.97), _candle("2026-04-20", 68.00)],
        })
        updater = BreadthUniverseHistoryUpdater(storage=self.bar_storage, repository=provider)
        updater.update_symbol_history_segments("P", security_id=self.security.security_id, segments=self.segments, strict_live=True)
        report = updater.update_symbol_history_segments("P", security_id=self.security.security_id, segments=self.segments, strict_live=True)
        self.assertEqual(provider.calls, ["PSTG", "P", "P"])
        self.assertTrue(report["source_symbols"][0]["skipped_closed_era"])
        self.assertEqual(report["source_symbols"][0]["requested_days"], 0)
        self.assertEqual(len(self.bar_storage.history("P")), 4)

    def test_reviewed_package_has_one_current_everpure_member_and_seven_equal_weights(self) -> None:
        root = Path(__file__).resolve().parents[1] / "data" / "reference" / "themes"
        definition = read_definition_markdown(root / "memory-storage-v1.1.md")
        values = read_members_csv(root / "memory-storage-v1.1.csv", definition)
        self.assertEqual(definition.version, "v1.1")
        self.assertTrue(definition.corporate_action_amendment)
        self.assertEqual([member.ticker for member in values], ["MU", "SNDK", "WDC", "STX", "MRVL", "NTAP", "P"])
        self.assertNotIn("PSTG", [member.ticker for member in values])
        self.assertAlmostEqual(sum(member.weight for member in values), 1.0, places=8)
        p_member = next(member for member in values if member.ticker == "P")
        self.assertEqual((p_member.company_name, p_member.role, p_member.purity, p_member.importance), ("Everpure", "infrastructure", 90, 6))
        self.assertEqual((p_member.previous_ticker, p_member.previous_company_name, p_member.continuity_status), ("PSTG", "Pure Storage", "verified"))


class _StitchProvider:
    def __init__(self, candles: dict[str, list[CandleData]]) -> None:
        self.candles = candles
        self.calls: list[str] = []

    def get_provider_for(self, _capability: str) -> "_StitchProvider":
        return self

    def get_history(self, symbol: str, resolution: str = "D", days: int = 450) -> HistoryData:
        self.calls.append(symbol)
        return HistoryData(symbol=symbol, candles=self.candles[symbol], timeframe=resolution, source="polygon", is_live=True, is_stale=False, fallback_used=False, as_of="2026-07-19T18:11:25Z", provider="polygon", source_state="live", adjusted=True)


def _candle(session_date: str, close: float) -> CandleData:
    return CandleData(timestamp=f"{session_date}T00:00:00+00:00", open=close, high=close, low=close, close=close, volume=1000.0)


if __name__ == "__main__": unittest.main()

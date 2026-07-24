from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.theme_snapshots.models import ThemeSnapshot
from app.theme_snapshots.readers import rotation_payload, rotation_summary_payload
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.intelligence import ThemeIntelligenceService
from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry
from app.themes.storage import ThemeStorage


def fixture_snapshot() -> ThemeSnapshot:
    previous = {
        "market_date": "2026-07-21",
        "relative_trend": 101.0,
        "relative_momentum": 100.5,
        "plotted_x": 101.0,
        "plotted_y": 100.5,
        "raw_rs": 1.01,
        "confidence": {"label": "moderate"},
        "coverage_ratio": 1.0,
        "source_series_ids": ["theme:memory_storage:rotation:1M"],
        "is_synthetic": False,
    }
    current = {
        **previous,
        "market_date": "2026-07-22",
        "relative_trend": 102.0,
        "relative_momentum": 101.5,
        "plotted_x": 102.0,
        "plotted_y": 101.5,
        "raw_rs": 1.02,
    }
    series = {
        "trail_points": [previous, current],
        "current_point": current,
        "direction": "north-east",
        "speed": 1.4,
        "distance_travelled": 1.4,
        "net_displacement": 1.4,
        "recent_acceleration": 0.1,
        "quadrant_transitions": 0,
        "confidence": {"label": "moderate"},
        "formula_version": "theme-relative-trend-momentum-v1",
        "model_id": "theme-relative-trend-momentum",
        "model_version": "theme-relative-trend-momentum-v1",
        "normalization_version": "zero-centered-rolling-robust-scale-v1",
        "normalization_metadata": {"window": 60},
    }
    row = {
        "theme_id": "memory_storage",
        "display_name": "Memory & Storage",
        "status": "available",
        "source_state": "live",
        "coverage_status": "complete",
        "coverage_ratio": 1.0,
        "rank": 1,
        "classification": "Leading",
        "composite_score": 82.5,
        "member_count": 4,
        "performance": {"1d": 0.5, "1w": 1.2, "1m": 3.4, "3m": 7.8, "6m": 9.0, "1y": 14.0},
        "participation": {"participation_score": 80.0},
        "concentration": {"concentration_quality_score": 75.0},
        "score_semantics": {"display_label": "Absolute composite score"},
        "confidence": {"label": "moderate"},
        "freshness": {"state": "live", "market_date": "2026-07-22"},
        "missing_data": [],
        "warnings": [],
        "members": [{"ticker": "AAA", "company_name": "AAA"}],
        "evidence": [{"evidence_id": "theme:memory_storage:evidence:1"}],
        "provenance": {"source_state": "live", "model_version": "theme-leadership-composite-v1"},
        "rotation_series": {"1M": series},
        "definition": {
            "id": "memory_storage",
            "name": "Memory & Storage",
            "aliases": ["memory-and-storage"],
            "parent_sector_ids": ["information_technology"],
            "status": "active",
        },
    }
    return ThemeSnapshot(
        snapshot_id="theme-stage12-2",
        schema_version=1,
        market_date="2026-07-22",
        generated_at="2026-07-22T21:00:00Z",
        published_at="2026-07-22T21:00:00Z",
        status="available",
        source_state="live",
        active_theme_versions=(),
        member_coverage={},
        providers=("polygon",),
        rows=(row,),
        rankings=("memory_storage",),
        rotation_summary="Available",
        overlap_matrix=({"left_theme_id": "memory_storage", "right_theme_id": "semiconductors"},),
        taxonomy_version=TAXONOMY_VERSION,
    )


class Stage122PerformanceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = fixture_snapshot()
        snapshots = SimpleNamespace(latest=lambda: self.snapshot, history=lambda _days=90: [])
        self.service = ThemeIntelligenceService(
            registry=get_launch_theme_registry(),
            snapshot_service=snapshots,
        )

    def test_directory_projection_omits_detail_fields_and_detail_preserves_them(self) -> None:
        summary = next(item for item in self.service.list_themes()["items"] if item["theme_id"] == "memory_storage")
        detail = self.service.current("memory_storage")
        for field in ("members", "evidence", "provenance", "rotation_series"):
            self.assertNotIn(field, summary)
            self.assertIn(field, detail["theme"])
        self.assertEqual(detail["snapshot_id"], self.service.list_themes()["snapshot_id"])
        self.assertEqual(detail["taxonomy_version"], summary["taxonomy_version"])
        self.assertEqual(detail["contract"], "theme_detail_v1")

    def test_rotation_summary_preserves_coordinates_without_duplicate_series(self) -> None:
        full = rotation_payload(self.snapshot, "1M")
        compact = rotation_summary_payload(self.snapshot, "1M")
        self.assertEqual(compact["contract"], "theme_rotation_summary_v1")
        self.assertNotIn("series", compact)
        self.assertNotIn("tails", compact)
        self.assertNotIn("current_point", compact["points"][0])
        for field in ("snapshot_id", "taxonomy_version", "rotation_model_version", "timeframe"):
            self.assertEqual(compact[field], full[field])
        for field in ("theme_id", "relative_trend", "relative_momentum", "rank", "confidence", "trail_points"):
            self.assertEqual(compact["points"][0][field], full["points"][0][field])

    def test_contract_payloads_remain_below_hard_compressed_budgets(self) -> None:
        summary = self.service.list_themes()
        rotation = rotation_summary_payload(self.snapshot, "1M")
        self.assertLess(len(gzip.compress(json.dumps(summary).encode())), 1_000_000)
        self.assertLess(len(gzip.compress(json.dumps(rotation).encode())), 500_000)

    def test_storage_migrations_run_once_per_storage_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            theme_snapshot_storage = ThemeSnapshotStorage(Path(directory) / "snapshots.sqlite3")
            with patch.object(
                theme_snapshot_storage,
                "_migrate_legacy_payloads",
                wraps=theme_snapshot_storage._migrate_legacy_payloads,
            ) as snapshot_migration:
                theme_snapshot_storage.initialize()
                theme_snapshot_storage.initialize()
                self.assertEqual(snapshot_migration.call_count, 1)

            theme_storage = ThemeStorage(Path(directory) / "themes.sqlite3")
            with patch.object(
                theme_storage,
                "_migrate_legacy_ids",
                wraps=theme_storage._migrate_legacy_ids,
            ) as theme_migration:
                theme_storage.initialize()
                theme_storage.initialize()
                self.assertEqual(theme_migration.call_count, 1)


if __name__ == "__main__":
    unittest.main()

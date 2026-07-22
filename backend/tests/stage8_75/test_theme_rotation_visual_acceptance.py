from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION
from app.rotation.visual_acceptance import (
    REPOSITORY_ROOT,
    REQUIRED_THEME_ROTATION_SCREENSHOTS,
    REQUIRED_THEME_ROTATION_VISUAL_CHECKS,
    THEME_ROTATION_VISUAL_ACCEPTANCE_PATH,
    inspect_theme_rotation_visual_acceptance,
    require_theme_rotation_visual_acceptance,
)
from app.themes.intelligence import get_theme_intelligence_service
from scripts.regenerate_stage8_75_theme_rotation_visual_acceptance import (
    EXPECTED_SCREENSHOT_DIMENSIONS,
    regenerate_visual_acceptance,
)
from scripts.validate_stage8_75_theme_intelligence import parser as authoritative_parser


class ThemeRotationVisualAcceptanceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.latest = get_theme_intelligence_service().snapshots.latest()
        self.assertIsNotNone(self.latest)
        self.artifact = json.loads(THEME_ROTATION_VISUAL_ACCEPTANCE_PATH.read_text())

    def test_authoritative_default_and_makefile_use_intended_frontend_artifact(self) -> None:
        parsed = authoritative_parser.parse_args([])
        self.assertEqual(Path(parsed.rotation_visual_acceptance).resolve(), THEME_ROTATION_VISUAL_ACCEPTANCE_PATH)
        makefile = (REPOSITORY_ROOT / "Makefile").read_text()
        self.assertIn(
            "STAGE875_ROTATION_VISUAL_ACCEPTANCE_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-frontend-visual-acceptance.json",
            makefile,
        )
        self.assertIn(
            "--rotation-visual-acceptance $(STAGE875_ROTATION_VISUAL_ACCEPTANCE_OUTPUT)",
            makefile,
        )

    def test_current_visual_artifact_matches_latest_model_and_required_checks(self) -> None:
        _, diagnostics = inspect_theme_rotation_visual_acceptance(
            THEME_ROTATION_VISUAL_ACCEPTANCE_PATH,
            latest_snapshot_id=self.latest.snapshot_id,
        )
        require_theme_rotation_visual_acceptance(diagnostics)
        self.assertEqual(self.artifact["snapshot_id"], self.latest.snapshot_id)
        self.assertEqual(self.artifact["model_version"], THEME_ROTATION_MODEL_VERSION)
        self.assertEqual(
            REQUIRED_THEME_ROTATION_VISUAL_CHECKS - set(self.artifact["checks"]),
            set(),
        )
        self.assertTrue(
            all(item.get("result") == "PASS" for item in self.artifact["checks"].values())
        )

    def test_wrong_visual_artifact_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stale-rotation-artifact.json"
            path.write_text(json.dumps(self.artifact))
            _, diagnostics = inspect_theme_rotation_visual_acceptance(
                path,
                latest_snapshot_id=self.latest.snapshot_id,
            )
            self.assertIn(
                "loaded_path_is_intended_frontend_visual_acceptance_artifact",
                diagnostics["false_predicates"],
            )
            with self.assertRaisesRegex(RuntimeError, "theme_rotation_visual_acceptance_failed"):
                require_theme_rotation_visual_acceptance(diagnostics)

    def test_stale_visual_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / THEME_ROTATION_VISUAL_ACCEPTANCE_PATH.name
            stale = {**self.artifact, "snapshot_id": "theme-2000-01-01-stale"}
            path.write_text(json.dumps(stale))
            _, diagnostics = inspect_theme_rotation_visual_acceptance(
                path,
                latest_snapshot_id=self.latest.snapshot_id,
                intended_path=path,
            )
            self.assertEqual(
                diagnostics["false_predicates"],
                ["visual_snapshot_id_equals_service_latest_snapshot_id"],
            )
            with self.assertRaisesRegex(RuntimeError, "theme_rotation_visual_acceptance_failed"):
                require_theme_rotation_visual_acceptance(diagnostics)

    def test_regenerating_fresh_renders_against_latest_snapshot_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            modified_at = datetime.now(timezone.utc).timestamp()
            for name, relative_path in REQUIRED_THEME_ROTATION_SCREENSHOTS.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                width, height = EXPECTED_SCREENSHOT_DIMENSIONS[name]
                path.write_bytes(
                    b"\x89PNG\r\n\x1a\n"
                    + struct.pack(">I", 13)
                    + b"IHDR"
                    + struct.pack(">II", width, height)
                )
                os.utime(path, (modified_at, modified_at))
            rotation = {
                "snapshot_id": self.latest.snapshot_id,
                "rotation_model_version": THEME_ROTATION_MODEL_VERSION,
            }
            regenerated = regenerate_visual_acceptance(
                template=self.artifact,
                rotation_artifact=rotation,
                latest_snapshot_id=self.latest.snapshot_id,
                latest_snapshot_generated_at=self.latest.generated_at,
                repository_root=root,
            )
            output = root / THEME_ROTATION_VISUAL_ACCEPTANCE_PATH.name
            output.write_text(json.dumps(regenerated))
            _, diagnostics = inspect_theme_rotation_visual_acceptance(
                output,
                latest_snapshot_id=self.latest.snapshot_id,
                intended_path=output,
            )
            require_theme_rotation_visual_acceptance(diagnostics)
            self.assertEqual(regenerated["snapshot_id"], self.latest.snapshot_id)
            self.assertEqual(regenerated["result"], "PASS")
            self.assertEqual(len(regenerated["screenshots"]), 8)


if __name__ == "__main__":
    unittest.main()

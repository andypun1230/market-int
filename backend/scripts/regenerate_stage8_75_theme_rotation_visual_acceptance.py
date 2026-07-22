from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION
from app.rotation.visual_acceptance import (
    REPOSITORY_ROOT,
    REQUIRED_THEME_ROTATION_SCREENSHOTS,
    REQUIRED_THEME_ROTATION_VISUAL_CHECKS,
    THEME_ROTATION_VISUAL_ACCEPTANCE_PATH,
)
from app.themes.intelligence import get_theme_intelligence_service


EXPECTED_SCREENSHOT_DIMENSIONS = {
    name: ((390, 844) if name.startswith("mobile") else (1280, 720))
    for name in REQUIRED_THEME_ROTATION_SCREENSHOTS
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate Theme Rotation visual acceptance from freshly captured browser renders."
    )
    parser.add_argument("--template", default=str(THEME_ROTATION_VISUAL_ACCEPTANCE_PATH))
    parser.add_argument("--rotation-artifact", default=str(REPOSITORY_ROOT / "artifacts/stage8.75-theme-rotation-validation.json"))
    parser.add_argument("--output", default=str(THEME_ROTATION_VISUAL_ACCEPTANCE_PATH))
    return parser.parse_args()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise RuntimeError(f"theme_rotation_visual_screenshot_is_not_png:{path}")
    return struct.unpack(">II", header[16:24])


def regenerate_visual_acceptance(
    *,
    template: dict[str, Any],
    rotation_artifact: dict[str, Any],
    latest_snapshot_id: str,
    latest_snapshot_generated_at: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    checks = template.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    missing_checks = sorted(REQUIRED_THEME_ROTATION_VISUAL_CHECKS - set(checks))
    failed_checks = sorted(
        name for name, item in checks.items()
        if not isinstance(item, dict) or item.get("result") != "PASS"
    )
    if missing_checks or failed_checks:
        raise RuntimeError(json.dumps({"missing_checks": missing_checks, "failed_checks": failed_checks}, sort_keys=True))
    if rotation_artifact.get("snapshot_id") != latest_snapshot_id:
        raise RuntimeError("theme_rotation_rotation_artifact_is_not_latest")
    if rotation_artifact.get("rotation_model_version") != THEME_ROTATION_MODEL_VERSION:
        raise RuntimeError("theme_rotation_rotation_artifact_model_version_mismatch")

    snapshot_time = _parse_timestamp(latest_snapshot_generated_at)
    screenshot_receipts: dict[str, Any] = {}
    for name, relative_path in REQUIRED_THEME_ROTATION_SCREENSHOTS.items():
        path = repository_root / relative_path
        if not path.is_file():
            raise RuntimeError(f"theme_rotation_visual_screenshot_missing:{path}")
        dimensions = _png_dimensions(path)
        if dimensions != EXPECTED_SCREENSHOT_DIMENSIONS[name]:
            raise RuntimeError(
                f"theme_rotation_visual_screenshot_dimensions_mismatch:{name}:{dimensions}"
            )
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified_at < snapshot_time:
            raise RuntimeError(
                f"theme_rotation_visual_screenshot_predates_latest_snapshot:{name}:"
                f"{modified_at.isoformat()}<{snapshot_time.isoformat()}"
            )
        screenshot_receipts[name] = {
            "dimensions": list(dimensions),
            "modified_at": modified_at.isoformat(),
            "path": relative_path,
        }

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        **template,
        "automated_at": generated_at,
        "model_version": THEME_ROTATION_MODEL_VERSION,
        "result": "PASS",
        "snapshot_id": latest_snapshot_id,
        "screenshots": dict(REQUIRED_THEME_ROTATION_SCREENSHOTS),
        "generation": {
            "method": "fresh_in_app_browser_renders_against_latest_canonical_snapshot",
            "latest_snapshot_generated_at": latest_snapshot_generated_at,
            "required_check_count": len(REQUIRED_THEME_ROTATION_VISUAL_CHECKS),
            "screenshot_receipts": screenshot_receipts,
        },
    }


def main() -> None:
    args = parse_args()
    template_path = Path(args.template).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    rotation_path = Path(args.rotation_artifact).expanduser().resolve()
    template = json.loads(template_path.read_text())
    rotation_artifact = json.loads(rotation_path.read_text())
    snapshot = get_theme_intelligence_service().snapshots.latest()
    if snapshot is None:
        raise RuntimeError("canonical_stage8_75_snapshot_required")
    artifact = regenerate_visual_acceptance(
        template=template,
        rotation_artifact=rotation_artifact,
        latest_snapshot_id=snapshot.snapshot_id,
        latest_snapshot_generated_at=snapshot.generated_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output_path),
        "result": artifact["result"],
        "snapshot_id": artifact["snapshot_id"],
        "screenshots": len(artifact["screenshots"]),
        "checks": len(artifact["checks"]),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

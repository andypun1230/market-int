from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
THEME_ROTATION_VISUAL_ACCEPTANCE_PATH = (
    REPOSITORY_ROOT / "artifacts/stage8.75-theme-rotation-frontend-visual-acceptance.json"
)

REQUIRED_THEME_ROTATION_VISUAL_CHECKS = frozenset({
    "all_eligible_themes_plotted",
    "all_labels_preserve_points",
    "axis_names",
    "browser_console_errors",
    "chronological_tails",
    "compare_mode",
    "current_point_inspector",
    "focus_mode",
    "indicator_explanation",
    "long_leading_filter",
    "long_profile_retrieval",
    "mobile_render",
    "n_a_at_zero",
    "none_labels_preserve_points",
    "profile_controls_are_explicit",
    "progressive_mobile_default",
    "proprietary_claims_absent",
    "smart_labels_preserve_points",
    "tail_and_transition_controls",
    "universe_and_alias_search",
    "web_render",
})

REQUIRED_THEME_ROTATION_SCREENSHOTS = {
    "mobile_390px_chart": "artifacts/theme-rotation-ux-screenshots/mobile-overview-default.png",
    "mobile_all_themes": "artifacts/theme-rotation-ux-screenshots/mobile-all-themes.png",
    "mobile_focus": "artifacts/theme-rotation-ux-screenshots/mobile-focus.png",
    "mobile_compare": "artifacts/theme-rotation-ux-screenshots/mobile-compare.png",
    "web_desktop_chart": "artifacts/theme-rotation-ux-screenshots/desktop-overview.png",
    "web_desktop_compare": "artifacts/theme-rotation-ux-screenshots/desktop-compare.png",
    "quadrant_filtered": "artifacts/theme-rotation-ux-screenshots/quadrant-filtered.png",
    "fast_movers": "artifacts/theme-rotation-ux-screenshots/fast-movers-filtered.png",
}


def load_theme_rotation_visual_acceptance(path: str | Path) -> tuple[Path, dict[str, Any]]:
    loaded_path = Path(path).expanduser().resolve()
    return loaded_path, json.loads(loaded_path.read_text())


def inspect_theme_rotation_visual_acceptance(
    path: str | Path,
    *,
    latest_snapshot_id: str,
    intended_path: str | Path = THEME_ROTATION_VISUAL_ACCEPTANCE_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded_path, artifact = load_theme_rotation_visual_acceptance(path)
    checks = artifact.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    missing_checks = sorted(REQUIRED_THEME_ROTATION_VISUAL_CHECKS - set(checks))
    failed_checks = {
        name: item.get("result") if isinstance(item, dict) else None
        for name, item in sorted(checks.items())
        if not isinstance(item, dict) or item.get("result") != "PASS"
    }
    screenshots = artifact.get("screenshots")
    screenshots = screenshots if isinstance(screenshots, dict) else {}
    missing_screenshots = sorted(set(REQUIRED_THEME_ROTATION_SCREENSHOTS) - set(screenshots))
    mismatched_screenshots = {
        name: screenshots.get(name)
        for name, expected in REQUIRED_THEME_ROTATION_SCREENSHOTS.items()
        if name in screenshots and screenshots.get(name) != expected
    }
    expected_path = Path(intended_path).expanduser().resolve()
    predicates = {
        "loaded_path_is_intended_frontend_visual_acceptance_artifact": loaded_path == expected_path,
        "result_is_pass": artifact.get("result") == "PASS",
        "visual_snapshot_id_equals_service_latest_snapshot_id": artifact.get("snapshot_id") == latest_snapshot_id,
        "model_version_is_theme_relative_trend_momentum_v1": artifact.get("model_version") == THEME_ROTATION_MODEL_VERSION,
        "every_required_visual_check_is_present": not missing_checks,
        "every_visual_check_is_pass": not failed_checks,
        "every_required_screenshot_is_present": not missing_screenshots,
        "every_required_screenshot_path_is_canonical": not mismatched_screenshots,
    }
    diagnostics = {
        "loaded_visual_artifact_path": str(loaded_path),
        "intended_visual_artifact_path": str(expected_path),
        "visual_snapshot_id": artifact.get("snapshot_id"),
        "service_latest_snapshot_id": latest_snapshot_id,
        "visual_model_version": artifact.get("model_version"),
        "missing_checks": missing_checks,
        "failed_checks": failed_checks,
        "missing_screenshots": missing_screenshots,
        "mismatched_screenshots": mismatched_screenshots,
        "predicates": predicates,
        "false_predicates": [name for name, passed in predicates.items() if not passed],
    }
    return artifact, diagnostics


def require_theme_rotation_visual_acceptance(diagnostics: dict[str, Any]) -> None:
    if diagnostics["false_predicates"]:
        raise RuntimeError(
            "theme_rotation_visual_acceptance_failed: "
            + json.dumps(diagnostics, sort_keys=True)
        )

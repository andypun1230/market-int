#!/usr/bin/env python3
"""Audit Theme provenance without deriving, fetching, or activating data."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.theme_snapshots.service import get_theme_snapshot_service
from app.themes.catalog import reference_definitions, reference_members
from app.themes.identifiers import normalize_theme_id


FIXTURE_PATHS = ["frontend/src/data/sectorTabTestData.ts"]
STATIC_PATHS = ["backend/app/services/theme_provenance.py", "frontend/src/features/market/marketOverviewAnalysis.ts", "frontend/src/app/report.tsx"]
UNAVAILABLE_PATHS = ["frontend/src/app/(tabs)/sectors.tsx", "backend/app/services/sector_dashboard.py"]
LIVE_PATHS = ["backend/app/themes/", "backend/app/theme_snapshots/"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Theme definition, fixture, static-preference, and snapshot provenance without mutation.",
        epilog="Example: --all-themes --mode all --json-output ../docs/phase-4.4d-theme-provenance.json --markdown-output ../docs/phase-4.4d-theme-provenance.md",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--theme", metavar="THEME_ID", help="Canonical snake_case Theme ID; legacy kebab-case alias is accepted.")
    selection.add_argument("--all-themes", action="store_true", help="Audit every registered reference package.")
    parser.add_argument("--mode", choices=("test", "live", "all"), default="all")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--fail-on-unknown", action="store_true")
    return parser.parse_args()


def audit(args: argparse.Namespace) -> dict[str, Any]:
    definitions, package_errors = reference_definitions()
    unknown_paths: list[str] = []
    requested_id = None
    if args.theme:
        try:
            requested_id = normalize_theme_id(args.theme)
        except ValueError as error:
            unknown_paths.append(str(error))
    selected = [definition for definition in definitions if requested_id is None or definition.theme_id == requested_id]
    if requested_id and not selected:
        unknown_paths.append(f"definition_package_not_found:{requested_id}")
    snapshot = get_theme_snapshot_service().latest()
    rows: list[dict[str, Any]] = []
    for definition in selected:
        members, member_errors = reference_members(definition.theme_id, definition.version)
        reviewed = definition.status in {"reviewed", "active"} and bool(definition.reviewed_at and definition.reviewed_by) and all(member.reviewed_at and member.reviewed_by for member in members if member.active)
        classification = "proposed_unreviewed" if definition.status == "proposed" else "live_verified" if definition.status == "active" and reviewed else "unknown"
        snapshot_contains_version = bool(snapshot and any(
            item.get("theme_id") == definition.theme_id and item.get("version") == definition.version
            for item in snapshot.rows
        ))
        rows.append({
            "theme_id": definition.theme_id,
            "display_name": definition.display_name,
            "definition_status": definition.status,
            "review_status": "reviewed" if reviewed else "awaiting_review",
            "active": definition.status == "active",
            "snapshot_status": snapshot.status if snapshot_contains_version else "unavailable",
            "data_mode": snapshot.source_state if snapshot_contains_version else "unavailable",
            "provenance_classification": classification,
            "source_references": list(definition.source_references),
            "member_count": len(members),
            "package_errors": member_errors,
            "production_exposure": bool(snapshot_contains_version and snapshot and snapshot.source_state == "live" and classification != "live_verified"),
            "blockers": ["human_review_required"] if not reviewed else [],
        })
        package_errors.extend(member_errors)
    failures = []
    if any(row["production_exposure"] for row in rows): failures.append("non_live_theme_provenance_exposed_in_production")
    if any(row["active"] and row["review_status"] != "reviewed" for row in rows): failures.append("active_unreviewed_definition")
    if package_errors: failures.append("malformed_definition_package")
    if args.fail_on_unknown and unknown_paths: failures.append("unknown_theme_provenance")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "themes_audited": [row["theme_id"] for row in rows],
        "definitions_found": len(rows),
        "themes": rows,
        "snapshot": {"status": snapshot.status if snapshot else "unavailable", "snapshot_id": snapshot.snapshot_id if snapshot else None, "source_state": snapshot.source_state if snapshot else "unavailable"},
        "fixture_paths": FIXTURE_PATHS,
        "static_strategy_preference_paths": STATIC_PATHS,
        "unavailable_paths": UNAVAILABLE_PATHS,
        "live_verified_paths": LIVE_PATHS,
        "unknown_paths": unknown_paths,
        "blockers": sorted({blocker for row in rows for blocker in row["blockers"]}),
        "failures": failures,
        "overall_result": "FAIL" if failures else "PASS",
    }


def markdown(report: dict[str, Any]) -> str:
    lines = ["# Phase 4.4D Theme Provenance Audit", "", f"Result: **{report['overall_result']}**", "", "| Theme | Definition | Review | Provenance | Production exposure |", "| --- | --- | --- | --- | --- |"]
    for row in report["themes"]:
        lines.append(f"| `{row['theme_id']}` | {row['definition_status']} | {row['review_status']} | {row['provenance_classification']} | {str(row['production_exposure']).lower()} |")
    lines.extend(["", "## Quarantined paths", *[f"- Test fixture: `{path}`" for path in report["fixture_paths"]], *[f"- Static strategy preference: `{path}`" for path in report["static_strategy_preference_paths"]]])
    if report["blockers"]: lines.extend(["", "## Blockers", *[f"- `{value}`" for value in report["blockers"]]])
    if report["failures"]: lines.extend(["", "## Failures", *[f"- `{value}`" for value in report["failures"]]])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args(); report = audit(args); rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    try:
        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
        if args.markdown_output:
            args.markdown_output.parent.mkdir(parents=True, exist_ok=True); args.markdown_output.write_text(markdown(report))
    except OSError as error:
        print(json.dumps({"overall_result": "FAIL", "failures": [f"report_write_failure:{type(error).__name__}"]}, indent=2))
        return 1
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

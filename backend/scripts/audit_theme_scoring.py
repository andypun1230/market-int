#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from app.theme_snapshots.service import get_theme_snapshot_service

parser = argparse.ArgumentParser(description="Read-only audit of published ThemeSnapshot scoring arithmetic."); parser.add_argument("--themes"); parser.add_argument("--json-output", type=Path); parser.add_argument("--markdown-output", type=Path)
args = parser.parse_args(); snapshot = get_theme_snapshot_service().latest(); rows = []
selected = {item.strip() for item in (args.themes or "").split(",") if item.strip()}
for row in snapshot.rows if snapshot else []:
    if selected and row.get("theme_id") not in selected: continue
    contributions = row.get("weighted_contributions", {})
    total = round(sum(float(value.get("weighted_contribution") or 0) for value in contributions.values()), 2)
    components = {
        name: {
            "component_score": value.get("score"),
            "weight": value.get("weight"),
            "weighted_contribution": value.get("weighted_contribution"),
        }
        for name, value in contributions.items()
    }
    score_semantics = row.get("score_semantics", {})
    rows.append({
        "theme_id": row["theme_id"], "rank": row.get("rank"),
        "displayed_score": row.get("composite_score"),
        "absolute_weighted_composite": total,
        "component_contributions": components,
        "score_semantics": score_semantics,
        "cross_sectional_percentile": score_semantics.get("cross_sectional_percentile"),
        "valid": row.get("composite_score") == total
        and (score_semantics.get("score_type") or score_semantics.get("displayed_score_type")) == "absolute_weighted_composite",
        "participation_definition": row.get("participation", {}).get("definition"),
    })
report = {"snapshot_id": snapshot.snapshot_id if snapshot else None, "themes": sorted(selected) if selected else None, "rows": rows, "valid": bool(snapshot) and bool(rows) and all(row["valid"] for row in rows), "status": "unavailable_pending_review" if snapshot is None else "pass" if rows and all(row["valid"] for row in rows) else "fail"}; rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
if args.json_output: args.json_output.write_text(rendered + "\n")
if args.markdown_output:
    details = "\n".join(
        f"- `{row['theme_id']}`: {'PASS' if row['valid'] else 'FAIL'}; displayed {row['displayed_score']} / 100, "
        f"absolute weighted composite {row['absolute_weighted_composite']}, rank #{row['rank']}."
        for row in rows
    ) or "- No published ThemeSnapshot."
    args.markdown_output.write_text("# Theme Scoring Audit\n\nStatus: **%s**\n\n%s\n" % (report["status"], details))
raise SystemExit(0 if snapshot is None or report["valid"] else 1)

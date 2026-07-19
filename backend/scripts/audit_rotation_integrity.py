#!/usr/bin/env python3
"""Audit durable rotation series and explicitly classify unavailable Theme rotation."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rotation.policy import INTERVAL_POLICIES, ROTATION_FORMULA_VERSION, ROTATION_NORMALIZATION_VERSION
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.sector_dashboard import build_sector_rotation_trails


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Sector and Theme rotation provenance and coordinate integrity.")
    parser.add_argument("--entity", choices=("sectors", "themes", "all"), default="all")
    parser.add_argument("--interval", choices=("1w", "1m", "3m"))
    parser.add_argument("--all-intervals", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--test", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--csv-output", type=Path)
    return parser.parse_args()


def selected_intervals(args: argparse.Namespace) -> tuple[str, ...]:
    if args.all_intervals:
        return tuple(INTERVAL_POLICIES)
    return ((args.interval or "1m").upper(),)


def point_record(series: dict[str, Any], point: dict[str, Any], point_index: int) -> dict[str, Any]:
    return {
        "entity_type": series.get("entity_type"),
        "entity_id": series.get("entity_id"),
        "label": series.get("short_label") or series.get("display_name"),
        "interval": series.get("interval"),
        "point_index": point_index,
        "market_date": point.get("market_date"),
        "source_state": series.get("source_state"),
        "data_mode": series.get("data_mode"),
        "benchmark": series.get("benchmark_symbol"),
        "formula_version": series.get("formula_version"),
        "normalization_version": series.get("normalization_version"),
        "raw_rs": point.get("raw_rs"),
        "raw_momentum": point.get("raw_momentum"),
        "plotted_x": point.get("plotted_x"),
        "plotted_y": point.get("plotted_y"),
        "quadrant": point.get("quadrant"),
        "expected_quadrant": expected_quadrant(point.get("plotted_x"), point.get("plotted_y")),
        "snapshot_id": point.get("snapshot_id"),
        "source_series_ids": ";".join(point.get("source_series_ids") or ()),
        "source_provider": point.get("source_provider"),
        "is_synthetic": point.get("is_synthetic"),
        "compatibility_signature": point.get("compatibility_signature"),
    }


def expected_quadrant(x: object, y: object) -> str | None:
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if x >= 100 and y >= 100:
        return "leading"
    if x >= 100:
        return "weakening"
    if y < 100:
        return "lagging"
    return "improving"


def audit_sector_series(args: argparse.Namespace, intervals: tuple[str, ...]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str], list[str]]:
    failures: list[str] = []
    conditions: list[str] = []
    snapshot = get_sector_snapshot_service().latest()
    if not snapshot:
        return [], {"classification": "UNAVAILABLE", "reason": "No published SectorSnapshot."}, ["sector_snapshot_unavailable"], conditions
    response = build_sector_rotation_trails(snapshot, get_sector_snapshot_service().history())
    series = [item for item in response["series"] if item["interval"] in intervals]
    records: list[dict[str, Any]] = []
    mismatch_counts = {"chronology": 0, "duplicate_dates": 0, "current_endpoint": 0, "coordinate": 0, "quadrant": 0, "synthetic": 0, "provenance": 0, "interval": 0, "compatibility": 0}
    for item in series:
        points = item.get("trail_points") or []
        policy = INTERVAL_POLICIES[item["interval"]]
        dates = [point.get("market_date") for point in points]
        if len(points) != policy.point_count:
            mismatch_counts["interval"] += 1
        if dates != sorted(dates):
            mismatch_counts["chronology"] += 1
        if len(set(dates)) != len(dates):
            mismatch_counts["duplicate_dates"] += 1
        if not points or item.get("current_point") != points[-1] or not points[-1].get("is_current"):
            mismatch_counts["current_endpoint"] += 1
        signatures = {point.get("compatibility_signature") for point in points}
        if len(signatures) != 1:
            mismatch_counts["compatibility"] += 1
        for index, point in enumerate(points):
            records.append(point_record(item, point, index))
            try:
                date.fromisoformat(point["market_date"])
            except (KeyError, TypeError, ValueError):
                mismatch_counts["chronology"] += 1
            if point.get("is_synthetic"):
                mismatch_counts["synthetic"] += 1
            if args.live and point.get("source_provider") != "polygon":
                mismatch_counts["provenance"] += 1
            if point.get("plotted_x") != round(100 + point.get("raw_rs", float("nan")), 4) or point.get("plotted_y") != round(100 + point.get("raw_momentum", float("nan")), 4):
                mismatch_counts["coordinate"] += 1
            if point.get("quadrant") != expected_quadrant(point.get("plotted_x"), point.get("plotted_y")):
                mismatch_counts["quadrant"] += 1
            if point.get("formula_version") not in (None, ROTATION_FORMULA_VERSION):
                mismatch_counts["compatibility"] += 1
    for name, count in mismatch_counts.items():
        if count:
            failures.append(f"sector_{name}_failures:{count}")
    if args.live and snapshot.source_state != "live":
        failures.append("sector_live_source_state_not_live")
    correlations = {interval: correlation_for(records, interval) for interval in intervals}
    high_correlation = [interval for interval, result in correlations.items() if result.get("pearson") is not None and abs(result["pearson"]) > 0.95]
    if high_correlation:
        conditions.append(f"high_rs_momentum_correlation:{','.join(high_correlation)}")
    summary = {
        "classification": "LIVE_VERIFIED" if snapshot.source_state == "live" else "TEST_FIXTURE",
        "snapshot_id": snapshot.snapshot_id,
        "source_state": snapshot.source_state,
        "data_mode": "live" if snapshot.source_state == "live" else "test",
        "formula_version": ROTATION_FORMULA_VERSION,
        "normalization_version": ROTATION_NORMALIZATION_VERSION,
        "benchmark": snapshot.benchmark,
        "entities": len({item["entity_id"] for item in series}),
        "series": len(series),
        "points": len(records),
        "correlations": correlations,
        "mismatches": mismatch_counts,
        "intervals": {key: vars(value) for key, value in INTERVAL_POLICIES.items() if key in intervals},
        "trail_source": response["market_trail_source"],
    }
    return records, summary, failures, conditions


def correlation_for(records: list[dict[str, Any]], interval: str) -> dict[str, float | None]:
    latest_by_entity: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["interval"] == interval:
            latest_by_entity[record["entity_id"]] = record
    xs = [float(item["plotted_x"]) for item in latest_by_entity.values() if isinstance(item.get("plotted_x"), (int, float)) and isinstance(item.get("plotted_y"), (int, float))]
    ys = [float(item["plotted_y"]) for item in latest_by_entity.values() if isinstance(item.get("plotted_x"), (int, float)) and isinstance(item.get("plotted_y"), (int, float))]
    if len(xs) < 2:
        return {"pearson": None, "count": float(len(xs)), "rs_min": None, "rs_max": None, "momentum_min": None, "momentum_max": None}
    mean_x = sum(xs) / len(xs); mean_y = sum(ys) / len(ys)
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    pearson = None if denominator == 0 else round(sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator, 6)
    return {"pearson": pearson, "count": float(len(xs)), "rs_min": round(min(xs), 4), "rs_max": round(max(xs), 4), "momentum_min": round(min(ys), 4), "momentum_max": round(max(ys), 4)}


def audit_themes(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], list[str], list[str]]:
    fixture = PROJECT_ROOT / "frontend" / "src" / "data" / "sectorTabTestData.ts"
    source = fixture.read_text() if fixture.exists() else ""
    generated = all(marker in source for marker in ("generateRotationHistory", "createSeededRandom", "buildRotationLabel"))
    classification = "TEST_FIXTURE" if generated else "UNKNOWN"
    conditions = ["theme_live_rotation_unavailable_until_phase_4_4d"]
    if args.live:
        conditions.append("theme_fixtures_are_quarantined_in_live_mode")
    summary = {
        "classification": classification,
        "source_state": "test" if generated else "unknown",
        "data_mode": "test_fixture" if generated else "unknown",
        "benchmark": "SPY",
        "points": 0,
        "first_market_date": None,
        "last_market_date": None,
        "persisted": False,
        "regenerated_on_request": generated,
        "interpolated_or_reconstructed": generated,
        "reason": "Frontend test fixture uses deterministic seeded path generation and synthetic -Nd labels; no reviewed theme membership or durable price series exists.",
    }
    return [], summary, [], conditions


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["entity_type", "entity_id", "label", "interval", "point_index", "market_date", "source_state", "data_mode", "benchmark", "formula_version", "normalization_version", "raw_rs", "raw_momentum", "plotted_x", "plotted_y", "quadrant", "expected_quadrant", "snapshot_id", "source_series_ids", "source_provider", "is_synthetic", "compatibility_signature"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(records)


def main() -> int:
    args = parse_args()
    intervals = selected_intervals(args)
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    conditions: list[str] = []
    summaries: dict[str, Any] = {}
    if args.entity in {"sectors", "all"}:
        sector_records, summary, sector_failures, sector_conditions = audit_sector_series(args, intervals)
        records.extend(sector_records); summaries["sectors"] = summary; failures.extend(sector_failures); conditions.extend(sector_conditions)
    if args.entity in {"themes", "all"}:
        theme_records, summary, theme_failures, theme_conditions = audit_themes(args)
        records.extend(theme_records); summaries["themes"] = summary; failures.extend(theme_failures); conditions.extend(theme_conditions)
    report = {"passed": not failures, "result": "PASS" if not failures and not conditions else "PASS WITH CONDITIONS" if not failures else "FAIL", "failures": failures, "conditions": sorted(set(conditions)), "intervals": intervals, "summary": summaries, "points": records}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    if args.csv_output:
        write_csv(args.csv_output, records)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

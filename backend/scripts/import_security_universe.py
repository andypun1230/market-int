#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.securities.import_validation import validate_reviewed_source_rows  # noqa: E402
from app.securities.registry import SP100_SOURCE_NAME, SP100_SOURCE_URL  # noqa: E402
from app.securities.service import SecurityMasterService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Versioned S&P 100 security-master importer")
    parser.add_argument("--universe", default="sp100")
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--version", default=None)
    parser.add_argument("--effective-date", default=date.today().isoformat())
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def load_rows(path: Path) -> tuple[list[dict], dict, list[str] | None]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text())
        return list(payload.get("members", payload if isinstance(payload, list) else [])), payload if isinstance(payload, dict) else {}, None
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        metadata = {
            "source": rows[0].get("source") if rows else None,
            "source_timestamp": rows[0].get("source_effective_date") if rows else None,
        }
        return rows, metadata, reader.fieldnames


def main() -> int:
    args = parse_args()
    if args.apply == args.dry_run:
        raise SystemExit("Specify exactly one of --dry-run or --apply.")
    rows, metadata, fieldnames = load_rows(args.source_file)
    validation_errors = validate_reviewed_source_rows(rows, fieldnames) if args.source_file.suffix.lower() == ".csv" else []
    if validation_errors:
        report = {"universe_id": None, "dry_run": args.dry_run, "invalid": validation_errors, "member_count": len(rows), "source_file": str(args.source_file)}
        rendered = json.dumps(report, indent=2, sort_keys=True)
        print(rendered)
        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
        return 1
    version = args.version or metadata.get("version") or f"v{args.effective_date.replace('-', '')}"
    source = metadata.get("source") or SP100_SOURCE_NAME
    source_timestamp = metadata.get("source_timestamp") or args.effective_date
    report = SecurityMasterService().import_universe(
        name=args.universe, version=version, effective_date=args.effective_date,
        benchmark_symbol=args.benchmark, rows=rows, source=source,
        source_timestamp=source_timestamp, notes=metadata.get("notes") or f"Reference: {SP100_SOURCE_URL}",
        dry_run=args.dry_run,
    ).model_dump()
    report["source_file"] = str(args.source_file)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    return 1 if report["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

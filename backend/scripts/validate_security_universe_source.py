#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.securities.import_validation import validate_reviewed_source_rows  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a reviewed, dated breadth-universe source CSV")
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--expected-members", default=101, type=int)
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.source_file.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        errors = validate_reviewed_source_rows(rows, reader.fieldnames)
    if len(rows) != args.expected_members:
        errors.append(f"file:expected_members:{args.expected_members}:actual:{len(rows)}")
    report = {
        "source_file": str(args.source_file),
        "sha256": hashlib.sha256(args.source_file.read_bytes()).hexdigest(),
        "member_count": len(rows),
        "unique_ticker_count": len({str(row.get('ticker') or '').upper() for row in rows}),
        "source_effective_dates": sorted({str(row.get("source_effective_date") or "") for row in rows}),
        "verified_dates": sorted({str(row.get("verified_at") or "") for row in rows}),
        "errors": sorted(errors),
        "status": "PASS" if not errors else "FAIL",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

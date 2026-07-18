#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.breadth.builder import BreadthSnapshotBuilder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a breadth snapshot from already persisted constituent history")
    parser.add_argument("--universe", default="sp100")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    snapshot = BreadthSnapshotBuilder().build_and_publish(args.universe)
    report = {"universe": args.universe, "snapshot_id": snapshot.snapshot_id if snapshot else None, "status": snapshot.status if snapshot else "unavailable", "coverage": snapshot.coverage if snapshot else None}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 0 if snapshot else 1


if __name__ == "__main__":
    raise SystemExit(main())

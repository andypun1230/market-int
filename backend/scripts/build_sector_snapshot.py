#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))
from app.sector_snapshots.service import get_sector_snapshot_service

parser = argparse.ArgumentParser(description="Build a provider-free durable sector snapshot")
parser.add_argument("--universe", default="sp100"); parser.add_argument("--no-publish", action="store_true"); parser.add_argument("--json-output", type=Path)
args = parser.parse_args(); snapshot = get_sector_snapshot_service().build_now(args.universe, publish=not args.no_publish)
report = snapshot.model_dump() if snapshot else {"status": "unavailable"}; print(json.dumps(report, indent=2, sort_keys=True))
if args.json_output: args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
raise SystemExit(0 if snapshot else 1)

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))
from app.theme_snapshots.service import get_theme_snapshot_service

parser = argparse.ArgumentParser(description="Mutate durable Theme basket history and optionally publish a ThemeSnapshot from reviewed active definitions and stored bars.")
parser.add_argument("--no-publish", action="store_true"); parser.add_argument("--json-output", type=Path)
args = parser.parse_args(); snapshot = get_theme_snapshot_service().build_now(publish=not args.no_publish)
report = snapshot.model_dump() if snapshot else get_theme_snapshot_service().status(); rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
if args.json_output: args.json_output.write_text(rendered + "\n")
raise SystemExit(0 if snapshot else 1)

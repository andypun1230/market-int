#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))

from app.breadth.service import get_breadth_snapshot_service  # noqa: E402
from app.market_history.updater import BreadthUniverseHistoryUpdater  # noqa: E402
from app.securities.service import SecurityMasterService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Incremental breadth-universe daily-history updater")
    parser.add_argument("--universe", default="sp100"); parser.add_argument("--json-output", type=Path); args = parser.parse_args()
    master = SecurityMasterService(); universe = master.storage.get_active_universe(args.universe)
    if not universe: raise SystemExit(f"No active universe named {args.universe}; import it explicitly first.")
    updater = BreadthUniverseHistoryUpdater(); rows = []
    for member in master.storage.members(universe.universe_id):
        security = master.storage.security(member.ticker)
        try: rows.append(updater.update_symbol(member.ticker, provider_symbol=security.history_provider_symbol if security else member.ticker, lookback_calendar_days=14, overlap_days=7))
        except Exception as exc: rows.append({"ticker": member.ticker, "status": "failed", "error_category": getattr(exc, "category", type(exc).__name__)})
    snapshot = get_breadth_snapshot_service().build_now(); report = {"universe": universe.universe_id, "updates": rows, "snapshot_id": snapshot.snapshot_id if snapshot else None}
    rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
    if args.json_output: args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    return 1 if any(row["status"] == "failed" for row in rows) else 0


if __name__ == "__main__": raise SystemExit(main())

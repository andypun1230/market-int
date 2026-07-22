#!/usr/bin/env python3
"""Verify and backfill missing canonical identity metadata for live Theme bars."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_history.storage import DailyBarStorage
from app.securities.service import get_security_master_service
from app.themes.service import ThemeDefinitionService


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill only missing verified Theme-bar identity fields.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    bars = DailyBarStorage()
    securities = get_security_master_service().storage
    rows = []
    failures = []
    seen: set[str] = set()
    for _definition, members in ThemeDefinitionService().active():
        for member in members:
            ticker = member.ticker.upper()
            if ticker in seen:
                continue
            seen.add(ticker)
            security = securities.security(ticker)
            history = bars.history(ticker)
            expected_by_date = {
                bar.session_date: (securities.provider_symbol_for(ticker, on_date=bar.session_date).provider_symbol if securities.provider_symbol_for(ticker, on_date=bar.session_date) else ticker)
                for bar in history
            }
            invalid_source = [bar.session_date for bar in history if (bar.source_symbol or ticker).upper() != expected_by_date[bar.session_date].upper()]
            invalid_identity = [bar.session_date for bar in history if bar.canonical_security_id not in {None, "", security.security_id if security else None}]
            missing_before = sum(bar.canonical_security_id in {None, ""} for bar in history)
            updated = 0
            if args.apply and security and not invalid_source and not invalid_identity:
                updated = bars.backfill_canonical_identity(ticker, security.security_id, lineage="reviewed_theme_identity_backfill_v1")
            final_history = bars.history(ticker)
            missing_after = sum(bar.canonical_security_id in {None, ""} for bar in final_history)
            row = {
                "ticker": ticker, "security_id": security.security_id if security else None,
                "bar_count": len(history), "first_session": history[0].session_date if history else None,
                "last_session": history[-1].session_date if history else None,
                "missing_identity_before": missing_before, "missing_identity_after": missing_after, "updated": updated,
                "invalid_source_sessions": invalid_source, "invalid_identity_sessions": invalid_identity,
            }
            if not security or not history or invalid_source or invalid_identity or missing_after:
                failures.append(ticker)
            rows.append(row)
    report = {"status": "PASS" if not failures else "FAIL", "applied": args.apply, "rows": rows, "failures": failures}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Import human-reviewed security-master records needed by Theme definitions.

This does not alter an index universe. It only adds or updates verified equity
records so an already reviewed ThemeDefinition can resolve a provider symbol.
"""
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

from app.securities.models import SecurityRecord
from app.securities.registry import canonical_sector_id, normalized_sector
from app.securities.service import get_security_master_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reviewed Theme security-master records.")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.dry_run == args.apply:
        parser.error("choose exactly one of --dry-run or --apply")

    rows = list(csv.DictReader(args.file.open(newline="")))
    records: list[SecurityRecord] = []
    errors: list[str] = []
    for index, row in enumerate(rows, 2):
        ticker = str(row.get("ticker") or "").strip().upper()
        sector = normalized_sector(row.get("sector"))
        sector_id = canonical_sector_id(row.get("sector"))
        required = (ticker, row.get("company_name"), sector_id, row.get("history_provider_symbol"), row.get("reviewed_at"), row.get("reviewed_by"), row.get("source_url"), row.get("source_retrieved_at"))
        if not all(required):
            errors.append(f"row:{index}:reviewed_security_metadata_required")
            continue
        records.append(SecurityRecord(
            security_id=str(row.get("security_id") or f"theme-sec-{hashlib.sha256(ticker.encode()).hexdigest()[:16]}"),
            ticker=ticker, company_name=str(row["company_name"]).strip(), exchange=str(row.get("exchange") or "US").strip(),
            asset_type="equity", active=True, sector=sector, sector_id=sector_id, industry=str(row.get("industry") or "").strip() or None,
            quote_provider_symbol=str(row.get("quote_provider_symbol") or ticker).strip().upper(), history_provider_symbol=str(row["history_provider_symbol"]).strip().upper(),
            effective_from=str(row.get("effective_from") or "").strip() or None, effective_to=str(row.get("effective_to") or "").strip() or None,
            source=f"theme-reviewed-security-master:{str(row['source_url']).strip()}", source_timestamp=str(row["source_retrieved_at"]).strip(), verified_at=str(row["reviewed_at"]).strip(),
        ))
    duplicate = {record.ticker for record in records if sum(other.ticker == record.ticker for other in records) > 1}
    errors.extend(f"duplicate_ticker:{ticker}" for ticker in sorted(duplicate))
    report = {"file": str(args.file), "dry_run": args.dry_run, "records": [record.ticker for record in records], "errors": errors, "applied": False, "review_gate": "Every record requires reviewer, review date, source URL, retrieval date, sector, and provider mapping."}
    if args.apply and not errors:
        storage = get_security_master_service().storage
        for record in records:
            storage.upsert_security(record)
        report["applied"] = True
    elif args.apply:
        report["errors"].append("security_master_import_blocked")
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.write_text(rendered + "\n")
    return 0 if args.dry_run or report["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Import reviewed historical aliases and date-aware provider symbols."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.securities.models import SecurityAlias, SecurityProviderSymbol
from app.securities.service import get_security_master_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Import human-reviewed security aliases and provider symbol history.")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.dry_run == args.apply:
        parser.error("choose exactly one of --dry-run or --apply")

    storage = get_security_master_service().storage
    aliases: list[SecurityAlias] = []
    symbols: list[SecurityProviderSymbol] = []
    errors: list[str] = []
    for line, row in enumerate(csv.DictReader(args.file.open(newline="")), 2):
        canonical = str(row.get("canonical_ticker") or "").strip().upper()
        security = storage.security(canonical)
        required = (canonical, row.get("provider"), row.get("purpose"), row.get("provider_symbol"), row.get("effective_from"), row.get("source"), row.get("verified_at"))
        if not all(required):
            errors.append(f"row:{line}:symbol_history_metadata_required")
            continue
        if security is None:
            errors.append(f"row:{line}:canonical_security_not_found:{canonical}")
            continue
        requested_security_id = str(row.get("security_id") or "").strip()
        if requested_security_id and requested_security_id != security.security_id:
            errors.append(f"row:{line}:security_id_mismatch:{canonical}")
            continue
        if row.get("alias_ticker"):
            alias_required = (row.get("former_company_name"), row.get("alias_effective_to"), row.get("corporate_action_type"), row.get("continuity_status"))
            if not all(alias_required):
                errors.append(f"row:{line}:alias_metadata_required")
                continue
            aliases.append(SecurityAlias(
                alias_ticker=str(row["alias_ticker"]).strip().upper(), security_id=security.security_id,
                former_company_name=str(row["former_company_name"]).strip(), effective_to=str(row["alias_effective_to"]).strip(),
                corporate_action_type=str(row["corporate_action_type"]).strip(), continuity_status=str(row["continuity_status"]).strip(),
                source=str(row["source"]).strip(), verified_at=str(row["verified_at"]).strip(),
            ))
        symbols.append(SecurityProviderSymbol(
            security_id=security.security_id, provider=str(row["provider"]).strip().lower(), purpose=str(row["purpose"]).strip().lower(),
            provider_symbol=str(row["provider_symbol"]).strip().upper(), effective_from=str(row["effective_from"]).strip(),
            effective_to=str(row.get("effective_to") or "").strip() or None, source=str(row["source"]).strip(),
            verified_at=str(row["verified_at"]).strip(), corporate_action_lineage=str(row.get("corporate_action_lineage") or "").strip() or None,
        ))
    report = {"file": str(args.file), "dry_run": args.dry_run, "aliases": [item.alias_ticker for item in aliases], "provider_symbols": [item.model_dump() for item in symbols], "errors": errors, "applied": False}
    if args.apply and not errors:
        try:
            for alias in aliases:
                storage.upsert_alias(alias)
            for symbol in symbols:
                storage.upsert_provider_symbol(symbol)
            report["applied"] = True
        except ValueError as error:
            report["errors"].append(str(error))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 0 if args.dry_run or report["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

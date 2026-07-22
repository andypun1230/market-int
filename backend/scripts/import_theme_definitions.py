#!/usr/bin/env python3
"""Validate and import a human-reviewed immutable ThemeDefinition version."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))

from app.securities.service import get_security_master_service
from app.themes.identifiers import normalize_theme_id
from app.themes.registry import read_definition_markdown, read_members_csv
from app.themes.service import ThemeDefinitionService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or import a reviewed, versioned Theme definition.",
        epilog="Example: --theme memory_storage --definition-file data/reference/themes/memory-storage-v1.md --members-file data/reference/themes/memory-storage-v1.csv --dry-run",
    )
    parser.add_argument("--theme", metavar="THEME_ID", help="Canonical snake_case Theme ID; legacy kebab-case alias is accepted."); parser.add_argument("--definition-file", type=Path, required=True); parser.add_argument("--members-file", type=Path, required=True)
    parser.add_argument("--version"); parser.add_argument("--effective-date"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--apply", action="store_true"); parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.apply == args.dry_run:
        parser.error("choose exactly one of --dry-run or --apply")
    try:
        requested_theme_id = normalize_theme_id(args.theme) if args.theme else None
        definition = read_definition_markdown(args.definition_file)
    except ValueError as error:
        report = {"status": "BLOCKED", "reason_code": "unknown_theme_id", "requested_theme_id": args.theme, "applied": False, "errors": [str(error)]}
        rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
        if args.json_output: args.json_output.write_text(rendered + "\n")
        return 2
    members = read_members_csv(args.members_file, definition)
    if requested_theme_id and requested_theme_id != definition.theme_id:
        report = {"status": "BLOCKED", "reason_code": "theme_id_mismatch", "requested_theme_id": args.theme, "canonical_requested_theme_id": requested_theme_id, "definition_theme_id": definition.theme_id, "applied": False}
        rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
        if args.json_output: args.json_output.write_text(rendered + "\n")
        return 2
    if args.version and args.version != definition.version: parser.error("--version does not match definition version")
    if args.effective_date and args.effective_date != definition.effective_from: parser.error("--effective-date does not match definition effective_from")
    service = ThemeDefinitionService(); errors = service.validate_import(definition, members, require_reviewed=True)
    master = get_security_master_service(); missing_security = [member.ticker for member in members if not master.storage.security(member.ticker)]
    invalid_provider_mapping = [member.ticker for member in members if (security := master.storage.security(member.ticker)) and not security.history_provider_symbol]
    security_id_mismatches = [member.ticker for member in members if member.security_id and (security := master.storage.security(member.ticker)) and security.security_id != member.security_id]
    reviewed = definition.status in {"reviewed", "active"} and bool(definition.reviewed_at and definition.reviewed_by) and all(member.reviewed_at and member.reviewed_by for member in members if member.active)
    reason_code = "human_review_required" if not reviewed else "security_master_required" if missing_security or invalid_provider_mapping or security_id_mismatches else None
    report = {"status": "READY" if not errors and not missing_security and not invalid_provider_mapping and not security_id_mismatches else "BLOCKED", "reason_code": reason_code, "requested_theme_id": args.theme, "canonical_theme_id": definition.theme_id, "theme_id": definition.theme_id, "version": definition.version, "definition_status": definition.status, "reviewed": reviewed, "reviewer": definition.reviewed_by, "reviewed_at": definition.reviewed_at, "dry_run": args.dry_run, "member_count": len(members), "errors": errors, "missing_security_records": missing_security, "missing_security_master_records": missing_security, "security_id_mismatches": security_id_mismatches, "provider_mapping_warnings": invalid_provider_mapping, "applied": False, "review_gate": "human reviewed metadata is required before apply"}
    if args.apply and not errors and not missing_security and not invalid_provider_mapping and not security_id_mismatches:
        service.import_reviewed(definition, members); report["applied"] = True
    elif args.apply:
        report["errors"] = [*errors, *("security_master_record_missing" for _ in missing_security), *("security_id_mismatch" for _ in security_id_mismatches), *("history_provider_mapping_missing" for _ in invalid_provider_mapping)]
    rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
    if args.json_output: args.json_output.write_text(rendered + "\n")
    return 0 if args.dry_run or report["applied"] else 1


if __name__ == "__main__": raise SystemExit(main())

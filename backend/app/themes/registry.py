from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.themes.identifiers import normalize_theme_id
from app.themes.models import ThemeDefinition, ThemeMember


def read_definition_markdown(path: str | Path) -> ThemeDefinition:
    text = Path(path).read_text()
    frontmatter = parse_frontmatter(text)
    references = tuple(
        {"title": item.partition(" @ ")[0].strip(), "url": item.partition(" @ ")[2].strip(), "retrieved_at": frontmatter.get("verification_date", "")}
        for item in frontmatter.get("source_references", "").split(";") if item.strip()
    )
    return ThemeDefinition(
        theme_id=normalize_theme_id(frontmatter["theme_id"]), display_name=frontmatter["display_name"], description=frontmatter["description"], version=frontmatter["version"], status=frontmatter["status"], effective_from=frontmatter["effective_from"], methodology=frontmatter["methodology"], inclusion_criteria=frontmatter["inclusion_criteria"], exclusion_criteria=frontmatter["exclusion_criteria"], weighting_policy=frontmatter["weighting_policy"], primary_benchmark=frontmatter.get("primary_benchmark", "SPY"), secondary_benchmark=frontmatter.get("secondary_benchmark") or None, parent_sector_ids=tuple(value.strip() for value in frontmatter.get("parent_sector_ids", "").split(",") if value.strip()), minimum_members=int(frontmatter.get("minimum_members", "3")), complete_coverage_threshold=float(frontmatter.get("complete_coverage_threshold", ".9")), partial_coverage_threshold=float(frontmatter.get("partial_coverage_threshold", ".75")), source_references=references, verification_date=frontmatter.get("verification_date") or None, reviewed_at=frontmatter.get("reviewed_at") or None, reviewed_by=frontmatter.get("reviewed_by") or None, review_commit=frontmatter.get("review_commit") or None, amends_version=frontmatter.get("amends_version") or None, amendment_reason=frontmatter.get("amendment_reason") or None, methodology_change=as_bool(frontmatter.get("methodology_change")), membership_change=as_bool(frontmatter.get("membership_change")), corporate_action_amendment=as_bool(frontmatter.get("corporate_action_amendment")), correction_metadata=as_json_object(frontmatter.get("correction_metadata")), notes=frontmatter.get("notes") or None,
    )


def read_members_csv(path: str | Path, definition: ThemeDefinition) -> list[ThemeMember]:
    result: list[ThemeMember] = []
    with Path(path).open(newline="") as handle:
        for row in csv.DictReader(handle):
            result.append(ThemeMember(
                theme_id=definition.theme_id, theme_version=definition.version, ticker=(row.get("ticker") or "").upper(), security_id=row.get("security_id") or None, company_name=row.get("company_name") or row.get("ticker") or "", role=row.get("role") or "core", weight=float(row.get("weight") or 0), effective_from=row.get("effective_from") or definition.effective_from, active=as_bool(row.get("active"), default=True), membership_source=row.get("membership_source") or "proposed-reference", inclusion_reason=row.get("inclusion_reason") or "", reviewed_at=row.get("reviewed_at") or None, reviewed_by=row.get("reviewed_by") or None, purity=as_int(row.get("purity")), importance=as_int(row.get("importance")), previous_ticker=(row.get("previous_ticker") or "").upper() or None, previous_company_name=row.get("previous_company_name") or None, corporate_action_type=row.get("corporate_action_type") or None, corporate_action_effective_date=row.get("corporate_action_effective_date") or None, continuity_status=row.get("continuity_status") or None, history_continuity_required=as_bool(row.get("history_continuity_required")), notes=row.get("notes") or None,
            ))
    return result


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---": raise ValueError("theme_definition_frontmatter_required")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---": break
        key, separator, value = line.partition(":")
        if separator: result[key.strip()] = value.strip()
    return result


def as_bool(value: str | None, *, default: bool = False) -> bool:
    return default if value is None or value == "" else value.strip().lower() in {"true", "1", "yes"}


def as_int(value: str | None) -> int | None:
    return int(value) if value and value.strip() else None


def as_json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("theme_correction_metadata_must_be_object")
    return decoded

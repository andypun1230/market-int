from __future__ import annotations

from datetime import date
from typing import Any

from app.securities.registry import normalized_sector, provider_symbol_for


SOURCE_COLUMNS = (
    "ticker",
    "company_name",
    "exchange",
    "sector",
    "industry",
    "active",
    "quote_provider_symbol",
    "history_provider_symbol",
    "asset_type",
    "source",
    "source_effective_date",
    "verified_at",
)
REQUIRED_SOURCE_VALUES = tuple(column for column in SOURCE_COLUMNS if column != "industry")
ALLOWED_EXCHANGES = {"NASDAQ", "NYSE", "NYSE ARCA"}


def validate_reviewed_source_rows(rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> list[str]:
    """Validate the maintainer-reviewed CSV contract before an import mutates storage."""
    errors: list[str] = []
    missing_columns = sorted(set(SOURCE_COLUMNS) - set(fieldnames or SOURCE_COLUMNS))
    if missing_columns:
        return [f"file:missing_columns:{','.join(missing_columns)}"]

    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        ticker = str(row.get("ticker") or "").strip().upper()
        prefix = f"row:{row_number}"
        if not ticker:
            errors.append(f"{prefix}:missing_ticker")
            continue
        if ticker in seen:
            errors.append(f"{prefix}:duplicate_ticker:{ticker}")
        seen.add(ticker)
        for field in REQUIRED_SOURCE_VALUES:
            if not str(row.get(field) or "").strip():
                errors.append(f"{prefix}:missing_{field}")
        if str(row.get("active") or "").strip().lower() not in {"true", "1", "yes"}:
            errors.append(f"{prefix}:inactive_member:{ticker}")
        if str(row.get("asset_type") or "").strip().lower() != "equity":
            errors.append(f"{prefix}:invalid_asset_type:{ticker}")
        if str(row.get("exchange") or "").strip().upper() not in ALLOWED_EXCHANGES:
            errors.append(f"{prefix}:invalid_exchange:{ticker}")
        if normalized_sector(row.get("sector")) == "Unknown":
            errors.append(f"{prefix}:missing_sector:{ticker}")
        provider_symbol = provider_symbol_for(ticker)
        for field in ("quote_provider_symbol", "history_provider_symbol"):
            if str(row.get(field) or "").strip().upper() != provider_symbol:
                errors.append(f"{prefix}:unexpected_{field}:{ticker}")
        for field in ("source_effective_date", "verified_at"):
            try:
                date.fromisoformat(str(row.get(field) or ""))
            except ValueError:
                errors.append(f"{prefix}:invalid_{field}:{ticker}")
    return errors

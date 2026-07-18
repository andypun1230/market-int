from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from typing import Any

from app.securities.models import BreadthUniverse, BreadthUniverseMember, SecurityRecord, UniverseImportReport
from app.securities.registry import SP100_SOURCE_NAME, normalized_sector, provider_symbol_for
from app.securities.storage import SecurityMasterStorage


class SecurityMasterService:
    def __init__(self, storage: SecurityMasterStorage | None = None) -> None:
        self.storage = storage or SecurityMasterStorage()

    def import_universe(self, *, name: str, version: str, effective_date: str, benchmark_symbol: str, rows: list[dict[str, Any]], source: str = SP100_SOURCE_NAME, source_timestamp: str | None = None, notes: str | None = None, dry_run: bool = True) -> UniverseImportReport:
        normalized, invalid = self._normalize_rows(rows)
        active = self.storage.get_active_universe(name)
        old = {member.ticker for member in self.storage.members(active.universe_id)} if active else set()
        current = {row["ticker"] for row in normalized}
        warnings = tuple(sorted(row["ticker"] for row in normalized if not row["history_provider_symbol"]))
        universe_id = f"{name.lower().replace(' ', '-')}-{version}"
        report = UniverseImportReport(universe_id=universe_id, dry_run=dry_run, additions=tuple(sorted(current - old)), removals=tuple(sorted(old - current)), unchanged=tuple(sorted(old & current)), invalid=tuple(invalid), provider_mapping_warnings=warnings, member_count=len(normalized), source=source, source_timestamp=source_timestamp)
        if invalid or dry_run:
            return report
        now = datetime.now(timezone.utc).isoformat()
        members: list[BreadthUniverseMember] = []
        for row in normalized:
            security_id = self._security_id(row["ticker"])
            row_source = row.get("source") or source
            row_source_timestamp = row.get("source_effective_date") or source_timestamp
            row_verified_at = row.get("verified_at") or now
            self.storage.upsert_security(SecurityRecord(security_id=security_id, ticker=row["ticker"], company_name=row["company_name"], exchange=row.get("exchange", "US"), asset_type=row.get("asset_type", "equity"), active=row["active"], sector=row["sector"], industry=row.get("industry"), quote_provider_symbol=row["quote_provider_symbol"], history_provider_symbol=row["history_provider_symbol"], index_memberships=(name,), effective_from=row_source_timestamp or effective_date, source=row_source, source_timestamp=row_source_timestamp, verified_at=row_verified_at))
            members.append(BreadthUniverseMember(universe_id=universe_id, security_id=security_id, ticker=row["ticker"], sector=row["sector"], active=row["active"], weight=row.get("weight"), effective_from=row_source_timestamp or effective_date, membership_source=row_source))
        universe = BreadthUniverse(universe_id=universe_id, name=name, version=version, benchmark_symbol=benchmark_symbol.upper(), effective_date=effective_date, created_at=now, source=source, source_timestamp=source_timestamp, member_count=len(members), notes=notes)
        self.storage.publish_universe(universe, members)
        return report

    def _normalize_rows(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        normalized: list[dict[str, Any]] = []
        invalid: list[str] = []
        seen: set[str] = set()
        for index, raw in enumerate(rows):
            ticker = str(raw.get("ticker") or raw.get("symbol") or "").strip().upper()
            if not ticker or ticker in seen:
                invalid.append(f"row:{index}:duplicate_or_missing_ticker")
                continue
            sector = normalized_sector(raw.get("sector"))
            if sector == "Unknown":
                invalid.append(f"{ticker}:missing_sector")
                continue
            seen.add(ticker)
            active = str(raw.get("active", "true")).strip().lower() in {"1", "true", "yes"}
            normalized.append({"ticker": ticker, "company_name": str(raw.get("company_name") or raw.get("name") or ticker).strip(), "sector": sector, "industry": raw.get("industry"), "exchange": str(raw.get("exchange") or "US"), "asset_type": str(raw.get("asset_type") or "equity"), "active": active, "quote_provider_symbol": str(raw.get("quote_provider_symbol") or provider_symbol_for(ticker)).upper(), "history_provider_symbol": str(raw.get("history_provider_symbol") or provider_symbol_for(ticker)).upper(), "weight": raw.get("weight"), "source": str(raw.get("source") or "").strip() or None, "source_effective_date": str(raw.get("source_effective_date") or "").strip() or None, "verified_at": str(raw.get("verified_at") or "").strip() or None})
        return normalized, invalid

    @staticmethod
    def _security_id(ticker: str) -> str:
        return f"sec-{hashlib.sha256(ticker.encode('utf-8')).hexdigest()[:16]}"


_service_lock = threading.RLock()
_service: SecurityMasterService | None = None


def get_security_master_service() -> SecurityMasterService:
    global _service
    with _service_lock:
        if _service is None:
            _service = SecurityMasterService()
        return _service


def reset_security_master_service() -> None:
    global _service
    with _service_lock:
        _service = None

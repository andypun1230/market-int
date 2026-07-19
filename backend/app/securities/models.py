from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SecurityRecord:
    security_id: str
    ticker: str
    company_name: str
    exchange: str = "US"
    asset_type: str = "equity"
    active: bool = True
    sector: str = "Unknown"
    sector_id: str | None = None
    industry: str | None = None
    quote_provider_symbol: str | None = None
    history_provider_symbol: str | None = None
    currency: str = "USD"
    country: str = "US"
    index_memberships: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    source: str = "maintainer-import"
    source_timestamp: str | None = None
    verified_at: str | None = None
    metadata_version: int = 1

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        data["index_memberships"] = list(self.index_memberships)
        return data


@dataclass(frozen=True)
class BreadthUniverse:
    universe_id: str
    name: str
    version: str
    benchmark_symbol: str
    effective_date: str
    created_at: str
    source: str
    source_timestamp: str | None
    member_count: int
    enabled: bool = True
    notes: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BreadthUniverseMember:
    universe_id: str
    security_id: str
    ticker: str
    sector: str
    sector_id: str | None = None
    active: bool = True
    weight: float | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    membership_source: str = "maintainer-import"

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniverseImportReport:
    universe_id: str
    dry_run: bool
    additions: tuple[str, ...] = ()
    removals: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    invalid: tuple[str, ...] = ()
    provider_mapping_warnings: tuple[str, ...] = ()
    member_count: int = 0
    source: str | None = None
    source_timestamp: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        for name in ("additions", "removals", "unchanged", "invalid", "provider_mapping_warnings"):
            data[name] = list(data[name])
        return data

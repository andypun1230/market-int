from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SectorSnapshot:
    snapshot_id: str
    schema_version: int
    universe_id: str
    universe_version: str
    market_date: str
    generated_at: str
    status: str
    coverage: dict[str, Any]
    benchmark: str
    source_state: str
    provider_provenance: dict[str, Any]
    sectors: tuple[dict[str, Any], ...]
    rankings: tuple[str, ...]
    rotation_summary: str
    alerts: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    input_hash: str = ""
    semantics_version: str = "market-semantics-v1"

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

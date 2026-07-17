from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


StockSnapshotStatus = Literal["complete", "partial", "stale", "unavailable", "initializing"]
StockSectionStatus = Literal["complete", "partial", "stale", "unavailable"]


class StockSnapshotSection(BaseModel):
    status: StockSectionStatus
    calculated_at: str
    coverage: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    payload: Any = None


class StockAnalysisSnapshot(BaseModel):
    snapshot_id: str
    version: int = 1
    snapshot_schema_version: int = 2
    symbol: str
    created_at: str
    published_at: str
    expires_at: str
    stale_until: str
    status: StockSnapshotStatus
    source_state: str = "unavailable"
    data_mode: str = "unknown"
    test_data: bool = False
    mock_data: bool = False
    configuration_signature: str | None = None
    algorithm_version: str = "unknown"
    history_provider: str | None = None
    quote_provider: str | None = None
    latest_history_timestamp: str | None = None
    latest_history_date: str | None = None
    input_hash: str
    coverage_ratio: float
    warnings: list[str] = Field(default_factory=list)
    missing_dependencies: list[str] = Field(default_factory=list)
    build_duration_ms: int | None = None
    sections: dict[str, StockSnapshotSection] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def section_payload(self, name: str) -> Any:
        section = self.sections.get(name)
        return section.payload if section else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(0, seconds))).isoformat()

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


SnapshotStatus = Literal["complete", "partial", "stale", "unavailable", "initializing"]
SectionStatus = Literal["complete", "partial", "stale", "unavailable"]


class SnapshotSection(BaseModel):
    status: SectionStatus
    calculated_at: str
    source_state: str = "unavailable"
    coverage_ratio: float = 0.0
    dependencies_requested: int = 0
    dependencies_available: int = 0
    dependencies_missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
    payload: Any = None


class InputCoverage(BaseModel):
    required_requested: int = 0
    required_available: int = 0
    optional_requested: int = 0
    optional_available: int = 0
    coverage_ratio: float = 0.0
    missing_required: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)


class MarketSnapshot(BaseModel):
    snapshot_id: str
    # Version 2 adds the persisted semantic contract carried by the breadth,
    # health, decision, and home sections. Older immutable snapshots remain
    # readable as version 1.
    version: int = 2
    status: SnapshotStatus
    created_at: str
    market_timestamp: str | None = None
    published_at: str
    expires_at: str
    stale_until: str | None = None
    build_started_at: str
    build_completed_at: str
    build_duration_ms: int
    input_fetch_duration_ms: int | None = None
    input_coverage: InputCoverage
    source_summary: dict[str, Any] = Field(default_factory=dict)
    freshness: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_dependencies: list[str] = Field(default_factory=list)
    sections: dict[str, SnapshotSection] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def section_payload(self, name: str) -> Any:
        section = self.sections.get(name)
        return section.payload if section else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

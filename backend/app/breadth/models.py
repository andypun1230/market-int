from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.market_history.storage import DailyBar
from app.securities.models import BreadthUniverse, BreadthUniverseMember


@dataclass(frozen=True)
class BreadthCalculationInput:
    universe: BreadthUniverse
    members: tuple[BreadthUniverseMember, ...]
    market_date: str
    histories: dict[str, tuple[DailyBar, ...]]
    benchmark_history: tuple[DailyBar, ...] = ()
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BreadthCalculationResult:
    market_date: str
    core: dict[str, Any]
    coverage: dict[str, Any]
    sectors: list[dict[str, Any]]
    score: float | None
    classification: str
    trend: str
    confidence: str
    warnings: list[str]
    input_hash: str


@dataclass(frozen=True)
class BreadthSnapshot:
    snapshot_id: str
    universe_id: str
    universe_version: str
    market_date: str
    created_at: str
    published_at: str
    status: str
    score: float | None
    classification: str
    trend: str
    confidence: str
    coverage: dict[str, Any]
    advance_decline: dict[str, Any]
    moving_average_breadth: dict[str, Any]
    highs_lows: dict[str, Any]
    sector_breadth: list[dict[str, Any]]
    divergences: list[dict[str, Any]]
    source_state: str
    providers: list[str]
    latest_input_timestamp: str | None
    oldest_input_timestamp: str | None
    timestamp_skew: int | None
    warnings: list[str]
    missing_dependencies: list[str]
    calculation_version: str
    input_hash: str
    sections: dict[str, dict[str, Any]]

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

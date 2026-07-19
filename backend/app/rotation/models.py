from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


RotationStatus = Literal["complete", "partial", "insufficient_history", "test", "unavailable"]


@dataclass(frozen=True)
class RotationPoint:
    market_date: str
    raw_rs: float
    raw_momentum: float
    plotted_x: float
    plotted_y: float
    quadrant: str
    source_series_ids: tuple[str, ...]
    source_provider: str
    is_current: bool
    is_synthetic: bool
    compatibility_signature: str
    snapshot_id: str | None = None

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RotationSeries:
    entity_type: Literal["sector", "theme"]
    entity_id: str
    display_name: str
    short_label: str
    benchmark_symbol: str
    interval: str
    formula_version: str
    normalization_version: str
    source_state: str
    data_mode: str
    universe_id: str | None
    universe_version: str | None
    coverage_ratio: float | None
    status: RotationStatus
    current_point: RotationPoint | None
    earliest_market_date: str | None
    latest_market_date: str | None
    point_count: int
    synthetic_point_count: int
    compatibility_signature: str
    trail_points: tuple[RotationPoint, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def model_dump(self) -> dict[str, object]:
        value = asdict(self)
        value["trail_points"] = [point.model_dump() for point in self.trail_points]
        value["current_point"] = self.current_point.model_dump() if self.current_point else None
        return value

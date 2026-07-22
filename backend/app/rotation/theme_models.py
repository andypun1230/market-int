from __future__ import annotations

from typing import Any, Literal, TypedDict


ThemeRotationStatus = Literal["complete", "partial", "insufficient_history", "unavailable"]


class ThemeRotationObservation(TypedDict, total=False):
    theme_id: str
    model_version: str
    profile: str
    observation_date: str
    market_date: str
    relative_trend: float
    relative_momentum: float
    quadrant: str
    theme_index_value: float
    benchmark_index_value: float
    benchmark_adjusted_close: float
    relative_price: float
    relative_price_rebased: float
    relative_price_change: float
    trend_change: float
    coverage_ratio: float
    eligible_constituent_count: int
    total_constituent_count: int
    status: str
    confidence: dict[str, Any]
    evidence: list[str]
    missing_data: list[str]
    winsorized_flags: dict[str, bool]
    normalization_metadata: dict[str, Any]
    direction: str
    speed: float
    dx: float
    dy: float
    direction_angle: float
    is_current: bool
    is_synthetic: bool


class ThemeRotationTail(TypedDict, total=False):
    theme_id: str
    profile: str
    observations: list[ThemeRotationObservation]
    current_observation: ThemeRotationObservation | None
    direction: str
    speed: float
    distance_travelled: float
    net_displacement: float
    recent_acceleration: float
    quadrant_transitions: int
    latest_common_date: str | None


class ThemeRotationSnapshotPayload(TypedDict, total=False):
    snapshot_id: str | None
    taxonomy_version: str | None
    rotation_model_id: str
    rotation_model_version: str
    benchmark: str
    profile: str
    profile_definition: dict[str, Any]
    as_of: str | None
    latest_common_date: str | None
    status: str
    eligible_count: int
    excluded_count: int
    quadrant_counts: dict[str, int]
    tails: list[ThemeRotationTail]
    exclusions: list[dict[str, str]]
    evidence_metadata: dict[str, Any]
    normalization_metadata: dict[str, Any]


from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ThemeStatus = Literal["proposed", "reviewed", "active", "retired"]
ThemeRole = Literal["core", "enabler", "infrastructure", "beneficiary", "adjacent"]


@dataclass(frozen=True)
class ThemeDefinition:
    theme_id: str
    display_name: str
    description: str
    version: str
    status: ThemeStatus
    effective_from: str
    methodology: str
    inclusion_criteria: str
    exclusion_criteria: str
    weighting_policy: str
    primary_benchmark: str
    secondary_benchmark: str | None
    parent_sector_ids: tuple[str, ...]
    minimum_members: int
    complete_coverage_threshold: float
    partial_coverage_threshold: float
    source_references: tuple[dict[str, str], ...]
    verification_date: str | None
    schema_version: int = 1
    effective_to: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    review_commit: str | None = None
    amends_version: str | None = None
    amendment_reason: str | None = None
    methodology_change: bool = False
    membership_change: bool = False
    corporate_action_amendment: bool = False
    correction_metadata: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None

    def model_dump(self) -> dict[str, Any]:
        value = asdict(self)
        value["parent_sector_ids"] = list(self.parent_sector_ids)
        value["source_references"] = [dict(item) for item in self.source_references]
        return value


@dataclass(frozen=True)
class ThemeMember:
    theme_id: str
    theme_version: str
    ticker: str
    security_id: str | None
    company_name: str
    role: ThemeRole
    weight: float
    effective_from: str
    active: bool
    membership_source: str
    inclusion_reason: str
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    effective_to: str | None = None
    purity: int | None = None
    importance: int | None = None
    previous_ticker: str | None = None
    previous_company_name: str | None = None
    corporate_action_type: str | None = None
    corporate_action_effective_date: str | None = None
    continuity_status: str | None = None
    history_continuity_required: bool = False
    notes: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeBasketBar:
    theme_id: str
    theme_version: str
    session_date: str
    index_level: float
    daily_return: float
    eligible_members: int
    total_members: int
    coverage_ratio: float
    source_state: str
    formula_version: str
    input_hash: str
    generated_at: str

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeBuildInput:
    definition: ThemeDefinition
    members: tuple[ThemeMember, ...]
    histories: dict[str, tuple[Any, ...]]
    benchmark_history: tuple[Any, ...]
    source_state: str
    market_date: str
    previous_snapshot: dict[str, Any] | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

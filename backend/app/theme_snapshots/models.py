from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ThemeSnapshot:
    snapshot_id: str
    schema_version: int
    market_date: str
    generated_at: str
    published_at: str
    status: str
    source_state: str
    active_theme_versions: tuple[dict[str, str], ...]
    member_coverage: dict[str, Any]
    providers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    rankings: tuple[str, ...]
    rotation_summary: str
    overlap_matrix: tuple[dict[str, Any], ...]
    alerts: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    input_hash: str = ""
    formula_version: str = "theme-leadership-composite-v1"
    configuration_signature: str = ""
    taxonomy_version: str | None = None
    repository_stats: dict[str, Any] = field(default_factory=dict)
    coverage_audit: tuple[dict[str, Any], ...] = ()

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

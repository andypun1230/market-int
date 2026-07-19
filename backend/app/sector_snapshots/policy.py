from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorPolicy:
    calculation_version: str = "sector-snapshot-v1"
    complete_constituent_coverage: float = 0.95
    partial_constituent_coverage: float = 0.50
    complete_etf_coverage: float = 1.0
    minimum_history_days: int = 200

    # Score components are explicit and bounded. Returns are capped before
    # conversion so one extreme interval cannot dominate sector leadership.
    def score_return(self, value: float | None, cap: float = 15.0) -> float | None:
        if value is None:
            return None
        return round(max(0.0, min(100.0, 50.0 + (value / cap) * 50.0)), 2)

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BreadthPolicy:
    ema20_min_bars: int = 20
    ema50_min_bars: int = 50
    ema200_min_bars: int = 200
    high_low_min_bars: int = 252
    stale_sessions: int = 5
    min_complete_coverage: float = 0.90
    min_partial_coverage: float = 0.75
    equality_tolerance: float = 1e-9
    calculation_version: str = "breadth-v1"

    @classmethod
    def from_environment(cls) -> "BreadthPolicy":
        return cls(
            min_complete_coverage=float(os.getenv("BREADTH_MIN_COMPLETE_COVERAGE", "0.90")),
            min_partial_coverage=float(os.getenv("BREADTH_MIN_PARTIAL_COVERAGE", "0.75")),
        )


WEIGHTS = {
    "percent_above_20ema": 0.15,
    "percent_above_50ema": 0.30,
    "percent_above_200ema": 0.25,
    "daily_participation": 0.15,
    "leadership": 0.15,
}


def classify_score(score: float | None) -> str:
    if score is None:
        return "unavailable"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "healthy"
    if score >= 45:
        return "mixed"
    if score >= 30:
        return "weak"
    return "oversold"

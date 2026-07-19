from __future__ import annotations

from dataclasses import dataclass


ROTATION_FORMULA_VERSION = "relative-return-momentum-v1"
ROTATION_NORMALIZATION_VERSION = "midpoint-100-relative-return-v1"


@dataclass(frozen=True)
class RotationIntervalPolicy:
    interval: str
    rs_lookback_sessions: int
    momentum_lookback_sessions: int
    sample_step_sessions: int
    point_count: int = 5


INTERVAL_POLICIES: dict[str, RotationIntervalPolicy] = {
    "1W": RotationIntervalPolicy("1W", rs_lookback_sessions=5, momentum_lookback_sessions=1, sample_step_sessions=1),
    "1M": RotationIntervalPolicy("1M", rs_lookback_sessions=21, momentum_lookback_sessions=5, sample_step_sessions=5),
    "3M": RotationIntervalPolicy("3M", rs_lookback_sessions=63, momentum_lookback_sessions=21, sample_step_sessions=15),
}


def policy_for(interval: str) -> RotationIntervalPolicy:
    normalized = interval.upper()
    if normalized not in INTERVAL_POLICIES:
        raise ValueError(f"Unsupported rotation interval: {interval}")
    return INTERVAL_POLICIES[normalized]

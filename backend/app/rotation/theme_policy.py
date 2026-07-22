from __future__ import annotations

from dataclasses import asdict, dataclass


THEME_ROTATION_MODEL_ID = "theme-relative-trend-momentum"
THEME_ROTATION_MODEL_VERSION = "theme-relative-trend-momentum-v1"
THEME_ROTATION_NORMALIZATION_VERSION = "zero-centered-rolling-robust-scale-v1"
THEME_ROTATION_EFFECTIVE_FROM = "2026-07-23"
THEME_ROTATION_BENCHMARK = "SPY"


@dataclass(frozen=True)
class ThemeRotationProfile:
    profile: str
    interval_alias: str
    sampling_frequency: str
    fast_window: int
    slow_window: int
    volatility_window: int
    normalization_window: int
    momentum_lag: int
    momentum_smoothing: int
    tail_observations: int
    observation_spacing: int
    trend_scale: float = 2.0
    momentum_scale: float = 2.0
    winsor_limit: float = 3.0
    epsilon: float = 1e-8

    def model_dump(self) -> dict[str, object]:
        return {
            **asdict(self),
            "model_id": THEME_ROTATION_MODEL_ID,
            "model_version": THEME_ROTATION_MODEL_VERSION,
            "normalization_method": THEME_ROTATION_NORMALIZATION_VERSION,
            "benchmark": THEME_ROTATION_BENCHMARK,
            "effective_from": THEME_ROTATION_EFFECTIVE_FROM,
        }


THEME_ROTATION_PROFILES: dict[str, ThemeRotationProfile] = {
    "short": ThemeRotationProfile(
        profile="short",
        interval_alias="1W",
        sampling_frequency="daily",
        fast_window=10,
        slow_window=30,
        volatility_window=30,
        normalization_window=60,
        momentum_lag=3,
        momentum_smoothing=5,
        tail_observations=8,
        observation_spacing=1,
    ),
    "medium": ThemeRotationProfile(
        profile="medium",
        interval_alias="1M",
        sampling_frequency="daily",
        fast_window=20,
        slow_window=50,
        volatility_window=50,
        normalization_window=126,
        momentum_lag=5,
        momentum_smoothing=10,
        tail_observations=10,
        observation_spacing=3,
    ),
    "long": ThemeRotationProfile(
        profile="long",
        interval_alias="3M",
        sampling_frequency="weekly_last_complete_session",
        fast_window=10,
        slow_window=26,
        volatility_window=26,
        normalization_window=52,
        momentum_lag=4,
        momentum_smoothing=4,
        tail_observations=8,
        observation_spacing=1,
    ),
}

PROFILE_BY_INTERVAL = {value.interval_alias: value for value in THEME_ROTATION_PROFILES.values()}


def theme_profile_for(value: str) -> ThemeRotationProfile:
    normalized = value.strip()
    profile = THEME_ROTATION_PROFILES.get(normalized.lower()) or PROFILE_BY_INTERVAL.get(normalized.upper())
    if profile is None:
        raise ValueError(f"Unsupported theme rotation profile: {value}")
    return profile


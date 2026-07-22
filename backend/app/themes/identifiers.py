from __future__ import annotations

from app.themes.launch import LAUNCH_THEMES

_LEGACY_THEME_IDS = (
    "memory_storage",
    "cybersecurity",
    "ai_infrastructure",
    "semiconductors",
    "cloud_data_centers",
    "defense_aerospace",
)

THEME_ID_ALIASES = {
    "memory_storage": "memory_storage",
    "memory-storage": "memory_storage",
    "cybersecurity": "cybersecurity",
    "ai_infrastructure": "ai_infrastructure",
    "ai-infrastructure": "ai_infrastructure",
    "semiconductors": "semiconductors",
    "cloud_data_centers": "cloud_data_centers",
    "cloud-data-centers": "cloud_data_centers",
    "defense_aerospace": "defense_aerospace",
    "defense-aerospace": "defense_aerospace",
}

# Stage 8.75 expands accepted identifiers without changing the canonical IDs
# used by immutable pilot snapshots and durable Phase 4.4D storage.
for _definition in LAUNCH_THEMES:
    for _alias in _definition.aliases:
        # The durable identifier normalizer intentionally remains stricter
        # than user-facing taxonomy search: display names are not storage IDs.
        if " " not in _alias.strip():
            THEME_ID_ALIASES.setdefault(_alias.strip().lower(), _definition.id)
    THEME_ID_ALIASES.setdefault(_definition.id, _definition.id)

CANONICAL_THEME_IDS = tuple(dict.fromkeys((*_LEGACY_THEME_IDS, *(item.id for item in LAUNCH_THEMES))))


def normalize_theme_id(value: str) -> str:
    normalized = value.strip().lower()
    canonical = THEME_ID_ALIASES.get(normalized)
    if canonical is None:
        raise ValueError(f"unknown_theme_id:{value}")
    return canonical


def try_normalize_theme_id(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_theme_id(value)

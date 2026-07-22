from __future__ import annotations

CANONICAL_THEME_IDS = (
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

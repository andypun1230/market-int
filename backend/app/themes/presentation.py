from __future__ import annotations


def format_taxonomy_label(value: str) -> str:
    """Render a persisted taxonomy ID without changing its canonical value."""
    return " ".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)

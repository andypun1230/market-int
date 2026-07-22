from __future__ import annotations

from pathlib import Path

from app.themes.identifiers import normalize_theme_id
from app.themes.models import ThemeDefinition, ThemeMember
from app.themes.registry import read_definition_markdown, read_members_csv


REFERENCE_THEME_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "reference" / "themes"


def reference_definitions() -> tuple[list[ThemeDefinition], list[str]]:
    definitions: list[ThemeDefinition] = []
    errors: list[str] = []
    for path in sorted(REFERENCE_THEME_DIRECTORY.glob("*-v*.md")):
        try:
            definition = read_definition_markdown(path)
            definitions.append(definition)
        except Exception as exc:
            errors.append(f"{path.name}:{type(exc).__name__}:{exc}")
    definitions.sort(key=lambda definition: (definition.theme_id, _version_key(definition.version)))
    return definitions, errors


def reference_definition(theme_id: str) -> ThemeDefinition | None:
    canonical = normalize_theme_id(theme_id)
    definitions, _errors = reference_definitions()
    matches = [definition for definition in definitions if definition.theme_id == canonical]
    return max(matches, key=lambda definition: _version_key(definition.version), default=None)


def reference_members(theme_id: str, version: str | None = None) -> tuple[list[ThemeMember], list[str]]:
    canonical = normalize_theme_id(theme_id)
    errors: list[str] = []
    matches: list[tuple[Path, ThemeDefinition]] = []
    for path in sorted(REFERENCE_THEME_DIRECTORY.glob("*-v*.md")):
        try:
            definition = read_definition_markdown(path)
            if definition.theme_id == canonical and (version is None or definition.version == version):
                matches.append((path, definition))
        except Exception as exc:
            errors.append(f"{path.name}:{type(exc).__name__}:{exc}")
    if matches:
        path, definition = max(matches, key=lambda item: _version_key(item[1].version))
        return read_members_csv(path.with_suffix(".csv"), definition), errors
    return [], errors


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.removeprefix("v").split(".") if part.isdigit())

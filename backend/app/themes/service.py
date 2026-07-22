from __future__ import annotations

from app.themes.models import ThemeDefinition, ThemeMember
from app.themes.policy import live_definition_allowed, validate_definition
from app.themes.storage import ThemeStorage


class ThemeDefinitionService:
    def __init__(self, storage: ThemeStorage | None = None) -> None:
        self.storage = storage or ThemeStorage()

    def validate_import(self, definition: ThemeDefinition, members: list[ThemeMember], *, require_reviewed: bool = True) -> list[str]:
        return validate_definition(definition, members, require_reviewed=require_reviewed)

    def import_reviewed(self, definition: ThemeDefinition, members: list[ThemeMember]) -> None:
        errors = self.validate_import(definition, members, require_reviewed=True)
        if errors: raise ValueError(",".join(errors))
        self.storage.save_definition(definition, members)

    def active(self) -> list[tuple[ThemeDefinition, list[ThemeMember]]]:
        # Active versions remain immutable audit records; only the newest
        # reviewed version for each Theme is current for new snapshots.
        current: dict[str, ThemeDefinition] = {}
        for definition in self.storage.active_definitions():
            previous = current.get(definition.theme_id)
            if previous is None or version_key(definition.version) > version_key(previous.version):
                current[definition.theme_id] = definition
        result: list[tuple[ThemeDefinition, list[ThemeMember]]] = []
        for definition in current.values():
            members = self.storage.members(definition.theme_id, definition.version)
            if live_definition_allowed(definition, members): result.append((definition, members))
        return sorted(result, key=lambda item: item[0].theme_id)


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.removeprefix("v").split(".") if part.isdigit())

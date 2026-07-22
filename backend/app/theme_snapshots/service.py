from __future__ import annotations

import threading
import os
from typing import Any

from app.theme_snapshots.builder import ThemeSnapshotBuilder, theme_namespace
from app.theme_snapshots.models import ThemeSnapshot
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.securities.service import get_security_master_service
from app.themes.catalog import reference_definitions, reference_members


class ThemeSnapshotService:
    def __init__(self, storage: ThemeSnapshotStorage | None = None) -> None:
        self.storage = storage or ThemeSnapshotStorage(); self.builder = ThemeSnapshotBuilder(snapshot_storage=self.storage); self._lock = threading.Lock()

    def latest(self) -> ThemeSnapshot | None: return self.storage.latest(theme_namespace())
    def history(self, days: int = 90) -> list[dict[str, Any]]: return self.storage.history(theme_namespace(), days)
    def build_now(self, *, publish: bool = True) -> ThemeSnapshot | None:
        if not self._lock.acquire(blocking=False): return self.latest()
        try: return self.builder.build(publish=publish)
        finally: self._lock.release()

    def status(self) -> dict[str, Any]:
        snapshot = self.latest()
        persisted_rows = self.builder.theme_storage.definitions()
        persisted = {(definition.theme_id, definition.version): definition for definition in persisted_rows}
        references, package_errors = reference_definitions()
        definitions = {(definition.theme_id, definition.version): definition for definition in references}
        definitions.update(persisted)
        values = sorted(definitions.values(), key=lambda definition: (definition.theme_id, _version_key(definition.version)))
        latest_by_id = {definition.theme_id: definition for definition in values}
        active = self.builder.definition_service.active()
        security_master = get_security_master_service().storage

        def review_status(definition: Any) -> str:
            if definition.status == "active" and definition.reviewed_at and definition.reviewed_by:
                return "active"
            if definition.status == "reviewed" and definition.reviewed_at and definition.reviewed_by:
                return "reviewed"
            return "awaiting_review"

        def missing_security(definition: Any) -> list[str]:
            members = self.builder.theme_storage.members(definition.theme_id, definition.version) if (definition.theme_id, definition.version) in persisted else reference_members(definition.theme_id, definition.version)[0]
            if not members:
                return []
            return sorted(member.ticker for member in members if security_master.security(member.ticker) is None)

        pilot_themes = []
        for theme_id in ("memory_storage", "cybersecurity"):
            definition = latest_by_id.get(theme_id)
            if definition is None:
                continue
            pilot_themes.append({"theme_id": definition.theme_id, "display_name": definition.display_name, "definition_status": definition.status, "review_status": review_status(definition), "missing_security_records": missing_security(definition)})
        published = bool(snapshot and snapshot.source_state == "live" and snapshot.status in {"complete", "partial"})
        # Definitions are immutable. Status reports the current reviewed Theme
        # count, while `active_definition_version_count` preserves the audit
        # count of version records.
        reviewed_count = sum(review_status(definition) in {"reviewed", "active"} for definition in latest_by_id.values())
        active_count = len(active)
        blockers = []
        if not reviewed_count: blockers.append("human_review_required")
        if not active_count: blockers.append("pilot_definitions_not_active")
        if package_errors: blockers.append("malformed_definition_package")
        status = "live" if published else "awaiting_review" if not reviewed_count else "awaiting_snapshot"
        return {
            "status": status,
            "reason_code": None if published else "no_reviewed_theme_snapshot",
            "architecture_ready": True,
            "proposed_definition_count": sum(definition.status == "proposed" for definition in values),
            "reviewed_definition_count": reviewed_count,
            "active_definition_count": active_count,
            "active_definition_version_count": sum(definition.status == "active" for definition in persisted_rows),
            "published_snapshot": published,
            "latest_snapshot_id": snapshot.snapshot_id if snapshot else None,
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "market_date": snapshot.market_date if snapshot else None,
            "coverage": snapshot.member_coverage if snapshot else {},
            "source_state": snapshot.source_state if snapshot else "unavailable",
            "pilot_themes": pilot_themes,
            "blockers": blockers,
            "package_errors": package_errors,
            "test_fixtures_enabled": os.getenv("ENABLE_TEST_SCENARIOS", "false").strip().lower() in {"1", "true", "yes"},
            "definition_count": len(values),
            "active_reviewed_definition_count": len(active),
            "live_theme_intelligence": published,
            "reason": None if published else self.storage.state(theme_namespace(), "last_error") or "no_reviewed_theme_snapshot",
        }


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.removeprefix("v").split(".") if part.isdigit())


_service: ThemeSnapshotService | None = None
_lock = threading.RLock()


def get_theme_snapshot_service() -> ThemeSnapshotService:
    global _service
    with _lock:
        if _service is None: _service = ThemeSnapshotService()
        return _service


def reset_theme_snapshot_service() -> None:
    global _service
    with _lock: _service = None

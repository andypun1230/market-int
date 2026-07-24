from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH
from app.theme_snapshots.models import ThemeSnapshot
from app.themes.identifiers import normalize_theme_id

_lock = threading.RLock()


class ThemeSnapshotStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        with _lock:
            if self._initialized:
                return
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("""CREATE TABLE IF NOT EXISTS theme_snapshots (
                    snapshot_id TEXT PRIMARY KEY, market_date TEXT NOT NULL, status TEXT NOT NULL,
                    source_state TEXT NOT NULL, generated_at TEXT NOT NULL, payload_json TEXT NOT NULL,
                    input_hash TEXT NOT NULL, payload_hash TEXT NOT NULL)""")
                connection.execute("CREATE INDEX IF NOT EXISTS theme_snapshots_date ON theme_snapshots(market_date, generated_at DESC)")
                connection.execute("""CREATE TABLE IF NOT EXISTS theme_snapshot_state (
                    namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(namespace, key))""")
                self._migrate_legacy_payloads(connection)
                connection.commit()
            self._initialized = True

    def _migrate_legacy_payloads(self, connection: sqlite3.Connection) -> None:
        for snapshot_id, payload in connection.execute("SELECT snapshot_id, payload_json FROM theme_snapshots").fetchall():
            snapshot = ThemeSnapshot(**json.loads(payload))
            canonical_payload = json.dumps(canonical_snapshot(snapshot).model_dump(), sort_keys=True)
            if canonical_payload == payload:
                continue
            digest = hashlib.sha256(canonical_payload.encode()).hexdigest()
            connection.execute("UPDATE theme_snapshots SET payload_json=?, payload_hash=? WHERE snapshot_id=?", (canonical_payload, digest, snapshot_id))

    def publish(self, snapshot: ThemeSnapshot, namespace: str) -> None:
        snapshot = canonical_snapshot(snapshot)
        self.initialize(); payload = json.dumps(snapshot.model_dump(), sort_keys=True); digest = hashlib.sha256(payload.encode()).hexdigest()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO theme_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (snapshot.snapshot_id, snapshot.market_date, snapshot.status, snapshot.source_state, snapshot.generated_at, payload, snapshot.input_hash, digest))
            self._set(connection, namespace, "latest", snapshot.snapshot_id, snapshot.published_at)
            if snapshot.status in {"complete", "partial"}:
                self._set(connection, namespace, "lkg", snapshot.snapshot_id, snapshot.published_at); self._set(connection, namespace, "last_error", "", snapshot.published_at)
            connection.commit()

    def get(self, snapshot_id: str) -> ThemeSnapshot | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM theme_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        try: return canonical_snapshot(ThemeSnapshot(**json.loads(row[0]))) if row else None
        except (TypeError, ValueError, json.JSONDecodeError): return None

    def latest(self, namespace: str) -> ThemeSnapshot | None:
        return self.get(self.state(namespace, "latest") or "") or self.get(self.state(namespace, "lkg") or "")

    def history(self, namespace: str, days: int = 90) -> list[dict[str, Any]]:
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM theme_snapshots WHERE source_state=? ORDER BY market_date DESC, generated_at DESC LIMIT ?", ("test" if namespace.startswith("test:") else "live", max(1, min(days, 260)))).fetchall()
        return [canonical_snapshot(ThemeSnapshot(**json.loads(row[0]))).model_dump() for row in reversed(rows)]

    def state(self, namespace: str, key: str) -> str | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT value FROM theme_snapshot_state WHERE namespace=? AND key=?", (namespace, key)).fetchone()
        return str(row[0]) if row else None

    def set_error(self, namespace: str, value: str, updated_at: str) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            self._set(connection, namespace, "last_error", value, updated_at); connection.commit()

    def _set(self, connection: sqlite3.Connection, namespace: str, key: str, value: str, updated_at: str) -> None:
        connection.execute("INSERT OR REPLACE INTO theme_snapshot_state VALUES (?, ?, ?, ?)", (namespace, key, value, updated_at))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)


def canonical_snapshot(snapshot: ThemeSnapshot) -> ThemeSnapshot:
    """Normalize legacy kebab-case snapshot payloads at the durable boundary."""
    def canonical(value: str) -> str:
        return normalize_theme_id(value)

    rows = tuple({**row, "theme_id": canonical(str(row["theme_id"]))} for row in snapshot.rows)
    active_versions = tuple({**item, "theme_id": canonical(str(item["theme_id"]))} for item in snapshot.active_theme_versions)
    coverage = {canonical(str(theme_id)): value for theme_id, value in snapshot.member_coverage.items()}
    rankings = tuple(canonical(str(theme_id)) for theme_id in snapshot.rankings)
    overlap = tuple({
        **item,
        "left_theme_id": canonical(str(item["left_theme_id"])),
        "right_theme_id": canonical(str(item["right_theme_id"])),
    } for item in snapshot.overlap_matrix)
    alerts = tuple({**item, "theme_id": canonical(str(item["theme_id"]))} if item.get("theme_id") else item for item in snapshot.alerts)
    return replace(snapshot, rows=rows, active_theme_versions=active_versions, member_coverage=coverage, rankings=rankings, overlap_matrix=overlap, alerts=alerts)

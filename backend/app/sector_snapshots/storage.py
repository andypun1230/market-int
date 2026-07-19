from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH
from app.sector_snapshots.models import SectorSnapshot

_lock = threading.RLock()


class SectorSnapshotStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS sector_snapshots (
                snapshot_id TEXT PRIMARY KEY, universe_id TEXT NOT NULL, universe_version TEXT NOT NULL,
                market_date TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL,
                generated_at TEXT NOT NULL, source_state TEXT NOT NULL, input_hash TEXT NOT NULL, payload_hash TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS sector_snapshots_by_universe ON sector_snapshots(universe_id, generated_at DESC)")
            connection.execute("""CREATE TABLE IF NOT EXISTS sector_snapshot_state (
                namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(namespace, key))""")
            connection.commit()

    def publish(self, snapshot: SectorSnapshot, namespace: str) -> None:
        self.initialize()
        payload = json.dumps(snapshot.model_dump(), sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO sector_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (snapshot.snapshot_id, snapshot.universe_id, snapshot.universe_version, snapshot.market_date, snapshot.status, payload, snapshot.generated_at, snapshot.source_state, snapshot.input_hash, digest))
            self._set(connection, namespace, f"latest:{snapshot.universe_id}", snapshot.snapshot_id, snapshot.generated_at)
            if snapshot.status in {"complete", "partial"}:
                self._set(connection, namespace, f"lkg:{snapshot.universe_id}", snapshot.snapshot_id, snapshot.generated_at)
                self._set(connection, namespace, "last_error", "", snapshot.generated_at)
            connection.commit()

    def get(self, snapshot_id: str) -> SectorSnapshot | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM sector_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        try:
            return SectorSnapshot(**json.loads(row[0])) if row else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def latest(self, universe_id: str, namespace: str) -> SectorSnapshot | None:
        return self.get(self.state(namespace, f"latest:{universe_id}") or "") or self.get(self.state(namespace, f"lkg:{universe_id}") or "")

    def history(self, universe_id: str, days: int = 90) -> list[dict[str, Any]]:
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM sector_snapshots WHERE universe_id=? ORDER BY market_date DESC, generated_at DESC LIMIT ?", (universe_id, max(1, min(days, 260)))).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def state(self, namespace: str, key: str) -> str | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT value FROM sector_snapshot_state WHERE namespace=? AND key=?", (namespace, key)).fetchone()
        return str(row[0]) if row else None

    def set_error(self, namespace: str, value: str, updated_at: str) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            self._set(connection, namespace, "last_error", value, updated_at)
            connection.commit()

    def _set(self, connection: sqlite3.Connection, namespace: str, key: str, value: str, updated_at: str) -> None:
        connection.execute("INSERT OR REPLACE INTO sector_snapshot_state VALUES (?, ?, ?, ?)", (namespace, key, value, updated_at))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

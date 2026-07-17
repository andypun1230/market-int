from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH
from app.snapshots.models import MarketSnapshot, now_iso

_lock = threading.RLock()


class MarketSnapshotStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        configured = os.getenv("MARKET_SNAPSHOT_DB_PATH")
        if db_path is not None:
            self.db_path = Path(db_path)
        elif configured:
            self.db_path = Path(configured)
        else:
            self.db_path = DEFAULT_DB_PATH

    def initialize(self) -> None:
        with _lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        version INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        market_timestamp TEXT NULL,
                        expires_at TEXT NOT NULL,
                        stale_until TEXT NULL,
                        build_duration_ms INTEGER NULL,
                        coverage_ratio REAL NULL,
                        source_state TEXT NOT NULL,
                        payload_hash TEXT NULL,
                        size_bytes INTEGER NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_snapshot_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()

    def publish_snapshot(self, snapshot: MarketSnapshot) -> None:
        self.initialize()
        payload_json = json.dumps(snapshot.model_dump(), sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        now = now_iso()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO market_snapshots (
                    snapshot_id, version, status, payload_json, created_at, published_at,
                    market_timestamp, expires_at, stale_until, build_duration_ms,
                    coverage_ratio, source_state, payload_hash, size_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.version,
                    snapshot.status,
                    payload_json,
                    snapshot.created_at,
                    snapshot.published_at,
                    snapshot.market_timestamp,
                    snapshot.expires_at,
                    snapshot.stale_until,
                    snapshot.build_duration_ms,
                    snapshot.input_coverage.coverage_ratio,
                    snapshot.source_summary.get("source_state", "mixed"),
                    payload_hash,
                    len(payload_json.encode("utf-8")),
                ),
            )
            self._set_state_in_tx(connection, "latest_snapshot_id", snapshot.snapshot_id, now)
            if snapshot.status in {"complete", "partial"}:
                self._set_state_in_tx(connection, "last_successful_snapshot_id", snapshot.snapshot_id, now)
                self._set_state_in_tx(connection, "last_build_error", "", now)
            self._set_state_in_tx(connection, "last_build_completed_at", snapshot.build_completed_at, now)
            connection.commit()
        self.cleanup_old_snapshots()

    def get_snapshot(self, snapshot_id: str) -> MarketSnapshot | None:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                row = connection.execute(
                    "SELECT payload_json FROM market_snapshots WHERE snapshot_id = ?",
                    (snapshot_id,),
                ).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        try:
            return MarketSnapshot.model_validate(json.loads(row[0]))
        except Exception:
            return None

    def get_latest_snapshot(self) -> MarketSnapshot | None:
        latest_id = self.get_state("latest_snapshot_id")
        return self.get_snapshot(latest_id) if latest_id else None

    def get_last_successful_snapshot(self) -> MarketSnapshot | None:
        snapshot_id = self.get_state("last_successful_snapshot_id")
        return self.get_snapshot(snapshot_id) if snapshot_id else None

    def set_state(self, key: str, value: str) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            self._set_state_in_tx(connection, key, value, now_iso())
            connection.commit()

    def get_state(self, key: str) -> str | None:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                row = connection.execute("SELECT value FROM market_snapshot_state WHERE key = ?", (key,)).fetchone()
            return str(row[0]) if row else None
        except Exception:
            return None

    def get_state_map(self) -> dict[str, str]:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                rows = connection.execute("SELECT key, value FROM market_snapshot_state").fetchall()
            return {str(key): str(value) for key, value in rows}
        except Exception:
            return {}

    def cleanup_old_snapshots(self) -> int:
        retention = max(2, int_env("MARKET_SNAPSHOT_RETENTION_COUNT", 48))
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                keep_rows = connection.execute(
                    "SELECT snapshot_id FROM market_snapshots ORDER BY published_at DESC LIMIT ?",
                    (retention,),
                ).fetchall()
                keep = {row[0] for row in keep_rows}
                if not keep:
                    return 0
                placeholders = ",".join("?" for _ in keep)
                cursor = connection.execute(
                    f"DELETE FROM market_snapshots WHERE snapshot_id NOT IN ({placeholders})",
                    tuple(keep),
                )
                connection.commit()
                return int(cursor.rowcount)
        except Exception:
            return 0

    def status(self) -> dict[str, Any]:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                count = connection.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
                latest = connection.execute(
                    "SELECT snapshot_id, status, published_at FROM market_snapshots ORDER BY published_at DESC LIMIT 1"
                ).fetchone()
        except Exception as exc:
            return {"healthy": False, "error": type(exc).__name__}
        return {
            "healthy": True,
            "snapshot_count": count,
            "latest": {"snapshot_id": latest[0], "status": latest[1], "published_at": latest[2]} if latest else None,
            "state": self.get_state_map(),
        }

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

    def _set_state_in_tx(self, connection: sqlite3.Connection, key: str, value: str, updated_at: str) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO market_snapshot_state (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, updated_at),
        )


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def unique_snapshot_id(payload: dict[str, Any]) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"market-{stamp}-{digest}"

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
from app.stock_snapshots.models import StockAnalysisSnapshot, now_iso
from app.stock_snapshots.provenance import is_snapshot_compatible, snapshot_namespace

_lock = threading.RLock()


class StockSnapshotStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        configured = os.getenv("STOCK_SNAPSHOT_DB_PATH")
        self.db_path = Path(db_path or configured or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stock_analysis_snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        stale_until TEXT NOT NULL,
                        source_state TEXT NOT NULL,
                        latest_history_date TEXT NULL,
                        input_hash TEXT NOT NULL,
                        coverage_ratio REAL NOT NULL,
                        payload_hash TEXT NULL,
                        size_bytes INTEGER NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stock_analysis_snapshot_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_stock_snapshots_symbol_published ON stock_analysis_snapshots(symbol, published_at DESC)"
                )
                connection.commit()

    def publish_snapshot(self, snapshot: StockAnalysisSnapshot) -> None:
        self.initialize()
        payload_json = json.dumps(snapshot.model_dump(), sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        now = now_iso()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO stock_analysis_snapshots (
                    snapshot_id, symbol, version, status, payload_json, created_at, published_at,
                    expires_at, stale_until, source_state, latest_history_date, input_hash,
                    coverage_ratio, payload_hash, size_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.symbol,
                    snapshot.version,
                    snapshot.status,
                    payload_json,
                    snapshot.created_at,
                    snapshot.published_at,
                    snapshot.expires_at,
                    snapshot.stale_until,
                    snapshot.source_state,
                    snapshot.latest_history_date,
                    snapshot.input_hash,
                    snapshot.coverage_ratio,
                    payload_hash,
                    len(payload_json.encode("utf-8")),
                ),
            )
            namespace = snapshot_namespace(snapshot.symbol)
            self._set_state_in_tx(connection, self._latest_key(snapshot.symbol, namespace), snapshot.snapshot_id, now)
            if snapshot.status in {"complete", "partial"}:
                self._set_state_in_tx(connection, self._lkg_key(snapshot.symbol, namespace), snapshot.snapshot_id, now)
                self._set_state_in_tx(connection, self._error_key(snapshot.symbol, namespace), "", now)
            connection.commit()
        self.cleanup_old_snapshots(snapshot.symbol)

    def get_snapshot(self, snapshot_id: str) -> StockAnalysisSnapshot | None:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                row = connection.execute(
                    "SELECT payload_json FROM stock_analysis_snapshots WHERE snapshot_id = ?",
                    (snapshot_id,),
                ).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        try:
            return StockAnalysisSnapshot.model_validate(json.loads(row[0]))
        except Exception:
            return None

    def get_latest_snapshot(self, symbol: str) -> StockAnalysisSnapshot | None:
        namespace = snapshot_namespace(symbol)
        snapshot = self._get_compatible_state_snapshot(self._latest_key(symbol, namespace), symbol)
        if snapshot is not None:
            return snapshot
        legacy = self._get_compatible_state_snapshot(self._legacy_latest_key(symbol), symbol, clear_on_incompatible=True)
        return legacy

    def get_last_successful_snapshot(self, symbol: str) -> StockAnalysisSnapshot | None:
        namespace = snapshot_namespace(symbol)
        snapshot = self._get_compatible_state_snapshot(self._lkg_key(symbol, namespace), symbol)
        if snapshot is not None:
            return snapshot
        legacy = self._get_compatible_state_snapshot(self._legacy_lkg_key(symbol), symbol, clear_on_incompatible=True)
        return legacy

    def set_build_error(self, symbol: str, error: str) -> None:
        self.set_state(self._error_key(symbol, snapshot_namespace(symbol)), error)

    def set_state(self, key: str, value: str) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            self._set_state_in_tx(connection, key, value, now_iso())
            connection.commit()

    def get_state(self, key: str) -> str | None:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                row = connection.execute("SELECT value FROM stock_analysis_snapshot_state WHERE key = ?", (key,)).fetchone()
            return str(row[0]) if row else None
        except Exception:
            return None

    def clear_symbol(self, symbol: str) -> dict[str, int]:
        normalized = symbol.upper()
        self.initialize()
        deleted_snapshots = 0
        deleted_state = 0
        try:
            with _lock, self._connect() as connection:
                cursor = connection.execute("DELETE FROM stock_analysis_snapshots WHERE symbol = ?", (normalized,))
                deleted_snapshots = int(cursor.rowcount)
                cursor = connection.execute(
                    "DELETE FROM stock_analysis_snapshot_state WHERE key LIKE ? OR key LIKE ? OR key LIKE ?",
                    (f"%:{normalized}", f"%:{normalized}:%", f"%:{normalized}"),
                )
                deleted_state = int(cursor.rowcount)
                connection.commit()
        except Exception:
            pass
        return {"snapshots": deleted_snapshots, "state": deleted_state}

    def clear_all(self) -> dict[str, int]:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                snapshots = connection.execute("DELETE FROM stock_analysis_snapshots").rowcount
                state = connection.execute("DELETE FROM stock_analysis_snapshot_state").rowcount
                connection.commit()
                return {"snapshots": int(snapshots), "state": int(state)}
        except Exception:
            return {"snapshots": 0, "state": 0}

    def clear_namespace(self, namespace_prefix: str) -> dict[str, int]:
        self.initialize()
        deleted_state = 0
        try:
            with _lock, self._connect() as connection:
                rows = connection.execute(
                    "SELECT value FROM stock_analysis_snapshot_state WHERE key LIKE ?",
                    (f"%:{namespace_prefix}:%",),
                ).fetchall()
                snapshot_ids = [row[0] for row in rows]
                deleted_state = connection.execute(
                    "DELETE FROM stock_analysis_snapshot_state WHERE key LIKE ?",
                    (f"%:{namespace_prefix}:%",),
                ).rowcount
                deleted_snapshots = 0
                for snapshot_id in snapshot_ids:
                    deleted_snapshots += connection.execute(
                        "DELETE FROM stock_analysis_snapshots WHERE snapshot_id = ?",
                        (snapshot_id,),
                    ).rowcount
                connection.commit()
                return {"snapshots": int(deleted_snapshots), "state": int(deleted_state)}
        except Exception:
            return {"snapshots": 0, "state": deleted_state}

    def clear_incompatible(self) -> dict[str, int]:
        self.initialize()
        deleted_state = 0
        checked = 0
        try:
            with _lock, self._connect() as connection:
                rows = connection.execute("SELECT key, value FROM stock_analysis_snapshot_state").fetchall()
                for key, snapshot_id in rows:
                    if not (str(key).startswith("latest:") or str(key).startswith("last_known_good:")):
                        continue
                    checked += 1
                    snapshot = self.get_snapshot(str(snapshot_id))
                    compatible, _reason = is_snapshot_compatible(snapshot) if snapshot else (False, "missing")
                    if not compatible:
                        deleted_state += connection.execute(
                            "DELETE FROM stock_analysis_snapshot_state WHERE key = ?",
                            (key,),
                        ).rowcount
                connection.commit()
        except Exception:
            pass
        return {"state": int(deleted_state), "checked": checked}

    def cleanup_old_snapshots(self, symbol: str) -> int:
        retention = max(1, int_env("STOCK_SNAPSHOT_RETENTION_PER_SYMBOL", 3))
        try:
            with _lock, self._connect() as connection:
                keep_rows = connection.execute(
                    "SELECT snapshot_id FROM stock_analysis_snapshots WHERE symbol = ? ORDER BY published_at DESC LIMIT ?",
                    (symbol.upper(), retention),
                ).fetchall()
                keep = {row[0] for row in keep_rows}
                if not keep:
                    return 0
                placeholders = ",".join("?" for _ in keep)
                cursor = connection.execute(
                    f"DELETE FROM stock_analysis_snapshots WHERE symbol = ? AND snapshot_id NOT IN ({placeholders})",
                    (symbol.upper(), *tuple(keep)),
                )
                connection.commit()
                return int(cursor.rowcount)
        except Exception:
            return 0

    def status(self, symbol: str | None = None) -> dict[str, Any]:
        self.initialize()
        try:
            with _lock, self._connect() as connection:
                if symbol:
                    count = connection.execute("SELECT COUNT(*) FROM stock_analysis_snapshots WHERE symbol = ?", (symbol.upper(),)).fetchone()[0]
                    latest = connection.execute(
                        "SELECT snapshot_id, status, published_at FROM stock_analysis_snapshots WHERE symbol = ? ORDER BY published_at DESC LIMIT 1",
                        (symbol.upper(),),
                    ).fetchone()
                else:
                    count = connection.execute("SELECT COUNT(*) FROM stock_analysis_snapshots").fetchone()[0]
                    latest = connection.execute(
                        "SELECT snapshot_id, status, published_at FROM stock_analysis_snapshots ORDER BY published_at DESC LIMIT 1"
                    ).fetchone()
        except Exception as exc:
            return {"healthy": False, "error": type(exc).__name__}
        return {
            "healthy": True,
            "snapshot_count": count,
            "latest": {"snapshot_id": latest[0], "status": latest[1], "published_at": latest[2]} if latest else None,
        }

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

    def _set_state_in_tx(self, connection: sqlite3.Connection, key: str, value: str, updated_at: str) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO stock_analysis_snapshot_state (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, updated_at),
        )

    def _get_compatible_state_snapshot(self, key: str, symbol: str, *, clear_on_incompatible: bool = True) -> StockAnalysisSnapshot | None:
        snapshot_id = self.get_state(key)
        if not snapshot_id:
            return None
        snapshot = self.get_snapshot(snapshot_id)
        compatible, reason = is_snapshot_compatible(snapshot) if snapshot else (False, "missing")
        if compatible:
            return snapshot
        if clear_on_incompatible:
            self._clear_state_key(key)
            self.set_state(f"incompatible:{symbol.upper()}:{int(time.time())}", f"{snapshot_id}:{reason}")
        return None

    def _clear_state_key(self, key: str) -> None:
        try:
            with _lock, self._connect() as connection:
                connection.execute("DELETE FROM stock_analysis_snapshot_state WHERE key = ?", (key,))
                connection.commit()
        except Exception:
            pass

    @staticmethod
    def _latest_key(symbol: str, namespace: str) -> str:
        return f"latest:{namespace}"

    @staticmethod
    def _lkg_key(symbol: str, namespace: str) -> str:
        return f"last_known_good:{namespace}"

    @staticmethod
    def _error_key(symbol: str, namespace: str) -> str:
        return f"last_error:{namespace}"

    @staticmethod
    def _legacy_latest_key(symbol: str) -> str:
        return f"latest:{symbol.upper()}"

    @staticmethod
    def _legacy_lkg_key(symbol: str) -> str:
        return f"last_known_good:{symbol.upper()}"


def unique_snapshot_id(symbol: str, payload: dict[str, Any]) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"stock-{symbol.upper()}-{stamp}-{digest}"


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

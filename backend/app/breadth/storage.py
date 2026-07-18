from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.breadth.models import BreadthSnapshot
from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH

_lock = threading.RLock()


class BreadthSnapshotStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS breadth_snapshots (
                snapshot_id TEXT PRIMARY KEY, universe_id TEXT NOT NULL, universe_version TEXT NOT NULL,
                market_date TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL, published_at TEXT NOT NULL, source_state TEXT NOT NULL,
                calculation_version TEXT NOT NULL, input_hash TEXT NOT NULL, payload_hash TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS breadth_snapshots_by_universe ON breadth_snapshots(universe_id, published_at DESC)")
            connection.execute("""CREATE TABLE IF NOT EXISTS breadth_snapshot_state (
                namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(namespace, key))""")
            connection.commit()

    def publish(self, snapshot: BreadthSnapshot, *, namespace: str) -> None:
        self.initialize()
        payload = json.dumps(snapshot.model_dump(), sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT INTO breadth_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (snapshot.snapshot_id, snapshot.universe_id, snapshot.universe_version, snapshot.market_date, snapshot.status, payload, snapshot.created_at, snapshot.published_at, snapshot.source_state, snapshot.calculation_version, snapshot.input_hash, digest))
            self._state_in_tx(connection, namespace, f"latest:{snapshot.universe_id}", snapshot.snapshot_id, snapshot.published_at)
            if snapshot.status in {"complete", "partial"}:
                self._state_in_tx(connection, namespace, f"lkg:{snapshot.universe_id}", snapshot.snapshot_id, snapshot.published_at)
                self._state_in_tx(connection, namespace, "last_error", "", snapshot.published_at)
            connection.commit()
        self.cleanup(snapshot.universe_id, namespace)

    def get(self, snapshot_id: str) -> BreadthSnapshot | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM breadth_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if not row: return None
        try: return BreadthSnapshot(**json.loads(row[0]))
        except (TypeError, ValueError, json.JSONDecodeError): return None

    def latest(self, universe_id: str, namespace: str) -> BreadthSnapshot | None:
        return self.get(self.state(namespace, f"latest:{universe_id}") or "") or self.last_known_good(universe_id, namespace)

    def last_known_good(self, universe_id: str, namespace: str) -> BreadthSnapshot | None:
        return self.get(self.state(namespace, f"lkg:{universe_id}") or "")

    def history(self, universe_id: str, metric: str, days: int = 90, *, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        allowed = {"breadth_score": ("score",), "percent_above_20ema": ("moving_average_breadth", "percent_above_20ema"), "percent_above_50ema": ("moving_average_breadth", "percent_above_50ema"), "percent_above_200ema": ("moving_average_breadth", "percent_above_200ema"), "advance_decline_ratio": ("advance_decline", "advance_decline_ratio"), "net_advances": ("advance_decline", "net_advances"), "highs_minus_lows": ("highs_lows", "highs_minus_lows")}
        if metric not in allowed: raise ValueError("unsupported breadth history metric")
        self.initialize()
        query = "SELECT payload_json FROM breadth_snapshots WHERE universe_id=?"
        args: list[object] = [universe_id]
        if start:
            query += " AND market_date >= ?"; args.append(start)
        if end:
            query += " AND market_date <= ?"; args.append(end)
        query += " ORDER BY market_date DESC LIMIT ?"; args.append(max(1, min(days, 260)))
        with _lock, self._connect() as connection:
            rows = connection.execute(query, args).fetchall()
        result = []
        for row in reversed(rows):
            payload = json.loads(row[0]); path = allowed[metric]; value: Any = payload
            for part in path: value = value.get(part) if isinstance(value, dict) else None
            result.append({"market_date": payload.get("market_date"), "metric": metric, "value": value, "snapshot_id": payload.get("snapshot_id")})
        return result

    def state(self, namespace: str, key: str) -> str | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT value FROM breadth_snapshot_state WHERE namespace=? AND key=?", (namespace, key)).fetchone()
        return str(row[0]) if row else None

    def set_state(self, namespace: str, key: str, value: str, updated_at: str) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            self._state_in_tx(connection, namespace, key, value, updated_at); connection.commit()

    def cleanup(self, universe_id: str, namespace: str) -> None:
        retention = max(2, int(os.getenv("BREADTH_RETENTION_COUNT", "260")))
        with _lock, self._connect() as connection:
            keep = [row[0] for row in connection.execute("SELECT snapshot_id FROM breadth_snapshots WHERE universe_id=? ORDER BY published_at DESC LIMIT ?", (universe_id, retention)).fetchall()]
            if keep:
                connection.execute(f"DELETE FROM breadth_snapshots WHERE universe_id=? AND snapshot_id NOT IN ({','.join('?' for _ in keep)})", (universe_id, *keep)); connection.commit()

    def status(self, universe_id: str, namespace: str) -> dict[str, Any]:
        snapshot = self.latest(universe_id, namespace)
        return {"latest_snapshot_id": snapshot.snapshot_id if snapshot else None, "latest_status": snapshot.status if snapshot else "unavailable", "last_known_good_snapshot_id": self.state(namespace, f"lkg:{universe_id}"), "last_error": self.state(namespace, "last_error")}

    def _state_in_tx(self, connection: sqlite3.Connection, namespace: str, key: str, value: str, updated_at: str) -> None:
        connection.execute("INSERT OR REPLACE INTO breadth_snapshot_state VALUES (?, ?, ?, ?)", (namespace, key, value, updated_at))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

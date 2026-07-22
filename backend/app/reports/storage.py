from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.market import DailyReportResponse


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "daily_reports.sqlite3"


@dataclass(frozen=True)
class StoredDailyReport:
    report: DailyReportResponse
    identity_key: str
    cache_key: str
    schema_version: str
    pdf_available: bool


class DailyReportStorage:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or report_db_path()
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS daily_reports (
                    report_id TEXT PRIMARY KEY,
                    identity_key TEXT NOT NULL UNIQUE,
                    market_date TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    snapshot_ids_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    pdf_blob BLOB,
                    pdf_hash TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS daily_reports_market_date_idx ON daily_reports(market_date DESC, generated_at DESC)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS daily_report_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            connection.commit()

    def get_by_identity(self, identity_key: str) -> StoredDailyReport | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM daily_reports WHERE identity_key=?", (identity_key,)).fetchone()
        return self._record(row)

    def get(self, report_id: str) -> StoredDailyReport | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM daily_reports WHERE report_id=?", (report_id,)).fetchone()
        return self._record(row)

    def latest(self) -> StoredDailyReport | None:
        with self._lock, self._connect() as connection:
            pointer = connection.execute("SELECT value FROM daily_report_state WHERE key='latest_report_id'").fetchone()
            row = connection.execute("SELECT * FROM daily_reports WHERE report_id=?", (pointer[0],)).fetchone() if pointer else None
        return self._record(row)

    def save_if_absent(self, report: DailyReportResponse, *, identity_key: str, cache_key: str, schema_version: str) -> StoredDailyReport:
        existing = self.get_by_identity(identity_key)
        if existing is not None:
            self.mark_latest(existing.report.report_id or "", existing.report.generated_at or existing.report.generated_time or "unknown")
            return existing

        payload = report.model_dump(mode="json")
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        snapshot_ids = (report.semantic_context or {}).get("snapshot_ids") or {}
        generated_at = report.generated_at or report.generated_time or "unknown"
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO daily_reports
                (report_id, identity_key, market_date, generated_at, schema_version, cache_key,
                 snapshot_ids_json, payload_json, payload_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.report_id,
                    identity_key,
                    report.market_date or report.date,
                    generated_at,
                    schema_version,
                    cache_key,
                    json.dumps(snapshot_ids, sort_keys=True),
                    payload_json,
                    payload_hash,
                    generated_at,
                ),
            )
            connection.execute(
                "INSERT OR REPLACE INTO daily_report_state(key, value, updated_at) VALUES ('latest_report_id', ?, ?)",
                (report.report_id, generated_at),
            )
            connection.commit()
        return self.get_by_identity(identity_key) or self._raise_missing_report(identity_key)

    def mark_latest(self, report_id: str, updated_at: str) -> None:
        """Advance the mutable pointer without changing an immutable report row."""
        if not report_id:
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO daily_report_state(key, value, updated_at) VALUES ('latest_report_id', ?, ?)",
                (report_id, updated_at),
            )
            connection.commit()

    def save_pdf_if_absent(self, report_id: str, pdf_bytes: bytes) -> bytes:
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE daily_reports SET pdf_blob=?, pdf_hash=? WHERE report_id=? AND pdf_blob IS NULL",
                (pdf_bytes, digest, report_id),
            )
            connection.commit()
            row = connection.execute("SELECT pdf_blob FROM daily_reports WHERE report_id=?", (report_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown report id: {report_id}")
        return bytes(row[0]) if row[0] is not None else pdf_bytes

    def get_pdf(self, report_id: str) -> bytes | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT pdf_blob FROM daily_reports WHERE report_id=?", (report_id,)).fetchone()
        return bytes(row[0]) if row and row[0] is not None else None

    def history(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT report_id, market_date, generated_at, schema_version, cache_key, snapshot_ids_json, pdf_blob IS NOT NULL AS pdf_available FROM daily_reports ORDER BY generated_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [
            {
                "report_id": row["report_id"],
                "market_date": row["market_date"],
                "generated_at": row["generated_at"],
                "report_schema_version": row["schema_version"],
                "report_cache_key": row["cache_key"],
                "snapshot_ids": json.loads(row["snapshot_ids_json"]),
                "pdf_available": bool(row["pdf_available"]),
            }
            for row in rows
        ]

    @staticmethod
    def _raise_missing_report(identity_key: str) -> StoredDailyReport:
        raise RuntimeError(f"Unable to persist report identity {identity_key}")

    @staticmethod
    def _record(row: sqlite3.Row | None) -> StoredDailyReport | None:
        if row is None:
            return None
        return StoredDailyReport(
            report=DailyReportResponse.model_validate(json.loads(row["payload_json"])),
            identity_key=row["identity_key"],
            cache_key=row["cache_key"],
            schema_version=row["schema_version"],
            pdf_available=row["pdf_blob"] is not None,
        )


def report_db_path() -> Path:
    configured = os.getenv("DAILY_REPORT_DB_PATH") or os.getenv("REPORT_DB_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_DB_PATH


_storage: DailyReportStorage | None = None
_storage_lock = threading.RLock()


def get_daily_report_storage() -> DailyReportStorage:
    global _storage
    with _storage_lock:
        if _storage is None or _storage.db_path != report_db_path():
            _storage = DailyReportStorage()
        return _storage


def reset_daily_report_storage() -> None:
    global _storage
    with _storage_lock:
        _storage = None

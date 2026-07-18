from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH

_lock = threading.RLock()


@dataclass(frozen=True)
class DailyBar:
    ticker: str
    provider: str
    session_date: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted: bool = True
    fetched_at: str | None = None
    source_timestamp: str | None = None
    data_version: int = 1
    quality_status: str = "valid"
    payload_hash: str | None = None

    def validate(self) -> None:
        if not self.ticker or not self.provider:
            raise ValueError("ticker and provider are required")
        if self.session_date > date.today().isoformat():
            raise ValueError("future daily bars are not allowed")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC must be positive")
        if self.high < max(self.open, self.low, self.close) or self.low > min(self.open, self.high, self.close):
            raise ValueError("invalid OHLC relationship")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
        if not self.adjusted:
            raise ValueError("breadth daily bars must be adjusted")

    def database_values(self) -> tuple[object, ...]:
        fetched_at = self.fetched_at or datetime.now(timezone.utc).isoformat()
        payload_hash = self.payload_hash or hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode("utf-8")).hexdigest()
        return (self.ticker.upper(), self.provider.lower(), self.session_date, self.timestamp, self.open, self.high, self.low, self.close, self.volume, int(self.adjusted), fetched_at, self.source_timestamp, self.data_version, self.quality_status, payload_hash)


class DailyBarStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS daily_price_bars (
                ticker TEXT NOT NULL, provider TEXT NOT NULL, session_date TEXT NOT NULL,
                timestamp TEXT NOT NULL, open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
                close REAL NOT NULL, volume REAL NOT NULL, adjusted INTEGER NOT NULL,
                fetched_at TEXT NOT NULL, source_timestamp TEXT, data_version INTEGER NOT NULL,
                quality_status TEXT NOT NULL, payload_hash TEXT,
                PRIMARY KEY(ticker, provider, session_date, adjusted))"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS daily_price_bars_by_ticker ON daily_price_bars(ticker, provider, session_date)")
            connection.commit()

    def upsert(self, bars: list[DailyBar]) -> tuple[int, int]:
        self.initialize()
        for bar in bars:
            bar.validate()
        inserted = updated = 0
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for bar in bars:
                values = bar.database_values()
                row = connection.execute("SELECT payload_hash FROM daily_price_bars WHERE ticker=? AND provider=? AND session_date=? AND adjusted=?", (values[0], values[1], values[2], values[9])).fetchone()
                if row is None:
                    connection.execute("INSERT INTO daily_price_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
                    inserted += 1
                elif row[0] != values[14]:
                    connection.execute("UPDATE daily_price_bars SET timestamp=?, open=?, high=?, low=?, close=?, volume=?, fetched_at=?, source_timestamp=?, data_version=?, quality_status=?, payload_hash=? WHERE ticker=? AND provider=? AND session_date=? AND adjusted=?", (*values[3:9], values[10], values[11], values[12], values[13], values[14], values[0], values[1], values[2], values[9]))
                    updated += 1
            connection.commit()
        return inserted, updated

    def history(self, ticker: str, provider: str = "polygon", *, end_date: str | None = None) -> list[DailyBar]:
        self.initialize()
        sql = "SELECT * FROM daily_price_bars WHERE ticker=? AND provider=? AND adjusted=1"
        args: list[object] = [ticker.upper(), provider.lower()]
        if end_date:
            sql += " AND session_date <= ?"
            args.append(end_date)
        sql += " ORDER BY session_date"
        with _lock, self._connect() as connection:
            rows = connection.execute(sql, args).fetchall()
        return [DailyBar(*row[:10], fetched_at=row[10], source_timestamp=row[11], data_version=row[12], quality_status=row[13], payload_hash=row[14]) for row in rows]

    def latest_session(self, ticker: str, provider: str = "polygon") -> str | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT MAX(session_date) FROM daily_price_bars WHERE ticker=? AND provider=? AND adjusted=1", (ticker.upper(), provider.lower())).fetchone()
        return row[0] if row and row[0] else None

    def status(self, tickers: list[str], provider: str = "polygon") -> dict[str, object]:
        rows = {ticker: self.latest_session(ticker, provider) for ticker in tickers}
        return {"symbols_total": len(tickers), "symbols_seeded": sum(value is not None for value in rows.values()), "latest_sessions": rows}

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

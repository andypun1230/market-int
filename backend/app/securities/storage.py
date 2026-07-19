from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH
from app.securities.models import BreadthUniverse, BreadthUniverseMember, SecurityRecord
from app.securities.registry import canonical_sector_id

_lock = threading.RLock()


class SecurityMasterStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("CREATE TABLE IF NOT EXISTS breadth_schema_versions (name TEXT PRIMARY KEY, version INTEGER NOT NULL)")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS securities (
                security_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, company_name TEXT NOT NULL,
                exchange TEXT NOT NULL, asset_type TEXT NOT NULL, active INTEGER NOT NULL,
                sector TEXT NOT NULL, sector_id TEXT, industry TEXT, quote_provider_symbol TEXT, history_provider_symbol TEXT,
                currency TEXT NOT NULL, country TEXT NOT NULL, index_memberships_json TEXT NOT NULL,
                effective_from TEXT, effective_to TEXT, source TEXT NOT NULL, source_timestamp TEXT,
                verified_at TEXT, metadata_version INTEGER NOT NULL, UNIQUE(ticker, active))"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS breadth_universes (
                universe_id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
                benchmark_symbol TEXT NOT NULL, effective_date TEXT NOT NULL, created_at TEXT NOT NULL,
                source TEXT NOT NULL, source_timestamp TEXT, member_count INTEGER NOT NULL,
                enabled INTEGER NOT NULL, notes TEXT, UNIQUE(name, version))"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS breadth_universe_members (
                universe_id TEXT NOT NULL, security_id TEXT NOT NULL, ticker TEXT NOT NULL, sector TEXT NOT NULL, sector_id TEXT,
                active INTEGER NOT NULL, weight REAL, effective_from TEXT, effective_to TEXT,
                membership_source TEXT NOT NULL, PRIMARY KEY(universe_id, security_id),
                FOREIGN KEY(universe_id) REFERENCES breadth_universes(universe_id),
                FOREIGN KEY(security_id) REFERENCES securities(security_id))"""
            )
            # Existing rollout databases predate canonical sector identifiers.
            for table, column in (("securities", "sector_id"), ("breadth_universe_members", "sector_id")):
                columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
            for table in ("securities", "breadth_universe_members"):
                for sector, in connection.execute(f"SELECT DISTINCT sector FROM {table} WHERE sector_id IS NULL OR sector_id = ''").fetchall():
                    sector_id = canonical_sector_id(sector)
                    if sector_id:
                        connection.execute(f"UPDATE {table} SET sector_id=? WHERE sector=? AND (sector_id IS NULL OR sector_id = '')", (sector_id, sector))
            connection.execute("INSERT OR REPLACE INTO breadth_schema_versions(name, version) VALUES ('security_master', 2)")
            connection.commit()

    def upsert_security(self, record: SecurityRecord) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO securities (security_id, ticker, company_name, exchange, asset_type, active, sector, sector_id, industry, quote_provider_symbol, history_provider_symbol, currency, country, index_memberships_json, effective_from, effective_to, source, source_timestamp, verified_at, metadata_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(security_id) DO UPDATE SET ticker=excluded.ticker, company_name=excluded.company_name,
                exchange=excluded.exchange, asset_type=excluded.asset_type, active=excluded.active, sector=excluded.sector, sector_id=excluded.sector_id,
                industry=excluded.industry, quote_provider_symbol=excluded.quote_provider_symbol,
                history_provider_symbol=excluded.history_provider_symbol, currency=excluded.currency, country=excluded.country,
                index_memberships_json=excluded.index_memberships_json, effective_from=excluded.effective_from,
                effective_to=excluded.effective_to, source=excluded.source, source_timestamp=excluded.source_timestamp,
                verified_at=excluded.verified_at, metadata_version=excluded.metadata_version""",
                (
                    record.security_id, record.ticker, record.company_name, record.exchange, record.asset_type,
                    int(record.active), record.sector, record.sector_id, record.industry, record.quote_provider_symbol,
                    record.history_provider_symbol, record.currency, record.country,
                    json.dumps(list(record.index_memberships)), record.effective_from, record.effective_to,
                    record.source, record.source_timestamp, record.verified_at, record.metadata_version,
                ),
            )
            connection.commit()

    def publish_universe(self, universe: BreadthUniverse, members: list[BreadthUniverseMember]) -> None:
        self.initialize()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO breadth_universes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    universe.universe_id, universe.name, universe.version, universe.benchmark_symbol,
                    universe.effective_date, universe.created_at, universe.source, universe.source_timestamp,
                    universe.member_count, int(universe.enabled), universe.notes,
                ),
            )
            connection.executemany(
                "INSERT INTO breadth_universe_members (universe_id, security_id, ticker, sector, sector_id, active, weight, effective_from, effective_to, membership_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(
                    member.universe_id, member.security_id, member.ticker, member.sector, member.sector_id, int(member.active),
                    member.weight, member.effective_from, member.effective_to, member.membership_source,
                ) for member in members],
            )
            connection.commit()

    def get_universe(self, universe_id: str) -> BreadthUniverse | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT universe_id, name, version, benchmark_symbol, effective_date, created_at, source, source_timestamp, member_count, enabled, notes FROM breadth_universes WHERE universe_id = ?", (universe_id,)).fetchone()
        return BreadthUniverse(*row) if row else None

    def get_active_universe(self, name: str) -> BreadthUniverse | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT universe_id, name, version, benchmark_symbol, effective_date, created_at, source, source_timestamp, member_count, enabled, notes FROM breadth_universes WHERE name = ? AND enabled = 1 ORDER BY effective_date DESC, created_at DESC LIMIT 1", (name,)).fetchone()
        return BreadthUniverse(*row) if row else None

    def members(self, universe_id: str) -> list[BreadthUniverseMember]:
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute("SELECT universe_id, security_id, ticker, sector, sector_id, active, weight, effective_from, effective_to, membership_source FROM breadth_universe_members WHERE universe_id = ? AND active = 1 ORDER BY ticker", (universe_id,)).fetchall()
        return [BreadthUniverseMember(*row) for row in rows]

    def security(self, ticker: str) -> SecurityRecord | None:
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT security_id, ticker, company_name, exchange, asset_type, active, sector, sector_id, industry, quote_provider_symbol, history_provider_symbol, currency, country, index_memberships_json, effective_from, effective_to, source, source_timestamp, verified_at, metadata_version FROM securities WHERE ticker = ? AND active = 1", (ticker.upper(),)).fetchone()
        if not row:
            return None
        values = list(row)
        values[13] = tuple(json.loads(values[13]))
        return SecurityRecord(*values)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)

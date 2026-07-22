from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from app.cache.persistent_cache import DB_PATH as DEFAULT_DB_PATH
from app.securities.models import BreadthUniverse, BreadthUniverseMember, SecurityAlias, SecurityProviderSymbol, SecurityRecord
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
            connection.execute(
                """CREATE TABLE IF NOT EXISTS security_aliases (
                alias_ticker TEXT PRIMARY KEY, security_id TEXT NOT NULL,
                former_company_name TEXT, effective_to TEXT NOT NULL,
                corporate_action_type TEXT NOT NULL, continuity_status TEXT NOT NULL,
                source TEXT NOT NULL, verified_at TEXT NOT NULL,
                FOREIGN KEY(security_id) REFERENCES securities(security_id))"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS security_aliases_by_security ON security_aliases(security_id, effective_to DESC)")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS security_provider_symbols (
                security_id TEXT NOT NULL, provider TEXT NOT NULL, purpose TEXT NOT NULL,
                provider_symbol TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT,
                source TEXT NOT NULL, verified_at TEXT NOT NULL, corporate_action_lineage TEXT,
                PRIMARY KEY(security_id, provider, purpose, effective_from),
                UNIQUE(provider, purpose, provider_symbol, effective_from),
                FOREIGN KEY(security_id) REFERENCES securities(security_id))"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS security_provider_symbols_by_date ON security_provider_symbols(security_id, provider, purpose, effective_from, effective_to)")
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
            connection.execute("INSERT OR REPLACE INTO breadth_schema_versions(name, version) VALUES ('security_master', 3)")
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

    def upsert_alias(self, alias: SecurityAlias) -> None:
        """Persist one historical alias while preventing canonical/alias collisions."""
        self.initialize()
        alias_ticker = alias.alias_ticker.upper()
        with _lock, self._connect() as connection:
            owner = connection.execute("SELECT security_id FROM securities WHERE ticker=? AND active=1", (alias_ticker,)).fetchone()
            if owner and owner[0] != alias.security_id:
                raise ValueError(f"historical_alias_collides_with_active_canonical:{alias_ticker}")
            existing = connection.execute("SELECT security_id FROM security_aliases WHERE alias_ticker=?", (alias_ticker,)).fetchone()
            if existing and existing[0] != alias.security_id:
                raise ValueError(f"historical_alias_collision:{alias_ticker}")
            connection.execute(
                """INSERT INTO security_aliases (alias_ticker, security_id, former_company_name, effective_to, corporate_action_type, continuity_status, source, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alias_ticker) DO UPDATE SET security_id=excluded.security_id, former_company_name=excluded.former_company_name,
                effective_to=excluded.effective_to, corporate_action_type=excluded.corporate_action_type,
                continuity_status=excluded.continuity_status, source=excluded.source, verified_at=excluded.verified_at""",
                (alias_ticker, alias.security_id, alias.former_company_name, alias.effective_to, alias.corporate_action_type, alias.continuity_status, alias.source, alias.verified_at),
            )
            connection.commit()

    def aliases(self, ticker: str) -> list[SecurityAlias]:
        security = self.security(ticker)
        if security is None:
            return []
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT alias_ticker, security_id, former_company_name, effective_to, corporate_action_type, continuity_status, source, verified_at FROM security_aliases WHERE security_id=? ORDER BY effective_to",
                (security.security_id,),
            ).fetchall()
        return [SecurityAlias(*row) for row in rows]

    def upsert_provider_symbol(self, symbol: SecurityProviderSymbol) -> None:
        """Store a non-overlapping, date-aware provider symbol mapping."""
        self.initialize()
        provider, purpose, provider_symbol = symbol.provider.lower(), symbol.purpose.lower(), symbol.provider_symbol.upper()
        with _lock, self._connect() as connection:
            owner = connection.execute("SELECT security_id FROM securities WHERE security_id=?", (symbol.security_id,)).fetchone()
            if not owner:
                raise ValueError(f"provider_symbol_security_not_found:{symbol.security_id}")
            conflicting_symbol = connection.execute(
                "SELECT security_id FROM security_provider_symbols WHERE provider=? AND purpose=? AND provider_symbol=? AND effective_from=?",
                (provider, purpose, provider_symbol, symbol.effective_from),
            ).fetchone()
            if conflicting_symbol and conflicting_symbol[0] != symbol.security_id:
                raise ValueError(f"provider_symbol_collision:{provider}:{purpose}:{provider_symbol}:{symbol.effective_from}")
            rows = connection.execute(
                "SELECT effective_from, effective_to FROM security_provider_symbols WHERE security_id=? AND provider=? AND purpose=? AND effective_from<>?",
                (symbol.security_id, provider, purpose, symbol.effective_from),
            ).fetchall()
            for existing_from, existing_to in rows:
                if _date_ranges_overlap(symbol.effective_from, symbol.effective_to, existing_from, existing_to):
                    raise ValueError(f"provider_symbol_date_overlap:{symbol.security_id}:{provider}:{purpose}")
            connection.execute(
                """INSERT INTO security_provider_symbols (security_id, provider, purpose, provider_symbol, effective_from, effective_to, source, verified_at, corporate_action_lineage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(security_id, provider, purpose, effective_from) DO UPDATE SET provider_symbol=excluded.provider_symbol,
                effective_to=excluded.effective_to, source=excluded.source, verified_at=excluded.verified_at,
                corporate_action_lineage=excluded.corporate_action_lineage""",
                (symbol.security_id, provider, purpose, provider_symbol, symbol.effective_from, symbol.effective_to, symbol.source, symbol.verified_at, symbol.corporate_action_lineage),
            )
            connection.commit()

    def provider_symbols(self, ticker: str, *, provider: str = "polygon", purpose: str = "history") -> list[SecurityProviderSymbol]:
        security = self.security(ticker)
        if security is None:
            return []
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT security_id, provider, purpose, provider_symbol, effective_from, effective_to, source, verified_at, corporate_action_lineage FROM security_provider_symbols WHERE security_id=? AND provider=? AND purpose=? ORDER BY effective_from",
                (security.security_id, provider.lower(), purpose.lower()),
            ).fetchall()
        return [SecurityProviderSymbol(*row) for row in rows]

    def provider_symbol_for(self, ticker: str, *, provider: str = "polygon", purpose: str = "history", on_date: str | None = None) -> SecurityProviderSymbol | None:
        security = self.security(ticker)
        if security is None:
            return None
        target = on_date or "9999-12-31"
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute(
                """SELECT security_id, provider, purpose, provider_symbol, effective_from, effective_to, source, verified_at, corporate_action_lineage
                FROM security_provider_symbols
                WHERE security_id=? AND provider=? AND purpose=? AND effective_from<=? AND (effective_to IS NULL OR effective_to>=?)
                ORDER BY effective_from DESC LIMIT 1""",
                (security.security_id, provider.lower(), purpose.lower(), target, target),
            ).fetchone()
        if row:
            return SecurityProviderSymbol(*row)
        fallback = security.history_provider_symbol if purpose.lower() == "history" else security.quote_provider_symbol
        return SecurityProviderSymbol(security.security_id, provider.lower(), purpose.lower(), fallback or security.ticker, security.effective_from or "1900-01-01", None, security.source, security.verified_at or security.source_timestamp or "", None)

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
            if row is None:
                row = connection.execute(
                    """SELECT s.security_id, s.ticker, s.company_name, s.exchange, s.asset_type, s.active, s.sector, s.sector_id, s.industry,
                    s.quote_provider_symbol, s.history_provider_symbol, s.currency, s.country, s.index_memberships_json, s.effective_from,
                    s.effective_to, s.source, s.source_timestamp, s.verified_at, s.metadata_version
                    FROM security_aliases a JOIN securities s ON s.security_id=a.security_id
                    WHERE a.alias_ticker=? AND s.active=1""",
                    (ticker.upper(),),
                ).fetchone()
        if not row:
            return None
        values = list(row)
        values[13] = tuple(json.loads(values[13]))
        return SecurityRecord(*values)

    def active_securities(self, tickers: list[str] | tuple[str, ...]) -> dict[str, SecurityRecord]:
        """Resolve a symbol set in one durable read; aliases remain date-aware on the single-symbol seam."""
        self.initialize()
        symbols = sorted({ticker.strip().upper() for ticker in tickers if ticker.strip()})
        if not symbols:
            return {}
        placeholders = ",".join("?" for _ in symbols)
        with _lock, self._connect() as connection:
            rows = connection.execute(
                f"""SELECT security_id, ticker, company_name, exchange, asset_type, active, sector, sector_id, industry,
                quote_provider_symbol, history_provider_symbol, currency, country, index_memberships_json, effective_from,
                effective_to, source, source_timestamp, verified_at, metadata_version
                FROM securities WHERE ticker IN ({placeholders}) AND active=1""",
                symbols,
            ).fetchall()
        result: dict[str, SecurityRecord] = {}
        for row in rows:
            values = list(row)
            values[13] = tuple(json.loads(values[13]))
            record = SecurityRecord(*values)
            result[record.ticker.upper()] = record
        return result

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)


def _date_ranges_overlap(left_from: str, left_to: str | None, right_from: str, right_to: str | None) -> bool:
    return left_from <= (right_to or "9999-12-31") and right_from <= (left_to or "9999-12-31")

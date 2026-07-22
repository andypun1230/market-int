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
from app.themes.models import ThemeBasketBar, ThemeDefinition, ThemeMember
from app.themes.identifiers import normalize_theme_id

_lock = threading.RLock()


class ThemeStorage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.getenv("BREADTH_DB_PATH") or DEFAULT_DB_PATH)

    def initialize(self) -> None:
        with _lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS theme_definitions (
                theme_id TEXT NOT NULL, version TEXT NOT NULL, status TEXT NOT NULL, effective_from TEXT NOT NULL,
                payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(theme_id, version))""")
            connection.execute("CREATE INDEX IF NOT EXISTS theme_definitions_active ON theme_definitions(status, effective_from DESC)")
            connection.execute("""CREATE TABLE IF NOT EXISTS theme_members (
                theme_id TEXT NOT NULL, theme_version TEXT NOT NULL, ticker TEXT NOT NULL, active INTEGER NOT NULL,
                payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
                PRIMARY KEY(theme_id, theme_version, ticker))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS theme_basket_bars (
                theme_id TEXT NOT NULL, theme_version TEXT NOT NULL, session_date TEXT NOT NULL,
                formula_version TEXT NOT NULL, payload_json TEXT NOT NULL, input_hash TEXT NOT NULL,
                PRIMARY KEY(theme_id, theme_version, session_date, formula_version))""")
            connection.execute("CREATE INDEX IF NOT EXISTS theme_basket_bars_history ON theme_basket_bars(theme_id, theme_version, session_date)")
            self._migrate_legacy_ids(connection)
            connection.commit()

    def _migrate_legacy_ids(self, connection: sqlite3.Connection) -> None:
        """Rewrite known legacy kebab IDs once, rejecting divergent collisions."""
        for theme_id, version, payload in connection.execute("SELECT theme_id, version, payload_json FROM theme_definitions").fetchall():
            canonical = normalize_theme_id(theme_id)
            if canonical == theme_id:
                continue
            definition = deserialize_definition(payload)
            normalized_payload = json.dumps(definition.model_dump(), sort_keys=True)
            digest = hashlib.sha256(normalized_payload.encode()).hexdigest()
            existing = connection.execute("SELECT payload_hash FROM theme_definitions WHERE theme_id=? AND version=?", (canonical, version)).fetchone()
            if existing and existing[0] != digest:
                raise ValueError(f"legacy_theme_id_collision:{theme_id}:{canonical}:{version}")
            if existing:
                connection.execute("DELETE FROM theme_definitions WHERE theme_id=? AND version=?", (theme_id, version))
            else:
                connection.execute("UPDATE theme_definitions SET theme_id=?, payload_json=?, payload_hash=? WHERE theme_id=? AND version=?", (canonical, normalized_payload, digest, theme_id, version))
        for theme_id, version, ticker, payload in connection.execute("SELECT theme_id, theme_version, ticker, payload_json FROM theme_members").fetchall():
            canonical = normalize_theme_id(theme_id)
            if canonical == theme_id:
                continue
            member = deserialize_member(payload)
            normalized_payload = json.dumps(member.model_dump(), sort_keys=True)
            digest = hashlib.sha256(normalized_payload.encode()).hexdigest()
            existing = connection.execute("SELECT payload_hash FROM theme_members WHERE theme_id=? AND theme_version=? AND ticker=?", (canonical, version, ticker)).fetchone()
            if existing and existing[0] != digest:
                raise ValueError(f"legacy_theme_member_collision:{theme_id}:{canonical}:{version}:{ticker}")
            if existing:
                connection.execute("DELETE FROM theme_members WHERE theme_id=? AND theme_version=? AND ticker=?", (theme_id, version, ticker))
            else:
                connection.execute("UPDATE theme_members SET theme_id=?, payload_json=?, payload_hash=? WHERE theme_id=? AND theme_version=? AND ticker=?", (canonical, normalized_payload, digest, theme_id, version, ticker))
        for theme_id, version, session_date, formula_version, payload, input_hash in connection.execute("SELECT theme_id, theme_version, session_date, formula_version, payload_json, input_hash FROM theme_basket_bars").fetchall():
            canonical = normalize_theme_id(theme_id)
            if canonical == theme_id:
                continue
            bar = deserialize_basket_bar(payload)
            normalized_payload = json.dumps(bar.model_dump(), sort_keys=True)
            existing = connection.execute("SELECT input_hash FROM theme_basket_bars WHERE theme_id=? AND theme_version=? AND session_date=? AND formula_version=?", (canonical, version, session_date, formula_version)).fetchone()
            if existing and existing[0] != input_hash:
                raise ValueError(f"legacy_theme_basket_collision:{theme_id}:{canonical}:{version}:{session_date}")
            if existing:
                connection.execute("DELETE FROM theme_basket_bars WHERE theme_id=? AND theme_version=? AND session_date=? AND formula_version=?", (theme_id, version, session_date, formula_version))
            else:
                connection.execute("UPDATE theme_basket_bars SET theme_id=?, payload_json=? WHERE theme_id=? AND theme_version=? AND session_date=? AND formula_version=?", (canonical, normalized_payload, theme_id, version, session_date, formula_version))

    def save_definition(self, definition: ThemeDefinition, members: list[ThemeMember]) -> None:
        canonical_id = normalize_theme_id(definition.theme_id)
        definition = replace(definition, theme_id=canonical_id)
        members = [replace(member, theme_id=canonical_id) for member in members]
        self.initialize()
        definition_payload = json.dumps(definition.model_dump(), sort_keys=True)
        definition_hash = hashlib.sha256(definition_payload.encode()).hexdigest()
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT payload_hash FROM theme_definitions WHERE theme_id=? AND version=?", (definition.theme_id, definition.version)).fetchone()
            if existing and existing[0] != definition_hash:
                raise ValueError("theme_definition_versions_are_immutable")
            connection.execute("INSERT OR IGNORE INTO theme_definitions VALUES (?, ?, ?, ?, ?, ?, datetime('now'))", (definition.theme_id, definition.version, definition.status, definition.effective_from, definition_payload, definition_hash))
            for member in members:
                payload = json.dumps(member.model_dump(), sort_keys=True)
                digest = hashlib.sha256(payload.encode()).hexdigest()
                existing_member = connection.execute("SELECT payload_hash FROM theme_members WHERE theme_id=? AND theme_version=? AND ticker=?", (member.theme_id, member.theme_version, member.ticker.upper())).fetchone()
                if existing_member and existing_member[0] != digest:
                    raise ValueError("theme_member_versions_are_immutable")
                connection.execute("INSERT OR IGNORE INTO theme_members VALUES (?, ?, ?, ?, ?, ?)", (member.theme_id, member.theme_version, member.ticker.upper(), int(member.active), payload, digest))
            connection.commit()

    def definition(self, theme_id: str, version: str) -> ThemeDefinition | None:
        theme_id = normalize_theme_id(theme_id)
        self.initialize()
        with _lock, self._connect() as connection:
            row = connection.execute("SELECT payload_json FROM theme_definitions WHERE theme_id=? AND version=?", (theme_id, version)).fetchone()
        return deserialize_definition(row[0]) if row else None

    def members(self, theme_id: str, version: str, *, active_only: bool = True) -> list[ThemeMember]:
        theme_id = normalize_theme_id(theme_id)
        self.initialize()
        sql = "SELECT payload_json FROM theme_members WHERE theme_id=? AND theme_version=?"
        args: list[object] = [theme_id, version]
        if active_only:
            sql += " AND active=1"
        sql += " ORDER BY ticker"
        with _lock, self._connect() as connection:
            rows = connection.execute(sql, args).fetchall()
        return [deserialize_member(row[0]) for row in rows]

    def active_definitions(self) -> list[ThemeDefinition]:
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM theme_definitions WHERE status='active' ORDER BY theme_id, version").fetchall()
        return [deserialize_definition(row[0]) for row in rows]

    def definitions(self) -> list[ThemeDefinition]:
        self.initialize()
        with _lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM theme_definitions ORDER BY theme_id, version").fetchall()
        return [deserialize_definition(row[0]) for row in rows]

    def upsert_basket_bars(self, bars: list[ThemeBasketBar]) -> tuple[int, int]:
        bars = [replace(bar, theme_id=normalize_theme_id(bar.theme_id)) for bar in bars]
        self.initialize()
        inserted = updated = 0
        with _lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for bar in bars:
                payload = json.dumps(bar.model_dump(), sort_keys=True)
                row = connection.execute("SELECT input_hash FROM theme_basket_bars WHERE theme_id=? AND theme_version=? AND session_date=? AND formula_version=?", (bar.theme_id, bar.theme_version, bar.session_date, bar.formula_version)).fetchone()
                if row is None:
                    connection.execute("INSERT INTO theme_basket_bars VALUES (?, ?, ?, ?, ?, ?)", (bar.theme_id, bar.theme_version, bar.session_date, bar.formula_version, payload, bar.input_hash))
                    inserted += 1
                elif row[0] != bar.input_hash:
                    connection.execute("UPDATE theme_basket_bars SET payload_json=?, input_hash=? WHERE theme_id=? AND theme_version=? AND session_date=? AND formula_version=?", (payload, bar.input_hash, bar.theme_id, bar.theme_version, bar.session_date, bar.formula_version))
                    updated += 1
            connection.commit()
        return inserted, updated

    def basket_history(self, theme_id: str, version: str, *, formula_version: str | None = None, end_date: str | None = None) -> list[ThemeBasketBar]:
        theme_id = normalize_theme_id(theme_id)
        self.initialize()
        sql = "SELECT payload_json FROM theme_basket_bars WHERE theme_id=? AND theme_version=?"
        args: list[object] = [theme_id, version]
        if formula_version:
            sql += " AND formula_version=?"; args.append(formula_version)
        if end_date:
            sql += " AND session_date<=?"; args.append(end_date)
        sql += " ORDER BY session_date"
        with _lock, self._connect() as connection:
            rows = connection.execute(sql, args).fetchall()
        return [deserialize_basket_bar(row[0]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)


def deserialize_definition(payload: str) -> ThemeDefinition:
    data = json.loads(payload)
    data["parent_sector_ids"] = tuple(data.get("parent_sector_ids") or [])
    data["source_references"] = tuple(dict(item) for item in data.get("source_references") or [])
    data["theme_id"] = normalize_theme_id(data["theme_id"])
    return ThemeDefinition(**data)


def deserialize_member(payload: str) -> ThemeMember:
    data = json.loads(payload); data["theme_id"] = normalize_theme_id(data["theme_id"])
    return ThemeMember(**data)


def deserialize_basket_bar(payload: str) -> ThemeBasketBar:
    data = json.loads(payload); data["theme_id"] = normalize_theme_id(data["theme_id"])
    return ThemeBasketBar(**data)

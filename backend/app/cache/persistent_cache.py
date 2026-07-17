import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = BACKEND_ROOT / ".cache"
DB_PATH = CACHE_DIR / "market_cache.sqlite3"

_lock = threading.RLock()
_initialized = False


@dataclass
class PersistentCacheResult:
    value: Any
    fresh: bool
    stale: bool
    age_seconds: float
    expires_in_seconds: float
    created_at: float
    expires_at: float
    stale_until: float
    data_source: str | None
    metadata: dict[str, Any]


def initialize_persistent_cache() -> None:
    global _initialized
    with _lock:
        if _initialized:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        stale_until REAL NOT NULL,
                        data_source TEXT,
                        metadata_json TEXT
                    )
                    """
                )
                connection.commit()
            _initialized = True
        except Exception as exc:  # pragma: no cover - defensive only
            logger.warning("Persistent cache unavailable: %s: %s", type(exc).__name__, exc)


def connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)


def get_persistent_value(key: str, allow_stale: bool = False) -> PersistentCacheResult | None:
    initialize_persistent_cache()
    now = time.time()
    try:
        with _lock, connect() as connection:
            row = connection.execute(
                """
                SELECT value_json, created_at, expires_at, stale_until, data_source, metadata_json
                FROM cache_entries
                WHERE key = ?
                """,
                (key,),
            ).fetchone()
    except Exception as exc:
        logger.warning("Persistent cache read failed: %s: %s", type(exc).__name__, exc)
        return None

    if row is None:
        return None

    value_json, created_at, expires_at, stale_until, data_source, metadata_json = row
    fresh = expires_at > now
    stale = not fresh and stale_until > now
    if not fresh and not (allow_stale and stale):
        return None

    try:
        value = json.loads(value_json)
        metadata = json.loads(metadata_json) if metadata_json else {}
    except Exception:
        delete_persistent_value(key)
        return None

    return PersistentCacheResult(
        value=value,
        fresh=fresh,
        stale=stale,
        age_seconds=max(0.0, now - created_at),
        expires_in_seconds=expires_at - now,
        created_at=created_at,
        expires_at=expires_at,
        stale_until=stale_until,
        data_source=data_source,
        metadata=metadata,
    )


def set_persistent_value(
    key: str,
    value: Any,
    ttl_seconds: int,
    stale_seconds: int,
    data_source: str | None = None,
    metadata: dict | None = None,
) -> None:
    initialize_persistent_cache()
    now = time.time()
    try:
        value_json = json.dumps(to_jsonable(value), sort_keys=True)
        metadata_json = json.dumps(to_jsonable(metadata or {}), sort_keys=True)
        with _lock, connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                    (key, value_json, created_at, expires_at, stale_until, data_source, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    value_json,
                    now,
                    now + max(0, ttl_seconds),
                    now + max(ttl_seconds, ttl_seconds + stale_seconds),
                    data_source,
                    metadata_json,
                ),
            )
            connection.commit()
    except Exception as exc:
        logger.warning("Persistent cache write failed: %s: %s", type(exc).__name__, exc)


def delete_persistent_value(key: str) -> None:
    initialize_persistent_cache()
    try:
        with _lock, connect() as connection:
            connection.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            connection.commit()
    except Exception as exc:
        logger.warning("Persistent cache delete failed: %s: %s", type(exc).__name__, exc)


def delete_persistent_prefix(prefix: str) -> int:
    initialize_persistent_cache()
    try:
        with _lock, connect() as connection:
            cursor = connection.execute("DELETE FROM cache_entries WHERE key LIKE ?", (f"{prefix}%",))
            connection.commit()
            return cursor.rowcount
    except Exception as exc:
        logger.warning("Persistent cache prefix delete failed: %s: %s", type(exc).__name__, exc)
        return 0


def get_persistent_cache_status() -> dict[str, Any]:
    initialize_persistent_cache()
    now = time.time()
    try:
        with _lock, connect() as connection:
            rows = connection.execute(
                "SELECT key, created_at, expires_at, stale_until, data_source FROM cache_entries"
            ).fetchall()
    except Exception as exc:
        logger.warning("Persistent cache status failed: %s: %s", type(exc).__name__, exc)
        return {"items": 0, "keys": [], "available": False}

    ages = [now - row[1] for row in rows]
    return {
        "available": True,
        "items": len(rows),
        "keys": sorted(row[0] for row in rows),
        "fresh_items": sum(1 for row in rows if row[2] > now),
        "stale_items": sum(1 for row in rows if row[2] <= now < row[3]),
        "expired_items": sum(1 for row in rows if row[3] <= now),
        "oldest_item_age": round(max(ages), 2) if ages else None,
        "newest_item_age": round(min(ages), 2) if ages else None,
        "database_path": str(DB_PATH),
    }


def vacuum_expired_entries() -> int:
    initialize_persistent_cache()
    now = time.time()
    try:
        with _lock, connect() as connection:
            cursor = connection.execute("DELETE FROM cache_entries WHERE stale_until <= ?", (now,))
            connection.commit()
            return cursor.rowcount
    except Exception as exc:
        logger.warning("Persistent cache vacuum failed: %s: %s", type(exc).__name__, exc)
        return 0


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.providers.models import HistoryData, QuoteData

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "market_cache.sqlite3"


@dataclass(frozen=True)
class CachePolicy:
    memory_ttl_seconds: int
    persistent_ttl_seconds: int
    stale_while_revalidate_seconds: int
    allow_stale_on_error: bool
    persist: bool
    negative_ttl_seconds: int
    max_entries: int | None
    schema_version: int


@dataclass
class CacheLookupResult:
    value: Any | None
    fresh: bool
    stale: bool
    layer: str
    age_seconds: int | None = None
    expires_at: str | None = None
    stale_until: str | None = None
    provider: str | None = None
    source_state: str | None = None
    background_refresh_started: bool = False


@dataclass
class CacheWriteMetadata:
    domain: str
    provider: str
    source_state: str
    market_timestamp: str | None = None


class CachePolicyRegistry:
    def __init__(self) -> None:
        self.schema_version = env_int("MARKET_DATA_CACHE_SCHEMA_VERSION", 1)

    def for_domain(self, domain: str) -> CachePolicy:
        if domain == "quotes":
            return CachePolicy(
                memory_ttl_seconds=env_int("MARKET_DATA_QUOTE_TTL_SECONDS", 20),
                persistent_ttl_seconds=env_int("MARKET_DATA_QUOTE_PERSISTENT_TTL_SECONDS", 60),
                stale_while_revalidate_seconds=env_int("MARKET_DATA_QUOTE_STALE_SECONDS", 300),
                allow_stale_on_error=env_bool("MARKET_DATA_ALLOW_STALE_ON_PROVIDER_ERROR", True),
                persist=env_bool("MARKET_DATA_PERSISTENT_CACHE_ENABLED", True),
                negative_ttl_seconds=env_int("MARKET_DATA_NEGATIVE_CACHE_TTL_SECONDS", 30),
                max_entries=None,
                schema_version=self.schema_version,
            )
        if domain in {"daily_history", "technical_history"}:
            default_persistent = 6 * 60 * 60 if domain == "technical_history" else 12 * 60 * 60
            default_stale = 24 * 60 * 60 if domain == "technical_history" else 7 * 24 * 60 * 60
            return CachePolicy(
                memory_ttl_seconds=env_int("MARKET_DATA_HISTORY_TTL_SECONDS", 15 * 60),
                persistent_ttl_seconds=env_int("MARKET_DATA_HISTORY_PERSISTENT_TTL_SECONDS", default_persistent),
                stale_while_revalidate_seconds=env_int("MARKET_DATA_HISTORY_STALE_SECONDS", default_stale),
                allow_stale_on_error=env_bool("MARKET_DATA_ALLOW_STALE_ON_PROVIDER_ERROR", True),
                persist=True,
                negative_ttl_seconds=env_int("MARKET_DATA_NEGATIVE_CACHE_TTL_SECONDS", 30),
                max_entries=None,
                schema_version=self.schema_version,
            )
        return CachePolicy(
            memory_ttl_seconds=30,
            persistent_ttl_seconds=0,
            stale_while_revalidate_seconds=0,
            allow_stale_on_error=False,
            persist=False,
            negative_ttl_seconds=30,
            max_entries=None,
            schema_version=self.schema_version,
        )


class SQLiteMarketCache:
    def __init__(self, db_path: str | Path | None = None) -> None:
        configured = os.getenv("MARKET_DATA_CACHE_DB_PATH")
        if db_path is not None:
            self.db_path = Path(db_path)
        elif configured:
            path = Path(configured)
            self.db_path = path if path.is_absolute() else BACKEND_ROOT.parent / path
        else:
            self.db_path = DEFAULT_DB_PATH
        self._lock = threading.RLock()
        self._initialized = False
        self.last_cleanup_at: str | None = None
        self.read_errors = 0
        self.write_errors = 0
        self.corrupt_entries = 0

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_data_cache (
                        key TEXT PRIMARY KEY,
                        domain TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        source_state TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        fetched_at TEXT NOT NULL,
                        market_timestamp TEXT NULL,
                        expires_at TEXT NOT NULL,
                        stale_until TEXT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        schema_version INTEGER NOT NULL,
                        payload_hash TEXT NULL,
                        size_bytes INTEGER NULL,
                        access_count INTEGER NOT NULL DEFAULT 0,
                        last_accessed_at TEXT NULL
                    )
                    """
                )
                connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_cache_domain ON market_data_cache(domain)")
                connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_cache_provider ON market_data_cache(provider)")
                connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_cache_expires ON market_data_cache(expires_at)")
                connection.commit()
            self._initialized = True

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)

    def get(self, key: str, *, allow_stale: bool = False, expected_schema_version: int = 1) -> CacheLookupResult:
        self.initialize()
        now = time.time()
        now_text = to_iso(now)
        try:
            with self._lock, self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT domain, provider, source_state, payload_json, fetched_at, market_timestamp,
                           expires_at, stale_until, created_at, schema_version
                    FROM market_data_cache
                    WHERE key = ?
                    """,
                    (key,),
                ).fetchone()
                if row is None:
                    return CacheLookupResult(None, False, False, "persistent-miss")
                connection.execute(
                    "UPDATE market_data_cache SET access_count = access_count + 1, last_accessed_at = ? WHERE key = ?",
                    (now_text, key),
                )
                connection.commit()
        except Exception:
            self.read_errors += 1
            return CacheLookupResult(None, False, False, "persistent-error")

        domain, provider, source_state, payload_json, _fetched_at, _market_timestamp, expires_at, stale_until, created_at, schema_version = row
        if int(schema_version) != expected_schema_version:
            self.delete(key)
            return CacheLookupResult(None, False, False, "schema-mismatch")

        expires_epoch = from_iso_epoch(expires_at)
        stale_epoch = from_iso_epoch(stale_until) if stale_until else expires_epoch
        fresh = expires_epoch > now
        stale = not fresh and stale_epoch > now
        if not fresh and not (allow_stale and stale):
            return CacheLookupResult(None, False, False, "persistent-expired")

        try:
            raw = json.loads(payload_json)
            value = deserialize_cache_value(key, raw)
        except Exception:
            self.corrupt_entries += 1
            self.delete(key)
            return CacheLookupResult(None, False, False, "corrupt")

        return CacheLookupResult(
            value=value,
            fresh=fresh,
            stale=stale,
            layer="persistent",
            age_seconds=max(0, int(now - from_iso_epoch(created_at))),
            expires_at=expires_at,
            stale_until=stale_until,
            provider=provider,
            source_state=source_state,
        )

    def set(self, key: str, value: Any, policy: CachePolicy, metadata: CacheWriteMetadata) -> None:
        if not policy.persist or policy.persistent_ttl_seconds <= 0:
            return
        self.initialize()
        now = time.time()
        now_text = to_iso(now)
        expires_at = to_iso(now + max(0, policy.persistent_ttl_seconds))
        stale_until = to_iso(now + max(policy.persistent_ttl_seconds, policy.persistent_ttl_seconds + policy.stale_while_revalidate_seconds))
        payload_json = json.dumps(to_jsonable(value), sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        try:
            with self._lock, self._connect() as connection:
                existing = connection.execute("SELECT created_at FROM market_data_cache WHERE key = ?", (key,)).fetchone()
                created_at = existing[0] if existing else now_text
                connection.execute(
                    """
                    INSERT OR REPLACE INTO market_data_cache (
                        key, domain, provider, source_state, payload_json, fetched_at, market_timestamp,
                        expires_at, stale_until, created_at, updated_at, schema_version, payload_hash,
                        size_bytes, access_count, last_accessed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT access_count FROM market_data_cache WHERE key = ?), 0), ?)
                    """,
                    (
                        key,
                        metadata.domain,
                        metadata.provider,
                        metadata.source_state,
                        payload_json,
                        now_text,
                        metadata.market_timestamp,
                        expires_at,
                        stale_until,
                        created_at,
                        now_text,
                        policy.schema_version,
                        payload_hash,
                        len(payload_json.encode("utf-8")),
                        key,
                        now_text,
                    ),
                )
                connection.commit()
        except Exception:
            self.write_errors += 1

    def delete(self, key: str) -> None:
        self.initialize()
        try:
            with self._lock, self._connect() as connection:
                connection.execute("DELETE FROM market_data_cache WHERE key = ?", (key,))
                connection.commit()
        except Exception:
            self.write_errors += 1

    def clear_domain(self, domain: str) -> int:
        self.initialize()
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute("DELETE FROM market_data_cache WHERE domain = ?", (domain,))
                connection.commit()
                return int(cursor.rowcount)
        except Exception:
            self.write_errors += 1
            return 0

    def clear_prefix(self, prefix: str) -> int:
        self.initialize()
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute("DELETE FROM market_data_cache WHERE key LIKE ?", (f"{prefix}%",))
                connection.commit()
                return int(cursor.rowcount)
        except Exception:
            self.write_errors += 1
            return 0

    def keys_for_prefix(self, prefix: str) -> list[str]:
        self.initialize()
        try:
            with self._lock, self._connect() as connection:
                rows = connection.execute(
                    "SELECT key FROM market_data_cache WHERE key LIKE ?",
                    (f"{prefix}%",),
                ).fetchall()
            return [str(row[0]) for row in rows]
        except Exception:
            self.read_errors += 1
            return []

    def cleanup(self) -> dict[str, Any]:
        self.initialize()
        now = to_iso(time.time())
        deleted = 0
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute("DELETE FROM market_data_cache WHERE stale_until IS NOT NULL AND stale_until <= ?", (now,))
                deleted = int(cursor.rowcount)
                connection.commit()
            self.last_cleanup_at = now
        except Exception:
            self.write_errors += 1
        return {"deleted": deleted, "last_cleanup_at": self.last_cleanup_at}

    def status(self) -> dict[str, Any]:
        self.initialize()
        now = time.time()
        try:
            with self._lock, self._connect() as connection:
                rows = connection.execute(
                    "SELECT domain, provider, expires_at, stale_until, created_at, size_bytes FROM market_data_cache"
                ).fetchall()
        except Exception:
            self.read_errors += 1
            return {"enabled": True, "healthy": False, "entries": 0}

        domain_counts: dict[str, int] = {}
        provider_counts: dict[str, int] = {}
        ages: list[float] = []
        fresh = stale = expired = 0
        for domain, provider, expires_at, stale_until, created_at, _size in rows:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            expires_epoch = from_iso_epoch(expires_at)
            stale_epoch = from_iso_epoch(stale_until) if stale_until else expires_epoch
            if expires_epoch > now:
                fresh += 1
            elif stale_epoch > now:
                stale += 1
            else:
                expired += 1
            ages.append(max(0, now - from_iso_epoch(created_at)))
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "enabled": env_bool("MARKET_DATA_PERSISTENT_CACHE_ENABLED", True),
            "healthy": True,
            "entries": len(rows),
            "fresh_entries": fresh,
            "stale_entries": stale,
            "expired_entries": expired,
            "domain_counts": domain_counts,
            "provider_counts": provider_counts,
            "database_size_bytes": size_bytes,
            "database_size_mb": round(size_bytes / (1024 * 1024), 3),
            "oldest_entry_age_seconds": int(max(ages)) if ages else None,
            "newest_entry_age_seconds": int(min(ages)) if ages else None,
            "last_cleanup_at": self.last_cleanup_at,
            "read_errors": self.read_errors,
            "write_errors": self.write_errors,
            "corrupt_entries": self.corrupt_entries,
        }


class LayeredMarketDataCache:
    def __init__(
        self,
        *,
        persistent_cache: SQLiteMarketCache | None = None,
        policy_registry: CachePolicyRegistry | None = None,
        max_items: int = 1000,
    ) -> None:
        self.persistent = persistent_cache or SQLiteMarketCache()
        self.policy_registry = policy_registry or CachePolicyRegistry()
        self.max_items = max_items
        self._memory: dict[str, tuple[float, Any, float]] = {}
        self._lock = threading.RLock()
        self.memory_hit_count = 0
        self.memory_miss_count = 0
        self.persistent_hit_count = 0
        self.stale_hit_count = 0
        self.write_count = 0

    def get(self, key: str) -> tuple[Any | None, int | None]:
        now = time.time()
        with self._lock:
            item = self._memory.get(key)
            if item:
                expires_at, value, created_at = item
                if expires_at > now and is_cache_value_compatible(key, value):
                    self.memory_hit_count += 1
                    return mark_value_memory_hit(clone_model(value)), int(now - created_at)
                self._memory.pop(key, None)
            self.memory_miss_count += 1

        domain = domain_from_cache_key(key)
        policy = self.policy_registry.for_domain(domain)
        result = self.persistent.get(key, allow_stale=False, expected_schema_version=policy.schema_version)
        if result.value is not None and result.fresh:
            self.persistent_hit_count += 1
            ttl = max(1, int(from_iso_epoch(result.expires_at or to_iso(now)) - now))
            value = mark_value_persistent_hit(result.value)
            self._set_memory(key, value, ttl)
            return clone_model(value), result.age_seconds
        return None, None

    def get_stale(self, key: str) -> CacheLookupResult:
        domain = domain_from_cache_key(key)
        policy = self.policy_registry.for_domain(domain)
        result = self.persistent.get(key, allow_stale=True, expected_schema_version=policy.schema_version)
        if result.value is not None and result.stale:
            self.stale_hit_count += 1
            value = mark_value_stale(mark_value_persistent_hit(result.value))
            self._set_memory(key, value, min(30, max(1, policy.memory_ttl_seconds)))
            result.value = value
        return result

    def set(self, key: str, value: Any, ttl_seconds: int | None = None, *, domain: str | None = None, provider: str | None = None, source_state: str | None = None) -> None:
        domain_name = domain or domain_from_cache_key(key)
        policy = self.policy_registry.for_domain(domain_name)
        memory_ttl = ttl_seconds if ttl_seconds is not None else policy.memory_ttl_seconds
        self._set_memory(key, value, memory_ttl)
        self.write_count += 1
        metadata = CacheWriteMetadata(
            domain=domain_name,
            provider=provider or getattr(value, "provider", None) or getattr(value, "source", None) or "unknown",
            source_state=source_state or getattr(value, "source_state", None) or "unavailable",
            market_timestamp=getattr(value, "timestamp", None),
        )
        self.persistent.set(key, value, policy, metadata)

    def _set_memory(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            if len(self._memory) >= self.max_items:
                oldest = min(self._memory.items(), key=lambda item: item[1][2])[0]
                self._memory.pop(oldest, None)
            now = time.time()
            self._memory[key] = (now + max(1, ttl_seconds), clone_model(value), now)

    def invalidate(self, prefix: str | None = None) -> int:
        removed = 0
        with self._lock:
            if prefix is None:
                removed += len(self._memory)
                self._memory.clear()
            else:
                keys = [key for key in self._memory if key.startswith(prefix)]
                removed += len(keys)
                for key in keys:
                    self._memory.pop(key, None)
        if prefix is None:
            removed += self.persistent.clear_prefix("")
        else:
            removed += self.persistent.clear_prefix(prefix)
        return removed

    def clear_domain(self, domain: str) -> int:
        with self._lock:
            for key in [key for key in self._memory if domain_from_cache_key(key) == domain]:
                self._memory.pop(key, None)
        return self.persistent.clear_domain(domain)

    def find_history_covering(self, provider: str, symbol: str, resolution: str, days: int) -> tuple[Any | None, int | None, str | None]:
        prefix = f"history:{provider}:{symbol}:{resolution}:"
        with self._lock:
            keys = {key for key in self._memory if key.startswith(prefix)}
        keys.update(self.persistent.keys_for_prefix(prefix))
        candidates = sorted(
            (key for key in keys if history_cache_days(key) >= days),
            key=history_cache_days,
        )
        requested_key = build_history_cache_key(provider, symbol, resolution, days)
        for candidate in candidates:
            if candidate == requested_key:
                continue
            value, age = self.get(candidate)
            if value is None or not is_cache_value_compatible(requested_key, value):
                continue
            return narrow_history_value(value, days), age, candidate
        return None, None, None

    def cleanup(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            for key in [key for key, (expires_at, _value, _created) in self._memory.items() if expires_at <= now]:
                self._memory.pop(key, None)
        return self.persistent.cleanup()

    def status(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            expired = [key for key, (expires_at, _value, _created) in self._memory.items() if expires_at <= now]
            for key in expired:
                self._memory.pop(key, None)
            memory_status = {
                "items": len(self._memory),
                "keys": sorted(self._memory.keys()),
                "hit_count": self.memory_hit_count,
                "miss_count": self.memory_miss_count,
            }
        return {
            **memory_status,
            "persistent_hit_count": self.persistent_hit_count,
            "stale_hit_count": self.stale_hit_count,
            "write_count": self.write_count,
            "persistent": self.persistent.status(),
        }


def build_quote_cache_key(provider: str, symbol: str) -> str:
    return f"quote:{provider}:{symbol}"


def build_history_cache_key(provider: str, symbol: str, resolution: str, days: int) -> str:
    return f"history:{provider}:{symbol}:{resolution}:{days}"


def history_cache_days(key: str) -> int:
    parts = key.split(":")
    if len(parts) < 5:
        return 0
    try:
        return int(parts[4])
    except ValueError:
        return 0


def narrow_history_value(value: Any, days: int) -> Any:
    if not isinstance(value, HistoryData):
        return value
    candles = value.candles
    if candles:
        narrowed = candles_for_days(candles, days)
    else:
        narrowed = candles
    return value.model_copy(update={"candles": narrowed, "requested_days": days, "returned_candles": len(narrowed)})


def candles_for_days(candles: list[Any], days: int) -> list[Any]:
    if not candles:
        return candles
    last_timestamp = getattr(candles[-1], "timestamp", "")
    last_date = _parse_candle_timestamp(str(last_timestamp))
    if last_date is None:
        return candles[-max(1, days):]
    cutoff = last_date - timedelta(days=max(1, days) + 2)
    narrowed = [
        candle for candle in candles
        if (_parse_candle_timestamp(getattr(candle, "timestamp", "")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
    ]
    if narrowed:
        return narrowed[-max(1, days):]
    return candles[-max(1, days):]


def _parse_candle_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def domain_from_cache_key(key: str) -> str:
    if key.startswith("quote:"):
        return "quotes"
    if key.startswith("history:"):
        return "daily_history"
    if key.startswith("technical:"):
        return "technical_history"
    return "unknown"


def deserialize_cache_value(key: str, value: Any) -> Any:
    if key.startswith("quote:"):
        return QuoteData.model_validate(value)
    if key.startswith("history:"):
        return HistoryData.model_validate(value)
    return value


def is_cache_value_compatible(key: str, value: Any) -> bool:
    if key.startswith("history:") and isinstance(value, HistoryData):
        parts = key.split(":")
        requested_days = int(parts[4]) if len(parts) >= 5 and parts[4].isdigit() else value.requested_days
        if requested_days:
            returned = value.returned_candles or len(value.candles)
            if requested_days >= 300:
                return returned >= min(220, round(requested_days * 0.60))
            if requested_days >= 120:
                return returned >= min(90, round(requested_days * 0.50))
            return returned >= min(requested_days, len(value.candles))
    return True


def mark_value_stale(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"is_stale": True, "source_state": "stale", "cache_hit": True})
    return value


def mark_value_persistent_hit(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"persistent_cache_hit": True, "cache_hit": True})
    return value


def mark_value_memory_hit(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"memory_cache_hit": True, "cache_hit": True})
    return value


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


def clone_model(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(deep=True)
    if isinstance(value, (dict, list)):
        return json.loads(json.dumps(value))
    return value


def to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def from_iso_epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

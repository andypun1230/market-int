from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol, Self

from pydantic import Field, field_validator, model_validator

from app.intelligence.news.contracts import (
    CorrectionLineage,
    EventProviderMetadata,
    ExpectedDirection,
    NewsContractModel,
    NewsEventRecord,
    NewsEventStatus,
    NewsEventType,
    NewsSessionPhase,
    SourceQuality,
)


NEWS_METADATA_SCHEMA_VERSION = "news-metadata-v1"
FORBIDDEN_PERSISTENCE_KEYS = frozenset(
    {
        "article",
        "article_body",
        "body",
        "content",
        "full_text",
        "html",
        "raw_article",
        "raw_content",
        "raw_html",
        "source_summary",
        "summary",
        "text",
        "transcript",
    }
)


class StoredNewsEventMetadata(NewsContractModel):
    """Persistence whitelist. It deliberately omits facts, summaries and bodies."""

    event_id: str
    cluster_id: str
    canonical_headline: str
    event_type: NewsEventType
    event_subtype: str | None = None
    expected_direction: ExpectedDirection
    source_name: str
    source_identifier: str
    source_url: str | None = None
    source_quality: SourceQuality
    primary_source: bool
    published_at: datetime
    updated_at: datetime | None = None
    first_seen_at: datetime
    language: str
    market_date: date
    session_phase: NewsSessionPhase
    named_symbols: tuple[str, ...] = ()
    event_status: NewsEventStatus
    correction: CorrectionLineage
    provider_metadata: EventProviderMetadata
    quarantined: bool
    quarantine_reasons: tuple[str, ...] = ()
    schema_version: str = NEWS_METADATA_SCHEMA_VERSION

    @field_validator("published_at", "updated_at", "first_seen_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("stored_news_timestamp_must_be_timezone_aware")
        return value

    @classmethod
    def from_event(cls, event: NewsEventRecord) -> "StoredNewsEventMetadata":
        return cls(
            event_id=event.event_id,
            cluster_id=event.cluster_id,
            canonical_headline=event.canonical_headline,
            event_type=event.event_type,
            event_subtype=event.event_subtype,
            expected_direction=event.expected_direction,
            source_name=event.source_name,
            source_identifier=event.source_identifier,
            source_url=event.source_url,
            source_quality=event.source_quality,
            primary_source=event.primary_source,
            published_at=event.published_at,
            updated_at=event.updated_at,
            first_seen_at=event.first_seen_at,
            language=event.language,
            market_date=event.market_date,
            session_phase=event.session_phase,
            named_symbols=tuple(
                dict.fromkeys(
                    mapping.symbol
                    for mapping in event.affected_entities
                    if mapping.symbol is not None
                    and mapping.relationship.value == "directly_named"
                )
            ),
            event_status=event.event_status,
            correction=event.correction,
            provider_metadata=event.provider_metadata,
            quarantined=event.quarantined,
            quarantine_reasons=event.quarantine_reasons,
        )


class NewsMetadataQuery(NewsContractModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    symbols: tuple[str, ...] = ()
    event_types: tuple[NewsEventType, ...] = ()
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("metadata_query_timestamp_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("metadata_query_invalid_range")
        return self


class NewsMetadataReader(Protocol):
    def get(self, event_id: str) -> StoredNewsEventMetadata | None: ...

    def get_cluster(self, cluster_id: str) -> tuple[StoredNewsEventMetadata, ...]: ...

    def query(self, query: NewsMetadataQuery) -> tuple[StoredNewsEventMetadata, ...]: ...


class NewsMetadataWriter(Protocol):
    def save_events(self, events: tuple[NewsEventRecord, ...]) -> tuple[int, int]: ...


class NewsMetadataRepository(NewsMetadataReader, NewsMetadataWriter):
    """SQLite repository that can persist only the explicit metadata contract."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.RLock()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS news_event_metadata (
                event_id TEXT PRIMARY KEY,
                cluster_id TEXT NOT NULL,
                published_at TEXT NOT NULL,
                source_identifier TEXT NOT NULL,
                event_type TEXT NOT NULL,
                symbols_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                stored_at TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1
                )"""
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(news_event_metadata)")
            }
            if "revision" not in columns:
                connection.execute(
                    "ALTER TABLE news_event_metadata ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS news_metadata_time ON news_event_metadata(published_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS news_metadata_cluster ON news_event_metadata(cluster_id)"
            )
            connection.commit()

    def save_events(self, events: tuple[NewsEventRecord, ...]) -> tuple[int, int]:
        metadata = tuple(StoredNewsEventMetadata.from_event(event) for event in events)
        inserted = existing = 0
        self.initialize()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for item in metadata:
                payload = item.model_dump(mode="json")
                self.assert_metadata_only(payload)
                encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                row = connection.execute(
                    "SELECT payload_hash, payload_json, revision FROM news_event_metadata WHERE event_id=?",
                    (item.event_id,),
                ).fetchone()
                if row is not None:
                    if row[0] != digest:
                        previous = self._decode(row[1])
                        if self._stable_identity(previous) != self._stable_identity(item):
                            raise ValueError(f"immutable_news_event_identity_collision:{item.event_id}")
                        connection.execute(
                            """UPDATE news_event_metadata
                            SET cluster_id=?, symbols_json=?, payload_json=?, payload_hash=?, stored_at=?, revision=?
                            WHERE event_id=?""",
                            (
                                item.cluster_id,
                                json.dumps(sorted(item.named_symbols)),
                                encoded,
                                digest,
                                datetime.now(timezone.utc).isoformat(),
                                int(row[2]) + 1,
                                item.event_id,
                            ),
                        )
                    existing += 1
                    continue
                connection.execute(
                    """INSERT INTO news_event_metadata
                    (event_id, cluster_id, published_at, source_identifier, event_type,
                    symbols_json, payload_json, payload_hash, stored_at, revision)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.event_id,
                        item.cluster_id,
                        item.published_at.isoformat(),
                        item.source_identifier,
                        item.event_type.value,
                        json.dumps(sorted(item.named_symbols)),
                        encoded,
                        digest,
                        datetime.now(timezone.utc).isoformat(),
                        1,
                    ),
                )
                inserted += 1
            connection.commit()
        return inserted, existing

    def get(self, event_id: str) -> StoredNewsEventMetadata | None:
        self.initialize()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM news_event_metadata WHERE event_id=?",
                (event_id,),
            ).fetchone()
        return self._decode(row[0]) if row else None

    def get_cluster(self, cluster_id: str) -> tuple[StoredNewsEventMetadata, ...]:
        self.initialize()
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM news_event_metadata
                WHERE cluster_id=? ORDER BY published_at ASC, event_id ASC""",
                (cluster_id,),
            ).fetchall()
        return tuple(self._decode(row[0]) for row in rows)

    def query(self, query: NewsMetadataQuery) -> tuple[StoredNewsEventMetadata, ...]:
        self.initialize()
        clauses: list[str] = []
        values: list[object] = []
        if query.start_at:
            clauses.append("published_at>=?")
            values.append(query.start_at.isoformat())
        if query.end_at:
            clauses.append("published_at<=?")
            values.append(query.end_at.isoformat())
        if query.event_types:
            placeholders = ",".join("?" for _ in query.event_types)
            clauses.append(f"event_type IN ({placeholders})")
            values.extend(event_type.value for event_type in query.event_types)
        sql = "SELECT payload_json FROM news_event_metadata"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY published_at DESC, event_id LIMIT ?"
        values.append(query.limit)
        with self._lock, self._connect() as connection:
            rows = connection.execute(sql, values).fetchall()
        decoded = tuple(self._decode(row[0]) for row in rows)
        if not query.symbols:
            return decoded
        symbols = set(query.symbols)
        return tuple(item for item in decoded if symbols.intersection(item.named_symbols))[
            : query.limit
        ]

    @classmethod
    def assert_metadata_only(cls, value: object, path: str = "root") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized = str(key).casefold().replace("-", "_")
                if normalized in FORBIDDEN_PERSISTENCE_KEYS:
                    raise ValueError(f"article_content_persistence_forbidden:{path}.{key}")
                cls.assert_metadata_only(nested, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                cls.assert_metadata_only(nested, f"{path}[{index}]")

    def _decode(self, payload: str) -> StoredNewsEventMetadata:
        decoded = json.loads(payload)
        self.assert_metadata_only(decoded)
        return StoredNewsEventMetadata.model_validate(decoded)

    @staticmethod
    def _stable_identity(item: StoredNewsEventMetadata) -> tuple[object, ...]:
        return (
            item.event_id,
            item.canonical_headline,
            item.event_type,
            item.source_identifier,
            item.published_at,
            item.provider_metadata.provider,
            item.provider_metadata.provider_event_id,
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)


class InMemoryNewsMetadataRepository(NewsMetadataReader, NewsMetadataWriter):
    def __init__(self) -> None:
        self._items: dict[str, StoredNewsEventMetadata] = {}

    def save_events(self, events: tuple[NewsEventRecord, ...]) -> tuple[int, int]:
        inserted = existing = 0
        for event in events:
            item = StoredNewsEventMetadata.from_event(event)
            payload = item.model_dump(mode="json")
            NewsMetadataRepository.assert_metadata_only(payload)
            prior = self._items.get(item.event_id)
            if prior is not None and prior != item:
                if NewsMetadataRepository._stable_identity(prior) != NewsMetadataRepository._stable_identity(item):
                    raise ValueError(f"immutable_news_event_identity_collision:{item.event_id}")
                self._items[item.event_id] = item
            if prior is None:
                self._items[item.event_id] = item
                inserted += 1
            else:
                existing += 1
        return inserted, existing

    def get(self, event_id: str) -> StoredNewsEventMetadata | None:
        return self._items.get(event_id)

    def get_cluster(self, cluster_id: str) -> tuple[StoredNewsEventMetadata, ...]:
        return tuple(
            sorted(
                (item for item in self._items.values() if item.cluster_id == cluster_id),
                key=lambda item: (item.published_at, item.event_id),
            )
        )

    def query(self, query: NewsMetadataQuery) -> tuple[StoredNewsEventMetadata, ...]:
        selected: list[StoredNewsEventMetadata] = []
        symbols = set(query.symbols)
        for item in sorted(
            self._items.values(),
            key=lambda candidate: (candidate.published_at, candidate.event_id),
            reverse=True,
        ):
            if query.start_at and item.published_at < query.start_at:
                continue
            if query.end_at and item.published_at > query.end_at:
                continue
            if query.event_types and item.event_type not in query.event_types:
                continue
            if symbols and not symbols.intersection(item.named_symbols):
                continue
            selected.append(item)
            if len(selected) >= query.limit:
                break
        return tuple(selected)

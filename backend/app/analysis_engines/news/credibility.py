from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from app.intelligence.news.contracts import (
    NewsContractModel,
    NewsEventType,
    NewsProviderMode,
    SourceQuality,
    SourceRegistryRecord,
)


SOURCE_CREDIBILITY_VERSION = "news-source-credibility-v1"
DEFAULT_SOURCE_REGISTRY = (
    Path(__file__).resolve().parents[2] / "intelligence" / "news" / "source_registry.json"
)


class SourceCredibilityAssessment(NewsContractModel):
    source_identifier: str
    registered: bool
    allowed: bool
    quality: SourceQuality
    primary_source: bool
    source_url: str | None = None
    url_accepted: bool
    reasons: tuple[str, ...] = ()
    registry_version: str
    engine_version: str = SOURCE_CREDIBILITY_VERSION


class SourceRegistry:
    """Configured credibility metadata; provider claims never set their own tier."""

    def __init__(
        self,
        records: tuple[SourceRegistryRecord, ...],
        *,
        version: str,
    ) -> None:
        by_id = {record.source_id: record for record in records}
        if len(by_id) != len(records):
            raise ValueError("duplicate_news_source_registry_id")
        self.records = records
        self.version = version
        self._by_id = by_id

    @classmethod
    def load(cls, path: str | Path | None = None) -> "SourceRegistry":
        payload = json.loads(Path(path or DEFAULT_SOURCE_REGISTRY).read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
            raise ValueError("invalid_news_source_registry")
        version = str(payload.get("registryVersion") or "").strip()
        if not version:
            raise ValueError("news_source_registry_version_required")
        records = tuple(SourceRegistryRecord.model_validate(item) for item in payload["sources"])
        return cls(records, version=version)

    def get(self, source_identifier: str) -> SourceRegistryRecord | None:
        return self._by_id.get(source_identifier.casefold().strip())

    def assess(
        self,
        *,
        source_identifier: str,
        event_type: NewsEventType,
        source_url: str | None,
        provider_mode: NewsProviderMode,
    ) -> SourceCredibilityAssessment:
        identifier = source_identifier.casefold().strip()
        record = self.get(identifier)
        if record is None:
            return SourceCredibilityAssessment(
                source_identifier=identifier or "unregistered",
                registered=False,
                allowed=False,
                quality=SourceQuality.UNAVAILABLE,
                primary_source=False,
                source_url=None,
                url_accepted=False,
                reasons=("source_registry_miss",),
                registry_version=self.version,
            )

        reasons: list[str] = []
        allowed = record.active
        quality = record.quality_tier
        if not record.active:
            quality = SourceQuality.UNAVAILABLE
            reasons.append("source_inactive")
        if record.test_only and provider_mode != NewsProviderMode.HERMETIC:
            allowed = False
            quality = SourceQuality.UNAVAILABLE
            reasons.append("test_only_source_in_non_test_provider")
        if event_type not in record.allowed_event_types:
            allowed = False
            quality = SourceQuality.UNVERIFIED
            reasons.append("event_type_not_allowed_for_source")

        accepted_url: str | None = None
        url_accepted = source_url is None
        if source_url:
            parsed = urlparse(source_url)
            host = (parsed.hostname or "").casefold().rstrip(".")
            url_accepted = bool(
                parsed.scheme == "https"
                and host
                and not parsed.username
                and not parsed.password
                and (host == record.domain or host.endswith(f".{record.domain}"))
            )
            if url_accepted:
                accepted_url = source_url
            else:
                allowed = False
                quality = SourceQuality.UNAVAILABLE
                reasons.append("source_url_domain_mismatch")

        primary = bool(
            allowed
            and quality == SourceQuality.PRIMARY
            and event_type in record.primary_source_categories
        )
        return SourceCredibilityAssessment(
            source_identifier=identifier,
            registered=True,
            allowed=allowed,
            quality=quality,
            primary_source=primary,
            source_url=accepted_url,
            url_accepted=url_accepted,
            reasons=tuple(dict.fromkeys(reasons)),
            registry_version=self.version,
        )


class SourceCredibilityEngine:
    version = SOURCE_CREDIBILITY_VERSION

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        self.registry = registry or SourceRegistry.load()

    def assess(
        self,
        *,
        source_identifier: str,
        event_type: NewsEventType,
        source_url: str | None,
        provider_mode: NewsProviderMode,
    ) -> SourceCredibilityAssessment:
        return self.registry.assess(
            source_identifier=source_identifier,
            event_type=event_type,
            source_url=source_url,
            provider_mode=provider_mode,
        )

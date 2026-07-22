from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.analysis_engines.news import NewsEntityMappingEngine, NewsNormalizationEngine
from app.intelligence.news import (
    NewsEventRecord,
    NewsEventStatus,
    NewsEventType,
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
)
from app.providers.news import NewsProviderItem
from app.securities.models import SecurityRecord
from app.themes.models import ThemeDefinition, ThemeMember


NOW = datetime(2026, 7, 22, 16, 0, tzinfo=timezone.utc)


def provider_item(
    provider_event_id: str = "evt-1",
    *,
    headline: str = "Acme raises full-year guidance",
    summary: str = "Acme raised its full-year outlook.",
    source_identifier: str = "fixture-company-ir",
    source_name: str = "Acme Investor Relations",
    source_url: str | None = "https://ir.fixture.test/releases/evt-1",
    published_at: datetime | None = NOW - timedelta(hours=1),
    structured_event_type: NewsEventType | None = NewsEventType.GUIDANCE,
    structured_symbols: tuple[str, ...] = ("ACME",),
    confirmed_facts: tuple[str, ...] = ("Acme raised full-year guidance.",),
    event_status: NewsEventStatus = NewsEventStatus.CONFIRMED,
    **updates: object,
) -> NewsProviderItem:
    payload: dict[str, object] = {
        "provider_event_id": provider_event_id,
        "headline": headline,
        "summary": summary,
        "source_identifier": source_identifier,
        "source_name": source_name,
        "source_url": source_url,
        "published_at": published_at,
        "first_seen_at": published_at + timedelta(minutes=5) if published_at else None,
        "structured_event_type": structured_event_type,
        "structured_symbols": structured_symbols,
        "confirmed_facts": confirmed_facts,
        "event_status": event_status,
        "is_official_release": source_identifier == "fixture-company-ir",
    }
    payload.update(updates)
    return NewsProviderItem.model_validate(payload)


def hermetic_provenance() -> NewsProviderProvenance:
    return NewsProviderProvenance(
        provider="hermetic-news",
        mode=NewsProviderMode.HERMETIC,
        source_state=NewsFreshnessState.TEST,
        as_of=NOW,
        fetched_at=NOW,
    )


def normalized_event(item: NewsProviderItem | None = None) -> NewsEventRecord:
    result = NewsNormalizationEngine().normalize(
        item or provider_item(),
        hermetic_provenance(),
        now=NOW,
    )
    assert result.event is not None, result.issues
    return result.event


def security_record(symbol: str = "ACME") -> SecurityRecord:
    return SecurityRecord(
        security_id=f"sec-{symbol.casefold()}",
        ticker=symbol,
        company_name="Acme Corporation" if symbol == "ACME" else f"{symbol} Corporation",
        sector="Information Technology",
        sector_id="information_technology",
        industry="Application Software",
        active=True,
        index_memberships=("S&P 100",),
        effective_from="2026-01-01",
        source="stage8-test-security-registry",
        source_timestamp="2026-07-01",
        verified_at="2026-07-01T00:00:00Z",
        metadata_version=3,
    )


def active_theme() -> tuple[ThemeDefinition, list[ThemeMember]]:
    definition = ThemeDefinition(
        theme_id="software_infrastructure",
        display_name="Software Infrastructure",
        description="Reviewed test theme.",
        version="v1.0",
        status="active",
        effective_from="2026-01-01",
        methodology="Reviewed membership only.",
        inclusion_criteria="Reviewed constituents.",
        exclusion_criteria="Unreviewed constituents.",
        weighting_policy="Equal weight.",
        primary_benchmark="SPY",
        secondary_benchmark=None,
        parent_sector_ids=("information_technology",),
        minimum_members=1,
        complete_coverage_threshold=0.9,
        partial_coverage_threshold=0.75,
        source_references=({"title": "Fixture", "url": "https://fixture.test", "retrieved_at": "2026-07-01"},),
        verification_date="2026-07-01",
        reviewed_at="2026-07-01T00:00:00Z",
        reviewed_by="stage8-test",
    )
    member = ThemeMember(
        theme_id=definition.theme_id,
        theme_version=definition.version,
        ticker="ACME",
        security_id="sec-acme",
        company_name="Acme Corporation",
        role="core",
        weight=1.0,
        effective_from="2026-01-01",
        active=True,
        membership_source="stage8-reviewed-fixture",
        inclusion_reason="Reviewed fixture membership.",
        reviewed_at="2026-07-01T00:00:00Z",
        reviewed_by="stage8-test",
    )
    return definition, [member]


def mapping_engine(*, include_theme: bool = True) -> NewsEntityMappingEngine:
    record = security_record()
    return NewsEntityMappingEngine(
        security_resolver=lambda symbol: record if symbol == "ACME" else None,
        theme_loader=(lambda: [active_theme()]) if include_theme else (lambda: []),
    )

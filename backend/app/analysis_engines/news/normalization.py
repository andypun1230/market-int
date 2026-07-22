from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.analysis_engines.freshness import (
    FreshnessAvailabilityEngine,
    FreshnessAvailabilityInput,
)
from app.analysis_engines.news.credibility import SourceCredibilityEngine
from app.analysis_engines.news.security import NewsContentSecurityEngine
from app.analysis_engines.news.taxonomy import NewsTaxonomyEngine
from app.intelligence.news.contracts import (
    CorrectionLineage,
    CorrectionStatus,
    EventProviderMetadata,
    EvidenceKind,
    InterpretationClass,
    NewsAvailability,
    NewsContractModel,
    NewsEventRecord,
    NewsEventStatus,
    NewsEvidenceRecord,
    NewsFreshness,
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
    NewsSessionPhase,
    SourceQuality,
)
from app.providers.news.models import NewsProviderItem


NEWS_NORMALIZATION_VERSION = "news-normalization-v1"
NEW_YORK = ZoneInfo("America/New_York")


class NewsNormalizationIssue(NewsContractModel):
    provider_event_id: str
    code: str
    detail: str


class NewsNormalizationResult(NewsContractModel):
    event: NewsEventRecord | None
    evidence: tuple[NewsEvidenceRecord, ...] = ()
    issues: tuple[NewsNormalizationIssue, ...] = ()
    engine_version: str = NEWS_NORMALIZATION_VERSION


class NewsNormalizationEngine:
    version = NEWS_NORMALIZATION_VERSION

    def __init__(
        self,
        *,
        credibility: SourceCredibilityEngine | None = None,
        taxonomy: NewsTaxonomyEngine | None = None,
        security: NewsContentSecurityEngine | None = None,
        freshness: FreshnessAvailabilityEngine | None = None,
        stale_after_seconds: int = 172_800,
    ) -> None:
        self.credibility = credibility or SourceCredibilityEngine()
        self.taxonomy = taxonomy or NewsTaxonomyEngine()
        self.security = security or NewsContentSecurityEngine()
        self.freshness = freshness or FreshnessAvailabilityEngine()
        self.stale_after_seconds = stale_after_seconds

    def normalize(
        self,
        item: NewsProviderItem,
        provenance: NewsProviderProvenance,
        *,
        now: datetime,
    ) -> NewsNormalizationResult:
        if item.published_at is None:
            return self._rejected(item, "missing_event_timestamp", "published_at is required")
        published = item.published_at
        if published > now + timedelta(minutes=5):
            return self._rejected(
                item,
                "future_event_timestamp",
                "published_at is later than the allowed clock-skew window",
            )
        if item.updated_at and item.updated_at > now + timedelta(minutes=5):
            return self._rejected(
                item,
                "future_update_timestamp",
                "updated_at is later than the allowed clock-skew window",
            )
        first_seen = item.first_seen_at or provenance.fetched_at or provenance.as_of
        if first_seen < published:
            return self._rejected(
                item,
                "invalid_first_seen_timestamp",
                "first_seen_at precedes published_at",
            )

        headline = self.security.sanitize(item.headline, max_output=500)
        summary = self.security.sanitize(item.summary, max_output=2_000)
        source_name = self.security.sanitize(item.source_name, max_output=200)
        subtype = self.security.sanitize(item.structured_event_subtype or "", max_output=120)
        correction_reason = self.security.sanitize(item.correction_reason or "", max_output=1_000)
        fact_results = tuple(
            self.security.sanitize(fact, max_output=1_000) for fact in item.confirmed_facts
        )
        unsafe_reasons = tuple(
            dict.fromkeys(
                reason
                for result in (
                    headline,
                    summary,
                    source_name,
                    subtype,
                    correction_reason,
                    *fact_results,
                )
                for reason in result.reasons
            )
        )
        safe_headline = headline.safe_text or "Quarantined untrusted news content"
        safe_summary = summary.safe_text
        safe_facts = tuple(result.safe_text for result in fact_results if result.safe_text)

        classification = self.taxonomy.classify(
            headline=safe_headline,
            summary=safe_summary,
            confirmed_facts=safe_facts,
            structured_event_type=item.structured_event_type,
            structured_subtype=subtype.safe_text or None,
            structured_direction=item.expected_direction,
        )
        effective_mode = item.origin_provider_mode or provenance.mode
        effective_provider = item.origin_provider or provenance.provider
        effective_fetched_at = item.origin_fetched_at or provenance.fetched_at or provenance.as_of
        credibility = self.credibility.assess(
            source_identifier=item.source_identifier,
            event_type=classification.event_type,
            source_url=item.source_url,
            provider_mode=effective_mode,
        )
        source_spoofed = "source_url_domain_mismatch" in credibility.reasons
        quarantined = bool(unsafe_reasons or source_spoofed)
        quarantine_reasons = tuple(
            dict.fromkeys((*unsafe_reasons, *(credibility.reasons if source_spoofed else ())))
        )
        event_status = self._status(item)
        if quarantined or credibility.quality in {SourceQuality.UNVERIFIED, SourceQuality.UNAVAILABLE}:
            event_status = NewsEventStatus.UNVERIFIED
            safe_facts = ()

        local = published.astimezone(NEW_YORK)
        market_date = local.date()
        session_phase = self._session_phase(local)
        freshness_result = self.freshness.evaluate(
            FreshnessAvailabilityInput(
                source_state=provenance.source_state.value,
                generated_at=effective_fetched_at.isoformat(),
                observed_at=published.isoformat(),
                market_date=market_date.isoformat(),
                stale_after_seconds=self.stale_after_seconds,
                completeness=(
                    0.0 if quarantined else 1.0 if credibility.allowed else 0.5
                ),
                provider=effective_provider,
                test_data=effective_mode == NewsProviderMode.HERMETIC,
                fallback_used=bool(provenance.fallback_reason),
                warnings=tuple((*credibility.reasons, *quarantine_reasons)),
                now=now,
            )
        )
        freshness = NewsFreshness(
            state=NewsFreshnessState(freshness_result.state),
            availability=NewsAvailability(freshness_result.availability),
            market_date=market_date,
            generated_at=effective_fetched_at,
            observed_at=published,
            expires_at=None,
            age_seconds=freshness_result.age_seconds,
            completeness=freshness_result.completeness,
            provider=freshness_result.provider,
            fallback_used=freshness_result.fallback_used,
            mixed_sources=freshness_result.mixed_sources,
            confidence_cap_recommendation=(
                freshness_result.confidence_cap_recommendation
            ),
            warnings=freshness_result.warnings,
            engine_version=freshness_result.engine_version,
        )

        event_id = self.event_id(
            effective_provider,
            item.provider_event_id,
            item.source_identifier,
            published,
        )
        source_id = f"news-source-{self._digest(item.source_identifier + '|' + item.provider_event_id)}"
        evidence = (
            tuple(
                NewsEvidenceRecord(
                    evidence_id=f"news-evidence-{self._digest(event_id + '|fact|' + str(index) + '|' + fact)}",
                    source_id=source_id,
                    event_id=event_id,
                    kind=EvidenceKind.CONFIRMED_FACT,
                    statement=fact,
                    interpretation_class=InterpretationClass.OBSERVED_FACT,
                    observed_at=published,
                    market_date=market_date,
                    source_quality=credibility.quality,
                    quarantined=False,
                )
                for index, fact in enumerate(safe_facts)
            )
            if safe_facts
            else (
                NewsEvidenceRecord(
                    evidence_id=f"news-evidence-{self._digest(event_id + '|source')}",
                    source_id=source_id,
                    event_id=event_id,
                    kind=EvidenceKind.SOURCE_METADATA,
                    statement=f"Source metadata records the event headline: {safe_headline}",
                    interpretation_class=(
                        InterpretationClass.MISSING_EVIDENCE
                        if quarantined or credibility.quality == SourceQuality.UNAVAILABLE
                        else InterpretationClass.OBSERVED_FACT
                    ),
                    observed_at=published,
                    market_date=market_date,
                    source_quality=credibility.quality,
                    quarantined=quarantined,
                ),
            )
        )
        correction = CorrectionLineage(
            status=item.correction_status,
            supersedes_event_id=(
                self._lineage_reference(effective_provider, item.supersedes_provider_event_id)
                if item.supersedes_provider_event_id
                else None
            ),
            superseded_by_event_id=(
                self._lineage_reference(effective_provider, item.superseded_by_provider_event_id)
                if item.superseded_by_provider_event_id
                else None
            ),
            correction_reason=correction_reason.safe_text or None,
        )
        event = NewsEventRecord(
            event_id=event_id,
            cluster_id=f"news-cluster-pending-{self._digest(event_id)}",
            canonical_headline=safe_headline,
            event_type=classification.event_type,
            event_subtype=classification.subtype,
            expected_direction=classification.expected_direction,
            source_name=source_name.safe_text or "Untrusted source name omitted",
            source_identifier=item.source_identifier.casefold(),
            source_url=credibility.source_url,
            source_quality=credibility.quality,
            primary_source=credibility.primary_source,
            published_at=published,
            updated_at=item.updated_at,
            first_seen_at=first_seen,
            language=item.language,
            market_date=market_date,
            session_phase=session_phase,
            confirmed_facts=safe_facts,
            source_summary=safe_summary,
            affected_entities=(),
            affected_sectors=(),
            affected_themes=(),
            affected_indexes=(),
            event_status=event_status,
            correction=correction,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            freshness=freshness,
            provider_metadata=EventProviderMetadata(
                provider=effective_provider,
                provider_event_id=item.provider_event_id,
                provider_mode=effective_mode,
                fetched_at=effective_fetched_at,
                canonical_event_reference=item.canonical_event_reference,
            ),
            quarantined=quarantined,
            quarantine_reasons=quarantine_reasons,
        )
        issues = tuple(
            NewsNormalizationIssue(
                provider_event_id=item.provider_event_id,
                code=reason,
                detail=reason.replace("_", " "),
            )
            for reason in tuple(dict.fromkeys((*credibility.reasons, *quarantine_reasons)))
        )
        return NewsNormalizationResult(event=event, evidence=evidence, issues=issues)

    @staticmethod
    def event_id(
        provider: str,
        provider_event_id: str,
        source_identifier: str,
        published_at: datetime,
    ) -> str:
        identity = "|".join(
            (
                provider.casefold(),
                provider_event_id.strip(),
                source_identifier.casefold(),
                published_at.isoformat(),
            )
        )
        return f"news-event-{NewsNormalizationEngine._digest(identity)}"

    @staticmethod
    def _status(item: NewsProviderItem) -> NewsEventStatus:
        if item.correction_status == CorrectionStatus.RETRACTED:
            return NewsEventStatus.RETRACTED
        if item.correction_status == CorrectionStatus.CORRECTED:
            return NewsEventStatus.CORRECTED
        if item.correction_status == CorrectionStatus.SUPERSEDED:
            return NewsEventStatus.CORRECTED
        return item.event_status

    @staticmethod
    def _lineage_reference(provider: str, value: str) -> str:
        if value.startswith("provider:") or value.startswith("news-event-"):
            return value
        return f"provider:{provider}:{value}"

    @staticmethod
    def _session_phase(value: datetime) -> NewsSessionPhase:
        if value.weekday() >= 5:
            return NewsSessionPhase.WEEKEND
        minute = value.hour * 60 + value.minute
        if 4 * 60 <= minute < 9 * 60 + 30:
            return NewsSessionPhase.PREMARKET
        if 9 * 60 + 30 <= minute < 16 * 60:
            return NewsSessionPhase.REGULAR
        if 16 * 60 <= minute < 20 * 60:
            return NewsSessionPhase.AFTER_HOURS
        return NewsSessionPhase.CLOSED

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _rejected(
        item: NewsProviderItem,
        code: str,
        detail: str,
    ) -> NewsNormalizationResult:
        return NewsNormalizationResult(
            event=None,
            issues=(
                NewsNormalizationIssue(
                    provider_event_id=item.provider_event_id,
                    code=code,
                    detail=detail,
                ),
            ),
        )

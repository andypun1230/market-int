from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.analysis_engines.evidence_validation import EvidenceValidationEngine
from app.analysis_engines.freshness import FreshnessAvailabilityEngine, FreshnessAvailabilityInput
from app.intelligence.news.contracts import (
    EntityMapping,
    EntityType,
    EvidenceKind,
    InterpretationClass,
    MappingRelationship,
    NewsAvailability,
    NewsContractModel,
    NewsEventRecord,
    NewsEvidenceRecord,
    NewsFreshness,
    NewsFreshnessState,
    SourceQuality,
)


NEWS_ENTITY_MAPPING_VERSION = "news-entity-mapping-v1"
AMBIGUOUS_TICKER_WORDS = frozenset(
    {"A", "AI", "ALL", "ARE", "CAN", "FOR", "IT", "ON", "OR", "SO", "TO"}
)


class NewsEntityMappingContext(NewsContractModel):
    candidate_symbols: tuple[str, ...] = ()
    candidate_company_names: tuple[str, ...] = ()
    watchlist_symbols: tuple[str, ...] = ()


class NewsEntityMappingResult(NewsContractModel):
    mappings: tuple[EntityMapping, ...]
    evidence: tuple[NewsEvidenceRecord, ...]
    rejected_candidates: tuple[str, ...] = ()
    engine_version: str = NEWS_ENTITY_MAPPING_VERSION


class NewsEntityMappingEngine:
    """Map only canonical registry relationships; never infer business links."""

    version = NEWS_ENTITY_MAPPING_VERSION

    def __init__(
        self,
        *,
        security_resolver: Callable[[str], Any | None] | None = None,
        company_resolver: Callable[[str], Any | None] | None = None,
        theme_loader: Callable[[], list[tuple[Any, list[Any]]]] | None = None,
    ) -> None:
        self.security_resolver = security_resolver or self._project_security_resolver
        self.company_resolver = company_resolver
        self.theme_loader = theme_loader or self._project_theme_loader
        self.freshness_engine = FreshnessAvailabilityEngine()
        self.evidence_engine = EvidenceValidationEngine()

    def map_event(
        self,
        event: NewsEventRecord,
        context: NewsEntityMappingContext,
        *,
        now: datetime,
    ) -> NewsEntityMappingResult:
        candidates: list[tuple[str, str]] = [
            (symbol.upper(), "structured") for symbol in context.candidate_symbols
        ]
        combined = f"{event.canonical_headline} {event.source_summary}"
        candidates.extend((match.upper(), "marked") for match in re.findall(r"\$([A-Za-z][A-Za-z0-9.-]{0,9})\b", combined))
        candidates.extend((match.upper(), "parenthetical") for match in re.findall(r"\(([A-Z][A-Z0-9.-]{0,9})\)", combined))
        for company_name in context.candidate_company_names:
            if self.company_resolver is None:
                continue
            record = self.company_resolver(company_name)
            if record is not None:
                candidates.append((str(record.ticker).upper(), "structured_company"))

        selected_records: dict[str, tuple[Any, str]] = {}
        rejected: list[str] = []
        for symbol, source in candidates:
            if source == "parenthetical" and symbol in AMBIGUOUS_TICKER_WORDS:
                rejected.append(f"ambiguous_ticker:{symbol}")
                continue
            record = self.security_resolver(symbol)
            if record is None or not bool(getattr(record, "active", True)):
                rejected.append(f"unregistered_ticker:{symbol}")
                continue
            selected_records.setdefault(str(record.ticker).upper(), (record, source))

        mappings: list[EntityMapping] = []
        evidence: list[NewsEvidenceRecord] = []
        theme_rows = self._safe_themes() if selected_records else []
        watchlist = {symbol.upper() for symbol in context.watchlist_symbols}
        for symbol, (record, _source) in sorted(selected_records.items()):
            mapping_freshness = self._mapping_freshness(record, now=now)
            direct_type = EntityType.ETF if str(getattr(record, "asset_type", "equity")) == "etf" else EntityType.SECURITY
            direct = self._mapping(
                event,
                entity_id=str(record.security_id),
                entity_type=direct_type,
                display_name=str(record.company_name),
                symbol=symbol,
                relationship=MappingRelationship.DIRECTLY_NAMED,
                source=f"security-master:{record.source}",
                confidence=1.0,
                freshness=mapping_freshness,
                version=f"security-master-v{getattr(record, 'metadata_version', 1)}",
            )
            self._append_mapping(direct, event, mappings, evidence)
            company = self._mapping(
                event,
                entity_id=f"company:{record.security_id}",
                entity_type=EntityType.COMPANY,
                display_name=str(record.company_name),
                symbol=symbol,
                relationship=MappingRelationship.COMPANY_PARENT,
                source=f"security-master:{record.source}",
                confidence=1.0,
                freshness=mapping_freshness,
                version=f"security-master-v{getattr(record, 'metadata_version', 1)}",
            )
            self._append_mapping(company, event, mappings, evidence)
            sector_id = getattr(record, "sector_id", None)
            sector = str(getattr(record, "sector", "") or "")
            if sector_id and sector and sector != "Unknown":
                mapped = self._mapping(
                    event,
                    entity_id=str(sector_id),
                    entity_type=EntityType.SECTOR,
                    display_name=sector,
                    symbol=None,
                    relationship=MappingRelationship.SECTOR_MEMBERSHIP,
                    source=f"security-master:{record.source}",
                    confidence=1.0,
                    freshness=mapping_freshness,
                    version=f"security-master-v{getattr(record, 'metadata_version', 1)}",
                )
                self._append_mapping(mapped, event, mappings, evidence)
            industry = str(getattr(record, "industry", "") or "")
            if industry:
                mapped = self._mapping(
                    event,
                    entity_id=f"industry:{self._slug(industry)}",
                    entity_type=EntityType.INDUSTRY,
                    display_name=industry,
                    symbol=None,
                    relationship=MappingRelationship.INDUSTRY_MEMBERSHIP,
                    source=f"security-master:{record.source}",
                    confidence=1.0,
                    freshness=mapping_freshness,
                    version=f"security-master-v{getattr(record, 'metadata_version', 1)}",
                )
                self._append_mapping(mapped, event, mappings, evidence)
            for index in tuple(getattr(record, "index_memberships", ()) or ()):
                mapped = self._mapping(
                    event,
                    entity_id=f"index:{self._slug(str(index))}",
                    entity_type=EntityType.INDEX,
                    display_name=str(index),
                    symbol=None,
                    relationship=MappingRelationship.BENCHMARK_RELATIONSHIP,
                    source=f"security-master:{record.source}",
                    confidence=1.0,
                    freshness=mapping_freshness,
                    version=f"security-master-v{getattr(record, 'metadata_version', 1)}",
                )
                self._append_mapping(mapped, event, mappings, evidence)
            for definition, members in theme_rows:
                member = next(
                    (candidate for candidate in members if str(candidate.ticker).upper() == symbol and bool(candidate.active)),
                    None,
                )
                if member is None:
                    continue
                theme_freshness = self._theme_freshness(definition, now=now)
                mapped = self._mapping(
                    event,
                    entity_id=str(definition.theme_id),
                    entity_type=EntityType.THEME,
                    display_name=str(definition.display_name),
                    symbol=None,
                    relationship=MappingRelationship.THEME_MEMBERSHIP,
                    source=f"theme-registry:{member.membership_source}",
                    confidence=1.0,
                    freshness=theme_freshness,
                    version=f"{definition.theme_id}:{definition.version}",
                )
                self._append_mapping(mapped, event, mappings, evidence)
            if symbol in watchlist:
                mapped = self._mapping(
                    event,
                    entity_id=f"watchlist:{symbol}",
                    entity_type=EntityType.WATCHLIST,
                    display_name=f"Watchlist overlap: {symbol}",
                    symbol=symbol,
                    relationship=MappingRelationship.WATCHLIST_OVERLAP,
                    source="explicit-query-watchlist",
                    confidence=1.0,
                    freshness=event.freshness,
                    version="watchlist-overlap-v1",
                )
                self._append_mapping(mapped, event, mappings, evidence)

        deduped = self.evidence_engine.deduplicate(
            mappings,
            identity=lambda item: f"{item.entity_type.value}:{item.entity_id}:{item.relationship.value}",
            fingerprint=lambda item: item.model_dump(mode="json"),
        )
        allowed_evidence = {mapping.evidence_id for mapping in deduped.items}
        return NewsEntityMappingResult(
            mappings=deduped.items,
            evidence=tuple(item for item in evidence if item.evidence_id in allowed_evidence),
            rejected_candidates=tuple(dict.fromkeys(rejected)),
        )

    def _mapping(
        self,
        event: NewsEventRecord,
        *,
        entity_id: str,
        entity_type: EntityType,
        display_name: str,
        symbol: str | None,
        relationship: MappingRelationship,
        source: str,
        confidence: float,
        freshness: NewsFreshness,
        version: str,
    ) -> EntityMapping:
        evidence_id = f"news-map-{self._digest(event.event_id + '|' + entity_id + '|' + relationship.value)}"
        return EntityMapping(
            entity_id=entity_id,
            entity_type=entity_type,
            display_name=display_name,
            symbol=symbol,
            relationship=relationship,
            mapping_source=source,
            confidence=confidence,
            evidence_id=evidence_id,
            freshness=freshness,
            mapping_version=version,
        )

    @staticmethod
    def _append_mapping(
        mapping: EntityMapping,
        event: NewsEventRecord,
        mappings: list[EntityMapping],
        evidence: list[NewsEvidenceRecord],
    ) -> None:
        mappings.append(mapping)
        evidence.append(
            NewsEvidenceRecord(
                evidence_id=mapping.evidence_id,
                source_id=f"mapping-source-{NewsEntityMappingEngine._digest(mapping.mapping_source)}",
                event_id=event.event_id,
                kind=EvidenceKind.ENTITY_MAPPING,
                statement=(
                    f"{mapping.display_name} has the configured relationship "
                    f"{mapping.relationship.value}."
                ),
                interpretation_class=InterpretationClass.OBSERVED_FACT,
                entity_ids=(mapping.entity_id,),
                observed_at=mapping.freshness.observed_at,
                market_date=mapping.freshness.market_date,
                source_quality=SourceQuality.PRIMARY,
            )
        )

    def _mapping_freshness(self, record: Any, *, now: datetime) -> NewsFreshness:
        timestamp = (
            getattr(record, "verified_at", None)
            or getattr(record, "source_timestamp", None)
            or getattr(record, "effective_from", None)
        )
        return self._freshness(
            source_state="cached",
            timestamp=timestamp,
            provider="security-master",
            now=now,
        )

    def _theme_freshness(self, definition: Any, *, now: datetime) -> NewsFreshness:
        timestamp = (
            getattr(definition, "reviewed_at", None)
            or getattr(definition, "verification_date", None)
            or getattr(definition, "effective_from", None)
        )
        return self._freshness(
            source_state="cached",
            timestamp=timestamp,
            provider="theme-registry",
            now=now,
        )

    def _freshness(
        self,
        *,
        source_state: str,
        timestamp: str | None,
        provider: str,
        now: datetime,
    ) -> NewsFreshness:
        observed = self.freshness_engine.parse_datetime(timestamp)
        result = self.freshness_engine.evaluate(
            FreshnessAvailabilityInput(
                source_state=source_state,
                generated_at=observed.isoformat() if observed else None,
                observed_at=observed.isoformat() if observed else None,
                market_date=observed.date().isoformat() if observed else None,
                stale_after_seconds=31_536_000,
                completeness=1,
                provider=provider,
                now=now,
            )
        )
        return NewsFreshness(
            state=NewsFreshnessState(result.state),
            availability=NewsAvailability(result.availability),
            market_date=observed.date() if observed else None,
            generated_at=observed,
            observed_at=observed,
            age_seconds=result.age_seconds,
            completeness=result.completeness,
            provider=provider,
            confidence_cap_recommendation=result.confidence_cap_recommendation,
            warnings=result.warnings,
            engine_version=result.engine_version,
        )

    def _safe_themes(self) -> list[tuple[Any, list[Any]]]:
        try:
            return self.theme_loader()
        except Exception:
            return []

    @staticmethod
    def _project_security_resolver(symbol: str) -> Any | None:
        from app.securities.service import get_security_master_service

        return get_security_master_service().storage.security(symbol)

    @staticmethod
    def _project_theme_loader() -> list[tuple[Any, list[Any]]]:
        from app.themes.service import ThemeDefinitionService

        return ThemeDefinitionService().active()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

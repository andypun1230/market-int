from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.securities.registry import SECTOR_TAXONOMY, canonical_sector_id
from app.securities.service import get_security_master_service
from app.services.report import get_latest_daily_report
from app.theme_snapshots.service import get_theme_snapshot_service


INDEX_SYMBOLS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "DIA": "Dow Jones Industrial Average",
}
FOLLOW_UP_REFERENCES = {"it", "this", "that", "this stock", "that stock", "this theme", "that theme"}
NON_SECURITY_TOKENS = {
    "I", "AI", "API", "APP", "ATR", "CPI", "EMA", "ETF", "GDP", "LLM",
    "MACD", "PCE", "PMI", "RSI", "SEC", "SMA", "US", "USA", "USD", "VIX", "YTD",
}


@dataclass(frozen=True)
class ResolvedEntity:
    entity_type: str
    entity_id: str
    display_name: str
    symbol: str | None = None
    confidence: float = 1.0
    source: str = "registry"


@dataclass
class EntityResolution:
    entities: list[ResolvedEntity] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)
    used_conversation_context: bool = False


class CopilotEntityResolver:
    """Resolve only entities backed by application registries or context IDs."""

    def resolve(
        self,
        message: str,
        *,
        screen_context: dict[str, Any] | None = None,
        active_entities: Iterable[ResolvedEntity | dict[str, Any]] = (),
    ) -> EntityResolution:
        resolution = EntityResolution()
        records = self._security_records()
        lowered = message.casefold()

        symbols = self._symbol_mentions(message, records)
        for symbol in symbols:
            if symbol in INDEX_SYMBOLS:
                self._append(resolution, ResolvedEntity("index", symbol, INDEX_SYMBOLS[symbol], symbol=symbol))
                continue
            record = records.get(symbol)
            if record:
                self._append(
                    resolution,
                    ResolvedEntity(
                        "stock",
                        symbol,
                        str(record.get("company_name") or symbol),
                        symbol=symbol,
                        source=str(record.get("source") or "security_master"),
                    ),
                )

        self._resolve_company_names(lowered, records, resolution)
        self._resolve_sectors(lowered, resolution)
        self._resolve_themes(lowered, resolution)
        self._resolve_report_sections(lowered, resolution)

        # Uppercase ticker-like strings that are not registered are explicit
        # unresolved entities.  Ordinary prose is never treated as a ticker.
        for raw_token in re.findall(r"(?<![A-Za-z0-9])\$?([A-Z][A-Z0-9.\-]{0,11})(?![A-Za-z0-9])", message):
            token = self._canonical_symbol_token(raw_token)
            if token not in records and token not in INDEX_SYMBOLS and len(token) <= 5 and token not in NON_SECURITY_TOKENS:
                resolution.unresolved.append(token)
        resolution.unresolved = list(dict.fromkeys(resolution.unresolved))

        # An explicitly named entity takes precedence over the current screen.
        # Screen context is a fallback for references such as "this stock",
        # not an implicit second comparison target.
        if (not resolution.entities and not resolution.unresolved) or self._is_follow_up_reference(lowered):
            self._resolve_screen_hints(screen_context or {}, records, resolution)

        if not resolution.entities and self._is_follow_up_reference(lowered):
            for value in active_entities:
                entity = self._coerce_entity(value)
                if entity:
                    self._append(resolution, entity)
            resolution.used_conversation_context = bool(resolution.entities)

        return resolution

    def _security_records(self) -> dict[str, dict[str, Any]]:
        storage = get_security_master_service().storage
        records: dict[str, dict[str, Any]] = {}
        universe = storage.get_active_universe("sp100")
        if universe:
            for member in storage.members(universe.universe_id):
                record = storage.security(member.ticker)
                if record:
                    records[record.ticker.upper()] = record.model_dump()

        # Report and reviewed Theme universes include research securities that
        # may sit outside the active breadth universe.
        report = get_latest_daily_report()
        if report and report.report_document:
            for item in report.report_document.get("securities") or []:
                if not isinstance(item, dict):
                    continue
                symbol = str(item.get("symbol") or "").upper()
                if symbol:
                    stored = storage.security(symbol)
                    records.setdefault(symbol, stored.model_dump() if stored else {"ticker": symbol, "company_name": symbol, "source": "report"})
        theme = get_theme_snapshot_service().latest()
        if theme:
            for row in theme.rows:
                for member in row.get("members") or []:
                    if not isinstance(member, dict):
                        continue
                    symbol = str(member.get("ticker") or member.get("symbol") or "").upper()
                    if symbol:
                        stored = storage.security(symbol)
                        records.setdefault(symbol, stored.model_dump() if stored else {"ticker": symbol, "company_name": symbol, "source": "theme_snapshot"})
        return records

    @staticmethod
    def _symbol_mentions(message: str, records: dict[str, dict[str, Any]]) -> list[str]:
        found: list[str] = []
        explicit = re.findall(r"\$([A-Za-z][A-Za-z0-9.\-]{0,11})", message)
        uppercase = re.findall(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9.\-]{0,11})(?![A-Za-z0-9])", message)
        contextual_tokens = re.findall(
            r"\b(?:ticker|symbol|stock)\s+\$?([A-Za-z][A-Za-z0-9.\-]{0,11})\b",
            message,
            flags=re.IGNORECASE,
        )
        contextual_tokens.extend(
            re.findall(
                r"\b([A-Za-z][A-Za-z0-9.\-]{1,11})\s+(?:stock|shares)\b",
                message,
                flags=re.IGNORECASE,
            )
        )
        for token in [*explicit, *uppercase, *contextual_tokens]:
            symbol = CopilotEntityResolver._canonical_symbol_token(token)
            if symbol in records or symbol in INDEX_SYMBOLS:
                found.append(symbol)
        return list(dict.fromkeys(found))

    @staticmethod
    def _canonical_symbol_token(value: str) -> str:
        # Regex tokenisation deliberately permits dots for symbols such as
        # BRK.B.  A sentence-ending full stop is punctuation, however, and
        # must not turn a valid ticker into a second unresolved entity.
        return str(value or "").strip().upper().rstrip(".-")

    @staticmethod
    def _resolve_company_names(lowered: str, records: dict[str, dict[str, Any]], resolution: EntityResolution) -> None:
        matches: dict[str, list[str]] = {}
        for symbol, record in records.items():
            name = str(record.get("company_name") or "").strip()
            normalized = re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
            if len(normalized) < 4:
                continue
            if normalized in re.sub(r"[^a-z0-9]+", " ", lowered):
                matches.setdefault(normalized, []).append(symbol)
        for name, symbols in matches.items():
            if len(symbols) > 1:
                resolution.ambiguous.append(name)
                continue
            symbol = symbols[0]
            record = records[symbol]
            CopilotEntityResolver._append(
                resolution,
                ResolvedEntity("stock", symbol, str(record.get("company_name") or symbol), symbol=symbol, confidence=0.95),
            )

    @staticmethod
    def _resolve_sectors(lowered: str, resolution: EntityResolution) -> None:
        normalized_message = lowered.replace("&", "and")
        for sector_id, display_name, etf, aliases in SECTOR_TAXONOMY:
            terms = {sector_id.replace("_", " "), display_name.casefold(), *(alias.casefold() for alias in aliases)}
            if any(re.search(rf"\b{re.escape(term)}\b", normalized_message) for term in terms if term):
                CopilotEntityResolver._append(
                    resolution,
                    ResolvedEntity("sector", sector_id, display_name, symbol=etf, confidence=0.98),
                )

    @staticmethod
    def _resolve_themes(lowered: str, resolution: EntityResolution) -> None:
        snapshot = get_theme_snapshot_service().latest()
        if not snapshot:
            return
        for row in snapshot.rows:
            theme_id = str(row.get("theme_id") or "")
            display = str(row.get("display_name") or theme_id)
            terms = {theme_id.casefold(), theme_id.replace("_", " ").casefold(), display.casefold()}
            if any(term and re.search(rf"\b{re.escape(term)}\b", lowered) for term in terms):
                CopilotEntityResolver._append(
                    resolution,
                    ResolvedEntity("theme", theme_id, display, confidence=0.98, source="theme_snapshot"),
                )

    @staticmethod
    def _resolve_report_sections(lowered: str, resolution: EntityResolution) -> None:
        sections = {
            "research focus": "research-focus",
            "scenario": "scenarios",
            "watchlist intelligence": "watchlist",
        }
        for phrase, section_id in sections.items():
            if phrase in lowered:
                CopilotEntityResolver._append(
                    resolution,
                    ResolvedEntity("report_section", section_id, phrase.title(), confidence=0.95, source="route_registry"),
                )
        if "report" in lowered:
            CopilotEntityResolver._append(
                resolution,
                ResolvedEntity("report", "latest", "Latest Report", confidence=0.95, source="report_registry"),
            )

    @staticmethod
    def _resolve_screen_hints(context: dict[str, Any], records: dict[str, dict[str, Any]], resolution: EntityResolution) -> None:
        candidates: list[Any] = []
        for path in (("symbol",), ("ticker",), ("stock", "symbol"), ("stock", "ticker"), ("stock", "stock", "ticker")):
            value: Any = context
            for part in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(part)
            candidates.append(value)
        for value in candidates:
            symbol = str(value or "").upper()
            record = records.get(symbol)
            if record:
                CopilotEntityResolver._append(
                    resolution,
                    ResolvedEntity("stock", symbol, str(record.get("company_name") or symbol), symbol=symbol, confidence=1.0, source="screen_context"),
                )
        sector_context = context.get("sector")
        if isinstance(sector_context, dict):
            value = sector_context.get("sector_id") or sector_context.get("id") or sector_context.get("name")
            sector_id = canonical_sector_id(str(value or ""))
            if sector_id:
                for item in SECTOR_TAXONOMY:
                    if item[0] == sector_id:
                        CopilotEntityResolver._append(resolution, ResolvedEntity("sector", sector_id, item[1], symbol=item[2], source="screen_context"))

    @staticmethod
    def _is_follow_up_reference(lowered: str) -> bool:
        return lowered.strip() in {"why?", "why", "show me", "show me."} or any(reference in lowered for reference in FOLLOW_UP_REFERENCES)

    @staticmethod
    def _coerce_entity(value: ResolvedEntity | dict[str, Any]) -> ResolvedEntity | None:
        if isinstance(value, ResolvedEntity):
            return value
        if not isinstance(value, dict):
            return None
        entity_id = value.get("entity_id") or value.get("entityId") or value.get("id")
        entity_type = value.get("entity_type") or value.get("entityType") or value.get("type")
        if not entity_id or not entity_type:
            return None
        return ResolvedEntity(
            str(entity_type),
            str(entity_id),
            str(value.get("display_name") or value.get("displayName") or entity_id),
            symbol=value.get("symbol"),
            confidence=float(value.get("confidence") or 1.0),
            source=str(value.get("source") or "session"),
        )

    @staticmethod
    def _append(resolution: EntityResolution, entity: ResolvedEntity) -> None:
        key = (entity.entity_type, entity.entity_id)
        if key not in {(item.entity_type, item.entity_id) for item in resolution.entities}:
            resolution.entities.append(entity)

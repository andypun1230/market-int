from __future__ import annotations

from typing import Any, Iterable

from app.theme_snapshots.service import ThemeSnapshotService, get_theme_snapshot_service
from app.themes.analytics import ThemeAnalyticsEngine
from app.themes.launch import TAXONOMY_VERSION, ThemeRegistry, get_launch_theme_registry


class ThemeIntelligenceService:
    """Canonical read seam shared by API, screens, Reports and Copilot."""

    def __init__(
        self,
        registry: ThemeRegistry | None = None,
        snapshot_service: ThemeSnapshotService | None = None,
    ) -> None:
        self.registry = registry or get_launch_theme_registry()
        self.snapshots = snapshot_service or get_theme_snapshot_service()
        self.analytics = ThemeAnalyticsEngine(self.registry)

    def resolve_alias(self, value: str) -> str:
        return self.registry.resolve(value)

    def taxonomy(self, *, include_retired: bool = True) -> dict[str, Any]:
        definitions = self.registry.definitions if include_retired else self.registry.launch()
        issues = self.registry.validate()
        return {
            "taxonomy_version": TAXONOMY_VERSION,
            "effective_from": min(item.effective_from for item in definitions),
            "status": "available" if not issues else "partial",
            "source_state": "curated_reference",
            "test_or_mock_label": None,
            "items": [item.model_dump() for item in sorted(definitions, key=lambda item: item.id)],
            "validation_issues": issues,
            "statistics": self.registry.statistics(),
        }

    def list_themes(self, *, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        rows = self._merged_rows()
        selected = rows[max(0, offset):max(0, offset) + max(1, min(limit, 100))]
        snapshot = self.snapshots.latest()
        statuses = {row.get("status") for row in rows}
        overall = "available" if statuses == {"available"} else "partial" if statuses.intersection({"available", "partial"}) else "unavailable"
        return {
            "snapshot_id": snapshot.snapshot_id if snapshot else f"theme-taxonomy-{TAXONOMY_VERSION}",
            "taxonomy_version": TAXONOMY_VERSION,
            "as_of": snapshot.generated_at if snapshot else None,
            "market_date": snapshot.market_date if snapshot else None,
            "status": overall,
            "source_state": snapshot.source_state if snapshot else "unavailable",
            "freshness": {"state": snapshot.source_state if snapshot else "unavailable", "availability": overall},
            "confidence": "limited" if overall != "available" else "moderate",
            "missing_data": [row["theme_id"] for row in rows if row.get("status") != "available"],
            "items": selected,
            "rows": selected,
            "rankings": [row["theme_id"] for row in rows if row.get("rank") is not None],
            "pagination": {"offset": max(0, offset), "limit": max(1, min(limit, 100)), "total": len(rows)},
            "warnings": ["Themes without a governed market snapshot remain explicitly unavailable; taxonomy membership is not market evidence."],
            "test_or_mock_label": "HERMETIC TEST DATA — NOT LIVE" if snapshot and snapshot.source_state == "test" else None,
        }

    def ranked_themes(self, *, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        payload = self.list_themes(limit=100)
        rows = [item for item in payload["items"] if item.get("rank") is not None]
        if status:
            rows = [item for item in rows if item.get("leadership_state", "").casefold() == status.casefold()]
        rows.sort(key=lambda item: (int(item.get("rank") or 10_000), item["theme_id"]))
        payload["items"] = rows[:max(1, min(limit, 100))]
        payload["rows"] = payload["items"]
        payload["pagination"] = {"offset": 0, "limit": max(1, min(limit, 100)), "total": len(rows)}
        return payload

    def definition(self, theme_id: str) -> dict[str, Any] | None:
        definition = self.registry.definition(theme_id)
        return definition.model_dump() if definition else None

    def current(self, theme_id: str) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None:
            return self._unavailable(theme_id, "unknown_theme_id")
        if definition.status == "retired":
            return self._unavailable(definition.id, "retired_theme")
        row = next((item for item in self._merged_rows() if item["theme_id"] == definition.id), None)
        if row is None:
            return self._unavailable(definition.id, "theme_snapshot_unavailable")
        return {
            "taxonomy_version": TAXONOMY_VERSION,
            "requested_theme_id": theme_id,
            "canonical_theme_id": definition.id,
            "status": row["status"],
            "source_state": row.get("source_state", "unavailable"),
            "theme": row,
            "definition": definition.model_dump(),
            "missing_data": row.get("missing_data", []),
            "confidence": row.get("confidence", "limited"),
            "test_or_mock_label": row.get("test_or_mock_label"),
        }

    def constituents(self, theme_id: str, *, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None:
            return self._unavailable(theme_id, "unknown_theme_id")
        mappings = [item.model_dump() for item in self.registry.constituents(definition.id)]
        current = self.current(definition.id).get("theme") or {}
        analytics = {item.get("symbol") or item.get("ticker"): item for item in current.get("constituents", current.get("members", [])) if isinstance(item, dict)}
        rows = []
        for mapping in mappings:
            metric = analytics.get(mapping["symbol"], {})
            rows.append({**mapping, "analytics": metric, "availability": metric.get("availability", "unavailable")})
        rows.sort(key=lambda item: ({"core": 0, "significant": 1, "adjacent": 2, "experimental": 3}[item["exposure"]], item["symbol"]))
        return {
            "theme_id": definition.id,
            "taxonomy_version": TAXONOMY_VERSION,
            "status": current.get("status", "unavailable"),
            "source_state": current.get("source_state", "unavailable"),
            "items": rows[offset:offset + max(1, min(limit, 100))],
            "pagination": {"offset": offset, "limit": max(1, min(limit, 100)), "total": len(rows)},
        }

    def mappings_for_symbol(self, symbol: str) -> dict[str, Any]:
        rows = []
        for mapping in self.registry.themes_for_symbol(symbol):
            definition = self.registry.definition(mapping.theme_id)
            rows.append({**mapping.model_dump(), "theme_name": definition.name if definition else mapping.theme_id})
        return {
            "symbol": symbol.strip().upper(),
            "taxonomy_version": TAXONOMY_VERSION,
            "status": "available" if rows else "unavailable",
            "source_state": "curated_reference" if rows else "unavailable",
            "primary": rows[0] if rows else None,
            "secondary": rows[1:] if rows else [],
            "items": rows,
            "missing_data": [] if rows else ["canonical_theme_mapping"],
        }

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        needle = query.strip().casefold()
        rows: list[dict[str, Any]] = []
        if needle:
            for definition in self.registry.launch():
                haystack = (definition.id, definition.name, definition.short_name, *definition.aliases)
                if any(needle in value.casefold() for value in haystack):
                    rows.append({"id": definition.id, "name": definition.name, "type": "theme", "aliases": list(definition.aliases), "taxonomy_version": TAXONOMY_VERSION})
        rows.sort(key=lambda item: (item["name"].casefold() != needle, item["name"]))
        return {"query": query, "taxonomy_version": TAXONOMY_VERSION, "status": "available", "items": rows[:max(1, min(limit, 50))]}

    def history(self, theme_id: str, *, days: int = 90) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None:
            return self._unavailable(theme_id, "unknown_theme_id")
        rows: list[dict[str, Any]] = []
        for snapshot in self.snapshots.history(days):
            items = snapshot.get("rows") or snapshot.get("items") or []
            match = next((item for item in items if self._canonical_legacy(item.get("theme_id")) == definition.id), None)
            if match:
                rows.append({"snapshot_id": snapshot.get("snapshot_id"), "market_date": snapshot.get("market_date"), "theme": match})
        return {"theme_id": definition.id, "taxonomy_version": TAXONOMY_VERSION, "status": "available" if rows else "unavailable", "items": rows, "missing_data": [] if rows else ["published_theme_history"]}

    def changes(self, theme_id: str) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None:
            return self._unavailable(theme_id, "unknown_theme_id")
        current = self.current(definition.id).get("theme") or {}
        snapshot = self.snapshots.latest()
        rows = list(current.get("change_events") or [])
        if snapshot:
            rows.extend(item for item in snapshot.alerts if self._canonical_legacy(item.get("theme_id")) == definition.id)
        return {"theme_id": definition.id, "taxonomy_version": TAXONOMY_VERSION, "status": "available" if rows else "unavailable", "items": rows, "missing_data": [] if rows else ["material_change_events"]}

    def evidence(self, theme_id: str) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None:
            return self._unavailable(theme_id, "unknown_theme_id")
        current = self.current(definition.id).get("theme") or {}
        rows = list(current.get("evidence") or [])
        mapping_rows = [
            {"evidence_id": f"theme:{item.theme_id}:mapping:{item.symbol}", "kind": "mapping_provenance", **item.model_dump()}
            for item in self.registry.constituents(definition.id)
        ]
        rows.extend(mapping_rows)
        return {"theme_id": definition.id, "taxonomy_version": TAXONOMY_VERSION, "status": "available" if rows else "unavailable", "items": rows, "evidence_count": len(rows)}

    def saved_themes(self, values: Iterable[str]) -> dict[str, Any]:
        resolved: list[str] = []
        invalid: list[str] = []
        for value in values:
            try:
                canonical = self.resolve_alias(value)
                if canonical not in resolved:
                    resolved.append(canonical)
            except ValueError:
                invalid.append(value)
        rows = [self.current(item).get("theme") for item in resolved]
        return {"taxonomy_version": TAXONOMY_VERSION, "status": "partial" if invalid else "available", "items": [item for item in rows if item], "invalid_theme_ids": invalid}

    def material_changes(self, *, limit: int = 5) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in self._merged_rows():
            for event in row.get("change_events") or []:
                if event.get("material"):
                    events.append({**event, "theme_name": row.get("display_name")})
        snapshot = self.snapshots.latest()
        if snapshot:
            events.extend({**item, "material": True} for item in snapshot.alerts)
        return events[:max(1, min(limit, 20))]

    def available_rows(self) -> list[dict[str, Any]]:
        return [row for row in self._merged_rows() if row.get("status") in {"available", "partial"} and row.get("rank") is not None]

    def _merged_rows(self) -> list[dict[str, Any]]:
        snapshot = self.snapshots.latest()
        live_rows: dict[str, dict[str, Any]] = {}
        if snapshot:
            for row in snapshot.rows:
                canonical = self._canonical_legacy(row.get("theme_id"))
                if canonical:
                    live_rows[canonical] = dict(row)
        result: list[dict[str, Any]] = []
        for definition in self.registry.launch():
            mappings = self.registry.constituents(definition.id)
            source = live_rows.get(definition.id)
            definition_payload = definition.model_dump()
            if source:
                coverage = float(source.get("coverage_ratio") or 0)
                state = "available" if source.get("coverage_status") == "complete" else "partial" if source.get("coverage_status") == "partial" else "unavailable"
                row = {
                    **source,
                    "theme_id": definition.id,
                    "display_name": definition.name,
                    "taxonomy_version": TAXONOMY_VERSION,
                    "status": state,
                    "leadership_state": str(source.get("classification") or "neutral").casefold(),
                    "source_state": snapshot.source_state if snapshot else "unavailable",
                    "freshness": {"state": snapshot.source_state if snapshot else "unavailable", "market_date": snapshot.market_date if snapshot else None},
                    "confidence": (source.get("signal_confidence") or {}).get("label", "limited"),
                    "missing_data": [] if state == "available" else ["constituent_coverage"],
                    "definition": {**(source.get("definition") or {}), **definition_payload},
                    "aliases": list(definition.aliases),
                    "benchmark_symbols": list(definition.benchmark_symbols),
                    "core_constituent_count": sum(item.exposure == "core" for item in mappings),
                    "significant_constituent_count": sum(item.exposure == "significant" for item in mappings),
                    "adjacent_constituent_count": sum(item.exposure == "adjacent" for item in mappings),
                    "experimental_constituent_count": sum(item.exposure == "experimental" for item in mappings),
                    "test_or_mock_label": "HERMETIC TEST DATA — NOT LIVE" if snapshot and snapshot.source_state == "test" else None,
                }
            else:
                row = self._catalog_row(definition_payload, len(mappings))
            result.append(row)
        result.sort(key=lambda item: (item.get("rank") is None, int(item.get("rank") or 10_000), item["display_name"]))
        return result

    @staticmethod
    def _catalog_row(definition: dict[str, Any], count: int) -> dict[str, Any]:
        return {
            "theme_id": definition["id"], "display_name": definition["name"], "taxonomy_version": definition["taxonomy_version"],
            "status": "unavailable", "source_state": "unavailable", "freshness": {"state": "unavailable", "availability": "unavailable"},
            "constituent_count": count, "member_count": count, "covered_constituent_count": 0, "coverage_ratio": 0.0,
            "rank": None, "leadership_state": "neutral", "classification": "Unavailable", "composite_score": None,
            "relative_strength": {}, "breadth": {}, "momentum": {}, "persistence": {}, "concentration": {},
            "leaders": [], "improving_constituents": [], "weakening_constituents": [], "laggards": [], "change_events": [],
            "evidence": [], "contradictions": [], "missing_data": ["governed_market_history", "benchmark_history", "published_snapshot"],
            "confidence": "limited", "definition": definition, "aliases": list(definition["aliases"]), "benchmark_symbols": list(definition["benchmark_symbols"]),
            "members": [], "warnings": ["Canonical taxonomy and mappings are available, but governed market analytics have not been published."],
            "test_or_mock_label": None,
        }

    @staticmethod
    def _unavailable(theme_id: str, reason: str) -> dict[str, Any]:
        return {"theme_id": theme_id, "taxonomy_version": TAXONOMY_VERSION, "status": "unavailable", "source_state": "unavailable", "theme": None, "items": [], "missing_data": [reason], "confidence": "limited", "test_or_mock_label": None}

    def _canonical_legacy(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        definition = self.registry.definition(value)
        return definition.id if definition else None


_service: ThemeIntelligenceService | None = None


def get_theme_intelligence_service() -> ThemeIntelligenceService:
    global _service
    if _service is None:
        _service = ThemeIntelligenceService()
    return _service


def reset_theme_intelligence_service() -> None:
    global _service
    _service = None

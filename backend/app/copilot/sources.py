from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from app.breadth.models import BreadthSnapshot
from app.breadth.service import get_breadth_snapshot_service
from app.reports.document import ReportDocument
from app.sector_snapshots.models import SectorSnapshot
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.report import get_latest_daily_report
from app.snapshots.models import MarketSnapshot
from app.snapshots.service import get_market_snapshot_service
from app.stock_snapshots.models import StockAnalysisSnapshot
from app.stock_snapshots.service import get_stock_snapshot_service
from app.theme_snapshots.models import ThemeSnapshot
from app.theme_snapshots.service import get_theme_snapshot_service


TRUSTED_SOURCE_STATES = {
    "live",
    "delayed",
    "cached",
    "stale",
    "test",
    "partial",
    "mixed",
    "unavailable",
}


@dataclass(frozen=True)
class CopilotWatchlistMembership:
    """Identity-only membership boundary for watchlist reasoning.

    ``symbols=None`` means membership is unavailable, while an empty tuple is
    a confirmed empty list.  The distinction prevents a missing device-local
    hint from being presented as "you have no saved stocks".
    """

    symbols: tuple[str, ...] | None
    scope: str
    provider: str
    source_id: str
    limitation: str | None = None


class TrustedCopilotSources:
    """Read-only facade over durable intelligence.

    User-supplied context is deliberately absent from these methods.  Screen
    context may identify an entity or saved membership, but it can never
    supply prices, scores, levels, source state, or conclusions.
    """

    def market_snapshot(self) -> MarketSnapshot | None:
        return get_market_snapshot_service().get_latest_snapshot()

    def breadth_snapshot(self) -> BreadthSnapshot | None:
        return get_breadth_snapshot_service().latest()

    def sector_snapshot(self) -> SectorSnapshot | None:
        return get_sector_snapshot_service().latest()

    def theme_snapshot(self) -> ThemeSnapshot | None:
        return get_theme_snapshot_service().latest()

    def stock_snapshot(self, symbol: str) -> StockAnalysisSnapshot | None:
        # This is a durable read.  Unlike get_analysis_payload, it never starts
        # request-time provider work or a background refresh.
        return get_stock_snapshot_service().get_latest_snapshot(symbol)

    def watchlist_membership(self) -> CopilotWatchlistMembership:
        # Saved membership currently lives in device/browser-local frontend
        # storage.  The backend's static WATCHLIST_SYMBOLS and summary rows are
        # application defaults, not authenticated proof of a user's saves.
        return CopilotWatchlistMembership(
            symbols=None,
            scope="unavailable",
            provider="unavailable",
            source_id="saved-watchlist-membership-unavailable",
            limitation=(
                "Saved-list membership is device-local and was not supplied in this request; "
                "backend account-scoped membership is not available."
            ),
        )

    def latest_report_document(self) -> ReportDocument | None:
        report = get_latest_daily_report()
        if report is None or not report.report_document:
            return None
        try:
            return ReportDocument.model_validate(report.report_document)
        except Exception:
            return None


def normalize_source_state(value: Any, *, partial: bool = False, test: bool = False) -> str:
    if test:
        return "test"
    text = str(getattr(value, "value", value) or "unavailable").strip().lower()
    if partial and text not in {"test", "stale", "unavailable"}:
        return "partial"
    if text in TRUSTED_SOURCE_STATES:
        return text
    if text in {"current", "fresh", "official", "available"}:
        return "live"
    if text in {"mock", "generated_test_data"}:
        return "test"
    if text in {"initializing", "failed", "error"}:
        return "unavailable"
    return "unavailable"


def aggregate_source_states(states: Iterable[str]) -> str:
    values = {normalize_source_state(state) for state in states}
    if not values or values == {"unavailable"}:
        return "unavailable"
    unavailable = "unavailable" in values
    values.discard("unavailable")
    if "test" in values:
        result = "test" if values == {"test"} else "mixed"
        return "mixed" if unavailable else result
    if "stale" in values:
        result = "stale" if values == {"stale"} else "mixed"
        return "mixed" if unavailable else result
    if "partial" in values:
        return "partial" if values <= {"partial", "live", "cached", "delayed"} else "mixed"
    if unavailable:
        return "partial"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def is_expired(expires_at: str | None, *, now: datetime | None = None) -> bool:
    value = parse_datetime(expires_at)
    if value is None:
        return False
    return value <= (now or datetime.now(timezone.utc))


def freshness_state(
    *,
    source_state: Any,
    status: Any = None,
    expires_at: str | None = None,
    test_data: bool = False,
) -> str:
    normalized_status = str(getattr(status, "value", status) or "").lower()
    if test_data:
        return "test"
    if is_expired(expires_at) or normalized_status == "stale":
        return "stale"
    if normalized_status in {"partial", "initializing"}:
        return "partial" if normalized_status == "partial" else "unavailable"
    if normalized_status in {"unavailable", "failed"}:
        return "unavailable"
    return normalize_source_state(source_state)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def extract_saved_symbols(context: dict[str, Any] | None) -> list[str]:
    """Read membership hints only; never ingest client market values."""

    context = context or {}
    candidates: list[Any] = []
    # Hydrated top-level membership is authoritative, including an explicit
    # empty list.  Rich watchlist rows may contain backend default/enrichment
    # rows and must not re-add them as saved identities.
    for key in ("savedSymbols", "saved_symbols"):
        if key in context:
            value = context.get(key)
            candidates.extend(value if isinstance(value, list) else [])
            return _normalize_saved_symbols(candidates)
    for path in (
        ("watchlist", "symbols"),
        ("watchlist", "savedSymbols"),
        ("watchlist", "saved_symbols"),
        ("report", "researchPreferences", "saved_stocks"),
        ("report", "research_preferences", "saved_stocks"),
    ):
        value: Any = context
        for part in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, list):
            candidates.extend(value)
    watchlist = context.get("watchlist")
    if isinstance(watchlist, dict) and isinstance(watchlist.get("items"), list):
        for item in watchlist["items"]:
            if isinstance(item, dict):
                candidates.append(item.get("symbol") or item.get("ticker"))
    return _normalize_saved_symbols(candidates)


def has_explicit_saved_symbol_hint(context: dict[str, Any] | None) -> bool:
    """Return true when membership was supplied, even when it is empty."""

    context = context or {}
    if any(key in context for key in ("savedSymbols", "saved_symbols")):
        return True
    watchlist = context.get("watchlist")
    if isinstance(watchlist, dict) and any(
        key in watchlist for key in ("symbols", "savedSymbols", "saved_symbols", "items")
    ):
        return True
    report = context.get("report")
    if isinstance(report, dict):
        for key in ("researchPreferences", "research_preferences"):
            preferences = report.get(key)
            if isinstance(preferences, dict) and "saved_stocks" in preferences:
                return True
    return False


def _normalize_saved_symbols(candidates: Iterable[Any]) -> list[str]:
    symbols: list[str] = []
    for value in candidates:
        symbol = str(value or "").strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
        if len(symbols) >= 50:
            break
    return symbols

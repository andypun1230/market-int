from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.services.breadth import calculate_market_breadth
from app.services.decision_intelligence import build_decision_dashboard
from app.services.fear_greed import build_fear_greed_index
from app.services.leadership import build_leadership_dashboard
from app.services.market_data import build_index_snapshots_from_inputs
from app.services.market_health import calculate_market_health
from app.services.regime import build_market_regime, build_market_risk
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.sectors_summary import build_sectors_summary
from app.services.watchlist_summary import build_watchlist_summary
from app.services.market_data_repository import get_market_data_repository
from app.snapshots.input_bundle import MarketSnapshotInputBundle, fetch_input_bundle
from app.snapshots.input_planner import MarketSnapshotInputPlanner
from app.snapshots.models import InputCoverage, MarketSnapshot, SnapshotSection, now_iso
from app.snapshots.storage import MarketSnapshotStorage, unique_snapshot_id


class MarketSnapshotBuilder:
    def __init__(self, storage: MarketSnapshotStorage | None = None) -> None:
        self.storage = storage or MarketSnapshotStorage()
        self._build_lock = threading.Lock()

    def build_and_publish(self) -> MarketSnapshot | None:
        if not self._build_lock.acquire(blocking=False):
            return self.storage.get_latest_snapshot()
        started = time.perf_counter()
        build_started_at = now_iso()
        self.storage.set_state("last_build_started_at", build_started_at)
        try:
            snapshot = self._build_snapshot(started, build_started_at)
            if snapshot.status == "unavailable":
                self.storage.set_state("last_build_error", "minimum_core_not_met")
                return self.storage.get_latest_snapshot()
            self.storage.publish_snapshot(snapshot)
            return snapshot
        except Exception as exc:
            self.storage.set_state("last_build_error", f"{type(exc).__name__}: {exc}")
            return self.storage.get_latest_snapshot()
        finally:
            self._build_lock.release()

    def _build_snapshot(self, started: float, build_started_at: str) -> MarketSnapshot:
        input_started = time.perf_counter()
        plan = MarketSnapshotInputPlanner().build_plan()
        bundle = fetch_input_bundle(plan, get_market_data_repository())
        input_fetch_duration_ms = int((time.perf_counter() - input_started) * 1000)
        coverage = build_input_coverage(bundle)
        sections = self._build_sections(bundle)
        completed_sections = sum(1 for section in sections.values() if section.status == "complete")
        partial_sections = sum(1 for section in sections.values() if section.status == "partial")
        minimum_core_met = coverage.required_available >= int_env("MARKET_SNAPSHOT_MIN_CORE_HISTORIES", 2)
        status = "complete" if minimum_core_met and completed_sections == len(sections) else "partial" if minimum_core_met else "unavailable"
        warnings = []
        if partial_sections:
            warnings.append(f"{partial_sections} section(s) are partial.")
        if coverage.missing_required:
            warnings.append("Required input coverage is partial.")
        payload_for_id = {
            "input_hash": bundle.input_hash(),
            "sections": sorted(sections),
            "created_at": build_started_at,
        }
        completed_at = now_iso()
        published_at = completed_at
        created = datetime.now(timezone.utc)
        ttl = int_env("MARKET_SNAPSHOT_MAX_AGE_SECONDS", 600)
        stale = int_env("MARKET_SNAPSHOT_STALE_SECONDS", 3600)
        return MarketSnapshot(
            snapshot_id=unique_snapshot_id(payload_for_id),
            status=status,
            created_at=build_started_at,
            market_timestamp=latest_market_timestamp(bundle),
            published_at=published_at,
            expires_at=(created + timedelta(seconds=ttl)).isoformat(),
            stale_until=(created + timedelta(seconds=ttl + stale)).isoformat(),
            build_started_at=build_started_at,
            build_completed_at=completed_at,
            build_duration_ms=int((time.perf_counter() - started) * 1000),
            input_fetch_duration_ms=input_fetch_duration_ms,
            input_coverage=coverage,
            source_summary={
                "source_state": source_state_from_sections(sections),
                "input_hash": bundle.input_hash(),
                "breadth_snapshot_id": breadth_snapshot_id(sections),
            },
            freshness={
                "oldest_input_timestamp": oldest_market_timestamp(bundle),
                "newest_input_timestamp": latest_market_timestamp(bundle),
            },
            warnings=warnings,
            missing_dependencies=[*coverage.missing_required, *coverage.missing_optional],
            sections=sections,
            metadata={
                "planner": "canonical-v1",
                "algorithm_version": "market-snapshot-v1",
                "input_latency_ms": bundle.input_latency_ms,
            },
        )

    def _build_sections(self, bundle: MarketSnapshotInputBundle) -> dict[str, SnapshotSection]:
        builders: dict[str, Callable[[], Any]] = {
            "indexes": lambda: [item.model_dump() for item in build_index_snapshots_from_inputs(bundle.quotes, bundle.histories)],
            "regime": lambda: build_market_regime().model_dump(),
            "health": lambda: calculate_market_health().model_dump(),
            "breadth": lambda: calculate_market_breadth().model_dump(),
            "risk": lambda: build_market_risk().model_dump(),
            "risk_dashboard": lambda: build_risk_dashboard_v2().model_dump(),
            "fear_greed": lambda: build_fear_greed_index().model_dump(),
            "decision": lambda: build_decision_dashboard().model_dump(),
            "leadership": lambda: build_leadership_dashboard().model_dump(),
            "sectors_summary": build_sectors_summary,
            "watchlist_summary": build_watchlist_summary,
        }
        sections: dict[str, SnapshotSection] = {}
        for name, fn in builders.items():
            sections[name] = build_section(name, fn, bundle)
        sections["home"] = build_section("home", lambda: build_home_payload(sections), bundle)
        sections["core"] = build_section("core", lambda: build_core_payload(sections), bundle)
        return sections


def build_section(name: str, fn: Callable[[], Any], bundle: MarketSnapshotInputBundle) -> SnapshotSection:
    started = time.perf_counter()
    requested = max(1, bundle.requested_required + bundle.requested_optional)
    available = len(bundle.histories)
    try:
        payload = fn()
        status = "complete" if payload is not None else "unavailable"
        warnings: list[str] = []
    except Exception as exc:
        payload = None
        status = "unavailable"
        warnings = [f"{type(exc).__name__}: {exc}"]
    return SnapshotSection(
        status=status,
        calculated_at=now_iso(),
        source_state="live" if available else "unavailable",
        coverage_ratio=round(available / requested, 4) if requested else 0.0,
        dependencies_requested=requested,
        dependencies_available=available,
        dependencies_missing=list(bundle.unavailable_inputs),
        warnings=warnings,
        duration_ms=int((time.perf_counter() - started) * 1000),
        payload=payload,
    )


def build_core_payload(sections: dict[str, SnapshotSection]) -> dict[str, Any]:
    decision = as_dict(sections.get("decision"))
    playbook = decision.get("playbook") if isinstance(decision, dict) else None
    aggressiveness = decision.get("aggressiveness") if isinstance(decision, dict) else None
    trading_styles = decision.get("trading_styles") if isinstance(decision, dict) else None
    sectors = as_dict(sections.get("sectors_summary"))
    return {
        "indexes": as_payload(sections.get("indexes")) or [],
        "market_health": as_payload(sections.get("health")),
        "decision_summary": {
            "playbook": playbook,
            "aggressiveness": aggressiveness,
            "preferred_style": (trading_styles or {}).get("preferred_style") if isinstance(trading_styles, dict) else None,
            "main_risk": (playbook or {}).get("main_risk") if isinstance(playbook, dict) else None,
        },
        "breadth_summary": compact_breadth(as_payload(sections.get("breadth"))),
        "top_sector": first_item(sectors, "top_sectors"),
        "top_industry_group": first_item(sectors, "top_industry_groups"),
        "as_of": now_iso(),
        "overall_mode": "live",
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "snapshot",
        "is_stale": False,
        "generated_at": now_iso(),
    }


def build_home_payload(sections: dict[str, SnapshotSection]) -> dict[str, Any]:
    core = build_core_payload(sections)
    risk_dashboard = as_dict(sections.get("risk_dashboard"))
    risk_summary = {
        "score": risk_dashboard.get("score") if isinstance(risk_dashboard, dict) else None,
        "status": classify_risk_score(risk_dashboard.get("score") if isinstance(risk_dashboard, dict) else None),
        "top_contributors": (risk_dashboard.get("contributors") or [])[:3] if isinstance(risk_dashboard, dict) else [],
        "summary": risk_dashboard.get("summary") if isinstance(risk_dashboard, dict) else "Risk summary is updating.",
    }
    return {
        "core": core,
        "risk_summary": risk_summary,
        "watchlist_summary": as_payload(sections.get("watchlist_summary")) or {"items": []},
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "snapshot",
        "is_stale": False,
    }


def build_input_coverage(bundle: MarketSnapshotInputBundle) -> InputCoverage:
    requested = bundle.requested_required + bundle.requested_optional
    available = len(bundle.histories)
    missing_required = [
        symbol for symbol in ["SPY", "QQQ", "DIA", "IWM"]
        if symbol not in bundle.histories
    ]
    missing_optional = [
        key.removeprefix("history:")
        for key in bundle.unavailable_inputs
        if key.startswith("history:") and key.removeprefix("history:") not in missing_required
    ]
    return InputCoverage(
        required_requested=bundle.requested_required,
        required_available=bundle.required_available,
        optional_requested=bundle.requested_optional,
        optional_available=bundle.optional_available,
        coverage_ratio=round(available / requested, 4) if requested else 0.0,
        missing_required=missing_required,
        missing_optional=missing_optional,
    )


def as_payload(section: SnapshotSection | None) -> Any:
    return section.payload if section else None


def as_dict(section: SnapshotSection | None) -> dict[str, Any]:
    payload = as_payload(section)
    return payload if isinstance(payload, dict) else {}


def compact_breadth(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "breadth_score": payload.get("breadth_score"),
        "breadth_status": payload.get("breadth_status"),
        "percent_above_50ema": payload.get("percent_above_50ema"),
        "coverage_percent": payload.get("coverage_percent"),
        "overall_mode": payload.get("overall_mode"),
        "universe": payload.get("universe"),
        "snapshot_id": payload.get("snapshot_id"),
        "universe_version": payload.get("universe_version"),
        "market_date": payload.get("market_date"),
        "coverage_status": payload.get("coverage_status"),
        "trend": payload.get("trend"),
    }


def first_item(value: dict[str, Any], key: str) -> Any:
    items = value.get(key)
    if isinstance(items, list) and items:
        return items[0]
    return None


def latest_market_timestamp(bundle: MarketSnapshotInputBundle) -> str | None:
    values = [history.as_of for history in bundle.histories.values() if history.as_of]
    values.extend(quote.timestamp for quote in bundle.quotes.values() if quote.timestamp)
    return max(values, default=None)


def oldest_market_timestamp(bundle: MarketSnapshotInputBundle) -> str | None:
    values = [history.as_of for history in bundle.histories.values() if history.as_of]
    values.extend(quote.timestamp for quote in bundle.quotes.values() if quote.timestamp)
    return min(values, default=None)


def breadth_snapshot_id(sections: dict[str, SnapshotSection]) -> str | None:
    payload = sections.get("breadth").payload if sections.get("breadth") else None
    return payload.get("snapshot_id") if isinstance(payload, dict) else None


def source_state_from_sections(sections: dict[str, SnapshotSection]) -> str:
    states = {section.source_state for section in sections.values() if section.source_state}
    if states == {"live"}:
        return "live"
    if states:
        return "mixed"
    return "unavailable"


def classify_risk_score(score: int | None) -> str:
    if score is None:
        return "Unavailable"
    if score >= 70:
        return "Elevated"
    if score >= 45:
        return "Moderate"
    return "Low"


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.stock_snapshots.models import StockAnalysisSnapshot, now_iso


def snapshot_response(snapshot: StockAnalysisSnapshot) -> dict[str, Any]:
    payload = aggregate_payload(snapshot)
    return {
        "snapshot": snapshot.model_dump(),
        "analysis": payload,
        "status": snapshot_status_for_read(snapshot),
        "source_state": snapshot.source_state,
        "snapshot_id": snapshot.snapshot_id,
        "symbol": snapshot.symbol,
    }


def aggregate_payload(snapshot: StockAnalysisSnapshot) -> dict[str, Any]:
    chart = snapshot.section_payload("chart") or {}
    payload = {
        "symbol": snapshot.symbol,
        "supportResistance": snapshot.section_payload("support_resistance"),
        "trendline": snapshot.section_payload("trend"),
        "volumeAnalysis": snapshot.section_payload("volume"),
        "riskPlan": snapshot.section_payload("risk"),
        "multiTimeframe": snapshot.section_payload("multi_timeframe"),
        "multiTimeframeSignals": snapshot.section_payload("signals"),
        "patterns": snapshot.section_payload("pattern"),
        "relativeStrength": snapshot.section_payload("relative_strength"),
        "leadershipSignal": snapshot.section_payload("leadership"),
        "stockRating": snapshot.section_payload("rating"),
        "options": None,
        "liquidity": None,
        "chart": chart,
        "chartHistory": chart.get("history") if isinstance(chart, dict) else None,
        "partial": snapshot.status != "complete",
        "errors": section_errors(snapshot),
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_status": snapshot_status_for_read(snapshot),
        "snapshot_source_state": snapshot.source_state,
        "snapshot_data_mode": snapshot.data_mode,
        "snapshot_test_data": snapshot.test_data,
        "snapshot_mock_data": snapshot.mock_data,
        "snapshot_configuration_signature": snapshot.configuration_signature,
        "snapshot_history_provider": snapshot.history_provider,
        "snapshot_quote_provider": snapshot.quote_provider,
        "snapshot_schema_version": snapshot.snapshot_schema_version,
        "snapshot_age_seconds": snapshot_age_seconds(snapshot),
        "snapshot_refreshing": False,
        "compare_included": False,
    }
    return payload


def initializing_payload(symbol: str, *, refresh_started: bool) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "supportResistance": None,
        "trendline": None,
        "volumeAnalysis": None,
        "riskPlan": None,
        "multiTimeframe": None,
        "multiTimeframeSignals": None,
        "patterns": {"symbol": symbol.upper(), "patterns": []},
        "relativeStrength": None,
        "leadershipSignal": None,
        "stockRating": None,
        "options": None,
        "liquidity": None,
        "chart": None,
        "chartHistory": None,
        "partial": True,
        "errors": {},
        "snapshot_id": None,
        "snapshot_status": "initializing",
        "snapshot_source_state": "initializing",
        "snapshot_data_mode": "initializing",
        "snapshot_test_data": False,
        "snapshot_mock_data": False,
        "snapshot_age_seconds": None,
        "snapshot_refreshing": refresh_started,
        "compare_included": False,
    }


def section_errors(snapshot: StockAnalysisSnapshot) -> dict[str, str]:
    errors: dict[str, str] = {}
    for key, section in snapshot.sections.items():
        if section.status == "unavailable":
            errors[key] = section.warnings[0] if section.warnings else "Section unavailable."
    return errors


def snapshot_status_for_read(snapshot: StockAnalysisSnapshot) -> str:
    if is_expired(snapshot):
        return "stale"
    return snapshot.status


def is_expired(snapshot: StockAnalysisSnapshot) -> bool:
    try:
        expires = datetime.fromisoformat(snapshot.expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= datetime.now(timezone.utc)


def snapshot_age_seconds(snapshot: StockAnalysisSnapshot | None) -> float | None:
    if snapshot is None:
        return None
    try:
        published = datetime.fromisoformat(snapshot.published_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - published).total_seconds(), 2)


def status_payload(snapshot: StockAnalysisSnapshot | None, *, refresh_in_progress: bool, enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "status": snapshot_status_for_read(snapshot) if snapshot else "initializing",
        "snapshot_id": snapshot.snapshot_id if snapshot else None,
        "symbol": snapshot.symbol if snapshot else None,
        "snapshot_age_seconds": snapshot_age_seconds(snapshot),
        "refresh_in_progress": refresh_in_progress,
        "checked_at": now_iso(),
    }

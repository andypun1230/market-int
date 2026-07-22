from datetime import datetime, timezone
from html import escape
from io import BytesIO
from hashlib import sha256
from math import isfinite
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.cache.persistent_cache import get_persistent_value, set_persistent_value
from app.models.market import (
    DailyMultiTimeframe,
    DailyReportResponse,
    DailyRiskPlans,
    DailyVolumeAnalysis,
    DashboardComparisonResponse,
    DecisionConfidenceResponse,
    DecisionDashboardResponse,
    FearGreedResponse,
    FollowThroughDay,
    IndustryRotationResponse,
    IndustryGroupResponse,
    InstitutionalBias,
    InstitutionalIntelligenceResponse,
    LeadershipResponse,
    MarketCapRotationResponse,
    MarketHealthResponse,
    ProbabilityResponse,
    RiskDashboardV2Response,
    SectorEtfResponse,
)
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.decision_confidence import calculate_decision_confidence
from app.services.decision_intelligence import build_decision_dashboard
from app.services.fear_greed import build_fear_greed_index
from app.services.institutional_activity import calculate_institutional_bias
from app.services.industry_groups import build_industry_groups
from app.services.industry_rotation import build_industry_rotation_dashboard
from app.services.institutional_intelligence import build_institutional_intelligence_dashboard
from app.services.leadership import build_leadership_dashboard
from app.services.candle_data import get_symbol_history
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_health import calculate_market_health
from app.services.macro_state import build_macro_state
from app.services.regime import build_market_regime
from app.services.breadth import calculate_market_breadth
from app.services.market_data import get_index_history, get_index_snapshots
from app.services.multi_timeframe import build_daily_multi_timeframe_summary
from app.services.probability_engine import build_probability_engine
from app.services.risk import build_daily_risk_summary
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.report_intelligence import build_report_intelligence, build_report_snapshot
from app.services.sector_dashboard import build_sector_dashboard
from app.services.sector_etfs import build_sector_etf_dashboard
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.support_resistance import calculate_support_resistance
from app.services.volume_analysis import build_volume_analysis
from app.services.watchlist_summary import build_watchlist_summary
from app.snapshots.service import get_market_snapshot_service
from app.services.theme_intelligence import build_theme_intelligence_context
from app.services.report_read_context import report_snapshot_read
from app.reports.storage import get_daily_report_storage
from app.reports.document_builder import build_report_document
from app.reports.pdf_v6 import generate_report_pdf_v6
from app.reports.pdf_v7 import generate_report_pdf_v7
from app.securities.service import get_security_master_service


REPORT_SCHEMA_VERSION = "daily-report-v23"
REPORT_PDF_FORMAT_VERSION = "daily-report-pdf-v7"


def build_daily_volume_analysis() -> DailyVolumeAnalysis:
    volume_response = build_volume_analysis()
    items = volume_response.items
    highest_relative_volume = max(
        items,
        key=lambda item: item.relative_volume if item.relative_volume is not None else 0,
    )
    best_volume_setup = max(items, key=lambda item: item.volume_quality_score)
    distribution_alerts = [
        f"{item.symbol}: {item.summary}" for item in items if item.distribution_volume
    ]

    if not distribution_alerts:
        distribution_alerts = ["No distribution volume alerts in the watchlist."]

    relative_volume_text = (
        f"{highest_relative_volume.symbol}: "
        f"{highest_relative_volume.relative_volume:.2f}x"
        if highest_relative_volume.relative_volume is not None
        else f"{highest_relative_volume.symbol}: N/A"
    )

    return DailyVolumeAnalysis(
        highest_relative_volume=relative_volume_text,
        best_volume_setup=(
            f"{best_volume_setup.symbol}: {best_volume_setup.volume_quality} "
            f"({best_volume_setup.status})"
        ),
        distribution_volume_alerts=distribution_alerts,
    )


def build_daily_risk_plans() -> DailyRiskPlans:
    return DailyRiskPlans(**build_daily_risk_summary())


def build_daily_multi_timeframe() -> DailyMultiTimeframe:
    return DailyMultiTimeframe(**build_daily_multi_timeframe_summary())


def build_daily_report(
    *,
    saved_stocks: list[str] | None = None,
    saved_sectors: list[str] | None = None,
    saved_themes: list[str] | None = None,
) -> DailyReportResponse:
    identity = current_report_identity(saved_stocks=saved_stocks, saved_sectors=saved_sectors, saved_themes=saved_themes)
    storage = get_daily_report_storage()
    persisted = storage.get_by_identity(identity["identity_key"])
    if persisted is not None:
        storage.mark_latest(
            persisted.report.report_id or "",
            persisted.report.generated_at or persisted.report.generated_time or "unknown",
        )
        return persisted.report
    value = get_or_compute(
        identity["cache_key"],
        get_service_ttl("SERVICE_CACHE_REPORT_TTL_SECONDS", 300),
        lambda: _build_daily_report_uncached(identity),
    )
    report = value if isinstance(value, DailyReportResponse) else DailyReportResponse.model_validate(value)
    return storage.save_if_absent(
        report,
        identity_key=identity["identity_key"],
        cache_key=identity["cache_key"],
        schema_version=REPORT_SCHEMA_VERSION,
    ).report


def get_daily_report_by_id(report_id: str) -> DailyReportResponse | None:
    stored = get_daily_report_storage().get(report_id)
    return stored.report if stored is not None else None


def get_latest_daily_report() -> DailyReportResponse | None:
    stored = get_daily_report_storage().latest()
    return stored.report if stored is not None else None


def get_daily_report_history(limit: int = 30) -> list[dict[str, Any]]:
    return get_daily_report_storage().history(limit)


def get_daily_report_pdf_bytes(report_id: str | None = None) -> tuple[DailyReportResponse, bytes]:
    storage = get_daily_report_storage()
    report = get_daily_report_by_id(report_id) if report_id else build_daily_report()
    if report is None:
        raise KeyError(f"Unknown report id: {report_id}")
    pdf = storage.get_pdf(report.report_id or "")
    if pdf is None:
        pdf = storage.save_pdf_if_absent(report.report_id or "", generate_daily_report_pdf(report).getvalue())
    return report, pdf


def latest_market_snapshot_id() -> str:
    try:
        snapshot = get_market_snapshot_service().get_latest_snapshot()
        return snapshot.snapshot_id if snapshot else "unavailable"
    except Exception:
        return "unavailable"


def latest_sector_snapshot_id() -> str:
    try:
        snapshot = get_sector_snapshot_service().latest()
        return snapshot.snapshot_id if snapshot else "unavailable"
    except Exception:
        return "unavailable"


def latest_breadth_snapshot_id() -> str:
    try:
        return calculate_market_breadth().snapshot_id or "unavailable"
    except Exception:
        return "unavailable"


def latest_theme_snapshot_id() -> str:
    return str(build_theme_intelligence_context().get("snapshot_id") or "unavailable")


def current_report_identity(
    *,
    saved_stocks: list[str] | None = None,
    saved_sectors: list[str] | None = None,
    saved_themes: list[str] | None = None,
) -> dict[str, Any]:
    personalization = normalize_research_preferences(saved_stocks, saved_sectors, saved_themes)
    snapshot_ids = {
        "market": latest_market_snapshot_id(),
        "breadth": latest_breadth_snapshot_id(),
        "sector": latest_sector_snapshot_id(),
        "theme": latest_theme_snapshot_id(),
    }
    cache_key = ":".join(
        [
            "report:daily",
            REPORT_SCHEMA_VERSION,
            REPORT_PDF_FORMAT_VERSION,
            "json",
            snapshot_ids["market"],
            snapshot_ids["breadth"],
            snapshot_ids["sector"],
            snapshot_ids["theme"],
            sha256(str(personalization).encode()).hexdigest()[:16],
        ]
    )
    return {
        "snapshot_ids": snapshot_ids,
        "cache_key": cache_key,
        "identity_key": sha256(cache_key.encode()).hexdigest(),
        "personalization": personalization,
    }


def report_id_for_identity(market_date: str, identity_key: str) -> str:
    return f"daily-{market_date}-{identity_key[:12]}"


def normalize_research_preferences(
    saved_stocks: list[str] | None,
    saved_sectors: list[str] | None,
    saved_themes: list[str] | None,
) -> dict[str, list[str]]:
    def normalized(values: list[str] | None, *, uppercase: bool, limit: int) -> list[str]:
        result = set()
        for value in values or []:
            text = str(value or "").strip()
            if not text:
                continue
            result.add(text.upper() if uppercase else text.lower().replace("&", "and").replace("-", "_").replace(" ", "_"))
        return sorted(result)[:limit]

    return {
        "saved_stocks": normalized(saved_stocks, uppercase=True, limit=50),
        "saved_sectors": normalized(saved_sectors, uppercase=False, limit=25),
        "saved_themes": normalized(saved_themes, uppercase=False, limit=25),
    }


def capture_daily_report_inputs(personalization: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Read existing report inputs without allowing report-time provider work."""
    with report_snapshot_read():
        inputs = {
            "institutional_activity": calculate_institutional_bias(),
            "volume_analysis": build_daily_volume_analysis(),
            "risk_plans": build_daily_risk_plans(),
            "multi_timeframe": build_daily_multi_timeframe(),
            "market_health": calculate_market_health(),
            "market_regime": build_market_regime(),
            "decision_dashboard": build_decision_dashboard(),
            "probabilities": build_probability_engine(),
            "leadership": build_leadership_dashboard(),
            "decision_confidence": calculate_decision_confidence(),
            "breadth": calculate_market_breadth(),
            "comparison": build_dashboard_comparison(),
            "industry_rotation": build_industry_rotation_dashboard(),
            "risk_dashboard": build_risk_dashboard_v2(),
            "institutional_intelligence": build_institutional_intelligence_dashboard(),
            "sector_etfs": build_sector_etf_dashboard(),
            "industry_groups": build_industry_groups(),
            "cap_rotation": build_market_cap_rotation(),
            "fear_greed": build_fear_greed_index(),
            "macro": build_macro_state(),
            "indexes": safe_build_index_snapshots(),
            "index_histories": safe_build_index_histories(),
            "index_ohlcv": safe_build_index_ohlcv(),
            "watchlist_summary": safe_build_watchlist_summary((personalization or {}).get("saved_stocks")),
            "sector_dashboard": safe_build_sector_dashboard(),
            "theme_intelligence": build_theme_intelligence_context(),
            "security_taxonomy": build_security_taxonomy(),
        }
    # The interactive narrative calls build_market_analysis(), which owns a
    # shared cache for Copilot and live screens. A report read must not seed
    # that cache with a deliberately no-fetch view, so its brief is derived
    # only from the frozen values captured above.
    inputs["ai_summary"] = build_captured_report_ai_summary(inputs)
    return inputs


def build_captured_report_ai_summary(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a report-local brief without invoking shared live analysis."""
    health = inputs["market_health"]
    regime = inputs["market_regime"]
    decision = inputs["decision_dashboard"]
    breadth = inputs["breadth"]
    risk_dashboard = inputs["risk_dashboard"]
    cap_rotation = inputs["cap_rotation"]
    sector_dashboard = inputs.get("sector_dashboard") or {}
    sectors = sector_dashboard.get("sectors") if isinstance(sector_dashboard, dict) else []
    leader = next(
        (
            str(item.get("name") or item.get("sector"))
            for item in (sectors or [])
            if isinstance(item, dict) and (item.get("name") or item.get("sector"))
        ),
        "the leading sector",
    )
    confidence = getattr(inputs["decision_confidence"], "score", None)
    playbook = decision.playbook
    health_score = getattr(health, "overall_score", "N/A")
    health_status = getattr(health, "status", "N/A")
    regime_status = getattr(regime, "status", "N/A")
    breadth_status = getattr(breadth, "breadth_status", "unavailable")
    percent_above_50ema = getattr(breadth, "percent_above_50ema", None)
    breadth_display = f"{percent_above_50ema:.1f}%" if isinstance(percent_above_50ema, (int, float)) else "N/A"
    risk_score = getattr(risk_dashboard, "score", "N/A")
    cap_leader = getattr(cap_rotation, "leader", "N/A")

    return {
        "type": "market_ai_summary",
        "headline": playbook.headline or "Stay selective with the current market evidence",
        "summary": (
            f"This immutable report captures a {regime_status} regime. Market health is {health_status} "
            f"at {health_score}/100, while breadth is {breadth_status} with {breadth_display} above the 50 EMA. "
            f"{leader} leads the durable sector snapshot, {cap_leader} leads cap rotation, and the risk dashboard "
            f"is {risk_score}/100."
        ),
        "confidence": confidence if isinstance(confidence, (int, float)) else 70,
        "generated_by": "captured_report_snapshot",
        "next_update": "Next Daily Report",
        "key_points": [
            f"Market health: {health_status} ({health_score}/100).",
            f"Breadth: {breadth_status} with {breadth_display} above the 50 EMA.",
            f"Current sector leader: {leader}.",
        ],
        "opportunities": [f"Follow confirmed leadership in {leader} while the playbook remains valid."],
        "risks": [playbook.main_risk or "Monitor the current risk dashboard and market breadth."],
        "what_to_watch": [
            f"Whether the regime remains {regime_status}.",
            f"Whether breadth holds near {breadth_display} above the 50 EMA.",
            f"Whether {leader} continues to lead the sector snapshot.",
        ],
        "disclaimer": "This is educational market analysis only and not financial advice.",
    }


def _build_daily_report_uncached(identity: dict[str, Any] | None = None) -> DailyReportResponse:
    identity = identity or current_report_identity()
    inputs = capture_daily_report_inputs(identity.get("personalization"))
    institutional_activity = inputs["institutional_activity"]
    volume_analysis = inputs["volume_analysis"]
    risk_plans = inputs["risk_plans"]
    multi_timeframe = inputs["multi_timeframe"]
    market_health = inputs["market_health"]
    market_regime = inputs["market_regime"]
    decision_dashboard = inputs["decision_dashboard"]
    probabilities = inputs["probabilities"]
    leadership = inputs["leadership"]
    decision_confidence = inputs["decision_confidence"]
    breadth = inputs["breadth"]
    comparison = inputs["comparison"]
    industry_rotation = inputs["industry_rotation"]
    risk_dashboard = inputs["risk_dashboard"]
    institutional_intelligence = inputs["institutional_intelligence"]
    sector_etfs = inputs["sector_etfs"]
    industry_groups = inputs["industry_groups"]
    cap_rotation = inputs["cap_rotation"]
    fear_greed = inputs["fear_greed"]
    macro = inputs["macro"]
    ai_summary = inputs["ai_summary"]
    indexes = inputs["indexes"]
    index_histories = inputs["index_histories"]
    index_ohlcv = inputs["index_ohlcv"]
    watchlist_summary = inputs["watchlist_summary"]
    with report_snapshot_read():
        stock_charts = safe_build_selected_stock_charts(watchlist_summary)
    sector_dashboard = inputs["sector_dashboard"]
    theme_intelligence = inputs["theme_intelligence"]
    security_taxonomy = inputs["security_taxonomy"]
    theme_report = build_theme_report_section(theme_intelligence)
    sector_names = [
        str(item.get("name") or item.get("sector") or "")
        for item in (sector_dashboard or {}).get("sectors", [])
        if isinstance(item, dict) and (item.get("name") or item.get("sector"))
    ]
    market_date = breadth.market_date or (sector_dashboard or {}).get("market_date") or datetime.now(timezone.utc).date().isoformat()
    leading_sector = sector_names[0] if sector_names else "Sector leadership"
    generated_at = datetime.now(timezone.utc).isoformat()
    report_id = report_id_for_identity(market_date, identity["identity_key"])
    base_report = DailyReportResponse(
        date=market_date,
        title="Daily Market Intelligence Briefing",
        executive_summary=(
            f"Market regime is {market_regime.status}. {leading_sector} is the current durable sector leader, "
            f"while breadth is {breadth.breadth_status or 'unavailable'} with "
            f"{breadth.percent_above_50ema:.1f}% above the 50 EMA. "
            + (
                f" {theme_intelligence['leaders'][0]['display_name']} leads the reviewed live ThemeSnapshot."
                if theme_intelligence.get("available") and theme_intelligence.get("leaders")
                else " Live Theme Intelligence is not published in this report."
            )
        ),
        market_regime=market_regime.status,
        key_drivers=[
            f"{leading_sector} is the current durable sector leader.",
            f"Breadth is {breadth.breadth_status or 'unavailable'} at {breadth.percent_above_50ema:.1f}% above the 50 EMA.",
        ],
        main_risks=[decision_dashboard.playbook.main_risk],
        sector_leaders=sector_names[:3],
        tomorrow_watch=list(risk_dashboard.upcoming_events),
        strategy_note=(
            "Prefer pullbacks in leading sectors. Avoid chasing extended breakouts."
        ),
        institutional_activity=institutional_activity,
        volume_analysis=volume_analysis,
        risk_plans=risk_plans,
        multi_timeframe=multi_timeframe,
        market_health=market_health,
        decision_dashboard=decision_dashboard,
        probabilities=probabilities,
        leadership=leadership,
        decision_confidence=decision_confidence,
        comparison=comparison,
        industry_rotation=industry_rotation,
        risk_dashboard=risk_dashboard,
        institutional_intelligence=institutional_intelligence,
        sector_etfs=sector_etfs,
        industry_groups=industry_groups,
        cap_rotation=cap_rotation,
        fear_greed=fear_greed,
        macro=macro,
        ai_summary=ai_summary,
        indexes=indexes,
        index_histories=index_histories,
        index_ohlcv=index_ohlcv,
        watchlist_summary=watchlist_summary,
        sector_dashboard=sector_dashboard,
        sector_snapshot_id=(sector_dashboard or {}).get("snapshot_id") if isinstance(sector_dashboard, dict) else None,
        theme_intelligence=theme_intelligence,
        theme_report=theme_report,
        stock_charts=stock_charts,
        economic_calendar=build_economic_calendar(risk_dashboard.upcoming_events),
        semantic_context=build_report_semantic_context(breadth, decision_confidence, industry_groups, macro, snapshot_ids=identity["snapshot_ids"]),
        report_id=report_id,
        market_date=market_date,
        generated_time=generated_at,
        generated_at=generated_at,
        report_schema_version=REPORT_SCHEMA_VERSION,
        report_cache_key=identity["cache_key"],
        report_pdf_format_version=REPORT_PDF_FORMAT_VERSION,
        research_preferences=identity.get("personalization") or {},
        security_taxonomy=security_taxonomy,
    )
    report_history = load_report_history()
    previous_snapshot = report_history[-1] if report_history else None
    current_snapshot = build_report_snapshot(base_report)
    # Report intelligence must reason from the same frozen Theme payload the
    # JSON and PDF expose; it never reads a live ThemeSnapshot after this point.
    current_snapshot["reportId"] = report_id
    current_snapshot["marketDate"] = market_date
    current_snapshot["generatedTime"] = generated_at
    current_snapshot["reportSchemaVersion"] = REPORT_SCHEMA_VERSION
    current_snapshot["reportCacheKey"] = identity["cache_key"]
    current_snapshot["snapshotIds"] = identity["snapshot_ids"]
    current_snapshot["themeRanking"] = list(theme_report.get("leadership") or [])
    intelligence = build_report_intelligence(previous_snapshot, current_snapshot, report_history)
    current_snapshot["conviction"] = intelligence["conviction"].get("score")
    current_snapshot["confidence"] = intelligence["confidence"].get("score")
    current_snapshot["historicalMetrics"] = {
        **current_snapshot.get("historicalMetrics", {}),
        "conviction": current_snapshot["conviction"],
        "confidence": current_snapshot["confidence"],
    }
    theme_report["report_generated_at"] = generated_at
    theme_report["report_schema_version"] = REPORT_SCHEMA_VERSION
    base_report.report_snapshot = current_snapshot
    base_report.report_changes = intelligence["changes"]
    base_report.signal_convergence = intelligence["convergence"]
    base_report.hidden_warnings = intelligence["hidden_warnings"]
    base_report.hidden_confirmations = intelligence["hidden_confirmations"]
    base_report.market_conviction = intelligence["conviction"]
    base_report.decision_checklist = intelligence["checklist"]
    base_report.recommendation_confidence = intelligence["confidence"]
    base_report.scenario_plan = intelligence["scenarios"]
    base_report.previous_playbook_review = intelligence["playbook_review"]
    base_report.market_evolution = intelligence["evolution"]
    base_report.signal_relationships = intelligence["relationships"]
    base_report.trade_off_analysis = intelligence["commentary"].get("tradeOff", {})
    base_report.report_commentary = intelligence["commentary"]
    base_report.report_narrative = intelligence["narrative"]
    report_document = build_report_document(base_report, previous_snapshot)
    base_report.report_document = report_document.model_dump(mode="json")
    current_focus = report_document.research_focus.subject if report_document.research_focus else None
    current_snapshot["researchFocus"] = current_focus
    current_snapshot["historicalMetrics"] = {
        **current_snapshot.get("historicalMetrics", {}),
        "researchFocus": current_focus,
    }
    save_report_history([*report_history, current_snapshot])
    return base_report


def build_report_semantic_context(
    breadth: object,
    decision_confidence: DecisionConfidenceResponse,
    industry_groups: IndustryGroupResponse | None = None,
    macro: dict[str, Any] | None = None,
    snapshot_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    sector_snapshot = get_sector_snapshot_service().latest()
    return {
        "advance_decline": {
            "raw_ratio": getattr(breadth, "advance_decline_ratio", None),
            "display": getattr(breadth, "advance_decline_ratio_display", None),
            "smoothed_ratio": getattr(breadth, "advance_decline_ratio_smoothed", None),
            "ratio_method": getattr(breadth, "ratio_method", None),
        },
        "coverage_dimensions": getattr(breadth, "coverage_dimensions", None) or {},
        "data_confidence": getattr(breadth, "data_confidence", None) or {},
        "signal_confidence": getattr(breadth, "signal_confidence", None) or {},
        "decision_confidence": decision_confidence.model_dump(),
        "theme_provenance": industry_groups.theme_provenance if industry_groups else {},
        "macro": macro or {},
        "snapshot_ids": snapshot_ids or {
            "market": latest_market_snapshot_id(),
            "breadth": getattr(breadth, "snapshot_id", None),
            "sector": sector_snapshot.snapshot_id if sector_snapshot else None,
            "theme": latest_theme_snapshot_id(),
        },
        "sector_breadth_representativeness": [
            {"sector": row.get("display_name"), "eligible_members": row.get("eligible_members"), "representativeness": row.get("breadth_representativeness"), "reason": row.get("representativeness_reason")}
            for row in (sector_snapshot.sectors if sector_snapshot else ())
        ],
    }


def build_theme_report_section(theme_intelligence: dict[str, Any]) -> dict[str, Any]:
    """Freeze ThemeSnapshot evidence into the report payload without recalculation."""
    available = bool(theme_intelligence.get("available"))
    base = {
        "available": available,
        "theme_snapshot_id": theme_intelligence.get("snapshot_id"),
        "market_date": theme_intelligence.get("market_date"),
        "generated_at": theme_intelligence.get("generated_at"),
        "active_theme_count": 0,
        "definition_versions": {},
        "pilot_scope": theme_intelligence.get("pilot_scope") or {},
        "leadership": [],
        "rotation": {
            "selected_interval": "1M",
            "items": [],
            "provenance": "Published ThemeSnapshot rotation series; no report-time calculation.",
        },
        "methodology": {
            "basket_method": "Daily-rebalanced equal-weight current reviewed baskets.",
            "historical_disclosure": theme_intelligence.get("historical_disclosure"),
            "ranking_disclosure": ((theme_intelligence.get("pilot_scope") or {}).get("rank_scope")),
        },
        "warnings": list(theme_intelligence.get("warnings") or []),
    }
    if not available:
        base["reason"] = theme_intelligence.get("reason") or "no_published_theme_snapshot"
        return base

    rows = [item for item in (theme_intelligence.get("items") or []) if isinstance(item, dict)]
    leaders: list[dict[str, Any]] = []
    rotations: list[dict[str, Any]] = []
    versions: dict[str, str] = {}
    for row in rows:
        theme_id = str(row.get("theme_id") or "")
        version = row.get("version")
        if theme_id and version:
            versions[theme_id] = str(version)
        selected_rotation = canonical_theme_rotation(row, "1M")
        leader = {
            "theme_id": theme_id,
            "display_name": row.get("display_name"),
            "rank": row.get("rank"),
            "classification": row.get("classification"),
            "absolute_composite_score": row.get("composite_score"),
            "score_semantics": row.get("score_semantics") or {},
            "performance": row.get("performance") or {},
            "relative_strength": row.get("relative_strength") or {},
            "breadth": row.get("breadth") or {},
            "coverage_ratio": row.get("coverage_ratio"),
            "participation": row.get("participation") or {},
            "concentration": row.get("concentration") or {},
            "signal_confidence": row.get("signal_confidence") or {},
            "data_confidence": row.get("data_confidence") or {},
            "representativeness": row.get("representativeness") or {},
            "definition_version": version,
            "parent_sector_labels": ((row.get("definition") or {}).get("parent_sector_labels") or []),
            "rotation": selected_rotation,
        }
        leaders.append(leader)
        rotations.append({
            "theme_id": theme_id,
            "display_name": row.get("display_name"),
            **selected_rotation,
        })
    base["active_theme_count"] = len(leaders)
    base["definition_versions"] = versions
    base["leadership"] = sorted(leaders, key=lambda item: int(item.get("rank") or 999))
    base["rotation"]["items"] = sorted(rotations, key=lambda item: int(item.get("rank") or 999))
    return base


def canonical_theme_rotation(row: dict[str, Any], interval: str) -> dict[str, Any]:
    series = row.get("rotation_series") if isinstance(row.get("rotation_series"), dict) else {}
    selected = series.get(interval) if isinstance(series.get(interval), dict) else {}
    current = selected.get("current_point") if isinstance(selected.get("current_point"), dict) else {}
    trail_points = [
        {
            "market_date": point.get("market_date"),
            "relative_strength": point.get("plotted_x"),
            "relative_momentum": point.get("plotted_y"),
            "raw_relative_strength": point.get("raw_rs"),
            "raw_relative_momentum": point.get("raw_momentum"),
            "quadrant": point.get("quadrant"),
            "source_provider": point.get("source_provider"),
            "source_series_ids": point.get("source_series_ids") or [],
            "is_synthetic": point.get("is_synthetic"),
        }
        for point in selected.get("trail_points") or []
        if isinstance(point, dict)
    ]
    return {
        "rank": row.get("rank"),
        "selected_interval": interval,
        "current": {
            "market_date": current.get("market_date"),
            "relative_strength": current.get("plotted_x"),
            "relative_momentum": current.get("plotted_y"),
            "raw_relative_strength": current.get("raw_rs"),
            "raw_relative_momentum": current.get("raw_momentum"),
            "quadrant": current.get("quadrant"),
            "source_provider": current.get("source_provider"),
            "source_series_ids": current.get("source_series_ids") or [],
            "is_synthetic": current.get("is_synthetic"),
        },
        "trail_points": trail_points,
        "trail_provenance": {
            "source_state": selected.get("source_state"),
            "data_mode": selected.get("data_mode"),
            "formula_version": selected.get("formula_version"),
            "normalization_version": selected.get("normalization_version"),
            "synthetic_point_count": selected.get("synthetic_point_count"),
        },
    }


def load_previous_report_snapshot() -> dict[str, Any] | None:
    history = load_report_history()
    return history[-1] if history else None


def load_report_history() -> list[dict[str, Any]]:
    cached = get_persistent_value("report:history", allow_stale=True)
    if cached and isinstance(cached.value, list):
        return [item for item in cached.value if isinstance(item, dict)][-10:]
    legacy = get_persistent_value("report:last-snapshot", allow_stale=True)
    if legacy and isinstance(legacy.value, dict):
        return [legacy.value]
    return []


def save_report_history(history: list[dict[str, Any]]) -> None:
    cleaned = [item for item in history if isinstance(item, dict)][-10:]
    if cleaned:
        save_previous_report_snapshot(cleaned[-1])
    set_persistent_value(
        "report:history",
        cleaned,
        ttl_seconds=60 * 60 * 24 * 90,
        stale_seconds=60 * 60 * 24 * 365,
        data_source="report",
        metadata={"purpose": "report evolution history"},
    )


def save_previous_report_snapshot(snapshot: dict[str, Any]) -> None:
    set_persistent_value(
        "report:last-snapshot",
        snapshot,
        ttl_seconds=60 * 60 * 24 * 30,
        stale_seconds=60 * 60 * 24 * 365,
        data_source="report",
        metadata={"purpose": "previous report comparison"},
    )


def safe_build_index_snapshots() -> list[Any]:
    try:
        return get_index_snapshots()
    except Exception:
        return []


def safe_build_index_histories() -> dict[str, list[float]]:
    histories: dict[str, list[float]] = {}
    for symbol in ["SPY", "QQQ", "IWM", "DJI"]:
        try:
            closes = get_index_history(symbol).closes
            if closes:
                histories[symbol] = closes
        except Exception:
            continue
    return histories


def safe_build_index_ohlcv() -> dict[str, dict[str, Any]]:
    """Freeze cached OHLCV without allowing a report read to initiate provider work."""
    histories: dict[str, dict[str, Any]] = {}
    for symbol in ["SPY", "QQQ", "IWM", "DIA"]:
        try:
            history, validation = get_symbol_history(symbol, days=450, minimum_candles=20)
            candles = [candle.model_dump(mode="json") for candle in history.candles]
            if candles:
                histories[symbol] = {
                    "symbol": symbol,
                    "provider": history.provider or history.source,
                    "source_state": history.source_state,
                    "as_of": history.as_of,
                    "quality_score": validation.get("quality_score"),
                    "candles": candles,
                }
        except Exception:
            continue
    return histories


def safe_build_watchlist_summary(symbols: list[str] | None = None) -> dict[str, Any]:
    try:
        return build_watchlist_summary(symbols)
    except Exception:
        return {"items": [], "summary": "Watchlist snapshot unavailable."}


def build_security_taxonomy() -> list[dict[str, Any]]:
    """Freeze validated sector/industry membership without provider traffic."""
    try:
        service = get_security_master_service()
        storage = service.storage
        universe = storage.get_active_universe("sp100")
        symbols = {member.ticker for member in storage.members(universe.universe_id)} if universe else set()
        theme_context = build_theme_intelligence_context()
        for row in theme_context.get("items") or []:
            symbols.update(str(item.get("ticker") or "").upper() for item in row.get("members") or [] if isinstance(item, dict))
        result = []
        for symbol in sorted(item for item in symbols if item):
            record = storage.security(symbol)
            if record is None:
                continue
            result.append({
                "security_id": record.security_id,
                "ticker": record.ticker,
                "company_name": record.company_name,
                "sector": record.sector,
                "sector_id": record.sector_id,
                "industry": record.industry,
                "source": record.source,
                "source_timestamp": record.source_timestamp,
                "verified_at": record.verified_at,
                "mapping_type": "validated_security_master_membership",
            })
        return result
    except Exception:
        return []


def safe_build_sector_dashboard() -> dict[str, Any] | None:
    try:
        return build_sector_dashboard()
    except Exception:
        return None


def safe_build_selected_stock_charts(watchlist_summary: dict[str, Any]) -> list[dict[str, Any]]:
    items = watchlist_summary.get("items") or []
    ranked = sorted(
        [item for item in items if isinstance(item, dict)],
        key=lambda item: (
            parse_number(item.get("overall_score")) or 0,
            parse_number(item.get("change_percent")) or 0,
        ),
        reverse=True,
    )
    charts: list[dict[str, Any]] = []
    for item in ranked[:3]:
        symbol = str(item.get("symbol") or item.get("ticker") or "").upper()
        if not symbol:
            continue
        try:
            history, validation = get_symbol_history(symbol, days=126, minimum_candles=40)
            closes = [candle.close for candle in history.candles if is_number(candle.close)]
            volumes = [candle.volume for candle in history.candles if is_number(candle.volume)]
            if len(closes) < 30:
                continue
            support_resistance = calculate_support_resistance(symbol)
            support = None
            if support_resistance.support_zones:
                support = support_resistance.support_zones[0].low
            resistance = None
            if support_resistance.resistance_zones:
                resistance = support_resistance.resistance_zones[0].high
            charts.append(
                {
                    "symbol": symbol,
                    "price_history": closes[-126:],
                    "volumes": volumes[-126:],
                    "support": support,
                    "resistance": resistance,
                    "breakout": support_resistance.breakout_level,
                    "setup": item.get("setup") or item.get("main_setup") or item.get("trend") or "Monitoring setup",
                    "reason": build_stock_chart_sentence(symbol, item, closes),
                    "source": history.source,
                    "quality_score": validation.get("quality_score"),
                }
            )
        except Exception:
            continue
    return charts


def build_stock_chart_sentence(symbol: str, item: dict[str, Any], closes: list[float]) -> str:
    setup = str(item.get("setup") or item.get("trend") or "current setup")
    if len(closes) >= 50:
        latest = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50
        if latest >= ma20 >= ma50:
            return f"{symbol} remains above rising short- and medium-term averages; monitor extension risk."
        if latest >= ma50:
            return f"{symbol} is holding above medium-term support, but short-term confirmation is still needed."
        return f"{symbol} is below key moving-average support, so risk control matters more than chasing."
    return f"{symbol} is classified as {setup}; monitor confirmation before acting."


def build_economic_calendar(upcoming_events: list[str]) -> list[dict[str, Any]]:
    impact_by_keyword = {
        "CPI": "High",
        "PPI": "Medium",
        "Fed": "High",
        "earnings": "Medium",
    }
    rows = []
    for index, event in enumerate(upcoming_events[:5]):
        impact = next((value for key, value in impact_by_keyword.items() if key.lower() in event.lower()), "Medium")
        rows.append(
            {
                "date": f"T+{index + 1}",
                "event": event,
                "impact": impact,
                "actual": "N/A",
                "forecast": "N/A",
                "previous": "N/A",
                "remark": "Monitor for market reaction.",
            }
        )
    return rows


def add_report_section(story: List[Any], heading: str, content: str, styles: Dict[str, Any]) -> None:
    story.append(Paragraph(heading, styles["section_heading"]))
    story.append(Paragraph(content, styles["body"]))
    story.append(Spacer(1, 0.16 * inch))


def add_report_list(story: List[Any], heading: str, items: List[str], styles: Dict[str, Any]) -> None:
    story.append(Paragraph(heading, styles["section_heading"]))
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["body"])) for item in items],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def format_follow_through_day(follow_through_day: FollowThroughDay) -> str:
    if not follow_through_day.triggered:
        return "Not triggered"

    details = [
        follow_through_day.index or "Index",
        follow_through_day.date or "date unavailable",
    ]

    if follow_through_day.gain_percent is not None:
        details.append(f"{follow_through_day.gain_percent:.2f}% gain")

    return "Triggered: " + " | ".join(details)


def add_institutional_activity_section(
    story: List[Any],
    institutional_activity: InstitutionalBias,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Institutional Activity", styles["section_heading"]))
    story.append(
        Paragraph(f"<b>Bias:</b> {institutional_activity.bias}", styles["body"])
    )
    story.append(
        Paragraph(f"<b>Summary:</b> {institutional_activity.summary}", styles["body"])
    )
    story.append(
        Paragraph(
            (
                f"<b>Distribution Days:</b> {institutional_activity.distribution_count}<br/>"
                f"<b>Accumulation Days:</b> {institutional_activity.accumulation_count}<br/>"
                f"<b>Stall Days:</b> {institutional_activity.stall_count}<br/>"
                f"<b>Churning Days:</b> {institutional_activity.churning_count}<br/>"
                f"<b>Follow-Through Day:</b> "
                f"{format_follow_through_day(institutional_activity.follow_through_day)}"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_volume_analysis_section(
    story: List[Any],
    volume_analysis: DailyVolumeAnalysis,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Volume Analysis", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Highest Relative Volume:</b> {volume_analysis.highest_relative_volume}<br/>"
                f"<b>Best Volume Setup:</b> {volume_analysis.best_volume_setup}"
            ),
            styles["body"],
        )
    )
    story.append(Paragraph("<b>Distribution Volume Alerts:</b>", styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(item, styles["body"]))
                for item in volume_analysis.distribution_volume_alerts
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_risk_plans_section(
    story: List[Any],
    risk_plans: DailyRiskPlans,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Risk Plans", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Best Risk/Reward Setup:</b> {risk_plans.best_risk_reward_setup}<br/>"
                f"<b>Highest Risk Stock:</b> {risk_plans.highest_risk_stock}<br/>"
                f"<b>Risk Summary:</b> {risk_plans.risk_summary}"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_multi_timeframe_section(
    story: List[Any],
    multi_timeframe: DailyMultiTimeframe,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Multi-Timeframe Alignment", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Strongest Alignment:</b> {multi_timeframe.strongest_alignment_stock}<br/>"
                f"<b>Weakest Alignment:</b> {multi_timeframe.weakest_alignment_stock}<br/>"
                f"<b>Summary:</b> {multi_timeframe.summary}"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_market_health_section(
    story: List[Any],
    market_health: MarketHealthResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Market Health", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Score:</b> {market_health.overall_score}<br/>"
                f"<b>Status:</b> {market_health.status}<br/>"
                f"<b>Data Mode:</b> {format_data_quality_mode(market_health)}<br/>"
                f"<b>Breadth Coverage:</b> {format_breadth_coverage(market_health)}<br/>"
                f"<b>Summary:</b> {market_health.summary}"
            ),
            styles["body"],
        )
    )
    story.append(Paragraph("<b>Improving Factors:</b>", styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(item, styles["body"]))
                for item in market_health.improving_factors
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Paragraph("<b>Weakening Factors:</b>", styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(item, styles["body"]))
                for item in market_health.weakening_factors
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_decision_intelligence_section(
    story: List[Any],
    decision_dashboard: DecisionDashboardResponse,
    probabilities: ProbabilityResponse,
    leadership: LeadershipResponse,
    decision_confidence: DecisionConfidenceResponse,
    comparison: DashboardComparisonResponse,
    industry_rotation: IndustryRotationResponse,
    risk_dashboard: RiskDashboardV2Response,
    styles: Dict[str, Any],
) -> None:
    playbook = decision_dashboard.playbook
    aggressiveness = decision_dashboard.aggressiveness
    checklist = decision_dashboard.checklist
    trading_styles = decision_dashboard.trading_styles

    story.append(Paragraph("Decision Intelligence", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Playbook:</b> {playbook.headline}<br/>"
                f"<b>Preferred Strategy:</b> {playbook.preferred_strategy}<br/>"
                f"<b>Aggressiveness:</b> {aggressiveness.status} "
                f"({aggressiveness.score}/100)<br/>"
                f"<b>Decision Confidence:</b> {decision_confidence.status} "
                f"({decision_confidence.score}/100)<br/>"
                f"<b>Top Probability:</b> {probabilities.items[0].strategy} "
                f"({probabilities.items[0].probability}%)<br/>"
                f"<b>Checklist:</b> {checklist.score}/{checklist.max_score} "
                f"({checklist.grade})<br/>"
                f"<b>Leadership:</b> {leadership.summary}<br/>"
                f"<b>Risk Score:</b> {risk_dashboard.score}/100<br/>"
                f"<b>Comparison:</b> {comparison.summary}<br/>"
                f"<b>Industry Rotation:</b> {industry_rotation.summary}<br/>"
                f"<b>Main Risk:</b> {playbook.main_risk}<br/>"
                f"<b>Preferred Style:</b> {trading_styles.preferred_style}"
            ),
            styles["body"],
        )
    )
    story.append(Paragraph("<b>Action Guidelines:</b>", styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(item, styles["body"]))
                for item in playbook.action_guidelines
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_institutional_intelligence_section(
    story: List[Any],
    institutional_intelligence: InstitutionalIntelligenceResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Institutional Intelligence", styles["section_heading"]))
    story.append(Paragraph(institutional_intelligence.summary, styles["body"]))
    story.append(
        Paragraph(
            (
                f"<b>Sentiment:</b> {institutional_intelligence.sentiment.status} "
                f"({institutional_intelligence.sentiment.score}/100)<br/>"
                f"<b>Money Flow:</b> {institutional_intelligence.money_flow.status} "
                f"({institutional_intelligence.money_flow.score}/100)<br/>"
                f"<b>Institutional:</b> {institutional_intelligence.institutional.status} "
                f"({institutional_intelligence.institutional.score}/100)<br/>"
                f"<b>Options:</b> {institutional_intelligence.options.status} "
                f"({institutional_intelligence.options.score}/100)<br/>"
                f"<b>Liquidity:</b> {institutional_intelligence.liquidity.status} "
                f"({institutional_intelligence.liquidity.score}/100)"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_sector_etfs_section(
    story: List[Any],
    sector_etfs: SectorEtfResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Sector ETF Dashboard", styles["section_heading"]))
    story.append(Paragraph(sector_etfs.summary, styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        (
                            f"{item.symbol} ({item.sector}): {item.status}, "
                            f"RS {item.relative_strength_score}, MTD {item.return_mtd:.1f}%, "
                            f"source {item.data_source or 'mock'}"
                        ),
                        styles["body"],
                    )
                )
                for item in sector_etfs.items[:5]
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def format_data_quality_mode(market_health: MarketHealthResponse) -> str:
    data_quality = market_health.data_quality or {}
    mode = data_quality.get("overall_mode", "mock")
    live_components = data_quality.get("live_components", [])
    fallback_components = data_quality.get("fallback_components", [])

    details = [str(mode).title()]
    if live_components:
        details.append(f"live: {', '.join(live_components)}")
    if fallback_components:
        details.append(f"fallback: {', '.join(fallback_components)}")

    return " | ".join(details)


def format_breadth_coverage(market_health: MarketHealthResponse) -> str:
    data_quality = market_health.data_quality or {}
    coverage = data_quality.get("breadth_coverage_percent")
    universe = data_quality.get("breadth_universe", "core")
    if isinstance(coverage, (int, float)):
        return f"{coverage:.1f}% ({universe} liquid-stock universe)"
    return f"N/A ({universe} liquid-stock universe)"


def add_industry_groups_section(
    story: List[Any],
    industry_groups: IndustryGroupResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Industry Group Leadership", styles["section_heading"]))
    story.append(Paragraph(industry_groups.summary, styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        (
                            f"{item.name} ({item.parent_sector}): {item.status}, "
                            f"RS {item.relative_strength_score}, MTD {item.return_mtd:.1f}%"
                        ),
                        styles["body"],
                    )
                )
                for item in industry_groups.items[:5]
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_cap_rotation_section(
    story: List[Any],
    cap_rotation: MarketCapRotationResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Market Cap Rotation", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Leader:</b> {cap_rotation.leader}<br/>"
                f"<b>Laggard:</b> {cap_rotation.laggard}<br/>"
                f"<b>Summary:</b> {cap_rotation.summary}"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_fear_greed_section(
    story: List[Any],
    fear_greed: FearGreedResponse,
    styles: Dict[str, Any],
) -> None:
    story.append(Paragraph("Fear & Greed Index", styles["section_heading"]))
    story.append(
        Paragraph(
            (
                f"<b>Score:</b> {fear_greed.score}<br/>"
                f"<b>Status:</b> {fear_greed.status}<br/>"
                f"<b>Summary:</b> {fear_greed.summary}"
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def add_ai_summary_section(
    story: List[Any],
    ai_summary: Dict[str, Any] | None,
    styles: Dict[str, Any],
) -> None:
    if not ai_summary:
        return

    story.append(Paragraph("Executive AI Brief", styles["section_heading"]))
    story.append(Paragraph(f"<b>{ai_summary.get('headline', 'Summary')}</b>", styles["body"]))
    story.append(
        Paragraph(
            (
                f"<b>Confidence:</b> {ai_summary.get('confidence', 'N/A')}%<br/>"
                f"<b>Generated By:</b> {ai_summary.get('generated_by', 'N/A')}<br/>"
                f"<b>Next Update:</b> {ai_summary.get('next_update', 'N/A')}"
            ),
            styles["body"],
        )
    )
    story.append(Paragraph(ai_summary.get("summary", "N/A"), styles["body"]))
    story.append(Paragraph("<b>What to Watch:</b>", styles["body"]))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(item, styles["body"]))
                for item in ai_summary.get("what_to_watch", [])
            ],
            bulletType="bullet",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.16 * inch))


REPORT_COLORS = {
    "ink": colors.HexColor("#0F172A"),
    "muted": colors.HexColor("#64748B"),
    "line": colors.HexColor("#CBD5E1"),
    "panel": colors.HexColor("#F8FAFC"),
    "panel_alt": colors.HexColor("#EFF6FF"),
    "green": colors.HexColor("#16A34A"),
    "red": colors.HexColor("#DC2626"),
    "orange": colors.HexColor("#F59E0B"),
    "blue": colors.HexColor("#2563EB"),
    "purple": colors.HexColor("#7C3AED"),
    "slate": colors.HexColor("#334155"),
}


class LineChartFlowable(Flowable):
    def __init__(
        self,
        series: list[dict[str, Any]],
        width: float,
        height: float,
        title: str = "",
        y_suffix: str = "",
        fixed_zero: bool = False,
    ):
        super().__init__()
        self.series = [
            {
                **item,
                "values": [float(value) for value in item.get("values", []) if is_number(value)],
            }
            for item in series
        ]
        self.width = width
        self.height = height
        self.title = title
        self.y_suffix = y_suffix
        self.fixed_zero = fixed_zero

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(REPORT_COLORS["line"])
        canvas.setFillColor(colors.white)
        canvas.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        values = [value for item in self.series for value in item["values"]]
        if not values:
            draw_unavailable(canvas, self.width, self.height, "Historical data unavailable.")
            canvas.restoreState()
            return

        left, right, bottom, top = 34, 12, 24, 30
        plot_w = self.width - left - right
        plot_h = self.height - bottom - top
        y_min = 0 if self.fixed_zero else min(values)
        y_max = 100 if self.fixed_zero else max(values)
        if y_max == y_min:
            y_max += 1
            y_min -= 1
        pad = 0 if self.fixed_zero else (y_max - y_min) * 0.08
        y_min -= pad
        y_max += pad

        if self.title:
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(10, self.height - 15, self.title)

        canvas.setFont("Helvetica", 6.5)
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        grid_values = [25, 50, 75] if self.fixed_zero else [y_min, (y_min + y_max) / 2, y_max]
        for grid in grid_values:
            y = bottom + ((grid - y_min) / (y_max - y_min)) * plot_h
            canvas.line(left, y, left + plot_w, y)
            canvas.setFillColor(REPORT_COLORS["muted"])
            label = f"{grid:.0f}{self.y_suffix}"
            canvas.drawRightString(left - 4, y - 2, label)

        for item in self.series:
            values = item["values"]
            if len(values) < 2:
                continue
            color = item.get("color", REPORT_COLORS["blue"])
            canvas.setStrokeColor(color)
            canvas.setLineWidth(1.4)
            points = []
            for index, value in enumerate(values):
                x = left + (index / (len(values) - 1)) * plot_w
                y = bottom + ((value - y_min) / (y_max - y_min)) * plot_h
                points.append((x, y))
            path = canvas.beginPath()
            path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]:
                path.lineTo(x, y)
            canvas.drawPath(path, stroke=1, fill=0)
            canvas.setFillColor(color)
            canvas.circle(points[-1][0], points[-1][1], 2.4, fill=1, stroke=0)

        canvas.setFont("Helvetica", 6.5)
        x = left
        step = min(82, max(48, (self.width - left - 12) / max(1, len(self.series))))
        for item in self.series:
            canvas.setFillColor(item.get("color", REPORT_COLORS["blue"]))
            canvas.circle(x, 10, 2, fill=1, stroke=0)
            canvas.setFillColor(REPORT_COLORS["muted"])
            canvas.drawString(x + 5, 7, str(item.get("label", ""))[:18])
            x += step
        canvas.restoreState()


class StockChartFlowable(Flowable):
    def __init__(self, item: dict[str, Any], width: float, height: float):
        super().__init__()
        self.item = item
        self.width = width
        self.height = height

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        values = [float(value) for value in self.item.get("price_history", []) if is_number(value)]
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(REPORT_COLORS["line"])
        canvas.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        if len(values) < 2:
            draw_unavailable(canvas, self.width, self.height, "Stock history unavailable.")
            canvas.restoreState()
            return

        left, right, bottom, top = 30, 10, 24, 18
        plot_w = self.width - left - right
        plot_h = self.height - bottom - top
        lines = [
            values,
            moving_average_series(values, 20),
            moving_average_series(values, 50),
        ]
        guide_values = [
            parse_number(self.item.get("support")),
            parse_number(self.item.get("resistance")),
            parse_number(self.item.get("breakout")),
        ]
        all_values = [value for series in lines for value in series] + [value for value in guide_values if value is not None]
        y_min = min(all_values)
        y_max = max(all_values)
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        pad = (y_max - y_min) * 0.08
        y_min -= pad
        y_max += pad

        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(REPORT_COLORS["ink"])
        canvas.drawString(10, self.height - 12, str(self.item.get("symbol", "Stock"))[:8])

        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        for grid in [y_min, (y_min + y_max) / 2, y_max]:
            y = bottom + ((grid - y_min) / (y_max - y_min)) * plot_h
            canvas.line(left, y, left + plot_w, y)
            canvas.setFillColor(REPORT_COLORS["muted"])
            canvas.setFont("Helvetica", 5.8)
            canvas.drawRightString(left - 3, y - 2, format_number(grid))

        for guide_index, (label, guide, color) in enumerate([
            ("Support", self.item.get("support"), REPORT_COLORS["green"]),
            ("Resist.", self.item.get("resistance"), REPORT_COLORS["orange"]),
            ("Breakout", self.item.get("breakout"), REPORT_COLORS["blue"]),
        ]):
            parsed = parse_number(guide)
            if parsed is None:
                continue
            y = bottom + ((parsed - y_min) / (y_max - y_min)) * plot_h
            canvas.setStrokeColor(color)
            canvas.setDash(2, 2)
            canvas.line(left, y, left + plot_w, y)
            canvas.setDash()
            canvas.setFillColor(color)
            canvas.setFont("Helvetica", 5.5)
            canvas.drawString(left + 2 + guide_index * 32, y + 2 + guide_index * 5, label)

        for series, color, width in [
            (values, REPORT_COLORS["green"], 1.5),
            (moving_average_series(values, 20), REPORT_COLORS["blue"], 0.9),
            (moving_average_series(values, 50), REPORT_COLORS["purple"], 0.9),
        ]:
            if len(series) < 2:
                continue
            points = []
            for index, value in enumerate(series):
                x = left + (index / (len(series) - 1)) * plot_w
                y = bottom + ((value - y_min) / (y_max - y_min)) * plot_h
                points.append((x, y))
            path = canvas.beginPath()
            path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]:
                path.lineTo(x, y)
            canvas.setStrokeColor(color)
            canvas.setLineWidth(width)
            canvas.drawPath(path, stroke=1, fill=0)

        canvas.setFillColor(REPORT_COLORS["green"])
        canvas.circle(left + plot_w, bottom + ((values[-1] - y_min) / (y_max - y_min)) * plot_h, 2.5, fill=1, stroke=0)
        canvas.setFont("Helvetica", 5.8)
        legend_x = left
        for label, color in [("Price", REPORT_COLORS["green"]), ("20D", REPORT_COLORS["blue"]), ("50D", REPORT_COLORS["purple"])]:
            canvas.setFillColor(color)
            canvas.circle(legend_x, 9, 1.8, fill=1, stroke=0)
            canvas.setFillColor(REPORT_COLORS["muted"])
            canvas.drawString(legend_x + 5, 6.5, label)
            legend_x += 42
        canvas.restoreState()


class HorizontalBarChartFlowable(Flowable):
    def __init__(self, items: list[tuple[str, float]], width: float, height: float, title: str = ""):
        super().__init__()
        self.items = [(label, float(value)) for label, value in items if is_number(value)]
        self.width = width
        self.height = height
        self.title = title

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(REPORT_COLORS["line"])
        canvas.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        if self.title:
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(10, self.height - 15, self.title)
        if not self.items:
            draw_unavailable(canvas, self.width, self.height, "Performance data unavailable.")
            canvas.restoreState()
            return
        max_abs = max(abs(value) for _, value in self.items) or 1
        top = self.height - 28
        row_h = max(12, min(18, (self.height - 38) / max(1, len(self.items))))
        label_w = 92
        zero_x = label_w + (self.width - label_w - 46) / 2
        half_w = (self.width - label_w - 54) / 2
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        canvas.line(zero_x, 10, zero_x, top + 5)
        for idx, (label, value) in enumerate(self.items[:10]):
            y = top - idx * row_h
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica-Bold", 7)
            canvas.drawString(10, y - 3, fit_text(label, 18))
            bar_w = abs(value) / max_abs * half_w
            color = REPORT_COLORS["green"] if value >= 0 else REPORT_COLORS["red"]
            x = zero_x if value >= 0 else zero_x - bar_w
            canvas.setFillColor(color)
            canvas.roundRect(x, y - 7, bar_w, 7, 2, fill=1, stroke=0)
            canvas.setFillColor(color)
            canvas.setFont("Helvetica-Bold", 7)
            canvas.drawRightString(self.width - 10, y - 6, format_percent(value))
        canvas.restoreState()


class ScatterChartFlowable(Flowable):
    def __init__(self, items: list[dict[str, Any]], width: float, height: float, title: str = ""):
        super().__init__()
        self.items = [item for item in items if is_number(item.get("x")) and is_number(item.get("y"))]
        self.width = width
        self.height = height
        self.title = title

    def wrap(self, _available_width: float, _available_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(REPORT_COLORS["line"])
        canvas.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        if self.title:
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(10, self.height - 15, self.title)
        if not self.items:
            draw_unavailable(canvas, self.width, self.height, "Rotation data unavailable.")
            canvas.restoreState()
            return
        left, right, bottom, top = 24, 14, 20, 28
        plot_w = self.width - left - right
        plot_h = self.height - bottom - top
        all_points = [
            point
            for item in self.items
            for point in [{"x": item["x"], "y": item["y"]}, *(item.get("trail") or [])]
            if is_number(point.get("x")) and is_number(point.get("y"))
        ]
        x_min = min(float(item["x"]) for item in all_points)
        x_max = max(float(item["x"]) for item in all_points)
        y_min = min(float(item["y"]) for item in all_points)
        y_max = max(float(item["y"]) for item in all_points)
        x_min, x_max = widen_range(x_min, x_max, 100)
        y_min, y_max = widen_range(y_min, y_max, 100)
        neutral_x = left + ((100 - x_min) / (x_max - x_min)) * plot_w
        neutral_y = bottom + ((100 - y_min) / (y_max - y_min)) * plot_h
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(left, neutral_y, left + plot_w, neutral_y)
        canvas.line(neutral_x, bottom, neutral_x, bottom + plot_h)
        canvas.setFillColor(REPORT_COLORS["muted"])
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(left + plot_w - 45, bottom + plot_h - 8, "Leading")
        canvas.drawString(left + 3, bottom + plot_h - 8, "Improving")
        canvas.drawString(left + 3, bottom + 4, "Lagging")
        canvas.drawString(left + plot_w - 48, bottom + 4, "Weakening")
        def plot_point(point: dict[str, Any]) -> tuple[float, float]:
            return (
                left + ((float(point["x"]) - x_min) / (x_max - x_min)) * plot_w,
                bottom + ((float(point["y"]) - y_min) / (y_max - y_min)) * plot_h,
            )

        for item in self.items[:11]:
            color = item.get("color", REPORT_COLORS["blue"])
            trail = [point for point in item.get("trail") or [] if is_number(point.get("x")) and is_number(point.get("y"))]
            if len(trail) > 1:
                canvas.setStrokeColor(color)
                canvas.setLineWidth(0.8)
                for previous, current in zip(trail, trail[1:]):
                    start_x, start_y = plot_point(previous)
                    end_x, end_y = plot_point(current)
                    canvas.line(start_x, start_y, end_x, end_y)
            x, y = plot_point(item)
            canvas.setFillColor(color)
            canvas.circle(x, y, 3, fill=1, stroke=0)
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica", 5.8)
            canvas.drawString(x + 4, y - 2, fit_text(str(item.get("label", "")), 14))
        canvas.restoreState()


def generate_daily_report_pdf(report: DailyReportResponse | dict[str, Any]) -> BytesIO:
    if isinstance(report, dict):
        report = DailyReportResponse(**report)
    if report.report_pdf_format_version == "daily-report-pdf-v7":
        document = report.report_document or build_report_document(report).model_dump(mode="json")
        return generate_report_pdf_v7(document)
    if report.report_pdf_format_version == "daily-report-pdf-v6":
        document = report.report_document
        if not document:
            document = build_report_document(report).model_copy(
                update={"pdf_format_version": "daily-report-pdf-v6"}
            ).model_dump(mode="json")
        return generate_report_pdf_v6(document)
    return generate_daily_report_pdf_v5(report)


def generate_daily_report_pdf_v5(report: DailyReportResponse | dict[str, Any]) -> BytesIO:
    if isinstance(report, dict):
        report = DailyReportResponse(**report)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.38 * inch,
        leftMargin=0.38 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.46 * inch,
        title=report.title,
    )
    styles = build_visual_report_styles()
    story: list[Any] = []
    context = build_report_narrative_context(report)
    story.extend(build_briefing_cover(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_executive_summary(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_changes_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_relationships_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_cross_market_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_leadership_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_risk_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_scenarios_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_watchlist_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_tomorrow_page(report, styles, context))
    if (report.market_evolution or {}).get("available"):
        story.append(PageBreak())
        story.extend(build_briefing_history_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_briefing_appendix(report, styles, context))
    source_state = infer_report_source_state(report)
    document.build(
        story,
        onFirstPage=lambda canvas, doc: draw_page_frame(canvas, doc, report, source_state),
        onLaterPages=lambda canvas, doc: draw_page_frame(canvas, doc, report, source_state),
    )
    buffer.seek(0)
    return buffer


def build_visual_report_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle(
            "ReportKicker",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=REPORT_COLORS["blue"],
            alignment=TA_LEFT,
        ),
        "title": ParagraphStyle(
            "VisualReportTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=27,
            textColor=REPORT_COLORS["ink"],
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "VisualReportSubtitle",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=REPORT_COLORS["muted"],
        ),
        "section": ParagraphStyle(
            "VisualSection",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=REPORT_COLORS["ink"],
            spaceBefore=4,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "VisualBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=REPORT_COLORS["ink"],
        ),
        "small": ParagraphStyle(
            "VisualSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=8.5,
            textColor=REPORT_COLORS["muted"],
        ),
        "label": ParagraphStyle(
            "VisualLabel",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.5,
            textColor=REPORT_COLORS["muted"],
        ),
        "metric": ParagraphStyle(
            "VisualMetric",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            textColor=REPORT_COLORS["green"],
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "VisualTableCell",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.7,
            leading=8.4,
            textColor=REPORT_COLORS["ink"],
        ),
        "table_header": ParagraphStyle(
            "VisualTableHeader",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            textColor=colors.white,
        ),
    }


def build_report_narrative_context(report: DailyReportResponse) -> dict[str, Any]:
    health = report.market_health
    risk = report.risk_dashboard
    playbook = report.decision_dashboard.playbook
    volatility = extract_volatility(report)
    top_sector = (get_sector_items(report) or [{}])[0].get("name", "Leadership")
    sentiment_state = report.fear_greed.status
    macro_state = report.macro.get("state_label", "Unavailable")
    recommendation = playbook.headline or "Stay Selective"
    primary_opportunity = (
        f"{top_sector} remains the clearest published leadership area."
        if top_sector != "Leadership"
        else first_or_default(report.key_drivers, "Leadership remains constructive.")
    )
    primary_risk = playbook.main_risk or first_or_default(report.main_risks, "Risk conditions require monitoring.")
    invalidation = build_risk_triggers(report)
    context = {
        "recommendation": recommendation,
        "regime": report.market_regime,
        "health_label": health.status,
        "risk_label": classify_risk_label(risk.score),
        "breadth_state": "Healthy" if health.components.breadth >= 70 else "Mixed" if health.components.breadth >= 50 else "Weak",
        "volatility_state": volatility["status"],
        "leadership_state": "Strong" if health.components.sector_strength >= 70 else "Mixed",
        "sentiment_state": sentiment_state,
        "macro_state": macro_state,
        "macro_current_risk": report.macro.get("key_risk", "Macro evidence unavailable."),
        "macro_invalidation": report.macro.get("invalidation_conditions", "Macro evidence unavailable."),
        "primary_opportunity": primary_opportunity,
        "primary_risk": primary_risk,
        "invalidation_conditions": invalidation,
    }
    narrative = report.report_narrative or {}
    if narrative:
        context["recommendation"] = narrative.get("recommendation") or context["recommendation"]
        context["primary_opportunity"] = narrative.get("primaryOpportunity") or context["primary_opportunity"]
        context["primary_risk"] = narrative.get("primaryRisk") or context["primary_risk"]
        context["market_narrative"] = narrative.get("marketNarrative")
        context["cross_tab_narrative"] = narrative.get("crossTabNarrative")
        context["action_summary"] = narrative.get("actionSummary") or []
    return context


def build_briefing_cover(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    confidence = report.recommendation_confidence or {}
    themes = get_theme_items(report)
    primary_theme = themes[0].get("name") if themes else (report.sector_leaders[0] if report.sector_leaders else "No qualified theme")
    if primary_theme == "Communication Services":
        primary_theme = "Comm. Services"
    cover_risk = str(context["primary_risk"])
    if "breadth" in cover_risk.lower():
        cover_risk = "Narrow Breadth"
    elif "volatil" in cover_risk.lower():
        cover_risk = "Volatility Risk"
    narrative = context.get("market_narrative") or report.executive_summary
    return [
        build_cover_header(report, styles),
        Spacer(1, 0.18 * inch),
        interpretation_callout("Overall Thesis", narrative, styles, width=6.9 * inch),
        Spacer(1, 0.16 * inch),
        metric_cards([
            ("Market Regime", fit_text(report.market_regime, 28), "Current market posture", REPORT_COLORS["green"]),
            ("Confidence", f"{confidence.get('score', 'N/A')}%", str(confidence.get("rating") or "Unavailable"), REPORT_COLORS["blue"]),
            ("Primary Theme", fit_text(str(primary_theme), 24), "Highest-ranked available leadership", REPORT_COLORS["purple"]),
            ("Major Risk", fit_text(cover_risk, 25), "Primary thesis constraint", REPORT_COLORS["orange"]),
        ], styles),
        Spacer(1, 0.16 * inch),
        two_column(
            panel_table("What Happened", [p(shorten_text(narrative, 420), styles["body"])], styles, width=3.35 * inch),
            panel_table("What Matters Next", [compact_list(list(context.get("action_summary") or report.tomorrow_watch), styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.16 * inch),
        chart_panel("Market Context: SPY 6M", build_spy_chart(report), styles, width=6.9 * inch),
    ]


def build_briefing_executive_summary(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Executive Summary", styles),
        p("WHAT IS THE MARKET POSTURE?", styles["kicker"]),
        Spacer(1, 0.06 * inch),
        interpretation_callout("Strategist's Read", context.get("market_narrative") or report.executive_summary, styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Market Conviction", [market_conviction_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Confidence & Alignment", [signal_convergence_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Primary Drivers", [compact_list(briefing_primary_drivers(report), styles)], styles, width=3.35 * inch),
            panel_table("Largest Risk", [p(context["primary_risk"], styles["body"])], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Highest Conviction", context["primary_opportunity"], styles, width=6.9 * inch),
    ]


def build_briefing_changes_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    changes = report.report_changes or {}
    story: list[Any] = [
        section_title("What Changed Today", styles),
        p("WHAT IS DIFFERENT FROM THE PREVIOUS BRIEFING?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
    ]
    if not changes.get("available"):
        story.extend([
            interpretation_callout("Change Baseline", "Baseline report established.", styles, width=6.9 * inch),
            Spacer(1, 0.12 * inch),
            panel_table("Current Baseline", [market_scoreboard(report, context, styles, 6.55 * inch)], styles, width=6.9 * inch),
        ])
        return story
    story.extend([
        panel_table("Meaningful Changes Only", [report_changes_detail_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Previous Playbook Review", [previous_playbook_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Recent Evolution", [market_evolution_wide_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Why The Change Matters", changes.get("summary") or "No meaningful changes since the previous report.", styles, width=6.9 * inch),
    ])
    return story


def build_briefing_relationships_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    relationships = report.signal_relationships or (report.report_narrative or {}).get("relationships") or []
    relationship_copy = context.get("cross_tab_narrative") or "No supported cross-signal relationship materially changes the base case."
    return [
        section_title("Why It Happened", styles),
        p("HOW DO THE SIGNALS CONNECT?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        interpretation_callout("Connected Narrative", relationship_copy, styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        panel_table("Evidence Chain", [relationship_flow_table(relationships, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Signal Agreement", [signal_convergence_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Trade-Off", [p(build_tradeoff_summary(report), styles["body"])], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
    ]


def build_briefing_cross_market_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Cross-Market Analysis", styles),
        p("DO INDEX, BREADTH, VOLATILITY, AND MACRO AGREE?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        chart_panel("Normalized Index Returns", index_comparison_chart(report, 6.65 * inch, 2.05 * inch), styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Market Structure", [market_scoreboard(report, context, styles, 3.0 * inch)], styles, width=3.35 * inch),
            panel_table("Captured Cross-Asset Evidence", [cross_asset_summary_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Synthesis", build_market_health_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_briefing_leadership_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Leadership Intelligence", styles),
        p("WHERE IS LEADERSHIP STRENGTHENING OR WEAKENING?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        panel_table("Leadership Map", [leadership_intelligence_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            chart_panel("Sector Rotation", sector_rotation_chart(report, 3.2 * inch, 1.8 * inch), styles, width=3.35 * inch),
            chart_panel("Theme Rotation", theme_rotation_chart(report, 3.2 * inch, 1.8 * inch), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Why Leadership Matters", build_leadership_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_briefing_risk_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    invalidation = (report.report_narrative or {}).get("invalidation") or context["invalidation_conditions"]
    return [
        section_title("Risk Assessment", styles),
        p("WHAT COULD INVALIDATE TODAY'S THESIS?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        two_column(
            panel_table("Risk Posture", [risk_summary_table(report, styles)], styles, width=2.6 * inch),
            panel_table("Risk Drivers", [risk_driver_table(report, styles)], styles, width=4.1 * inch),
            [2.65 * inch, 4.15 * inch],
        ),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Hidden Weaknesses", [hidden_warnings_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Hidden Strengths", [hidden_confirmations_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        panel_table("Thesis Invalidation", [checkbox_list(invalidation, styles, checked=False, width=6.45 * inch)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Risk Interpretation", build_risk_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_briefing_scenarios_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Scenario Planning", styles),
        p("WHAT WOULD CHANGE THE BASE CASE?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        panel_table("Bull, Base, and Bear Paths", [scenario_briefing_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.12 * inch),
        interpretation_callout("How To Use These Scenarios", "The scenarios are conditional, not predictions. Probability is shown only because the existing conviction engine produced it; conditions and response should be rechecked as evidence changes.", styles, width=6.9 * inch),
        Spacer(1, 0.12 * inch),
        panel_table("Current Decision Checklist", [decision_checklist_table(report, styles)], styles, width=6.9 * inch),
    ]


def build_briefing_watchlist_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Watchlist Intelligence", styles),
        p("WHICH PERSONAL POSITIONS DESERVE ATTENTION?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        panel_table("Personalized Priorities", [watchlist_intelligence_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Portfolio Read", build_watchlist_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_briefing_tomorrow_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Tomorrow's Checklist", styles),
        p("WHAT MUST TRADERS VERIFY NEXT?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        two_column(
            panel_table("Signal Checklist", [decision_checklist_wide_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Tomorrow Watch", [checkbox_list(report.tomorrow_watch, styles, checked=False, width=3.0 * inch)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        panel_table("Upcoming Economic Events", [economic_calendar_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Levels To Monitor", [market_levels_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Invalidation Watch", [checkbox_list(context["invalidation_conditions"], styles, checked=False, width=3.0 * inch)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
    ]


def build_briefing_history_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Historical Context", styles),
        p("HOW HAS THE MARKET EVIDENCE EVOLVED?", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        panel_table("Recent Report History", [market_evolution_wide_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.12 * inch),
        panel_table("Previous Playbook Review", [previous_playbook_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.12 * inch),
        interpretation_callout("Evidence Boundary", "Historical context is limited to prior frozen report snapshots. No analogous-period statistics are shown because the current report pipeline does not capture validated similarity outcomes.", styles, width=6.9 * inch),
    ]


def build_briefing_appendix(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Appendix", styles),
        p("PROVENANCE, METHODOLOGY, AND DATA LIMITS", styles["kicker"]),
        Spacer(1, 0.08 * inch),
        two_column(
            panel_table("Report Identity", [report_identity_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Data Sources", [p(f"Source state: {infer_report_source_state(report)}. Provider, cache, stale, fallback, and test states remain labelled from the frozen report snapshot.", styles["body"])], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        panel_table("Methodology", [p("Market posture, change detection, conviction, scenarios, leadership, risk, and watchlist priorities are derived from existing deterministic application engines and the immutable inputs captured at generation time.", styles["body"])], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        panel_table("Theme Methodology", [p(theme_methodology_disclosure(report), styles["small"])], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        panel_table("Unavailable or Partial Data", [checkbox_list(build_unavailable_data_notes(report), styles, checked=False, width=6.45 * inch)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Disclaimer", "This report is for informational and educational purposes only and does not constitute investment advice. Investing involves risk, including possible loss of principal. Data may be delayed, incomplete, cached, simulated, or unavailable.", styles, width=6.9 * inch),
    ]


def build_executive_dashboard(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    health = report.market_health
    risk = report.risk_dashboard
    story: list[Any] = [
        build_cover_header(report, styles),
        Spacer(1, 0.08 * inch),
        recommendation_card(report, context, styles),
        Spacer(1, 0.1 * inch),
    ]
    playbook_panel = panel_table(
        "Cross-Tab Intelligence",
        [
            p(context.get("cross_tab_narrative") or build_market_playbook_interpretation(report, context), styles["body"]),
            Spacer(1, 0.08 * inch),
            p((report.report_narrative or {}).get("confidenceReasoning") or "Confidence reasoning unavailable.", styles["small"]),
        ],
        styles,
        width=3.25 * inch,
    )
    spy_chart = chart_panel(
        "Main Trend: SPY 6M Chart",
        build_spy_chart(report),
        styles,
        width=3.25 * inch,
    )
    story.append(two_column(playbook_panel, spy_chart, [3.35 * inch, 3.45 * inch]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        two_column(
            panel_table("Market Conviction", [market_conviction_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Today's Decision Checklist", [decision_checklist_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        two_column(
            panel_table("What Changed Since Last Report", [report_changes_table(report, styles)], styles, width=3.35 * inch),
            interpretation_callout("What This Means", build_market_playbook_interpretation(report, context), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        )
    )
    return story


def build_market_index_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Is the Uptrend Healthy?", styles),
        top_insights_panel(build_page_insights(report, context, "health"), styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        chart_panel(
            "Normalized Index Returns",
            index_comparison_chart(report, 6.75 * inch, 2.1 * inch),
            styles,
            width=6.9 * inch,
        ),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Market Snapshot", [market_snapshot_table(report, styles)], styles, width=3.35 * inch),
            chart_panel(
                "Health Driver Scorecard",
                HorizontalBarChartFlowable(build_health_driver_items(report), 3.2 * inch, 1.65 * inch),
                styles,
                width=3.35 * inch,
            ),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Breadth & Volatility", [breadth_volatility_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Cross-Asset Conditions", [cross_asset_summary_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("What This Means", build_market_health_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_sector_theme_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Where Is Money Flowing?", styles),
        top_insights_panel(build_page_insights(report, context, "leadership"), styles, width=6.9 * inch),
        Spacer(1, 0.06 * inch),
        two_column(
            panel_table("Top Sectors", [sector_snapshot_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Themes", theme_leadership_panel(report, styles), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        two_column(
            chart_panel("Sector Rotation", sector_rotation_chart(report, 3.25 * inch, 1.65 * inch), styles, width=3.35 * inch),
            panel_table("Theme Rotation", theme_rotation_panel(report, styles), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        three_column(
            ranking_panel("Improving", rotation_bucket_items(get_sector_items(report), "improving"), styles, width=2.15 * inch),
            ranking_panel("Weakening", rotation_bucket_items(get_sector_items(report), "weakening"), styles, width=2.15 * inch),
            ranking_panel("Laggards", ranking_items(list(reversed(get_sector_items(report))), "1m", limit=5, preserve_order=True), styles, width=2.15 * inch),
            [2.25 * inch, 2.25 * inch, 2.25 * inch],
        ),
    ]


def build_risk_sentiment_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("What Could Go Wrong?", styles),
        top_insights_panel(build_page_insights(report, context, "risk"), styles, width=6.9 * inch),
        Spacer(1, 0.06 * inch),
        two_column(
            panel_table("Overall Risk", [risk_summary_table(report, styles)], styles, width=2.6 * inch),
            chart_panel(
                "Risk Scoreboard",
                HorizontalBarChartFlowable(build_risk_breakdown_items(report), 4.0 * inch, 1.8 * inch),
                styles,
                width=4.1 * inch,
            ),
            [2.65 * inch, 4.15 * inch],
        ),
        Spacer(1, 0.06 * inch),
        two_column(
            ranking_panel("Top Risk Drivers", risk_driver_ranking_items(report), styles, width=3.35 * inch),
            panel_table("Market Sentiment", [sentiment_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        two_column(
            panel_table("Hidden Warnings", [hidden_warnings_table(report, styles)], styles, width=3.35 * inch),
            panel_table("Hidden Confirmations", [hidden_confirmations_table(report, styles)], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        interpretation_callout("What This Means", build_risk_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_watchlist_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("Which Stocks Stand Out?", styles),
        top_insights_panel(build_page_insights(report, context, "watchlist"), styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        feature_stock_cards(report, styles),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Watchlist Ranking", [watchlist_table(report, styles)], styles, width=3.95 * inch),
            panel_table("Top Stock Ideas", [stock_ideas_table(report, styles)], styles, width=2.75 * inch),
            [4.0 * inch, 2.8 * inch],
        ),
        Spacer(1, 0.1 * inch),
        selected_stock_charts_panel(report, styles),
        Spacer(1, 0.1 * inch),
        interpretation_callout("What This Means", build_watchlist_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_macro_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("What Matters Next?", styles),
        top_insights_panel(build_page_insights(report, context, "macro"), styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        panel_table("Economic Calendar", [economic_calendar_table(report, styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        three_column(
            panel_table("Previous Playbook Review", [previous_playbook_table(report, styles)], styles, width=2.15 * inch),
            panel_table("Market Evolution", [market_evolution_table(report, styles)], styles, width=2.15 * inch),
            panel_table("Scenario Plan", [scenario_plan_table(report, styles)], styles, width=2.15 * inch),
            [2.25 * inch, 2.25 * inch, 2.25 * inch],
        ),
        Spacer(1, 0.1 * inch),
        interpretation_callout("What This Means", build_macro_interpretation(report, context), styles, width=6.9 * inch),
    ]


def build_final_page(report: DailyReportResponse, styles: dict[str, ParagraphStyle], context: dict[str, Any]) -> list[Any]:
    return [
        section_title("How This Report Was Built", styles),
        top_insights_panel(build_page_insights(report, context, "methodology"), styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        two_column(
            panel_table("Report Methodology", [p("Market regime, health, risk, leadership, breadth, and sentiment are derived from existing deterministic app engines and provider snapshots captured when the report is generated.", styles["body"])], styles, width=3.35 * inch),
            panel_table("Data Sources", [p(f"Source state: {infer_report_source_state(report)}. Mock, cached, stale, fallback, and live states remain labelled from the captured report snapshot.", styles["body"])], styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.1 * inch),
        panel_table("Theme Methodology", [p(theme_methodology_disclosure(report), styles["small"])], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        panel_table("Unavailable or Partial Data", [compact_list(build_unavailable_data_notes(report), styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Disclaimer", "This report is for informational and educational purposes only and does not constitute investment advice. Investing involves risk, including possible loss of principal. Data may be delayed, incomplete, cached, simulated, or unavailable.", styles, width=6.9 * inch),
    ]


def build_cover_header(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    left = [
        p("Market Intelligence", styles["kicker"]),
        p("Daily Market Intelligence Briefing", styles["title"]),
        p(f"{format_report_date(report.date)} | {session_label()} | {report.report_schema_version or 'Version 1'}", styles["subtitle"]),
    ]
    right = [
        p(f"Generated: {format_generated_time(report.generated_at or report.generated_time)}", styles["subtitle"]),
        p(f"Data Source: {infer_report_source_state(report)}", styles["subtitle"]),
        badge_paragraph(infer_report_source_state(report), styles),
    ]
    table = Table([[left, right]], colWidths=[4.7 * inch, 2.0 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def metric_cards(items: list[tuple[str, str, str, colors.Color]], styles: dict[str, ParagraphStyle]) -> Table:
    cells = []
    for label, value, note, color in items:
        cells.append([
            p(label.upper(), styles["label"]),
            Paragraph(f"<font color='{color.hexval()}'><b>{escape(value)}</b></font>", styles["metric"]),
            p(shorten_text(note, 55), styles["small"]),
        ])
    table = Table([cells], colWidths=[1.68 * inch] * 4)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, REPORT_COLORS["line"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def panel_table(title: str, content: list[Any], styles: dict[str, ParagraphStyle], width: float) -> Table:
    table = Table([[p(title.upper(), styles["section"])], [content]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, REPORT_COLORS["line"]),
        ("LINEBELOW", (0, 0), (0, 0), 0.4, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def chart_panel(title: str, chart: Flowable, styles: dict[str, ParagraphStyle], width: float) -> Table:
    return panel_table(title, [chart], styles, width)


def two_column(left: Any, right: Any, widths: list[float]) -> Table:
    table = Table([[left, right]], colWidths=widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def three_column(a: Any, b: Any, c: Any, widths: list[float]) -> Table:
    table = Table([[a, b, c]], colWidths=widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def section_title(title: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"<b>{escape(title)}</b>", styles["title"])


def callout_grid(items: list[tuple[str, str, colors.Color]], styles: dict[str, ParagraphStyle]) -> Table:
    cells = []
    for label, body, color in items:
        cells.append([
            Paragraph(f"<font color='{color.hexval()}'><b>{escape(label)}</b></font>", styles["label"]),
            p(shorten_text(body, 105), styles["small"]),
        ])
    table = Table([cells], colWidths=[1.02 * inch] * len(cells))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), REPORT_COLORS["panel"]),
        ("BOX", (0, 0), (-1, -1), 0.4, REPORT_COLORS["line"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def recommendation_card(report: DailyReportResponse, context: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    playbook = report.decision_dashboard.playbook
    confidence = report.recommendation_confidence or {}
    cells = [
        [
            p("TODAY'S INTELLIGENCE", styles["kicker"]),
            Paragraph(f"<font color='{REPORT_COLORS['green'].hexval()}'><b>{escape(context['recommendation'])}</b></font>", styles["title"]),
            p(shorten_text(playbook.summary or report.executive_summary, 210), styles["body"]),
        ],
        [
            p("Decision Posture", styles["label"]),
            Paragraph(f"<font color='{REPORT_COLORS['blue'].hexval()}'><b>{escape(report.decision_dashboard.aggressiveness.status)}</b></font>", styles["metric"]),
            p(f"Confidence: {confidence.get('score', report.decision_confidence.score)}% | Risk: {classify_risk_label(report.risk_dashboard.score)}", styles["small"]),
        ],
    ]
    table = Table([cells], colWidths=[4.9 * inch, 1.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), REPORT_COLORS["panel_alt"]),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#BFDBFE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def top_insights_panel(insights: list[str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    return panel_table("Top Insights", [top_insights_table(insights, styles, width - 0.18 * inch)], styles, width=width)


def top_insights_table(insights: list[str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    rows = [[p(f"{index}. {shorten_text(insight, 116)}", styles["body"])] for index, insight in enumerate(insights[:5], 1)]
    if not rows:
        rows = [[p("No material insight available from the report snapshot.", styles["body"])]]
    return data_table(rows, [width], header=False)


def interpretation_callout(title: str, text: str, styles: dict[str, ParagraphStyle], width: float) -> Table:
    table = Table([[p(title.upper(), styles["label"])], [p(shorten_text(text, 460), styles["body"])]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#86EFAC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def market_scoreboard(report: DailyReportResponse, context: dict[str, Any], styles: dict[str, ParagraphStyle], width: float) -> Table:
    rows = [[p("Category", styles["table_header"]), p("Status", styles["table_header"]), p("Value", styles["table_header"])]]
    rows.extend([
        [p("Trend", styles["table_cell"]), p("Strong" if report.market_health.components.trend >= 70 else "Mixed", styles["table_cell"]), p(f"{report.market_health.components.trend}/100", styles["table_cell"])],
        [p("Breadth", styles["table_cell"]), p(context["breadth_state"], styles["table_cell"]), p(f"{report.market_health.components.breadth}/100", styles["table_cell"])],
        [p("Leadership", styles["table_cell"]), p(context["leadership_state"], styles["table_cell"]), p(f"{report.market_health.components.sector_strength}/100", styles["table_cell"])],
        [p("Volatility", styles["table_cell"]), p(context["volatility_state"], styles["table_cell"]), p(f"{report.market_health.components.volatility}/100", styles["table_cell"])],
        [p("Sentiment", styles["table_cell"]), p(context["sentiment_state"], styles["table_cell"]), p(str(report.fear_greed.score), styles["table_cell"])],
        [p("Macro", styles["table_cell"]), p(context["macro_state"], styles["table_cell"]), p("Watch", styles["table_cell"])],
        [p("Risk", styles["table_cell"]), p(context["risk_label"], styles["table_cell"]), p(f"{report.risk_dashboard.score}/100", styles["table_cell"])],
    ])
    return data_table(rows, [width * 0.34, width * 0.36, width * 0.22])


def market_conviction_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    conviction = report.market_conviction or {}
    rows = [
        [p("Score", styles["label"]), Paragraph(f"<font color='{REPORT_COLORS['green'].hexval()}'><b>{conviction.get('score', 'N/A')}/100</b></font>", styles["metric"])],
        [p("Read", styles["table_cell"]), p(str(conviction.get("rating", "N/A")), styles["table_cell"])],
        [p("Why not higher", styles["table_cell"]), p(shorten_text("; ".join(conviction.get("whyNotHigher") or []), 84), styles["table_cell"])],
        [p("Why not lower", styles["table_cell"]), p(shorten_text("; ".join(conviction.get("whyNotLower") or []), 84), styles["table_cell"])],
    ]
    for item in (conviction.get("contributors") or [])[:3]:
        score = parse_number(item.get("score")) or 0
        weight = parse_number(item.get("weight")) or 0
        points = round(score * weight / 100)
        rows.append([p(str(item.get("label")), styles["table_cell"]), p(f"{points}/{round(weight)}", styles["table_cell"])])
    return data_table(rows, [1.05 * inch, 1.95 * inch], header=False)


def decision_checklist_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    checklist = report.decision_checklist or {}
    rows = [[p("Item", styles["table_header"]), p("Read", styles["table_header"]), p("Reason", styles["table_header"])]]
    for item in (checklist.get("items") or [])[:5]:
        rows.append([p(str(item.get("label")), styles["table_cell"]), p(str(item.get("status")), styles["table_cell"]), p(shorten_text(item.get("reason"), 44), styles["table_cell"])])
    rows.append([p("Overall", styles["table_cell"]), p(f"{checklist.get('passed', 0)}/{checklist.get('total', 0)}", styles["table_cell"]), p(str(checklist.get("readiness", "N/A")), styles["table_cell"])])
    return data_table(rows, [0.92 * inch, 0.45 * inch, 1.43 * inch])


def report_changes_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    changes = report.report_changes or {}
    items = changes.get("items") or []
    if not changes.get("available"):
        return data_table([[p(changes.get("summary") or "Baseline report established.", styles["table_cell"])]], [3.0 * inch], header=False)
    rows = [[p("Area", styles["table_header"]), p("Importance", styles["table_header"]), p("Why", styles["table_header"])]]
    for item in items[:5]:
        rows.append([
            p(shorten_text(item.get("label"), 24), styles["table_cell"]),
            p(str(item.get("importance", "N/A")), styles["table_cell"]),
            p(shorten_text(item.get("reason") or f"{item.get('previous', 'N/A')} -> {item.get('current', 'N/A')}", 44), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("No meaningful changes", styles["table_cell"]), p("-", styles["table_cell"]), p("-", styles["table_cell"])])
    return data_table(rows, [1.25 * inch, 0.7 * inch, 1.0 * inch])


def report_changes_detail_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    items = (report.report_changes or {}).get("items") or []
    rows = [[p(value, styles["table_header"]) for value in ["Area", "Before", "Now", "Read", "Evidence"]]]
    for item in items[:8]:
        rows.append([
            p(shorten_text(item.get("label"), 30), styles["table_cell"]),
            p(str(item.get("previous", "N/A")), styles["table_cell"]),
            p(str(item.get("current", "N/A")), styles["table_cell"]),
            p(str(item.get("direction", "changed")).title(), styles["table_cell"]),
            p(shorten_text(item.get("reason") or "No supported explanation was captured.", 88), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("No meaningful changes", styles["table_cell"]), p("-", styles["table_cell"]), p("-", styles["table_cell"]), p("Stable", styles["table_cell"]), p("No threshold-level change was detected.", styles["table_cell"])])
    return data_table(rows, [1.08 * inch, 0.68 * inch, 0.68 * inch, 0.72 * inch, 3.29 * inch])


def market_evolution_wide_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    evolution = report.market_evolution or {}
    points = evolution.get("points") or []
    if len(points) < 2:
        return data_table([[p("Insufficient report history.", styles["table_cell"])]], [3.0 * inch], header=False)
    previous, latest = points[-2], points[-1]
    rows = [[p("Evidence", styles["table_header"]), p("Previous", styles["table_header"]), p("Current", styles["table_header"])]]
    for label, key in [("Health", "health"), ("Risk", "risk"), ("Breadth", "breadth"), ("Conviction", "conviction"), ("Confidence", "confidence")]:
        rows.append([p(label, styles["table_cell"]), p(format_number(previous.get(key)), styles["table_cell"]), p(format_number(latest.get(key)), styles["table_cell"])])
    return data_table(rows, [1.3 * inch, 0.82 * inch, 0.82 * inch])


def relationship_flow_table(relationships: list[Any], styles: dict[str, ParagraphStyle]) -> Table:
    supported = [str(item) for item in relationships if item]
    if not supported:
        supported = ["No supported cross-signal relationship is available for this report snapshot."]
    rows = []
    for index, item in enumerate(supported[:5], 1):
        rows.append([
            Paragraph(f"<font color='{REPORT_COLORS['blue'].hexval()}'><b>{index}</b></font>", styles["metric"]),
            p(shorten_text(item, 190), styles["body"]),
        ])
    return data_table(rows, [0.5 * inch, 5.95 * inch], header=False)


def build_tradeoff_summary(report: DailyReportResponse) -> str:
    tradeoff = report.trade_off_analysis or (report.report_commentary or {}).get("tradeOff") or (report.report_narrative or {}).get("tradeOff") or {}
    if isinstance(tradeoff, dict):
        return str(tradeoff.get("overall") or tradeoff.get("summary") or "No supported trade-off analysis is available.")
    return str(tradeoff or "No supported trade-off analysis is available.")


def briefing_primary_drivers(report: DailyReportResponse) -> list[str]:
    contributors = [item for item in (report.market_conviction or {}).get("contributors", []) if isinstance(item, dict) and parse_number(item.get("score")) is not None]
    contributors.sort(key=lambda item: parse_number(item.get("score")) or 0, reverse=True)
    output = [f"{item.get('label', 'Signal')} {format_number(item.get('score'))}/100." for item in contributors[:3]]
    output.extend(report.hidden_confirmations or [])
    output.extend(report.key_drivers or [])
    return list(dict.fromkeys(output))[:4]


def leadership_intelligence_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    sectors = get_sector_items(report)
    themes = get_theme_items(report)
    current = [str(item.get("name") or "N/A") for item in sectors[:3]]
    emerging = leadership_names_by_state(sectors, ("improving", "emerging")) + leadership_names_by_state(themes, ("improving", "emerging"))
    weakening = leadership_names_by_state(sectors, ("weakening", "lagging", "at risk")) + leadership_names_by_state(themes, ("weakening", "lagging", "at risk"))
    rotation_changes = [
        str(item.get("reason"))
        for item in (report.report_changes or {}).get("items", [])
        if isinstance(item, dict) and "leadership" in str(item.get("label", "")).lower()
    ]
    rows = [[p("Read", styles["table_header"]), p("Groups", styles["table_header"]), p("Evidence", styles["table_header"])]]
    rows.extend([
        [p("Current Leaders", styles["table_cell"]), p(", ".join(current) or "Unavailable", styles["table_cell"]), p("Highest-ranked captured sector and theme evidence.", styles["table_cell"])],
        [p("Emerging", styles["table_cell"]), p(", ".join(dict.fromkeys(emerging[:4])) or "No qualified signal", styles["table_cell"]), p("Classification explicitly indicates improving or emerging.", styles["table_cell"])],
        [p("Weakening", styles["table_cell"]), p(", ".join(dict.fromkeys(weakening[:4])) or "No qualified signal", styles["table_cell"]), p("Classification explicitly indicates weakening or lagging.", styles["table_cell"])],
        [p("Rotation Change", styles["table_cell"]), p(shorten_text(rotation_changes[0], 80) if rotation_changes else "No threshold-level change", styles["table_cell"]), p("Compared with the previous frozen report.", styles["table_cell"])],
    ])
    return data_table(rows, [1.05 * inch, 2.25 * inch, 3.15 * inch])


def leadership_names_by_state(items: list[dict[str, Any]], states: tuple[str, ...]) -> list[str]:
    names = []
    for item in items:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        state = f"{item.get('classification', '')} {item.get('status', '')} {metadata.get('status', '')}".lower()
        if any(value in state for value in states):
            names.append(str(item.get("name") or item.get("display_name") or "N/A"))
    return names


def checkbox_list(items: Any, styles: dict[str, ParagraphStyle], *, checked: bool, width: float) -> Table:
    values = items if isinstance(items, list) else [items] if items else []
    mark = "[x]" if checked else "[ ]"
    rows = [[p(f"{mark} {shorten_text(item, 150)}", styles["table_cell"])] for item in values[:8]]
    if not rows:
        rows = [[p("[ ] No supported checklist item is available.", styles["table_cell"])]]
    return data_table(rows, [width], header=False)


def scenario_briefing_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    scenarios = [item for item in (report.scenario_plan or []) if isinstance(item, dict)]
    rows = [[p(value, styles["table_header"]) for value in ["Scenario", "Probability", "Conditions", "Expectation", "What Changes It", "Response"]]]
    for item in scenarios[:3]:
        probability = f"{item.get('probability')}%" if item.get("probability") is not None else str(item.get("probabilityBand") or "Qualitative")
        rows.append([
            p(str(item.get("name") or "Scenario"), styles["table_cell"]),
            p(probability, styles["table_cell"]),
            p(shorten_text(item.get("conditions") or "Unavailable", 70), styles["table_cell"]),
            p(shorten_text(item.get("expectedBehaviour") or item.get("expectation") or "Unavailable", 70), styles["table_cell"]),
            p(shorten_text(item.get("changesProbability") or item.get("invalidation") or "Unavailable", 70), styles["table_cell"]),
            p(shorten_text(item.get("suggestedResponse") or "Unavailable", 70), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("Unavailable", styles["table_cell"]), p("-", styles["table_cell"]), p("No supported scenario evidence.", styles["table_cell"]), p("-", styles["table_cell"]), p("-", styles["table_cell"]), p("-", styles["table_cell"])])
    return data_table(rows, [0.82 * inch, 0.58 * inch, 1.17 * inch, 1.17 * inch, 1.17 * inch, 1.54 * inch])


def watchlist_intelligence_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    items = [item for item in (report.watchlist_summary or {}).get("items", []) if isinstance(item, dict)]
    rows = [[p(value, styles["table_header"]) for value in ["Priority", "Ticker", "Evidence-Based Read"]]]
    if not items:
        fallback = [item for item in report.stock_charts if isinstance(item, dict)][:4]
        for item in fallback:
            rows.append([p("Market Idea", styles["table_cell"]), p(str(item.get("symbol") or item.get("ticker") or "N/A"), styles["table_cell"]), p(shorten_text(item.get("reason") or "Captured highest-conviction setup.", 100), styles["table_cell"])])
    else:
        by_score = sorted(items, key=lambda item: parse_number(item.get("overall_score") if item.get("overall_score") is not None else item.get("score")) or -999, reverse=True)
        by_change = sorted(items, key=lambda item: parse_number(item.get("change_percent")) or -999, reverse=True)
        risk_item = next((item for item in items if any(word in f"{item.get('risk_flag', '')} {item.get('rating', '')}".lower() for word in ("risk", "weak", "avoid", "sell", "below"))), None)
        selections = [
            ("Highest Opportunity", by_score[0] if by_score else None),
            ("Most Improved", next((item for item in by_change if (parse_number(item.get("change_percent")) or 0) > 0), None)),
            ("Needs Review", by_score[-1] if by_score else None),
            ("Highest Risk", risk_item),
        ]
        for category, item in selections:
            if not item:
                continue
            setup = item.get("main_setup") or item.get("setup") or item.get("rating") or item.get("risk_flag") or "No setup detail available."
            change = parse_number(item.get("change_percent"))
            detail = f"{setup} | {format_percent(change)} today" if change is not None else str(setup)
            rows.append([p(category, styles["table_cell"]), p(str(item.get("symbol") or item.get("ticker") or "N/A"), styles["table_cell"]), p(shorten_text(detail, 110), styles["table_cell"])])
    if len(rows) == 1:
        rows.append([p("Unavailable", styles["table_cell"]), p("N/A", styles["table_cell"]), p("No personal watchlist or supported fallback ideas were captured.", styles["table_cell"])])
    return data_table(rows, [1.28 * inch, 0.72 * inch, 4.45 * inch])


def decision_checklist_wide_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    checklist = report.decision_checklist or {}
    rows = []
    for item in (checklist.get("items") or [])[:7]:
        status = str(item.get("status") or "Watch")
        mark = "[x]" if status.lower() == "pass" else "[ ]"
        rows.append([p(f"{mark} {item.get('label', 'Condition')}", styles["table_cell"]), p(status, styles["table_cell"]), p(format_number(item.get("value")), styles["table_cell"])])
    if not rows:
        rows = [[p("[ ] Checklist unavailable", styles["table_cell"]), p("Watch", styles["table_cell"]), p("N/A", styles["table_cell"])]]
    return data_table(rows, [1.75 * inch, 0.65 * inch, 0.55 * inch], header=False)


def report_identity_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [p("Report ID", styles["table_cell"]), p(shorten_text(report.report_id or "Unavailable", 50), styles["table_cell"])],
        [p("Market Date", styles["table_cell"]), p(str(report.market_date or report.date), styles["table_cell"])],
        [p("Schema", styles["table_cell"]), p(str(report.report_schema_version or "Unavailable"), styles["table_cell"])],
        [p("PDF Format", styles["table_cell"]), p(str(report.report_pdf_format_version or REPORT_PDF_FORMAT_VERSION), styles["table_cell"])],
    ]
    return data_table(rows, [0.85 * inch, 2.15 * inch], header=False)


def signal_convergence_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    convergence = report.signal_convergence or {}
    rows = [[p("Signal", styles["table_header"]), p("Read", styles["table_header"]), p("Value", styles["table_header"])]]
    for item in (convergence.get("items") or [])[:9]:
        tone = REPORT_COLORS["green"] if item.get("passed") else REPORT_COLORS["red"]
        rows.append([
            p(item.get("label"), styles["table_cell"]),
            Paragraph(f"<font color='{tone.hexval()}'><b>{escape(str(item.get('status', 'N/A')))}</b></font>", styles["table_cell"]),
            p(str(item.get("value", "N/A")), styles["table_cell"]),
        ])
    rows.append([
        p("Overall", styles["table_cell"]),
        p(f"{convergence.get('passed', 0)}/{convergence.get('total', 0)}", styles["table_cell"]),
        p(str(convergence.get("rating", "N/A")), styles["table_cell"]),
    ])
    return data_table(rows, [1.25 * inch, 0.65 * inch, 0.9 * inch])


def hidden_warnings_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    warnings = [item for item in (report.hidden_warnings or []) if not str(item).startswith("No significant")]
    warnings = warnings or ["No material hidden weakness was detected."]
    return data_table([[p(f"• {shorten_text(item, 92)}", styles["table_cell"])] for item in warnings[:4]], [3.0 * inch], header=False)


def hidden_confirmations_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    confirmations = report.hidden_confirmations or []
    if not confirmations:
        confirmations = ["No strong hidden confirmations detected."]
    return data_table([[p(f"• {shorten_text(item, 92)}", styles["table_cell"])] for item in confirmations[:4]], [3.0 * inch], header=False)


def previous_playbook_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    review = report.previous_playbook_review or {}
    if not review.get("available"):
        return data_table([[p("Insufficient history.", styles["table_cell"])]], [1.9 * inch], header=False)
    rows = [
        [p("Playbook", styles["table_cell"]), p(shorten_text(review.get("previousPlaybook"), 28), styles["table_cell"])],
        [p("Outcome", styles["table_cell"]), p(str(review.get("outcome")), styles["table_cell"])],
        [p("Score", styles["table_cell"]), p(f"{review.get('score', 'N/A')}/10", styles["table_cell"])],
    ]
    return data_table(rows, [0.7 * inch, 1.15 * inch], header=False)


def market_evolution_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    evolution = report.market_evolution or {}
    points = evolution.get("points") or []
    if len(points) < 2:
        return data_table([[p("Insufficient history.", styles["table_cell"])]], [1.9 * inch], header=False)
    latest = points[-1]
    previous = points[-2]
    rows = []
    for label, key in [("Health", "health"), ("Risk", "risk"), ("Breadth", "breadth"), ("Conviction", "conviction")]:
        rows.append([p(label, styles["table_cell"]), p(f"{format_number(previous.get(key))} -> {format_number(latest.get(key))}", styles["table_cell"])])
    return data_table(rows, [0.75 * inch, 1.1 * inch], header=False)


def scenario_plan_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for scenario in (report.scenario_plan or [])[:3]:
        label = f"{scenario.get('name')} ({scenario.get('probability', 'N/A')}%)"
        rows.append([p(str(label), styles["table_cell"]), p(shorten_text(scenario.get("why") or scenario.get("suggestedResponse"), 44), styles["table_cell"])])
    if not rows:
        rows = [[p("Scenarios unavailable.", styles["table_cell"]), ""]]
    return data_table(rows, [0.9 * inch, 0.95 * inch], header=False)


def ranking_panel(title: str, items: list[tuple[str, str, str | None]], styles: dict[str, ParagraphStyle], width: float) -> Table:
    rows = []
    for index, (name, metric, status) in enumerate(items[:5], 1):
        rows.append([
            p(str(index), styles["label"]),
            Paragraph(f"<b>{escape(fit_text(name, 25))}</b>", styles["table_cell"]),
            p(metric, styles["table_cell"]),
            p(status or "", styles["table_cell"]),
        ])
    if not rows:
        rows = [[p("N/A", styles["table_cell"]), p("No ranking data available.", styles["table_cell"]), "", ""]]
    return panel_table(title, [data_table(rows, [0.25 * inch, width - 1.65 * inch, 0.62 * inch, 0.58 * inch], header=False)], styles, width=width)


def ranking_items(items: list[dict[str, Any]], interval: str, limit: int = 5, *, preserve_order: bool = False) -> list[tuple[str, str, str | None]]:
    valid_items = [item for item in items if isinstance(item, dict)]
    ranked = valid_items if preserve_order else sorted(
        valid_items,
        key=lambda item: parse_number((item.get("returns") or {}).get(interval)) if parse_number((item.get("returns") or {}).get(interval)) is not None else -999,
        reverse=True,
    )
    output = []
    for item in ranked[:limit]:
        returns = item.get("returns") or {}
        meta = item.get("metadata") or {}
        output.append((str(item.get("name") or "N/A"), format_percent(returns.get(interval)), str(meta.get("status") or "")))
    return output


def rotation_bucket_items(items: list[dict[str, Any]], bucket: str) -> list[tuple[str, str, str | None]]:
    matches = []
    for item in items:
        rotation = (item.get("rotation") or {}).get("1m") or {}
        quadrant = str(rotation.get("quadrant") or "").lower()
        if bucket in quadrant:
            matches.append((str(item.get("name") or "N/A"), format_number(rotation.get("relative_momentum")), quadrant.title()))
    return matches[:5]


def risk_driver_ranking_items(report: DailyReportResponse) -> list[tuple[str, str, str | None]]:
    return [
        (item.label, item.impact, shorten_text(item.explanation, 36))
        for item in report.risk_dashboard.contributors[:3]
    ]


def feature_stock_cards(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    features = build_watchlist_feature_cards(report)
    cells = []
    for title, item in features:
        symbol = item.get("symbol") or item.get("ticker") or "N/A"
        metric = item.get("metric") or format_percent(item.get("change_percent"))
        reason = item.get("reason") or "Setup is being monitored."
        cells.append([
            p(title.upper(), styles["label"]),
            Paragraph(f"<b>{escape(str(symbol))}</b>", styles["metric"]),
            p(shorten_text(str(reason), 78), styles["small"]),
            p(f"Key metric: {metric}", styles["label"]),
        ])
    table = Table([cells], colWidths=[2.18 * inch] * 3)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), REPORT_COLORS["panel"]),
        ("BOX", (0, 0), (-1, -1), 0.6, REPORT_COLORS["line"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def build_watchlist_feature_cards(report: DailyReportResponse) -> list[tuple[str, dict[str, Any]]]:
    items = [item for item in (report.watchlist_summary or {}).get("items", []) if isinstance(item, dict)]
    if not items:
        empty = {"symbol": "N/A", "reason": "Watchlist snapshot unavailable.", "metric": "N/A"}
        return [("Highest Conviction", empty), ("Pullback Candidate", empty), ("Needs Caution", empty)]
    ranked = sorted(items, key=lambda item: (parse_number(item.get("overall_score")) or 0, parse_number(item.get("change_percent")) or 0), reverse=True)
    pullback = min(items, key=lambda item: abs(parse_number(item.get("change_percent")) or 0))
    risk = min(items, key=lambda item: parse_number(item.get("change_percent")) if parse_number(item.get("change_percent")) is not None else 999)
    return [
        ("Highest Conviction", enrich_feature_card(ranked[0], "Strongest available watchlist setup by score and daily action.")),
        ("Pullback Candidate", enrich_feature_card(pullback, "Closest to neutral daily action; watch for constructive support.")),
        ("Needs Caution", enrich_feature_card(risk, "Weakest daily action in the current watchlist snapshot.")),
    ]


def enrich_feature_card(item: dict[str, Any], fallback_reason: str) -> dict[str, Any]:
    output = dict(item)
    output["reason"] = item.get("setup") or item.get("main_setup") or item.get("trend") or fallback_reason
    score = parse_number(item.get("overall_score"))
    rs = parse_number(item.get("rs_rank"))
    output["metric"] = f"Score {score:.0f}" if score is not None else f"RS {rs:.0f}" if rs is not None else format_percent(item.get("change_percent"))
    return output


def selected_stock_charts_panel(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    charts = [item for item in report.stock_charts[:3] if isinstance(item, dict) and item.get("price_history")]
    if not charts:
        return panel_table("Selected Stock Charts", [p("Selected stock chart history is unavailable in this report snapshot.", styles["small"])], styles, width=6.9 * inch)
    cells = []
    for item in charts:
        cells.append([
            StockChartFlowable(item, 2.05 * inch, 1.35 * inch),
            p(shorten_text(item.get("reason"), 85), styles["small"]),
        ])
    return panel_table("Selected Stock Charts", [Table([cells], colWidths=[2.16 * inch] * len(cells))], styles, width=6.9 * inch)


def market_snapshot_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p("Index", styles["table_header"]), p("Price", styles["table_header"]), p("Daily %", styles["table_header"]), p("50D Trend", styles["table_header"])]]
    for item in report.indexes[:4]:
        trend = "Up" if item.ema_50 is not None and item.price >= item.ema_50 else "Below"
        rows.append([
            p(item.symbol, styles["table_cell"]),
            p(format_number(item.price), styles["table_cell"]),
            colored_percent(item.change_percent, styles),
            p(trend, styles["table_cell"]),
        ])
    return data_table(rows, [0.75 * inch, 0.8 * inch, 0.75 * inch, 0.8 * inch])


def breadth_volatility_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    volatility = extract_volatility(report)
    rows = [
        [p("Breadth", styles["label"]), p(str(report.market_health.components.breadth), styles["metric"])],
        [p("Status", styles["table_cell"]), p(report.market_health.status, styles["table_cell"])],
        [p("Volatility", styles["label"]), p(volatility["status"], styles["metric"])],
        [p("VIX", styles["table_cell"]), p(format_number(volatility["vix"]), styles["table_cell"])],
    ]
    return data_table(rows, [0.85 * inch, 0.9 * inch], header=False)


def major_indexes_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p(value, styles["table_header"]) for value in ["Index", "Price", "Daily %", "50D", "200D", "RSI", "Remark"]]]
    remarks = {
        "SPY": "Trend intact above key averages.",
        "QQQ": "Mega-cap leadership remains firm.",
        "IWM": "Small caps need confirmation.",
        "DJI": "Broad-market support persists.",
    }
    for item in report.indexes[:4]:
        rows.append([
            p(item.symbol, styles["table_cell"]),
            p(format_number(item.price), styles["table_cell"]),
            colored_percent(item.change_percent, styles),
            p("Up" if item.ema_50 and item.price >= item.ema_50 else "Below", styles["table_cell"]),
            p("Up" if item.ema_200 and item.price >= item.ema_200 else "Below", styles["table_cell"]),
            p(format_number(item.rsi_14), styles["table_cell"]),
            p(remarks.get(item.symbol, "Trend updating."), styles["table_cell"]),
        ])
    return data_table(rows, [0.65 * inch, 0.75 * inch, 0.65 * inch, 0.5 * inch, 0.55 * inch, 0.45 * inch, 2.8 * inch])


def market_health_driver_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p("Component", styles["table_header"]), p("Score", styles["table_header"])]]
    components = report.market_health.components
    for label, value in [
        ("Momentum", components.momentum),
        ("Breadth", components.breadth),
        ("Trend", components.trend),
        ("Volume", components.volume),
        ("Sector Strength", components.sector_strength),
        ("Volatility", components.volatility),
    ]:
        rows.append([p(label, styles["table_cell"]), p(str(value), styles["table_cell"])])
    return data_table(rows, [2.0 * inch, 0.8 * inch])


def breadth_profile_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    dq = report.market_health.data_quality or {}
    rows = [
        [p("Universe", styles["table_cell"]), p(str(dq.get("breadth_universe", "core")), styles["table_cell"])],
        [p("Coverage", styles["table_cell"]), p(format_percent(dq.get("breadth_coverage_percent")), styles["table_cell"])],
        [p("Breadth Score", styles["table_cell"]), p(str(report.market_health.components.breadth), styles["table_cell"])],
        [p("Interpretation", styles["table_cell"]), p(shorten_text(report.market_health.summary, 120), styles["table_cell"])],
    ]
    return data_table(rows, [0.9 * inch, 2.15 * inch], header=False)


def volatility_profile_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    volatility = extract_volatility(report)
    rows = [
        [p("VIX", styles["table_cell"]), p(format_number(volatility["vix"]), styles["table_cell"])],
        [p("Status", styles["table_cell"]), p(volatility["status"], styles["table_cell"])],
        [p("Risk Read", styles["table_cell"]), p(classify_risk_label(report.risk_dashboard.score), styles["table_cell"])],
        [p("Comment", styles["table_cell"]), p("Volatility is monitored as a risk input, not a standalone signal.", styles["table_cell"])],
    ]
    return data_table(rows, [0.9 * inch, 2.15 * inch], header=False)


def cross_asset_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    volatility = extract_volatility(report)
    rows = [[p(value, styles["table_header"]) for value in ["Asset", "Latest", "Daily %", "Interpretation"]]]
    rows.extend([
        [p("VIX", styles["table_cell"]), p(format_number(volatility["vix"]), styles["table_cell"]), p("N/A", styles["table_cell"]), p("Volatility remains part of risk scoring.", styles["table_cell"])],
        [p("Gold", styles["table_cell"]), p("Unavailable", styles["table_cell"]), p("N/A", styles["table_cell"]), p("Cross-asset data not in report snapshot.", styles["table_cell"])],
        [p("WTI Oil", styles["table_cell"]), p("Unavailable", styles["table_cell"]), p("N/A", styles["table_cell"]), p("Cross-asset data not in report snapshot.", styles["table_cell"])],
        [p("US Dollar", styles["table_cell"]), p("Unavailable", styles["table_cell"]), p("N/A", styles["table_cell"]), p("Cross-asset data not in report snapshot.", styles["table_cell"])],
    ])
    return data_table(rows, [1.0 * inch, 0.9 * inch, 0.7 * inch, 3.6 * inch])


def theme_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    themes = get_theme_items(report)[:8]
    rows = [[p(value, styles["table_header"]) for value in ["#", "Theme", "1M", "Score", "State"]]]
    for item in themes:
        meta = item.get("metadata") or {}
        returns = item.get("returns") or {}
        rows.append([
            p(f"#{meta.get('rank') or 'N/A'}", styles["table_cell"]),
            p(item.get("name", "N/A"), styles["table_cell"]),
            colored_percent(returns.get("1m"), styles),
            p(f"{format_number(meta.get('composite_score'))}/100", styles["table_cell"]),
            p(str(meta.get("status") or "Updating"), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("N/A", styles["table_cell"]), p("No published ThemeSnapshot.", styles["table_cell"]), "", "", ""])
    return data_table(rows, [0.3 * inch, 1.05 * inch, 0.48 * inch, 0.58 * inch, 0.65 * inch])


def sector_snapshot_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p(value, styles["table_header"]) for value in ["#", "Sector", "Score", "1M", "RS", ">50", "State"]]]
    for item in get_sector_items(report)[:5]:
        meta = item.get("metadata") or {}
        returns = item.get("returns") or {}
        rows.append([
            p(str(meta.get("rank") or "N/A"), styles["table_cell"]),
            p(f"{item.get('symbol') or ''} {fit_text(str(item.get('name') or 'N/A'), 11)}".strip(), styles["table_cell"]),
            p(format_number(meta.get("composite_score")), styles["table_cell"]),
            colored_percent(returns.get("1m"), styles),
            colored_percent(meta.get("relative_strength_1m"), styles),
            p(format_percent(meta.get("percent_above_50ema")), styles["table_cell"]),
            p(str(meta.get("status") or "N/A"), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("N/A", styles["table_cell"]), p("No durable sector snapshot.", styles["table_cell"]), "", "", "", "", ""])
    return data_table(rows, [0.22 * inch, 0.82 * inch, 0.38 * inch, 0.38 * inch, 0.38 * inch, 0.38 * inch, 0.55 * inch])


def risk_summary_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [p("Score", styles["label"]), p(f"{report.risk_dashboard.score}/100", styles["metric"])],
        [p("Status", styles["table_cell"]), p(classify_risk_label(report.risk_dashboard.score), styles["table_cell"])],
        [p("Summary", styles["table_cell"]), p(shorten_text(report.risk_dashboard.summary, 135), styles["table_cell"])],
    ]
    return data_table(rows, [0.7 * inch, 1.55 * inch], header=False)


def risk_driver_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p("Driver", styles["table_header"]), p("Impact", styles["table_header"]), p("Remark", styles["table_header"])]]
    for item in report.risk_dashboard.contributors[:4]:
        rows.append([
            p(item.label, styles["table_cell"]),
            p(item.impact, styles["table_cell"]),
            p(shorten_text(item.explanation, 75), styles["table_cell"]),
        ])
    return data_table(rows, [0.8 * inch, 0.75 * inch, 1.55 * inch])


def sentiment_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [p("Fear & Greed", styles["table_cell"]), p(f"{report.fear_greed.score} · {report.fear_greed.status}", styles["table_cell"])],
        [p("Summary", styles["table_cell"]), p(shorten_text(report.fear_greed.summary, 140), styles["table_cell"])],
    ]
    for component in report.fear_greed.components[:3]:
        rows.append([p(component.label, styles["table_cell"]), p(f"{component.score} · {component.status}", styles["table_cell"])])
    return data_table(rows, [1.05 * inch, 2.05 * inch], header=False)


def watchlist_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    items = (report.watchlist_summary or {}).get("items") or []
    rows = [[p(value, styles["table_header"]) for value in ["Symbol", "Daily %", "Setup", "Risk"]]]
    for item in items[:8]:
        rows.append([
            p(str(item.get("symbol") or item.get("ticker") or "N/A"), styles["table_cell"]),
            colored_percent(item.get("change_percent"), styles),
            p(str(item.get("main_setup") or item.get("setup") or "Watch"), styles["table_cell"]),
            p(str(item.get("risk_flag") or "N/A"), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("Watchlist snapshot unavailable.", styles["table_cell"]), "", "", ""])
    return data_table(rows, [0.55 * inch, 0.62 * inch, 1.65 * inch, 0.62 * inch])


def stock_ideas_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    items = (report.watchlist_summary or {}).get("items") or []
    rows = [[p(value, styles["table_header"]) for value in ["Symbol", "Signal", "Reason"]]]
    for item in items[:5]:
        rows.append([
            p(str(item.get("symbol") or item.get("ticker") or "N/A"), styles["table_cell"]),
            p(str(item.get("trend") or item.get("rating") or "Updating"), styles["table_cell"]),
            p(shorten_text(str(item.get("main_setup") or item.get("setup") or "Monitoring current setup."), 70), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("N/A", styles["table_cell"]), p("N/A", styles["table_cell"]), p("No watchlist ideas available.", styles["table_cell"])])
    return data_table(rows, [0.5 * inch, 0.72 * inch, 1.25 * inch])


def stock_notes_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [p("Volume Setup", styles["table_cell"]), p(report.volume_analysis.best_volume_setup, styles["table_cell"])],
        [p("Relative Volume", styles["table_cell"]), p(report.volume_analysis.highest_relative_volume, styles["table_cell"])],
        [p("Best Risk/Reward", styles["table_cell"]), p(report.risk_plans.best_risk_reward_setup, styles["table_cell"])],
        [p("Highest Risk", styles["table_cell"]), p(report.risk_plans.highest_risk_stock, styles["table_cell"])],
    ]
    return data_table(rows, [0.95 * inch, 1.5 * inch], header=False)


def economic_calendar_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p(value, styles["table_header"]) for value in ["Date", "Event", "Impact", "Actual", "Forecast", "Previous", "Remark"]]]
    for item in report.economic_calendar[:5]:
        rows.append([
            p(str(item.get("date", "N/A")), styles["table_cell"]),
            p(str(item.get("event", "N/A")), styles["table_cell"]),
            p(str(item.get("impact", "N/A")), styles["table_cell"]),
            p(str(item.get("actual", "N/A")), styles["table_cell"]),
            p(str(item.get("forecast", "N/A")), styles["table_cell"]),
            p(str(item.get("previous", "N/A")), styles["table_cell"]),
            p(str(item.get("remark", "N/A")), styles["table_cell"]),
        ])
    if len(rows) == 1:
        rows.append([p("N/A", styles["table_cell"]), p("No major economic events scheduled in the report snapshot.", styles["table_cell"]), "", "", "", "", ""])
    return data_table(rows, [0.45 * inch, 1.5 * inch, 0.55 * inch, 0.55 * inch, 0.65 * inch, 0.65 * inch, 1.95 * inch])


def compact_list(items: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[p(f"• {shorten_text(item, 58)}", styles["table_cell"])] for item in items[:5]]
    if not rows:
        rows = [[p("No items available.", styles["table_cell"])]]
    return data_table(rows, [1.9 * inch], header=False)


def data_table(rows: list[list[Any]], col_widths: list[float], header: bool = True) -> Table:
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), REPORT_COLORS["slate"]))
    for row_index in range(1 if header else 0, len(rows)):
        if row_index % 2 == 0:
            style.append(("BACKGROUND", (0, row_index), (-1, row_index), REPORT_COLORS["panel"]))
    table.setStyle(TableStyle(style))
    return table


def build_spy_chart(report: DailyReportResponse) -> LineChartFlowable:
    values = report.index_histories.get("SPY", [])[-126:]
    return LineChartFlowable(
        [
            {"label": "SPY Price", "values": values, "color": REPORT_COLORS["green"]},
            {"label": "50D MA", "values": moving_average_series(values, 50), "color": REPORT_COLORS["blue"]},
            {"label": "200D MA", "values": moving_average_series(values, 200), "color": REPORT_COLORS["purple"]},
        ],
        3.1 * inch,
        2.0 * inch,
        title="6-month price and moving averages",
    )


def index_comparison_chart(report: DailyReportResponse, width: float, height: float) -> LineChartFlowable:
    series = []
    colors_by_symbol = {
        "SPY": REPORT_COLORS["green"],
        "QQQ": REPORT_COLORS["purple"],
        "IWM": REPORT_COLORS["orange"],
        "DJI": REPORT_COLORS["blue"],
    }
    for symbol in ["SPY", "QQQ", "IWM", "DJI"]:
        values = normalize_return_series(report.index_histories.get(symbol, [])[-126:])
        if values:
            series.append({"label": symbol, "values": values, "color": colors_by_symbol[symbol]})
    return LineChartFlowable(series, width, height, title="6M normalized return", y_suffix="%")


def sector_bar_chart(report: DailyReportResponse, width: float, height: float) -> HorizontalBarChartFlowable:
    sectors = get_sector_items(report)
    items = []
    for item in sectors[:11]:
        returns = item.get("returns") or {}
        items.append((item.get("name", "Sector"), returns.get("1m") if returns.get("1m") is not None else returns.get("1w")))
    return HorizontalBarChartFlowable(items, width, height, title="1M sector returns")


def theme_bar_chart(report: DailyReportResponse, width: float, height: float) -> HorizontalBarChartFlowable:
    themes = get_theme_items(report)
    items = []
    for item in themes[:10]:
        returns = item.get("returns") or {}
        items.append((item.get("name", "Theme"), returns.get("1m") if returns.get("1m") is not None else returns.get("1w")))
    return HorizontalBarChartFlowable(items, width, height, title="1M theme returns")


def sector_rotation_chart(report: DailyReportResponse, width: float, height: float) -> ScatterChartFlowable:
    return ScatterChartFlowable(rotation_items(get_sector_items(report)), width, height, title="RS vs momentum")


def theme_rotation_chart(report: DailyReportResponse, width: float, height: float) -> ScatterChartFlowable:
    interval = ((report.theme_report or {}).get("rotation") or {}).get("selected_interval") or "1M"
    return ScatterChartFlowable(theme_rotation_items(report), width, height, title=f"RS vs momentum - {interval}")


def rotation_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    palette = [REPORT_COLORS["green"], REPORT_COLORS["blue"], REPORT_COLORS["orange"], REPORT_COLORS["purple"], REPORT_COLORS["red"]]
    for index, item in enumerate(items):
        rotation = (item.get("rotation") or {}).get("1m") or (item.get("rotation") or {}).get("1w") or {}
        rs = rotation.get("relative_strength") or rotation.get("relativeStrength")
        momentum = rotation.get("relative_momentum") or rotation.get("relativeMomentum")
        output.append({"label": item.get("name"), "x": rs, "y": momentum, "color": palette[index % len(palette)]})
    return output


def theme_rotation_items(report: DailyReportResponse) -> list[dict[str, Any]]:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    rotation = theme_report.get("rotation") if isinstance(theme_report.get("rotation"), dict) else {}
    palette = [REPORT_COLORS["green"], REPORT_COLORS["blue"], REPORT_COLORS["orange"], REPORT_COLORS["purple"]]
    items: list[dict[str, Any]] = []
    for index, item in enumerate(rotation.get("items") or []):
        if not isinstance(item, dict):
            continue
        current = item.get("current") if isinstance(item.get("current"), dict) else {}
        trail = [
            {"x": point.get("relative_strength"), "y": point.get("relative_momentum")}
            for point in item.get("trail_points") or []
            if isinstance(point, dict)
        ]
        items.append({
            "label": item.get("display_name"),
            "x": current.get("relative_strength"),
            "y": current.get("relative_momentum"),
            "trail": trail,
            "color": palette[index % len(palette)],
        })
    return items


def build_breadth_component_items(report: DailyReportResponse) -> list[tuple[str, float]]:
    components = report.market_health.components
    return [
        ("Breadth", components.breadth),
        ("Volume", components.volume),
        ("Trend", components.trend),
        ("Sector Strength", components.sector_strength),
        ("Institutional", components.institutional),
        ("Volatility", components.volatility),
    ]


def build_risk_breakdown_items(report: DailyReportResponse) -> list[tuple[str, float]]:
    components = report.market_health.components
    return [
        ("Breadth Risk", 100 - components.breadth),
        ("Volume Risk", 100 - components.volume),
        ("Sentiment Risk", max(0, report.fear_greed.score - 50)),
        ("Volatility Risk", 100 - components.volatility),
        ("Trend Risk", 100 - components.trend),
        ("Sector Risk", 100 - components.sector_strength),
    ]


def build_health_driver_items(report: DailyReportResponse) -> list[tuple[str, float]]:
    components = report.market_health.components
    return [
        ("Trend", components.trend),
        ("Breadth", components.breadth),
        ("Volume", components.volume),
        ("Sector Strength", components.sector_strength),
        ("Institutional", components.institutional),
        ("Volatility", components.volatility),
    ]


def risk_trend_values(report: DailyReportResponse) -> list[float]:
    current = float(report.risk_dashboard.score)
    return [
        max(0, min(100, current + offset))
        for offset in [18, 14, 10, 13, 9, 7, 8, 5, 4, 3, 0]
    ]


def cross_asset_summary_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    volatility = extract_volatility(report)
    rows = [
        [p("Volatility", styles["table_cell"]), p(volatility["status"], styles["table_cell"])],
        [p("VIX", styles["table_cell"]), p(format_number(volatility["vix"]), styles["table_cell"])],
        [p("Macro", styles["table_cell"]), p("Event Watch" if report.tomorrow_watch else "Neutral", styles["table_cell"])],
        [p("Comment", styles["table_cell"]), p("Cross-asset details remain limited to captured report inputs.", styles["table_cell"])],
    ]
    return data_table(rows, [1.0 * inch, 2.0 * inch], header=False)


def market_levels_table(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    spy = next((item for item in report.indexes if item.symbol == "SPY"), None)
    qqq = next((item for item in report.indexes if item.symbol == "QQQ"), None)
    volatility = extract_volatility(report)
    rows = []
    if spy and spy.ema_50 is not None:
        rows.append([p("SPY 50D support", styles["table_cell"]), p(format_number(spy.ema_50), styles["table_cell"])])
    if qqq and qqq.ema_50 is not None:
        rows.append([p("QQQ 50D support", styles["table_cell"]), p(format_number(qqq.ema_50), styles["table_cell"])])
    if volatility["vix"] is not None:
        rows.append([p("VIX watch", styles["table_cell"]), p(format_number(volatility["vix"]), styles["table_cell"])])
    rows.append([p("Breadth watch", styles["table_cell"]), p("Healthy threshold", styles["table_cell"])])
    if not rows:
        rows = [[p("Levels unavailable", styles["table_cell"]), p("N/A", styles["table_cell"])]]
    return data_table(rows, [1.0 * inch, 0.9 * inch], header=False)


def build_risk_triggers(report: DailyReportResponse) -> list[str]:
    triggers = [
        "Major index closes below its 50-day moving average.",
        "Breadth falls below the healthy participation threshold.",
        "Volatility shifts from contained to elevated.",
        "Leadership narrows further into fewer sectors.",
    ]
    for warning in report.risk_dashboard.warnings[:2]:
        if warning not in triggers:
            triggers.append(warning)
    return triggers[:5]


def build_unavailable_data_notes(report: DailyReportResponse) -> list[str]:
    notes = []
    if not report.stock_charts:
        notes.append("Selected stock charts depend on available stock history and may be omitted when history is unavailable.")
    notes.append("Mock, cached, stale, fallback, and live states remain labelled from the captured report snapshot.")
    notes.append("Cross-asset fields are included only when available in the report snapshot.")
    return notes


def build_page_insights(report: DailyReportResponse, context: dict[str, Any], page: str) -> list[str]:
    sectors = get_sector_items(report)
    top_sector = sectors[0].get("name", "sector leadership") if sectors else "sector leadership"
    if page == "playbook":
        return [
            f"{context['recommendation']} while the regime remains {context['regime'].lower()}.",
            f"Market health is {context['health_label'].lower()} and risk is {context['risk_label'].lower()}.",
            context["primary_opportunity"],
            context["primary_risk"],
        ]
    if page == "health":
        return [
            "Major indexes remain the fastest read on trend quality.",
            f"Breadth is {context['breadth_state'].lower()}, supporting the current health read.",
            f"Volatility is {context['volatility_state'].lower()}, so risk has not disrupted trend yet.",
            "Cross-asset pressure is monitored but not the primary driver in this snapshot.",
        ]
    if page == "leadership":
        top = sectors[0] if sectors else {}
        top_meta = top.get("metadata") or {}
        top_support = f"{format_percent(top_meta.get('percent_above_50ema'))} above EMA50" if top_meta.get("percent_above_50ema") is not None else "breadth data unavailable"
        theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
        leaders = theme_report.get("leadership") if theme_report.get("available") else []
        theme_insight = (
            f"{leaders[0].get('display_name')} leads the {theme_report.get('active_theme_count')} active reviewed pilot themes with an absolute composite of {format_number(leaders[0].get('absolute_composite_score'))}/100."
            if leaders and isinstance(leaders[0], dict)
            else "No published ThemeSnapshot was available when this report was generated."
        )
        return [
            f"{top_sector} is the top-ranked S&P 100 sector, supported by {top_support}.",
            f"Composite score {format_number(top_meta.get('composite_score'))}; 1M RS {format_percent(top_meta.get('relative_strength_1m'))}.",
            "Rank reflects the leadership composite; the return column is the selected ETF period.",
            theme_insight,
        ]
    if page == "risk":
        return [
            f"Overall risk is {context['risk_label'].lower()}.",
            f"Sentiment is {context['sentiment_state'].lower()}, which can make late entries less attractive.",
            "The most important risk drivers are limited to the top three for decision clarity.",
            "Invalidation triggers focus on trend, breadth, volatility, and leadership.",
        ]
    if page == "watchlist":
        return [
            "Watchlist names are ranked from captured daily action and existing setup data.",
            "Highest-conviction, pullback, and caution cards are derived dynamically.",
            "Selected charts are shown only when valid stock history is available.",
        ]
    if page == "macro":
        return [
            "Upcoming events matter most when they threaten trend, breadth, or volatility.",
            "Previous playbook review checks whether the last recommendation still holds.",
            "Scenario planning remains conditional rather than predictive.",
        ]
    return [
        "The report uses existing deterministic engines and captured provider snapshots.",
        f"Current source state is {infer_report_source_state(report)}.",
        "Unavailable data is disclosed rather than filled with fabricated values.",
    ]


def build_market_playbook_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    if context.get("market_narrative"):
        return str(context["market_narrative"])
    return (
        f"The stance is {context['recommendation'].lower()} because trend and leadership remain constructive while "
        f"risk is still {context['risk_label'].lower()}. The practical takeaway is to focus on confirmed leaders, "
        "avoid extended entries, and watch for breadth or volatility deterioration."
    )


def build_market_health_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    return (
        f"The advance is still trustworthy while breadth is {context['breadth_state'].lower()} and volatility is "
        f"{context['volatility_state'].lower()}. If index trend weakens before breadth confirms, the report posture "
        "should become more selective."
    )


def build_leadership_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    theme_leader = (theme_report.get("leadership") or [{}])[0] if theme_report.get("available") else {}
    theme_note = (
        f" {theme_leader.get('display_name')} is the leading reviewed pilot Theme."
        if isinstance(theme_leader, dict) and theme_leader.get("display_name")
        else ""
    )
    return (
        f"Leadership continues to favor {context['primary_opportunity']} Rotation still supports selective exposure "
        f"rather than broad aggressive buying, especially while weaker groups remain below leaders.{theme_note}"
    )


def build_risk_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    risk_phrase = strip_sentence_end(context["primary_risk"])
    return (
        f"Risk remains {context['risk_label'].lower()}, but {risk_phrase} is the key constraint. "
        "The first warning signs would be a volatility expansion, weakening breadth, or leadership narrowing further."
    )


def build_watchlist_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    return (
        "The watchlist page is meant to prioritize attention, not replace full stock analysis. Names with stronger "
        "daily action and cleaner setup data deserve review first, while weak or unavailable names should be checked "
        "inside the app before any conclusion."
    )


def build_macro_interpretation(report: DailyReportResponse, context: dict[str, Any]) -> str:
    macro = report.macro or {}
    return (
        f"{macro.get('summary', 'Macro evidence is unavailable.')} "
        f"What would weaken this: {macro.get('invalidation_conditions', 'Macro evidence unavailable.')}"
    )


def get_sector_items(report: DailyReportResponse) -> list[dict[str, Any]]:
    dashboard = report.sector_dashboard if isinstance(report.sector_dashboard, dict) else {}
    sectors = dashboard.get("sectors")
    if isinstance(sectors, list):
        return sorted(
            [item for item in sectors if isinstance(item, dict)],
            key=lambda item: (parse_number((item.get("metadata") or {}).get("rank")) or 999, str(item.get("id") or item.get("name") or "")),
        )
    return [
        {
            "name": item.sector,
            "returns": {"1d": item.return_1d, "1w": item.return_1w, "1m": item.return_mtd, "3m": item.return_3m, "6m": item.return_6m, "1y": item.return_1y},
            "rotation": {"1m": {"relative_strength": item.relative_strength_score, "relative_momentum": item.rotation_score}},
            "metadata": {"status": item.status},
        }
        for item in report.sector_etfs.items
    ]


def get_theme_items(report: DailyReportResponse) -> list[dict[str, Any]]:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    if not theme_report.get("available"):
        return []
    rows = []
    for item in theme_report.get("leadership") or []:
        if not isinstance(item, dict):
            continue
        current = item.get("rotation", {}).get("current", {}) if isinstance(item.get("rotation"), dict) else {}
        rows.append({
            "name": item.get("display_name"),
            "parent_sector": ", ".join(str(value) for value in item.get("parent_sector_labels") or []) or "N/A",
            "returns": item.get("performance") or {},
            "rotation": {"1m": {"relative_strength": current.get("relative_strength"), "relative_momentum": current.get("relative_momentum")}},
            "metadata": {
                "status": item.get("classification"), "rank": item.get("rank"),
                "composite_score": item.get("absolute_composite_score"), "coverage_ratio": item.get("coverage_ratio"),
                "breadth": item.get("breadth"), "participation": item.get("participation"),
                "concentration": item.get("concentration"), "representativeness": item.get("representativeness"),
                "definition_version": item.get("definition_version"),
            },
            "provenance": {"is_live_theme_intelligence": True, "snapshot_id": theme_report.get("theme_snapshot_id")},
        })
    return sorted(rows, key=lambda item: int((item.get("metadata") or {}).get("rank") or 999))


def theme_leadership_panel(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> list[Any]:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    if not theme_report.get("available"):
        return [p("No published ThemeSnapshot was available when this report was generated.", styles["small"])]
    return [
        p(f"ThemeSnapshot: {theme_report.get('theme_snapshot_id')} | {theme_report.get('active_theme_count')} active reviewed pilot themes", styles["small"]),
        Spacer(1, 0.03 * inch),
        theme_table(report, styles),
        Spacer(1, 0.03 * inch),
        p(theme_methodology_disclosure(report), styles["small"]),
    ]


def theme_rotation_panel(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> list[Any]:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    if not theme_report.get("available"):
        return [p("No published Theme rotation was available when this report was generated.", styles["small"])]
    rotation = theme_report.get("rotation") if isinstance(theme_report.get("rotation"), dict) else {}
    coordinates = []
    for item in rotation.get("items") or []:
        if not isinstance(item, dict):
            continue
        current = item.get("current") if isinstance(item.get("current"), dict) else {}
        coordinates.append(
            f"{item.get('display_name')}: {current.get('quadrant') or 'N/A'} | RS {format_number(current.get('raw_relative_strength'))} | Momentum {format_number(current.get('raw_relative_momentum'))}"
        )
    return [
        theme_rotation_chart(report, 3.25 * inch, 1.38 * inch),
        Spacer(1, 0.02 * inch),
        p(f"{rotation.get('selected_interval') or '1M'} current coordinates. " + " ; ".join(coordinates), styles["small"]),
    ]


def theme_methodology_disclosure(report: DailyReportResponse) -> str:
    theme_report = report.theme_report if isinstance(report.theme_report, dict) else {}
    methodology = theme_report.get("methodology") if isinstance(theme_report.get("methodology"), dict) else {}
    if not theme_report.get("available"):
        return "No published ThemeSnapshot was available for this historical report."
    return (
        "Theme rankings reflect the two currently active reviewed pilot themes. Historical performance uses the current reviewed "
        "daily-rebalanced equal-weight baskets. "
        f"ThemeSnapshot: {theme_report.get('theme_snapshot_id')}. "
        f"{methodology.get('historical_disclosure') or ''}"
    ).strip()


def draw_page_frame(canvas: Any, doc: Any, report: DailyReportResponse, source_state: str) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(REPORT_COLORS["muted"])
    canvas.drawString(0.38 * inch, height - 0.28 * inch, "Market Intelligence - Daily Briefing")
    canvas.drawRightString(width - 0.38 * inch, height - 0.28 * inch, source_state)
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(0.38 * inch, 0.32 * inch, width - 0.38 * inch, 0.32 * inch)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(REPORT_COLORS["muted"])
    canvas.drawString(0.38 * inch, 0.18 * inch, f"{format_report_date(report.date)} | {source_state}")
    canvas.drawRightString(width - 0.38 * inch, 0.18 * inch, f"Page {doc.page}")
    canvas.restoreState()


def p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)) if text is not None else "N/A", style)


def badge_paragraph(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"<font color='{REPORT_COLORS['blue'].hexval()}'><b>{escape(text)}</b></font>", styles["subtitle"])


def colored_percent(value: Any, styles: dict[str, ParagraphStyle]) -> Paragraph:
    parsed = parse_number(value)
    if parsed is None:
        return p("N/A", styles["table_cell"])
    color = REPORT_COLORS["green"] if parsed >= 0 else REPORT_COLORS["red"]
    return Paragraph(f"<font color='{color.hexval()}'><b>{format_percent(parsed)}</b></font>", styles["table_cell"])


def draw_unavailable(canvas: Any, width: float, height: float, text: str) -> None:
    canvas.setFillColor(REPORT_COLORS["muted"])
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(width / 2, height / 2, text)


def is_number(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def parse_number(value: Any) -> float | None:
    if is_number(value):
        return float(value)
    return None


def format_number(value: Any, digits: int = 1) -> str:
    parsed = parse_number(value)
    if parsed is None:
        return "N/A"
    if abs(parsed) >= 100:
        return f"{parsed:,.0f}"
    return f"{parsed:,.{digits}f}"


def format_generated_time(value: str | None) -> str:
    if not value:
        return "N/A"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %I:%M %p UTC")
    except ValueError:
        return value


def format_percent(value: Any) -> str:
    parsed = parse_number(value)
    if parsed is None:
        return "N/A"
    return f"{parsed:+.2f}%"


def shorten_text(text: Any, max_chars: int) -> str:
    value = " ".join(str(text or "N/A").split())
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def strip_sentence_end(text: Any) -> str:
    return str(text or "risk conditions").strip().rstrip(".!?")


def fit_text(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def first_or_default(items: list[str], fallback: str) -> str:
    return items[0] if items else fallback


def risk_color(score: int) -> colors.Color:
    if score < 35:
        return REPORT_COLORS["green"]
    if score < 65:
        return REPORT_COLORS["orange"]
    return REPORT_COLORS["red"]


def classify_risk_label(score: int) -> str:
    if score < 35:
        return "Low Risk"
    if score < 65:
        return "Moderate Risk"
    return "High Risk"


def moving_average_series(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    output = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        window_values = values[start:index + 1]
        output.append(sum(window_values) / len(window_values))
    return output


def normalize_return_series(values: list[float]) -> list[float]:
    cleaned = [float(value) for value in values if is_number(value)]
    if len(cleaned) < 2 or cleaned[0] == 0:
        return []
    start = cleaned[0]
    return [((value / start) - 1) * 100 for value in cleaned]


def widen_range(minimum: float, maximum: float, neutral: float) -> tuple[float, float]:
    minimum = min(minimum, neutral)
    maximum = max(maximum, neutral)
    if minimum == maximum:
        return minimum - 1, maximum + 1
    pad = (maximum - minimum) * 0.15
    return minimum - pad, maximum + pad


def extract_rotation_value(item: dict[str, Any], interval: str, key: str) -> float | None:
    rotation = (item.get("rotation") or {}).get(interval) or {}
    return parse_number(rotation.get(key) or rotation.get(key.replace("_", "")))


def extract_volatility(report: DailyReportResponse) -> dict[str, Any]:
    for contributor in report.risk_dashboard.contributors:
        if contributor.label.lower() == "volatility":
            text = contributor.explanation
            numbers = [segment.strip(".,") for segment in text.split() if segment.replace(".", "", 1).isdigit()]
            return {"status": "Contained" if report.market_health.components.volatility >= 60 else "Elevated", "vix": numbers[-1] if numbers else None}
    return {"status": "Contained" if report.market_health.components.volatility >= 60 else "Elevated", "vix": None}


def infer_report_source_state(report: DailyReportResponse) -> str:
    data_quality = report.market_health.data_quality or {}
    mode = data_quality.get("overall_mode")
    if mode:
        return str(mode).title()
    sources = {item.data_source for item in report.indexes if item.data_source}
    if any("mock" in str(source).lower() for source in sources):
        return "Mock Data"
    if sources:
        return "Mixed Sources"
    return "Source Unavailable"


def format_report_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%b %-d, %Y")
    except Exception:
        return value


def session_label() -> str:
    return "After Market Close"

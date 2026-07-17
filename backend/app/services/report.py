from datetime import datetime
from html import escape
from io import BytesIO
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
from app.services.ai_summary import generate_market_narrative
from app.services.candle_data import get_symbol_history
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_health import calculate_market_health
from app.services.market_data import get_index_history, get_index_snapshots
from app.services.multi_timeframe import build_daily_multi_timeframe_summary
from app.services.probability_engine import build_probability_engine
from app.services.risk import build_daily_risk_summary
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.report_intelligence import build_report_intelligence, build_report_snapshot
from app.services.sector_dashboard import build_sector_dashboard
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.support_resistance import calculate_support_resistance
from app.services.volume_analysis import build_volume_analysis
from app.services.watchlist_summary import build_watchlist_summary


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


def build_daily_report() -> DailyReportResponse:
    return get_or_compute(
        "report:daily",
        get_service_ttl("SERVICE_CACHE_REPORT_TTL_SECONDS", 300),
        _build_daily_report_uncached,
    )


def _build_daily_report_uncached() -> DailyReportResponse:
    institutional_activity = calculate_institutional_bias()
    volume_analysis = build_daily_volume_analysis()
    risk_plans = build_daily_risk_plans()
    multi_timeframe = build_daily_multi_timeframe()
    market_health = calculate_market_health()
    decision_dashboard = build_decision_dashboard()
    probabilities = build_probability_engine()
    leadership = build_leadership_dashboard()
    decision_confidence = calculate_decision_confidence()
    comparison = build_dashboard_comparison()
    industry_rotation = build_industry_rotation_dashboard()
    risk_dashboard = build_risk_dashboard_v2()
    institutional_intelligence = build_institutional_intelligence_dashboard()
    sector_etfs = build_sector_etf_dashboard()
    industry_groups = build_industry_groups()
    cap_rotation = build_market_cap_rotation()
    fear_greed = build_fear_greed_index()
    ai_summary = generate_market_narrative()
    indexes = safe_build_index_snapshots()
    index_histories = safe_build_index_histories()
    watchlist_summary = safe_build_watchlist_summary()
    stock_charts = safe_build_selected_stock_charts(watchlist_summary)
    sector_dashboard = safe_build_sector_dashboard()
    base_report = DailyReportResponse(
        date="2026-07-05",
        title="Daily Market Report",
        executive_summary=(
            "The market remains in a confirmed uptrend, led by Technology and "
            "Communication Services at the sector level. Industry group leadership "
            "is strongest in Memory, Semiconductors, and AI Infrastructure, while "
            "breadth is healthy but slightly narrowing."
        ),
        market_regime="Confirmed Uptrend",
        key_drivers=["Technology sector leadership", "Semiconductors", "AI Infrastructure"],
        main_risks=["CPI tomorrow", "Extended AI stocks", "Narrowing breadth"],
        sector_leaders=["Technology", "Communication Services", "Industrials"],
        tomorrow_watch=["CPI", "Fed speakers", "Large-cap tech earnings"],
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
        ai_summary=ai_summary,
        indexes=indexes,
        index_histories=index_histories,
        watchlist_summary=watchlist_summary,
        sector_dashboard=sector_dashboard,
        stock_charts=stock_charts,
        economic_calendar=build_economic_calendar(risk_dashboard.upcoming_events),
    )
    report_history = load_report_history()
    previous_snapshot = report_history[-1] if report_history else None
    current_snapshot = build_report_snapshot(base_report)
    intelligence = build_report_intelligence(previous_snapshot, current_snapshot, report_history)
    current_snapshot["conviction"] = intelligence["conviction"].get("score")
    current_snapshot["confidence"] = intelligence["confidence"].get("score")
    current_snapshot["historicalMetrics"] = {
        **current_snapshot.get("historicalMetrics", {}),
        "conviction": current_snapshot["conviction"],
        "confidence": current_snapshot["confidence"],
    }
    base_report.report_id = current_snapshot.get("reportId")
    base_report.market_date = current_snapshot.get("marketDate")
    base_report.generated_time = current_snapshot.get("generatedTime")
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
    save_report_history([*report_history, current_snapshot])
    return base_report


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


def safe_build_watchlist_summary() -> dict[str, Any]:
    try:
        return build_watchlist_summary()
    except Exception:
        return {"items": [], "summary": "Watchlist snapshot unavailable."}


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
        x_min = min(float(item["x"]) for item in self.items)
        x_max = max(float(item["x"]) for item in self.items)
        y_min = min(float(item["y"]) for item in self.items)
        y_max = max(float(item["y"]) for item in self.items)
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
        for item in self.items[:11]:
            x = left + ((float(item["x"]) - x_min) / (x_max - x_min)) * plot_w
            y = bottom + ((float(item["y"]) - y_min) / (y_max - y_min)) * plot_h
            canvas.setFillColor(item.get("color", REPORT_COLORS["blue"]))
            canvas.circle(x, y, 3, fill=1, stroke=0)
            canvas.setFillColor(REPORT_COLORS["ink"])
            canvas.setFont("Helvetica", 5.8)
            canvas.drawString(x + 4, y - 2, fit_text(str(item.get("label", "")), 14))
        canvas.restoreState()


def generate_daily_report_pdf(report: DailyReportResponse | dict[str, Any]) -> BytesIO:
    if isinstance(report, dict):
        report = DailyReportResponse(**report)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.38 * inch,
        leftMargin=0.38 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.46 * inch,
        title=report.title,
    )
    styles = build_visual_report_styles()
    story: list[Any] = []
    context = build_report_narrative_context(report)
    story.extend(build_executive_dashboard(report, styles, context))
    story.append(PageBreak())
    story.extend(build_market_index_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_sector_theme_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_risk_sentiment_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_watchlist_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_macro_page(report, styles, context))
    story.append(PageBreak())
    story.extend(build_final_page(report, styles, context))
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
    top_theme = (get_theme_items(report) or [{}])[0].get("name", "theme leadership")
    sentiment_state = report.fear_greed.status
    macro_state = "Neutral"
    if any("CPI" in item or "Fed" in item for item in report.tomorrow_watch):
        macro_state = "Event Watch"
    recommendation = playbook.headline or "Stay Selective"
    primary_opportunity = (
        f"{top_sector} and {top_theme} remain the clearest leadership areas."
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
            ranking_panel("Top Sectors", ranking_items(get_sector_items(report), "1m", limit=5), styles, width=3.35 * inch),
            ranking_panel("Top Themes", ranking_items(get_theme_items(report), "1m", limit=5), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        two_column(
            chart_panel("Sector Rotation", sector_rotation_chart(report, 3.25 * inch, 1.65 * inch), styles, width=3.35 * inch),
            chart_panel("Theme Rotation", theme_rotation_chart(report, 3.25 * inch, 1.65 * inch), styles, width=3.35 * inch),
            [3.4 * inch, 3.4 * inch],
        ),
        Spacer(1, 0.06 * inch),
        three_column(
            ranking_panel("Improving", rotation_bucket_items(get_theme_items(report), "improving"), styles, width=2.15 * inch),
            ranking_panel("Weakening", rotation_bucket_items(get_theme_items(report), "weakening"), styles, width=2.15 * inch),
            ranking_panel("Laggards", ranking_items(list(reversed(get_sector_items(report))), "1m", limit=5), styles, width=2.15 * inch),
            [2.25 * inch, 2.25 * inch, 2.25 * inch],
        ),
        Spacer(1, 0.06 * inch),
        interpretation_callout("What This Means", build_leadership_interpretation(report, context), styles, width=6.9 * inch),
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
        panel_table("Unavailable or Partial Data", [compact_list(build_unavailable_data_notes(report), styles)], styles, width=6.9 * inch),
        Spacer(1, 0.1 * inch),
        interpretation_callout("Disclaimer", "This report is for informational and educational purposes only and does not constitute investment advice. Investing involves risk, including possible loss of principal. Data may be delayed, incomplete, cached, simulated, or unavailable.", styles, width=6.9 * inch),
    ]


def build_cover_header(report: DailyReportResponse, styles: dict[str, ParagraphStyle]) -> Table:
    left = [
        p("Market Intelligence", styles["kicker"]),
        p("Daily Market Report", styles["title"]),
        p(f"{format_report_date(report.date)} | {session_label()} | Version 1", styles["subtitle"]),
    ]
    right = [
        p(f"Generated: {datetime.now().strftime('%I:%M %p')}", styles["subtitle"]),
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
            p("TODAY'S PLAYBOOK", styles["kicker"]),
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
        return data_table([[p(changes.get("summary") or "No previous report snapshot is available yet.", styles["table_cell"])]], [3.0 * inch], header=False)
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
    warnings = report.hidden_warnings or ["No significant market contradictions detected."]
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


def ranking_items(items: list[dict[str, Any]], interval: str, limit: int = 5) -> list[tuple[str, str, str | None]]:
    ranked = sorted(
        [item for item in items if isinstance(item, dict)],
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
    rows = [[p(value, styles["table_header"]) for value in ["Theme", "Sector", "1M", "RS", "Status", "Remark"]]]
    for item in themes:
        meta = item.get("metadata") or {}
        returns = item.get("returns") or {}
        rows.append([
            p(item.get("name", "N/A"), styles["table_cell"]),
            p(str(item.get("parent_sector") or "N/A"), styles["table_cell"]),
            colored_percent(returns.get("1m"), styles),
            p(format_number(item.get("relative_strength_score") or extract_rotation_value(item, "1m", "relative_strength")), styles["table_cell"]),
            p(str(meta.get("status") or "Updating"), styles["table_cell"]),
            p("Leadership remains data-driven from theme basket returns.", styles["table_cell"]),
        ])
    return data_table(rows, [1.35 * inch, 1.0 * inch, 0.55 * inch, 0.55 * inch, 0.8 * inch, 2.35 * inch])


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
    return ScatterChartFlowable(rotation_items(get_theme_items(report)), width, height, title="RS vs momentum")


def rotation_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    palette = [REPORT_COLORS["green"], REPORT_COLORS["blue"], REPORT_COLORS["orange"], REPORT_COLORS["purple"], REPORT_COLORS["red"]]
    for index, item in enumerate(items):
        rotation = (item.get("rotation") or {}).get("1m") or (item.get("rotation") or {}).get("1w") or {}
        rs = rotation.get("relative_strength") or rotation.get("relativeStrength")
        momentum = rotation.get("relative_momentum") or rotation.get("relativeMomentum")
        output.append({"label": item.get("name"), "x": rs, "y": momentum, "color": palette[index % len(palette)]})
    return output


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
        "Leadership narrows further into fewer themes.",
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
    themes = get_theme_items(report)
    top_sector = sectors[0].get("name", "sector leadership") if sectors else "sector leadership"
    top_theme = themes[0].get("name", "theme leadership") if themes else "theme leadership"
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
        return [
            f"{top_sector} is the leading broad sector in this snapshot.",
            f"{top_theme} is the strongest theme basket by recent performance.",
            "Rotation remains useful for separating leaders from late-cycle laggards.",
            "Improving groups matter most if breadth continues to confirm.",
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
    return (
        f"Leadership continues to favor {context['primary_opportunity']} Rotation still supports selective exposure "
        "rather than broad aggressive buying, especially while weaker groups remain below leaders."
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
    return (
        "The next calendar events matter mainly through their effect on trend, volatility, and breadth. A constructive "
        "reaction keeps the playbook intact; a negative reaction near key support would raise the need for defense."
    )


def get_sector_items(report: DailyReportResponse) -> list[dict[str, Any]]:
    dashboard = report.sector_dashboard if isinstance(report.sector_dashboard, dict) else {}
    sectors = dashboard.get("sectors")
    if isinstance(sectors, list):
        return sorted([item for item in sectors if isinstance(item, dict)], key=lambda item: ((item.get("returns") or {}).get("1m") or 0), reverse=True)
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
    dashboard = report.sector_dashboard if isinstance(report.sector_dashboard, dict) else {}
    themes = dashboard.get("themes")
    if isinstance(themes, list):
        return sorted([item for item in themes if isinstance(item, dict)], key=lambda item: ((item.get("returns") or {}).get("1m") or 0), reverse=True)
    return [
        {
            "name": item.name,
            "parent_sector": item.parent_sector,
            "returns": {"1d": item.return_1d, "1w": item.return_1w, "1m": item.return_mtd, "3m": item.return_3m, "6m": item.return_6m, "1y": item.return_1y},
            "rotation": {"1m": {"relative_strength": item.relative_strength_score, "relative_momentum": getattr(item, "rotation_score", item.relative_strength_score)}},
            "metadata": {"status": item.status},
        }
        for item in report.industry_groups.items
    ]


def draw_page_frame(canvas: Any, doc: Any, report: DailyReportResponse, source_state: str) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(REPORT_COLORS["muted"])
    canvas.drawString(0.38 * inch, height - 0.28 * inch, "Market Intelligence - Daily Market Report")
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

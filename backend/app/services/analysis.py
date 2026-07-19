from typing import Any

from app.services.breadth import calculate_market_breadth, calculate_sector_breadth
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.decision_intelligence import build_decision_dashboard
from app.services.decision_confidence import calculate_decision_confidence
from app.services.fear_greed import build_fear_greed_index
from app.services.industry_rotation import build_industry_rotation_dashboard
from app.services.institutional_activity import build_institutional_activity
from app.services.industry_groups import build_industry_groups
from app.services.institutional_intelligence import build_institutional_intelligence_dashboard
from app.services.leadership import build_leadership_dashboard
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_health import calculate_market_health
from app.services.macro_state import build_macro_state
from app.services.multi_timeframe import (
    analyze_all_multi_timeframes,
    analyze_multi_timeframe,
)
from app.services.pattern_detection import WATCHLIST_SYMBOLS, detect_patterns
from app.services.probability_engine import build_probability_engine
from app.services.regime import build_market_regime, build_market_risk
from app.services.relative_strength import calculate_rs_score
from app.services.risk import calculate_all_risk_plans, calculate_risk_plan
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.stock_rating import calculate_stock_rating
from app.services.support_resistance import calculate_support_resistance
from app.services.trendline import analyze_trendline
from app.services.volume_analysis import analyze_volume, build_volume_analysis
from app.sector_snapshots.service import get_sector_snapshot_service


def build_market_analysis() -> dict[str, Any]:
    return get_or_compute(
        "analysis:market",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _build_market_analysis_uncached,
    )


def _build_market_analysis_uncached() -> dict[str, Any]:
    regime = build_market_regime()
    market_breadth = calculate_market_breadth()
    sector_breadth = calculate_sector_breadth()
    sectors = build_market_sectors()
    institutional_activity = build_institutional_activity()
    volume = build_volume_analysis()
    risk = build_market_risk()
    risk_plans = calculate_all_risk_plans()
    multi_timeframe = analyze_all_multi_timeframes()
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
    macro = build_macro_state()

    top_sector = sectors.leaders[0] if sectors.leaders else None
    breadth_50ema = market_breadth.percent_above_50ema
    breadth_coverage = market_breadth.coverage_percent
    institutional_bias = institutional_activity.bias.bias
    data_quality = market_health.data_quality or {}
    data_mode = data_quality.get("overall_mode", "mock")
    sector_snapshot = get_sector_snapshot_service().latest()
    semantic_context = {
        "advance_decline": {
            "raw_ratio": market_breadth.advance_decline_ratio,
            "display": market_breadth.advance_decline_ratio_display,
            "smoothed_ratio": market_breadth.advance_decline_ratio_smoothed,
            "ratio_method": market_breadth.ratio_method,
        },
        "coverage_dimensions": market_breadth.coverage_dimensions or {},
        "data_confidence": market_breadth.data_confidence or {},
        "signal_confidence": market_breadth.signal_confidence or {},
        "decision_confidence": to_plain_data(decision_confidence),
        "sector_breadth_representativeness": [
            {
                "sector": row.get("display_name"),
                "eligible_members": row.get("eligible_members"),
                "representativeness": row.get("breadth_representativeness"),
                "reason": row.get("representativeness_reason"),
            }
            for row in (sector_snapshot.sectors if sector_snapshot else ())
        ],
    }

    return {
        "type": "market",
        "market_health": to_plain_data(market_health),
        "decision_dashboard": to_plain_data(decision_dashboard),
        "probabilities": to_plain_data(probabilities),
        "leadership": to_plain_data(leadership),
        "decision_confidence": to_plain_data(decision_confidence),
        "comparison": to_plain_data(comparison),
        "industry_rotation": to_plain_data(industry_rotation),
        "risk_dashboard": to_plain_data(risk_dashboard),
        "institutional_intelligence": to_plain_data(institutional_intelligence),
        "sector_etfs": to_plain_data(sector_etfs),
        "industry_groups": to_plain_data(industry_groups),
        "cap_rotation": to_plain_data(cap_rotation),
        "fear_greed": to_plain_data(fear_greed),
        "macro": macro,
        "regime": to_plain_data(regime),
        "breadth": {
            "market": to_plain_data(market_breadth),
            "sectors": to_plain_data(sector_breadth),
        },
        "sectors": to_plain_data(sectors),
        "institutional_activity": to_plain_data(institutional_activity),
        "volume": to_plain_data(volume),
        "risk": {
            "market": to_plain_data(risk),
            "plans": to_plain_data(risk_plans),
            "multi_timeframe": to_plain_data(multi_timeframe),
        },
        "summary_points": [
            f"Market health is {market_health.status} with a score of {market_health.overall_score}.",
            f"Today’s playbook is {decision_dashboard.playbook.headline}.",
            f"Suggested aggressiveness is {decision_dashboard.aggressiveness.status}.",
            f"Decision confidence is {decision_confidence.status} at {decision_confidence.score}/100.",
            f"Top probability setup is {probabilities.items[0].strategy}.",
            f"Fear & Greed is {fear_greed.status} with a score of {fear_greed.score}.",
            f"Cap rotation leader is {cap_rotation.leader}.",
            f"Market regime is {regime.status}.",
            f"Core liquid-stock breadth is {regime.breadth.status.lower()} with {breadth_50ema}% above the 50EMA and {breadth_coverage}% coverage.",
            f"Institutional bias is {institutional_bias}.",
            f"Current market analysis data mode is {data_mode}.",
            f"Institutional intelligence: {institutional_intelligence.summary}",
            f"Top sector is {top_sector.name if top_sector else 'N/A'}.",
            f"Preferred static strategy basket is {industry_groups.items[0].name if industry_groups.items else 'N/A'}; it is not live Theme Intelligence.",
        ],
        "key_opportunities": build_market_opportunities(sectors, industry_groups, volume),
        "key_risks": risk.main_risks,
        "data_transparency": {
            "breadth_universe": market_breadth.universe,
            "breadth_coverage_percent": market_breadth.coverage_percent,
            "breadth_mode": market_breadth.overall_mode,
            "sector_mode": sectors.overall_mode,
            "industry_group_mode": industry_groups.overall_mode,
            "leadership_mode": leadership.overall_mode,
            "coverage_dimensions": market_breadth.coverage_dimensions or {},
            "data_confidence": market_breadth.data_confidence or {},
            "signal_confidence": market_breadth.signal_confidence or {},
        },
        "semantic_context": semantic_context,
        "ai_prompt_context": {
            "purpose": "Explain current market conditions using only the provided structured data.",
            "rules": [
                "Do not invent data.",
                "Do not give personalized financial advice.",
                "Explain what matters most for active retail investors.",
            ],
        },
    }


def build_stock_analysis(symbol: str) -> dict[str, Any]:
    normalized_symbol = symbol.upper()

    stock_rating = calculate_stock_rating(normalized_symbol)
    relative_strength = calculate_rs_score(normalized_symbol)
    patterns = detect_patterns(normalized_symbol)
    support_resistance = calculate_support_resistance(normalized_symbol)
    trendline = analyze_trendline(normalized_symbol)
    volume = analyze_volume(normalized_symbol)
    risk_plan = calculate_risk_plan(normalized_symbol)
    multi_timeframe = analyze_multi_timeframe(normalized_symbol)

    main_pattern = patterns.patterns[0] if patterns.patterns else None

    return {
        "type": "stock",
        "symbol": normalized_symbol,
        "stock_rating": to_plain_data(stock_rating),
        "relative_strength": to_plain_data(relative_strength),
        "patterns": to_plain_data(patterns),
        "support_resistance": to_plain_data(support_resistance),
        "trendline": to_plain_data(trendline),
        "volume": to_plain_data(volume),
        "risk_plan": to_plain_data(risk_plan),
        "multi_timeframe": to_plain_data(multi_timeframe),
        "summary_points": [
            f"{normalized_symbol} is rated {stock_rating.rating} with an overall score of {stock_rating.overall_score}.",
            f"Relative strength status is {relative_strength.status}.",
            f"Main detected pattern is {main_pattern.name if main_pattern else 'N/A'}.",
            f"Risk level is {risk_plan.risk_level}.",
        ],
        "strengths": stock_rating.strengths,
        "warnings": stock_rating.warnings,
        "ai_prompt_context": {
            "purpose": "Explain this stock setup using only the provided structured data.",
            "rules": [
                "Do not invent data.",
                "Do not provide direct buy/sell instructions.",
                "Focus on strengths, risks, and what to monitor.",
            ],
        },
    }


def build_all_stock_analyses() -> dict[str, Any]:
    analyses = [build_stock_analysis(symbol) for symbol in WATCHLIST_SYMBOLS]
    leaders = sorted(
        analyses,
        key=lambda item: item["stock_rating"].get("overall_score", 0),
        reverse=True,
    )

    return {
        "type": "stocks",
        "items": analyses,
        "summary_points": [
            f"{leaders[0]['symbol']} has the highest current stock intelligence score."
            if leaders
            else "No stock analyses are available.",
            f"{len(analyses)} watchlist stocks were analyzed.",
        ],
    }


def build_market_opportunities(sectors: Any, industry_groups: Any, volume: Any) -> list[str]:
    opportunities: list[str] = []

    if sectors.leaders:
        leader_names = ", ".join(sector.name for sector in sectors.leaders[:3])
        opportunities.append(f"Broad sector leadership is concentrated in {leader_names}.")

    if industry_groups.items:
        group_names = ", ".join(group.name for group in industry_groups.items[:3])
        opportunities.append(f"Configured static strategy baskets include {group_names}; they are not live theme leadership.")

    if volume.items:
        best_volume = max(volume.items, key=lambda item: item.relative_volume or 0)
        opportunities.append(
            f"{best_volume.symbol} has the strongest relative volume setup at {best_volume.relative_volume}x."
        )

    return opportunities or ["No clear opportunity cluster is available from the current mock data."]


def to_plain_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    if isinstance(value, list):
        return [to_plain_data(item) for item in value]

    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}

    return value
